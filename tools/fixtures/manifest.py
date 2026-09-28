#!/usr/bin/env python3
"""Validator for the F1 fixture manifest (fixtures/f1/instances.yaml).

Contract: specs/001-connect-and-browse/contracts/fixture-format.md

This tool is deliberately independent of the fixture builder (T060): it only
parses and checks the manifest document. It never touches a real Hermes home,
opens a socket, or mutates anything.

Checks performed, beyond the JSON Schema in fixtures/f1/SCHEMA.json:

  1. ``continuity_evidence`` is exactly ``false``. Fixtures are never
     continuity evidence (owner amendment 3); this manifest format states it
     explicitly, and this tool refuses to run if it has been changed.
  2. Every explicit (non-generated) message text starts with the manifest's
     ``label_prefix``, so seeded content is always clearly labelled as
     synthetic.
  3. No string value anywhere in the manifest looks like a real email
     address, hostname/domain, or IPv4/IPv6 address. Reserved,
     non-resolving test domains (RFC 2606 / RFC 6761: ``.invalid``,
     ``.example``, ``.test``, ``.localhost``, ``.local``) are allowed, since
     the contract itself uses ``example.invalid`` as a synthetic hostile-URL
     payload.
  4. Cross references resolve: every ``authorize_for`` entry names a user key
     declared on that instance; every ``conversation`` reference (on a
     profile or a mutation) names a conversation declared at the top level.
  5. Every required instance (``A`` and ``B``) has at least one profile with
     an empty history (``conversation`` null/absent) and at least one
     profile with a non-empty history (``conversation`` set) — the F1
     fixtures must cover both cases for both instances.
  6. ``device_name_prefix`` and ``operator_label_prefix`` are present and
     equal exactly the CS-22 scannable prefixes from
     contracts/fixture-format.md rule 7 (``f1-fixture-device-`` and
     ``f1-fixture-label-``). ``tools/ci/scan_logs.py`` (T033) greps logs for
     these literal prefixes, so a fixture builder or test client that reads
     them from this manifest can never drift from what the scanner expects
     (IR-17).

The JSON Schema structural pass uses ``jsonschema`` when it is importable;
when it is not, this tool still runs the semantic checks above (which need
only the standard library plus PyYAML) and reports that the schema pass was
skipped, rather than failing the whole run on a missing optional dependency.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment error, not a validation result
    raise SystemExit(
        "tools/fixtures/manifest.py requires PyYAML. Install it in your venv: "
        "pip install pyyaml"
    ) from exc

try:
    import jsonschema
except ImportError:  # pragma: no cover - optional dependency
    jsonschema = None  # type: ignore[assignment]


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
DEFAULT_MANIFEST_PATH = REPO_ROOT / "fixtures" / "f1" / "instances.yaml"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "fixtures" / "f1" / "SCHEMA.json"

VALID_ROLES = {"user", "assistant", "tool", "system"}
REQUIRED_INSTANCE_KEYS = {"A", "B"}

# CS-22 scannable prefixes (contracts/fixture-format.md rule 7). Fixed,
# exact values — not just a naming convention. tools/ci/scan_logs.py (T033)
# greps logs for these literal strings.
CS22_DEVICE_NAME_PREFIX = "f1-fixture-device-"
CS22_OPERATOR_LABEL_PREFIX = "f1-fixture-label-"

# RFC 2606 / RFC 6761 reserved domains that never resolve to a real host and
# are therefore safe to use as synthetic payloads (e.g. inside hostile text
# meant to exercise link/markup rendering).
RESERVED_TLDS = {"invalid", "example", "test", "localhost", "local", "arpa"}

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_HOSTNAME_RE = re.compile(
    r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+([A-Za-z]{2,63})\b"
)
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
)
_IPV6_RE = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{0,4}\b")


class ManifestValidationError(Exception):
    """Raised with all accumulated validation errors."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_manifest(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_schema(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check_schema(manifest: Any, schema: dict) -> list[str]:
    """Structural validation against SCHEMA.json. Returns [] if jsonschema
    is unavailable (the semantic checks below still run in that case)."""
    if jsonschema is None:
        return []
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"schema: {location}: {err.message}")
    return errors


def check_continuity_evidence(manifest: dict) -> list[str]:
    value = manifest.get("continuity_evidence", "<missing>")
    if value is not False:
        return [
            "continuity_evidence must be exactly `false` "
            f"(got {value!r}); fixtures are never continuity evidence"
        ]
    return []


def check_label_prefix(manifest: dict) -> list[str]:
    errors: list[str] = []
    prefix = manifest.get("label_prefix")
    if not prefix or not isinstance(prefix, str):
        return ["label_prefix is missing or empty; every seeded message must be labelled"]

    conversations = manifest.get("conversations") or {}
    if not isinstance(conversations, dict):
        return errors
    for conv_key, conv in conversations.items():
        if not isinstance(conv, dict):
            continue
        messages = conv.get("messages")
        if not isinstance(messages, list):
            continue
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
            text = msg.get("text")
            if not isinstance(text, str) or not text.startswith(prefix):
                errors.append(
                    f"conversations.{conv_key}.messages[{i}] text does not start with "
                    f"label_prefix {prefix!r}"
                )
    return errors


def check_scannable_prefixes(manifest: dict) -> list[str]:
    """CS-22 (contracts/fixture-format.md rule 7, IR-17): device_name_prefix
    and operator_label_prefix must be present and equal exactly the fixed
    scannable prefixes tools/ci/scan_logs.py (T033) greps for. These are not
    a naming convention a fixture author can vary — they are the literal
    strings the log scanner matches on, so any drift here silently breaks
    T033's leak detection."""
    errors: list[str] = []

    device_prefix = manifest.get("device_name_prefix", "<missing>")
    if device_prefix != CS22_DEVICE_NAME_PREFIX:
        errors.append(
            "device_name_prefix must be exactly "
            f"{CS22_DEVICE_NAME_PREFIX!r} (CS-22; got {device_prefix!r})"
        )

    operator_prefix = manifest.get("operator_label_prefix", "<missing>")
    if operator_prefix != CS22_OPERATOR_LABEL_PREFIX:
        errors.append(
            "operator_label_prefix must be exactly "
            f"{CS22_OPERATOR_LABEL_PREFIX!r} (CS-22; got {operator_prefix!r})"
        )

    return errors


def _iter_strings(value: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _iter_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _iter_strings(v, f"{path}[{i}]")


def _looks_real(match_tld: str) -> bool:
    return match_tld.lower() not in RESERVED_TLDS


def check_no_real_identifiers(manifest: dict) -> list[str]:
    errors: list[str] = []
    for path, text in _iter_strings(manifest, ""):
        for m in _EMAIL_RE.finditer(text):
            tld = m.group(1).rsplit(".", 1)[-1]
            if _looks_real(tld):
                errors.append(f"{path}: looks like a real email address: {m.group(0)!r}")
        for m in _IPV4_RE.finditer(text):
            errors.append(f"{path}: looks like a real IPv4 address: {m.group(0)!r}")
        for m in _IPV6_RE.finditer(text):
            errors.append(f"{path}: looks like a real IPv6 address: {m.group(0)!r}")
        for m in _HOSTNAME_RE.finditer(text):
            tld = m.group(1)
            if _looks_real(tld):
                errors.append(f"{path}: looks like a real hostname/domain: {m.group(0)!r}")
    return errors


def check_references(manifest: dict) -> list[str]:
    errors: list[str] = []
    instances = manifest.get("instances")
    conversations = manifest.get("conversations") or {}
    conversation_keys = set(conversations) if isinstance(conversations, dict) else set()

    if not isinstance(instances, list):
        return ["instances must be a list"]

    seen_instance_keys: set[str] = set()
    for idx, instance in enumerate(instances):
        if not isinstance(instance, dict):
            errors.append(f"instances[{idx}] must be a mapping")
            continue
        key = instance.get("key")
        if key in seen_instance_keys:
            errors.append(f"instances[{idx}]: duplicate instance key {key!r}")
        if isinstance(key, str):
            seen_instance_keys.add(key)

        users = instance.get("users") or []
        user_keys = {u.get("key") for u in users if isinstance(u, dict)}

        profiles = instance.get("profiles") or []
        if not isinstance(profiles, list):
            errors.append(f"instances[{idx}] ({key}): profiles must be a list")
            continue
        for pidx, profile in enumerate(profiles):
            if not isinstance(profile, dict):
                errors.append(f"instances[{idx}] ({key}): profiles[{pidx}] must be a mapping")
                continue
            for auth_user in profile.get("authorize_for") or []:
                if auth_user not in user_keys:
                    errors.append(
                        f"instances[{idx}] ({key}): profile {profile.get('name')!r} "
                        f"authorizes unknown user key {auth_user!r}"
                    )
            conv = profile.get("conversation")
            if conv is not None and conv not in conversation_keys:
                errors.append(
                    f"instances[{idx}] ({key}): profile {profile.get('name')!r} "
                    f"references unknown conversation {conv!r}"
                )
            # Amendment A1 (session browsing): other_sessions' own conversation references, and
            # parent_session_id must name another other_session declared on the SAME profile.
            other_sessions = profile.get("other_sessions") or []
            other_ids = {
                o.get("session_id") for o in other_sessions if isinstance(o, dict)
            }
            for oidx, other in enumerate(other_sessions):
                if not isinstance(other, dict):
                    continue
                oconv = other.get("conversation")
                if oconv is not None and oconv not in conversation_keys:
                    errors.append(
                        f"instances[{idx}] ({key}): profile {profile.get('name')!r} "
                        f"other_sessions[{oidx}] references unknown conversation {oconv!r}"
                    )
                parent = other.get("parent_session_id")
                if parent is not None and parent not in other_ids:
                    errors.append(
                        f"instances[{idx}] ({key}): profile {profile.get('name')!r} "
                        f"other_sessions[{oidx}] references unknown parent_session_id {parent!r}"
                    )

    mutations = manifest.get("mutations") or {}
    if isinstance(mutations, dict):
        for mut_key, mutation in mutations.items():
            if not isinstance(mutation, dict):
                continue
            conv = mutation.get("conversation")
            if conv is not None and conv not in conversation_keys:
                errors.append(
                    f"mutations.{mut_key}: references unknown conversation {conv!r}"
                )

    missing_required = REQUIRED_INSTANCE_KEYS - seen_instance_keys
    if missing_required:
        errors.append(
            "instances must include both required fixture instances "
            f"{sorted(REQUIRED_INSTANCE_KEYS)}; missing {sorted(missing_required)}"
        )

    return errors


def check_history_coverage(manifest: dict) -> list[str]:
    errors: list[str] = []
    instances = manifest.get("instances")
    if not isinstance(instances, list):
        return errors

    for instance in instances:
        if not isinstance(instance, dict):
            continue
        key = instance.get("key")
        if key not in REQUIRED_INSTANCE_KEYS:
            continue
        profiles = instance.get("profiles") or []
        has_empty = False
        has_nonempty = False
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            conv = profile.get("conversation")
            if conv is None:
                has_empty = True
            else:
                has_nonempty = True
        if not has_empty:
            errors.append(
                f"instance {key!r} has no empty-history profile "
                "(a profile with conversation: null)"
            )
        if not has_nonempty:
            errors.append(
                f"instance {key!r} has no non-empty-history profile "
                "(a profile with a conversation reference)"
            )
    return errors


def validate(manifest: Any, schema: dict | None = None) -> list[str]:
    """Run every check and return the accumulated list of error strings
    (empty means the manifest is valid)."""
    if not isinstance(manifest, dict):
        return ["manifest root must be a mapping"]

    errors: list[str] = []
    if schema is not None:
        errors += check_schema(manifest, schema)
    errors += check_continuity_evidence(manifest)
    errors += check_label_prefix(manifest)
    errors += check_scannable_prefixes(manifest)
    errors += check_no_real_identifiers(manifest)
    errors += check_references(manifest)
    errors += check_history_coverage(manifest)
    return errors


def validate_or_raise(manifest: Any, schema: dict | None = None) -> None:
    errors = validate(manifest, schema)
    if errors:
        raise ManifestValidationError(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=f"Path to instances.yaml (default: {DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to SCHEMA.json (default: {DEFAULT_SCHEMA_PATH})",
    )
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="Skip the JSON Schema structural pass even if jsonschema is installed.",
    )
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
    except FileNotFoundError:
        print(f"error: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    except yaml.YAMLError as exc:
        print(f"error: manifest is not valid YAML: {exc}", file=sys.stderr)
        return 2

    schema = None
    if not args.no_schema:
        try:
            schema = load_schema(args.schema)
        except FileNotFoundError:
            print(f"error: schema not found: {args.schema}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(f"error: schema is not valid JSON: {exc}", file=sys.stderr)
            return 2
        if jsonschema is None:
            print(
                "warning: jsonschema is not installed; skipping the schema "
                "structural pass (semantic checks still run)",
                file=sys.stderr,
            )

    errors = validate(manifest, schema)
    if errors:
        print(f"FAIL: {args.manifest} — {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK: {args.manifest} is a valid F1 fixture manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

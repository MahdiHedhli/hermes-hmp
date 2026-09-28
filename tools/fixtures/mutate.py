#!/usr/bin/env python3
"""T062: the F1 fixture mutations -- append, in-place compaction, session replaced.

Applies one of `fixtures/f1/instances.yaml`'s named `mutations` (`append`, `rewrite`,
`new_session`) to one instance of an already-built fixture (`build_fixture.py`, T060), offline,
through the same `SessionDB`/`SessionStore` APIs the builder uses (contracts/fixture-format.md
rule 3), via `fixture_seed.py`. These mutations exist to drive T030's read-path integration tests
(append -> rows, in-place compaction -> `history_rewritten`, session replaced ->
`session_replaced`), not to be interesting on their own.

Requires a fixture already built with `build_fixture.py --build <label> --out <dir>` at the SAME
`--out`: this reads that run's `fixture_meta.json` (written by `build_fixture.py`) for the
build/venv to run under and the user/chat/session ids to mutate, so this script takes neither
`--build` nor `--builds-dir` itself (`server/tests/integration/test_reads_fixture.py`'s
interface).

Usage:
    python3 tools/fixtures/mutate.py --out ... --instance A --mutation append
    python3 tools/fixtures/mutate.py --out ... --instance A --mutation rewrite
    python3 tools/fixtures/mutate.py --out ... --instance A --mutation new_session
    python3 tools/fixtures/mutate.py --out ... --instance A --mutation all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import _fixture_common as fc
from build_fixture import (
    _write_messages_file,
    build_info_from_meta,
    fixture_meta_path,
    read_fixture_meta,
)

THIS_DIR = Path(__file__).resolve().parent
FIXTURE_SEED = THIS_DIR / "fixture_seed.py"

MUTATION_KINDS = ("append", "rewrite", "new_session")


def _load_fixture_meta(out_dir: Path) -> dict[str, Any]:
    path = fixture_meta_path(out_dir)
    if not path.exists():
        raise fc.FixtureSafetyError(
            f"{path} does not exist -- run build_fixture.py --build <label> "
            f"--out {out_dir} first (T060)"
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _find_targets(
    manifest: dict[str, Any], instance_key: str, conv_key: str
) -> list[tuple[str, str]]:
    """Every (instance_key, profile_name) pair, within `instance_key` only, whose `conversation`
    is `conv_key`."""
    targets: list[tuple[str, str]] = []
    for instance in manifest["instances"]:
        if instance["key"] != instance_key:
            continue
        for profile in instance["profiles"]:
            if profile.get("conversation") == conv_key:
                targets.append((instance["key"], profile["name"]))
    return targets


def _profile_meta(meta: dict[str, Any], instance_key: str, profile_name: str) -> dict[str, Any]:
    instances = {i["key"]: i for i in meta.get("instances", [])}
    if instance_key not in instances:
        raise fc.FixtureSafetyError(f"fixture_meta.json has no instance {instance_key!r}")
    profiles = {p["name"]: p for p in instances[instance_key].get("profiles", [])}
    if profile_name not in profiles:
        raise fc.FixtureSafetyError(
            f"fixture_meta.json has no profile {profile_name!r} on instance {instance_key!r}"
        )
    profile = profiles[profile_name]
    if "session_id" not in profile:
        raise fc.FixtureSafetyError(
            f"profile {profile_name!r} on instance {instance_key!r} has no seeded session "
            "(its manifest conversation is null) -- nothing to mutate"
        )
    return profile


def _update_session_id(
    out_dir: Path, instance_key: str, profile_name: str, session_id: str
) -> None:
    path = fixture_meta_path(out_dir)
    with path.open(encoding="utf-8") as fh:
        meta = json.load(fh)
    for inst in meta.get("instances", []):
        if inst["key"] != instance_key:
            continue
        for profile in inst.get("profiles", []):
            if profile["name"] == profile_name:
                profile["session_id"] = session_id
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def apply_append(
    build: fc.BuildInfo, paths: fc.InstancePaths, manifest: dict[str, Any],
    instance_key: str, profile_name: str, profile_meta: dict[str, Any],
    spec: dict[str, Any], tmp_dir: Path,
) -> dict[str, Any]:
    conv_key = spec["conversation"]
    add = spec["add"]
    label_prefix = manifest["label_prefix"]
    conv_spec = manifest["conversations"][conv_key]
    roles = conv_spec.get("generate", {}).get("roles", ["user", "assistant"])
    base_count = conv_spec.get("generate", {}).get("count", 0)
    messages = [
        {
            "role": roles[i % len(roles)],
            "text": f"{label_prefix} appended message {i} ({roles[i % len(roles)]})",
        }
        for i in range(base_count, base_count + add)
    ]
    messages_file = _write_messages_file(
        messages, tmp_dir, f"append-{instance_key}-{profile_name}"
    )
    result = fc.run_seed_script(
        build, FIXTURE_SEED, "append",
        "--home", str(paths.home),
        "--profile", profile_name,
        "--session-id", profile_meta["session_id"],
        "--messages-file", str(messages_file),
    )
    return json.loads(result.stdout)


def apply_rewrite(
    build: fc.BuildInfo, paths: fc.InstancePaths, manifest: dict[str, Any],
    instance_key: str, profile_name: str, profile_meta: dict[str, Any],
    spec: dict[str, Any], tmp_dir: Path,
) -> dict[str, Any]:
    """`kind: in_place_compaction` (RO-8): archive the active rows and insert a fresh, shorter set
    under the SAME session id -- new row ids, same session."""
    conv_key = spec["conversation"]
    label_prefix = manifest["label_prefix"]
    compacted = [
        {"role": "assistant", "text": f"{label_prefix} in-place compaction summary for {conv_key}"},
    ]
    messages_file = _write_messages_file(
        compacted, tmp_dir, f"rewrite-{instance_key}-{profile_name}"
    )
    result = fc.run_seed_script(
        build, FIXTURE_SEED, "compact",
        "--home", str(paths.home),
        "--profile", profile_name,
        "--session-id", profile_meta["session_id"],
        "--messages-file", str(messages_file),
    )
    return json.loads(result.stdout)


def apply_new_session(
    build: fc.BuildInfo, paths: fc.InstancePaths, manifest: dict[str, Any],
    instance_key: str, profile_name: str, profile_meta: dict[str, Any],
    spec: dict[str, Any], tmp_dir: Path,
) -> dict[str, Any]:
    """`kind: session_replaced` (RO-6): a fresh session id for the same routing key, `/new`-
    equivalent. The old session id is left ended, never deleted."""
    del manifest, spec, tmp_dir  # unused -- routing key alone determines the new session
    result = fc.run_seed_script(
        build, FIXTURE_SEED, "new-session",
        "--home", str(paths.home),
        "--profile", profile_name,
        "--user-id", profile_meta["user_id"],
        "--chat-id", profile_meta["chat_id"],
    )
    return json.loads(result.stdout)


_APPLIERS = {
    "append": apply_append,
    "rewrite": apply_rewrite,
    "new_session": apply_new_session,
}


def run_mutation(
    build: fc.BuildInfo,
    out_dir: Path,
    manifest: dict[str, Any],
    instance_key: str,
    mutation_name: str,
) -> list[dict[str, Any]]:
    spec = manifest.get("mutations", {}).get(mutation_name)
    if spec is None:
        raise fc.FixtureSafetyError(f"manifest has no mutation named {mutation_name!r}")
    meta = _load_fixture_meta(out_dir)
    targets = _find_targets(manifest, instance_key, spec["conversation"])
    if not targets:
        raise fc.FixtureSafetyError(
            f"no profile on instance {instance_key!r} references conversation "
            f"{spec['conversation']!r} (mutation {mutation_name!r})"
        )
    results = []
    for target_instance_key, profile_name in targets:
        paths = fc.instance_paths(out_dir, target_instance_key)
        fc.assert_instance_paths_safe(paths)
        profile_meta = _profile_meta(meta, target_instance_key, profile_name)
        tmp_dir = paths.out_dir / "tmp" / target_instance_key
        outcome = _APPLIERS[mutation_name](
            build, paths, manifest, target_instance_key, profile_name, profile_meta, spec, tmp_dir
        )
        if "session_id" in outcome and outcome["session_id"] != profile_meta["session_id"]:
            _update_session_id(out_dir, target_instance_key, profile_name, outcome["session_id"])
        results.append(
            {
                "instance": target_instance_key,
                "profile": profile_name,
                "mutation": mutation_name,
                **outcome,
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", required=True, type=Path, help="the --out a prior build_fixture.py run used"
    )
    parser.add_argument("--instance", required=True, help="fixture instance key (e.g. A) to mutate")
    parser.add_argument("--manifest", type=Path, default=fc.DEFAULT_MANIFEST_PATH)
    parser.add_argument("--schema", type=Path, default=fc.DEFAULT_SCHEMA_PATH)
    parser.add_argument(
        "--mutation", required=True, choices=(*MUTATION_KINDS, "all"),
        help="which named mutation from the manifest's `mutations:` block to apply",
    )
    args = parser.parse_args(argv)

    fc.assert_outside_real_home(args.out, "--out")
    manifest = fc.load_and_validate_manifest(args.manifest, args.schema)
    meta = read_fixture_meta(args.out)
    if not meta:
        raise fc.FixtureSafetyError(
            f"{fixture_meta_path(args.out)} does not exist -- run build_fixture.py --build <label> "
            f"--out {args.out} first (T060)"
        )
    build = build_info_from_meta(meta)
    fc.ensure_runtime_deps(build)

    names = list(MUTATION_KINDS) if args.mutation == "all" else [args.mutation]
    all_results: list[dict[str, Any]] = []
    for name in names:
        all_results.extend(run_mutation(build, args.out, manifest, args.instance, name))

    print(json.dumps({"ok": True, "build": build.label, "results": all_results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Log scanner (T033; SR-007, CS-22): flags anything SR-007 says a gateway or phone log must
never carry, and anything CS-22's fixture/device-under-test markers say should never have reached
a log at all.

This is a narrow, precise scanner over *log output*, not `scan_private.py`'s general-purpose scan
of tracked source (T002) or `scan_artifact.py`'s scan of a built IPA/APK/AAB (T086): it is meant to
run over the gateway's log (the plugin logger via `logging_policy.log_event`, the aiohttp access
log, bridge exception text) and the app's own log output (`adb logcat` filtered to the app
process; the iOS unified log filtered to the app's subsystem), captured as plain text files.

Deliberately standalone (no `hmp_plugin` import): a log scanner must work against evidence
produced by any build, on any machine, independent of which worktree's `hmp-plugin` happens to be
pip-installed in the venv running it. The wire literals it matches (the `hmp1:` prefix, the
fixture-manifest prefixes) are re-declared here with a citation to their source of truth, the same
way `tools/vectors/gen_hmp1_vectors.py` (T015) independently re-derives the wire format instead of
importing the codec it is checking.

Signals (SR-007 "default logs ... exclude": offer secrets and QR payloads; pairing nonces; tokens,
signatures and keys; authorization headers; SAS values; Hermes pairing codes; message text; device
names, operator labels and peer addresses — SEC-4 permits only 8-character id prefixes and outcome
codes):

  TOKEN_B64U      - a token/nonce/secret-shaped run of unpadded base64url characters, at or above
                    the shortest real secret length on the wire (`nd`/`ni`/`nonce`/`oid`/
                    `pairing_id`: 16 raw bytes -> 22 b64u characters; TR-11). An 8-character
                    `logging_policy.id_prefix()` output is well under this and never matches.
  SAS_GROUP       - a `device_sas`-shaped value: four groups of 5 base32 letters/digits, dashed
                    (HMP v1 §2: `upper(device_fp[0:20])` grouped `XXXXX-XXXXX-XXXXX-XXXXX`).
  HMP1_PAYLOAD    - the QR offer payload prefix (`hmp1:`, HMP v1 §1 V-1).
  BEARER          - an `Authorization: Bearer ...`-shaped value.
  HERMES_PAIRING_CODE - Hermes's own operator-approval code shape: 8 characters from its
                    Crockford-like alphabet (`gateway/pairing.py` `ALPHABET`/`CODE_LENGTH`, stable
                    across both extracted builds, research R10) — the code PR6-2 says must never
                    be relayed to the device at all, so any occurrence in a log is a leak. Matched
                    case-insensitively (a real code may be rendered or typed in lowercase before
                    `gateway/pairing.py`'s own `.upper()` normalization), but only when the
                    8-character candidate also contains at least one of the alphabet's 8 digits
                    (`23456789`): a real code has one with ~90% probability (8 independent draws
                    from a 32-character alphabet), while an ordinary English word never does. This
                    is what tells a real code apart from a coincidental same-length dictionary
                    word ("embedded", "database" — a real false-positive regression the plain
                    case-insensitive rule produced; see `find_hermes_pairing_code`). The
                    remaining ~10% of codes that happen to be all letters are an accepted blind
                    spot for this generic, log-shape-only rule; `test_pairing_code_never_relayed`
                    additionally checks the *specific* code a test actually issued, by its stored
                    hash, which does not depend on this heuristic at all.
  FIXTURE_LABEL   - the fixture text label (`fixtures/f1/instances.yaml` `label_prefix`), which
                    must never reach a log line if only ids and outcomes are being logged (SEC-4).
  FIXTURE_PREFIX  - a `f1-fixture-device-`/`f1-fixture-label-` scannable prefix (CS-22): finding
                    one at all proves a fixture-originated device name or operator label reached
                    the log, which SR-007 forbids logging regardless of source.
  TAILNET         - a peer IP literal, reusing `scan_private.py`'s own patterns (SEC-11): a
                    Tailscale CGNAT address/CIDR (100\x2e64.0.0/10), the ULA range
                    (fd7a:115c:a1e0::/48) or a `*.ts.net` MagicDNS hostname, excluding the two
                    ranges written out exactly as CIDR/wildcard contract syntax the way
                    docs/architecture/contracts/HMP_V1.md documents them.
  HOME_IP         - a private/home-LAN IPv4 literal (RFC 1918: 10.0.0.0/8, 172.16.0.0/12,
                    192.168.0.0/16) — a peer address SR-007 forbids just as much as a tailnet one.

Usage:
    python3 tools/ci/scan_logs.py LOGFILE [LOGFILE ...]
    some-command | python3 tools/ci/scan_logs.py -          # read stdin
    python3 tools/ci/scan_logs.py                           # no args: scan every captured log
                                                              # artifact under DEFAULT_SCAN_DIR
                                                              # (empty or absent -> clean; this is
                                                              # what tools/ci/check_all.sh's
                                                              # generic no-arg checker loop runs,
                                                              # the same way it runs check_icon.py
                                                              # or check_network_paths.py)

No-argument mode only ever looks at *captured log artifacts* under `DEFAULT_SCAN_DIR`: files whose
extension is in `LOG_ARTIFACT_EXTENSIONS` (`.log`, `.jsonl`, `.txt` — logcat and xcresult text
exports land as one of these). It never scans `.md`: an evidence write-up is prose, not a log
capture, and its own quoted test names, code fragments and (legitimately public) key/signature
material are exactly the kind of token-shaped text `TOKEN_B64U` exists to catch in a *log*, so
scanning Markdown produces false positives, not findings. Explicit file arguments are scanned
regardless of extension: an operator who names a file on the command line is choosing to scan it.

A finding is suppressed only when it matches an entry of `tools/ci/scan_logs_baseline.txt` scoped
to that finding's *rule*, at *exactly* the count of findings that rule produced for that path
(SEC-11): `<path-glob>  <RULE>  <count>  # <reason>`, one line per reviewed (path, rule) pair. A
baseline entry never suppresses any rule but the one it names, and never suppresses a count other
than the one pinned — a later re-capture of the same path that produces a different rule, or a
different number of hits for the same rule, is reported as a real finding (plus a loud "baseline
count mismatch" line) rather than silently hidden behind an unrelated, already-reviewed entry.
Path globs and rule names only, never values, each with a one-line reason. It exists for
reviewed, genuinely public material that is only token-*shaped* (e.g. a device public key or
signature quoted in an evidence report) — it must never be used to hide an actual secret, and the
suppressed count is always printed so nothing is silent.

Exit code: 0 if every given (or defaulted) log is clean, 1 if any finding (printed to stdout,
values redacted).
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

# Where T081/T082/T083/T084 evidence logs land (their own docstrings). Scanned by default when
# this tool is run with no arguments, e.g. from tools/ci/check_all.sh's generic no-arg checker
# loop (the same way it runs check_icon.py or check_network_paths.py).
DEFAULT_SCAN_DIR = Path("docs") / "research" / "f1-acceptance"

# No-argument mode only ever looks at these extensions: real captured log artifacts (a plugin log,
# a JSON-lines capture, a logcat or xcresult text export saved as plain text), never a `.md`
# evidence write-up (see module docstring).
LOG_ARTIFACT_EXTENSIONS = frozenset({".log", ".jsonl", ".txt"})

# Test-only escape hatch: overrides where no-argument mode looks for DEFAULT_SCAN_DIR, so the
# tools/ci/tests suite can point a no-arg run at an empty temporary directory instead of this
# worktree's own (possibly populated) docs/research/f1-acceptance/. Never set outside a test.
_REPO_ROOT_OVERRIDE_ENV = "HMP_SCAN_LOGS_REPO_ROOT"

# Re-declared, not imported (see module docstring): HMP v1 §1 V-1.
QR_PREFIX = "hmp1:"

# fixtures/f1/instances.yaml defaults (contracts/fixture-format.md); read from the manifest below
# when it is available and PyYAML is installed, so a manifest edit does not silently desync this
# scanner.
DEFAULT_FIXTURE_LABEL_PREFIX = "[F1 SYNTHETIC]"
DEFAULT_FIXTURE_DEVICE_PREFIX = "f1-fixture-device-"
DEFAULT_FIXTURE_OPERATOR_LABEL_PREFIX = "f1-fixture-label-"

# gateway/pairing.py `ALPHABET`/`CODE_LENGTH`, confirmed identical in both extracted builds
# (research R10: stock-base `04fa849e70`, experimental `7e8c8f07a1`) — Crockford-base32-like,
# excluding I, O, 0 and 1.
HERMES_PAIRING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
HERMES_PAIRING_CODE_LENGTH = 8

# TR-11: the shortest real wire secret (`nd`, `ni`, `nonce`, `oid`, `pairing_id`) is 16 raw bytes,
# 22 unpadded base64url characters. `logging_policy.id_prefix()` never emits more than 8.
TOKEN_B64U_MIN_LEN = 20

# SEC-11: also catch standard base64 (`+`, `/`, `=` padding), not only base64url's `-`/`_`.
# Two tries were rejected before this one, each for the same reason (a real, seeded false
# positive against this server's own `hmp_plugin` log output, not a theoretical concern):
#   1. Adding `=` as an ordinary body character joined unrelated adjacent words across every
#      `key=value` log line (`logging_policy.py`'s own `event=... outcome=...` format), turning
#      "outcome=awaiting_operator" into one 20+-character false-positive match.
#   2. Adding bare `/` as an ordinary body character joined unrelated adjacent URL path segments
#      in the access logger's own `POST /hmp/v1/pair/request ...` lines, turning
#      "/hmp/v1/pair/request" (four short segments) into one 20-character false-positive match.
# Real base64 padding (`=`) is always 0-2 characters at the very END of an encoded string, never
# in the middle -- and a standard-base64 string long enough to matter is a much stronger signal
# than a bare `/`, which any URL path also has in abundance. So `/`/`+` are only treated as
# body characters in a SEPARATE branch that also requires the match to end in real `=` padding
# (never true of a URL path or an ordinary word in these logs); a base64url-shaped run with
# neither `+`, `/` nor `=` still matches the plain, unchanged first branch at the same
# TOKEN_B64U_MIN_LEN this scanner has always used. A standard-base64 secret that happens to need
# no padding at all (its length already a multiple of 4) falls outside both branches, same as
# before this fix -- accepted here in exchange for not flooding every ordinary access-log line
# with false positives; TR-11's actual wire secrets are unpadded base64url in the first place.
_B64URL_BODY_CHARS = "A-Za-z0-9_-"
_B64_STD_BODY_CHARS = "A-Za-z0-9+/"
_B64_STD_MIN_LEN = 8
TOKEN_B64U_RE = re.compile(
    rf"(?<![{_B64URL_BODY_CHARS}])[{_B64URL_BODY_CHARS}]{{{TOKEN_B64U_MIN_LEN},}}"
    rf"(?![{_B64URL_BODY_CHARS}])"
    rf"|(?<![{_B64_STD_BODY_CHARS}=])[{_B64_STD_BODY_CHARS}]{{{_B64_STD_MIN_LEN},}}={{1,2}}"
    rf"(?![{_B64_STD_BODY_CHARS}=])"
)
SAS_GROUP_RE = re.compile(r"\b[A-Z2-7]{5}-[A-Z2-7]{5}-[A-Z2-7]{5}-[A-Z2-7]{5}\b")
BEARER_RE = re.compile(r"(?i)\bBearer\s+\S+")
# SEC-11: case-insensitive. `HERMES_PAIRING_CODE_ALPHABET` already excludes the ambiguous
# characters (I, O, 0, 1) gateway/pairing.py's own alphabet excludes, so IGNORECASE only ever
# additionally matches lowercase forms of the same 33 characters -- never a new, wider alphabet.
#
# Regression found after SEC-11 shipped: case-insensitivity also matches ordinary English words
# that happen to be exactly 8 letters, all drawn from the alphabet's 24 letters (it excludes only
# I and O) -- captured Hermes SQLite/watchdog log lines flagged "embedded", "database", "escalate"
# and "tampered" as pairing codes (see the now-removed HERMES_PAIRING_CODE entries this fix drops
# from scan_logs_baseline.txt). The regex itself is unchanged; `find_hermes_pairing_code` below
# additionally requires a digit in the match (see its docstring and the module docstring's
# HERMES_PAIRING_CODE entry) rather than narrowing the character class or reverting IGNORECASE,
# so a real lowercase-rendered code is still caught.
HERMES_PAIRING_CODE_RE = re.compile(
    rf"\b[{HERMES_PAIRING_CODE_ALPHABET}]{{{HERMES_PAIRING_CODE_LENGTH}}}\b",
    re.IGNORECASE,
)

# The 8 digit characters of HERMES_PAIRING_CODE_ALPHABET (2-9; the alphabet excludes 0/1 the same
# way it excludes I/O). No dictionary word contains one, so requiring at least one in an
# 8-character candidate is what tells a real code apart from a coincidental English word.
_HERMES_PAIRING_CODE_DIGITS = frozenset("23456789")

# SEC-11: peer IP literals, which SR-007 forbids in a log the same way it forbids a device name
# or operator label. `find_tailnet_and_home_ip` below reuses scan_private.py's own CGNAT/ULA/
# ts.net patterns for the tailnet/CGNAT case (loaded from that sibling file by path, exactly the
# way this scanner's own test loads *this* file as a module, rather than a plain `import
# scan_private` — that would depend on tools/ci/ already being on sys.path, which is true for a
# bare CLI invocation but not guaranteed for every way this module gets loaded), plus a new
# RFC 1918 "home IP" pattern scan_private.py has no equivalent of yet.
HOME_LAN_RE = re.compile(
    r"\b(?:10(?:\.[0-9]{1,3}){3}"
    r"|172\.(?:1[6-9]|2[0-9]|3[01])(?:\.[0-9]{1,3}){2}"
    r"|192\.168(?:\.[0-9]{1,3}){2})(?:/[0-9]{1,2})?\b"
)


def _load_scan_private_tailnet_patterns() -> (
    tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]
):
    path = Path(__file__).resolve().parent / "scan_private.py"
    spec = importlib.util.spec_from_file_location("_scan_logs_scan_private", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CGNAT_RE, module.TS_ULA_RE, module.TS_NET_RE


def load_fixture_prefixes(manifest_path: Path) -> tuple[str, str, str]:
    """`(label_prefix, device_name_prefix, operator_label_prefix)` from the fixture manifest, or
    the contract defaults if the manifest or PyYAML is unavailable (never a hard failure: this
    scanner must still run over a log captured with no repo checkout nearby)."""
    try:
        import yaml
    except ImportError:
        return (
            DEFAULT_FIXTURE_LABEL_PREFIX,
            DEFAULT_FIXTURE_DEVICE_PREFIX,
            DEFAULT_FIXTURE_OPERATOR_LABEL_PREFIX,
        )
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except OSError:
        return (
            DEFAULT_FIXTURE_LABEL_PREFIX,
            DEFAULT_FIXTURE_DEVICE_PREFIX,
            DEFAULT_FIXTURE_OPERATOR_LABEL_PREFIX,
        )
    if not isinstance(data, dict):
        return (
            DEFAULT_FIXTURE_LABEL_PREFIX,
            DEFAULT_FIXTURE_DEVICE_PREFIX,
            DEFAULT_FIXTURE_OPERATOR_LABEL_PREFIX,
        )
    return (
        str(data.get("label_prefix", DEFAULT_FIXTURE_LABEL_PREFIX)),
        str(data.get("device_name_prefix", DEFAULT_FIXTURE_DEVICE_PREFIX)),
        str(data.get("operator_label_prefix", DEFAULT_FIXTURE_OPERATOR_LABEL_PREFIX)),
    )


def find_token_b64u(line: str) -> list[str]:
    return [m.group(0) for m in TOKEN_B64U_RE.finditer(line)]


def find_sas_group(line: str) -> list[str]:
    return [m.group(0) for m in SAS_GROUP_RE.finditer(line)]


def find_hmp1_payload(line: str) -> list[str]:
    out = []
    start = 0
    while True:
        idx = line.find(QR_PREFIX, start)
        if idx == -1:
            break
        out.append(line[idx : idx + 40])  # enough to be recognizable in the finding, still short
        start = idx + len(QR_PREFIX)
    return out


def find_bearer(line: str) -> list[str]:
    return [m.group(0) for m in BEARER_RE.finditer(line)]


def find_hermes_pairing_code(line: str) -> list[str]:
    """`HERMES_PAIRING_CODE_RE` matches, filtered to require at least one digit (SEC-11
    regression fix): a real code drawn from the 32-character alphabet (24 letters, 8 digits) has
    one with ~90% probability, while an ordinary English word of the same length never does. See
    the module docstring's HERMES_PAIRING_CODE entry and the comment above `HERMES_PAIRING_CODE_RE`
    for the false positives ("embedded", "database", ...) this removes, and the accepted ~10%
    blind spot (a genuinely all-letter code) it trades for that."""
    return [
        m.group(0)
        for m in HERMES_PAIRING_CODE_RE.finditer(line)
        if any(ch in _HERMES_PAIRING_CODE_DIGITS for ch in m.group(0))
    ]


def _make_tailnet_finder() -> Callable[[str], list[str]]:
    cgnat_re, ts_ula_re, ts_net_re = _load_scan_private_tailnet_patterns()

    def finder(line: str) -> list[str]:
        out = []
        for m in cgnat_re.finditer(line):
            if m.group(0) != "100\x2e64.0.0/10":  # the contract-syntax CIDR itself, not a leak
                out.append(m.group(0))
        for m in ts_ula_re.finditer(line):
            if m.group(0) != "fd7a:115c:a1e0::/48":
                out.append(m.group(0))
        for m in ts_net_re.finditer(line):
            if m.group(1) != "*":
                out.append(m.group(0))
        return out

    return finder


def find_home_lan_ip(line: str) -> list[str]:
    return [m.group(0) for m in HOME_LAN_RE.finditer(line)]


def _make_literal_finder(literal: str) -> Callable[[str], list[str]]:
    def finder(line: str) -> list[str]:
        out = []
        start = 0
        while True:
            idx = line.find(literal, start)
            if idx == -1:
                break
            out.append(literal)
            start = idx + len(literal)
        return out

    return finder


BASELINE_FILENAME = "scan_logs_baseline.txt"

# SEC-11: a baseline entry is now scoped to one (path glob, rule) pair, with a pinned expected
# count, not to a whole file across every rule. The old format (`<glob>  # <reason>`) suppressed
# EVERY rule's hits in a matched file, so a later re-capture of the same path that introduced a
# new, different kind of leak (a different rule) — or simply more hits of the same rule than were
# actually reviewed — was silently hidden behind whatever reason was written down for a completely
# different, earlier finding. Pinning `(glob, rule, count)` together means a re-capture is only
# ever suppressed when it reproduces exactly the reviewed shape; anything else (a new rule, or a
# different count for the same rule) surfaces as a real finding demanding the baseline be looked
# at and updated on purpose (see the count-mismatch handling in `main`).
_BASELINE_LINE_RE = re.compile(r"^(\S+)\s+(\S+)\s+(\d+)\s+#\s*(.+)$")


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a gitignore-like glob (only `**` and `*` are used) to an anchored regex. Mirrors
    `scan_private.py`'s `_glob_to_regex` (same format, deliberately not shared: this scanner is
    standalone by design, see the module docstring)."""
    parts = []
    for segment in re.split(r"(\*\*|\*)", glob):
        if segment == "**":
            parts.append(".*")
        elif segment == "*":
            parts.append("[^/]*")
        elif segment:
            parts.append(re.escape(segment))
    return re.compile("^" + "".join(parts) + "$")


class BaselineEntry:
    """One `(path glob, rule, expected count, reason)` line of `scan_logs_baseline.txt`."""

    __slots__ = ("count", "glob", "reason", "regex", "rule")

    def __init__(
        self, regex: re.Pattern[str], glob: str, rule: str, count: int, reason: str
    ) -> None:
        self.regex = regex
        self.glob = glob
        self.rule = rule
        self.count = count
        self.reason = reason


def load_baseline(script_dir: Path) -> list[BaselineEntry]:
    """Return the entries of tools/ci/scan_logs_baseline.txt. Never a hard failure: an absent
    baseline file just means nothing is suppressed."""
    path = script_dir / BASELINE_FILENAME
    if not path.is_file():
        return []
    entries: list[BaselineEntry] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = _BASELINE_LINE_RE.match(line)
        if not m:
            # Malformed baseline entries are a config bug worth surfacing, not silently
            # ignoring — but do not let them crash the scan.
            print(f"scan_logs: ignoring malformed baseline line: {raw_line!r}", file=sys.stderr)
            continue
        glob, rule, count_str, reason = m.groups()
        entries.append(BaselineEntry(_glob_to_regex(glob), glob, rule, int(count_str), reason))
    return entries


def build_rules(manifest_path: Path) -> list[tuple[str, Callable[[str], list[str]]]]:
    label_prefix, device_prefix, operator_prefix = load_fixture_prefixes(manifest_path)
    return [
        ("TOKEN_B64U", find_token_b64u),
        ("SAS_GROUP", find_sas_group),
        ("HMP1_PAYLOAD", find_hmp1_payload),
        ("BEARER", find_bearer),
        ("HERMES_PAIRING_CODE", find_hermes_pairing_code),
        ("TAILNET", _make_tailnet_finder()),
        ("HOME_IP", find_home_lan_ip),
        ("FIXTURE_LABEL", _make_literal_finder(label_prefix)),
        ("FIXTURE_DEVICE_PREFIX", _make_literal_finder(device_prefix)),
        ("FIXTURE_OPERATOR_LABEL_PREFIX", _make_literal_finder(operator_prefix)),
    ]


def redact(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}…{value[-4:]}"


def scan_text(
    text: str, rules: list[tuple[str, Callable[[str], list[str]]]]
) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule_name, finder in rules:
            for match in finder(line):
                findings.append((lineno, rule_name, match))
    return findings


def _default_targets(repo_root: Path) -> list[Path]:
    """Every captured log artifact (`LOG_ARTIFACT_EXTENSIONS`) already under `DEFAULT_SCAN_DIR`,
    for a no-argument run. Empty (not an error) when nothing has been captured there yet —
    T081/T082/T083/T084 are what populate it. Never `.md`: an evidence write-up is prose, not a
    captured log (module docstring)."""
    scan_dir = repo_root / DEFAULT_SCAN_DIR
    if not scan_dir.is_dir():
        return []
    return sorted(
        p
        for p in scan_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in LOG_ARTIFACT_EXTENSIONS
    )


def _match_key(path: Path, repo_root: Path) -> str:
    """The path a baseline glob matches against: repo-relative and posix-separated when the path
    is inside `repo_root`, else its own posix form (mirrors `scan_private.py`)."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def apply_baseline(
    all_findings: list[tuple[str, str, int, str, str]], baseline: list[BaselineEntry]
) -> tuple[
    list[tuple[str, int, str, str]],
    dict[tuple[str, str], int],
    list[tuple[str, str, str, int, int]],
]:
    """Splits `all_findings` (`label, match_key, lineno, rule, match`) into:

    - real (unsuppressed) findings, as `(label, lineno, rule, match)`;
    - the suppressed count per `(glob, rule)` baseline entry actually used;
    - count mismatches, as `(match_key, rule, glob, expected_count, actual_count)`, for a
      `(match_key, rule)` group whose size does not equal the one baseline entry that matches it.

    SEC-11: grouped by `(match_key, rule)`, not by `match_key` alone, so a baseline entry can
    only ever suppress the one rule it was reviewed for, and only at the exact count reviewed —
    never every rule in a matched file, and never a different (larger or smaller) count.
    """
    grouped: dict[tuple[str, str], list[tuple[str, int, str]]] = defaultdict(list)
    for label, match_key, lineno, rule, match in all_findings:
        grouped[(match_key, rule)].append((label, lineno, match))

    real_findings: list[tuple[str, int, str, str]] = []
    suppressed_count_by_entry: dict[tuple[str, str], int] = {}
    count_mismatches: list[tuple[str, str, str, int, int]] = []
    for (match_key, rule), items in grouped.items():
        entry = next((e for e in baseline if e.rule == rule and e.regex.match(match_key)), None)
        if entry is None:
            for label, lineno, match in items:
                real_findings.append((label, lineno, rule, match))
            continue
        if len(items) == entry.count:
            key = (entry.glob, entry.rule)
            suppressed_count_by_entry[key] = suppressed_count_by_entry.get(key, 0) + len(items)
        else:
            # The reviewed count no longer matches what this run found: never silently suppress
            # a shape that was not the one actually reviewed (a fresh, larger hit count is
            # exactly the "later re-capture hides a real leak" scenario SEC-11 closes). Every
            # instance surfaces as a real finding, and the mismatch itself is reported loudly so
            # the baseline gets looked at and updated on purpose, not papered over.
            count_mismatches.append((match_key, rule, entry.glob, entry.count, len(items)))
            for label, lineno, match in items:
                real_findings.append((label, lineno, rule, match))
    return real_findings, suppressed_count_by_entry, count_mismatches


def main(argv: list[str]) -> int:
    script_dir = Path(__file__).resolve().parent
    override = os.environ.get(_REPO_ROOT_OVERRIDE_ENV)
    repo_root = Path(override).resolve() if override else script_dir.parent.parent
    manifest_path = repo_root / "fixtures" / "f1" / "instances.yaml"
    rules = build_rules(manifest_path)
    baseline = load_baseline(script_dir)

    if argv:
        sources: list[tuple[str, str, str]] = []  # (label, match_key, text)
        for arg in argv:
            if arg == "-":
                sources.append(("<stdin>", "<stdin>", sys.stdin.read()))
                continue
            path = Path(arg)
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                print(f"scan_logs: cannot read {arg}: {e}", file=sys.stderr)
                return 2
            sources.append((str(path), _match_key(path.resolve(), repo_root), text))
        scanned_count_desc = f"{len(argv)} log(s)"
    else:
        # No arguments: scan whatever log artifacts already exist under DEFAULT_SCAN_DIR, exactly
        # as tools/ci/check_all.sh's generic no-arg checker loop invokes every scanner in tools/ci.
        targets = _default_targets(repo_root)
        if not targets:
            print(f"scan_logs: nothing captured yet under {DEFAULT_SCAN_DIR}/ — nothing to scan.")
            return 0
        sources = [
            (
                str(p.relative_to(repo_root)),
                _match_key(p, repo_root),
                p.read_text(encoding="utf-8", errors="replace"),
            )
            for p in targets
        ]
        scanned_count_desc = f"{len(targets)} log(s) under {DEFAULT_SCAN_DIR}/"

    # (label, match_key, lineno, rule, match)
    all_findings: list[tuple[str, str, int, str, str]] = []
    for label, match_key, text in sources:
        for lineno, rule, match in scan_text(text, rules):
            all_findings.append((label, match_key, lineno, rule, match))

    real_findings, suppressed_count_by_entry, count_mismatches = apply_baseline(
        all_findings, baseline
    )

    total_suppressed = sum(suppressed_count_by_entry.values())
    if total_suppressed:
        reasons = {(e.glob, e.rule): e.reason for e in baseline}
        for (glob, rule), count in suppressed_count_by_entry.items():
            if count:
                print(
                    f"scan_logs: suppressed {count} finding(s) matching baseline glob "
                    f"'{glob}' rule '{rule}' ({reasons[(glob, rule)]}) — see {BASELINE_FILENAME}."
                )
    for match_key, rule, glob, expected, actual in count_mismatches:
        print(
            f"scan_logs: baseline count mismatch for '{match_key}' rule '{rule}' "
            f"(glob '{glob}'): expected {expected}, found {actual} — not suppressed; "
            f"review and update {BASELINE_FILENAME}.",
            file=sys.stderr,
        )

    if not real_findings:
        suffix = f" ({total_suppressed} suppressed by baseline)" if total_suppressed else ""
        print(f"scan_logs: clean ({scanned_count_desc} scanned){suffix}.")
        return 0

    for label, lineno, rule, match in real_findings:
        print(f"{label}:{lineno}: {rule}: {redact(match)}")
    print(
        f"\nscan_logs: {len(real_findings)} finding(s) across {scanned_count_desc}"
        f" ({total_suppressed} additional suppressed by baseline).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

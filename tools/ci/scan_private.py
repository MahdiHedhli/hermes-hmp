#!/usr/bin/env python3
"""Hygiene scanner: flags private values in tracked files (T002, `specs/001-connect-and-browse`).

Per the repository's hard rules (`.claude`'s F1 worker rules) and SECURITY.md, no artifact may
carry: names, emails, tailnet names or IPs, device names, UDIDs or serials, team IDs, home paths
or scratch paths. This scans the repository's git-tracked content — untracked/ignored files
(build output, `.dart_tool/`, venvs, generated Xcode ephemeral config, ...) are out of scope by
construction, since they are never committed in the first place — for four concrete signals:

  EMAIL      - an email address, excluding RFC 2606 reserved placeholder domains
               (example.com/.net/.org, *.example, *.test, *.invalid) used by generated
               boilerplate (e.g. a Flutter plugin's default podspec author).
  TAILNET    - a Tailscale CGNAT address/CIDR (100\x2e64.0.0/10), the ULA range
               (fd7a:115c:a1e0::/48) or a `*.ts.net` MagicDNS hostname, excluding the two
               ranges written out exactly as CIDR/wildcard *contract syntax*
               (`100\x2e64.0.0/10`, `fd7a:115c:a1e0::/48`, `*.ts.net`) the way
               docs/architecture/contracts/HMP_V1.md documents them.
  HOME_PATH  - an absolute `/Users/<real-name>/...` or `/home/<real-name>/...` path, excluding
               already-redacted placeholders (`<user>`, `youruser`, ...).
  TEAM_ID    - a non-empty Xcode `DEVELOPMENT_TEAM` value (an Apple Developer Team ID).

This is intentionally a narrow, precise v1: it is not a general secrets scanner (T033's
`scan_logs.py` and T086's `scan_artifact.py` cover server-log and release-artifact surfaces with
their own, differently-scoped rules).

Usage:
    python3 tools/ci/scan_private.py                  # scan every git-tracked file
    python3 tools/ci/scan_private.py PATH [PATH ...]   # scan only these files/directories
                                                        # (directories are filtered through
                                                        # `git ls-files --others --exclude-standard`
                                                        # when inside the repo, so build output
                                                        # and other gitignored content is still
                                                        # skipped; a path outside the repo, e.g. a
                                                        # test's temp directory, is read directly)

A finding whose path matches a glob in `tools/ci/private_scan_baseline.txt` is suppressed rather
than reported. That file holds path globs only (never values) with a one-line reason each,
currently just the private R0 evidence archive under `docs/research/`, which is sanitized only
on publication (owner ruling, R-1) and never edited in place here. Every other tracked path must
scan clean. The suppressed count is always printed, so nothing is hidden silently.

Exit code: 0 if clean (after baseline suppression), 1 if any unsuppressed finding (printed to
stdout, one per line, value partly redacted).
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".icns", ".bmp",
    ".ttf", ".otf", ".woff", ".woff2",
    ".zip", ".gz", ".tar", ".jar", ".ipa", ".apk", ".aab", ".pdf",
    ".keystore", ".jks", ".p12", ".mobileprovision", ".der", ".class",
    ".so", ".dylib", ".a", ".o", ".dll", ".exe",
}

ALLOWED_EMAIL_DOMAINS = {"example.com", "example.net", "example.org"}
ALLOWED_EMAIL_SUFFIXES = (".example", ".test", ".invalid")

# Final "TLD-like" labels that are actually file extensions, so a filename such as
# `Icon-App-20x20@2x.png` (real Xcode asset-catalog boilerplate) or `1x.json` is not mistaken for
# an email address just because it contains '@' and dot-separated alnum labels.
_FILE_EXT_TLDS = {
    "png", "jpg", "jpeg", "gif", "ico", "icns", "bmp", "svg", "webp",
    "json", "xml", "yaml", "yml", "toml", "ini", "cfg", "log", "csv", "tsv",
    "dart", "py", "js", "ts", "md", "txt", "html", "css",
    "swift", "kt", "java", "m", "h", "c", "cpp", "mm",
    "plist", "strings", "xcconfig", "pbxproj", "storyboard", "xib",
    "class", "so", "dylib", "a", "o", "dll", "exe",
    "ttf", "otf", "woff", "woff2",
    "apk", "aab", "ipa", "jar", "gz", "tar", "zip", "lock", "pdf",
}

PLACEHOLDER_USERS = {
    "user", "username", "youruser", "yourusername", "replaceme", "name", "anyuser",
}

EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?![\w.-])"
)
CGNAT_RE = re.compile(
    r"\b100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.[0-9]{1,3}\.[0-9]{1,3}(?:/[0-9]{1,2})?\b"
)
TS_ULA_RE = re.compile(r"\bfd7a:115c:a1e0:[0-9a-fA-F:]*(?:/[0-9]{1,3})?\b")
TS_NET_RE = re.compile(r"(\*|[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)\.ts\.net\b")
HOME_PATH_RE = re.compile(r"(?<!\w)/(?:Users|home)/([A-Za-z0-9_.-]+)/")
TEAM_ID_RE = re.compile(r'DEVELOPMENT_TEAM\s*=\s*"?([A-Za-z0-9]{10})"?\s*;')


def find_emails(line: str) -> list[str]:
    out = []
    for m in EMAIL_RE.finditer(line):
        domain = m.group(0).split("@", 1)[1].lower()
        if domain in ALLOWED_EMAIL_DOMAINS or domain.endswith(ALLOWED_EMAIL_SUFFIXES):
            continue
        if domain.rsplit(".", 1)[-1] in _FILE_EXT_TLDS:
            continue
        out.append(m.group(0))
    return out


def find_tailnet(line: str) -> list[str]:
    out = []
    for m in CGNAT_RE.finditer(line):
        if m.group(0) != "100\x2e64.0.0/10":
            out.append(m.group(0))
    for m in TS_ULA_RE.finditer(line):
        if m.group(0) != "fd7a:115c:a1e0::/48":
            out.append(m.group(0))
    for m in TS_NET_RE.finditer(line):
        if m.group(1) != "*":
            out.append(m.group(0))
    return out


def find_home_paths(line: str) -> list[str]:
    out = []
    for m in HOME_PATH_RE.finditer(line):
        if m.group(1).lower() in PLACEHOLDER_USERS:
            continue
        out.append(m.group(0))
    return out


def find_team_ids(line: str) -> list[str]:
    return [m.group(0) for m in TEAM_ID_RE.finditer(line)]


RULES: list[tuple[str, Callable[[str], list[str]]]] = [
    ("EMAIL", find_emails),
    ("TAILNET", find_tailnet),
    ("HOME_PATH", find_home_paths),
    ("TEAM_ID", find_team_ids),
]


BASELINE_FILENAME = "private_scan_baseline.txt"
SYNTHETIC_FILENAME = "private_scan_synthetic.txt"


def load_synthetic(script_dir: Path) -> set[str]:
    """Exact synthetic literals from tools/ci/private_scan_synthetic.txt (each with a reason)."""
    path = script_dir / SYNTHETIC_FILENAME
    values: set[str] = set()
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            values.add(line)
    return values
_BASELINE_LINE_RE = re.compile(r"^(\S+)\s+#\s*(.+)$")


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a gitignore-like glob (only `**` and `*` are used) to an anchored regex."""
    parts = []
    # (named `part`/`segment`, not `token`: a ruff/bandit S105 false positive flags a bare
    # `token` variable holding a string literal as a "possible hardcoded password" — this is a
    # glob-syntax fragment, not a credential.)
    for segment in re.split(r"(\*\*|\*)", glob):
        if segment == "**":
            parts.append(".*")
        elif segment == "*":
            parts.append("[^/]*")
        elif segment:
            parts.append(re.escape(segment))
    return re.compile("^" + "".join(parts) + "$")


def load_baseline(script_dir: Path) -> list[tuple[re.Pattern[str], str, str]]:
    """Return [(compiled_regex, glob, reason), ...] from tools/ci/private_scan_baseline.txt."""
    path = script_dir / BASELINE_FILENAME
    if not path.is_file():
        return []
    entries: list[tuple[re.Pattern[str], str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = _BASELINE_LINE_RE.match(line)
        if not m:
            # Malformed baseline entries are a config bug worth surfacing, not silently
            # ignoring — but do not let them crash the scan.
            print(f"scan_private: ignoring malformed baseline line: {raw_line!r}", file=sys.stderr)
            continue
        glob, reason = m.group(1), m.group(2)
        entries.append((_glob_to_regex(glob), glob, reason))
    return entries


def redact(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}…{value[-2:]}"


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=True
    ).stdout


def repo_root(start: Path) -> Path:
    out = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(out)


def resolve_targets(root: Path, args: list[str]) -> list[Path]:
    """Resolve CLI arguments to a concrete file list, always excluding gitignored content."""
    if not args:
        raw = _git(root, "ls-files", "-z")
        return [root / p for p in raw.decode("utf-8", "surrogateescape").split("\0") if p]

    files: list[Path] = []
    for arg in args:
        p = Path(arg).resolve()
        if p.is_file():
            files.append(p)
            continue
        if not p.is_dir():
            continue
        try:
            rel = p.relative_to(root)
            inside_repo = True
        except ValueError:
            inside_repo = False
        if inside_repo:
            raw = _git(
                root, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", str(rel)
            )
            files.extend(root / f for f in raw.decode("utf-8", "surrogateescape").split("\0") if f)
        else:
            # Outside the repository (e.g. a test's temp directory): no gitignore applies.
            files.extend(f for f in p.rglob("*") if f.is_file() and ".git" not in f.parts)
    return files


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    if path.suffix.lower() in BINARY_EXTS:
        return []
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if b"\0" in data[:8000]:
        return []
    text = data.decode("utf-8", errors="replace")
    findings: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule_name, finder in RULES:
            for match in finder(line):
                findings.append((lineno, rule_name, match))
    return findings


def main(argv: list[str]) -> int:
    script_dir = Path(__file__).resolve().parent
    root = repo_root(script_dir)
    targets = resolve_targets(root, argv)
    baseline = load_baseline(script_dir)
    synthetic = load_synthetic(script_dir)

    all_findings: list[tuple[Path, int, str, str]] = []
    synthetic_hits = 0
    for f in targets:
        for lineno, rule, match in scan_file(f):
            if match in synthetic:
                synthetic_hits += 1
                continue
            all_findings.append((f, lineno, rule, match))

    real_findings: list[tuple[Path, int, str, str]] = []
    suppressed_by_glob: dict[str, int] = {glob: 0 for _, glob, _ in baseline}
    for f, lineno, rule, match in all_findings:
        try:
            rel = f.relative_to(root).as_posix()
        except ValueError:
            rel = f.as_posix()
        matched_glob = next((glob for regex, glob, _ in baseline if regex.match(rel)), None)
        if matched_glob is not None:
            suppressed_by_glob[matched_glob] += 1
        else:
            real_findings.append((f, lineno, rule, match))

    total_suppressed = sum(suppressed_by_glob.values())
    if synthetic_hits:
        print(
            f"scan_private: ignored {synthetic_hits} listed synthetic value(s) — "
            f"see {SYNTHETIC_FILENAME}."
        )
    if total_suppressed:
        reasons = {glob: reason for _, glob, reason in baseline}
        for glob, count in suppressed_by_glob.items():
            if count:
                print(
                    f"scan_private: suppressed {count} finding(s) matching baseline glob "
                    f"'{glob}' ({reasons[glob]}) — see {BASELINE_FILENAME}."
                )

    if not real_findings:
        suffix = f" ({total_suppressed} suppressed by baseline)" if total_suppressed else ""
        print(f"scan_private: clean{suffix}.")
        return 0

    for f, lineno, rule, match in real_findings:
        try:
            shown = f.relative_to(root)
        except ValueError:
            shown = f
        print(f"{shown}:{lineno}: {rule}: {redact(match)}")
    print(
        f"\nscan_private: {len(real_findings)} private-value finding(s)"
        f" ({total_suppressed} additional suppressed by baseline).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""T063: the compat matrix runner (research R8, SC-007; specs/001-connect-and-browse/tasks.md).

For each build named in `tools/hermes_builds/builds.yaml` (already extracted by T004's
`tools/hermes_builds/extract.py --out <builds-dir>`), this:

  1. Runs the fixture self-check (T061 `tools/fixtures/selfcheck.py`) against a real gateway on
     that build: every fixture profile's roster/authz state and seeded conversation content, read
     back through the real HMP read path.
  2. Runs "the read suite" -- `server/tests/integration/test_reads_fixture.py`'s build-parametrized
     tests (T030/T062 fixture mutations: append, in-place compaction, session replaced, an
     unresolvable cursor, and the non-`default` conversation-id 404) -- selected to this one build
     via `-k <label>`.
  3. Computes the build's identity exactly as the real gate would (`hmp_plugin.compat`): the
     read-bridge fingerprint over the committed `bridge_files` list, and a git SHA read from
     `.git` when present. An extracted build has no `.git` (T004 archives a tree, never a clone),
     so `git_sha` is always `None` here and the entry is fingerprint-only (CS-19); the archived
     ref's own resolved commit is recorded separately, as `source_sha` -- provenance only, never
     used for matching (R8 step 4, builds.yaml's header comment).
  4. Emits one candidate `BuildEntry` (label, fingerprint, git_sha=None, source_sha) per build
     whose self-check AND read suite both passed. A build that fails either step is reported, not
     silently dropped, and contributes no entry.

Also runs a synthetic minimum-version policy check after a build qualifies: listed,
unlisted and unknown-version builds with the required APIs remain available;
below-floor versions and missing required APIs are refused. This check does not
import native Hermes and does not replace the real self-check or read suite.

This tool never writes `server/hmp_plugin/read_compat_builds.json` itself (T064's job, done with
human judgement, not mechanically here) -- it only emits candidate entries as JSON, for T064 to
read and populate the committed list from.

Usage:
    python3 tools/compat/run_matrix.py --builds-dir <dir> --out <scratch dir> [--builds LABEL,...]
        [--refs-dir <dir>]
    python3 tools/compat/run_matrix.py --builds-dir <dir> --out <scratch dir>
        --candidate-label LABEL --candidate-sha FULL_40_HEX_SHA

`--builds-dir` defaults to `$HMP_HERMES_BUILDS_DIR`. `--out` is a scratch directory for the
self-check and read-suite fixture homes (never the real Hermes home; see `_fixture_common.py`'s
isolation rules, which every subprocess this tool launches also obeys). At most one fixture
gateway runs at a time (host load): builds are processed one at a time, never in parallel, and
`-o addopts=` / no xdist is passed to every pytest invocation.
The candidate form runs the same checks on an already extracted upstream release whose source
tree is `<builds-dir>/<LABEL>/src`; its SHA records provenance without granting runtime support.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    print(
        "run_matrix: PyYAML is required (pip install -r tools/requirements.txt).",
        file=sys.stderr,
    )
    raise

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "server"
TOOLS_DIR = REPO_ROOT / "tools"
BUILDS_YAML = TOOLS_DIR / "hermes_builds" / "builds.yaml"
SELFCHECK = TOOLS_DIR / "fixtures" / "selfcheck.py"
READ_SUITE = SERVER_DIR / "tests" / "integration" / "test_reads_fixture.py"
READ_COMPAT_PATH = SERVER_DIR / "hmp_plugin" / "read_compat_builds.json"

sys.path.insert(0, str(SERVER_DIR))


@dataclass
class BuildSpec:
    label: str
    clone: str
    ref: str
    optional: bool
    git_install: bool = False
    source_sha: str | None = None


def load_build_specs() -> list[BuildSpec]:
    data = yaml.safe_load(BUILDS_YAML.read_text(encoding="utf-8"))
    if data.get("format") != 1:
        raise SystemExit(f"run_matrix: unsupported builds.yaml format {data.get('format')!r}")
    return [
        BuildSpec(
            label=b["label"],
            clone=b["clone"],
            ref=b["ref"],
            optional=bool(b.get("optional", False)),
            git_install=bool(b.get("git_install", False)),
        )
        for b in data["builds"]
    ]


_REFS_DIR_OVERRIDE: Path | None = None  # `--refs-dir`, mirroring extract.py's own override


def _refs_dir() -> Path:
    """Walk up from this file looking for `_refs`, exactly like `extract.py`'s `find_refs_dir`
    (the clones live one level above the repository root, outside version control), unless
    `--refs-dir` overrides it (the same directory given to `extract.py --refs-dir`)."""
    if _REFS_DIR_OVERRIDE is not None:
        return _REFS_DIR_OVERRIDE
    cur = Path(__file__).resolve()
    for _ in range(6):
        candidate = cur / "_refs"
        if candidate.is_dir():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    raise SystemExit("run_matrix: could not find a `_refs` directory by walking up")


def resolve_source_sha(spec: BuildSpec) -> str | None:
    """The archived ref's own resolved commit, read-only, from the `_refs` clone -- the same
    resolution `extract.py` does, never a fetch. `None` for an optional build whose ref does not
    resolve locally (never an error)."""
    if spec.source_sha is not None:
        return spec.source_sha
    clone = _refs_dir() / spec.clone
    if not (clone / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "--verify", "--quiet", f"{spec.ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def run_selfcheck(label: str, out_dir: Path, builds_dir: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [
            sys.executable, str(SELFCHECK),
            "--build", label, "--out", str(out_dir), "--builds-dir", str(builds_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr)


def run_read_suite(label: str, tmp_home: Path) -> tuple[bool, str]:
    env = dict(os.environ)
    env["HMP_HERMES_BUILDS_DIR"] = str(tmp_home)
    env["HMP_COMPAT_CANDIDATE_LABEL"] = label
    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest", str(READ_SUITE),
            "-k", label, "-q", "-o", "addopts=",
        ],
        cwd=str(SERVER_DIR),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr)


def compute_identity(build_dir: Path) -> tuple[str | None, str | None]:
    """(fingerprint, git_sha) exactly as the real gate computes it (`hmp_plugin.compat`)."""
    from hmp_plugin.compat import (
        compute_read_bridge_fingerprint,
        load_read_compat_list,
        resolve_git_head_sha,
    )

    bridge_files = load_read_compat_list(READ_COMPAT_PATH).bridge_files
    src = build_dir / "src"
    fingerprint = compute_read_bridge_fingerprint(src, bridge_files)
    try:
        git_sha = resolve_git_head_sha(src)
    except (OSError, ValueError):
        git_sha = None
    return fingerprint, git_sha


def process_build(spec: BuildSpec, builds_dir: Path, scratch: Path) -> dict[str, Any]:
    build_dir = builds_dir / spec.label
    src = build_dir / "src"
    result: dict[str, Any] = {"label": spec.label, "qualified": False}
    if not src.is_dir():
        result["error"] = f"not extracted at {src}"
        return result

    fingerprint, git_sha = compute_identity(build_dir)
    result["fingerprint"] = fingerprint
    result["git_sha"] = git_sha
    result["source_sha"] = resolve_source_sha(spec)
    if spec.git_install and git_sha is None:
        # builds.yaml `git_install: true`: this entry qualifies a git-checkout install at exactly
        # this commit (CS-19 needs BOTH its git SHA and its fingerprint). The extracted tree has
        # no `.git`, so the SHA is the archived ref's own resolved commit; with no resolvable
        # commit there is no git identity to qualify, and the build is not qualified.
        if result["source_sha"] is None:
            result["error"] = "git_install build: its ref did not resolve to a commit"
            return result
        git_sha = result["source_sha"]
        result["git_sha"] = git_sha
    if fingerprint is None:
        result["error"] = "fingerprint computation failed (a listed bridge_files entry is missing)"
        return result

    selfcheck_out = scratch / spec.label / "selfcheck"
    ok, log = run_selfcheck(spec.label, selfcheck_out, builds_dir)
    result["selfcheck_ok"] = ok
    if not ok:
        result["selfcheck_log_tail"] = "\n".join(log.splitlines()[-40:])
        return result

    ok, log = run_read_suite(spec.label, builds_dir)
    result["read_suite_ok"] = ok
    if not ok:
        result["read_suite_log_tail"] = "\n".join(log.splitlines()[-60:])
        return result

    result["qualified"] = True
    return result


def minimum_version_policy_check(scratch: Path) -> dict[str, Any]:
    """Synthetic policy check only; native self-check/read suites remain mandatory.

    Tested fingerprints describe evidence. They must neither authorize missing
    APIs nor prevent use of an unlisted version above the declared floor.
    """
    from hmp_plugin.compat import CompatGate, Feature, CompatStatus
    from hmp_plugin.hermes_version import HermesVersion, Scheme, VersionSource, UNKNOWN_VERSION

    newer = HermesVersion(Scheme.SEMVER, (0, 99, 0), VersionSource.LITERAL)
    older = HermesVersion(Scheme.SEMVER, (0, 0, 0), VersionSource.LITERAL)
    calls = []

    def evaluate(version, *, listed=False, missing=False):
        def probe(_root, _table):
            calls.append(1)
            return ("synthetic-required-api",) if missing else ()

        return CompatGate(
            root_locator=lambda: scratch,
            version_reader=lambda _root: version,
            probe=probe,
            evidence=lambda _root: {f: "synthetic-tested" if listed else None for f in Feature},
            hook_probe=lambda *_args: True,
        ).evaluate()

    listed = evaluate(newer, listed=True)
    unlisted = evaluate(newer)
    unknown = evaluate(UNKNOWN_VERSION)
    missing = evaluate(newer, listed=True, missing=True)
    calls.clear()
    below = evaluate(older)
    facts = {
        "listed_supported": listed.status is CompatStatus.SUPPORTED,
        "unlisted_supported": unlisted.status is CompatStatus.SUPPORTED,
        "unknown_version_probes_supported": unknown.status is CompatStatus.SUPPORTED,
        "missing_api_refused": missing.status is CompatStatus.UNSUPPORTED,
        "below_floor_refused_without_probe": below.status is CompatStatus.UNSUPPORTED and not calls,
    }
    return {"ok": all(facts.values()), "scope": "synthetic minimum-version policy; no native runtime qualification", **facts}



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builds-dir", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--builds", default=None, help="comma-separated labels (default: all)")
    parser.add_argument("--json-out", type=Path, default=None, help="write the full matrix JSON")
    parser.add_argument(
        "--candidate-label", default=None,
        help="label of an externally extracted Hermes release in --builds-dir",
    )
    parser.add_argument(
        "--candidate-sha", default=None,
        help="full source commit SHA of that candidate (provenance, not a compatibility grant)",
    )
    parser.add_argument(
        "--refs-dir", type=Path, default=None,
        help="override the located _refs dir (the one given to extract.py --refs-dir)",
    )
    args = parser.parse_args(argv)
    if (args.candidate_label is None) != (args.candidate_sha is None):
        parser.error("--candidate-label and --candidate-sha must be supplied together")
    if args.candidate_label is not None:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", args.candidate_label):
            parser.error("--candidate-label must be a simple build label")
        if not re.fullmatch(r"[0-9a-f]{40}", args.candidate_sha):
            parser.error("--candidate-sha must be a full lowercase commit SHA")
    global _REFS_DIR_OVERRIDE
    _REFS_DIR_OVERRIDE = args.refs_dir

    builds_dir = args.builds_dir or Path(os.environ.get("HMP_HERMES_BUILDS_DIR", ""))
    if not builds_dir or not builds_dir.is_dir():
        print("run_matrix: --builds-dir (or $HMP_HERMES_BUILDS_DIR) must be an extracted builds "
              "directory (tools/hermes_builds/extract.py)", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)

    specs = (
        [BuildSpec(args.candidate_label, "", args.candidate_sha, False,
                   source_sha=args.candidate_sha)]
        if args.candidate_label is not None else load_build_specs()
    )
    if args.builds:
        wanted = set(args.builds.split(","))
        specs = [s for s in specs if s.label in wanted]

    results: list[dict[str, Any]] = []
    for spec in specs:
        print(f"run_matrix: {spec.label} ...", file=sys.stderr)
        res = process_build(spec, builds_dir, args.out)
        results.append(res)
        if res["qualified"]:
            status = "QUALIFIED"
        else:
            status = f"NOT QUALIFIED ({res.get('error', 'see log')})"
        print(f"run_matrix: {spec.label}: {status}", file=sys.stderr)

    qualified = [r for r in results if r["qualified"]]
    unsupported: dict[str, Any] | None = None
    if qualified:
        unsupported = minimum_version_policy_check(args.out)
        print(
            f"run_matrix: minimum-version/evidence policy check: {'OK' if unsupported['ok'] else 'FAIL'} "
            f"{unsupported}",
            file=sys.stderr,
        )

    matrix = {
        "format": 1,
        "results": results,
        "candidate_entries": [
            {
                "label": r["label"],
                "fingerprint": r["fingerprint"],
                "git_sha": r["git_sha"],
                "source_sha": r["source_sha"],
            }
            for r in qualified
        ],
        # Retired allowlist check: preserve the old optional field as unevaluated,
        # never report minimum-version support as an old-style fingerprint denial.
        "sc007_unsupported_path_check": None,
        "minimum_version_policy_check": unsupported,
    }
    text = json.dumps(matrix, indent=2) + "\n"
    print(text)
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")

    ok = bool(qualified) and (unsupported is None or unsupported["ok"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""T063: the compat matrix runner (research R8, SC-007; specs/001-connect-and-browse/tasks.md).

With `--target direct-send`, runs the source-containment and real-Hermes approval probes,
then F2/F3 integration with a provisional entry installed ONLY in scratch fixture copies.
Emits candidates only for passing builds, and `--fixture-qualification-out` only when ALL
selected builds pass without skips. The committed lists and live owner configuration are never
changed. Use HMP_DIRECT_SEND_QUALIFICATION=<receipt> for subsequent fixture integration.

In the default read mode, for each build named in `tools/hermes_builds/builds.yaml`
(already extracted by `tools/hermes_builds/extract.py --out <builds-dir>`), this:

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

Also runs the unsupported-path check (SC-007): copies one already-qualified build's tree, alters
one byte of a single `bridge_files` file (changing its fingerprint so no listed entry matches),
and asserts the real `CompatGate` answers `UNSUPPORTED` / `hermes_build_unsupported` (ERR-2a) for
it, with zero bridge calls -- verified by confirming `hmp_plugin.bridge` is never imported for an
unsupported build, checked in a fresh subprocess so nothing from this process's own imports (or
pytest's collection of `tests/integration/test_reads_fixture.py`, which never touches `bridge.py`
either) can leave a false negative.

This tool never writes `server/hmp_plugin/read_compat_builds.json` itself (T064's job, done with
human judgement, not mechanically here) -- it only emits candidate entries as JSON, for T064 to
read and populate the committed list from.

Usage:
    python3 tools/compat/run_matrix.py --builds-dir <dir> --out <scratch dir> [--builds LABEL,...]
        [--refs-dir <dir>]

`--builds-dir` defaults to `$HMP_HERMES_BUILDS_DIR`. `--out` is a scratch directory for the
self-check and read-suite fixture homes (never the real Hermes home; see `_fixture_common.py`'s
isolation rules, which every subprocess this tool launches also obeys). At most one fixture
gateway runs at a time (host load): builds are processed one at a time, never in parallel, and
`-o addopts=` / no xdist is passed to every pytest invocation.
"""

from __future__ import annotations

import argparse
import json
import os
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
DIRECT_COMPAT_PATH = SERVER_DIR / "hmp_plugin" / "direct_send_supported_builds.json"
COMPAT_DIR = TOOLS_DIR / "compat"


sys.path.insert(0, str(SERVER_DIR))


@dataclass
class BuildSpec:
    label: str
    clone: str
    ref: str
    optional: bool
    git_install: bool = False


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


_UNSUPPORTED_PATH_CHECK_SCRIPT = """
import json
import sys

sys.path.insert(0, sys.argv[1])  # server/
sys.path.insert(0, sys.argv[2])  # the mutated Hermes tree

from pathlib import Path

from hmp_plugin import compat as compat_mod

mutated_root = Path(sys.argv[2])
read_compat_path = Path(sys.argv[3])

# Point compat's root locator straight at the mutated tree, in place of the real
# `importlib.util.find_spec(HERMES_ROOT_MARKER_MODULE)` resolution a real Hermes install would
# give -- this subprocess never installs Hermes, it only needs `locate_hermes_root()`'s answer.
compat_mod.locate_hermes_root = lambda: mutated_root

gate = compat_mod.default_gate(read_compat_path=read_compat_path)
result = gate.evaluate()
bridge_imported = "hmp_plugin.bridge" in sys.modules
print(json.dumps({
    "status": result.status.value,
    "why": result.why.value if result.why else None,
    "bridge_imported": bridge_imported,
}))
"""


def unsupported_path_check(builds_dir: Path, qualified_label: str, scratch: Path) -> dict[str, Any]:
    """SC-007: an unlisted build (a qualified build's tree with one `bridge_files` file altered
    by one byte) must be refused `UNSUPPORTED` / `hermes_build_unsupported` (ERR-2a), with zero
    bridge calls. Run in a fresh subprocess so nothing this process (or pytest's own collection)
    already imported can hide a real bridge import."""
    import shutil

    src = builds_dir / qualified_label / "src"
    from hmp_plugin.compat import load_read_compat_list

    bridge_files = load_read_compat_list(READ_COMPAT_PATH).bridge_files
    mutated_root = scratch / "unsupported_mutant"
    if mutated_root.exists():
        shutil.rmtree(mutated_root)
    shutil.copytree(src, mutated_root)
    altered = mutated_root / bridge_files[0]
    altered.write_bytes(altered.read_bytes() + b"\n# SC-007 mutation\n")

    script_path = scratch / "_sc007_check.py"
    script_path.write_text(_UNSUPPORTED_PATH_CHECK_SCRIPT, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable, str(script_path),
            str(SERVER_DIR), str(mutated_root), str(READ_COMPAT_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    status = why = bridge_imported = None
    parsed = None
    for line in proc.stdout.splitlines():
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
    if parsed is not None:
        status = parsed.get("status")
        why = parsed.get("why")
        bridge_imported = parsed.get("bridge_imported")
    ok = status == "unsupported" and why == "hermes_build_unsupported" and bridge_imported is False
    return {
        "ok": ok,
        "status": status,
        "why": why,
        "bridge_imported": bridge_imported,
        "stderr_tail": "\n".join(proc.stderr.splitlines()[-30:]) if not ok else "",
    }


def process_direct_build(spec: BuildSpec, builds_dir: Path, scratch: Path) -> dict[str, Any]:
    """Probe first; provisional qualification only in disposable fixture copies."""
    from hmp_plugin.compat import compute_read_bridge_fingerprint

    src = (builds_dir / spec.label / "src").resolve()
    python = src / ".venv" / "bin" / "python"
    result: dict[str, Any] = {"label": spec.label, "qualified": False, "git_sha": None}
    data = json.loads(DIRECT_COMPAT_PATH.read_text(encoding="utf-8"))
    fingerprint = compute_read_bridge_fingerprint(src, data["bridge_files"])
    result["fingerprint"] = fingerprint
    result["source_sha"] = resolve_source_sha(spec)
    if not fingerprint or not python.is_file():
        result["error"] = "missing fingerprint files or build interpreter"
        return result
    # This mode qualifies archive fixtures only. Never turn it into an owner-local git entry.
    if (src / ".git").exists() or spec.git_install:
        result["error"] = "direct-send matrix requires an extracted fixture build"
        return result
    work = scratch / spec.label
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HMP_HERMES_BUILDS_DIR=str(builds_dir.resolve()))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("HMP_DIRECT_SEND_QUALIFICATION", None)
    commands = {
        "boundary": [str(python), str(COMPAT_DIR / "bridge_files.py"), "--hermes-src", str(src),
                     "--dependencies-attr", "DIRECT_SEND_DEPENDENCIES", "--target",
                     str(DIRECT_COMPAT_PATH), "--check"],
        "behavior": [str(python), str(COMPAT_DIR / "approval_probes.py"), "--hermes-src", str(src)],
    }
    for stage, cmd in commands.items():
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
        (work / f"{stage}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        result[f"{stage}_ok"] = proc.returncode == 0
        if proc.returncode:
            result["error"] = f"{stage} failed; see {stage}.log"
            return result
    candidate = {k: result[k] for k in ("label", "fingerprint", "git_sha", "source_sha")}
    provisional = work / "provisional-fixture-only.json"
    provisional.write_text(json.dumps({"format": 1, "bridge_files": data["bridge_files"],
                                      "builds": [candidate]}, indent=2) + "\n", encoding="utf-8")
    env["HMP_DIRECT_SEND_QUALIFICATION"] = str(provisional.resolve())
    # Empty selections / skips must never count as qualification: pytest's JUnit report
    # provides the independently checked count and outcomes.
    report = work / "integration.xml"
    proc = subprocess.run([
        sys.executable, "-m", "pytest", "server/tests/integration/test_direct_send_fixture.py",
        "server/tests/integration/test_approvals_fixture.py", "-k", spec.label, "-q",
        "-o", "addopts=", f"--junitxml={report.resolve()}",
    ], cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env)
    (work / "integration.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    result["integration_ok"] = proc.returncode == 0 and integration_report_passed(report)
    if not result["integration_ok"]:
        result["error"] = "integration failed or skipped; see integration.log"
        return result
    if compute_read_bridge_fingerprint(src, data["bridge_files"]) != fingerprint:
        result["error"] = "Hermes files changed during qualification"
        return result
    result["qualified"] = True
    return result


def integration_report_passed(path: Path) -> bool:
    import xml.etree.ElementTree as ET

    if not path.is_file():
        return False
    cases = list(ET.parse(path).getroot().iter("testcase"))  # noqa: S314 -- local pytest output
    return bool(cases) and all(
        case.find(tag) is None for case in cases for tag in ("failure", "error", "skipped")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("read", "direct-send"), default="read")
    parser.add_argument("--fixture-qualification-out", type=Path, default=None,
                        help="direct-send: final receipt for scratch fixture copies only")
    parser.add_argument("--builds-dir", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--builds", default=None, help="comma-separated labels (default: all)")
    parser.add_argument("--json-out", type=Path, default=None, help="write the full matrix JSON")
    parser.add_argument(
        "--refs-dir", type=Path, default=None,
        help="override the located _refs dir (the one given to extract.py --refs-dir)",
    )
    args = parser.parse_args(argv)
    global _REFS_DIR_OVERRIDE
    _REFS_DIR_OVERRIDE = args.refs_dir

    builds_dir = args.builds_dir or Path(os.environ.get("HMP_HERMES_BUILDS_DIR", ""))
    if not builds_dir or not builds_dir.is_dir():
        print("run_matrix: --builds-dir (or $HMP_HERMES_BUILDS_DIR) must be an extracted builds "
              "directory (tools/hermes_builds/extract.py)", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)

    specs = load_build_specs()
    if args.builds:
        wanted = set(args.builds.split(","))
        unknown = wanted - {s.label for s in specs}
        if unknown:
            parser.error(f"unknown builds: {sorted(unknown)}")
        specs = [s for s in specs if s.label in wanted]
    if args.fixture_qualification_out:
        if args.target != "direct-send":
            parser.error("--fixture-qualification-out requires --target direct-send")
        if not args.fixture_qualification_out.resolve().is_relative_to(args.out.resolve()):
            parser.error("fixture qualification receipt must be inside --out")
        # Do not leave a previous successful receipt behind on a failed requalification.
        args.fixture_qualification_out.unlink(missing_ok=True)

    results: list[dict[str, Any]] = []
    for spec in specs:
        print(f"run_matrix: {spec.label} ...", file=sys.stderr)
        process = process_direct_build if args.target == "direct-send" else process_build
        res = process(spec, builds_dir, args.out)
        results.append(res)
        if res["qualified"]:
            status = "QUALIFIED"
        else:
            status = f"NOT QUALIFIED ({res.get('error', 'see log')})"
        print(f"run_matrix: {spec.label}: {status}", file=sys.stderr)

    qualified = [r for r in results if r["qualified"]]
    unsupported: dict[str, Any] | None = None
    if qualified and args.target == "read":
        unsupported = unsupported_path_check(builds_dir, qualified[0]["label"], args.out)
        print(
            f"run_matrix: SC-007 unsupported-path check: {'OK' if unsupported['ok'] else 'FAIL'} "
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
        "sc007_unsupported_path_check": unsupported,
    }
    text = json.dumps(matrix, indent=2) + "\n"
    print(text)
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")

    ok = bool(qualified) and (unsupported is None or unsupported["ok"])
    if args.target == "direct-send":
        ok = ok and len(qualified) == len(results)
    if ok and args.fixture_qualification_out:
        data = json.loads(DIRECT_COMPAT_PATH.read_text(encoding="utf-8"))
        data["builds"] = matrix["candidate_entries"]
        args.fixture_qualification_out.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

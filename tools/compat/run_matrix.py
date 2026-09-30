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

Ad-hoc exact candidate (scratch only; never touches builds.yaml or read_compat_builds.json):
    python3 tools/compat/run_matrix.py --refs-dir <dir> --builds-dir <dir> --out <scratch dir>
        --candidate-sha <full 40 lowercase hex> --candidate-interpreter </abs/path/python3.MINOR>
        [--candidate-python 3.MINOR[.PATCH]] [--json-out <file inside --out>]
The candidate must first have been extracted with the same `--candidate-sha`,
`--candidate-interpreter` and `--candidate-python` (`extract.py`). The matrix then runs ONLY the
fixed label `candidate`. In order, and stopping at the first failure:

  - verifies the extraction: metadata (label, commit, interpreter), the clone's git dirs (never a
    partial clone; git runs with every transport and lazy fetching disabled), and -- BEFORE any
    candidate Python runs -- that the ENTIRE extracted tracked source is byte- and mode-exact
    against the commit in `<refs-dir>/hermes-agent` with nothing unexpected beside it (only a
    top-level `.venv` and `*.egg-info` metadata are tolerated);
  - then, still before the venv's interpreter runs: `--candidate-interpreter` is proven with
    lstat/readlink/realpath only to be a base Python that neither lies in nor links through the
    real home, is probed once (`-I -S`), and every `.venv/bin/python*` and `pyvenv.cfg` is proven
    to lead only to it (or the base it reported) outside the home. Anything else fails closed;
  - runs the self-check and the read suite for exactly that label (the read suite by exact pytest
    node id, never `-k`, with a private `--basetemp`; zero collected, skipped or failed tests, or
    any collected test it cannot parse, fail closed);
  - runs SC-007 on copies of just the bridge files (no symlink or `.venv` is ever followed): a
    SCRATCH compatibility list holding one provisional exact row for the candidate must list and
    support the pristine copy and refuse a one-byte-mutated copy, before any bridge import. HMP is
    imported from the reviewed `server/` directory under `python -I`; the candidate tree is only
    read as data. The committed list is never edited;
  - re-verifies, AFTER SC-007, the whole tracked tree, the bridge-file fingerprint and the
    lockfile against the commit again (`source_unchanged_after_run`), to catch accidental drift
    (a stage that wrote into the tree, an editor, a stray process). It cannot catch a same-user
    process that restores what it changed, or anything in `.venv`.

It cannot be combined with `--builds`. Every subprocess gets a scrubbed environment: HOME,
HERMES_HOME, XDG_*, TMPDIR and caches are private (0700) scratch that is DELETED and recreated at
the start of every run (so no stale bytecode, cache or home is ever consumed), no credentials,
proxies or `GIT_*`/`PYTHON*` variables are inherited, PATH entries that link into `~/.hermes` are
dropped, and the real-home checks use the OS account database, not `$HOME`. That only redirects
where well-behaved code looks: it confines nothing, and candidate code can still read the real
home (a live `~/.hermes` included) and write outside scratch by absolute path. The JSON it prints
(and writes, 0600, to `--json-out`) is a public-safe report: named booleans, the HMP source commit
and version, the coarse matrix runtime, the versions of the fixture's unpinned runtime
dependencies, a UTC `generated_at` -- no paths, secrets, transcripts or logs (those stay in the
scratch `--out`). `--json-out` must be a regular file inside `--out`, in a directory that is not
itself a symlink (an existing regular file of ours is replaced; a symlink or hard link is
refused); the layout is validated at start and again immediately before the report is written.

SECURITY: none of this is a sandbox or an attestation. The candidate's Python and locked
dependencies execute as this user (uv builds, imports, the fixture gateway, the read suite), so
they can read what the user can read, write anywhere the user can write, and forge the results of
every check here -- including this report. `candidate_passed` is NON-ADVERSARIAL COMPATIBILITY
EVIDENCE ONLY: it says an honest candidate at this commit behaved as expected, not that a hostile
one was contained. An isolated VM, container or user account protects the HOST; it does not
protect this harness from code running as the same user inside it.

`--builds-dir` defaults to `$HMP_HERMES_BUILDS_DIR`. `--out` is a scratch directory for the
self-check and read-suite fixture homes (never the real Hermes home; see `_fixture_common.py`'s
isolation rules, which every subprocess this tool launches also obeys). At most one fixture
gateway runs at a time (host load): builds are processed one at a time, never in parallel, and
`-o addopts=` / no xdist is passed to every pytest invocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

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
sys.path.insert(0, str(TOOLS_DIR / "hermes_builds"))

import candidate_safety as safety  # noqa: E402 -- after the sys.path bootstrap above
import extract as extract_mod  # noqa: E402

CANDIDATE_LABEL = extract_mod.CANDIDATE_LABEL
CANDIDATE_CLONE = extract_mod.CANDIDATE_CLONE
PLUGIN_MANIFEST = REPO_ROOT / "plugin.yaml"
# Set (only) by the candidate path for its scrubbed pytest: without it the read suite never
# parametrizes over `candidate`, so no other pytest run can start the candidate's code.
CANDIDATE_OPT_IN_ENV = "HMP_ENABLE_CANDIDATE_BUILD"
CANDIDATE_WARNING = (
    "run_matrix: WARNING: --candidate-sha executes the candidate's Python and its locked "
    "dependencies (self-check gateway, read suite) as this user. Environment scrubbing and path "
    "checks are not a sandbox or an attestation, and code running as this user can forge results: "
    "run an unreviewed candidate only in an isolated VM, container or user account (which "
    "protects the host, not this harness)."
)
ASSURANCE = (
    "non-adversarial compatibility evidence only; not an attestation, not a sandbox: code running "
    "as the same user can forge these results"
)
# Installed unpinned by the fixture tools (`_fixture_common.ensure_runtime_deps`), so NOT covered
# by the candidate's lockfile; their installed versions are reported instead.
RUNTIME_DEPENDENCIES = ("aiohttp", "cryptography", "qrcode")
_VERSION_RE = re.compile(r"^[0-9][0-9A-Za-z.+!_-]{0,31}$")


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
    if any(b["label"] == CANDIDATE_LABEL for b in data["builds"]):
        raise SystemExit(
            f"run_matrix: builds.yaml may not use the reserved label {CANDIDATE_LABEL!r}"
        )
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
    return extract_mod.ref_resolves(clone, spec.ref)


def run_selfcheck(
    label: str, out_dir: Path, builds_dir: Path, env: dict[str, str] | None = None
) -> tuple[bool, str]:
    proc = subprocess.run(
        [
            sys.executable, str(SELFCHECK),
            "--build", label, "--out", str(out_dir), "--builds-dir", str(builds_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
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


# The SC-007 check, run as `python -I -c <script> <server dir> <mutated> <pristine> <list> <mode>`.
# `-I` (isolated mode) drops PYTHON* variables, the user site and the working directory from
# `sys.path`; the only thing added is the reviewed `server/` directory, so `hmp_plugin` can only
# come from there (asserted). The candidate's bridge files are DATA: the gate reads their bytes,
# nothing of theirs is imported or executed, and their directory is never on `sys.path`. The
# dependency probe (which would import Hermes modules) is replaced by a counter: SC-007 is about
# the identity decision, and the real probe runs in the read suite against a real gateway.
_UNSUPPORTED_PATH_CHECK_SCRIPT = """
import json
import sys
from pathlib import Path

server_dir, mutant, pristine, list_path = (Path(a).resolve() for a in sys.argv[1:5])
mode = sys.argv[5]
if not sys.flags.isolated:
    raise SystemExit("SC-007 check must run under `python -I`")
sys.path.insert(0, str(server_dir))

from hmp_plugin import compat as compat_mod

origin_ok = (
    Path(compat_mod.__file__).resolve() == server_dir / "hmp_plugin" / "compat.py"
    and not any(
        Path(entry or ".").resolve().is_relative_to(root)
        for entry in sys.path
        for root in (mutant, pristine)
    )
)

compat_list = compat_mod.load_read_compat_list(list_path)
reader = compat_mod.GitFingerprintReader(compat_list.bridge_files)


def evaluate(root):
    probes = []

    def probe():
        probes.append(1)
        return ()

    gate = compat_mod.CompatGate(reader, compat_list, probe, lambda: root)
    return gate.evaluate(), len(probes)


result, probe_calls = evaluate(mutant)
pristine_result, pristine_probe_calls = (None, None)
if mode == "candidate":
    pristine_result, pristine_probe_calls = evaluate(pristine)
print(json.dumps({
    "status": result.status.value,
    "why": result.why.value if result.why else None,
    "probe_calls": probe_calls,
    "pristine_status": pristine_result.status.value if pristine_result else None,
    "pristine_entry": (
        pristine_result.entry.label if pristine_result and pristine_result.entry else None
    ),
    "pristine_probe_calls": pristine_probe_calls,
    "bridge_imported": any(
        name == "hmp_plugin.bridge" or name.startswith("hmp_plugin.bridge.")
        for name in sys.modules
    ),
    "origin_ok": origin_ok,
}))
"""


def _flip_one_byte(path: Path) -> None:
    """Change exactly one byte of our own private copy (a length-preserving flip; an empty file
    gets one byte instead), so its read-bridge fingerprint changes."""
    data = path.read_bytes()
    path.write_bytes(data[:-1] + bytes([data[-1] ^ 0x01]) if data else b"\0")


def _provisional_list(bridge_files: list[str], fingerprint: str, source_sha: str | None) -> str:
    """The scratch compatibility list for the candidate: the committed `bridge_files` and exactly
    one provisional row -- the candidate's own verified fingerprint. Nothing else is listed."""
    return json.dumps({
        "format": 1,
        "bridge_files": bridge_files,
        "builds": [{
            "label": CANDIDATE_LABEL,
            "fingerprint": fingerprint,
            "git_sha": None,
            "source_sha": source_sha,
            "qualified_by": "provisional ad-hoc candidate row (scratch list; never committed)",
            "qualified_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        }],
    })


def unsupported_path_check(
    builds_dir: Path,
    qualified_label: str,
    scratch: Path,
    expected_fingerprint: str | None = None,
    env: dict[str, str] | None = None,
    source_sha: str | None = None,
) -> dict[str, Any]:
    """SC-007: an unlisted build (a qualified build's bridge files with one byte altered) must be
    refused `UNSUPPORTED` / `hermes_build_unsupported` (ERR-2a), with zero bridge calls. Run in a
    fresh isolated interpreter so nothing this process (or pytest's own collection) already
    imported can hide a real bridge import.

    Only the `bridge_files` are copied out of the build (never following a symlink, never
    entering `.venv`; a FIFO, device, symlink or directory where a bridge file should be is
    refused), into a private scratch directory. Nothing of the tree is imported or executed.

    With `expected_fingerprint` (the candidate path) the pristine copy is first proven to have
    that verified fingerprint, and the check runs against a SCRATCH list holding one provisional
    row for exactly that fingerprint: the pristine copy must be listed and supported, the mutated
    copy refused, and the mutation must actually change the fingerprint. The committed list is
    only read (for `bridge_files`), never edited. Without it (listed builds), the committed list
    is used and only the mutated copy is evaluated. `env` (the candidate path's scrubbed
    environment) replaces the inherited one."""
    from hmp_plugin.compat import compute_read_bridge_fingerprint, load_read_compat_list

    candidate_mode = expected_fingerprint is not None
    result: dict[str, Any] = {
        "label": qualified_label, "ok": False, "status": None, "why": None,
        "bridge_imported": None,
        "source_matches_expected": False if candidate_mode else None,
        "pristine_supported": None, "stderr_tail": "",
    }
    try:
        bridge_files = list(load_read_compat_list(READ_COMPAT_PATH).bridge_files)
        work = scratch / "sc007"
        safety.remove_private_tree(work, scratch)
        safety.ensure_private_dir(work, "SC-007 scratch directory")
        src = builds_dir / qualified_label / "src"
        pristine, mutant = work / "pristine", work / "mutant"
        safety.copy_regular_files(src, bridge_files, pristine)
        safety.copy_regular_files(src, bridge_files, mutant)
        pristine_fingerprint = compute_read_bridge_fingerprint(pristine, bridge_files)
        _flip_one_byte(mutant / sorted(bridge_files)[0])
        mutant_fingerprint = compute_read_bridge_fingerprint(mutant, bridge_files)
        list_path = READ_COMPAT_PATH
        if candidate_mode:
            result["source_matches_expected"] = pristine_fingerprint == expected_fingerprint
            if not result["source_matches_expected"] or mutant_fingerprint in (
                expected_fingerprint, None
            ):
                result["stderr_tail"] = "SC-007 copy is not the verified candidate"
                return result
            list_path = safety.write_private_file(
                work / "provisional_read_compat_builds.json",
                _provisional_list(bridge_files, expected_fingerprint, source_sha),
            )
        elif mutant_fingerprint in (pristine_fingerprint, None):
            result["stderr_tail"] = "SC-007 mutation did not change the fingerprint"
            return result
    except (safety.SafetyError, OSError, ValueError) as exc:
        result["stderr_tail"] = f"SC-007 setup refused: {exc}"
        return result

    proc = subprocess.run(
        [
            sys.executable, "-I", "-c", _UNSUPPORTED_PATH_CHECK_SCRIPT,
            str(SERVER_DIR), str(mutant), str(pristine), str(list_path),
            "candidate" if candidate_mode else "listed",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(work),
    )
    parsed: dict[str, Any] | None = None
    for line in proc.stdout.splitlines():
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            parsed = loaded
    parsed = parsed or {}
    refused = (
        parsed.get("status") == "unsupported"
        and parsed.get("why") == "hermes_build_unsupported"
        and parsed.get("bridge_imported") is False
        and parsed.get("origin_ok") is True
        and parsed.get("probe_calls") == 0
    )
    pristine_supported: bool | None = None
    if candidate_mode:
        pristine_supported = (
            parsed.get("pristine_status") == "supported"
            and parsed.get("pristine_entry") == CANDIDATE_LABEL
            and parsed.get("pristine_probe_calls") == 1
        )
    ok = refused and pristine_supported is not False
    result.update(
        ok=ok,
        status=parsed.get("status"),
        why=parsed.get("why"),
        bridge_imported=parsed.get("bridge_imported"),
        pristine_supported=pristine_supported,
        stderr_tail="\n".join(proc.stderr.splitlines()[-30:]) if not ok else "",
    )
    return result


# ---- ad-hoc exact candidate (`--candidate-sha`) ------------------------------------------------
#
# Everything below is reachable only through `--candidate-sha`; the listed-build path above is
# unchanged. The label and clone name are fixed (see extract.py); the only executable a caller
# names is `--candidate-interpreter`, which is validated without being run before anything uses it.

_NODE_ID_RE = re.compile(r"^(?P<file>\S+)::(?P<func>[A-Za-z_]\w*)\[(?P<param>[^\[\]]*)\]$")
_COLLECTED_SUMMARY_RE = re.compile(r"^(\d+) tests? collected\b")
_READ_SUITE_ID_FILE = READ_SUITE.relative_to(SERVER_DIR).as_posix()
_TOKEN_RE = re.compile(r"^[a-z_]{1,64}$")
_MAX_METADATA_BYTES = 1 << 20


def _candidate_env(builds_dir: Path, scratch: Path) -> dict[str, str]:
    """The environment of every candidate subprocess: HOME, HERMES_HOME, every XDG_* directory,
    TMPDIR and the caches are private (0700) directories under `<scratch>/env`; only the
    `extract.py` allowlist is inherited (no credentials, proxies, `GIT_*`, `PYTHON*`); plus the
    builds directory and the explicit opt-in the read suite needs to parametrize `candidate`.
    Called once per run, and it starts by deleting the previous run's `<scratch>/env` contents
    (stale bytecode, caches, homes are never evidence, and never an input)."""
    safety.reset_scratch_env(scratch / "env")
    env = safety.scrubbed_env(scratch / "env")
    env["HMP_HERMES_BUILDS_DIR"] = str(builds_dir)
    env[CANDIDATE_OPT_IN_ENV] = "1"
    return env


def _version_matches(actual: object, requested: str) -> bool:
    return isinstance(actual, str) and (actual == requested or actual.startswith(requested + "."))


def _commit_bridge_fingerprint(
    clone: Path, entries: list[safety.TreeEntry], bridge_files: list[str], scratch: Path | None
) -> str | None:
    """The read-bridge fingerprint of the commit computed straight from its raw blobs (no
    `git archive`, no filters), read-only. `None` if any listed file is not a regular tracked
    file of that commit."""
    from hmp_plugin.compat import compute_read_bridge_fingerprint

    by_path = {e.path: e for e in entries}
    for rel in bridge_files:
        entry = by_path.get(rel)
        if entry is None or entry.mode not in ("100644", "100755"):
            return None
    with tempfile.TemporaryDirectory(prefix="fp-", dir=scratch) as tmp:
        root = Path(tmp)
        with safety.BlobReader(clone) as reader:
            for rel in bridge_files:
                safety.check_relative_path(rel, "bridge file")
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(reader.read(by_path[rel].oid, limit=safety.MAX_BRIDGE_FILE_BYTES))
        return compute_read_bridge_fingerprint(root, bridge_files)


def _read_metadata(path: Path) -> dict[str, Any] | None:
    """`build-metadata.json` as a dict, only if it is a regular file (never a symlink or FIFO)
    of sane size; anything else is treated as missing."""
    try:
        fd = os.open(path, safety.READ_FLAGS)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        with os.fdopen(fd, "rb", closefd=False) as fh:
            raw = fh.read(_MAX_METADATA_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > _MAX_METADATA_BYTES:
        return None
    try:
        meta = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return meta if isinstance(meta, dict) else None


def verify_candidate(
    builds_dir: Path,
    refs_dir: Path,
    sha: str,
    python: str,
    *,
    scratch: Path | None = None,
    env: dict[str, str] | None = None,
    problems: list[str] | None = None,
    interpreter: Path | str | None = None,
) -> tuple[dict[str, bool], str | None]:
    """Prove the extracted `candidate` tree is the one requested. Returns named booleans and the
    tree's read-bridge fingerprint (only when every check passed, else `None`). Fail-closed: any
    missing, unreadable or malformed input makes the affected boolean False.

    Ordering matters: the whole extracted tracked source is proven byte- and mode-exact against
    the commit (and free of unexpected files) BEFORE any interpreter is run, so no code of an
    unverified tree executes here. Then `interpreter` (`--candidate-interpreter`; `None` fails
    closed) is proven without executing it (`validate_base_interpreter`), probed once, and every
    `.venv/bin/python*` plus `pyvenv.cfg` is proven to lead only to it (or the base it reported)
    outside the real home (`validate_venv_interpreters`) -- all before the venv's interpreter is
    executed. `source_fingerprint_matches` covers the tree proof, the bridge-file fingerprint
    against the commit's own blobs, and the lockfile. Human-readable reasons are appended to
    `problems` (private: they contain paths)."""
    checks = {
        "clone_commit_matches": False,
        "extraction_metadata_valid": False,
        "extraction_metadata_commit_matches": False,
        "interpreter_matches": False,
        "source_fingerprint_matches": False,
    }
    notes = problems if problems is not None else []
    build_dir = builds_dir / CANDIDATE_LABEL
    src = build_dir / "src"
    clone = refs_dir / CANDIDATE_CLONE

    if (clone / ".git").exists():
        try:
            safety.resolve_clone_git_dirs(clone)  # nothing here may lead into ~/.hermes
            checks["clone_commit_matches"] = extract_mod.ref_resolves(clone, sha) == sha
        except safety.SafetyError as exc:
            notes.append(f"clone: {exc}")

    meta = _read_metadata(build_dir / extract_mod.METADATA_NAME)
    if meta is None:
        notes.append("extraction metadata is missing, unreadable or not a regular file")
        return checks, None
    checks["extraction_metadata_valid"] = (
        meta.get("label") == CANDIDATE_LABEL
        and meta.get("extraction_ok") is True
        and meta.get("imports_ok") is True
        and src.is_dir()
    )
    checks["extraction_metadata_commit_matches"] = (
        meta.get("commit") == sha and meta.get("ref") == sha
    )
    if not checks["extraction_metadata_valid"]:
        return checks, None

    # The whole tracked tree, before any interpreter of it runs.
    tree_ok, entries = _verify_tree(
        builds_dir, build_dir, clone, sha, clone_ok=checks["clone_commit_matches"], notes=notes
    )

    recorded = meta.get("python_version")
    live = None
    base = None
    if tree_ok:
        probe_env = env if env is not None else safety.minimal_env()
        base = _checked_venv(src, interpreter, python, probe_env, notes)
        if base is not None:
            try:
                live = extract_mod.interpreter_info(src, probe_env)
            except OSError:  # the venv interpreter cannot be executed
                live = None
    checks["interpreter_matches"] = (
        tree_ok
        and base is not None
        and meta.get("python_base_interpreter") == str(base)
        and meta.get("python_requested") == python
        and _version_matches(recorded, python)
        and live is not None
        and live.get("version") == recorded
        and _base_outside_home(live, notes)
    )

    fingerprint: str | None = None
    from_git: str | None = None
    lock_ok = False
    if tree_ok:
        fingerprint, from_git, lock_ok = _source_identity(src, clone, entries, meta, scratch)
    checks["source_fingerprint_matches"] = (
        tree_ok and fingerprint is not None and fingerprint == from_git and lock_ok
    )
    return checks, fingerprint if all(checks.values()) else None


def _checked_venv(
    src: Path, interpreter: Path | str | None, python: str, env: dict[str, str], notes: list[str]
) -> Path | None:
    """The real path of `--candidate-interpreter`, once it and the candidate venv have been
    proven not to execute anything from the real home: the interpreter by lstat/readlink/realpath
    and `pyvenv.cfg` (nothing executed), then ONE isolated probe of it (version and base), then
    every `.venv/bin/python*` and `pyvenv.cfg` (nothing executed). `None` (with a note) otherwise;
    the venv's interpreter must not be run then."""
    if interpreter is None:
        notes.append(f"interpreter: {extract_mod.CANDIDATE_INTERPRETER_SETUP}")
        return None
    try:
        base = safety.validate_base_interpreter(interpreter, "--candidate-interpreter")
        _, allowed = extract_mod.probe_base_interpreter(base, python, env)
        safety.validate_venv_interpreters(src / safety.VENV_DIRNAME, allowed)
    except (safety.SafetyError, OSError) as exc:
        notes.append(f"interpreter: {exc}")
        return None
    return base


def _base_outside_home(info: dict[str, Any], notes: list[str]) -> bool:
    """The venv interpreter's base (`sys.base_prefix`, `sys._base_executable`) is outside the real
    home -- the same rule extraction enforces, so a venv built on an interpreter from the home is
    never run, whoever built it."""
    reason = extract_mod.check_interpreter_outside_home(info)
    if reason is not None:
        notes.append(f"interpreter: {reason}")
    return reason is None


def _verify_tree(
    builds_dir: Path, build_dir: Path, clone: Path, sha: str, *, clone_ok: bool, notes: list[str]
) -> tuple[bool, list[safety.TreeEntry]]:
    """Trusted builds/build directories, and the whole tracked source proven byte- and mode-exact
    against the commit (nothing else beside it but a `.venv` and `*.egg-info` metadata). Reads
    only; executes nothing. Returns `(ok, the commit's tree entries)`."""
    entries: list[safety.TreeEntry] = []
    try:
        safety.assert_trusted_dir(builds_dir, "--builds-dir")
        safety.assert_leaf_not_symlink(build_dir, "the candidate build directory")
        safety.assert_trusted_dir(build_dir, "the candidate build directory")
        if not clone_ok:
            return False, entries
        entries = safety.list_commit_tree(clone, sha)
        tree_problems = safety.verify_tree_matches_commit(build_dir / "src", entries)
        notes.extend(f"tree: {p}" for p in tree_problems)
        return not tree_problems, entries
    except safety.SafetyError as exc:
        notes.append(str(exc))
        return False, entries


def _source_identity(
    src: Path,
    clone: Path,
    entries: list[safety.TreeEntry],
    meta: dict[str, Any],
    scratch: Path | None,
) -> tuple[str | None, str | None, bool]:
    """`(bridge fingerprint of the extracted tree, fingerprint of the commit's own blobs, lockfile
    matches the extraction metadata)`; `(None, None, False)` if anything cannot be read."""
    try:
        from hmp_plugin.compat import compute_read_bridge_fingerprint, load_read_compat_list

        bridge_files = list(load_read_compat_list(READ_COMPAT_PATH).bridge_files)
        fingerprint = compute_read_bridge_fingerprint(src, bridge_files)
        from_git = _commit_bridge_fingerprint(clone, entries, bridge_files, scratch)
        lock_sha = hashlib.sha256((src / "uv.lock").read_bytes()).hexdigest()
        return fingerprint, from_git, meta.get("uv_lock_sha256") == lock_sha
    except (OSError, ValueError, safety.SafetyError):
        return None, None, False


def recheck_source(
    builds_dir: Path,
    refs_dir: Path,
    sha: str,
    expected_fingerprint: str,
    *,
    scratch: Path | None = None,
    problems: list[str] | None = None,
) -> bool:
    """Prove again, after every stage that ran the candidate (SC-007 is last), that the tracked
    tree is still exactly the commit, and that its bridge-file fingerprint (equal to the one
    verified before the run) and lockfile are unchanged. Reads only; executes nothing. This
    catches drift -- a stage that wrote into the tree, a stray edit or process -- and NOTHING
    adversarial: code running as this user can restore what it changed, forge the metadata this
    reads, or alter `.venv` (never checked). `True` only if every check passed."""
    notes = problems if problems is not None else []
    build_dir = builds_dir / CANDIDATE_LABEL
    clone = refs_dir / CANDIDATE_CLONE
    clone_ok = False
    if (clone / ".git").exists():
        try:
            safety.resolve_clone_git_dirs(clone)
            clone_ok = extract_mod.ref_resolves(clone, sha) == sha
        except safety.SafetyError as exc:
            notes.append(f"clone: {exc}")
    meta = _read_metadata(build_dir / extract_mod.METADATA_NAME)
    if meta is None or meta.get("commit") != sha or meta.get("ref") != sha:
        notes.append("extraction metadata changed or is unreadable")
        return False
    tree_ok, entries = _verify_tree(
        builds_dir, build_dir, clone, sha, clone_ok=clone_ok, notes=notes
    )
    if not tree_ok:
        return False
    fingerprint, from_git, lock_ok = _source_identity(
        build_dir / "src", clone, entries, meta, scratch
    )
    ok = fingerprint is not None and fingerprint == from_git == expected_fingerprint and lock_ok
    if not ok:
        notes.append("bridge fingerprint or lockfile differs from the verified extraction")
    return ok


def selfcheck_really_ran(ok: bool, log: str, label: str) -> bool:
    """`selfcheck.py` exits 0 for its `SKIP:` path too; only its explicit `OK:` line for this
    label counts as a pass."""
    lines = [ln for ln in log.splitlines() if ln.strip()]
    return (
        ok
        and not any(ln.startswith("SKIP:") for ln in lines)
        and any(ln.startswith(f"OK: {label!r} ") for ln in lines)
    )


def parse_collected_ids(output: str) -> list[tuple[str, str, str]] | None:
    """`(node id, test function, parameter id)` for every test of `pytest --collect-only -q`
    output, or `None` if ANY collected line cannot be parsed. The leading block of non-blank
    lines must be nothing but parametrized node ids of the read suite file, and the trailing
    `N tests collected` count must equal the number parsed; a test that cannot be parsed can
    never be silently left out of (or into) the selection."""
    lines = output.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    found: list[tuple[str, str, str]] = []
    while index < len(lines) and lines[index].strip():
        node_id = lines[index].strip()
        m = _NODE_ID_RE.match(node_id)
        if m is None or m["file"] != _READ_SUITE_ID_FILE:
            return None
        found.append((node_id, m["func"], m["param"]))
        index += 1
    summary = next(
        (m for m in (_COLLECTED_SUMMARY_RE.match(ln.strip()) for ln in lines[index:]) if m), None
    )
    if summary is None or int(summary.group(1)) != len(found):
        return None
    return found


def select_exact_node_ids(collected: list[tuple[str, str, str]], label: str) -> list[str] | None:
    """Node ids whose parameter id is exactly `label` (no substring / `-k` matching). `None`
    (fail closed) when there are none, or when `label` does not cover every test function in the
    module -- a partially parametrized suite is not "the read suite" for that label."""
    every = {func for _n, func, _p in collected}
    chosen = [(n, func) for n, func, p in collected if p == label]
    if not chosen or {func for _n, func in chosen} != every:
        return None
    return [n for n, _func in chosen]


def junit_totals(path: Path) -> dict[str, int] | None:
    try:
        # Our own pytest's junit output, written a moment ago into the scratch directory.
        root = ElementTree.parse(path).getroot()  # noqa: S314
    except (OSError, ElementTree.ParseError):
        return None
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    suites = list(root.iter("testsuite"))
    if not suites:
        return None
    for suite in suites:
        for key in totals:
            try:
                totals[key] += int(suite.get(key, "0"))
            except ValueError:
                return None
    return totals


def run_read_suite_exact(
    label: str, builds_dir: Path, scratch: Path, env: dict[str, str]
) -> tuple[bool, int, str]:
    """The read suite for exactly `label`: collect, select by exact parameter id, run those node
    ids, and require every one to have actually executed and passed (junit: tests == selected,
    0 failures/errors/skipped). pytest's temp directories go to a private `--basetemp` under
    `scratch`. Returns `(passed, tests_run, private log)`."""
    base = [sys.executable, "-m", "pytest", "-o", "addopts=", "-p", "no:cacheprovider"]
    collect = subprocess.run(
        [*base, str(READ_SUITE), "--collect-only", "-q"],
        cwd=str(SERVER_DIR), capture_output=True, text=True, env=env, check=False,
    )
    log = collect.stdout + collect.stderr
    if collect.returncode != 0:
        return False, 0, log
    collected = parse_collected_ids(collect.stdout)
    if collected is None:
        return False, 0, log + "\nrun_matrix: a collected test could not be parsed\n"
    node_ids = select_exact_node_ids(collected, label)
    if node_ids is None:
        return False, 0, log
    junit = scratch / "read-suite-junit.xml"
    basetemp = scratch / "pytest-basetemp"
    try:
        if os.path.lexists(junit):
            junit.unlink()
        safety.remove_private_tree(basetemp, scratch)  # pytest deletes --basetemp itself
    except (safety.SafetyError, OSError) as exc:
        return False, 0, log + f"\nrun_matrix: {exc}\n"
    run = subprocess.run(
        [*base, "-q", f"--junitxml={junit}", f"--basetemp={basetemp}", *node_ids],
        cwd=str(SERVER_DIR), capture_output=True, text=True, env=env, check=False,
    )
    log += run.stdout + run.stderr
    totals = junit_totals(junit)
    passed = (
        run.returncode == 0
        and totals is not None
        and totals["tests"] == len(node_ids)
        and totals["failures"] == totals["errors"] == totals["skipped"] == 0
    )
    return passed, (totals["tests"] if totals else 0), log


def hmp_source_info() -> dict[str, Any]:
    """The HMP source under test: its git commit, `plugin.yaml` version, and whether the working
    tree had uncommitted changes (so a commit alone is not mistaken for the code that ran)."""
    def _git(*args: str) -> str | None:
        proc = safety.run_git(REPO_ROOT, *args)
        return proc.stdout if proc.returncode == 0 else None

    head = (_git("rev-parse", "HEAD") or "").strip()
    status = _git("status", "--porcelain")
    try:
        version = yaml.safe_load(PLUGIN_MANIFEST.read_text(encoding="utf-8")).get("version")
    except (OSError, yaml.YAMLError, AttributeError):
        version = None
    return {
        "commit": head if extract_mod.FULL_SHA_RE.fullmatch(head) else None,
        "version": version if isinstance(version, str) and len(version) <= 64 else None,
        "worktree_dirty": status is None or bool(status.strip()),
    }


def _is_real_dir(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def runtime_dependency_versions(src: Path) -> dict[str, str | None]:
    """Installed versions of `RUNTIME_DEPENDENCIES` in the candidate's venv, from the names of
    their `*.dist-info` directories: nothing is executed and no symlink is followed. These
    packages are installed by the fixture tools from the package index WITHOUT pins, so they are
    not covered by the candidate's lockfile; the versions are reported rather than assumed. `None`
    when a package is absent, appears more than once, or has an unexpected version string."""
    counts: dict[str, list[str]] = {name: [] for name in RUNTIME_DEPENDENCIES}
    lib = src / ".venv" / "lib"
    if _is_real_dir(src / ".venv") and _is_real_dir(lib):
        try:
            pythons = [d for d in os.scandir(lib) if d.name.startswith("python")]
        except OSError:
            pythons = []
        for py in pythons:
            site = Path(py.path) / "site-packages"
            if not _is_real_dir(Path(py.path)) or not _is_real_dir(site):
                continue
            try:
                listing = list(os.scandir(site))
            except OSError:
                continue
            for dirent in listing:
                if not dirent.name.endswith(".dist-info") or not dirent.is_dir(
                    follow_symlinks=False
                ):
                    continue
                name, _, version = dirent.name[: -len(".dist-info")].partition("-")
                normalized = name.lower().replace("_", "-").replace(".", "-")
                if normalized in counts:
                    counts[normalized].append(version)
    return {
        name: found[0] if len(found) == 1 and _VERSION_RE.fullmatch(found[0]) else None
        for name, found in counts.items()
    }


def _safe_token(value: object) -> str | None:
    return value if isinstance(value, str) and _TOKEN_RE.fullmatch(value) else None


def run_candidate(
    sha: str,
    python: str,
    refs_dir: Path,
    builds_dir: Path,
    out: Path,
    now: datetime | None = None,
    *,
    interpreter: Path | str | None = None,
) -> dict[str, Any]:
    """Qualify the ad-hoc candidate and return the public-safe report (see the module docstring).
    Stages run in order and stop at the first failure: extraction verification, self-check, read
    suite, SC-007. Nothing of the candidate executes before its whole tracked source has been
    proven exact, and no interpreter runs before `interpreter` (`--candidate-interpreter`; without
    it the verification fails closed) and the venv's `bin/python*`/`pyvenv.cfg` are proven to
    lead nowhere into the real home. SC-007 is only ever run on the tree those earlier stages
    verified. Every file and directory created (also by the candidate's own processes) is private
    to this user."""
    sha = extract_mod.parse_candidate_sha(sha)
    python = extract_mod.parse_python_version(CANDIDATE_LABEL, python)
    try:
        safety.validate_candidate_layout(
            repo_root=REPO_ROOT, builds_dir=builds_dir, refs_dir=refs_dir, out=out,
            interpreter=interpreter,
        )
        scratch = safety.ensure_private_dir(
            safety.ensure_private_dir(out, "--out") / CANDIDATE_LABEL, "scratch directory"
        )
        env = _candidate_env(builds_dir, scratch)
    except safety.SafetyError as exc:
        raise SystemExit(f"run_matrix: {exc}") from exc
    old_umask = os.umask(0o077)
    try:
        return _run_candidate_stages(
            sha, python, refs_dir, builds_dir, scratch, env, now, interpreter
        )
    finally:
        os.umask(old_umask)


def _write_log(scratch: Path, name: str, text: str) -> None:
    safety.write_private_file(scratch / name, text)


def _run_candidate_stages(
    sha: str,
    python: str,
    refs_dir: Path,
    builds_dir: Path,
    scratch: Path,
    env: dict[str, str],
    now: datetime | None,
    interpreter: Path | str | None,
) -> dict[str, Any]:
    stamp = (now or datetime.now(UTC)).astimezone(UTC)
    checks = {
        "clone_commit_matches": False,
        "extraction_metadata_valid": False,
        "extraction_metadata_commit_matches": False,
        "interpreter_matches": False,
        "source_fingerprint_matches": False,
        "selfcheck_passed": False,
        "read_suite_passed": False,
        "sc007_passed": False,
        "sc007_bound_to_candidate": False,
        "source_unchanged_after_run": False,
    }
    sc007: dict[str, Any] = {
        "label": CANDIDATE_LABEL, "ran": False, "ok": False,
        "status": None, "why": None, "bridge_imported": None,
    }
    tests_run = 0
    failed_stage: str | None = None

    problems: list[str] = []
    verified, fingerprint = verify_candidate(
        builds_dir, refs_dir, sha, python, scratch=scratch, env=env, problems=problems,
        interpreter=interpreter,
    )
    _write_log(scratch, "verification.log", "\n".join(problems) + ("\n" if problems else ""))
    checks.update(verified)
    if fingerprint is None:
        failed_stage = "extraction_verification"
    if failed_stage is None:
        try:  # a stale fixture from an earlier run is never evidence
            safety.remove_private_tree(scratch / "selfcheck", scratch)
        except safety.SafetyError as exc:
            _write_log(scratch, "selfcheck.log", f"{exc}\n")
            failed_stage = "selfcheck"
    if failed_stage is None:
        ok, log = run_selfcheck(CANDIDATE_LABEL, scratch / "selfcheck", builds_dir, env)
        _write_log(scratch, "selfcheck.log", log)
        checks["selfcheck_passed"] = selfcheck_really_ran(ok, log, CANDIDATE_LABEL)
        if not checks["selfcheck_passed"]:
            failed_stage = "selfcheck"
    if failed_stage is None:
        passed, tests_run, log = run_read_suite_exact(CANDIDATE_LABEL, builds_dir, scratch, env)
        _write_log(scratch, "read-suite.log", log)
        checks["read_suite_passed"] = passed
        if not passed:
            failed_stage = "read_suite"
    if failed_stage is None:
        raw = unsupported_path_check(
            builds_dir, CANDIDATE_LABEL, scratch,
            expected_fingerprint=fingerprint, env=env, source_sha=sha,
        )
        _write_log(scratch, "sc007.log", raw.get("stderr_tail", ""))
        sc007 = {
            "label": raw.get("label"),
            "ran": True,
            "ok": raw.get("ok") is True,
            "status": _safe_token(raw.get("status")),
            "why": _safe_token(raw.get("why")),
            "bridge_imported": raw.get("bridge_imported")
            if isinstance(raw.get("bridge_imported"), bool) else None,
        }
        # Bound to the candidate: the pristine copy had the verified fingerprint AND the scratch
        # list's provisional row for it listed and supported it (the mutated copy was refused).
        checks["sc007_bound_to_candidate"] = (
            raw.get("label") == CANDIDATE_LABEL
            and raw.get("source_matches_expected") is True
            and raw.get("pristine_supported") is True
        )
        checks["sc007_passed"] = sc007["ok"] and checks["sc007_bound_to_candidate"]
        if not checks["sc007_passed"]:
            failed_stage = "sc007"
    if failed_stage is None:
        # Everything that ran the candidate is done: prove the tracked tree, the bridge
        # fingerprint and the lockfile are still exactly what was verified at the start.
        assert fingerprint is not None
        recheck_problems: list[str] = []
        checks["source_unchanged_after_run"] = recheck_source(
            builds_dir, refs_dir, sha, fingerprint, scratch=scratch, problems=recheck_problems
        )
        _write_log(
            scratch, "post-run-verification.log",
            "\n".join(recheck_problems) + ("\n" if recheck_problems else ""),
        )
        if not checks["source_unchanged_after_run"]:
            failed_stage = "post_run_verification"

    return {
        "format": 1,
        "mode": "candidate",
        "generated_at": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hmp_source": hmp_source_info(),
        "matrix_runtime": {
            "os": platform.system() or None,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
        "candidate": {
            "label": CANDIDATE_LABEL,
            "commit": sha,
            "python_requested": python,
            "fingerprint": fingerprint,
        },
        "runtime_dependencies": runtime_dependency_versions(builds_dir / CANDIDATE_LABEL / "src"),
        "checks": checks,
        "read_suite_tests_run": tests_run,
        "sc007": sc007,
        "failed_stage": failed_stage,
        "candidate_passed": failed_stage is None and all(checks.values()),
        "assurance": ASSURANCE,
    }


def main_candidate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.builds:
        parser.error("--candidate-sha cannot be combined with --builds")
    if args.refs_dir is None:
        parser.error("--candidate-sha requires an explicit --refs-dir")
    if not args.candidate_interpreter:
        parser.error(
            "--candidate-sha requires --candidate-interpreter (the same one given to extract.py). "
            f"{extract_mod.CANDIDATE_INTERPRETER_SETUP}"
        )
    sha = extract_mod.parse_candidate_sha(args.candidate_sha)
    python = extract_mod.parse_python_version(
        CANDIDATE_LABEL,
        extract_mod.DEFAULT_PYTHON if args.candidate_python is None else args.candidate_python,
    )
    builds_dir = args.builds_dir or Path(os.environ.get("HMP_HERMES_BUILDS_DIR", ""))
    if not builds_dir or not builds_dir.is_dir():
        print("run_matrix: --builds-dir (or $HMP_HERMES_BUILDS_DIR) must be an extracted builds "
              "directory (tools/hermes_builds/extract.py)", file=sys.stderr)
        return 2
    try:
        # Everything about placement is decided before anything runs or is created: symlinked
        # or overlapping scratch/build/refs dirs, paths in or around the real home (from the OS
        # account database), and a --json-out that is not a fresh private file inside --out.
        safety.validate_candidate_layout(
            repo_root=REPO_ROOT, builds_dir=builds_dir, refs_dir=args.refs_dir,
            out=args.out, json_out=args.json_out, interpreter=args.candidate_interpreter,
        )
        safety.ensure_private_dir(args.out, "--out")
    except safety.SafetyError as exc:
        raise SystemExit(f"run_matrix: {exc}") from exc

    print(CANDIDATE_WARNING, file=sys.stderr)
    print(f"run_matrix: {CANDIDATE_LABEL} ...", file=sys.stderr)
    report = run_candidate(
        sha, python, args.refs_dir, builds_dir, args.out, interpreter=args.candidate_interpreter
    )
    verdict = "PASSED" if report["candidate_passed"] else f"FAILED ({report['failed_stage']})"
    print(f"run_matrix: {CANDIDATE_LABEL}: {verdict} ({ASSURANCE}); private logs are in the "
          "--out directory", file=sys.stderr)
    text = json.dumps(report, indent=2) + "\n"
    print(text)
    if args.json_out:
        try:
            # The candidate ran as this user since the layout was first validated: check again,
            # immediately before writing, that --json-out is still a plain file in a real --out.
            safety.validate_candidate_layout(
                repo_root=REPO_ROOT, builds_dir=builds_dir, refs_dir=args.refs_dir,
                out=args.out, json_out=args.json_out,
            )
            safety.write_private_file(args.json_out, text)
        except (safety.SafetyError, OSError) as exc:
            raise SystemExit(f"run_matrix: cannot write --json-out: {exc}") from exc
    return 0 if report["candidate_passed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builds-dir", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--builds", default=None, help="comma-separated labels (default: all)")
    parser.add_argument(
        "--json-out", type=Path, default=None,
        help="write the full matrix JSON (with --candidate-sha: a 0600 regular file inside "
        "--out; an existing regular file of yours is replaced, a symlink or hard link is "
        "refused; validated before the run and again right before writing)",
    )
    parser.add_argument(
        "--refs-dir", type=Path, default=None,
        help="override the located _refs dir (the one given to extract.py --refs-dir)",
    )
    parser.add_argument(
        "--candidate-sha", default=None,
        help="ad-hoc: qualify exactly this full 40-hex commit (extracted by extract.py with the "
        "same --candidate-sha) as the fixed label 'candidate' from <--refs-dir>/hermes-agent. "
        "Executes the candidate's code: use an isolated VM, container or user.",
    )
    parser.add_argument(
        "--candidate-python", default=None,
        help='interpreter version the candidate was extracted with ("3.MINOR" or '
        '"3.MINOR.PATCH"; default "3.11"); requires --candidate-sha',
    )
    parser.add_argument(
        "--candidate-interpreter", default=None,
        help="absolute path of the base Python the candidate was extracted with (the same "
        "--candidate-interpreter given to extract.py); required with --candidate-sha. Validated "
        "without being executed, and the venv's bin/python* and pyvenv.cfg are proven to lead "
        "only to it before any of them runs",
    )
    args = parser.parse_args(argv)
    if args.candidate_python is not None and args.candidate_sha is None:
        parser.error("--candidate-python requires --candidate-sha")
    if args.candidate_interpreter is not None and args.candidate_sha is None:
        parser.error("--candidate-interpreter requires --candidate-sha")
    if args.candidate_sha is not None:
        return main_candidate(args, parser)
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
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

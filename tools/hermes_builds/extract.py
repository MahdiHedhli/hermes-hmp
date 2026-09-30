#!/usr/bin/env python3
"""Extract Hermes builds for the compatibility matrix, without touching the `_refs` clones
(T004, `specs/001-connect-and-browse/tasks.md`; research R10).

For each build in `tools/hermes_builds/builds.yaml`, this:
  1. Verifies the ref resolves in the clone *without fetching* (`git cat-file -e`, `git rev-parse`
     — read-only, no network, no ref/HEAD/working-tree mutation).
  2. Snapshots the clone's HEAD, branch, `git status --porcelain` and HEAD reflog entry count
     before and after, and fails loudly if anything differs — the F1 worker rules require the
     clones to end up byte-for-byte where they started, and this makes that a machine-checked
     property of the tool itself rather than something to verify by hand afterwards.
  3. Exports the tree at that ref with `git archive <ref> | tar -x` into a scratch directory.
     `git archive` reads a commit into a tar stream; it never touches the working tree, the
     index, HEAD or any ref, so there is nothing here for step 2 to have changed.
  4. Creates one venv per build (`uv sync --locked --no-python-downloads`, using the extracted
     tree's own `uv.lock` — the same tool and lockfile Hermes itself uses) and does an editable
     install of the extracted tree. The interpreter is the build's optional `python:` value in
     builds.yaml (a *quoted* `"3.MINOR"` or `"3.MINOR.PATCH"` string), default `"3.11"`. An
     interpreter that is not already installed fails the build; uv never downloads one.
  5. Sanity-imports a couple of the package's top-level modules (`agent`, `hermes_cli`) by
     invoking the extracted `.venv/bin/python` directly (no `uv run`, so nothing re-resolves the
     interpreter or lock), with `HERMES_HOME` pointed at an isolated per-build scratch directory.
  6. Only after every step above succeeded, writes `build-metadata.json` (nonsecret: requested
     and actual interpreter version, implementation, GIL-disabled flag, interpreter path, uv
     version, SHA-256 of `uv.lock`, `imports_ok`, and `extraction_ok`) into the per-build
     scratch directory. Each run first removes any stale `build-metadata.json` and
     `hermes_home` for that build, so a leftover file from an earlier run is never evidence of
     this one — its existence is not a qualification signal; read `imports_ok`/`extraction_ok`.

Both uv and the import run with a minimal allowlisted environment (PATH, locale, OS cert
settings) plus scratch HOME/cache/HERMES_HOME. Ambient provider credentials are never passed,
and neither are proxy variables (HTTP(S)_PROXY, ALL_PROXY), private-index settings
(UV_INDEX*, UV_EXTRA_INDEX_URL, PIP_*) or a netrc (HOME is scratch). Builds must therefore
resolve from the committed `uv.lock` without private-index credentials or an inherited proxy.

Every `HERMES_HOME` this tool sets, and any inherited from the caller's environment, is checked
against the real user home directory before use; the tool refuses to run rather than let a
sanity-import (or anything else) read or write `~/.hermes` or any other path under the real home
(F1 worker rules: "Never touch the owner's live Hermes"; SECURITY.md "Isolation of test
environments"). The extraction output directory gets the same check, as a second, independent
guard against generated build trees, venvs or Hermes homes ending up under the real home.

Usage:
    python3 tools/hermes_builds/extract.py --out /path/to/scratch/hermes_builds
    python3 tools/hermes_builds/extract.py --out DIR --builds stock-base,experimental
    python3 tools/hermes_builds/extract.py --out DIR --skip-venv   # extraction + safety checks only

Ad-hoc exact candidate (scratch only; nothing is written to builds.yaml):
    python3 tools/hermes_builds/extract.py --out DIR --refs-dir REFS
        --candidate-sha <full 40 lowercase hex> --candidate-interpreter /ABS/PATH/python3.MINOR
        [--candidate-python 3.MINOR[.PATCH]]
`--candidate-sha` extracts that one commit from `REFS/hermes-agent` (a fixed clone name) under the
fixed label `candidate`; the commit must already exist in the clone (never fetched) and must
resolve to exactly that SHA. It cannot be combined with `--builds`. `--candidate-python` follows
the same rules as builds.yaml `python:` and requires `--candidate-sha`. `--candidate-interpreter`
(required with `--candidate-sha` unless `--skip-venv`) is the absolute path of the base Python the
venv is built on; there is no interpreter discovery for a candidate. There is deliberately no way
to name another label, clone or source path.

The candidate path is hardened beyond the listed builds (`candidate_safety.py`): the real-home
checks use the OS account database, never `$HOME`; every git command runs with `GIT_*` stripped
and replace refs, optional locks, fsmonitor, hooks, every transport and lazy fetching disabled,
after the clone's git dirs are proven not to lead into `~/.hermes` and the clone is proven not to
be a partial (promisor) clone; the tree is written from raw git blobs (never `git archive`) into a
0700 directory and proven byte- and mode-exact against the commit; `--out`/`--refs-dir` symlinks
and overlaps with the repository or the real home are refused.

The candidate also starts from a fresh scratch environment (HOME, caches, XDG_*, TMPDIR, bytecode
prefix and uv cache under `--out/candidate` are deleted first, with the guarded remove helper), and
no interpreter in the real home is ever executed, not even to be queried. Before uv or any Python
runs, `--candidate-interpreter` is proven with lstat/readlink/realpath only
(`safety.validate_base_interpreter`): an absolute path that neither lies in nor links through the
real home, whose real path is a regular executable no one else can write, outside `--out`,
`--refs-dir` and the repository, and not a venv interpreter (no `pyvenv.cfg` beside it). Only then
is it probed (`-I -S`) for its version and base, and `uv sync` gets its real path. After the sync,
and before the venv's interpreter runs, every `.venv/bin/python*` must resolve to that validated
interpreter (or the base it reported, itself validated) and `pyvenv.cfg` must name bases outside
the home (`safety.validate_venv_interpreters`). Use a system Python (in a VM, e.g.
`/usr/bin/python3.14` or `/opt/python/3.14/bin/python3.14`); a uv- or pyenv-managed Python under
the home is refused. `uv` itself is found first and run by absolute path; PATH entries that link
into `~/.hermes` are dropped from the candidate's PATH.

SECURITY: none of this is a sandbox or an attestation. `uv sync` builds and installs the
candidate's project and locked dependencies (build backends and `.pth` files execute), and the
sanity imports run its code, all as the current user. A scratch HOME does not stop that code from
reading the real home, including a live `~/.hermes`, by absolute path; same-user code can read,
write and forge anything that user can, including the metadata this tool writes and the venv the
checks above looked at. A VM, container or separate account protects the host, not this tool's
results from code running as the same user inside it. Run an unreviewed candidate only in one. A
run that succeeds is non-adversarial compatibility evidence only.

Requires PyYAML (`pip install -r tools/requirements.txt`) and, for the venv step, `uv` on PATH.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("extract: PyYAML is required (pip install -r tools/requirements.txt).", file=sys.stderr)
    raise

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import candidate_safety as safety  # noqa: E402 -- after the sys.path bootstrap above

BUILDS_YAML = _THIS_DIR / "builds.yaml"
REPO_ROOT = _THIS_DIR.parents[1]
SANITY_IMPORTS = ("agent", "hermes_cli")
DEFAULT_PYTHON = "3.11"
PYTHON_VERSION_RE = re.compile(r"3\.\d+(\.\d+)?")
CANDIDATE_LABEL = safety.CANDIDATE_LABEL  # fixed: an ad-hoc candidate can never pick its own label
CANDIDATE_CLONE = safety.CANDIDATE_CLONE  # fixed: ... nor its own clone directory under --refs-dir
FULL_SHA_RE = safety.FULL_SHA_RE
METADATA_NAME = "build-metadata.json"
# The only ambient variables a uv / import subprocess may inherit. Everything else — notably
# provider API keys and tokens — is dropped.
ENV_ALLOWLIST = safety.ENV_ALLOWLIST


CANDIDATE_WARNING = (
    "extract: WARNING: --candidate-sha executes the candidate's Python and its locked "
    "dependencies (uv builds, imports) as this user. Environment scrubbing and path checks "
    "are not a sandbox: run an unreviewed candidate only in an isolated VM, container or "
    "user account."
)


@dataclass
class Build:
    label: str
    clone: str
    ref: str
    optional: bool
    python: str = DEFAULT_PYTHON
    exact: bool = False  # `ref` is a full commit SHA that must resolve to itself, not a ref name
    # Candidate only: the explicit absolute base interpreter (`--candidate-interpreter`).
    interpreter: str | None = None


def parse_python_version(label: str, value: object) -> str:
    """Validate a builds.yaml `python:` value. Only *strings* `3.MINOR` / `3.MINOR.PATCH` are
    accepted: an unquoted `3.14` is loaded by YAML as the float 3.14 (and `3.10` as 3.1), so
    floats are rejected rather than guessed at."""
    if not isinstance(value, str) or PYTHON_VERSION_RE.fullmatch(value) is None:
        raise SystemExit(
            f"extract: build {label!r}: invalid python {value!r}; use a quoted string like "
            '"3.14" or "3.14.0" (3.MINOR or 3.MINOR.PATCH)'
        )
    return value


def parse_candidate_sha(value: object) -> str:
    """Validate `--candidate-sha`: exactly 40 lowercase hex characters, nothing else (no ref
    name, abbreviation, uppercase, whitespace or option-like text ever reaches git)."""
    if not isinstance(value, str) or FULL_SHA_RE.fullmatch(value) is None:
        raise SystemExit(
            "extract: invalid --candidate-sha; use a full 40-character lowercase hex SHA"
        )
    return value


def candidate_build(
    sha: object, python: object = DEFAULT_PYTHON, interpreter: str | os.PathLike | None = None
) -> Build:
    """The one ad-hoc build: fixed label and clone, an exact commit, a validated interpreter
    version and (for the venv step) an explicit absolute interpreter path, re-validated right
    before it is used."""
    return Build(
        label=CANDIDATE_LABEL,
        clone=CANDIDATE_CLONE,
        ref=parse_candidate_sha(sha),
        optional=False,
        python=parse_python_version(CANDIDATE_LABEL, python),
        exact=True,
        interpreter=None if interpreter is None else os.fspath(interpreter),
    )


def load_builds() -> list[Build]:
    data = yaml.safe_load(BUILDS_YAML.read_text(encoding="utf-8"))
    if data.get("format") != 1:
        raise SystemExit(f"extract: unsupported builds.yaml format {data.get('format')!r}")
    if any(b["label"] == CANDIDATE_LABEL for b in data["builds"]):
        raise SystemExit(
            f"extract: builds.yaml may not use the reserved label {CANDIDATE_LABEL!r}"
        )
    return [
        Build(
            label=b["label"],
            clone=b["clone"],
            ref=b["ref"],
            optional=bool(b.get("optional", False)),
            python=parse_python_version(b["label"], b.get("python", DEFAULT_PYTHON)),
        )
        for b in data["builds"]
    ]


def find_refs_dir(start: Path) -> Path:
    """Walk up from `start` looking for a `_refs` directory (see builds.yaml's header comment:
    the clones live one level above the repository root, outside version control)."""
    cur = start.resolve()
    for _ in range(6):
        candidate = cur / "_refs"
        if candidate.is_dir():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    raise SystemExit(f"extract: could not find a `_refs` directory by walking up from {start}")


def assert_outside_real_home(path: Path, what: str) -> None:
    """Refuse `path` inside (or containing) the REAL account home -- looked up from the OS
    account database, never from `$HOME`, which the scratch environments below change."""
    try:
        safety.assert_outside_real_home(path, what)
    except safety.SafetyError as exc:
        raise SystemExit(f"extract: {exc}") from exc


def assert_not_live_hermes(path: Path, what: str) -> None:
    """Refuse the owner's live `~/.hermes` (or anything inside it) as a source or destination."""
    try:
        safety.assert_not_live_hermes(path, what, contains_ok=True)
    except safety.SafetyError as exc:
        raise SystemExit(f"extract: {exc}") from exc


def git(clone: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Read-only git against `clone` with a fresh environment (no `GIT_*` inherited) and replace
    refs, optional locks, fsmonitor and hooks disabled (`candidate_safety.run_git`)."""
    return safety.run_git(clone, *args)


def clone_snapshot(clone: Path, *, include_status: bool = True) -> tuple[str, str, str, str]:
    """(HEAD sha, symbolic ref (or ''), porcelain status, HEAD reflog entry count) — used to
    prove the clone is untouched before and after (F1 worker rules: no checkout, no fetch, no
    reflog changes). `include_status=False` (the exact candidate path) replaces `git status`,
    which reads the working tree and can run clean filters, with a digest of every ref; the
    exact path only uses object-database commands (`ls-tree`, `cat-file`, `rev-parse`)."""
    head = git(clone, "rev-parse", "HEAD").stdout.strip()
    branch = git(clone, "symbolic-ref", "-q", "HEAD").stdout.strip()
    if include_status:
        status = git(clone, "status", "--porcelain").stdout
    else:
        status = git(clone, "for-each-ref", "--format=%(objectname) %(refname)").stdout
    reflog = git(clone, "reflog", "show", "HEAD").stdout
    return head, branch, status, str(len(reflog.splitlines()))


def ref_resolves(clone: Path, ref: str) -> str | None:
    """The commit sha `ref` resolves to in `clone`, read-only, or None. Never fetches."""
    result = git(clone, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def extract_tree(clone: Path, commit: str, dest: Path) -> None:
    """`git archive <commit> | tar -x -C dest` — read-only on the clone (archive reads a commit
    into a tar stream; it never touches the working tree, index, HEAD or any ref)."""
    dest.mkdir(parents=True, exist_ok=True)
    git_archive = subprocess.Popen(
        safety.git_argv(clone, "archive", "--format=tar", commit),
        stdout=subprocess.PIPE,
        env=safety.git_env(),
    )
    tar_extract = subprocess.Popen(
        ["tar", "-x", "-C", str(dest)],
        stdin=git_archive.stdout,
        env=safety.minimal_env(strict_path=False),  # listed builds only; unchanged behaviour
    )
    assert git_archive.stdout is not None
    git_archive.stdout.close()  # let tar_extract get SIGPIPE if git_archive dies early
    tar_extract.wait()
    git_archive.wait()
    if git_archive.returncode != 0:
        raise SystemExit(
            f"extract: `git archive` failed for {clone} @ {commit} (exit {git_archive.returncode})"
        )
    if tar_extract.returncode != 0:
        raise SystemExit(
            f"extract: `tar -x` failed extracting into {dest} (exit {tar_extract.returncode})"
        )


def scratch_env(
    build_dir: Path, hermes_home: Path | None = None, *, candidate: bool = False
) -> dict[str, str]:
    """A minimal environment for the uv and sanity-import subprocesses: allowlisted essentials
    from the caller's environment plus scratch HOME and caches (and HERMES_HOME when given).

    `candidate=True` first deletes the previous run's scratch environment (`reset_scratch_env`),
    drops PATH entries that link into `~/.hermes`, and passes on no interpreter directory at all:
    a candidate's interpreter is the explicit `--candidate-interpreter`, never discovered. Listed
    builds keep the caller's PATH entries and, when it exists, the caller's uv-managed interpreter
    directory, as before."""
    install_dir: str | None = None
    try:
        if candidate:
            safety.reset_scratch_env(build_dir, hermes_home)
        # HOME, HERMES_HOME, every XDG_* directory, TMPDIR and the caches are private (0700)
        # scratch directories; nothing but the allowlist is inherited; the real-home checks use
        # the account database, not the HOME being replaced here.
        env = safety.scrubbed_env(build_dir, hermes_home, strict_path=candidate)
        if not candidate:
            # A scratch HOME would hide already-installed uv-managed interpreters; keep
            # discovering them (read-only) from where the caller's uv keeps them. Downloads stay
            # disabled.
            install_dir = os.environ.get("UV_PYTHON_INSTALL_DIR")
            if not install_dir:
                data_home = os.environ.get("XDG_DATA_HOME") or str(
                    safety.real_user_home() / ".local" / "share"
                )
                install_dir = str(Path(data_home) / "uv" / "python")
            if not Path(install_dir).is_dir() or safety.is_within(
                install_dir, safety.live_hermes_home()
            ):
                install_dir = None
        if install_dir:
            env["UV_PYTHON_INSTALL_DIR"] = install_dir
    except safety.SafetyError as exc:
        raise SystemExit(f"extract: {exc}") from exc
    return env


CANDIDATE_INTERPRETER_SETUP = (
    "A candidate needs --candidate-interpreter: the absolute path of a base (non-venv) system or "
    "VM Python outside the real home, e.g. /usr/bin/python3.14 or /opt/python/3.14/bin/python3.14."
)


def probe_base_interpreter(
    interpreter: Path, python: str, env: dict[str, str]
) -> tuple[dict, set[Path]]:
    """Run the candidate's base interpreter ONCE, in isolated mode without `site`, to learn its
    version and base; `interpreter` must be the real path `safety.validate_base_interpreter`
    returned (re-validated here, immediately before it is executed). Returns the reported info and
    the set of real paths a venv built on it may link its `bin/python*` to: the interpreter itself
    plus its reported `executable`/`_base_executable` when those also pass
    `validate_base_interpreter` (a path that fails is simply not allowed). `SafetyError` if the
    version is not `python` or the reported base is in the real home."""
    interpreter = safety.validate_base_interpreter(interpreter)
    proc = subprocess.run(
        [str(interpreter), "-I", "-S", "-c", _INFO_SCRIPT],
        cwd=env.get("TMPDIR"), env=env, capture_output=True, text=True,
    )
    try:
        info = json.loads(proc.stdout) if proc.returncode == 0 else None
    except ValueError:
        info = None
    if not isinstance(info, dict) or not isinstance(info.get("version"), str):
        raise safety.SafetyError(f"refusing: {interpreter} did not report its version")
    version = info["version"]
    if not (version == python or version.startswith(python + ".")):
        raise safety.SafetyError(
            f"refusing: {interpreter} is Python {version}, not the requested {python}"
        )
    reason = check_interpreter_outside_home(info)
    if reason is not None:
        raise safety.SafetyError(reason)
    allowed = {interpreter}
    for key in ("executable", "base_executable"):
        value = info.get(key)
        if isinstance(value, str) and value:
            with contextlib.suppress(safety.SafetyError):  # not proven: simply not allowed
                allowed.add(safety.validate_base_interpreter(value, f"the interpreter's {key}"))
    return info, allowed


def check_interpreter_outside_home(info: dict) -> str | None:
    """`None` if the venv interpreter's base (`sys.base_prefix` / `sys._base_executable`, as
    probed by `interpreter_info`) is outside the real home, else the reason. A missing value is
    a failure: the base cannot be shown to be outside the home."""
    for key in ("base_prefix", "base_executable"):
        value = info.get(key)
        if not isinstance(value, str) or not value:
            return f"the interpreter did not report its {key}"
        try:
            safety.assert_outside_real_home(os.path.realpath(value), f"the interpreter {key}")
        except safety.SafetyError as exc:
            return str(exc)
    return None


def run_uv_sync(
    src_dir: Path, python: str, env: dict[str, str], *, uv: str = "uv"
) -> bool:
    """`uv sync --locked` for `python`. `uv` is a bare command looked up on `env`'s PATH for listed
    builds; the candidate path passes the absolute path `safety.require_uv` found and, as
    `python`, the real path of the validated `--candidate-interpreter` (so uv discovers
    nothing)."""
    if uv == "uv" and shutil.which("uv", path=env.get("PATH")) is None:
        print("extract: `uv` not on PATH, skipping venv setup for", src_dir, file=sys.stderr)
        return False
    result = subprocess.run(
        [uv, "sync", "--locked", "--no-python-downloads", "--python", python],
        cwd=src_dir,
        env=env,
    )
    return result.returncode == 0


def venv_python(src_dir: Path) -> Path:
    return src_dir / ".venv" / "bin" / "python"


_INFO_SCRIPT = (
    "import json, platform, sys, sysconfig; "
    "print(json.dumps({'version': platform.python_version(), "
    "'implementation': platform.python_implementation(), "
    "'gil_disabled': bool(sysconfig.get_config_var('Py_GIL_DISABLED')), "
    "'executable': sys.executable, 'base_prefix': sys.base_prefix, "
    "'base_executable': getattr(sys, '_base_executable', '')}))"
)


def interpreter_info(src_dir: Path, env: dict[str, str]) -> dict | None:
    """The venv interpreter's own version, probed in isolated mode without `site`: no `.pth`
    file, `sitecustomize`, user site or `PYTHON*` variable is processed, so this reports what the
    interpreter is without running anything the candidate's environment provides."""
    proc = subprocess.run(
        [str(venv_python(src_dir)), "-I", "-S", "-c", _INFO_SCRIPT],
        cwd=src_dir, env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        info = json.loads(proc.stdout)
    except ValueError:
        return None
    return info if isinstance(info, dict) and isinstance(info.get("version"), str) else None


def uv_version(env: dict[str, str], *, uv: str = "uv") -> str | None:
    proc = subprocess.run([uv, "--version"], env=env, capture_output=True, text=True)
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def clean_build_state(build_dir: Path) -> None:
    """Remove the previous run's `build-metadata.json` and `hermes_home` so nothing stale can
    look like this run's result. Refuses (rather than deletes) anything that is a symlink or
    resolves into the real home."""
    assert_outside_real_home(build_dir, "build directory")
    if build_dir.is_symlink():
        raise SystemExit(f"extract: refusing: build directory {build_dir} is a symlink")
    for name in (METADATA_NAME, "hermes_home"):
        path = build_dir / name
        if path.is_symlink():
            raise SystemExit(f"extract: refusing to remove symlink {path}")
        if not path.exists():
            continue
        assert_outside_real_home(path, name)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def write_build_metadata(
    build: Build, commit: str, src_dir: Path, build_dir: Path, info: dict, uv: str | None,
    imports: dict[str, bool], base_interpreter: Path | None = None,
) -> Path:
    """Nonsecret record of what actually ran, for a later matrix report. Only called after
    extraction, sync and every sanity import succeeded. Written with `write_private_file` (a NEW
    0600 regular file; a symlink or anything else planted at the path -- for instance by the
    candidate's own build or import code -- is refused, never followed). The file is a record of
    what this tool saw, not a proof: same-user code can rewrite it."""
    metadata = {
        "label": build.label,
        "ref": build.ref,
        "commit": commit,
        "python_requested": build.python,
        "python_version": info["version"],
        "python_implementation": info.get("implementation"),
        "python_gil_disabled": info.get("gil_disabled"),
        "python_executable": info.get("executable"),
        "uv_version": uv,
        "uv_lock_sha256": hashlib.sha256((src_dir / "uv.lock").read_bytes()).hexdigest(),
        "imports": dict(imports),
        "imports_ok": all(imports.values()),
        "extraction_ok": True,
    }
    if base_interpreter is not None:  # the candidate: the validated `--candidate-interpreter`
        metadata["python_base_interpreter"] = str(base_interpreter)
    try:
        return safety.write_private_file(
            build_dir / METADATA_NAME, json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )
    except (safety.SafetyError, OSError) as exc:
        raise SystemExit(f"extract: cannot write {METADATA_NAME}: {exc}") from exc


def sanity_import(src_dir: Path, env: dict[str, str]) -> dict[str, bool]:
    """Import each module with the extracted venv's own interpreter (no `uv run`, so neither
    the interpreter nor the lock can be re-resolved). `env` comes from `scratch_env`, which has
    already checked HERMES_HOME against the real home."""
    results: dict[str, bool] = {}
    for module in SANITY_IMPORTS:
        proc = subprocess.run(
            [str(venv_python(src_dir)), "-c", f"import {module}"],
            cwd=src_dir,
            env=env,
            capture_output=True, text=True,
        )
        results[module] = proc.returncode == 0
        if proc.returncode != 0:
            print(
                f"extract: `import {module}` failed in {src_dir}:\n{proc.stderr}", file=sys.stderr
            )
    return results


def process_build(build: Build, refs_dir: Path, out_root: Path, skip_venv: bool) -> bool:
    if not build.exact:
        return _process_build(build, refs_dir, out_root, skip_venv)
    # The exact candidate: everything created (and everything the candidate's own uv/Python
    # creates) is private to this user.
    old_umask = os.umask(0o077)
    try:
        return _process_build(build, refs_dir, out_root, skip_venv)
    finally:
        os.umask(old_umask)


def _process_build(build: Build, refs_dir: Path, out_root: Path, skip_venv: bool) -> bool:
    build_dir = out_root / build.label
    if build.exact:
        try:
            safety.ensure_private_dir(build_dir, "build directory")
        except safety.SafetyError as exc:
            raise SystemExit(f"extract: {exc}") from exc
    clean_build_state(build_dir)
    clone = refs_dir / build.clone
    if build.exact and (clone / ".git").exists():
        try:  # the clone and its git dirs must not lead into the live ~/.hermes
            safety.resolve_clone_git_dirs(clone)
        except safety.SafetyError as exc:
            raise SystemExit(f"extract: {exc}") from exc
    if not (clone / ".git").exists():
        msg = f"extract: no git clone at {clone}"
        if build.optional:
            print(f"{msg}; skipping optional build {build.label!r}.")
            return True
        raise SystemExit(msg)

    commit = ref_resolves(clone, build.ref)
    if commit is None:
        msg = (
            f"extract: {build.ref!r} does not resolve locally in {clone} "
            "(never fetched to make it)"
        )
        if build.optional:
            print(f"{msg}; skipping optional build {build.label!r}.")
            return True
        raise SystemExit(msg)
    if build.exact and commit != build.ref:
        raise SystemExit(
            f"extract: {build.ref!r} in {clone} resolves to a different object "
            f"({commit!r}); refusing to extract anything but that exact commit"
        )

    before = clone_snapshot(clone, include_status=not build.exact)
    src_dir = build_dir / "src"
    if src_dir.is_symlink():
        raise SystemExit(f"extract: refusing: source directory {src_dir} is a symlink")
    if src_dir.exists():
        shutil.rmtree(src_dir)
    if build.exact:
        # Raw blobs straight from the tree object (no `git archive`: it applies `export-ignore`,
        # `export-subst` and smudge filters), then proven to be exactly the commit.
        try:
            entries = safety.write_tree_exact(clone, commit, src_dir)
            problems = safety.verify_tree_matches_commit(src_dir, entries)
        except safety.SafetyError as exc:
            raise SystemExit(f"extract: {exc}") from exc
        if problems:
            raise SystemExit(
                f"extract: the extracted tree is not exactly commit {commit}: {problems[0]}"
            )
    else:
        extract_tree(clone, commit, src_dir)
    after = clone_snapshot(clone, include_status=not build.exact)

    if before != after:
        raise SystemExit(
            f"extract: clone {clone} changed during extraction of {build.label!r}!\n"
            f"  before: {before}\n  after:  {after}\n"
            "This should be impossible (git archive is read-only) — treat the clone as "
            "possibly modified and stop."
        )

    print(f"extract: {build.label} ({build.ref} -> {commit[:10]}) extracted to {src_dir}")

    if skip_venv:
        return True

    uv = "uv"
    if build.exact:
        try:  # found (and later run) by absolute path: its directory may not survive the scrub
            uv = safety.require_uv()
        except safety.SafetyError as exc:
            raise SystemExit(f"extract: {exc}") from exc
    env = scratch_env(build_dir, build_dir / "hermes_home", candidate=build.exact)
    interpreter = build.python
    base: Path | None = None
    allowed: set[Path] = set()
    if build.exact:
        # No discovery: only the explicit interpreter, proven (without executing anything) not
        # to be in or link through the real home, is probed and handed to uv by real path.
        if build.interpreter is None:
            raise SystemExit(f"extract: {CANDIDATE_INTERPRETER_SETUP}")
        try:
            base = safety.validate_base_interpreter(build.interpreter, "--candidate-interpreter")
            _, allowed = probe_base_interpreter(base, build.python, env)
        except (safety.SafetyError, OSError) as exc:
            raise SystemExit(f"extract: {exc} {CANDIDATE_INTERPRETER_SETUP}") from exc
        interpreter = str(base)
    ok = run_uv_sync(src_dir, interpreter, env, uv=uv)
    if not ok:
        print(f"extract: `uv sync` failed for {build.label}", file=sys.stderr)
        return False

    if build.exact:
        # `uv sync` ran the candidate's build backends: prove, before the venv's interpreter is
        # executed, that every `bin/python*` still resolves to the validated interpreter and that
        # `pyvenv.cfg` takes its base from outside the home.
        try:
            safety.validate_venv_interpreters(src_dir / safety.VENV_DIRNAME, allowed)
        except safety.SafetyError as exc:
            print(f"extract: {build.label}: {exc}", file=sys.stderr)
            return False
    info = interpreter_info(src_dir, env)
    if build.exact and info is not None:
        outside = check_interpreter_outside_home(info)
        if outside is not None:
            print(
                f"extract: {build.label}: refusing: {outside} A candidate needs a system or VM "
                "Python outside the real home.",
                file=sys.stderr,
            )
            return False
    actual = info["version"] if info else None
    if actual is None or not (actual == build.python or actual.startswith(build.python + ".")):
        print(
            f"extract: {build.label}: venv interpreter {actual!r} does not match requested "
            f"python {build.python!r}",
            file=sys.stderr,
        )
        return False

    results = sanity_import(src_dir, env)
    print(f"extract: {build.label} sanity imports: {results}")
    if not all(results.values()):
        return False
    write_build_metadata(
        build, commit, src_dir, build_dir, info, uv_version(env, uv=uv), results, base
    )
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="scratch output directory")
    parser.add_argument(
        "--refs-dir", type=Path, default=None, help="override the located _refs dir"
    )
    parser.add_argument(
        "--builds", default=None, help="comma-separated labels to run (default: all)"
    )
    parser.add_argument(
        "--skip-venv", action="store_true", help="extract only; skip uv sync + import"
    )
    parser.add_argument(
        "--candidate-sha", default=None,
        help="ad-hoc: extract this exact full 40-hex commit from <--refs-dir>/hermes-agent as the "
        "fixed label 'candidate' (requires --refs-dir; not combinable with --builds)",
    )
    parser.add_argument(
        "--candidate-python", default=None,
        help=f'interpreter version for the candidate ("3.MINOR" or "3.MINOR.PATCH"; default '
        f'"{DEFAULT_PYTHON}"); requires --candidate-sha',
    )
    parser.add_argument(
        "--candidate-interpreter", default=None,
        help="absolute path of the base (non-venv) Python the candidate's venv is built on, "
        "outside the real home; required with --candidate-sha unless --skip-venv. Validated "
        "without being executed before uv or Python runs; nothing is discovered",
    )
    args = parser.parse_args(argv)

    if args.candidate_python is not None and args.candidate_sha is None:
        parser.error("--candidate-python requires --candidate-sha")
    if args.candidate_interpreter is not None and args.candidate_sha is None:
        parser.error("--candidate-interpreter requires --candidate-sha")
    if args.candidate_sha is not None and args.builds:
        parser.error("--candidate-sha cannot be combined with --builds")
    if args.candidate_sha is not None and args.refs_dir is None:
        parser.error("--candidate-sha requires an explicit --refs-dir")
    if args.candidate_sha is not None and not args.skip_venv and not args.candidate_interpreter:
        parser.error(
            f"--candidate-sha requires --candidate-interpreter. {CANDIDATE_INTERPRETER_SETUP}"
        )

    out_root = args.out.resolve()
    assert_outside_real_home(out_root, "--out")
    if args.candidate_sha is not None:
        assert_not_live_hermes(args.refs_dir, "--refs-dir")
        python = DEFAULT_PYTHON if args.candidate_python is None else args.candidate_python
        builds = [candidate_build(args.candidate_sha, python, args.candidate_interpreter)]
        try:
            # Symlinked or overlapping --out/--refs-dir/repository, paths in or around the real
            # home, an interpreter in or linking through the home: refused before anything is
            # created or executed.
            safety.validate_candidate_layout(
                repo_root=REPO_ROOT, builds_dir=args.out, refs_dir=args.refs_dir,
                interpreter=args.candidate_interpreter,
            )
            safety.ensure_private_dir(out_root, "--out")
        except safety.SafetyError as exc:
            raise SystemExit(f"extract: {exc}") from exc
        print(CANDIDATE_WARNING, file=sys.stderr)
    out_root.mkdir(parents=True, exist_ok=True)

    refs_dir = args.refs_dir or find_refs_dir(Path(__file__).resolve().parent)
    if args.candidate_sha is None:
        builds = load_builds()
    if args.builds:
        wanted = set(args.builds.split(","))
        builds = [b for b in builds if b.label in wanted]

    ok = True
    for b in builds:
        if not process_build(b, refs_dir, out_root, args.skip_venv):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Shared helpers for the F1 fixture tools (T060 `build_fixture.py`, T061 `selfcheck.py`, T062
`mutate.py`). Pure Python: no Hermes import lives here. Hermes/`hmp_plugin`-aware work always runs
in a subprocess under the *target build's own* venv python (see `fixture_seed.py` and
`fixture_pairing_cli.py`) — this module only manages paths, safety checks, the manifest and
process plumbing.

Contract: specs/001-connect-and-browse/contracts/fixture-format.md
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
SERVER_DIR = REPO_ROOT / "server"
BUILDS_YAML = REPO_ROOT / "tools" / "hermes_builds" / "builds.yaml"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "fixtures" / "f1" / "instances.yaml"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "fixtures" / "f1" / "SCHEMA.json"

if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import manifest as manifest_mod  # noqa: E402 -- after sys.path bootstrap, matching tests/conftest.py

# The shared isolation helpers live next to extract.py (which the fixture tools already import).
_HERMES_BUILDS_TOOL_DIR = REPO_ROOT / "tools" / "hermes_builds"
if str(_HERMES_BUILDS_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_HERMES_BUILDS_TOOL_DIR))

import candidate_safety as safety  # noqa: E402 -- after the sys.path bootstrap above

CANDIDATE_LABEL = safety.CANDIDATE_LABEL
# The explicit opt-in every fixture tool requires before it will start the ad-hoc `candidate`
# build. `tools/compat/run_matrix.py --candidate-sha` sets it for its own subprocesses only AFTER
# it has proven the extracted source is exactly the requested commit; nothing in these tools
# verifies that. Run directly, `build_fixture.py`/`mutate.py`/`selfcheck.py --build candidate`
# therefore execute an UNVERIFIED tree: they are unsafe developer tools, and setting the variable
# by hand is a statement that you have checked the tree yourself, in an isolated VM.
CANDIDATE_OPT_IN_ENV = "HMP_ENABLE_CANDIDATE_BUILD"
# A build label is one lowercase path component (builds.yaml's labels, and `candidate`): no
# separator, no `.`/`..`, no uppercase (a case variant of `candidate` names the same directory on a
# case-insensitive filesystem), no whitespace.
BUILD_LABEL_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_METADATA_NAME = "build-metadata.json"  # tools/hermes_builds/extract.py METADATA_NAME
_MAX_METADATA_BYTES = 1 << 20


class FixtureSafetyError(RuntimeError):
    """A path resolved inside the real user home, or another isolation invariant was violated."""


def assert_outside_real_home(path: Path, what: str) -> None:
    """Refuse any path (a `HERMES_HOME`, a binding/XDG root, a build output directory, ...) that
    resolves inside the real user home (F1 worker rules: "Never touch the owner's live Hermes";
    SECURITY.md "Isolation of test environments"). The home is the account database's, NOT
    `$HOME`: candidate processes run with `HOME` pointed at scratch, and a check against that
    would pass for the real home. Mirrors `tools/hermes_builds/extract.py`."""
    try:
        safety.assert_outside_real_home(path, what)
    except safety.SafetyError as exc:
        raise FixtureSafetyError(str(exc)) from exc


def assert_never_real_hermes_dir(path: Path, what: str) -> None:
    """Extra guard: never `~/.hermes` itself, even if some future real home layout changes and the
    generic `assert_outside_real_home` check above would somehow miss it."""
    real_hermes = safety.live_hermes_home()
    p = Path(path).resolve()
    if safety.overlaps(p, real_hermes):
        raise FixtureSafetyError(
            f"refusing: {what} ({p}) touches the real ~/.hermes ({real_hermes})."
        )


def load_and_validate_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH, schema_path: Path = DEFAULT_SCHEMA_PATH
) -> dict[str, Any]:
    manifest = manifest_mod.load_manifest(manifest_path)
    schema = manifest_mod.load_schema(schema_path)
    manifest_mod.validate_or_raise(manifest, schema)
    return manifest


@dataclass(frozen=True)
class BuildInfo:
    label: str
    src_dir: Path
    venv_python: Path


def check_build_label(label: object) -> str:
    """`label`, if it is a well-formed build label (`BUILD_LABEL_RE`); else `FixtureSafetyError`.
    `candidate/`, `./candidate`, `Candidate`, `../x/candidate` and the like never reach a path."""
    if not isinstance(label, str) or BUILD_LABEL_RE.fullmatch(label) is None:
        raise FixtureSafetyError(
            f"refusing: malformed build label {label!r} (one lowercase path component: letters, "
            "digits, '.', '_' or '-', e.g. stock-base or candidate)"
        )
    return label


def is_candidate_tree(builds_dir: Path | str, label: str) -> bool:
    """Whether `<builds_dir>/<label>` IS the ad-hoc candidate's build tree, decided by what the
    path leads to rather than how it is spelled: the exact label; or the build directory, its
    `src` or `src/.venv` resolving into (or being the same file as) `<builds_dir>/candidate`, or
    to a directory named `candidate` in any case (a link to another builds directory's candidate,
    a case alias); or its extraction metadata naming the `candidate` label (a renamed copy).
    Reads only. A metadata file that is a symlink, FIFO or oversized is a `FixtureSafetyError`."""
    label = check_build_label(label)
    if label == CANDIDATE_LABEL:
        return True
    base = Path(os.path.abspath(builds_dir))
    candidate_dir = base / CANDIDATE_LABEL
    build_dir = base / label
    levels = ((build_dir, 0), (build_dir / "src", 1), (build_dir / "src" / ".venv", 2))
    for path, depth in levels:
        if not os.path.lexists(path):
            continue
        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError):  # a link loop: cannot be shown not to be the candidate
            return True
        build_level = resolved.parents[depth - 1] if depth else resolved
        if build_level.name.casefold() == CANDIDATE_LABEL:
            return True
        if os.path.lexists(candidate_dir) and safety.is_within(resolved, candidate_dir):
            return True
    if not build_dir.is_dir():
        return False
    try:
        raw = safety.read_regular_file(build_dir.resolve() / _METADATA_NAME, _MAX_METADATA_BYTES)
    except safety.SafetyError as exc:
        raise FixtureSafetyError(f"build {label!r} metadata: {exc}") from exc
    if raw is not None:
        try:
            recorded = json.loads(raw.decode("utf-8")).get("label")
        except (UnicodeDecodeError, ValueError, AttributeError):
            recorded = None
        if isinstance(recorded, str) and recorded.casefold() == CANDIDATE_LABEL:
            return True
    return False


def classify_build(builds_dir: Path | str, label: str) -> bool:
    """`True` for the ad-hoc candidate named by its exact label, `False` for any other build;
    `FixtureSafetyError` for a malformed label or for ANY other name that leads to the candidate's
    tree (`is_candidate_tree`) -- the candidate is only ever reached as exactly `candidate`, so it
    always gets the opt-in gate and the scrubbed environment."""
    if is_candidate_tree(builds_dir, label):
        if label != CANDIDATE_LABEL:
            raise FixtureSafetyError(
                f"refusing: build label {label!r} leads to the ad-hoc `candidate` build tree; the "
                "candidate is only run as exactly `--build candidate` (opt-in and isolation apply)"
            )
        return True
    return False


def resolve_build(builds_dir: Path, label: str) -> BuildInfo:
    """Locate a T004 extraction: `<builds_dir>/<label>/src` with its own `.venv`. Never extracts
    anything itself — T004's `extract.py` is the only tool that touches the `_refs` clones.

    The candidate's tree is resolved only by its exact label (`classify_build`), only through the
    opt-in gate, only once `enable_candidate_isolation` has scrubbed this process's children's
    environment, never through a symlinked builds/build/src directory, and only if its venv's
    `bin/python*` and `pyvenv.cfg` lead nowhere into the real home (checked without executing)."""
    is_candidate = classify_build(builds_dir, label)
    if is_candidate:
        require_candidate_gate("resolving the `candidate` build")
        if _CANDIDATE_ENV_ROOT is None:
            raise FixtureSafetyError(
                "refusing: the `candidate` build is only resolved after "
                "enable_candidate_isolation (it never runs with the caller's HOME or environment)"
            )
        for part in (Path(builds_dir), Path(builds_dir) / label, Path(builds_dir) / label / "src"):
            if Path(os.path.abspath(part)).is_symlink():
                raise FixtureSafetyError(f"refusing: {part} is a symlink")
    src_dir = (Path(builds_dir) / label / "src").resolve()
    if not src_dir.is_dir():
        raise FixtureSafetyError(
            f"no extracted build {label!r} at {src_dir} — run tools/hermes_builds/extract.py "
            f"--out {builds_dir} --builds {label} first (T004)"
        )
    venv_python = src_dir / ".venv" / "bin" / "python3"
    if not venv_python.exists():
        raise FixtureSafetyError(
            f"no venv python at {venv_python} — run tools/hermes_builds/extract.py "
            f"--out {builds_dir} --builds {label} (without --skip-venv) first"
        )
    if is_candidate:
        try:
            safety.validate_venv_interpreters(src_dir / safety.VENV_DIRNAME)
        except safety.SafetyError as exc:
            raise FixtureSafetyError(str(exc)) from exc
    return BuildInfo(label=label, src_dir=src_dir, venv_python=venv_python)


def find_free_port() -> int:
    """A loopback TCP port free at the moment of the check (best-effort; classic bind-to-0 trick,
    matching `server/tests/unit/test_adapter.py`'s `_free_port`)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass(frozen=True)
class InstancePaths:
    """Every isolated location for one fixture instance. `home` is the instance's `HERMES_HOME`
    (root, never a named profile — HMP identity binds only at the root per identity.py's ID-2
    ruling). `xdg_state` is the instance's *binding root*: identity.py's `k_grace` and
    `binding.json` custody live OUTSIDE every Hermes home by design (research R16, CS-13), and
    their real default (`$XDG_STATE_HOME` / `~/.local/state/hermes-hmp`) is under the real user
    home — every fixture caller MUST override it explicitly with this path, on every process that
    touches HMP identity (the live gateway, `fixture_seed.py`, `fixture_pairing_cli.py`), never by
    relying on an inherited `XDG_STATE_HOME` env var."""

    home: Path
    xdg_state: Path
    out_dir: Path  # `--out` itself — where run descriptors, logs and metadata live


def instance_paths(out_dir: Path, instance_key: str) -> InstancePaths:
    """One `--out` directory holds exactly one build's fixture (`server/tests/integration/
    test_reads_fixture.py`'s interface: `build_fixture.py --build <label> --out <dir>`, re-served
    and mutated against that SAME `<dir>` with no build label in the path). Which build produced
    it is recorded in `fixture_meta.json` (`write_fixture_meta`), not encoded in the path."""
    resolved = Path(out_dir).resolve()
    return InstancePaths(
        home=resolved / "homes" / instance_key,
        xdg_state=resolved / "xdg_state" / instance_key,
        out_dir=resolved,
    )


def assert_instance_paths_safe(paths: InstancePaths) -> None:
    assert_outside_real_home(paths.home, "HERMES_HOME")
    assert_outside_real_home(paths.xdg_state, "the identity binding root (XDG_STATE_HOME)")
    assert_never_real_hermes_dir(paths.home, "HERMES_HOME")


# `identity.py`'s PLUGIN_DATA_PARTS ("plugin-data", "hmp", "instance"). `Store.migrate()` opens
# its sqlite file at this directory's PARENT and does not create it (neither does
# `identity.resolve_custody()`, which only computes the path and writes nothing) -- nobody in
# `server/hmp_plugin` currently creates this directory before first use. Pre-creating it here,
# from fixture tooling only, is a workaround for that gap; see this task's final report.
_PLUGIN_DATA_RELATIVE = ("plugin-data", "hmp", "instance")


def ensure_plugin_data_dir(paths: InstancePaths) -> None:
    assert_instance_paths_safe(paths)
    Path(paths.home, *_PLUGIN_DATA_RELATIVE).mkdir(parents=True, exist_ok=True)


_CANDIDATE_ENV_ROOT: Path | None = None


def require_candidate_gate(tool: str) -> None:
    """Refuse to start the ad-hoc `candidate` unless the explicit opt-in is set. This is a gate,
    not a verification: only `run_matrix.py --candidate-sha` proves the tree is the commit before
    it sets the variable. Used directly, this is an unsafe developer tool (see
    `CANDIDATE_OPT_IN_ENV`)."""
    if os.environ.get(CANDIDATE_OPT_IN_ENV) != "1":
        raise FixtureSafetyError(
            f"refusing: {tool} would execute the ad-hoc `candidate` build, whose extracted tree "
            "nothing here has verified. Qualify it with `tools/compat/run_matrix.py "
            "--candidate-sha`, which verifies first. Running this tool directly on a candidate is "
            f"an unsafe developer path: set {CANDIDATE_OPT_IN_ENV}=1 only if you have checked the "
            "tree yourself and are inside an isolated VM, container or user account."
        )


def enable_candidate_isolation(out_dir: Path, *, fresh: bool = False) -> None:
    """Called by every fixture entry point (`build_fixture.py`, `mutate.py`) when the build under
    test is the ad-hoc `candidate`, whoever launched it, and only through the opt-in gate
    (`require_candidate_gate`). From here on `clean_hermes_env` ignores the caller's environment
    entirely (no credentials, proxies, real HOME or `GIT_*`/`PYTHON*` variables) and every process
    this tool starts -- the gateway, the seed and pairing scripts, `uv` -- gets a scrubbed
    environment with HOME, XDG_* and TMPDIR in private scratch under `<out>/_candidate_env`. Files
    and directories are created 0600/0700. This redirects where well-behaved code looks; it does
    not confine the candidate, which can still read the real home by absolute path.

    `fresh=True` (the entry point that BUILDS the fixture) first deletes the previous run's scratch
    environment (stale bytecode, caches, HOME); `mutate.py` re-enters an existing fixture whose
    gateway may still be running from that environment, so it must not."""
    global _CANDIDATE_ENV_ROOT
    require_candidate_gate("the fixture tools")
    root = Path(os.path.abspath(out_dir)) / "_candidate_env"
    try:
        assert_outside_real_home(out_dir, "--out")
        safety.ensure_private_dir(out_dir, "--out")
        if fresh:
            safety.reset_scratch_env(root)
        safety.scrubbed_env(root)  # validates against the real home, creates the 0700 dirs
    except safety.SafetyError as exc:
        raise FixtureSafetyError(str(exc)) from exc
    _CANDIDATE_ENV_ROOT = root
    os.umask(0o077)


def uv_command() -> str:
    """`uv` for a listed build (a bare command, as before). For the candidate: the absolute path
    found before the PATH scrub, because the scrubbed PATH drops directories that link into
    `~/.hermes` -- which may be where `uv` lives."""
    if _CANDIDATE_ENV_ROOT is None:
        return "uv"
    try:
        return safety.require_uv()
    except safety.SafetyError as exc:
        raise FixtureSafetyError(str(exc)) from exc


def clean_hermes_env(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    """A minimal, isolated environment for any subprocess that must not see the caller's own
    Hermes/XDG state (fixture-format.md rule 1: "unsets every inherited HERMES_* variable").
    Callers add `HERMES_HOME` / `XDG_STATE_HOME` (already safety-checked) via `extra`."""
    if _CANDIDATE_ENV_ROOT is not None:
        try:
            base = safety.scrubbed_env(_CANDIDATE_ENV_ROOT)
        except safety.SafetyError as exc:
            raise FixtureSafetyError(str(exc)) from exc
    else:
        base = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("HERMES_", "XDG_", "GIT_"))
        }
        # A minimal PATH is enough for `git`/`uv`/the venv's own interpreter; never let a stray
        # HERMES_* var survive through PATH-adjacent tooling.
        base.setdefault("PATH", os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"))
        base.setdefault("HOME", os.environ.get("HOME", str(safety.real_user_home())))
    if extra:
        base.update(extra)
    return base


def run_hermes_cli(
    build: BuildInfo,
    paths: InstancePaths,
    *args: str,
    timeout: float = 120.0,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run `hermes <args>` from `build`'s venv against the isolated instance `paths`."""
    assert_instance_paths_safe(paths)
    hermes_bin = build.venv_python.parent / "hermes"
    env = clean_hermes_env(
        extra={"HERMES_HOME": str(paths.home), "XDG_STATE_HOME": str(paths.xdg_state)}
    )
    result = subprocess.run(
        [str(hermes_bin), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"`hermes {' '.join(args)}` failed (exit {result.returncode}) for build "
            f"{build.label!r} home {paths.home}:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def run_seed_script(
    build: BuildInfo,
    script: Path,
    *args: str,
    timeout: float = 120.0,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a `hmp_plugin`-aware helper script (`fixture_seed.py`, `fixture_pairing_cli.py`) under
    `build`'s own venv python, with `SERVER_DIR` on `PYTHONPATH` so `import hmp_plugin...`
    resolves. These scripts take their own `--home`/`--xdg-state` flags and never rely on an
    inherited environment (they may be re-invoked later by Dart's `Process.run`, which does not
    forward a custom environment)."""
    env = clean_hermes_env()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SERVER_DIR) + (os.pathsep + existing_pp if existing_pp else "")
    result = subprocess.run(
        [str(build.venv_python), str(script), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"{script.name} {' '.join(args)} failed (exit {result.returncode}) for build "
            f"{build.label!r}:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def ensure_runtime_deps(build: BuildInfo, *, timeout: float = 300.0) -> None:
    """`--serve` needs `aiohttp` (the HMP listener) and `qrcode` (`hermes hmp pair offer`'s
    renderer, in case anything ever reaches it) inside the build's own venv; `cryptography` and
    `pyyaml` are already Hermes dependencies. Installed via `uv` (T004 uses the same tool), never
    `pip` (uv-managed venvs ship without pip). Idempotent — `uv pip install` is a no-op when the
    package is already the requested version.

    These three packages are NOT pinned and NOT in the candidate's lockfile: they resolve from the
    package index at install time, so a fixture run is not reproducible from the lockfile alone.
    `tools/compat/run_matrix.py --candidate-sha` reports the versions that ended up installed
    (`runtime_dependencies`) instead of claiming they are locked."""
    subprocess.run(
        [
            uv_command(), "pip", "install", "--python", str(build.venv_python),
            "aiohttp", "cryptography", "qrcode",
        ],
        env=clean_hermes_env(),
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

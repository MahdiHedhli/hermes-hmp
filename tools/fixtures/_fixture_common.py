"""Shared helpers for the F1 fixture tools (T060 `build_fixture.py`, T061 `selfcheck.py`, T062
`mutate.py`). Pure Python: no Hermes import lives here. Hermes/`hmp_plugin`-aware work always runs
in a subprocess under the *target build's own* venv python (see `fixture_seed.py` and
`fixture_pairing_cli.py`) — this module only manages paths, safety checks, the manifest and
process plumbing.

Contract: specs/001-connect-and-browse/contracts/fixture-format.md
"""

from __future__ import annotations

import os
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


class FixtureSafetyError(RuntimeError):
    """A path resolved inside the real user home, or another isolation invariant was violated."""


def assert_outside_real_home(path: Path, what: str) -> None:
    """Refuse any path (a `HERMES_HOME`, a binding/XDG root, a build output directory, ...) that
    resolves inside the real user home (F1 worker rules: "Never touch the owner's live Hermes";
    SECURITY.md "Isolation of test environments"). Mirrors `tools/hermes_builds/extract.py`."""
    home = Path.home().resolve()
    p = Path(path).resolve()
    if p == home or home in p.parents:
        raise FixtureSafetyError(
            f"refusing: {what} ({p}) is inside the real user home ({home}). "
            "Use a scratch/tmp directory instead."
        )


def assert_never_real_hermes_dir(path: Path, what: str) -> None:
    """Extra guard: never `~/.hermes` itself, even if some future real home layout changes and the
    generic `assert_outside_real_home` check above would somehow miss it."""
    real_hermes = (Path.home() / ".hermes").resolve()
    p = Path(path).resolve()
    if p == real_hermes or real_hermes in p.parents or p in real_hermes.parents:
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


def resolve_build(builds_dir: Path, label: str) -> BuildInfo:
    """Locate a T004 extraction: `<builds_dir>/<label>/src` with its own `.venv`. Never extracts
    anything itself — T004's `extract.py` is the only tool that touches the `_refs` clones."""
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


def clean_hermes_env(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    """A minimal, isolated environment for any subprocess that must not see the caller's own
    Hermes/XDG state (fixture-format.md rule 1: "unsets every inherited HERMES_* variable").
    Callers add `HERMES_HOME` / `XDG_STATE_HOME` (already safety-checked) via `extra`."""
    base = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("HERMES_") and not k.startswith("XDG_")
    }
    # A minimal PATH is enough for `git`/`uv`/the venv's own interpreter; never let a stray
    # HERMES_* var survive through PATH-adjacent tooling.
    base.setdefault("PATH", os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"))
    base.setdefault("HOME", os.environ.get("HOME", str(Path.home())))
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
    package is already the requested version."""
    subprocess.run(
        [
            "uv", "pip", "install", "--python", str(build.venv_python),
            "aiohttp", "cryptography", "qrcode",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

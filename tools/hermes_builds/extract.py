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

Requires PyYAML (`pip install -r tools/requirements.txt`) and, for the venv step, `uv` on PATH.
"""

from __future__ import annotations

import argparse
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

BUILDS_YAML = Path(__file__).resolve().parent / "builds.yaml"
SANITY_IMPORTS = ("agent", "hermes_cli")
DEFAULT_PYTHON = "3.11"
PYTHON_VERSION_RE = re.compile(r"3\.\d+(\.\d+)?")
METADATA_NAME = "build-metadata.json"
# The only ambient variables a uv / import subprocess may inherit. Everything else — notably
# provider API keys and tokens — is dropped.
ENV_ALLOWLIST = ("PATH", "LANG", "LANGUAGE", "TERM", "SSL_CERT_FILE", "SSL_CERT_DIR")


@dataclass
class Build:
    label: str
    clone: str
    ref: str
    optional: bool
    python: str = DEFAULT_PYTHON


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


def load_builds() -> list[Build]:
    data = yaml.safe_load(BUILDS_YAML.read_text(encoding="utf-8"))
    if data.get("format") != 1:
        raise SystemExit(f"extract: unsupported builds.yaml format {data.get('format')!r}")
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
    home = Path.home().resolve()
    p = path.resolve()
    if p == home or home in p.parents:
        raise SystemExit(
            f"extract: refusing: {what} ({p}) is inside the real user home ({home}). "
            "Use a scratch/tmp directory instead."
        )


def git(clone: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(clone), *args], capture_output=True, text=True
    )


def clone_snapshot(clone: Path) -> tuple[str, str, str, str]:
    """(HEAD sha, symbolic ref (or ''), porcelain status, HEAD reflog entry count) — used to
    prove the clone is untouched before and after (F1 worker rules: no checkout, no fetch, no
    reflog changes)."""
    head = git(clone, "rev-parse", "HEAD").stdout.strip()
    branch = git(clone, "symbolic-ref", "-q", "HEAD").stdout.strip()
    status = git(clone, "status", "--porcelain").stdout
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
        ["git", "-C", str(clone), "archive", "--format=tar", commit],
        stdout=subprocess.PIPE,
    )
    tar_extract = subprocess.Popen(["tar", "-x", "-C", str(dest)], stdin=git_archive.stdout)
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


def scratch_env(build_dir: Path, hermes_home: Path | None = None) -> dict[str, str]:
    """A minimal environment for the uv and sanity-import subprocesses: allowlisted essentials
    from the caller's environment plus scratch HOME and caches (and HERMES_HOME when given)."""
    home = build_dir / "home"
    cache = build_dir / "cache"
    tmp = build_dir / "tmp"
    checks = [("scratch HOME", home), ("scratch cache", cache), ("scratch tmp", tmp)]
    if hermes_home is not None:
        checks.append(("HERMES_HOME", hermes_home))
    for what, path in checks:  # validate everything before creating anything
        assert_outside_real_home(path, what)
    for _what, path in checks:
        path.mkdir(parents=True, exist_ok=True)
    env = {k: os.environ[k] for k in ENV_ALLOWLIST if k in os.environ}
    env["HOME"] = str(home)
    env["XDG_CACHE_HOME"] = str(cache)
    env["UV_CACHE_DIR"] = str(cache / "uv")
    env["TMPDIR"] = str(tmp)
    env["UV_PYTHON_DOWNLOADS"] = "never"
    # A scratch HOME would hide already-installed uv-managed interpreters; keep discovering them
    # (read-only) from where the caller's uv keeps them. Downloads stay disabled regardless.
    install_dir = os.environ.get("UV_PYTHON_INSTALL_DIR")
    if not install_dir:
        data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        install_dir = str(Path(data_home) / "uv" / "python")
    if Path(install_dir).is_dir():
        env["UV_PYTHON_INSTALL_DIR"] = install_dir
    if hermes_home is not None:
        env["HERMES_HOME"] = str(hermes_home)
    return env


def run_uv_sync(src_dir: Path, python: str, env: dict[str, str]) -> bool:
    if shutil.which("uv", path=env.get("PATH")) is None:
        print("extract: `uv` not on PATH, skipping venv setup for", src_dir, file=sys.stderr)
        return False
    result = subprocess.run(
        ["uv", "sync", "--locked", "--no-python-downloads", "--python", python],
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
    "'executable': sys.executable}))"
)


def interpreter_info(src_dir: Path, env: dict[str, str]) -> dict | None:
    proc = subprocess.run(
        [str(venv_python(src_dir)), "-c", _INFO_SCRIPT],
        cwd=src_dir, env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        info = json.loads(proc.stdout)
    except ValueError:
        return None
    return info if isinstance(info, dict) and isinstance(info.get("version"), str) else None


def uv_version(env: dict[str, str]) -> str | None:
    proc = subprocess.run(["uv", "--version"], env=env, capture_output=True, text=True)
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def clean_build_state(build_dir: Path) -> None:
    """Remove the previous run's `build-metadata.json` and `hermes_home` so nothing stale can
    look like this run's result. Refuses (rather than deletes) anything that is a symlink or
    resolves into the real home."""
    assert_outside_real_home(build_dir, "build directory")
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
    imports: dict[str, bool],
) -> Path:
    """Nonsecret record of what actually ran, for a later matrix report. Only called after
    extraction, sync and every sanity import succeeded."""
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
    path = build_dir / METADATA_NAME
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


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
    build_dir = out_root / build.label
    clean_build_state(build_dir)
    clone = refs_dir / build.clone
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

    before = clone_snapshot(clone)
    src_dir = build_dir / "src"
    if src_dir.exists():
        shutil.rmtree(src_dir)
    extract_tree(clone, commit, src_dir)
    after = clone_snapshot(clone)

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

    env = scratch_env(build_dir, build_dir / "hermes_home")
    ok = run_uv_sync(src_dir, build.python, env)
    if not ok:
        print(f"extract: `uv sync` failed for {build.label}", file=sys.stderr)
        return False

    info = interpreter_info(src_dir, env)
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
    write_build_metadata(build, commit, src_dir, build_dir, info, uv_version(env), results)
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
    args = parser.parse_args(argv)

    out_root = args.out.resolve()
    assert_outside_real_home(out_root, "--out")
    out_root.mkdir(parents=True, exist_ok=True)

    refs_dir = args.refs_dir or find_refs_dir(Path(__file__).resolve().parent)
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

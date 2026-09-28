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
  4. Creates one Python 3.11 venv per build (`uv sync`, using the extracted tree's own
     `uv.lock` — the same tool and lockfile Hermes itself uses) and does an editable install of
     the extracted tree.
  5. Sanity-imports a couple of the package's top-level modules (`agent`, `hermes_cli`) inside
     that venv, with `HERMES_HOME` pointed at an isolated per-build scratch directory.

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
import os
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


@dataclass
class Build:
    label: str
    clone: str
    ref: str
    optional: bool


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


def run_uv_sync(src_dir: Path) -> bool:
    if shutil.which("uv") is None:
        print("extract: `uv` not on PATH, skipping venv setup for", src_dir, file=sys.stderr)
        return False
    result = subprocess.run(["uv", "sync", "--python", "3.11"], cwd=src_dir)
    return result.returncode == 0


def sanity_import(src_dir: Path, hermes_home: Path) -> dict[str, bool]:
    assert_outside_real_home(hermes_home, "HERMES_HOME")
    hermes_home.mkdir(parents=True, exist_ok=True)
    # Unset every inherited HERMES_* variable (matching contracts/fixture-format.md rule 1) and
    # pin HERMES_HOME to the isolated per-build scratch directory just asserted safe above.
    env = {k: v for k, v in os.environ.items() if not k.startswith("HERMES_")}
    env["HERMES_HOME"] = str(hermes_home)
    results: dict[str, bool] = {}
    for module in SANITY_IMPORTS:
        proc = subprocess.run(
            ["uv", "run", "--python", "3.11", "python", "-c", f"import {module}"],
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
    build_dir = out_root / build.label
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

    ok = run_uv_sync(src_dir)
    if not ok:
        print(f"extract: `uv sync` failed for {build.label}", file=sys.stderr)
        return False

    hermes_home = build_dir / "hermes_home"
    results = sanity_import(src_dir, hermes_home)
    print(f"extract: {build.label} sanity imports: {results}")
    return all(results.values())


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

#!/usr/bin/env python3
"""Build and verify a PRIVATE owner-local HMP package candidate (spec 007 ROOT_DECISIONS OD-2).

The package is the exact tracked tree of one reviewed revision I, copied out of git objects into a
new 0700 directory outside the repository, with exactly two files changed: the `builds` arrays of
`approval_supported_builds.json` and `direct_send_supported_builds.json`, each gaining one
owner-local exact-git entry. Nothing else may differ: `check_delta` refuses any other byte.

This is trusted local evidence, not a signature and not production approval. The entry names a
Hermes source build, not an owner, device or host: scope comes from local package custody, the
target-host install and the existing explicit grants. The fixture receipt for I stays unsigned
evidence for I; it is stale by plugin digest for the package and is never edited, relabelled
or waived here.
Before anything is built or verified, the production `validate_approval_receipt(final=True)` is run
against the clean source I (never P) with I's own bridge lists; that is the correct use of the
validator for I, and its verdict is never transferred to P.

No Hermes module is imported and no host, config, key or service is touched. Only the plugin's own
parser (`load_read_compat_list`, `match_build`, `GitFingerprintReader`) reads files.

    python3 tools/compat/owner_package.py build  --expected-head <I> --hermes-src <tree> ...
    python3 tools/compat/owner_package.py verify --package <dir> --expected-head <I> ...
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True  # a package copy must never gain __pycache__

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SUBDIR = "plugin"
APPROVAL = "server/hmp_plugin/approval_supported_builds.json"
DIRECT = "server/hmp_plugin/direct_send_supported_builds.json"
READ = "server/hmp_plugin/read_compat_builds.json"
MANIFESTS = (APPROVAL, DIRECT)
ENTRY_KEYS = ("label", "fingerprint", "git_sha", "source_sha", "qualified_by", "qualified_at")
SHA40 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
Tree = dict[str, tuple[int, bytes]]  # path -> (git mode 0o100644 or 0o100755, bytes)


class PackageRefusalError(RuntimeError):
    """A packaging precondition or the strict delta check failed; nothing is trusted."""


def _git(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False, timeout=120,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"),
    )
    if proc.returncode != 0:
        raise PackageRefusalError(f"git {args[0]} failed")
    return proc.stdout


def require_clean_head(repo: Path, expected: str, *, what: str) -> None:
    if not SHA40.fullmatch(expected):
        raise PackageRefusalError(f"{what}: expected SHA must be a full 40-hex commit")
    if _git(repo, "rev-parse", "HEAD").decode().strip() != expected:
        raise PackageRefusalError(f"{what}: HEAD is not the expected commit")
    if _git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        raise PackageRefusalError(f"{what}: tracked files are modified")


def read_git_tree(repo: Path, rev: str) -> Tree:
    """Every tracked file at `rev`, from git objects (never the working tree). Symlinks,
    submodules and any other non-regular mode are refused rather than copied."""
    tree: Tree = {}
    listing = _git(repo, "ls-tree", "-r", "-z", "--full-tree", rev)
    for record in filter(None, listing.split(b"\0")):
        meta, _, raw_path = record.partition(b"\t")
        mode_s, kind, obj = meta.decode().split()
        path = raw_path.decode("utf-8")
        mode = int(mode_s, 8)
        if kind != "blob" or mode not in (0o100644, 0o100755):
            raise PackageRefusalError(f"non-regular tracked entry refused: {path}")
        if path.startswith("/") or ".." in Path(path).parts:
            raise PackageRefusalError(f"unsafe tracked path refused: {path}")
        tree[path] = (mode, _git(repo, "cat-file", "blob", obj))
    return tree


def _load_object(data: bytes, path: str) -> dict[str, Any]:
    try:
        raw = json.loads(data.decode("utf-8"))
    except ValueError as exc:
        raise PackageRefusalError(f"{path} is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise PackageRefusalError(f"{path} is not a JSON object")
    return raw


def _dump(raw: Mapping[str, Any]) -> bytes:
    return (json.dumps(raw, indent=2) + "\n").encode("utf-8")


def make_entry(
    *, label: str, fingerprint: str, git_sha: str, source_sha: str, qualified_by: str,
    qualified_at: str,
) -> dict[str, str]:
    """A runtime `BuildEntry` as the parser reads it: exactly these six keys, no extras."""
    if not SHA256.fullmatch(fingerprint):
        raise PackageRefusalError("fingerprint must be 64 lowercase hex")
    if not (SHA40.fullmatch(git_sha) and SHA40.fullmatch(source_sha)):
        raise PackageRefusalError("git_sha and source_sha must be full 40-hex commits")
    if git_sha != source_sha:
        raise PackageRefusalError("an exact-git owner entry needs git_sha == source_sha")
    if not label or not qualified_by or not qualified_at:
        raise PackageRefusalError("label, qualified_by and qualified_at are required")
    return dict(zip(
        ENTRY_KEYS, (label, fingerprint, git_sha, source_sha, qualified_by, qualified_at),
        strict=True,
    ))


def apply_entries(tree: Tree, entries: Mapping[str, Mapping[str, str]]) -> Tree:
    """A copy of `tree` whose two manifests carry `entries[path]` as their only build. Refuses a
    manifest that already lists builds or is not in the canonical form this tool writes, so the
    only bytes that change are the `builds` array."""
    if set(entries) != set(MANIFESTS):
        raise PackageRefusalError("exactly the approval and direct-send manifests are updated")
    out = dict(tree)
    for path in MANIFESTS:
        mode, data = tree[path]
        raw = _load_object(data, path)
        if raw.get("builds") != []:
            raise PackageRefusalError(f"{path} already lists builds; refusing to overwrite")
        if _dump(raw) != data:
            raise PackageRefusalError(f"{path} is not canonical; a byte-exact delta is impossible")
        raw["builds"] = [dict(entries[path])]
        out[path] = (mode, _dump(raw))
    return out


def check_delta(before: Tree, after: Tree, entries: Mapping[str, Mapping[str, str]]) -> list[str]:
    """Prove `after` differs from `before` ONLY by the two manifests' `builds` arrays, each going
    from empty to exactly `entries[path]`. Returns the changed paths; raises otherwise."""
    if set(before) != set(after):
        raise PackageRefusalError("the file set differs between the source and the package")
    changed = sorted(p for p in before if before[p] != after[p])
    if changed != sorted(MANIFESTS):
        raise PackageRefusalError("unexpected delta: " + ", ".join(changed or ["none"]))
    for path in MANIFESTS:
        if before[path][0] != after[path][0]:
            raise PackageRefusalError(f"{path} mode changed")
        old, new = _load_object(before[path][1], path), _load_object(after[path][1], path)
        if list(old) != list(new):
            raise PackageRefusalError(f"{path} top-level keys or order changed")
        if {k: v for k, v in old.items() if k != "builds"} != {
            k: v for k, v in new.items() if k != "builds"
        }:
            raise PackageRefusalError(f"{path} changed outside builds")
        if old["builds"] != [] or new["builds"] != [dict(entries[path])]:
            raise PackageRefusalError(f"{path} builds is not [] -> exactly the reviewed entry")
        if list(new["builds"][0]) != list(ENTRY_KEYS):
            raise PackageRefusalError(f"{path} entry has invented or missing fields")
    return changed


def tree_digest(tree: Tree) -> str:
    """SHA-256 over `path\\0mode\\0len\\0bytes` for every file, sorted: whole-package identity."""
    digest = hashlib.sha256()
    for path in sorted(tree):
        mode, data = tree[path]
        digest.update(f"{path}\0{mode & 0o777:o}\0{len(data)}\0".encode() + data)
    return digest.hexdigest()


def write_package(tree: Tree, parent: Path, repo: Path) -> Path:
    """Create a fresh 0700 `hmp-owner-local-package-*` under `parent` (outside `repo`, never
    existing before) holding the tree under `plugin/`: files 0600, tracked executables 0700."""
    parent = parent.resolve()
    if parent == repo.resolve() or repo.resolve() in parent.parents:
        raise PackageRefusalError("the package must live outside the repository")
    if ".hermes" in parent.parts:
        raise PackageRefusalError("refusing a Hermes home as the package parent")
    root = Path(tempfile.mkdtemp(prefix="hmp-owner-local-package-", dir=parent))
    os.chmod(root, 0o700)
    plugin = root / PLUGIN_SUBDIR
    plugin.mkdir(mode=0o700)
    for path, (mode, data) in tree.items():
        target = plugin / path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(target, 0o700 if mode == 0o100755 else 0o600)
    for directory in {p for p in plugin.rglob("*") if p.is_dir()}:
        os.chmod(directory, 0o700)
    return root


def read_package_tree(plugin: Path) -> Tree:
    """The package as found on disk. Refuses symlinks, hardlinks, bytecode, loose modes and any
    group/world access, so the later comparison cannot be satisfied by a copy trick."""
    tree: Tree = {}
    for path in sorted(plugin.rglob("*")):
        info = path.lstat()
        rel = path.relative_to(plugin).as_posix()
        if stat.S_ISLNK(info.st_mode):
            raise PackageRefusalError(f"symlink in package: {rel}")
        if info.st_mode & 0o077:
            raise PackageRefusalError(f"group/world access in package: {rel}")
        if path.is_dir():
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PackageRefusalError(f"not a plain unlinked file: {rel}")
        if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
            raise PackageRefusalError(f"bytecode in package: {rel}")
        tree[rel] = (0o100755 if info.st_mode & 0o100 else 0o100644, path.read_bytes())
    return tree


class _PackageParser:
    """The package's own compat.py, imported as a submodule of a stub package so the plugin
    `__init__` (registration, aiohttp) never runs and no Hermes module is touched."""

    def __init__(self, hmp_plugin_dir: Path) -> None:
        self._name = f"_owner_pkg_{os.getpid()}"
        stub = types.ModuleType(self._name)
        stub.__path__ = [str(hmp_plugin_dir)]  # type: ignore[attr-defined]
        sys.modules[self._name] = stub
        self.compat = importlib.import_module(f"{self._name}.compat")

    def close(self) -> None:
        for name in [n for n in sys.modules if n == self._name or n.startswith(self._name + ".")]:
            del sys.modules[name]


def hermes_identity(
    compat: Any, hermes_src: Path, manifests: Mapping[str, Sequence[str]], expected_sha: str,
) -> dict[str, Any]:
    """The Hermes source's identity per lane, through the runtime's own GitFingerprintReader."""
    require_clean_head(hermes_src, expected_sha, what="hermes source")
    out: dict[str, Any] = {}
    for path, files in manifests.items():
        identity = compat.GitFingerprintReader(files).read(hermes_src)
        if identity is None or identity.git_sha != expected_sha:
            raise PackageRefusalError(f"hermes source is unidentifiable for {path}")
        out[path] = identity
    return out


def check_runtime_match(
    plugin: Path, hermes_src: Path, expected_sha: str,
    expected_fingerprints: Mapping[str, str],
) -> dict[str, Any]:
    """Run the package's own parser and `match_build` against the real Hermes source. Each lane
    must match exactly its one entry; a moved SHA or a fingerprint-only identity must not."""
    parser = _PackageParser(plugin / "server" / "hmp_plugin")
    try:
        compat = parser.compat
        lists = {p: compat.load_read_compat_list(plugin / p) for p in MANIFESTS}
        identities = hermes_identity(
            compat, hermes_src, {p: lists[p].bridge_files for p in MANIFESTS}, expected_sha)
        report: dict[str, Any] = {}
        for path in MANIFESTS:
            identity, builds = identities[path], lists[path].builds
            if identity.fingerprint != expected_fingerprints[path]:
                raise PackageRefusalError(f"{path}: fingerprint differs from the expected value")
            if len(builds) != 1 or compat.match_build(identity, builds) is not builds[0]:
                raise PackageRefusalError(f"{path}: runtime match_build does not select the entry")
            moved = compat.BuildIdentity(identity.fingerprint, "0" * 40)
            bare = compat.BuildIdentity(identity.fingerprint, None)
            if compat.match_build(moved, builds) or compat.match_build(bare, builds):
                raise PackageRefusalError(f"{path}: entry matches a moved SHA or no-git identity")
            report[path] = {
                "fingerprint": identity.fingerprint, "git_sha": identity.git_sha,
                "label": builds[0].label, "matched": True,
                "requalification_required_present": "requalification_required"
                in _load_object((plugin / path).read_bytes(), path),
            }
        return report
    finally:
        parser.close()


def _fixture_modules() -> tuple[Any, Any]:
    """The production fixture validator and its error type. HMP-only: these import this repo's
    plugin `compat`, never a Hermes module."""
    fixtures = str(REPO_ROOT / "tools" / "fixtures")
    if fixtures not in sys.path:
        sys.path.insert(0, fixtures)
    import _fixture_common as fc
    import approval_fixture as af
    return af, fc


def plugin_digest(plugin_dir: Path) -> str:
    """The receipt's own `plugin_source_digest`, over `<root>/server/hmp_plugin`."""
    return _fixture_modules()[0].plugin_source_digest(plugin_dir / "server" / "hmp_plugin")


def _bridge_files(tree: Tree, path: str) -> list[str]:
    files = _load_object(tree[path][1], path).get("bridge_files")
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise PackageRefusalError(f"{path} has no usable bridge_files")
    return files


def validate_source_receipt(
    receipt: Path, *, source: Tree, source_plugin_root: Path, hermes_src: Path, label: str,
) -> None:
    """Delegate to the production `validate_approval_receipt(final=True)` for the CLEAN SOURCE I
    (never the package P): I's own plugin copy, I's approval/read/direct bridge lists and the
    Hermes build the receipt names. Its seven stages, required case set, read boundary, schema,
    upstream-verified identity and lifecycle/timing rules are the validator's, not a copy.
    The validator is used correctly for I; its verdict is never waived or relabelled for P."""
    af, fc = _fixture_modules()
    build = fc.BuildInfo(
        label=label, src_dir=hermes_src, venv_python=hermes_src / ".venv" / "bin" / "python3")
    try:
        af.validate_approval_receipt(
            receipt, build, target_files=_bridge_files(source, APPROVAL), final=True,
            plugin_dir=source_plugin_root / "server" / "hmp_plugin",
            read_files=_bridge_files(source, READ), direct_files=_bridge_files(source, DIRECT))
    except fc.FixtureSafetyError as exc:
        raise PackageRefusalError(
            f"source receipt refused by the fixture validator: {exc}",
        ) from exc


def check_source_receipt(
    receipt: Path, *, source_digest: str, package_digest: str, git_sha: str,
    fingerprints: Mapping[str, str],
) -> dict[str, Any]:
    """Read-only extra checks after `validate_source_receipt` has accepted the receipt for I: it
    binds I's digest, SHA and recomputed fingerprints and does NOT match the package digest (so it
    is stale for P and stays unwaived). Never edits the receipt."""
    if source_digest == package_digest:
        raise PackageRefusalError("package digest equals the source digest; the delta is empty")
    raw = _load_object(receipt.read_bytes(), "source receipt")
    ev = raw.get("evidence")
    if not isinstance(ev, dict):
        raise PackageRefusalError("source receipt has no evidence block")
    if ev.get("plugin_sha256") != source_digest:
        raise PackageRefusalError("source receipt does not bind the plugin digest of I")
    if ev.get("git_sha") != git_sha or ev.get("source_sha") != git_sha:
        raise PackageRefusalError("source receipt names a different Hermes SHA")
    if (ev.get("approval_fingerprint"), ev.get("direct_send_fingerprint")) != (
        fingerprints[APPROVAL], fingerprints[DIRECT]):
        raise PackageRefusalError("source receipt fingerprints differ from the recomputed values")
    if ev.get("complete") is not True or ev.get("not_for_commit") is not True:
        raise PackageRefusalError("source receipt is not a complete fixture receipt")
    return {
        "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "validated_for_source_by_fixture_validator": True,
        "binds_digest_of_source": True, "stale_for_package_by_digest": True,
    }


def inventory(tree: Tree) -> list[dict[str, Any]]:
    return [
        {"path": p, "mode": f"{tree[p][0] & 0o777:o}", "bytes": len(tree[p][1]),
         "sha256": hashlib.sha256(tree[p][1]).hexdigest()}
        for p in sorted(tree)
    ]


def _expected_fingerprints(args: argparse.Namespace) -> dict[str, str]:
    for value in (args.expected_approval_fingerprint, args.expected_direct_fingerprint):
        if not SHA256.fullmatch(value):
            raise PackageRefusalError("expected fingerprints must be 64 lowercase hex")
    return {APPROVAL: args.expected_approval_fingerprint, DIRECT: args.expected_direct_fingerprint}


def _verify(
    args: argparse.Namespace, source: Tree, plugin: Path, entries: Mapping[str, Mapping[str, str]],
    source_digest: str,
) -> dict[str, Any]:
    fingerprints = _expected_fingerprints(args)
    package = read_package_tree(plugin)
    changed = check_delta(source, package, entries)
    runtime = check_runtime_match(plugin, args.hermes_src, args.expected_hermes_sha, fingerprints)
    if any("__pycache__" in str(p) for p in plugin.rglob("*")):
        raise PackageRefusalError("verification left bytecode in the package")
    package_digest = plugin_digest(plugin)
    receipt = check_source_receipt(
        args.source_receipt, source_digest=source_digest, package_digest=package_digest,
        git_sha=args.expected_hermes_sha, fingerprints=fingerprints)
    return {
        "changed_files": changed, "file_count": len(package),
        "package_tree_sha256": tree_digest(package), "source_tree_sha256": tree_digest(source),
        "plugin_source_digest_source": source_digest,
        "plugin_source_digest_package": package_digest,
        "manifest_sha256": {p: hashlib.sha256(package[p][1]).hexdigest() for p in MANIFESTS},
        "runtime_match": runtime, "source_receipt": receipt, "files": inventory(package),
    }


def gate_source_receipt(args: argparse.Namespace, source: Tree) -> str:
    """Run the production validator on I (final=True) BEFORE anything is built or verified.
    Returns I's plugin digest. I's plugin is materialised in scratch only to be read."""
    with tempfile.TemporaryDirectory(prefix="hmp-owner-digest-") as scratch:
        root = Path(scratch)
        for path, (_, data) in source.items():
            if path.startswith("server/hmp_plugin/"):
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                (root / path).write_bytes(data)
        validate_source_receipt(
            args.source_receipt, source=source, source_plugin_root=root,
            hermes_src=args.hermes_src, label=args.source_label)
        return plugin_digest(root)


def _entries(
    args: argparse.Namespace, fingerprints: Mapping[str, str],
) -> dict[str, dict[str, str]]:
    head = args.expected_head[:12]
    entries = {}
    for path in MANIFESTS:
        entries[path] = make_entry(
            label=args.label, fingerprint=fingerprints[path], git_sha=args.expected_hermes_sha,
            source_sha=args.expected_hermes_sha,
            qualified_by=args.qualified_by or (
                f"tools/compat/owner_package.py: owner-local package candidate, manifest-only "
                f"delta from {head}; unsigned fixture evidence for the exact Hermes git SHA; "
                f"not signed and not production approval"),
            qualified_at=args.qualified_at or datetime.now(UTC).isoformat(),
        )
    return entries


def cmd_build(args: argparse.Namespace) -> int:
    fingerprints = _expected_fingerprints(args)
    require_clean_head(args.repo, args.expected_head, what="repository")
    source = read_git_tree(args.repo, args.expected_head)
    source_digest = gate_source_receipt(args, source)
    entries = _entries(args, fingerprints)
    package = apply_entries(source, entries)
    check_delta(source, package, entries)
    root = write_package(package, args.out_parent, args.repo)
    try:
        report = _verify(args, source, root / PLUGIN_SUBDIR, entries, source_digest)
    except BaseException:
        shutil.rmtree(root)  # a refused candidate must not be left lying around as a package
        raise
    report.update(format=1, source_head=args.expected_head, hermes_sha=args.expected_hermes_sha,
                  entries=entries, generated_at=datetime.now(UTC).isoformat(),
                  limits="unsigned local candidate; metadata is not an owner/device restriction")
    out = root / "report.json"
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2) + "\n")
    print(root)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    require_clean_head(args.repo, args.expected_head, what="repository")
    source = read_git_tree(args.repo, args.expected_head)
    source_digest = gate_source_receipt(args, source)
    plugin = args.package / PLUGIN_SUBDIR
    shipped = {
        p: _load_object((plugin / p).read_bytes(), p)["builds"] for p in MANIFESTS
    }
    entries = {p: builds[0] for p, builds in shipped.items() if len(builds) == 1}
    if set(entries) != set(MANIFESTS):
        raise PackageRefusalError("each manifest must carry exactly one build")
    report = _verify(args, source, plugin, entries, source_digest)
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--repo", type=Path, default=REPO_ROOT)
        p.add_argument("--expected-head", required=True)
        p.add_argument("--hermes-src", type=Path, required=True)
        p.add_argument("--expected-hermes-sha", required=True)
        p.add_argument("--expected-approval-fingerprint", required=True)
        p.add_argument("--expected-direct-fingerprint", required=True)
        p.add_argument("--source-receipt", type=Path, required=True)
        p.add_argument("--source-label", required=True,
                       help="build label the I receipt was issued for (BuildInfo.label)")
        if name == "build":
            p.add_argument("--out-parent", type=Path, required=True)
            p.add_argument("--label", default="owner-local-approval-git")
            p.add_argument("--qualified-by")
            p.add_argument("--qualified-at")
        else:
            p.add_argument("--package", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        return cmd_build(args) if args.cmd == "build" else cmd_verify(args)
    except PackageRefusalError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

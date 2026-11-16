"""Materialize fixed native-journey sources; never start Hermes or issue authority.

Caller exclusively owns a fresh private root and invokes this in a fresh -I -B
process with umask077. Failed/unknown setup remains quarantined, never retried in
that root. The existing Git helper retains and joins each actual child, including
late/unknown outcomes. No historical broker/GO or native admission is invoked.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tarfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

_EXTENSIONS = frozenset((".py", ".json", ".toml", ".yaml", ".yml"))
_NATIVE = "ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df"
_HMP = "a4a157a5d04a20f23dddc6d614d462b758a947f4"
_MANIFEST = "28f13dcb4a90fce810bc0cf8aecb35b33584f5095e5e427a1887637135bcc702"
_DRIVER = None


class PresentationSourceStageError(RuntimeError):
    """The fixed source snapshot was not established."""


def _require(value):
    if value is not True:
        raise PresentationSourceStageError("presentation_source_stage_refused")


def _driver():
    global _DRIVER
    if _DRIVER is None:
        path = Path(__file__).with_name("local_media_native_serving_driver.py")
        spec = importlib.util.spec_from_file_location("_presentation_source_git", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _DRIVER = module
    return _DRIVER


def _name(raw):
    _require(type(raw) is str and 0 < len(raw) <= 1024 and "\\" not in raw)
    path = PurePosixPath(raw)
    _require(not path.is_absolute() and ".." not in path.parts and ".git" not in path.parts)
    _require(str(path) == raw and raw not in ("", "."))
    return path


def literal_tree(raw, extensions):
    _require(type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024)
    _require(raw.endswith(b"\0") and (extensions is None or extensions == _EXTENSIONS))
    rows = raw[:-1].split(b"\0")
    _require(len(rows) <= 65536)
    result = {}
    for row in rows:
        header, separator, name = row.partition(b"\t")
        _require(separator == b"\t")
        text = name.decode("utf-8", "strict")
        path = _name(text)
        if extensions is not None and path.suffix not in extensions:
            continue
        parts = header.split(b" ")
        _require(len(parts) == 3)
        mode, kind, oid = parts
        _require(mode in (b"100644", b"100755") and kind == b"blob")
        _require(re.fullmatch(rb"[0-9a-f]{40}", oid) is not None)
        _require(text not in result and len(result) < 20000)
        result[text] = (mode.decode("ascii"), oid.decode("ascii"))
    _require(bool(result))
    return result


@contextmanager
def _tar_stream(source):
    try:
        with tarfile.open(fileobj=source, mode="r:") as stream:
            yield stream
    except tarfile.TarError:
        raise PresentationSourceStageError("presentation_source_stage_refused") from None


def extract_snapshot(archive, destination, commit, literal):
    """Copy only inventoried plain files; no extractall, links or metadata replay.

    Accept only archives from the owned trusted Git setup, not arbitrary uploads.
    This is not a general hostile-archive parser or hard process-RSS bound.
    The caller owns the root exclusively throughout. A partial destination is
    invalid and retained on refusal; no manifest is published by this function.
    """
    _require(type(archive) is type(Path()) and type(destination) is type(Path()))
    _require(archive.is_absolute() and destination.is_absolute())
    _require(archive.parent == destination.parent and archive.parent.resolve() == archive.parent)
    parent = archive.parent.lstat()
    _require(stat.S_ISDIR(parent.st_mode) and parent.st_uid == os.geteuid())
    _require(stat.S_IMODE(parent.st_mode) == 0o700)
    _require(not destination.exists() and not destination.is_symlink())
    _require(type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit) is not None)
    _require(type(literal) is dict and 0 < len(literal) <= 20000)
    for item in literal.values():
        _require(type(item) is tuple and len(item) == 2)
        _require(item[0] in ("100644", "100755"))
        _require(type(item[1]) is str and re.fullmatch(r"[0-9a-f]{40}", item[1]) is not None)
    prefixes = set()
    for name in literal:
        for parent in _name(name).parents:
            if str(parent) != ".":
                prefixes.add(str(parent))
    destination.mkdir(mode=0o700)
    fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        _require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid())
        _require(before.st_nlink == 1 and stat.S_IMODE(before.st_mode) == 0o600)
        _require(before.st_size <= 160 * 1024 * 1024)
        seen, files, total = set(), {}, 0
        with _tar_stream(source) as stream:
            for member in stream:
                text = member.name.rstrip("/") if member.isdir() else member.name
                path = _name(text)
                _require(text not in seen and len(seen) < 20000)
                seen.add(text)
                target = destination.joinpath(*path.parts)
                if member.isdir():
                    _require(text in prefixes)
                    target.mkdir(mode=0o700, parents=True, exist_ok=True)
                    continue
                _require(member.isfile() and not member.issparse() and text in literal)
                mode, oid = literal[text]
                _require(member.mode == (0o700 if mode == "100755" else 0o600))
                _require(0 <= member.size <= 4 * 1024 * 1024)
                total += member.size
                _require(total <= 128 * 1024 * 1024)
                payload = stream.extractfile(member)
                _require(payload is not None)
                with payload:
                    data = payload.read(member.size + 1)
                _require(len(data) == member.size)
                blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
                _require(hashlib.sha1(blob, usedforsecurity=False).hexdigest() == oid)
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                out = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(out, "wb") as writer:
                    writer.write(data)
                files[text] = hashlib.sha256(data).hexdigest()
            _require(stream.pax_headers.get("comment") == commit)
        after = os.fstat(source.fileno())
        _require(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        )
    _require(set(files) == set(literal))
    return files


def stage_sources(root, native_repository, hmp_repository):
    """One fixed setup in a new root; source measurements are not runtime grants."""
    _require(sys.flags.isolated == 1 and sys.dont_write_bytecode and sys.flags.optimize == 0)
    _require(type(root) is type(Path()) and root.is_absolute() and root.resolve() == root)
    info = root.lstat()
    _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid())
    _require(stat.S_IMODE(info.st_mode) == 0o700 and not any(root.iterdir()))
    for repository in (native_repository, hmp_repository):
        _require(type(repository) is type(Path()) and repository.is_absolute())
        _require(repository.resolve(strict=True) == repository and repository.is_dir())
    driver = _driver()
    receipt = {"commands": [], "stage": "source_setup", "native_executed": False}
    (root / "tool-home").mkdir(mode=0o700)
    driver.commands._save(root / "receipt.json", receipt)
    version = driver._git(root, hmp_repository, ["--version"], "git_version", receipt)
    match = re.fullmatch(rb"git version (\d+)\.(\d+)\.(\d+)(?:[ .-].*)?\n", version)
    _require(match is not None and tuple(map(int, match.groups())) >= (2, 54, 0))
    sources = {}
    for label, repository, commit, extensions, count in (
        ("native", native_repository, _NATIVE, _EXTENSIONS, 12185),
        ("hmp", hmp_repository, _HMP, None, 1021),
    ):
        _require(
            driver._git(root, repository, ["cat-file", "-t", commit], label + "_kind", receipt)
            == b"commit\n"
        )
        driver._no_custom_tar(root, repository, label, receipt)
        raw = driver._git(
            root,
            repository,
            ["ls-tree", "-r", "-z", "--full-tree", commit],
            label + "_tree",
            receipt,
            tree=True,
        )
        literal = literal_tree(raw, extensions)
        _require(len(literal) == count)
        archive = root / (label + ".tar")
        args = ["archive", "--format=tar", "--output=" + str(archive), commit]
        if extensions is not None:
            args += ["--", "*.py", "*.json", "*.toml", "*.yaml", "*.yml"]
        driver._git(root, repository, args, label + "_archive", receipt)
        files = extract_snapshot(archive, root / label, commit, literal)
        sources[label] = {"commit": commit, "files": files}
    data = json.dumps({"sources": sources}, sort_keys=True, indent=2).encode()
    _require(hashlib.sha256(data).hexdigest() == _MANIFEST)
    fd = os.open(
        root / "source-manifest.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(fd, "wb") as writer:
        writer.write(data)
    receipt.update(stage="source_setup_complete", manifest_sha256=_MANIFEST)
    driver.commands._save(root / "receipt.json", receipt)
    return root / "source-manifest.json"

"""Darwin-only clone of one verified private archive; no import-time IO or fallback.

This is fixture storage preparation, not native-service or host-file authority.
Normal source extraction and literal Git checks remain the caller's responsibility.
"""
import contextlib
import hashlib
import os
import re
import stat
import sys
from pathlib import Path

MAX_ARCHIVE = 160 * 1024 * 1024


def require(value):
    if not value:
        raise RuntimeError("native_archive_clone_refused")


def _snapshot(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_uid, info.st_mode, info.st_nlink)


def _regular(info):
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
            stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1 and
            0 < info.st_size <= MAX_ARCHIVE)


def _digest(fd, size):
    digest = hashlib.sha256()
    for offset in range(0, size, 1024 * 1024):
        wanted = min(1024 * 1024, size - offset)
        data = os.pread(fd, wanted, offset)
        require(len(data) == wanted)
        digest.update(data)
    require(os.pread(fd, 1, size) == b"")
    return digest.hexdigest()


def _has_xattrs(fd):
    import ctypes

    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    function = library.flistxattr
    function.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
    function.restype = ctypes.c_ssize_t
    result = function(fd, None, 0, 0)
    if result == -1:
        raise OSError(ctypes.get_errno(), "native_archive_attributes_failed")
    require(result >= 0)
    return result != 0


def _call_clone(source_fd, directory_fd, name):
    import ctypes

    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    function = library.fclonefileat
    function.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32)
    function.restype = ctypes.c_int
    # Current SDK: CLONE_NOOWNERCOPY=2, CLONE_NOFOLLOW_ANY=8. A single basename
    # relative to the retained directory FD has no intermediate target path.
    result = function(source_fd, directory_fd, name, 0x000A)
    if result == -1:
        raise OSError(ctypes.get_errno(), "native_archive_clone_failed")
    require(result == 0)


def clone_archive(source, destination, expected_sha256):
    """Retain source/destination directory FDs through clone and exact-byte checks.

    No directory clone, subprocess, shell, retry, ordinary copy, deletion or
    archive interpretation. Failed/uncertain output stays under its owned parent.
    """
    require(sys.platform == "darwin" and type(source) is type(Path()) and
            type(destination) is type(Path()) and source.is_absolute() and
            destination.is_absolute() and source.resolve() == source and
            destination.parent.resolve() == destination.parent and
            type(expected_sha256) is str and re.fullmatch("[0-9a-f]{64}", expected_sha256))
    require(destination.name == "native.tar" and not destination.exists())
    parent = destination.parent.lstat()
    require(stat.S_ISDIR(parent.st_mode) and parent.st_uid == os.geteuid() and
            stat.S_IMODE(parent.st_mode) == 0o700)
    with contextlib.ExitStack() as owned:
        source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        owned.callback(os.close, source_fd)
        before = os.fstat(source_fd)
        _regular(before)
        require(not _has_xattrs(source_fd) and
                _digest(source_fd, before.st_size) == expected_sha256)
        directory_fd = os.open(destination.parent,
                               os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        owned.callback(os.close, directory_fd)
        directory = os.fstat(directory_fd)
        require((directory.st_dev, directory.st_ino) == (parent.st_dev, parent.st_ino) and
                directory.st_dev == before.st_dev)
        _call_clone(source_fd, directory_fd, b"native.tar")
        target_fd = os.open("native.tar", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=directory_fd)
        owned.callback(os.close, target_fd)
        target = os.fstat(target_fd)
        _regular(target)
        require((target.st_dev, target.st_ino) != (before.st_dev, before.st_ino) and
                target.st_dev == before.st_dev and target.st_size == before.st_size and
                not _has_xattrs(target_fd) and
                _digest(target_fd, target.st_size) == expected_sha256)
        require(_snapshot(os.fstat(source_fd)) == _snapshot(before) and
                _snapshot(os.fstat(target_fd)) == _snapshot(target))
        return {"method": "fclonefileat", "sha256": expected_sha256, "bytes": target.st_size,
                "distinct_inode": True, "source_unchanged": True, "fallback_used": False}

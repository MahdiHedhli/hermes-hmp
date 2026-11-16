"""Read-only descriptor proof for fresh POSIX native-test homes, not a runtime grant."""

from __future__ import annotations

import fcntl
import os
import stat
import sys
from pathlib import Path, PosixPath


class FixtureFdScopeError(ValueError):
    """A descriptor's owned, named fixture scope could not be established."""


def verify_owned_writable_fd(fd: int, root: Path) -> Path:
    """Observe the actual descriptor and named inode; never chmod, open or repair it.

    Darwin uses F_GETPATH; Linux uses its actual /proc descriptor link. Unknown
    platforms or inaccessible metadata refuse. This is a fixture admission check,
    not an OS sandbox or a guarantee against arbitrary same-process native code.
    The caller must exclusively retain the descriptor and root through this
    observation and any later action. The returned path is sampled metadata,
    never an atomic or durable permission to act.
    """
    if type(fd) is not int or fd < 0 or type(root) is not PosixPath:
        raise FixtureFdScopeError("fixture_fd_scope_refused")
    try:
        root_info = root.lstat()
        if (
            not root.is_absolute()
            or root.resolve(strict=True) != root
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.geteuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
        ):
            raise FixtureFdScopeError("fixture_fd_scope_refused")
        before = os.fstat(fd)
        access = fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE
        if access not in (os.O_WRONLY, os.O_RDWR):
            raise FixtureFdScopeError("fixture_fd_scope_refused")
        if sys.platform == "darwin":
            value = fcntl.fcntl(fd, fcntl.F_GETPATH, b"\0" * 1024)
            raw = os.fsdecode(value.split(b"\0", 1)[0])
        elif sys.platform.startswith("linux"):
            raw = os.readlink(f"/proc/self/fd/{fd}")
        else:
            raise FixtureFdScopeError("fixture_fd_scope_refused")
        path = Path(raw)
        if not path.is_absolute() or path.resolve(strict=True) != path or root not in path.parents:
            raise FixtureFdScopeError("fixture_fd_scope_refused")
        named = path.lstat()
        after = os.fstat(fd)
        observations = (before, named, after)
        if not all(
            stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1
            for info in observations
        ):
            raise FixtureFdScopeError("fixture_fd_scope_refused")
        if len({(info.st_dev, info.st_ino) for info in observations}) != 1:
            raise FixtureFdScopeError("fixture_fd_scope_refused")
        final_access = fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE
        if final_access not in (os.O_WRONLY, os.O_RDWR):
            raise FixtureFdScopeError("fixture_fd_scope_refused")
        return path
    except (OSError, ValueError, TypeError, AttributeError, OverflowError):
        raise FixtureFdScopeError("fixture_fd_scope_refused") from None

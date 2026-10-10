"""Descriptor lifetime regressions for the imported operator parent verifier.

Fake paths and descriptors are inert. The physical traversal uses pytest's owned
temporary directory, opens no socket and invokes no service.
"""
from __future__ import annotations

import errno
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from hmp_plugin import operator_read

_FAKE_PARENT = Path("/virtual/sticky/owned")
_FAULTS = (
    "fstat", "identity-read", "ino", "dev", "type", "uid", "mode",
    "metadata-typeerror", "open", "final-name", "previous-close",
)


def _row(ino: int, *, uid: int, mode: int = stat.S_IFDIR | 0o700,
         dev: int = 1) -> SimpleNamespace:
    return SimpleNamespace(st_dev=dev, st_ino=ino, st_uid=uid, st_mode=mode)


class _DescriptorOS:
    """Complete finite census of only fake descriptors opened by the verifier."""

    O_RDONLY = os.O_RDONLY
    O_DIRECTORY = os.O_DIRECTORY
    O_NOFOLLOW = os.O_NOFOLLOW

    def __init__(self, fault: str | None = None) -> None:
        self.fault = fault
        self.uid = os.getuid()
        self.live: dict[int, str] = {}
        self.opened: list[int] = []
        self.closed: list[int] = []
        self.nextfd = 10
        self.path_by_fd: dict[int, str] = {}
        self.rows = {
            "/": _row(1, uid=0, mode=stat.S_IFDIR | 0o755),
            "/virtual": _row(2, uid=0, mode=stat.S_IFDIR | 0o755),
            "/virtual/sticky": _row(3, uid=0, mode=stat.S_IFDIR | 0o1777),
            str(_FAKE_PARENT): _row(4, uid=self.uid),
        }
        self.fail_used = False

    def getuid(self) -> int:
        return self.uid

    def open(self, name: str, flags: int, *, dir_fd: int | None = None) -> int:
        assert flags == self.O_RDONLY | self.O_DIRECTORY | self.O_NOFOLLOW
        path = str(name) if dir_fd is None else self.path_by_fd[dir_fd] + "/" + str(name)
        path = path.replace("//", "/")
        if self.fault == "open" and path == str(_FAKE_PARENT):
            raise OSError(errno.EIO, "injected child open")
        fd = self.nextfd
        self.nextfd += 1
        self.live[fd] = path
        self.path_by_fd[fd] = path
        self.opened.append(fd)
        return fd

    def close(self, fd: int) -> None:
        assert fd in self.live, "double or foreign descriptor close"
        self.live.pop(fd)
        self.closed.append(fd)
        if self.fault == "previous-close" and len(self.closed) == 1:
            # Models a failure reported after release, without claiming arbitrary
            # real OS close errors guarantee descriptor absence.
            raise OSError(errno.EIO, "injected after previous-parent release")

    def stat(self, name: str, *, dir_fd: int, follow_symlinks: bool) -> SimpleNamespace:
        assert follow_symlinks is False
        path = (self.path_by_fd[dir_fd] + "/" + str(name)).replace("//", "/")
        return self.rows[path]

    def lstat(self, path: Path) -> SimpleNamespace:
        if self.fault == "final-name":
            return _row(400, uid=self.uid)
        return self.rows[str(path)]

    def fstat(self, fd: int) -> object:
        path = self.path_by_fd[fd]
        if path == str(_FAKE_PARENT):
            if self.fault == "fstat" and not self.fail_used:
                self.fail_used = True
                raise OSError(errno.EIO, "injected child fstat")
            if self.fault == "identity-read":
                class BrokenIdentity:
                    st_dev = 1

                    @property
                    def st_ino(self) -> int:
                        raise OSError(errno.EIO, "injected identity read")

                return BrokenIdentity()
            if self.fault == "ino":
                return _row(400, uid=self.uid)
            if self.fault == "dev":
                return _row(4, uid=self.uid, dev=99)
            if self.fault == "type":
                return _row(4, uid=self.uid, mode=stat.S_IFREG | 0o700)
            if self.fault == "uid":
                return _row(4, uid=self.uid + 1)
            if self.fault == "mode":
                return _row(4, uid=self.uid, mode=stat.S_IFDIR | 0o755)
            if self.fault == "metadata-typeerror":
                return SimpleNamespace(st_dev=1, st_ino=4, st_uid=self.uid, st_mode="invalid")
        return self.rows[path]


@pytest.mark.parametrize("fault", _FAULTS)
def test_parent_fd_fault_closes_every_opened_descriptor_once(
    monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    proxy = _DescriptorOS(fault)
    monkeypatch.setattr(operator_read, "os", proxy)
    with pytest.raises((OSError, operator_read.OperatorUnavailableError, TypeError)):
        operator_read._parent_fd(_FAKE_PARENT / operator_read.SOCKET_NAME)
    assert proxy.opened
    assert not proxy.live
    assert sorted(proxy.opened) == sorted(proxy.closed)
    assert len(proxy.closed) == len(set(proxy.closed))


def test_parent_fd_healthy_fake_census_returns_only_owned_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proxy = _DescriptorOS()
    monkeypatch.setattr(operator_read, "os", proxy)
    fd, held = operator_read._parent_fd(_FAKE_PARENT / operator_read.SOCKET_NAME)
    assert set(proxy.live) == {fd}
    assert held.st_ino == 4 and held.st_uid == proxy.uid
    proxy.close(fd)
    assert not proxy.live
    assert sorted(proxy.opened) == sorted(proxy.closed)
    assert len(proxy.closed) == len(set(proxy.closed))


class _RealTrackedOS:
    """Tracks only this verifier's opens, without enumerating other descriptors."""

    O_RDONLY = os.O_RDONLY
    O_DIRECTORY = os.O_DIRECTORY
    O_NOFOLLOW = os.O_NOFOLLOW

    def __init__(self) -> None:
        self.live: set[int] = set()
        self.opened: list[int] = []
        self.closed: list[int] = []

    def getuid(self) -> int:
        return os.getuid()

    def open(self, *args: Any, **kwargs: Any) -> int:
        fd = os.open(*args, **kwargs)
        self.live.add(fd)
        self.opened.append(fd)
        return fd

    def close(self, fd: int) -> None:
        assert fd in self.live
        os.close(fd)
        self.live.remove(fd)
        self.closed.append(fd)

    def stat(self, *args: Any, **kwargs: Any) -> os.stat_result:
        return os.stat(*args, **kwargs)

    def lstat(self, *args: Any, **kwargs: Any) -> os.stat_result:
        return os.lstat(*args, **kwargs)

    def fstat(self, fd: int) -> os.stat_result:
        return os.fstat(fd)


def test_parent_fd_healthy_physical_directory_releases_owned_descriptor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    parent = Path(os.path.realpath(tmp_path))
    parent.chmod(0o700)
    proxy = _RealTrackedOS()
    monkeypatch.setattr(operator_read, "os", proxy)
    fd, held = operator_read._parent_fd(parent / operator_read.SOCKET_NAME)
    try:
        assert proxy.live == {fd}
        assert held.st_uid == os.getuid() and stat.S_IMODE(held.st_mode) == 0o700
    finally:
        proxy.close(fd)
    assert not proxy.live
    assert len(proxy.opened) == len(proxy.closed)
    with pytest.raises(OSError) as error:
        os.fstat(fd)
    assert error.value.errno == errno.EBADF

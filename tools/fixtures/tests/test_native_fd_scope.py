"""Actual local-kernel descriptor tests; no synthetic platform or native host."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "fixture_fd_scope", Path(__file__).parents[1] / "native_fd_scope.py"
)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)


@pytest.fixture
def owned(tmp_path):
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    return root.resolve()


def test_owned_writable_fd_is_observed_without_changing_file_or_mode(owned):
    path = owned / "synthetic.png"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, b"synthetic-only")
        before = os.fstat(fd)
        assert module.verify_owned_writable_fd(fd, owned) == path
        after = os.fstat(fd)
        assert (before.st_dev, before.st_ino, before.st_mode, before.st_size) == (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
        )
        assert os.pread(fd, 14, 0) == b"synthetic-only"
    finally:
        os.close(fd)


@pytest.mark.parametrize("fault", ["outside", "readonly", "hardlink", "unlinked", "closed"])
def test_actual_descriptor_scope_failures_refuse(owned, fault):
    path = (owned.parent if fault == "outside" else owned) / "synthetic"
    path.write_bytes(b"synthetic-only")
    path.chmod(0o600)
    fd = os.open(path, os.O_RDONLY if fault == "readonly" else os.O_RDWR)
    closed = False
    try:
        if fault == "hardlink":
            os.link(path, owned / "other-name")
        elif fault == "unlinked":
            path.unlink()
        elif fault == "closed":
            os.close(fd)
            closed = True
        with pytest.raises(module.FixtureFdScopeError, match=r"^fixture_fd_scope_refused$"):
            module.verify_owned_writable_fd(fd, owned)
    finally:
        if not closed:
            os.close(fd)


def test_nonprivate_or_symlink_root_refuses(owned):
    path = owned / "synthetic"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        owned.chmod(0o755)
        with pytest.raises(module.FixtureFdScopeError):
            module.verify_owned_writable_fd(fd, owned)
        owned.chmod(0o700)
        link = owned.parent / "root-link"
        link.symlink_to(owned, target_is_directory=True)
        with pytest.raises(module.FixtureFdScopeError):
            module.verify_owned_writable_fd(fd, link)
    finally:
        os.close(fd)


@pytest.mark.parametrize("replacement", ["different_inode_writable", "same_inode_readonly"])
def test_descriptor_replaced_after_kernel_path_observation_refuses(owned, monkeypatch, replacement):
    first = owned / "first"
    second = owned / "second"
    fd = os.open(first, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    other = (
        os.open(first, os.O_RDONLY)
        if replacement == "same_inode_readonly"
        else os.open(second, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    )
    observed = []
    if sys.platform == "darwin":
        original = module.fcntl.fcntl

        def replaced(target, command, *args):
            result = original(target, command, *args)
            if target == fd and command == module.fcntl.F_GETPATH:
                os.dup2(other, fd)
                observed.append(True)
            return result

        monkeypatch.setattr(module.fcntl, "fcntl", replaced)
    else:
        assert sys.platform.startswith("linux")
        original = os.readlink

        def replaced(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path == f"/proc/self/fd/{fd}":
                os.dup2(other, fd)
                observed.append(True)
            return result

        monkeypatch.setattr(os, "readlink", replaced)
    try:
        with pytest.raises(module.FixtureFdScopeError):
            module.verify_owned_writable_fd(fd, owned)
        assert observed == [True]
        assert os.fstat(fd).st_ino == os.fstat(other).st_ino
    finally:
        os.close(fd)
        os.close(other)


@pytest.mark.parametrize("fd", [True, -1, 1.5, 2**100])
def test_invalid_or_unrepresentable_descriptor_refuses_with_fixed_error(owned, fd):
    with pytest.raises(module.FixtureFdScopeError, match=r"^fixture_fd_scope_refused$"):
        module.verify_owned_writable_fd(fd, owned)

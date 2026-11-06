"""Archive clone guard models: fake backend, no actual native clone/library load."""
import hashlib
import importlib.util
import os
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_archive_clone.py"


def load():
    spec = importlib.util.spec_from_file_location("_archive_clone_guard_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, monkeypatch, fault=None):
    module, calls, fds = load(), [], []
    source = tmp_path / "cache.tar"
    source.write_bytes(b"SYNTHETIC_ARCHIVE_ONLY" * 8)
    source.chmod(0o600)
    parent = tmp_path / "owned"
    parent.mkdir(mode=0o700)
    target = parent / "native.tar"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    def backend(source_fd, directory_fd, name):
        calls.append(name)
        fds.extend((source_fd, directory_fd))
        if fault == "backend_error":
            raise OSError("synthetic unsupported clone")
        fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=directory_fd)
        try:
            data = os.pread(source_fd, os.fstat(source_fd).st_size, 0)
            os.write(fd, b"wrong" if fault == "corrupt_target" else data)
        finally:
            os.close(fd)
        if fault == "source_changed":
            source.write_bytes(b"z" * source.stat().st_size)

    monkeypatch.setattr(module, "_call_clone", backend)
    monkeypatch.setattr(module, "_has_xattrs", lambda fd: fault == "xattrs")
    monkeypatch.setattr(module.sys, "platform", "darwin")
    return module, source, target, digest, calls, fds


def test_exact_archive_model_has_distinct_inode_and_closes_retained_fds(tmp_path, monkeypatch):
    module, source, target, digest, calls, fds = fixture(tmp_path, monkeypatch)
    result = module.clone_archive(source, target, digest)
    assert calls == [b"native.tar"] and target.read_bytes() == source.read_bytes()
    assert source.stat().st_ino != target.stat().st_ino
    assert result["sha256"] == digest and result["fallback_used"] is False
    for fd in fds:
        with pytest.raises(OSError):
            os.fstat(fd)


@pytest.mark.parametrize("fault", ["backend_error", "corrupt_target", "source_changed"])
def test_failed_clone_never_falls_back_retries_or_deletes_partial_output(
    tmp_path, monkeypatch, fault
):
    module, source, target, digest, calls, fds = fixture(tmp_path, monkeypatch, fault)
    with pytest.raises((OSError, RuntimeError)):
        module.clone_archive(source, target, digest)
    assert calls == [b"native.tar"]
    assert target.exists() is (fault != "backend_error")
    for fd in fds:
        with pytest.raises(OSError):
            os.fstat(fd)


@pytest.mark.parametrize("fault", ["digest", "permissions", "hardlink", "symlink",
                                   "existing_target", "parent_mode", "platform", "wrong_name",
                                   "xattrs"])
def test_untrusted_input_refuses_before_backend_and_preserves_existing_files(
    tmp_path, monkeypatch, fault
):
    module, source, target, digest, calls, _ = fixture(tmp_path, monkeypatch, fault)
    if fault == "digest":
        digest = "0" * 64
    if fault == "permissions":
        source.chmod(0o644)
    if fault == "hardlink":
        os.link(source, tmp_path / "alias")
    if fault == "symlink":
        link = tmp_path / "source-link"
        link.symlink_to(source)
        source = link
    if fault == "existing_target":
        target.write_bytes(b"PRESERVE")
    if fault == "parent_mode":
        target.parent.chmod(0o755)
    if fault == "platform":
        monkeypatch.setattr(module.sys, "platform", "unsupported")
    if fault == "wrong_name":
        target = target.parent / "foreign"
    with pytest.raises(RuntimeError):
        module.clone_archive(source, target, digest)
    assert calls == []
    if fault == "existing_target":
        assert target.read_bytes() == b"PRESERVE"

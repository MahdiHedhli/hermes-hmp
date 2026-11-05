"""Actual private socket fixtures; no service, connection or host content."""

from __future__ import annotations

import errno
import os
import socket
import tempfile
from pathlib import Path

import pytest

from hmp_plugin import presentation_broker_endpoint as module
from hmp_plugin.presentation_jobs import FrameError

_NATIVE_CLOSE = os.close


@pytest.fixture
def endpoint():
    if os.name != "posix" or os.getuid() == 0:
        pytest.skip("non-root POSIX endpoint fixture")
    scratch = "/private/tmp" if os.path.isdir("/private/tmp") else tempfile.gettempdir()
    with tempfile.TemporaryDirectory(prefix="hbe-", dir=scratch) as root:
        directory = Path(root) / "private"
        directory.mkdir(mode=0o700)
        path = directory / "presentation.sock"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(path))
        path.chmod(0o600)
        owners = []

        def acquire(value=None, uid=None):
            try:
                owner = module.BrokerEndpointOwner(
                    str(directory) if value is None else value,
                    expected_uid=os.getuid() if uid is None else uid,
                )
            except module.EndpointAcquisitionError as error:
                owners.append(error.failed_owner)
                raise
            owners.append(owner)
            return owner

        yield directory, path, acquire
        # Fixture-only cleanup of exact retained directory descriptors. Unknown
        # protocol close is not retried by the implementation or called success.
        for owner in owners:
            for record in owner._records:
                if type(record.fd) is not int or record.identity is None:
                    continue
                try:
                    row = os.fstat(record.fd)
                    if module._identity(row) == record.identity:
                        _NATIVE_CLOSE(record.fd)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        raise
        sock.close()


def test_real_endpoint_snapshot_and_close(endpoint):
    _, _, acquire = endpoint
    owner = acquire()
    observation = owner.observe()
    assert owner.validates(observation) is True
    assert owner.close() is True
    assert owner.close() is True
    with pytest.raises(FrameError):
        owner.observe()


@pytest.mark.parametrize(
    "value",
    [None, True, 1, "relative", "/", "/synthetic/../x", "/synthetic//x",
     "/synthetic/x/", "/synthetic/x\n"],
)
def test_invalid_startup_path_opens_nothing(endpoint, monkeypatch, value):
    calls = []
    monkeypatch.setattr(module.os, "open", lambda *a, **k: calls.append(a))
    with pytest.raises(module.EndpointAcquisitionError) as caught:
        module.BrokerEndpointOwner(value, expected_uid=os.getuid())
    assert not calls
    assert not caught.value.failed_owner._records


@pytest.mark.parametrize("uid", [True, False, 0, -1, 1.0, "1", 2**32])
def test_invalid_uid_opens_nothing(endpoint, monkeypatch, uid):
    directory, _, _ = endpoint
    calls = []
    monkeypatch.setattr(module.os, "open", lambda *a, **k: calls.append(a))
    with pytest.raises(module.EndpointAcquisitionError):
        module.BrokerEndpointOwner(str(directory), expected_uid=uid)
    assert not calls


@pytest.mark.parametrize("mode", [0o755, 0o750, 0o770, 0o1700, 0o4700])
def test_private_directory_mode_exact(endpoint, mode):
    directory, _, acquire = endpoint
    directory.chmod(mode)
    try:
        with pytest.raises(module.EndpointAcquisitionError):
            acquire()
    finally:
        directory.chmod(0o700)


@pytest.mark.parametrize("mode", [0o666, 0o640, 0o1600, 0o4600])
def test_socket_mode_exact(endpoint, mode):
    _, path, acquire = endpoint
    path.chmod(mode)
    with pytest.raises(module.EndpointAcquisitionError):
        acquire()


def test_missing_endpoint_is_distinct_no_creation(endpoint):
    _, path, acquire = endpoint
    path.unlink()
    with pytest.raises(module.EndpointAcquisitionError, match="ENDPOINT_MISSING") as caught:
        acquire()
    assert not path.exists()
    assert caught.value.failed_owner.close() is True


@pytest.mark.parametrize("kind", ["regular", "directory", "symlink"])
def test_socket_type_refused(endpoint, kind):
    _, path, acquire = endpoint
    path.unlink()
    if kind == "regular":
        path.write_text("synthetic")
    elif kind == "directory":
        path.mkdir()
    else:
        path.symlink_to("missing")
    with pytest.raises(module.EndpointAcquisitionError):
        acquire()


def test_ancestor_symlink_refused(endpoint):
    directory, _, acquire = endpoint
    alias = directory.parent / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    with pytest.raises(module.EndpointAcquisitionError, match="UNAVAILABLE"):
        acquire(str(alias))


@pytest.mark.parametrize("mode", [0o770, 0o777, 0o1777])
def test_user_writable_ancestor_not_exempted_by_sticky(endpoint, mode):
    directory, _, acquire = endpoint
    directory.parent.chmod(mode)
    try:
        with pytest.raises(module.EndpointAcquisitionError):
            acquire()
    finally:
        directory.parent.chmod(0o700)


def test_retained_directory_renamed_and_replaced_refuses(endpoint):
    directory, _, acquire = endpoint
    owner = acquire()
    observation = owner.observe()
    moved = directory.with_name("moved")
    directory.rename(moved)
    directory.mkdir(mode=0o700)
    with pytest.raises(FrameError):
        owner.validates(observation)
    directory.rmdir()
    moved.rename(directory)
    with pytest.raises(FrameError):
        owner.observe()
    assert owner.close() is True


def test_socket_replaced_and_restored_stays_refused(endpoint):
    _, path, acquire = endpoint
    owner = acquire()
    moved = path.with_name("old.sock")
    path.rename(moved)
    other = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        other.bind(str(path))
        path.chmod(0o600)
        with pytest.raises(FrameError):
            owner.observe()
        path.unlink()
        moved.rename(path)
        with pytest.raises(FrameError):
            owner.observe()
    finally:
        other.close()
    assert owner.close() is True


def test_post_acquisition_socket_disappearance_not_missing_admission(endpoint):
    _, path, acquire = endpoint
    owner = acquire()
    path.unlink()
    with pytest.raises(FrameError, match="UNAVAILABLE"):
        owner.observe()
    assert owner.close() is True


def test_observation_must_be_exact_owner_minted(endpoint):
    _, _, acquire = endpoint
    a, b = acquire(), acquire()
    observed = a.observe()
    b.observe()
    with pytest.raises(FrameError):
        b.validates(observed)
    assert a.validates(observed) is True
    assert a.close() is True
    assert b.close() is True


def test_old_observation_retires_after_new_snapshot(endpoint):
    _, _, acquire = endpoint
    owner = acquire()
    old = owner.observe()
    owner.observe()
    with pytest.raises(FrameError):
        owner.validates(old)
    assert owner.close() is True


def test_partial_open_retained_before_failure(endpoint, monkeypatch):
    _, _, acquire = endpoint
    real_open = os.open
    calls = []

    def fail(*args, **kwargs):
        calls.append(args[0])
        if len(calls) == 3:
            raise OSError(errno.EIO, "synthetic")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(module.os, "open", fail)
    with pytest.raises(module.EndpointAcquisitionError) as caught:
        acquire()
    owner = caught.value.failed_owner
    assert len(owner._records) == 3
    assert owner._records[-1].fd is None
    assert len(owner._seals) == 2
    assert owner.close() is False
    assert all(r.closed for r in owner._records[:-1])


def test_descriptor_bool_never_reaches_fstat(endpoint, monkeypatch):
    _, _, acquire = endpoint
    monkeypatch.setattr(module.os, "open", lambda *a, **k: True)
    real_fstat = os.fstat

    def fstat(fd):
        if type(fd) is bool:
            pytest.fail("coerced descriptor")
        return real_fstat(fd)

    monkeypatch.setattr(module.os, "fstat", fstat)
    with pytest.raises(module.EndpointAcquisitionError):
        acquire()


def test_close_noop_does_not_produce_fact_or_retry(endpoint, monkeypatch):
    _, _, acquire = endpoint
    owner = acquire()
    calls = []
    monkeypatch.setattr(module.os, "close", lambda fd: calls.append(fd))
    assert owner.close() is False
    assert len(calls) == len(owner._records)
    assert owner.close() is False
    assert len(calls) == len(owner._records)


def test_ambiguous_close_after_effect_not_retried(endpoint, monkeypatch):
    _, _, acquire = endpoint
    owner = acquire()
    calls = []

    def fail(fd):
        calls.append(fd)
        _NATIVE_CLOSE(fd)
        raise OSError(errno.EINTR, "synthetic")

    monkeypatch.setattr(module.os, "close", fail)
    assert owner.close() is False
    assert owner.close() is False
    assert len(calls) == len(owner._records)


def test_retarged_descriptor_is_not_closed(endpoint, monkeypatch):
    _, _, acquire = endpoint
    a, b = acquire(), acquire()
    original = a._records[-1].fd
    a._records[-1].fd = a._records[-1].original_fd = b._records[-1].fd
    calls = []
    real_close = os.close

    def close(fd):
        calls.append(fd)
        real_close(fd)

    monkeypatch.setattr(module.os, "close", close)
    assert a.close() is False
    assert b._records[-1].fd not in calls
    assert b.validates(b.observe()) is True
    a._records[-1].fd = a._records[-1].original_fd = original
    assert a.close() is False
    assert original not in calls
    assert b.close() is True


def test_wrong_startup_uid_refused(endpoint):
    _, _, acquire = endpoint
    with pytest.raises(module.EndpointAcquisitionError):
        acquire(uid=os.getuid() + 1)


def test_socket_wrong_uid_refused(endpoint, monkeypatch):
    _, _, acquire = endpoint
    real_stat = os.stat

    def stat_row(path, *args, **kwargs):
        row = real_stat(path, *args, **kwargs)
        if path == "presentation.sock":
            fields = list(row)
            fields[4] = os.getuid() + 1
            return os.stat_result(fields)
        return row

    monkeypatch.setattr(module.os, "stat", stat_row)
    with pytest.raises(module.EndpointAcquisitionError):
        acquire()


def test_ancestor_replaced_during_acquisition_refused(endpoint, monkeypatch):
    directory, _, acquire = endpoint
    parent = directory.parent
    moved = parent.with_name(parent.name + "-moved")
    real_open = os.open
    changed = False

    def open_dir(name, *args, **kwargs):
        nonlocal changed
        fd = real_open(name, *args, **kwargs)
        if name == "private":
            parent.rename(moved)
            parent.mkdir(mode=0o700)
            changed = True
        return fd

    monkeypatch.setattr(module.os, "open", open_dir)
    try:
        with pytest.raises(module.EndpointAcquisitionError, match="UNAVAILABLE"):
            acquire()
    finally:
        if changed:
            parent.rmdir()
            moved.rename(parent)


def test_actual_descriptor_reuse_does_not_close_replacement(endpoint, monkeypatch):
    directory, _, acquire = endpoint
    owner = acquire()
    descriptor = owner._records[-1].fd
    replacement = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    os.dup2(replacement, descriptor, inheritable=False)
    _NATIVE_CLOSE(replacement)
    calls = []

    def close(fd):
        calls.append(fd)
        _NATIVE_CLOSE(fd)

    monkeypatch.setattr(module.os, "close", close)
    try:
        assert owner.close() is False
        assert descriptor not in calls
        assert os.fstat(descriptor).st_ino == directory.parent.stat().st_ino
    finally:
        # This reused slot is solely this test's explicit dup2-owned descriptor.
        _NATIVE_CLOSE(descriptor)


@pytest.mark.parametrize("action", ["observe", "close"])
def test_foreign_original_fd_never_compares_or_reaches_syscall(endpoint, action):
    _, _, acquire = endpoint
    owner = acquire()

    class Foreign:
        def __eq__(self, other):
            pytest.fail("foreign descriptor equality executed")

    owner._records[-1].original_fd = Foreign()
    if action == "close":
        assert owner.close() is False
    else:
        with pytest.raises(FrameError):
            owner.observe()


@pytest.mark.parametrize("action", ["observe", "close"])
@pytest.mark.parametrize("field", ["_records", "_record_refs", "_seals"])
def test_foreign_container_never_traversed(endpoint, action, field):
    _, _, acquire = endpoint
    owner = acquire()
    original = getattr(owner, field)

    class Foreign:
        def __len__(self):
            pytest.fail("foreign container length executed")

        def __iter__(self):
            pytest.fail("foreign container iteration executed")

    setattr(owner, field, Foreign())
    try:
        if action == "close":
            assert owner.close() is False
        else:
            with pytest.raises(FrameError):
                owner.observe()
    finally:
        setattr(owner, field, original)

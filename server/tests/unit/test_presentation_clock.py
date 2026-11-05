"""Native own-host primitives plus causal clock models, not runtime admission.

Shared channel fixture deliberately mocks kernel peer identity. Linux fault
models mock native APIs; they cannot qualify a real Linux peer or namespace.
"""

import contextlib
import dataclasses
import errno
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import presentation_clock as clock
from hmp_plugin.presentation_broker_codec import BrokerBinding
from hmp_plugin.presentation_broker_endpoint import BrokerEndpointOwner
from hmp_plugin.presentation_broker_service import SocketChannel, StartupEnrollment
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import local as local
from .test_presentation_terminal_status import gateway as gateway

BOOT = b"12345678-1234-1234-1234-123456789abc"


def darwin_model(monkeypatch):
    monkeypatch.setattr(clock, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(clock, "_darwin_boot", lambda: BOOT)
    monkeypatch.setattr(clock.NativeClockOwner, "_implementation",
                        lambda self: "mach_absolute_time()")


@pytest.mark.asyncio
async def test_retained_clock_samples_are_native_and_close_cannot_release_channel(
    gateway, monkeypatch
):
    channel, _, _ = gateway
    darwin_model(monkeypatch)
    owner = clock.NativeClockOwner(channel)
    assert owner.sample() >= owner._last_ns
    assert owner._domain.boot == BOOT and owner._domain.namespace is None
    assert BOOT.decode() not in repr(owner) + repr(owner._domain)
    with pytest.raises(dataclasses.FrozenInstanceError):
        owner._domain.boot = b"x"
    assert owner.close_local() is True
    assert channel._closed_known is False and channel._refused is False
    with pytest.raises(FrameError):
        owner.sample()


@pytest.mark.asyncio
@pytest.mark.parametrize("drift", ["boot", "peer", "channel_values", "domain", "context",
                                   "platform", "backward", "negative", "overflow", "bool"])
async def test_drift_poisons_original_clock_and_never_recovers(gateway, monkeypatch, drift):
    channel, _, _ = gateway
    darwin_model(monkeypatch)
    owner = clock.NativeClockOwner(channel)
    if drift == "boot":
        monkeypatch.setattr(clock, "_darwin_boot", lambda: b"0" * 36)
    elif drift == "peer":
        monkeypatch.setattr(channel, "_check", lambda: clock.PeerObservation(1, 1))
    elif drift == "channel_values":
        owner._channel_values = tuple(v for v in owner._channel_values)
    elif drift == "domain":
        owner._domain = dataclasses.replace(owner._domain)
    elif drift == "context":
        owner._context = (0, 0, 0)
    elif drift == "platform":
        monkeypatch.setattr(clock, "sys", SimpleNamespace(platform="linux"))
    else:
        value = {"backward": owner._last_ns - 1, "negative": -1,
                 "overflow": clock.MAX_NS + 1, "bool": True}[drift]
        monkeypatch.setattr(clock, "_MONOTONIC_NS", lambda: value)
    with pytest.raises(FrameError) as error:
        owner.sample()
    assert str(error.value) == "BI1_NATIVE_CLOCK_UNAVAILABLE"
    assert owner._refused is True
    with pytest.raises(FrameError):
        owner.sample()


def test_selected_provider_guard_rejects_replacement_and_wrong_implementation(monkeypatch):
    owner = clock.NativeClockOwner.__new__(clock.NativeClockOwner)
    owner._platform = "darwin"
    monkeypatch.setattr(clock.time, "monotonic_ns", lambda: 1)
    with pytest.raises(FrameError):
        owner._implementation()


@pytest.mark.parametrize("value", [b"", b"x" * 36, bytearray(BOOT), BOOT + b"\n", b"0" * 37])
def test_boot_grammar_never_coerces(value):
    with pytest.raises(FrameError):
        clock._uuid(value)


@pytest.mark.skipif(sys.platform != "darwin", reason="native fixed Darwin kernel observation")
def test_actual_darwin_boot_and_clock_implementation_without_disclosing_uuid():
    before = clock._darwin_boot()
    assert len(before) == 36 and clock._darwin_boot() == before
    owner = clock.NativeClockOwner.__new__(clock.NativeClockOwner)
    owner._platform = "darwin"
    assert owner._implementation() == "mach_absolute_time()"


class LinuxModel:
    def __init__(self, channel, monkeypatch):
        self.nextfd = 1000
        self.entries = {}
        self.closed = []
        self.paths = []
        self.live_calls = 0
        self.dead_on = None
        self.fail_open = self.bad_fs = None
        self.close_error = None
        self.namespace_drift = False
        self.boot = BOOT + b"\n"
        self.peer_pid = channel._check().pid
        monkeypatch.setattr(clock, "sys", SimpleNamespace(platform="linux"))
        monkeypatch.setattr(clock.NativeClockOwner, "_implementation",
                            lambda self: "clock_gettime(CLOCK_MONOTONIC)")
        api = SimpleNamespace(**{name: getattr(os, name) for name in (
            "getpid", "geteuid", "O_RDONLY", "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "SEEK_SET"
        )})
        api.open = self.open
        api.close = self.close
        api.stat = self.stat
        api.fstat = self.fstat
        api.lseek = lambda *args: 0
        api.read = lambda *args: self.boot
        api.uname = lambda: SimpleNamespace(machine="x86_64")
        monkeypatch.setattr(clock, "os", api)
        monkeypatch.setattr(clock, "_GETSOCKOPT", self.pidfd)
        monkeypatch.setattr(clock, "_identity", self.identity)
        monkeypatch.setattr(clock, "_filesystem", self.filesystem)
        monkeypatch.setattr(clock, "select",
                            SimpleNamespace(poll=self.poll, POLLIN=1, POLLHUP=16, POLLERR=8))

    def acquire(self, name):
        self.nextfd += 1
        self.entries[self.nextfd] = name
        return self.nextfd

    def pidfd(self, sock, level, option):
        assert type(sock) is socket.socket and level == socket.SOL_SOCKET and option == 77
        return self.acquire("pidfd")

    def open(self, name, flags, *, dir_fd):
        self.paths.append(name)
        if name == self.fail_open:
            raise OSError(errno.EACCES, "synthetic refusal")
        assert flags & os.O_CLOEXEC
        if name.endswith("/ns/time"):
            assert not flags & os.O_NOFOLLOW
        return self.acquire(name)

    def identity(self, fd):
        assert fd not in self.closed
        name = self.entries[fd]
        return (4, 200 if name.endswith("/ns/time") else fd, 0o100444)

    def fstat(self, fd):
        if fd in self.closed:
            raise OSError(errno.EBADF, "synthetic closed")
        return SimpleNamespace(st_dev=4, st_ino=fd, st_mode=0o100444)

    def filesystem(self, fd):
        name = self.entries[fd]
        if name == self.bad_fs:
            return 0
        return (clock._NSFS if name.endswith("/ns/time") else
                0x09041934 if name == "pidfd" else clock._PROCFS)

    def stat(self, name, **kwargs):
        assert name in ("self/ns/time", f"{self.peer_pid}/ns/time")
        inode = 201 if self.namespace_drift else 200
        return SimpleNamespace(st_dev=4, st_ino=inode, st_mode=0o100444)

    def poll(self):
        model = self
        class Poll:
            def register(self, fd, flags):
                assert model.entries[fd] == "pidfd"
            def poll(self, timeout):
                assert timeout == 0
                model.live_calls += 1
                return [(1002, 1)] if model.live_calls == model.dead_on else []
        return Poll()

    def close(self, fd):
        self.closed.append(fd)
        if fd == self.close_error:
            raise OSError(errno.EINTR, "synthetic ambiguous close")


@pytest.mark.asyncio
async def test_linux_matches_actual_namespace_not_children_and_retains_all_fds(
    gateway, monkeypatch
):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    assert owner._domain.namespace == (4, 200)
    assert owner.sample() >= owner._last_ns
    assert model.paths == ["/proc", "sys/kernel/random/boot_id", "self/ns/time",
                           f"{model.peer_pid}/ns/time"]
    assert len(owner._records) == 5
    assert owner.close_local() and len(model.closed) == 5
    assert owner.close_local() and len(model.closed) == 5


@pytest.mark.asyncio
@pytest.mark.parametrize("point", [1, 2, 3, 4, 5])
async def test_dead_peer_at_each_initialization_boundary_refuses(gateway, monkeypatch, point):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    model.dead_on = point
    with pytest.raises(clock.ClockAcquisitionError) as error:
        clock.NativeClockOwner(channel)
    owner = error.value.failed_owner
    assert owner._refused
    assert owner.close_local()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["proc", "boot", "namespace", "pidfd", "malformed_boot",
                                     "namespace_drift", "missing_namespace", "missing_pidfd"])
async def test_linux_missing_origin_api_or_common_domain_never_falls_back(
    gateway, monkeypatch, failure
):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    if failure in ("proc", "boot", "namespace", "pidfd"):
        model.bad_fs = {"proc": "/proc", "boot": "sys/kernel/random/boot_id",
                        "namespace": "self/ns/time", "pidfd": "pidfd"}[failure]
    elif failure == "malformed_boot":
        model.boot = b"x" * 38
    elif failure == "namespace_drift":
        model.namespace_drift = True
    elif failure == "missing_namespace":
        model.fail_open = f"{model.peer_pid}/ns/time"
    else:
        def unsupported(*args):
            raise OSError(errno.ENOPROTOOPT, "synthetic unsupported kernel")
        monkeypatch.setattr(clock, "_GETSOCKOPT", unsupported)
    with pytest.raises(clock.ClockAcquisitionError) as error:
        clock.NativeClockOwner(channel)
    assert error.value.failed_owner.close_local()


@pytest.mark.asyncio
async def test_partial_fstat_and_close_ambiguity_remain_retained_without_retry(
    gateway, monkeypatch
):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    model.close_error = owner._pidfd.fd
    assert owner.close_local() is False
    assert owner._pidfd.unknown and owner._pidfd.close_attempted
    assert owner.close_local() is False
    assert len(model.closed) == 5 and model.closed.count(model.close_error) == 1


@pytest.mark.asyncio
async def test_fd_validation_failure_retains_exact_partial_without_unsafe_close(
    gateway, monkeypatch
):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    def refuse(fd):
        raise OSError(errno.EBADF, "synthetic fstat failure")
    monkeypatch.setattr(clock, "_identity", refuse)
    with pytest.raises(clock.ClockAcquisitionError) as error:
        clock.NativeClockOwner(channel)
    owner = error.value.failed_owner
    assert len(owner._records) == 1 and owner._records[0].fd == 1001
    assert owner.close_local() is False and not model.closed


@pytest.mark.asyncio
async def test_noop_close_never_becomes_known_closure(gateway, monkeypatch):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    calls = []
    monkeypatch.setattr(clock.os, "close", lambda fd: calls.append(fd))
    assert owner.close_local() is False
    assert owner.close_local() is False
    assert len(calls) == 5 and model.closed == []
    assert all(record.unknown and not record.closed for record in owner._record_refs)


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["close", "nested_sample"])
async def test_swallowed_clock_reentry_cannot_publish_sample(gateway, monkeypatch, action):
    channel, _, _ = gateway
    darwin_model(monkeypatch)
    owner = clock.NativeClockOwner(channel)
    original = owner._last_ns
    def reenter():
        with contextlib.suppress(FrameError):
            owner.close_local() if action == "close" else owner.sample()
        return original + 1
    monkeypatch.setattr(clock, "_MONOTONIC_NS", reenter)
    with pytest.raises(FrameError):
        owner.sample()
    assert owner._last_ns == original and owner._refused


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["fd", "original_fd", "identity", "record", "context",
                                   "seals", "records", "last_ns"])
async def test_foreign_metadata_refuses_before_callbacks(gateway, monkeypatch, field):
    channel, _, _ = gateway
    LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    touched = []
    class Foreign:
        def __eq__(self, other):
            touched.append("eq")
            return True
        def __iter__(self):
            touched.append("iter")
            return iter(())
        def __len__(self):
            touched.append("len")
            return 0
        def __bool__(self):
            touched.append("bool")
            return True
        def __lt__(self, other):
            touched.append("lt")
            return False
    value = Foreign()
    if field in ("fd", "original_fd", "identity"):
        setattr(owner._pidfd, field, value)
    elif field == "record":
        owner._records[0] = value
    elif field == "context":
        owner._context = owner._context_snapshot = value
    elif field == "seals":
        owner._seals = owner._seals_snapshot = value
    elif field == "records":
        owner._records = owner._records_snapshot = value
    else:
        owner._last_ns = value
    with pytest.raises(FrameError):
        owner.sample()
    if field != "last_ns":
        with pytest.raises(FrameError):
            owner.close_local()
    assert touched == []


@pytest.mark.skipif(sys.platform != "linux", reason="native Linux own-process primitives only")
def test_actual_linux_pidfd_procfs_and_active_namespace_without_foreign_process():
    """Own-process primitive qualification; not remote enrollment/service proof."""
    if not hasattr(os, "pidfd_open"):
        pytest.skip("native pidfd unavailable")
    left, right = socket.socketpair()
    owner = clock.NativeClockOwner.__new__(clock.NativeClockOwner)
    owner._channel = SimpleNamespace(_socket_snapshot=left)
    owner._peer = clock.PeerObservation(os.geteuid(), os.getpid())
    owner._records = owner._records_snapshot = []
    owner._record_refs = owner._seals = owner._seals_snapshot = ()
    owner._proc = owner._pidfd = owner._bootfd = owner._ownns = owner._peerns = None
    owner._context = owner._context_snapshot = (
        os.getpid(), os.geteuid(), clock.threading.get_ident())
    owner._refused = owner._closing = owner._closed_known = False
    owner._sampling = owner._close_running = owner._close_reentered = False
    owner._platform = owner._platform_snapshot = sys.platform
    try:
        try:
            owner._linux_initialize()
        except OSError as error:
            if error.errno in (errno.ENOPROTOOPT, errno.EINVAL, errno.ENOSYS, errno.EACCES):
                pytest.skip("required kernel/procfs API unavailable; no qualification")
            raise
        assert owner._ownns.identity[:2] == owner._peerns.identity[:2]
        assert len(owner._linux_boot()) == 36
        owner._linux_current()
    finally:
        assert owner.close_local()
        left.close()
        right.close()


@pytest.mark.skipif(sys.platform not in ("darwin", "linux") or os.geteuid() == 0,
                    reason="native nonroot private connected-channel clock fixture")
def test_actual_separate_process_peer_and_common_clock_without_work():
    """One exact owned helper; no broker work, manager, profile or v2 activation."""
    temporary = "/private/tmp" if sys.platform == "darwin" else tempfile.gettempdir()
    root = Path(tempfile.mkdtemp(prefix="hc-", dir=temporary)).resolve()
    path = str(root / "presentation.sock")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.settimeout(5)
    child = endpoint = channel = remote = owner = None
    try:
        listener.bind(path)
        os.chmod(path, 0o600)
        listener.listen(1)
        endpoint = BrokerEndpointOwner(str(root), expected_uid=os.geteuid())
        program = (
            "import socket,sys; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);"
            "s.settimeout(5); s.connect(sys.argv[1]); s.sendall(b'R');"
            "assert s.recv(1)==b''; s.close()"
        )
        child = subprocess.Popen([sys.executable, "-I", "-B", "-S", "-c", program, path],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        remote, _ = listener.accept()
        remote.settimeout(5)
        assert remote.recv(1) == b"R"
        binding = BrokerBinding("a" * 52, "1" * 32, "2" * 64, "3" * 64, "4" * 64)
        enrollment = StartupEnrollment(binding, os.geteuid(), child.pid,
                                       os.geteuid(), os.getpid(), "5" * 64)
        channel = SocketChannel(remote, enrollment, role="broker", endpoint=endpoint,
                                observation=endpoint.observe())
        try:
            owner = clock.NativeClockOwner(channel)
        except clock.ClockAcquisitionError as error:
            owner = error.failed_owner
            cause = error.__context__
            if (sys.platform == "linux" and isinstance(cause, OSError)
                    and cause.errno in (errno.ENOPROTOOPT, errno.ENOSYS, errno.EACCES)):
                pytest.skip("required native API unavailable; no common-clock qualification")
            raise
        assert owner._peer_values == (os.geteuid(), child.pid)
        assert owner.sample() >= owner._last_ns
        assert owner.close_local()
        assert not channel._closed_known
        channel.close()
        stdout, stderr = child.communicate(timeout=5)
        assert child.returncode == 0 and stdout == stderr == b""
    finally:
        if owner is not None:
            assert owner.close_local()
        if channel is not None:
            channel.close()
        if remote is not None:
            remote.close()
        listener.close()
        if child is not None:
            if child.poll() is None:
                # Test-owned Popen identity only; never numeric PID/group signal.
                child.kill()
            child.communicate(timeout=5)
        if endpoint is not None:
            assert endpoint.close()
        shutil.rmtree(root)

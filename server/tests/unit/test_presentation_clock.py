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
from hmp_plugin.presentation_broker_service import (
    ChannelAcquisitionError,
    SocketChannel,
    StartupEnrollment,
)
from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationBudget
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
        self.info = f"Pid:\t{os.getpid()}\nNSpid:\t{os.getpid()}\n".encode("ascii")
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
        api.read = self.read
        api.pidfd_open = self.self_pidfd
        api.uname = lambda: SimpleNamespace(machine="x86_64")
        monkeypatch.setattr(clock, "os", api)
        monkeypatch.setattr(clock, "_GETSOCKOPT", self.pidfd)
        monkeypatch.setattr(clock, "_identity", self.identity)
        monkeypatch.setattr(clock, "_filesystem", self.filesystem)
        monkeypatch.setattr(clock, "_namespace_kind", lambda fd: 0x80)
        monkeypatch.setattr(clock, "select",
                            SimpleNamespace(poll=self.poll, POLLIN=1, POLLHUP=16, POLLERR=8))

    def acquire(self, name):
        self.nextfd += 1
        self.entries[self.nextfd] = name
        return self.nextfd

    def pidfd(self, sock, level, option):
        assert type(sock) is socket.socket and level == socket.SOL_SOCKET and option == 77
        return self.acquire("pidfd")

    def self_pidfd(self, pid, flags):
        assert pid == os.getpid() and flags == 0
        return self.acquire("ownpidfd")

    def read(self, fd, count):
        if self.entries[fd].startswith("self/fdinfo/"):
            assert count == clock._FDINFO_LIMIT + 1
            return self.info
        assert count == 38
        return self.boot

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
                0x09041934 if name in ("pidfd", "ownpidfd") else clock._PROCFS)

    def stat(self, name, **kwargs):
        if name.startswith("self/fdinfo/"):
            fd = next(fd for fd, value in self.entries.items() if value == name)
            return SimpleNamespace(st_dev=4, st_ino=fd, st_mode=0o100444)
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
    assert model.paths == ["/proc", "sys/kernel/random/boot_id",
                           f"self/fdinfo/{owner._own_pidfd.fd}", "self/ns/time",
                           f"{model.peer_pid}/ns/time"]
    assert len(owner._records) == 7
    assert owner.close_local() and len(model.closed) == 7
    assert owner.close_local() and len(model.closed) == 7


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
    assert len(model.closed) == 7 and model.closed.count(model.close_error) == 1


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
    assert len(calls) == 7 and model.closed == []
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
    owner._local_lost = owner._cleanup_started = False
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
@pytest.mark.parametrize("protocol_version", [1, 2])
def test_actual_separate_process_peer_and_common_clock_without_work(protocol_version):
    """One exact owned helper; selected clock only, no broker work/manager/profile."""
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
                                       os.geteuid(), os.getpid(), "5" * 64, protocol_version)
        try:
            channel = SocketChannel(remote, enrollment, role="broker", endpoint=endpoint,
                                    observation=endpoint.observe())
            owner = (channel._clock_owner if protocol_version == 2
                     else clock.NativeClockOwner(channel))
        except (clock.ClockAcquisitionError, ChannelAcquisitionError) as error:
            # Capture every partially allocated owner before inspecting a known
            # native unsupported-API cause; never discard a v2 clock allocation.
            if isinstance(error, clock.ClockAcquisitionError):
                owner = error.failed_owner
            else:
                channel = error.failed_owner
                owner = channel._clock_owner
            cause = error.__context__
            if isinstance(cause, clock.ClockAcquisitionError):
                cause = cause.__context__
            if (sys.platform == "linux" and isinstance(cause, OSError)
                    and cause.errno in (errno.ENOPROTOOPT, errno.ENOSYS, errno.EACCES)):
                pytest.skip("required native API unavailable; no common-clock qualification")
            raise
        assert owner._peer_values == (os.geteuid(), child.pid)
        assert owner.sample() >= owner._last_ns
        budget = CancellationBudget(owner._last_ns + 1_000_000_000)
        first = budget.local(owner.cleanup_sample())  # retire work before closing transport
        assert not channel._closed_known
        channel.close()
        stdout, stderr = child.communicate(timeout=5)
        assert child.returncode == 0 and stdout == stderr == b""
        now = owner.cleanup_sample()  # exact original helper is gone; no peer clock call
        assert budget.local(now) == first
        assert budget.remaining_ns(now) <= CLEANUP_NS
        with pytest.raises(FrameError):
            owner.sample()
        assert owner.cleanup_sample() >= now
        assert owner.close_local()
        assert channel.close_clock()
    finally:
        if owner is not None:
            assert owner.close_local()
        if channel is not None:
            channel.close()
            assert channel.close_clock()
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


@pytest.mark.asyncio
async def test_cleanup_clock_survives_closed_peer_and_never_revives_work(gateway, monkeypatch):
    channel, remote, _ = gateway
    darwin_model(monkeypatch)
    owner = clock.NativeClockOwner(channel)
    previous = owner._last_ns
    remote.close()
    assert channel.close()
    def no_peer():
        pytest.fail("local cleanup time must not consult a closed peer")
    monkeypatch.setattr(channel, "_check", no_peer)
    assert owner.cleanup_sample() >= previous
    assert owner._cleanup_started and owner._refused and not owner._local_lost
    with pytest.raises(FrameError):
        owner.sample()
    assert owner.cleanup_sample() >= owner._last_ns
    assert owner.close_local()


@pytest.mark.asyncio
async def test_generic_channel_refusal_cannot_be_reclassified_peer_only(gateway, monkeypatch):
    channel, _, _ = gateway
    darwin_model(monkeypatch)
    owner = clock.NativeClockOwner(channel)
    def refused():
        raise FrameError("synthetic peer unavailable")
    monkeypatch.setattr(channel, "_check", refused)
    with pytest.raises(FrameError):
        owner.sample()
    assert owner._refused and owner._local_lost
    with pytest.raises(FrameError):
        owner.cleanup_sample()
    assert owner.close_local()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["boot", "provider", "backward", "context", "reentry",
                                     "ambiguous_peer_exception", "local_fd", "domain_values"])
async def test_local_failures_cannot_requalify_for_cleanup(gateway, monkeypatch, failure):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    original_clock = clock._MONOTONIC_NS
    original_boot = model.boot
    if failure == "boot":
        model.boot = b"0" * 37
    elif failure == "provider":
        def wrong_provider(self):
            raise FrameError("synthetic provider changed")
        monkeypatch.setattr(clock.NativeClockOwner, "_implementation", wrong_provider)
    elif failure == "backward":
        monkeypatch.setattr(clock, "_MONOTONIC_NS", lambda: owner._last_ns - 1)
    elif failure == "context":
        owner._context = (0, 0, 0)
    elif failure == "reentry":
        def recursive():
            with contextlib.suppress(FrameError):
                owner.cleanup_sample()
            return owner._last_ns + 1
        monkeypatch.setattr(clock, "_MONOTONIC_NS", recursive)
    elif failure == "ambiguous_peer_exception":
        def uncertain():
            raise RuntimeError("synthetic unexpected native boundary")
        monkeypatch.setattr(channel, "_check", uncertain)
    elif failure == "local_fd":
        model.closed.append(owner._ownns.fd)
    else:
        object.__setattr__(owner._domain, "boot", bytes(bytearray(BOOT)))
    with pytest.raises(FrameError):
        owner.sample()
    assert owner._local_lost and owner._refused
    # Restoration of native observations is not a new qualification.
    model.boot = original_boot
    owner._context = owner._context_snapshot
    monkeypatch.setattr(clock, "_MONOTONIC_NS", original_clock)
    with pytest.raises(FrameError):
        owner.cleanup_sample()


@pytest.mark.asyncio
async def test_cleanup_uses_original_own_namespace_without_peer_lookup(gateway, monkeypatch):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    own_stat = model.stat
    paths = []
    def only_local(path, **kwargs):
        paths.append(path)
        assert path == "self/ns/time" or path.startswith("self/fdinfo/")
        return own_stat(path, **kwargs)
    monkeypatch.setattr(clock.os, "stat", only_local)
    monkeypatch.setattr(owner, "_live", lambda: pytest.fail("no peer liveness for local time"))
    assert owner.cleanup_sample() >= owner._last_ns
    assert paths == [f"self/fdinfo/{owner._own_pidfd.fd}", "self/ns/time"]
    model.namespace_drift = True
    with pytest.raises(FrameError):
        owner.cleanup_sample()
    assert owner._local_lost
    model.namespace_drift = False
    with pytest.raises(FrameError):
        owner.cleanup_sample()
    assert owner.close_local()


@pytest.mark.asyncio
async def test_partial_initialization_never_qualifies_cleanup(gateway, monkeypatch):
    channel, _, _ = gateway
    darwin_model(monkeypatch)
    monkeypatch.setattr(clock, "_darwin_boot", lambda: b"bad")
    # Domain is frozen, but bootstrap peer failure must still prevent qualification.
    def refuse():
        raise FrameError("synthetic initialization peer refusal")
    monkeypatch.setattr(channel, "_check", refuse)
    with pytest.raises(clock.ClockAcquisitionError) as error:
        clock.NativeClockOwner(channel)
    owner = error.value.failed_owner
    assert owner._qualification is None
    with pytest.raises(FrameError):
        owner.cleanup_sample()
    assert owner.close_local()


@pytest.mark.asyncio
async def test_typed_dead_peer_keeps_only_original_local_cleanup_clock(gateway, monkeypatch):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    model.dead_on = model.live_calls + 1
    with pytest.raises(FrameError):
        owner.sample()
    assert owner._refused and not owner._local_lost
    calls = model.live_calls
    assert owner.cleanup_sample() >= owner._last_ns
    assert model.live_calls == calls  # no peer liveness/namespace path in local cleanup
    assert owner.close_local()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["context", "socket", "unexpected"])
async def test_actual_channel_local_or_wrapped_unknown_failure_poison_cleanup(
    gateway, monkeypatch, failure
):
    channel, _, _ = gateway
    darwin_model(monkeypatch)
    owner = clock.NativeClockOwner(channel)
    if failure == "context":
        channel._context = (0, 0)
    elif failure == "socket":
        channel._socket = object()
    else:
        def unexpected():
            raise RuntimeError("synthetic underlying channel failure")
        monkeypatch.setattr(channel._endpoint, "validates", lambda *args: unexpected())
    with pytest.raises(FrameError):
        owner.sample()  # actual SocketChannel._check wraps the cause
    assert owner._local_lost
    with pytest.raises(FrameError):
        owner.cleanup_sample()
    # Restore test metadata so the fixture can retire its original owned socket.
    channel._context = channel._context_snapshot
    channel._socket = channel._socket_snapshot
    assert owner.close_local()


def test_self_pidfd_fdinfo_realm_accepts_only_current_single_namespace():
    clock._pid_realm(b"pos:\t0\nflags:\t02000002\nPid:\t123\nNSpid:\t123\n", 123)


@pytest.mark.parametrize("data", [
    b"Pid:\t123\nNSpid:\t123\t123\n",  # identical numbers still span two realms
    b"Pid:\t321\nNSpid:\t123\n",
    b"Pid:\t123\nNSpid:\t321\n",
    b"Pid:\t123\nNSpid:\t0\n",
    b"Pid:\t123\n", b"NSpid:\t123\n",
    b"Pid:\t123\nPid:\t123\nNSpid:\t123\n",
    b"Pid:\t123\nNSpid:\t123\nNSpid:\t123\n",
    b"Pid:\t123 extra\nNSpid:\t123\n",
    b"Pid:\t123\nNSpid:\t123",
    b"Pid:\t+123\nNSpid:\t123\n",
    b"Pid:\t0123\nNSpid:\t123\n",
    b"Pid:\t123\r\nNSpid:\t123\n",
    b"Pid:\t123\nNSpid:\t123\ninvalid\n",
    b"Pid:\t123\nNSpid:\t123\nextra:\t\xff\n",
    b"x" * 2049,
    bytearray(b"Pid:\t123\nNSpid:\t123\n"), None,
])
def test_self_realm_malformed_ancestor_or_truncated_metadata_refuses(data):
    with pytest.raises(FrameError):
        clock._pid_realm(data, 123)


@pytest.mark.asyncio
async def test_foreign_pid_proc_view_refuses_before_numeric_peer_path(gateway, monkeypatch):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    model.info = f"Pid:\t{os.getpid()}\nNSpid:\t{os.getpid()}\t{os.getpid()}\n".encode()
    with pytest.raises(clock.ClockAcquisitionError) as error:
        clock.NativeClockOwner(channel)
    owner = error.value.failed_owner
    assert f"{model.peer_pid}/ns/time" not in model.paths
    assert "self/ns/time" not in model.paths
    assert owner._qualification is None and owner.close_local()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["realm_drift", "wrong_namespace_type", "fdinfo_origin"])
async def test_realm_or_namespace_kind_loss_is_permanent_local_poison(
    gateway, monkeypatch, failure
):
    channel, _, _ = gateway
    model = LinuxModel(channel, monkeypatch)
    owner = clock.NativeClockOwner(channel)
    if failure == "realm_drift":
        model.info = f"Pid:\t{os.getpid()}\nNSpid:\t1\t{os.getpid()}\n".encode()
    elif failure == "wrong_namespace_type":
        monkeypatch.setattr(clock, "_namespace_kind", lambda fd: 0x20000000)  # PID, not time
    else:
        model.bad_fs = model.entries[owner._fdinfo.fd]
    with pytest.raises(FrameError):
        owner.sample()
    assert owner._local_lost
    with pytest.raises(FrameError):
        owner.cleanup_sample()
    assert owner.close_local()

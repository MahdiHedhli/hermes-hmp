"""Kernel tests use only a private synthetic endpoint and exact own child."""

import dataclasses
import os
import socket
import struct
import subprocess
import sys

import pytest

from hmp_plugin import presentation_broker_peer as peer
from hmp_plugin.presentation_jobs import FrameError


@pytest.mark.parametrize("uid,pid", [(0, 1), (501, 123), ((1 << 32) - 2, (1 << 31) - 1)])
def test_fixed_linux_and_darwin_credential_decoders(uid, pid):
    linux = peer._linux(struct.pack("=iII", pid, uid, 0))
    darwin = peer._darwin(struct.pack("=IIh2x16I", 0, uid, 1, *([0] * 16)), struct.pack("=i", pid))
    assert linux == darwin == peer.PeerObservation(uid, pid)
    with pytest.raises(dataclasses.FrozenInstanceError):
        linux.pid = 456


@pytest.mark.parametrize(
    "data",
    [
        None,
        bytearray(12),
        b"",
        b"x" * 11,
        b"x" * 13,
        struct.pack("=iII", 0, 501, 0),
        struct.pack("=iII", -1, 501, 0),
        struct.pack("=iII", 1, (1 << 32) - 1, 0),
        struct.pack("=iII", 1, 501, (1 << 32) - 1),
    ],
)
def test_malformed_or_unknown_linux_credentials_refuse(data):
    with pytest.raises(FrameError):
        peer._linux(data)


@pytest.mark.parametrize(
    "version,groups,uid,pid",
    [
        (1, 1, 501, 123),
        (0, 0, 501, 123),
        (0, 17, 501, 123),
        (0, -1, 501, 123),
        (0, 1, (1 << 32) - 1, 123),
        (0, 1, 501, 0),
        (0, 1, 501, -1),
    ],
)
def test_darwin_version_range_and_pid_do_not_fallback(version, groups, uid, pid):
    with pytest.raises(FrameError):
        peer._darwin(
            struct.pack("=IIh2x16I", version, uid, groups, *([0] * 16)), struct.pack("=i", pid)
        )


@pytest.mark.parametrize(
    "credentials,process",
    [(b"x" * 75, b"x" * 4), (b"x" * 77, b"x" * 4), (b"x" * 76, b"x" * 3), (None, b"x" * 4)],
)
def test_darwin_shapes_are_exact(credentials, process):
    with pytest.raises(FrameError):
        peer._darwin(credentials, process)


@pytest.mark.parametrize(
    "uid,pid",
    [(True, None), (0, None), (-1, None), ("501", None), (501, True), (501, 0), (501, 1 << 31)],
)
def test_trusted_expectations_are_not_coerced(uid, pid):
    left, right = socket.socketpair()
    try:
        with pytest.raises(FrameError):
            peer.observe_peer(left, expected_uid=uid, expected_pid=pid)
    finally:
        left.close()
        right.close()


@pytest.mark.skipif(
    sys.platform not in ("darwin", "linux") or os.geteuid() == 0,
    reason="actual supported nonroot kernel connection fixture",
)
def test_actual_private_connection_matches_exact_retained_child_identity(tmp_path):
    root = tmp_path / "p"
    root.mkdir(mode=0o700)
    path = root / "s"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.settimeout(5)
    child = None
    try:
        listener.bind(str(path))
        listener.listen(1)
        program = (
            "import socket,sys;s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);"
            "s.settimeout(5);s.connect(sys.argv[1]);s.sendall(b'r');"
            "assert s.recv(1)==b'x';s.close()"
        )
        child = subprocess.Popen(
            [sys.executable, "-I", "-B", "-S", "-c", program, str(path)],
            env={"LANG": "C", "LC_ALL": "C"},
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(5)
            observed = peer.observe_peer(
                connection, expected_uid=os.geteuid(), expected_pid=child.pid
            )
            assert observed.uid == os.geteuid() and observed.pid == child.pid
            for uid, pid in ((os.geteuid() + 1, child.pid), (os.geteuid(), child.pid + 1)):
                with pytest.raises(FrameError):
                    peer.observe_peer(connection, expected_uid=uid, expected_pid=pid)
            assert connection.recv(1) == b"r"
            connection.sendall(b"x")
        out, err = child.communicate(timeout=5)
        assert child.returncode == 0 and out == b"" and err == b""
    finally:
        listener.close()
        if child is not None and child.poll() is None:
            # Only this fixture's retained exact child; never an arbitrary peer PID.
            child.kill()
            child.communicate(timeout=5)
        path.unlink(missing_ok=True)


def test_closed_unconnected_and_listener_sockets_are_not_peer_identity(tmp_path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        with pytest.raises(FrameError):
            peer.observe_peer(sock, expected_uid=501)
        sock.bind(str(tmp_path / "listener.sock"))
        sock.listen(1)
        with pytest.raises(FrameError):
            peer.observe_peer(sock, expected_uid=501)
    finally:
        sock.close()
    with pytest.raises(FrameError) as error:
        peer.observe_peer(sock, expected_uid=501)
    assert str(error.value) == "BI1_BROKER_PEER_UNAVAILABLE"


def test_foreign_socket_class_is_rejected_without_callbacks():
    class Foreign:
        def fileno(self):
            pytest.fail("foreign callback invoked")

    with pytest.raises(FrameError):
        peer.observe_peer(Foreign(), expected_uid=501)


@pytest.mark.skipif(
    sys.platform not in ("darwin", "linux") or os.geteuid() == 0,
    reason="actual supported nonroot kernel fixture",
)
def test_observed_descriptor_replacement_refuses_without_claiming_identity(monkeypatch):
    left, right = socket.socketpair()
    original = peer._descriptor
    calls = 0

    def replaced(sock):
        nonlocal calls
        calls += 1
        row = original(sock)
        return row if calls == 1 else (row[0], row[1], row[2] + 1, row[3])

    monkeypatch.setattr(peer, "_descriptor", replaced)
    try:
        with pytest.raises(FrameError):
            peer.observe_peer(left, expected_uid=os.geteuid())
        assert calls == 2
    finally:
        left.close()
        right.close()


@pytest.mark.parametrize(
    "name,value", [("SO_ACCEPTCONN", None), ("SO_TYPE", "wrong"), ("SOL_SOCKET", True)]
)
def test_missing_or_malformed_required_api_is_fixed_unavailable(monkeypatch, name, value):
    left, right = socket.socketpair()
    monkeypatch.setattr(peer.sys, "platform", "linux")
    monkeypatch.setattr(peer.socket, name, value)
    try:
        with pytest.raises(FrameError) as error:
            peer.observe_peer(left, expected_uid=501)
        assert str(error.value) == "BI1_BROKER_PEER_UNAVAILABLE"
    finally:
        left.close()
        right.close()


def test_unsupported_platform_refuses_before_any_descriptor_observation(monkeypatch):
    left, right = socket.socketpair()
    monkeypatch.setattr(peer.sys, "platform", "unsupported")
    monkeypatch.setattr(peer, "_descriptor", lambda _: pytest.fail("observed descriptor"))
    try:
        with pytest.raises(FrameError) as error:
            peer.observe_peer(left, expected_uid=501)
        assert str(error.value) == "BI1_BROKER_PEER_UNAVAILABLE"
    finally:
        left.close()
        right.close()


def test_missing_linux_peercred_constant_is_not_guessed(monkeypatch):
    monkeypatch.delattr(peer.socket, "SO_PEERCRED", raising=False)
    with pytest.raises(FrameError) as error:
        peer._api("SO_PEERCRED")
    assert str(error.value) == "BI1_BROKER_PEER_UNAVAILABLE"

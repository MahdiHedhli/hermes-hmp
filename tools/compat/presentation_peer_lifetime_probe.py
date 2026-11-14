"""Owned-child Darwin lifetime/possession experiment, never runtime admission.

Only new fixed no-content children and a disposable local endpoint are used.
The controller is the sole reaper and retains its child unreaped through the
exchange. This proves that fixture's custody, not ambient gateway FD custody,
code origin, production qualification or authority to execute a tool.
"""
from __future__ import annotations

import array
import errno
import hashlib
import importlib.util
import os
import select
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path

from hmp_plugin.presentation_broker_peer import observe_peer
from hmp_plugin.presentation_jobs import FrameError

_SPEC = importlib.util.spec_from_file_location(
    "_hmp_lifetime_exit_observer", Path(__file__).with_name("darwin_process_exit_observer.py"))
observer = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = observer
_SPEC.loader.exec_module(observer)

_RANDOM = os.urandom
_POPEN = subprocess.Popen
_SEND, _RECV = socket.socket.send, socket.socket.recv
_RETAINED = []  # uncertainty keeps actual owners, never just a boolean receipt
_CHALLENGE = b"HMP-FIXTURE-LIFETIME/1:gateway:"
_RESPONSE = b"HMP-FIXTURE-LIFETIME/1:broker:"
_PAYLOAD = 64  # original scope bytes + independently fresh 256-bit challenge
_MODES = frozenset({"echo", "prequeued", "wrong_role", "wrong_scope", "old_nonce",
                    "partial", "silent", "exit_before_proof", "delegated"})
_CHILD = r'''
import array, os, socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(3)
s.connect(sys.argv[1])
mode = sys.argv[2]
request = b"HMP-FIXTURE-LIFETIME/1:gateway:"
reply = b"HMP-FIXTURE-LIFETIME/1:broker:"
if mode == "prequeued":
    s.sendall(reply + b"x" * 64)
if mode == "delegated":
    control = socket.socket(fileno=int(sys.argv[3]))
    control.settimeout(3)
    assert not os.get_inheritable(s.fileno())
    assert control.sendmsg([b"d"], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
        array.array("i", [s.fileno()]))]) == 1
sys.stdout.buffer.write(b"r")
sys.stdout.buffer.flush()
if mode == "exit_before_proof":
    s.close()
    raise SystemExit(0)
if mode == "delegated":
    assert control.recv(1) == b"x"
    control.close()
    s.close()
    raise SystemExit(0)
data = bytearray()
while len(data) < len(request) + 64:
    part = s.recv(len(request) + 64 - len(data))
    if not part:
        s.close()
        raise SystemExit(0)
    data.extend(part)
assert data[:len(request)] == request
body = bytes(data[len(request):])
answer = reply + body
if mode == "wrong_role":
    answer = request + body
elif mode == "wrong_scope":
    answer = reply + bytes([body[0] ^ 1]) + body[1:]
elif mode == "old_nonce":
    answer = reply + body[:32] + b"x" * 32
if mode != "silent":
    s.sendall(answer[:7] if mode == "partial" else answer)
if mode == "partial":
    s.close()
    raise SystemExit(0)
while s.recv(1):
    pass
s.close()
'''


class ProbeRefusedError(RuntimeError):
    def __init__(self):
        super().__init__("fixture_peer_lifetime_refused")


def _require(value):
    if value is not True:
        raise ProbeRefusedError


def _remaining(end):
    now = time.monotonic_ns()
    _require(type(end) is int and now < end)
    return (end - now) / 1_000_000_000


def _ready(fd, end, *, write=False):
    r, w, _ = select.select([] if write else [fd], [fd] if write else [], [], _remaining(end))
    _require(bool(w if write else r))
    _remaining(end)


def _empty(connection):
    try:
        _RECV(connection, 1, socket.MSG_PEEK)
    except BlockingIOError as error:
        _require(type(error) is BlockingIOError
                 and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK))
        return
    _require(False)  # both queued bytes and EOF refuse, never drain/reset


def _send_once(connection, raw, end, row):
    offset = 0
    while offset < len(raw):
        _ready(connection, end, write=True)
        count = _SEND(connection, raw[offset:])
        _require(type(count) is int and 0 < count <= len(raw) - offset)
        offset += count
        row["challenge_bytes_sent"] = offset
        _remaining(end)


def _receive_once(connection, count, end, row):
    data = bytearray()
    try:
        while len(data) < count:
            _ready(connection, end)
            part = _RECV(connection, count - len(data))
            _require(type(part) is bytes and 0 < len(part) <= count - len(data))
            data.extend(part)
            row["response_bytes_received"] = len(data)
            _remaining(end)
        return bytes(data)
    finally:
        data[:] = b"\0" * len(data)
        data.clear()


def run_owned_case(directory: Path, mode: str, *, admission_ns=2_000_000_000):
    """One attempt; returned observations are never a producer/receiver permit.

    The directory must be a newly created private fixture directory. This helper
    has no command-line entry, manager operation, host/native home or GO path.
    """
    _require(sys.platform == "darwin" and type(mode) is str and mode in _MODES
             and type(admission_ns) is int and 100_000_000 <= admission_ns <= 2_000_000_000)
    _require(type(directory) is type(Path()) and directory.is_absolute())
    info = directory.lstat()
    _require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
             and info.st_uid == os.geteuid())
    row = {"mode": mode, "attempts": 1, "exchange_observed": False,
           "challenge_bytes_sent": 0, "response_bytes_received": 0,
           "observer_registered": False, "observer_pending_after_response": False,
           "child_wait_known": False, "observer_close_known": False,
           "production_qualified": False, "stage": "initial"}
    child = connection = lifetime = listener = delegated = None
    controls = ()
    owners = {"listener": None, "accepted": None, "child": None, "observer": None,
              "controls": (), "delegated_fd": None, "delegated": None,
              "received_fds": [], "wrapper_started": False, "wrapper_completed": False,
              "bind_attempted": False}
    _RETAINED.append(owners)
    binding = object()
    path = directory / "s"
    owners["path"] = path
    path_identity = None
    scope = nonce = expected = received = None
    end = time.monotonic_ns() + admission_ns
    cleanup_end = end + 2_000_000_000
    try:
        _require(not path.exists() and not path.is_symlink())
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        owners["listener"] = listener
        owners["bind_attempted"] = True
        listener.bind(str(path))
        info = path.lstat()
        _require(stat.S_ISSOCK(info.st_mode))
        path_identity = (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))
        os.chmod(path, 0o600)
        listener.listen(1)
        listener.setblocking(False)
        if mode == "delegated":
            controls = socket.socketpair()
            owners["controls"] = controls
            for local in controls:
                local.setblocking(False)
        child = _POPEN.__new__(_POPEN)
        owners["child"] = child
        _POPEN.__init__(child, [sys.executable, "-I", "-B", "-S", "-c", _CHILD,
                               str(path), mode, str(controls[1].fileno()) if controls else "-1"],
                        env={"LANG": "C", "LC_ALL": "C"}, close_fds=True,
                        pass_fds=(controls[1].fileno(),) if controls else (),
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if controls:
            controls[1].close()
        # Never poll/wait/reap before registration and the possession proof.
        _ready(listener, end)
        accepted = listener.accept()
        owners["accepted"] = accepted  # actual accepted object before later native calls
        connection, _ = accepted
        connection.setblocking(False)
        _ready(child.stdout, end)
        _require(os.read(child.stdout.fileno(), 1) == b"r")
        row["stage"] = "initial_peer"
        initial = observe_peer(connection, expected_uid=os.geteuid(), expected_pid=child.pid)
        _require(not os.get_inheritable(connection.fileno()))
        row["stage"] = "register"
        lifetime = observer.ProcessExitObserver.__new__(observer.ProcessExitObserver)
        owners["observer"] = lifetime
        observer.ProcessExitObserver.__init__(lifetime, binding, child.pid,
            observe_end_ns=end, cleanup_end_ns=cleanup_end)
        row["observer_registered"] = True
        lifetime.ensure_pending(binding)
        row["stage"] = "predrain"
        _empty(connection)
        if mode == "delegated":
            # Deliberately violate the custody premise using only this own
            # fixture's socket. The original child remains unreaped throughout.
            _ready(controls[0], end)
            size = array.array("i").itemsize
            data, ancillary, flags, _ = controls[0].recvmsg(1, socket.CMSG_SPACE(size))
            # Retain every native-returned rights FD before validating the
            # expected singleton; padding can accommodate more than one int.
            for level, kind, raw in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    descriptors = array.array("i")
                    descriptors.frombytes(raw)
                    owners["received_fds"].extend(descriptors)
            _require(data == b"d" and flags == 0 and len(ancillary) == 1)
            level, kind, raw = ancillary[0]
            _require(level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS and len(raw) == size)
            _require(len(owners["received_fds"]) == 1)
            descriptor = owners["received_fds"][0]
            owners["delegated_fd"] = descriptor
            delegated = socket.socket.__new__(socket.socket)
            owners["delegated"] = delegated
            owners["wrapper_started"] = True
            socket.socket.__init__(delegated, fileno=descriptor)
            owners["wrapper_completed"] = True
            delegated.setblocking(False)
            _ready(controls[0], end, write=True)
            _require(_SEND(controls[0], b"x") == 1)
            while lifetime.poll(binding) is None:
                _remaining(end)
                time.sleep(0.001)
            row["original_peer_exit_observed"] = True
        row["stage"] = "fresh_challenge"
        scope, nonce = _RANDOM(32), _RANDOM(32)
        _require(type(scope) is bytes and len(scope) == 32
                 and type(nonce) is bytes and len(nonce) == 32)
        expected = _RESPONSE + scope + nonce
        _send_once(connection, _CHALLENGE + scope + nonce, end, row)
        if delegated is not None:
            # A different holder can answer even though the original peer is
            # already kernel-observed exited. Nonce possession alone is not PID proof.
            scratch = {}
            reflected = _receive_once(delegated, len(_CHALLENGE) + _PAYLOAD, end, scratch)
            _require(reflected == _CHALLENGE + scope + nonce)
            _send_once(delegated, expected, end, scratch)
            reflected = None
        row["stage"] = "response"
        received = _receive_once(connection, len(expected), end, row)
        _require(received == expected)
        if delegated is not None:
            row["bare_echo_after_original_exit"] = True
            lifetime.ensure_pending(binding)  # must refuse despite correct fresh response
            _require(False)
        row["stage"] = "final_fences"
        _empty(connection)
        _require(observe_peer(connection, expected_uid=initial.uid,
                              expected_pid=initial.pid) == initial)
        lifetime.ensure_pending(binding)
        _remaining(end)
        row["observer_pending_after_response"] = True
        row["exchange_sha256"] = hashlib.sha256(expected).hexdigest()
        row["exchange_observed"] = True
        row["stage"] = "observed"
    except observer.ObserverAcquisitionError as error:
        lifetime = error.failed_owner
        row["refused"] = True
    except (OSError, ValueError, FrameError, ProbeRefusedError,
            observer.ObserverRefusedError, subprocess.SubprocessError):
        row["refused"] = True  # never retain native exception text or private bytes
    finally:
        scope = nonce = expected = received = None
        row["local_sockets_closed"] = True
        for local in (delegated, connection, listener, *controls):
            if local is not None:
                try:
                    local.close()
                    _require(local.fileno() == -1)
                except (OSError, ProbeRefusedError):
                    row["local_sockets_closed"] = False
        for fd in owners["received_fds"]:
            if fd == owners["delegated_fd"] and owners["wrapper_started"]:
                if not owners["wrapper_completed"]:
                    row["local_sockets_closed"] = False  # partial wrapper is retained debt
                continue
            try:
                os.close(fd)  # unwrapped exact native-returned own descriptor only
            except OSError:
                row["local_sockets_closed"] = False
        if child is not None:
            try:
                _require(getattr(child, "_child_created", False) is True)
                try:
                    out, err = child.communicate(timeout=min(1, _remaining(cleanup_end)))
                except subprocess.TimeoutExpired:
                    _remaining(cleanup_end)
                    child.terminate()  # exact owned Popen, never a peer/PID lookup
                    out, err = child.communicate(timeout=_remaining(cleanup_end))
                row["child_wait_known"] = type(child.returncode) is int
                row["child_exit_code"] = child.returncode
                row["child_output_empty"] = out == b"" and err == b""
            except (OSError, ValueError, AttributeError, ProbeRefusedError,
                    subprocess.SubprocessError):
                row["child_cleanup_unknown"] = True
        if lifetime is not None:
            try:
                row["observer_close_known"] = lifetime.close(binding)
            except (OSError, observer.ObserverRefusedError):
                row["observer_close_known"] = False
        clean = (row["local_sockets_closed"] and (child is None or row["child_wait_known"])
                 and (lifetime is None or row["observer_close_known"]))
        if owners["bind_attempted"] and path_identity is None:
            clean = False
        if clean and path_identity is not None:
            try:
                info = path.lstat()
                _require((info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)) == path_identity)
                path.unlink()
            except (OSError, ProbeRefusedError):
                clean = False  # never unlink a preexisting or replaced path
        if clean:
            for index, retained in enumerate(_RETAINED):
                if retained is owners:
                    del _RETAINED[index]
                    break
        row["cleanup_known"] = clean
    return row

"""Fixture-only externally supervised no-GO service oracle.

Never installed or registered as a host control API. Trusted fixture startup pins
its source, installation, boot and peer; a private enrollment file is consumed
once before application frames. All retained debt awaits exact-label supervision.
"""
from __future__ import annotations

import asyncio
import errno
import hashlib
import importlib.util
import json
import os
import socket
import stat
import sys
import time
from pathlib import Path

_RETAINED: list[object] = []
_MAX_RECORD = 2048
_CHILD_OWNER_TYPE = None
_SOCKET_TYPE = socket.socket
_SOCKET_CLOSE, _SOCKET_FILENO = socket.socket.close, socket.socket.fileno


def require(value: bool) -> None:
    if value is not True:
        raise RuntimeError("service_fixture_refused")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def pairs(rows):
    result = {}
    for key, value in rows:
        require(key not in result)
        result[key] = value
    return result


def remaining(end_ns: int) -> float:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None  # bounded synchronous startup before its event loop exists
    if task is not None:
        pending = task.cancelling()
        require(type(pending) is int and pending >= 0)
        if pending:
            raise asyncio.CancelledError
    now = time.monotonic_ns()
    require(type(end_ns) is int and now < end_ns)
    return (end_ns - now) / 1_000_000_000


async def receive_control(sock: socket.socket, end_ns: int) -> dict:
    data = bytearray()
    loop = asyncio.get_running_loop()
    while not data.endswith(b"\n"):
        timeout = remaining(end_ns)
        part = await asyncio.wait_for(loop.sock_recv(sock, 1), timeout)
        remaining(end_ns)
        require(bool(part) and len(data) < 512)
        data.extend(part)
    raw = bytes(data[:-1])
    value = json.loads(raw, object_pairs_hook=pairs)
    require(type(value) is dict and raw == canonical(value))
    return value


async def send_control(sock: socket.socket, value: dict, end_ns: int) -> None:
    raw = canonical(value) + b"\n"
    require(len(raw) <= 2048)
    timeout = remaining(end_ns)
    await asyncio.wait_for(asyncio.get_running_loop().sock_sendall(sock, raw), timeout)
    remaining(end_ns)


def enrollment_file(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                and stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
                and 0 < before.st_size <= _MAX_RECORD)
        data = bytearray()
        while len(data) < before.st_size:
            part = os.read(fd, before.st_size - len(data))
            require(bool(part))
            data.extend(part)
        require(os.read(fd, 1) == b"")
        after = os.fstat(fd)
        def identity(row):
            return (row.st_dev, row.st_ino, row.st_mode, row.st_uid, row.st_gid,
                    row.st_nlink, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        require(identity(before) == identity(after))
    finally:
        os.close(fd)
    raw = bytes(data)
    value = json.loads(raw, object_pairs_hook=pairs)
    require(type(value) is dict and raw == canonical(value))
    return value


def own_socket() -> socket.socket:
    # Retain native allocation before initializer effects, including partial FD
    # acquisition. No replacement close or successful closure is invented here.
    sock = socket.socket.__new__(socket.socket)
    _RETAINED.append(sock)
    socket.socket.__init__(sock, socket.AF_UNIX, socket.SOCK_STREAM)
    return sock


def close_socket(sock) -> bool:
    """One known fixture-owned native socket close, not remote custody."""
    try:
        require(type(sock) is _SOCKET_TYPE)
        fd = _SOCKET_FILENO(sock)
        require(type(fd) is int and fd >= 0 and stat.S_ISSOCK(os.fstat(fd).st_mode))
        _SOCKET_CLOSE(sock)
        require(_SOCKET_FILENO(sock) == -1)
        try:
            os.fstat(fd)
        except OSError as error:
            require(error.errno == errno.EBADF)
        else:
            return False
        return True
    except BaseException:
        return False


def reader_identity(owner, operation) -> tuple[int | None, bool | None]:
    # Never consult attributes of partial/foreign native allocations. The
    # actual owner validates constructor, recipe, context and opaque binding
    # first; uncertainty/ECHILD remains unknown even when returncode is None.
    if _CHILD_OWNER_TYPE is None or type(owner) is not _CHILD_OWNER_TYPE:
        return None, None
    try:
        require(_CHILD_OWNER_TYPE.owns(owner, operation) is True)
        require(owner._constructor_returned is True)
        if owner._wait is not None:
            return None, False  # owned terminal wait, not new PID authority
        require(owner._signals_retired is False)
        pid = owner._pid_snapshot
        require(type(pid) is int and pid > 1)
        require(_CHILD_OWNER_TYPE.owns(owner, operation) is True)
        return pid, True
    except BaseException:
        return None, None


def serve_deadline(deadline, end_ns: int) -> int:
    now = time.monotonic_ns()
    require(type(deadline) is int and type(end_ns) is int
            and now < deadline <= min(now + 2_000_000_000, end_ns))
    return deadline


def snapshot(spine, pending) -> dict:
    require(len(spine._registry._records) <= 1)
    operations = []
    for ticket, record in spine._registry._records.items():
        owner = record.owner
        local = False
        try:
            observation = spine._registry.resource_local_observation(ticket)
            local = record.resources.validates_local(record, observation) is True
        except BaseException:
            local = False  # diagnostic uncertainty never supplies closure
        pid, unreaped = reader_identity(owner, record)
        operations.append({"operation": record.binding.operation,
            "status": spine._registry.status(record.binding).value,
            "reader_pid": pid,
            "reader_unreaped": unreaped,
            "go_attempted": None if record.resources is None else record.resources._go_attempted,
            "local_drain_observed": local})
    if pending is None:
        task_state = "none"
    elif not pending.done():
        task_state = "running"
    elif pending.cancelled():
        task_state = "cancelled"
    else:
        error = pending.exception()
        task_state = "complete" if error is None else type(error).__name__
    counts = spine._registry.counts
    return {"task": task_state, "connections": len(spine._records),
            "counts": {"active": counts.active, "waiting": counts.waiting,
                       "terminal": counts.terminal, "unknown": counts.unknown},
            "operations": operations}


async def service_loop(control, end_ns, enrollment, endpoint, observation, listener,
                       module, parser):
    spine = module.BrokerServiceSpine.__new__(module.BrokerServiceSpine)
    _RETAINED.append(spine)
    spine.__init__(listener, enrollment, endpoint=endpoint, observation=observation,
                   parser_package=parser)
    pending = None
    await send_control(control, {"ready": True}, end_ns)
    for sequence in range(1, 33):
        command = await receive_control(control, end_ns)
        require(type(command.get("sequence")) is int and command["sequence"] == sequence)
        mode = command.get("mode")
        expected = {"mode", "sequence", "deadline_ns"} if mode == "serve" else {"mode", "sequence"}
        require(command.keys() == expected and mode in ("serve", "inspect", "shutdown"))
        if mode == "serve":
            require(pending is None or pending.done())
            if pending is not None and not pending.cancelled():
                pending.exception()  # consume fixed diagnostic; never raw traceback
            deadline = serve_deadline(command["deadline_ns"], end_ns)
            pending = asyncio.create_task(spine.serve_once(deadline))
            _RETAINED.append(pending)
            reply = {"scheduled": True}  # NOT application/worker admission
        elif mode == "inspect":
            await asyncio.sleep(0)
            reply = snapshot(spine, pending)
        else:
            closed = await spine.stop_local_sockets()
            reply = {"local_sockets_closed": closed, "retained": snapshot(spine, pending)}
        await send_control(control, {"sequence": sequence, "reply": reply}, end_ns)
        if mode == "shutdown":
            # No started ACK/release or normal exit. Retain PENDING registry debt
            # until the external fixture controller removes this exact owned job.
            await asyncio.Event().wait()
    raise RuntimeError("fixture_control_exhausted")


def run(arguments: list[str]) -> None:
    require(len(arguments) == 9 and arguments[0] == "--fixture-oracle")
    _, plugin, manifest, digest, bootstrap_digest, root, nonce, boot, controller = arguments
    require(len(nonce) == 32 and all(c in "0123456789abcdef" for c in nonce)
            and len(boot) == 64 and all(c in "0123456789abcdef" for c in boot)
            and controller.isascii() and controller.isdecimal() and int(controller) > 1)
    end_ns = time.monotonic_ns() + 25_000_000_000
    bootstrap = Path(plugin) / "presentation_broker_bootstrap.py"
    require(hashlib.sha256(bootstrap.read_bytes()).hexdigest() == bootstrap_digest)
    spec = importlib.util.spec_from_file_location("_service_fixture_bootstrap", bootstrap)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    installation = module.VerifiedInstall(Path(manifest).read_bytes(), digest)
    installation.current()
    require(installation._selection_snapshot[0] == plugin)
    module._namespace(plugin)
    from _hmp_presentation_broker.presentation_broker_peer import observe_peer

    control = own_socket()
    control.settimeout(remaining(end_ns))
    control.connect(str(Path(root) / "control.sock"))
    remaining(end_ns)
    observe_peer(control, expected_uid=os.geteuid(), expected_pid=int(controller))
    # Controller first verifies kernel/job identity, then writes+fsyncs this
    # one-shot file and signals completion. No file-poll/partial-write race.
    expected = b"ENROLL " + nonce.encode("ascii") + b"\n"
    received = bytearray()
    while len(received) < len(expected):
        control.settimeout(remaining(end_ns))
        part = control.recv(len(expected) - len(received))
        remaining(end_ns)
        require(bool(part))
        received.extend(part)
    require(bytes(received) == expected)
    value = enrollment_file(Path(root) / "enrollment.json")
    require(value.keys() == {"iid", "listener", "broker", "gateway_uid", "gateway_pid",
                              "service_uid", "service_pid", "installation_generation"})
    require(value["iid"] == "a" * 52 and value["listener"] == nonce and value["broker"] == boot
            and type(value["gateway_pid"]) is int and value["gateway_pid"] == int(controller)
            and type(value["service_pid"]) is int and value["service_pid"] == os.getpid()
            and type(value["gateway_uid"]) is int and value["gateway_uid"] == os.geteuid()
            and type(value["service_uid"]) is int and value["service_uid"] == os.geteuid()
            and value["installation_generation"] == installation._selection_snapshot[2])
    from _hmp_presentation_broker import presentation_broker_service as service
    from _hmp_presentation_broker.presentation_broker_child import BrokerChildOwner
    global _CHILD_OWNER_TYPE
    _CHILD_OWNER_TYPE = BrokerChildOwner
    from _hmp_presentation_broker.presentation_broker_codec import BrokerBinding
    from _hmp_presentation_broker.presentation_broker_endpoint import BrokerEndpointOwner
    from _hmp_presentation_broker.presentation_broker_lifecycle import operation_id

    binding = BrokerBinding(value["iid"], nonce, boot, "d" * 64, operation_id(1))
    enrollment = service.StartupEnrollment(binding, value["gateway_uid"], value["gateway_pid"],
        value["service_uid"], value["service_pid"], value["installation_generation"])
    enrollment.validate()
    listener = own_socket()
    listener.bind(str(Path(root) / "ipc/presentation.sock"))  # no stale unlink/repair
    os.chmod(Path(root) / "ipc/presentation.sock", 0o600)
    listener.listen(8)
    endpoint = BrokerEndpointOwner.__new__(BrokerEndpointOwner)
    _RETAINED.append(endpoint)
    endpoint.__init__(str(Path(root) / "ipc"), expected_uid=os.geteuid())
    observation = endpoint.observe()
    installation.current()
    control.setblocking(False)
    asyncio.run(service_loop(control, end_ns, enrollment, endpoint, observation, listener,
                             service, installation._selection_snapshot[1]))


def main() -> int:
    try:
        run(sys.argv[1:])
    except BaseException:
        try:
            sys.stderr.write("SERVICE_FIXTURE_ORACLE_REFUSED\n")
            sys.stderr.flush()
        except BaseException:
            if not _RETAINED:
                return 1
        if not _RETAINED:
            return 1
    while True:
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())

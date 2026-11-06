"""One explicit owned launchd label: real enrolled no-GO socket service.

Never touches an existing host/service, real profile, grant or provider. Unknown
acquisition/cleanup preserves the lock and prohibits automatic rerun.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import plistlib
import secrets
import stat
import subprocess
import sys
import tempfile
import time
import types
from dataclasses import replace
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_service_fixture_base", Path(__file__).with_name("presentation_broker_crash_fixture.py")
)
base = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = base
_SPEC.loader.exec_module(base)
protocol = base._load("_service_fixture_control", "presentation_service_oracle.py")
probe, observer = base.probe, base.observer
_LOCK = Path("/private/tmp/hermes-character-service-fixture.lock")
_POINTER = Path("/private/tmp/hermes-character-service-fixture-current.json")
_RETAINED: list[object] = []
_HELPER = """import socket,sys
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
code=1
try:
    s.settimeout(1.3)
    s.connect(sys.argv[1])
    code=0 if s.recv(1)==b"" else 1
except BaseException:
    code=1
finally:
    s.close()
print("REFUSED" if code==0 else "UNKNOWN")
raise SystemExit(code)
"""


def _prepare(root: Path):
    original = base._prepare(root)
    (root / "ipc").mkdir(mode=0o700)
    oracle = root / "oracle.py"
    probe._private_write(
        oracle, Path(__file__).with_name("presentation_service_oracle.py").read_bytes()
    )
    helper = root / "helper.py"
    probe._private_write(helper, _HELPER.encode(), exclusive=True)
    manifest = root / "manifest.json"
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    bootstrap = root / "plugin/presentation_broker_bootstrap.py"
    boot = secrets.token_hex(32)
    argv = (
        "/usr/bin/env",
        "-i",
        "LANG=C",
        "LC_ALL=C",
        str(Path(sys.executable).resolve()),
        "-I",
        "-B",
        "-S",
        str(oracle),
        "--fixture-oracle",
        str(root / "plugin"),
        str(manifest),
        digest,
        hashlib.sha256(bootstrap.read_bytes()).hexdigest(),
        str(root),
        original.nonce,
        boot,
        str(os.getpid()),
    )
    value = plistlib.loads(original.plist.read_bytes())
    value["ProgramArguments"] = list(argv)
    probe._private_write(original.plist, plistlib.dumps(value))
    hashes = tuple(
        (str(p), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in (oracle, helper, manifest, original.plist)
    )
    return replace(original, argv=argv, mode="service", hashes=hashes), boot


def _client_modules(plugin: Path):
    base._require(sys.dont_write_bytecode is True, "controller_bytecode_disabled_required")
    # Trusted controller source assumption, not installed-listener admission.
    # Import only copied modules; never execute plugin __init__/Hermes startup.
    name = "_service_fixture_client"
    base._require(name not in sys.modules, "fixture_namespace_reuse")
    package = types.ModuleType(name)
    package.__package__, package.__path__ = name, [str(plugin)]
    package.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    package.__spec__.submodule_search_locations = [str(plugin)]
    sys.modules[name] = package
    return {
        suffix: importlib.import_module(name + "." + suffix)
        for suffix in (
            "presentation_broker_service",
            "presentation_broker_codec",
            "presentation_broker_lifecycle",
            "presentation_broker_endpoint",
            "presentation_parent_policy",
            "presentation_posix",
            "presentation_budget",
            "presentation_input_v3",
        )
    }


class Control:
    def __init__(self, sock, end_ns, progress=None):
        self.sock, self.end_ns, self.sequence = sock, end_ns, 0
        self.progress = {} if progress is None else progress

    async def command(self, mode, **values):
        base._require(self.sequence < protocol.MAX_CONTROL_COMMANDS, "control_count_exhausted")
        self.sequence += 1  # record intent before potentially partial send; never retry
        self.progress.update(control_sequence=self.sequence, control_mode=mode)
        command = {"mode": mode, "sequence": self.sequence, **values}
        await protocol.send_control(self.sock, command, self.end_ns)
        result = await protocol.receive_control(self.sock, self.end_ns)
        base._require(
            result.keys() == {"sequence", "reply"}
            and type(result["sequence"]) is int
            and result["sequence"] == self.sequence,
            "fixture_control_reply",
        )
        self.progress["control_reply_sequence"] = self.sequence
        return result["reply"]

    async def settled(self):
        for _ in range(64):
            result = await self.command("inspect")
            if result["task"] != "running":
                return result
            await asyncio.sleep(0.025)
        raise probe.ProbeRefusedError("control_settle_samples_exhausted")


def _packet(modules, home: Path, binding, end_ns: int, digest: str) -> bytes:
    ledger = modules["presentation_budget"].PresentationWorkLedger(
        clock=time.monotonic, deadline=end_ns / 1e9
    )
    owner = modules["presentation_parent_policy"].ParentPolicyReadOwner(
        root=str(home),
        home=str(home),
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=ledger,
        fs=modules["presentation_posix"].PosixFileOps(),
        current=lambda: True,
    )
    snapshot = owner.run()
    base._require(owner.descriptors_closed is True, "fixture_policy_fd_unknown")
    return modules["presentation_input_v3"].encode_input_v3(
        {
            "schema": 3,
            "challenge": "f" * 64,
            "epoch": 1,
            "profile": "default",
            "root": str(home),
            "home": str(home),
            "operation": "METADATA",
            "expected_avatar_sha": None,
            "uid": os.geteuid(),
            "gid": os.getegid(),
            "dir_modes": [0o700, 0o750, 0o755],
            "leaf_modes": [0o600, 0o640, 0o644],
            "source_manifest_sha": digest,
            "deadline_ns": end_ns,
            "directory_policy": [[r.uid, r.gid, r.modes[0]] for r in snapshot.rules],
            "iid": binding.iid,
            "canonical_fallback": "Synthetic",
            "observed_at": 0,
            "parent_work_counts": dict(snapshot.counts),
        }
    )


async def _run(case, boot, home, record, receipt, state):
    control_socket = None
    listener = protocol.own_socket()
    _RETAINED.append(listener)
    channels, raw_sockets, monitors = [], [], {}
    endpoint = None
    binding_token = object()
    try:
        probe._verify_case(case)
        query = probe._query_result(case, probe._command(case, "print"))
        base._require(query["absent"], "service_label_absence_unknown")
        address = str(case.root / "control.sock")
        base._require(len(address.encode()) < 104, "control_path_too_long")
        listener.bind(address)
        os.chmod(address, 0o600)
        listener.listen(1)
        startup_end = time.monotonic_ns() + 8_000_000_000
        record["submission_attempted"] = True
        probe._save(receipt, state)
        result = probe._command(case, "bootstrap")
        record["bootstrap_returncode"] = result.returncode
        base._require(result.returncode == 0, "service_bootstrap_ambiguous")
        control_holder = [None]
        _RETAINED.append(control_holder)  # holder precedes native accept effect
        listener.settimeout(protocol.remaining(startup_end))
        control_holder[0], _ = listener.accept()
        control_socket = control_holder[0]
        protocol.remaining(startup_end)
        peer = probe._kernel_peer(control_socket)
        query = probe._query_result(case, probe._command(case, "print"))
        record["verified_job"] = query
        base._require(query["owned"] and query["pid"] == peer.pid, "service_job_peer_mismatch")
        probe._verify_case(case)
        now = time.monotonic_ns()
        record["observe_end_ns"], record["cleanup_end_ns"] = (
            now + 12_000_000_000,
            now + 18_000_000_000,
        )
        try:
            monitors["broker"] = observer.ProcessExitObserver(
                binding_token,
                peer.pid,
                observe_end_ns=record["observe_end_ns"],
                cleanup_end_ns=record["cleanup_end_ns"],
            )
        except observer.ObserverAcquisitionError as error:
            monitors["broker"] = error.failed_owner
            raise
        modules = _client_modules(case.root / "plugin")
        service = modules["presentation_broker_service"]
        codec = modules["presentation_broker_codec"]
        scope = codec.BrokerBinding(
            "a" * 52,
            case.nonce,
            boot,
            "d" * 64,
            modules["presentation_broker_lifecycle"].operation_id(1),
        )
        enrollment = service.StartupEnrollment(
            scope, os.geteuid(), os.getpid(), os.geteuid(), peer.pid, "d" * 64
        )
        value = dict(
            zip(
                (
                    "iid",
                    "listener",
                    "broker",
                    "gateway_uid",
                    "gateway_pid",
                    "service_uid",
                    "service_pid",
                    "installation_generation",
                ),
                enrollment.values(),
                strict=True,
            )
        )
        probe._private_write(
            case.root / "enrollment.json", protocol.canonical(value), exclusive=True
        )
        base._send(
            control_socket, b"ENROLL " + case.nonce.encode() + b"\n", record["observe_end_ns"]
        )
        control_socket.setblocking(False)
        base._require(
            await protocol.receive_control(control_socket, record["observe_end_ns"])
            == {"ready": True},
            "service_not_ready",
        )
        control = Control(control_socket, record["observe_end_ns"], record)
        endpoint_type = modules["presentation_broker_endpoint"].BrokerEndpointOwner
        endpoint = endpoint_type.__new__(endpoint_type)
        _RETAINED.append(endpoint)
        endpoint.__init__(str(case.root / "ipc"), expected_uid=os.geteuid())
        observation = endpoint.observe()

        async def connect():
            endpoint.validates(observation)
            sock = protocol.own_socket()
            raw_sockets.append(sock)
            sock.setblocking(False)
            timeout = protocol.remaining(record["observe_end_ns"])
            await asyncio.wait_for(
                asyncio.get_running_loop().sock_connect(
                    sock, str(case.root / "ipc/presentation.sock")
                ),
                timeout,
            )
            endpoint.validates(observation)
            try:
                channel = service.SocketChannel(
                    sock, enrollment, role="gateway", endpoint=endpoint, observation=observation
                )
            except service.ChannelAcquisitionError as error:
                channels.append(error.failed_owner)
                raise
            channels.append(channel)
            return channel

        # Wrong process, same UID; helper sends no application bytes at all.
        end = time.monotonic_ns() + 1_700_000_000
        await control.command("serve", deadline_ns=end)
        helper = subprocess.Popen.__new__(subprocess.Popen)
        _RETAINED.append(helper)
        record["helper_launch_attempted"] = True
        subprocess.Popen.__init__(
            helper,
            [
                case.argv[4],
                "-I",
                "-B",
                "-S",
                str(case.root / "helper.py"),
                str(case.root / "ipc/presentation.sock"),
            ],
            env={"LANG": "C", "LC_ALL": "C"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        out, err = helper.communicate(timeout=2)
        record["helper_cleanup_known"] = (
            helper.returncode == 0 and out == b"REFUSED\n" and err == b""
        )
        base._require(record["helper_cleanup_known"], "wrong_peer_helper_unknown")
        wrong_peer = await control.settled()
        record["wrong_peer"] = wrong_peer
        base._require(
            wrong_peer["task"] == "ChannelAcquisitionError"
            and wrong_peer["counts"]["active"] == 0
            and not wrong_peer["operations"],
            "wrong_peer_not_refused_before_work",
        )
        # Legitimate process deliberately bypasses its outbound scope guard to
        # test the server's independent header gate, using only bodyless STATUS.
        await control.command("serve", deadline_ns=time.monotonic_ns() + 1_700_000_000)
        bad = await connect()
        wrong = replace(scope, broker="f" * 64 if boot != "f" * 64 else "e" * 64)
        await asyncio.wait_for(
            asyncio.get_running_loop().sock_sendall(
                bad._socket, codec.encode_frame(wrong, "STATUS", 0)
            ),
            protocol.remaining(record["observe_end_ns"]),
        )
        base._require(
            await asyncio.wait_for(
                asyncio.get_running_loop().sock_recv(bad._socket, 1),
                protocol.remaining(record["observe_end_ns"]),
            )
            == b"",
            "wrong_boot_not_eof",
        )
        base._require(bad.close(), "wrong_boot_local_close_unknown")
        wrong_boot = await control.settled()
        record["wrong_boot"] = wrong_boot
        base._require(
            wrong_boot["task"] == "FrameError" and not wrong_boot["operations"],
            "wrong_boot_created_work",
        )
        # Only new synthetic directory metadata enters input3, never a native
        # profile/credential/message. There is no GO and no profile-file read.
        end = time.monotonic_ns() + 1_700_000_000
        body = _packet(
            modules,
            home,
            scope,
            end,
            hashlib.sha256((case.root / "manifest.json").read_bytes()).hexdigest(),
        )
        await control.command("serve", deadline_ns=end)
        channel = await connect()
        grammar = modules["presentation_broker_lifecycle"].OperationGrammar(scope, role="gateway")
        first = codec.BrokerFrame(codec.BrokerHeader(scope, "BEGIN", 0, len(body)), body)
        grammar.observe(first, sender="client")
        record["begin_write_attempted"] = True
        probe._save(receipt, state)
        await channel.send(first, end)
        ready = await channel.receive(end, expected=scope)
        grammar.observe(ready, sender="broker")
        base._require(ready.header.kind == "READY", "actual_service_no_ready")
        before = await control.command("inspect")
        record["before_cancel"] = before
        base._require(len(before["operations"]) == 1, "reader_not_retained")
        row = before["operations"][0]
        base._require(
            type(row["reader_pid"]) is int
            and row["reader_unreaped"] is True
            and row["go_attempted"] is False
            and row["status"] == "pending",
            "reader_identity_or_no_go_unknown",
        )
        try:
            monitors["reader"] = observer.ProcessExitObserver(
                binding_token,
                row["reader_pid"],
                observe_end_ns=record["observe_end_ns"],
                cleanup_end_ns=record["cleanup_end_ns"],
            )
        except observer.ObserverAcquisitionError as error:
            monitors["reader"] = error.failed_owner
            raise
        monitors["reader"].ensure_pending(binding_token)
        cancel = codec.BrokerFrame(codec.BrokerHeader(scope, "CANCEL", 1, 0), b"")
        grammar.observe(cancel, sender="client")
        record["cancel_write_attempted"] = True
        await channel.send(cancel, end)
        # Communication EOF is recorded separately, never closure authority.
        value = await asyncio.wait_for(
            asyncio.get_running_loop().sock_recv(channel._socket, 1),
            protocol.remaining(record["observe_end_ns"]),
        )
        base._require(value == b"", "cancel_returned_unexpected_frame")
        record["cancel_connection_eof"] = True
        base._require(channel.close(), "application_local_close_unknown")
        after = await control.settled()
        record["after_cancel"] = after
        row = after["operations"][0]
        base._require(
            after["task"] == "complete"
            and after["connections"] == 0
            and row["go_attempted"] is False
            and row["local_drain_observed"] is True
            and row["status"] == "pending",
            "local_drain_or_pending_unknown",
        )
        fact = None
        while fact is None and time.monotonic_ns() < record["observe_end_ns"]:
            fact = monitors["reader"].poll(binding_token)
            if fact is None:
                await asyncio.sleep(0.001)
        base._require(fact is not None, "reader_kernel_exit_not_observed")
        record["reader_kernel_exit_observed_ns"] = fact.observed_at_ns
        record["phase"] = "status_serve"
        status = replace(scope, channel=secrets.token_hex(32))
        status_end = time.monotonic_ns() + 1_000_000_000
        await control.command("serve", deadline_ns=status_end)
        record["phase"] = "status_connect"
        status_channel = await connect()
        terminal = service.TerminalStatusExchange.__new__(service.TerminalStatusExchange)
        _RETAINED.append(terminal)
        terminal.__init__(status_channel, status, status_end)
        record["phase"] = "status_write"
        await terminal.request()
        record["phase"] = "status_receive"
        pending = await terminal.receive_reply()
        record["status_transport_completion"] = terminal._completion
        base._require(
            pending.header.kind == "PENDING" and pending.body == b"", "status_replayed_body"
        )
        base._require(status_channel.close(), "status_socket_close_unknown")
        record["phase"] = "status_settle"
        record["status"] = await control.settled()
        record["phase"] = "shutdown"
        record["shutdown"] = await control.command("shutdown")
        base._require(
            record["shutdown"]["local_sockets_closed"] is True
            and record["shutdown"]["retained"]["operations"][0]["status"] == "pending",
            "shutdown_claimed_started_release",
        )
        record["phase"] = "observations_complete"
        record["expected_observations"] = True
    finally:
        errors = []
        for channel in channels:
            try:
                if channel.close() is not True:
                    errors.append("client_channel_close_unknown")
            except BaseException:
                errors.append("client_channel_close_unknown")
        # Raw sockets retained before channel acquisition remain reachable. Only
        # successful channel-owned closes count; no fallback close invents proof.
        for sock in raw_sockets:
            try:
                if sock.fileno() != -1:
                    errors.append("unadopted_client_socket_unknown")
            except BaseException:
                errors.append("unadopted_client_socket_unknown")
        for sock in (control_socket, listener):
            if sock is not None:
                try:
                    if protocol.close_socket(sock) is not True:
                        errors.append("control_socket_close_unknown")
                except BaseException:
                    errors.append("control_socket_close_unknown")
        if record.get("submission_attempted"):
            try:
                probe._cleanup(case, record, receipt, state)
            except BaseException:
                record["cleanup"] = "unknown"
                errors.append("manager_cleanup_unknown")
            for kind, owner in monitors.items():
                key = kind + "_kernel_exit_observed_ns"
                while record.get(key) is None and time.monotonic_ns() < record.get(
                    "cleanup_end_ns", 0
                ):
                    try:
                        fact = owner.poll(binding_token, cleanup=True)
                    except BaseException:
                        break
                    if fact is not None:
                        record[key] = fact.observed_at_ns
                    else:
                        await asyncio.sleep(0.001)
        closes = []
        for owner in monitors.values():
            try:
                closes.append(owner.close(binding_token) is True)
            except BaseException:
                closes.append(False)
                errors.append("kernel_monitor_close_unknown")
        if endpoint is not None:
            try:
                if endpoint.close() is not True:
                    errors.append("client_endpoint_close_unknown")
            except BaseException:
                errors.append("client_endpoint_close_unknown")
        record["cleanup_errors"] = errors
        record["cleanup_known"] = (
            record.get("cleanup") == "known_absent"
            and record.get("broker_kernel_exit_observed_ns") is not None
            and (
                not record.get("begin_write_attempted")
                or record.get("reader_kernel_exit_observed_ns") is not None
            )
            and (
                not record.get("helper_launch_attempted")
                or record.get("helper_cleanup_known") is True
            )
            and all(closes)
            and not errors
        )
        probe._save(receipt, state)


def main() -> int:
    base._require(
        sys.argv[1:] == ["--run-local-fixture"] and sys.platform == "darwin" and os.geteuid() > 0,
        "explicit_nonroot_darwin_fixture_required",
    )
    base._require(sys.dont_write_bytecode is True, "controller_bytecode_disabled_required")
    try:
        importlib.import_module("yaml")
    except ModuleNotFoundError as error:
        raise probe.ProbeRefusedError("controller_pyyaml_dependency_missing") from error
    fd = os.open(_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    root = Path(tempfile.mkdtemp(prefix="hbr-service-", dir="/private/tmp"))
    home = Path(
        tempfile.mkdtemp(prefix="hmp-service-integration-", dir=Path(__file__).resolve().parents[2])
    ).resolve()
    (home / "profile.yaml").write_text("display_name: SYNTHETIC_SERVICE_FIXTURE_ONLY\n")
    (home / "profile.yaml").chmod(0o600)
    receipt = root / "receipt.json"
    record = {"submission_attempted": False, "cleanup_known": False}
    state = {
        "scope": "separateprocess synthetic no-GO enrolled service fixture",
        "production_qualified": False,
        "status": "preparing",
        "record": record,
        "controller_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    probe._save(_POINTER, {"root": str(root), "home": str(home), "receipt": str(receipt)})
    probe._save(receipt, state)
    try:
        for directory in (home, *home.parents):
            info = directory.stat()
            base._require(stat.S_IMODE(info.st_mode) in (0o700, 0o750, 0o755)
                          and info.st_uid in (0, os.geteuid()), "synthetic_home_policy_unavailable")
        case, boot = _prepare(root / "a")
        record.update(label=case.label, target=case.target, hashes=dict(case.hashes))
        asyncio.run(_run(case, boot, home, record, receipt, state))
        base._require(
            record.get("expected_observations") is True and record["cleanup_known"],
            "service_fixture_incomplete",
        )
        state["status"] = "terminal_observed"
    except BaseException as error:
        state["status"] = "terminal_refused"
        state["error"] = (
            str(error) if type(error) is probe.ProbeRefusedError else type(error).__name__
        )
    probe._save(receipt, state)
    if state["status"] == "terminal_observed":
        _LOCK.unlink()
    print(
        json.dumps(
            {
                "status": state["status"],
                "receipt": str(receipt),
                "cleanup_known": record["cleanup_known"],
                "production_qualified": False,
            }
        )
    )
    return 0 if state["status"] == "terminal_observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Synthetic native AT1 IPC/TLS integration fixture, never a live host.

Invoke through the reviewed controller with a new private fixture root, immutable
export sample (native/ and hmp/), one loopback TLS port, and literal `matrix`.
The sample must be independently content-bound before and after execution.
Synthetic owner/API-key data exist only under that new private home. No tool,
model, shell, ordinary message, real pairing or host setting is exercised.
This tests real native helpers, listener/Store/auth, CLI observation + same-UID
IPC, and authenticated HTTP card/control. It does not test shell parser/TTY,
physical phone UI, push delivery, Linux or release eligibility.
"""

import argparse
import asyncio
import errno
import fcntl
import hashlib
import hmac
import importlib
import json
import os
import pwd
import queue
import select
import socket
import ssl
import stat
import sys
import threading
import time
import traceback
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Admission is explicit, not assert-based: -O must never erase these guards.
if (
    len(sys.argv) != 5
    or not sys.flags.isolated
    or not sys.dont_write_bytecode
    or sys.flags.optimize
):
    raise SystemExit("refusing fixture flags or arguments")
root = Path(sys.argv[1])
sample = Path(sys.argv[2])
native = sample / "native"
hmp = sample / "hmp"
real_homes = {
    (Path.home() / ".hermes").resolve(),
    (Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".hermes").resolve(),
}
if (
    not root.is_absolute()
    or root.resolve() != root
    or stat.S_IMODE(root.stat().st_mode) != 0o700
    or root.stat().st_uid != os.geteuid()
    or any(
        root == home
        or home in root.parents
        or sample.resolve() == home
        or home in sample.resolve().parents
        for home in real_homes
    )
    or {p.name for p in root.iterdir()} != {"tmp", "fixture.py", "controller.json", "child.log"}
    or os.environ.get("HERMES_HOME") != str(root / "home")
    or Path.home() != root / "user-home"
):
    raise SystemExit("refusing nonprivate or nonfresh fixture root/source")
scenario = sys.argv[4]
assert scenario == "matrix"
port = int(sys.argv[3])
assert 1 <= port <= 65535
assert sys.flags.isolated and sys.dont_write_bytecode
assert root.is_absolute() and root.resolve() == root and stat.S_IMODE(root.stat().st_mode) == 0o700
assert Path(os.environ["HERMES_HOME"]) == root / "home" and Path.home() == root / "user-home"
for folder in [root / "home", root / "user-home", root / "runtime"]:
    folder.mkdir(mode=0o700)
os.umask(0o077)
(root / "home/config.yaml").write_text(
    f"""sessions:
  cjk_fts: false
gateway:
  multiplex_profiles: true
  profile_routes:
    - name: hmp-default
      platform: hmp
      profile: default
      guild_id: default
    - name: hmp-beta
      platform: hmp
      profile: beta
      guild_id: beta
platforms:
  hmp:
    enabled: true
    extra:
      bind: 127.0.0.1
      port: {port}
      local_media:
        enabled: true
      direct_send:
        enabled: true
      owner_device_ids: [aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]
  api_server:
    enabled: false
    extra:
      host: 127.0.0.1
      key: SYNTHETIC_AT1_NO_API_REQUEST_WILL_BE_SENT
"""
)
allowed = [root, native, hmp, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
absent_proc = [0]
os_metadata = [0]
absent_parent_manifest = [0]
root_directory_opens = [0]
owned_fd_chmods = [0]


def inside(p, base):
    return p == base or base in p.parents


registered_cli_mode = os.environ.get("HMP_AT1_FIXTURE_CLI_PTY") == "1"
cli_jobs = queue.Queue()
cli_stop = object()
cli_connects = [0]
cli_main_thread = threading.get_ident()
cli_resource_debt = []


def audit(event, args):
    if event.startswith("socket."):
        if event == "socket.__new__":
            _obj, family, kind, protocol = args
            if (
                family in (socket.AF_INET, socket.AF_UNIX)
                and (kind & 15) == socket.SOCK_STREAM
                and protocol in ((0, socket.IPPROTO_TCP) if family == socket.AF_INET else (0,))
            ):
                return
        if event in ("socket.bind", "socket.connect"):
            obj, address = args[:2]
            if (
                obj.family == socket.AF_INET
                and type(address) is tuple
                and address == ("127.0.0.1", port)
            ):
                return
            if (
                obj.family == socket.AF_UNIX
                and type(address) is str
                and Path(address).is_absolute()
                and inside(Path(address).resolve(), root)
            ):
                if event == "socket.connect" and threading.get_ident() == cli_main_thread:
                    cli_connects[0] += 1
                return
        if event == "socket.getaddrinfo" and args[0] == "127.0.0.1" and args[1] == port:
            return
        raise RuntimeError("tls_fixture_socket_refused:" + event)
    if event == "os.kill":
        if type(args[0]) is int and args[0] > 0 and args[1] == 0:
            return
        raise RuntimeError("native_fixture_process_signal_refused")
    if event in {"os.killpg", "signal.pthread_kill", "sqlite3.load_extension"}:
        raise RuntimeError("native_fixture_signal_or_sqlite_extension_refused")
    if event in {
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.posix_spawn",
        "os.fork",
        "os.forkpty",
    }:
        raise RuntimeError("smoke_external_effect_refused:" + event)
    if event == "sqlite3.connect":
        raw = os.fspath(args[0])
        assert type(raw) is str and "\x00" not in raw
        if raw != ":memory:":
            if raw.startswith("file:"):
                parts = urlsplit(raw)
                assert (
                    parts.scheme == "file"
                    and parts.netloc == ""
                    and parts.query == "mode=ro"
                    and parts.fragment == ""
                )
                path = Path(unquote(parts.path, encoding="utf-8", errors="strict")).resolve()
                assert path.as_uri() + "?mode=ro" == raw
            else:
                assert Path(raw).is_absolute()
                path = Path(raw).resolve()
            assert inside(path, root)
    if event == "open":
        path, mode, flags = args
        if isinstance(path, int):
            return
        p = Path(os.fsdecode(path)).resolve()
        write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if (
            not write
            and os.fsdecode(path) == "/"
            and flags & os.O_DIRECTORY
            and flags & os.O_NOFOLLOW
        ):
            root_directory_opens[0] += 1
            return
        if not write and os.fsdecode(path) == str(sample / "manifest.json"):
            try:
                Path(os.fsdecode(path)).lstat()
            except FileNotFoundError:
                absent_parent_manifest[0] += 1
                raise FileNotFoundError("verified_absent_owned_source_parent_manifest") from None
            raise RuntimeError("unexpected_source_parent_manifest_refused")
        if (
            not write
            and sys.platform == "darwin"
            and os.fsdecode(path)
            in ("/proc/1/cgroup", "/proc/self/mountinfo", f"/proc/{os.getpid()}/stat")
        ):
            absent_proc[0] += 1
            raise FileNotFoundError("smoke_synthetic_darwin_proc_absent")
        if (
            sys.platform == "darwin"
            and not write
            and os.fsdecode(path) == "/System/Library/CoreServices/SystemVersion.plist"
        ):
            info = p.lstat()
            assert (
                stat.S_ISREG(info.st_mode)
                and info.st_uid == 0
                and info.st_nlink == 1
                and not info.st_mode & 0o222
                and info.st_size <= 65536
                and p == Path(os.fsdecode(path))
            )
            os_metadata[0] += 1
            return
        if not write and p == Path(__file__).resolve():
            return
        if not any(inside(p, x) for x in ([root] if write else allowed)) and p != Path("/dev/null"):
            raise RuntimeError("smoke_file_refused")
    if event == "os.chmod" and type(args[0]) is int:
        fd, mode = args[:2]
        assert mode == 0o600
        before = os.fstat(fd)
        assert fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE in (os.O_WRONLY, os.O_RDWR)
        raw = fcntl.fcntl(fd, fcntl.F_GETPATH, b"\0" * 1024).split(b"\0", 1)[0]
        path = Path(os.fsdecode(raw))
        assert path.is_absolute() and path.resolve() == path and inside(path, root)
        named = path.lstat()
        after = os.fstat(fd)
        assert (
            stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid() and before.st_nlink == 1
        )
        assert (
            (before.st_dev, before.st_ino)
            == (named.st_dev, named.st_ino)
            == (after.st_dev, after.st_ino)
        )
        assert all(
            stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1
            for info in (named, after)
        )
        owned_fd_chmods[0] += 1
        return
    if event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.chmod"}:
        for raw in args[:2] if event == "os.rename" else args[:1]:
            if not inside(Path(os.fsdecode(raw)).resolve(), root):
                raise RuntimeError("smoke_write_refused")


sys.addaudithook(audit)
# Same built-in-only MIME seeding as the accepted native serving fixture.
import mimetypes  # noqa: E402 -- install the filesystem audit before MIME initialization.

mimetypes.inited = True
mimetypes._db = mimetypes.MimeTypes(filenames=())
mimetypes.init(files=[])
sys.path[:0] = [str(native), str(hmp / "server")]
report = {
    "schema": 1,
    "productionQualified": False,
    "liveHost": False,
    "physicalQualified": False,
    "networkScope": "single-loopback-port/private-unix-only",
    "builtinOnlyMimeTables": True,
    "privateUmask": True,
    "phase": "imports",
}
report["scenario"] = scenario
manager = None
context = None
loader_threads = None
loader_lock = None
identity_module = None
original_identity_load = None
try:
    from hermes_cli import plugins_loader

    loader_threads = plugins_loader._ABANDONED_LOADERS
    loader_lock = plugins_loader._ABANDONED_LOADERS_LOCK
    from gateway.config import PlatformConfig
    from gateway.platform_registry import platform_registry
    from hermes_cli.plugins import PluginManager
    from hermes_cli.plugins_manifest import parse_manifest_file

    plugin = hmp / "server/hmp_plugin"
    manifest = parse_manifest_file(plugin / "plugin.yaml", plugin, "user", "")
    assert manifest is not None and manifest.name == "hmp"
    manager = PluginManager(scope_key=str(root / "home"))
    report["phase"] = "load"
    manager._load_plugin(manifest)
    loaded = manager._plugins["hmp"]
    report.update(loaderEnabled=loaded.enabled, loaderError=loaded.error)
    assert loaded.enabled and not loaded.error
    entry = platform_registry.get("hmp")
    assert entry is not None
    assert manager._plugin_platform_names == {"hmp"} and set(manager._cli_commands) == {"hmp"}
    assert (
        not manager._plugin_tool_names and not manager._hooks and not manager._approval_transports
    )
    report.update(exactClosedSurface=True, passiveDependencies=bool(entry.check_fn()))
    assert entry.ensure_deps_fn is None
    report["phase"] = "factory"
    adapter = platform_registry.create_adapter(
        "hmp",
        PlatformConfig(
            enabled=True,
            extra={"bind": "127.0.0.1", "port": port, "local_media": {"enabled": True}},
        ),
    )
    assert adapter is not None
    report["adapterConstructed"] = True
    report["phase"] = "components"
    module = importlib.import_module(type(adapter).__module__)
    identity_module = importlib.import_module(module.__package__ + ".identity")
    original_identity_load = identity_module.load_or_create
    report["syntheticHostIdentityCalls"] = 0

    def scratch_identity_load(store):
        report["syntheticHostIdentityCalls"] += 1
        result = original_identity_load(
            store,
            host_id=lambda: identity_module.HostId(
                identity_module.HOST_SOURCE_DARWIN, "00000000-0000-4000-8000-000000000001"
            ),
        )
        report["originalIdentityLoadReturned"] = True
        return result

    identity_module.load_or_create = scratch_identity_load
    report["syntheticHostIdentity"] = True
    native_status = importlib.import_module("gateway.status")
    held_runtime_writer = [None]

    async def status_readback(expected):
        status = native_status
        writer = status._runtime_status_writer
        assert writer is not None
        if held_runtime_writer[0] is None:
            held_runtime_writer[0] = writer
        assert writer is held_runtime_writer[0]
        with writer._condition:
            generation = writer._submitted_generation
        assert generation > 0
        success = await asyncio.to_thread(writer.wait, generation, 2.0)
        with writer._condition:
            settled = writer.settled(generation)
        if not success and settled is None:
            try:
                fd = os.open(
                    root / ("waiting-status-" + expected + ".json"),
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                )
                with os.fdopen(fd, "w") as f:
                    json.dump(
                        {
                            "stage": "waiting-original-status-generation",
                            "generation": generation,
                            "retryAllowed": False,
                        },
                        f,
                    )
            except BaseException:  # noqa: S110 -- diagnostic failure cannot abandon owned wait.
                pass
            success = await asyncio.to_thread(writer.wait, generation, None)
        assert success is True
        with writer._condition:
            idle = (
                writer._writing_generation == 0
                and writer._pending is None
                and writer._successful_generation >= writer._submitted_generation
                and writer._last_error is None
            )
        assert idle
        payload = status.read_runtime_status()
        assert payload["platforms"]["hmp"]["state"] == expected
        path = status._get_runtime_status_path()
        info = path.lstat()
        assert (
            inside(path.resolve(), root)
            and stat.S_ISREG(info.st_mode)
            and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_uid == os.geteuid()
            and info.st_size <= 65536
        )
        return {
            "targetGeneration": generation,
            "persisted": True,
            "writerIdle": True,
            "state": expected,
            "privateMode": True,
            "bodySHA256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    async def settle_actual_status_writer():
        current = native_status._runtime_status_writer
        candidates = []
        for writer in (held_runtime_writer[0], current):
            if writer is not None and all(writer is not item for item in candidates):
                candidates.append(writer)
        errors = []
        observations = []
        if len(candidates) > 1:
            errors.append({"operation": "status-writer-identity", "type": "ChangedWriter"})
        for writer in candidates:
            while True:
                with writer._condition:
                    target = writer._submitted_generation
                success = await asyncio.to_thread(writer.wait, target, 2.0)
                with writer._condition:
                    settled = writer.settled(target)
                if not success and settled is None:
                    try:
                        fd = os.open(
                            root / "waiting-final-status.json",
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600,
                        )
                        with os.fdopen(fd, "w") as f:
                            json.dump(
                                {
                                    "stage": "waiting-original-final-status-generation",
                                    "target": target,
                                    "retryAllowed": False,
                                },
                                f,
                            )
                    except BaseException:  # noqa: S110 -- diagnostic failure cannot abandon owned wait.
                        pass
                    try:
                        success = await asyncio.to_thread(writer.wait, target, None)
                    except BaseException as exc:
                        errors.append(
                            {"operation": "status-generation", "type": type(exc).__name__}
                        )
                with writer._condition:
                    idle = writer._writing_generation == 0 and writer._pending is None
                    persisted = (
                        writer._successful_generation >= writer._submitted_generation
                        and writer._last_error is None
                    )
                    latest = writer._submitted_generation
                if idle:
                    observations.append(
                        {
                            "target": target,
                            "latest": latest,
                            "writerIdle": True,
                            "persisted": persisted,
                            "idleDaemonAlive": writer._thread is not None
                            and writer._thread.is_alive(),
                        }
                    )
                    if not persisted:
                        errors.append(
                            {"operation": "status-generation", "type": "PersistenceFailed"}
                        )
                    break
                # Observe the next actual submitted generation; never submit/replay a write.
        return observations, errors

    async def registered_cli(argv, *, terminal=True, agent=False):
        # The owning server loop retains this result until the real handler
        # returns on the main thread; observer cancellation cannot cancel it.
        loop = asyncio.get_running_loop()
        completed = loop.create_future()
        cli_jobs.put((loop, completed, argv, terminal, agent))
        return await asyncio.shield(completed)

    def run_registered_cli(job):
        loop, completed, argv, terminal, agent = job
        streams, descriptors, cleanup_errors = [], [], []
        stream_close_attempts, fd_close_attempts = set(), set()
        saved_streams = sys.stdin, sys.stdout, sys.stderr
        before_connects = cli_connects[0]
        result = failure = None

        def stream(fd, mode):
            # fdopen may fail after ownership transfer. Never close a possibly
            # reused numeric fd after an uncertain transfer.
            descriptors.remove(fd)
            try:
                value = os.fdopen(fd, mode, encoding="utf-8", buffering=1)
            except BaseException:
                cli_resource_debt.append(("fdopen-transfer-unknown", fd))
                raise
            streams.append(value)
            return value

        def close_stream(value):
            stream_close_attempts.add(id(value))
            try:
                value.close()
            except BaseException:
                cli_resource_debt.append(("stream-close-unknown", value))
                raise

        def close_fd(fd):
            fd_close_attempts.add(fd)
            try:
                os.close(fd)
            except BaseException:
                cli_resource_debt.append(("fd-close-unknown", fd))
                raise

        def duplicate(fd):
            copied = os.dup(fd)
            descriptors.append(copied)
            return copied

        try:
            if terminal:
                output_reader, slave = os.openpty()
                descriptors.extend((output_reader, slave))
                input_reader = stream(duplicate(slave), "r")
                output_writer = stream(duplicate(slave), "w")
                close_fd(slave)
                descriptors.remove(slave)
            else:
                input_fd, input_writer = os.pipe()
                descriptors.extend((input_fd, input_writer))
                output_reader, output_fd = os.pipe()
                descriptors.extend((output_reader, output_fd))
                input_reader = stream(input_fd, "r")
                output_writer = stream(output_fd, "w")
            sys.stdin, sys.stdout, sys.stderr = input_reader, output_writer, output_writer
            stdin_tty, stdout_tty = input_reader.isatty(), output_writer.isatty()
            assert stdin_tty is terminal and stdout_tty is terminal
            # Use the genuine descriptor's setup_fn and handler_fn. The tiny
            # argparse attachment is fixture wiring; never import native main,
            # whose module-level interrupted-update recovery is outside this test.
            command = manager._cli_commands["hmp"]
            parser = argparse.ArgumentParser(prog="hermes")
            groups = parser.add_subparsers(dest="command")
            hmp_parser = groups.add_parser(command["name"])
            command["setup_fn"](hmp_parser)
            hmp_parser.set_defaults(func=command["handler_fn"])
            try:
                parsed = parser.parse_args(argv)
                assert parsed.func is command["handler_fn"]
                fixture_env = dict(os.environ)
                if agent:
                    fixture_env["HERMES_SESSION_SYNTHETIC_AT1"] = "1"
                cli_module = importlib.import_module(module.__package__ + ".cli")
                env = cli_module.CliEnv(
                    environ=fixture_env,
                    identity_kwargs={
                        "host_id": lambda: identity_module.HostId(
                            identity_module.HOST_SOURCE_DARWIN,
                            "00000000-0000-4000-8000-000000000001",
                        )
                    },
                )
                code = parsed.func(parsed, env=env)
            except SystemExit as exc:
                code = exc.code
            assert type(code) is int
            output_writer.flush()
            # Darwin can discard unread PTY bytes at last-slave close. Drain
            # the actual flushed output while its slave remains owned/open.
            os.set_blocking(output_reader, False)
            raw = bytearray()
            capture_deadline = time.monotonic() + 2.0
            while True:
                # Bounded readiness observation, not tcdrain: Darwin may wait
                # for a master reader inside tcdrain itself. CLI has returned
                # and explicitly flushed, so no more command writes are owned.
                remaining = capture_deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("fixture_cli_capture_incomplete")
                ready, _, _ = select.select(
                    [output_reader], [], [], min(remaining, 0.05 if raw else 1.0)
                )
                if not ready:
                    break
                try:
                    chunk = os.read(output_reader, 4096)
                except BlockingIOError:
                    break
                except OSError as exc:
                    if terminal and exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                raw.extend(chunk)
                assert len(raw) <= 4096
            close_stream(output_writer)
            close_stream(input_reader)
            if not terminal:
                close_fd(input_writer)
                descriptors.remove(input_writer)
            result = {
                "code": code,
                "stdout": bytes(raw).decode("utf-8").replace("\r\n", "\n"),
                "stdinTty": stdin_tty,
                "stdoutTty": stdout_tty,
                "unixConnects": cli_connects[0] - before_connects,
            }
        except BaseException as exc:
            failure = exc
        finally:
            sys.stdin, sys.stdout, sys.stderr = saved_streams
            for value in streams:
                if id(value) in stream_close_attempts:
                    continue
                try:
                    close_stream(value)
                except BaseException as exc:
                    cleanup_errors.append(type(exc).__name__)
            for descriptor in descriptors:
                if descriptor in fd_close_attempts:
                    continue
                try:
                    close_fd(descriptor)
                except BaseException as exc:
                    cleanup_errors.append(type(exc).__name__)
            if cleanup_errors:
                # Retain evidence of uncertain ownership; do not replay closes
                # or turn a failed diagnostic into a successful native result.
                cli_resource_debt.append((streams, descriptors, cleanup_errors))
                if failure is None:
                    failure = RuntimeError("fixture_cli_cleanup_unconfirmed")
        if failure is not None:
            loop.call_soon_threadsafe(completed.set_exception, failure)
        else:
            loop.call_soon_threadsafe(completed.set_result, result)

    async def lifecycle():
        global context, adapter
        srv = None
        writer = None
        operator_service = None
        cleanup = []
        native_runner = None
        native_db_owners = []
        native_constructor_complete = False
        original_main_profile = sys.getprofile()
        original_thread_profile = None
        report["nativeRunnerResourcesReleased"] = False
        report["lifecycleResourcesReleased"] = False
        try:
            import threading

            from gateway.config import Platform
            from gateway.run import GatewayRunner
            from hermes_state import SessionDB

            original_thread_profile = threading.getprofile()
            runner_constructor = GatewayRunner.__init__.__code__
            db_constructor = SessionDB.__init__.__code__

            def retain_native_constructors(frame, event, arg):
                nonlocal native_runner
                if event == "call":
                    if frame.f_code is runner_constructor:
                        native_runner = frame.f_locals["self"]
                    if frame.f_code is db_constructor:
                        native_db_owners.append(frame.f_locals["self"])

            sys.setprofile(retain_native_constructors)
            threading.setprofile(retain_native_constructors)
            report["phase"] = "native-runner-construction"
            from hermes_cli.config import atomic_config_write, read_user_config_raw
            from hermes_cli.profiles import create_profile

            beta_home = create_profile("beta", no_alias=True, no_skills=True)
            assert beta_home == root / "home/profiles/beta"
            beta_config = read_user_config_raw(beta_home / "config.yaml")
            beta_config.setdefault("gateway", {})["multiplex_profiles"] = True
            beta_config.setdefault("sessions", {})["cjk_fts"] = False
            atomic_config_write(beta_home / "config.yaml", beta_config)
            report["nativeProfileCreated"] = True
            native_runner = GatewayRunner()
            native_constructor_complete = True
            assert native_runner.config.multiplex_profiles is True
            native_platform_config = native_runner.config.platforms[Platform("hmp")]
            from gateway.run import _multiplex_profile_homes

            native_homes = _multiplex_profile_homes(native_runner.config)
            assert native_homes == [("default", root / "home"), ("beta", beta_home)]
            native_runner._record_served_profiles("default", native_homes)
            report["nativeConfiguredRoutes"] = len(native_runner.config.profile_routes)
            report["nativeRunnerConstructed"] = True
            assert native_runner._session_db_init_error is None
            adapter = native_runner._create_adapter(Platform("hmp"), native_platform_config)
            assert adapter is not None and adapter.gateway_runner is native_runner
            native_runner.adapters[Platform("hmp")] = adapter
            report["nativeFactoryBound"] = True
            held_server = [None]
            held_context = [None]
            captures = [0]
            constructor_code = module.server.HmpServer.__init__.__code__
            connect_code = type(adapter).connect.__code__
            previous_profile = sys.getprofile()

            def observe_constructor(frame, event, arg):
                if (
                    event == "call"
                    and frame.f_code is constructor_code
                    and frame.f_back is not None
                    and frame.f_back.f_code is connect_code
                    and frame.f_back.f_locals.get("self") is adapter
                ):
                    captures[0] += 1
                    held_server[0] = frame.f_locals["self"]
                    held_context[0] = frame.f_locals["ctx"]
                    sys.setprofile(previous_profile)

            sys.setprofile(observe_constructor)
            try:
                connected = await adapter.connect()
            finally:
                sys.setprofile(previous_profile)
                if held_server[0] is not None:
                    srv = held_server[0]
                    context = held_context[0]
                report["actualServerConstructorCaptures"] = captures[0]
            report["adapterConnected"] = connected
            assert connected is True and captures[0] == 1 and srv is adapter._server
            assert srv is not None and srv.bound == ("127.0.0.1", port)
            context = srv.ctx
            operator_service = srv._operator_read
            assert operator_service is not None
            report.update(
                componentsOpened=True,
                supported=context.compat.supported,
                mediaFlag=context.media_enabled(),
                mediaAvailable=context.is_media_available(),
            )
            assert (
                context.compat.supported
                and context.media_enabled()
                and context.is_media_available()
            )
            report["connectedRuntimeStatus"] = await status_readback("connected")
            report["phase"] = "ready-client"
            client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            client.check_hostname = False
            client.verify_mode = ssl.CERT_REQUIRED
            client.load_verify_locations(cafile=str(context.identity.custody.cert_path))
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    "127.0.0.1",
                    port,
                    family=socket.AF_INET,
                    ssl=client,
                    server_hostname=None,
                    limit=8192,
                ),
                10,
            )
            negotiated = writer.get_extra_info("ssl_object")
            report["tlsVersion"] = negotiated.version()
            assert report["tlsVersion"] == "TLSv1.3"
            peer = negotiated.getpeercert(binary_form=True)
            assert hmac.compare_digest(
                hashlib.sha256(peer).digest(),
                hashlib.sha256(context.identity.certificate_der()).digest(),
            )
            report["peerCertificatePinnedBeforeRequest"] = True
            writer.write(
                b"GET /hmp/v1/ready HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
            )
            await writer.drain()
            headers = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            assert headers.startswith(b"HTTP/1.1 200 ")
            lengths = [
                int(line.split(b":", 1)[1].strip())
                for line in headers.split(b"\r\n")
                if line.lower().startswith(b"content-length:")
            ]
            assert len(lengths) == 1 and 0 < lengths[0] <= 32768
            body = await asyncio.wait_for(reader.readexactly(lengths[0]), 10)
            data = json.loads(body)
            assert data["iid"] == context.iid and data["versions"] == [1]
            report.update(
                readyHTTPStatus=200,
                readySameInstance=True,
                readyBodySHA256=hashlib.sha256(body).hexdigest(),
            )
            # All authority data below belongs to this new synthetic instance only.
            auth_crypto = importlib.import_module(module.__package__ + ".crypto")
            auth_wire = importlib.import_module(module.__package__ + ".wire")
            now = context.now()
            device_id = "a" * 32
            user_id = "synthetic_at1_owner"
            family_id = "b" * 32
            device_pub = auth_crypto.spki_der(auth_crypto.generate_private_key().public_key())
            context.store.insert_user(user_id, "Synthetic AT1 fixture", now)
            context.store.insert_device(
                device_id,
                user_id,
                auth_crypto.spki_fingerprint(device_pub),
                device_pub,
                "Synthetic AT1 fixture",
                now,
                state="ACTIVE",
            )
            context.store.insert_token_family(family_id, device_id, now)
            access = auth_crypto.random_bytes(32)
            context.store.insert_access_token(
                auth_crypto.sha256(access), family_id, device_id, context.iid, now + 600
            )
            authz = importlib.import_module(module.__package__ + ".contract").AuthzState
            assert context.bridge.authz_state(user_id, "default") is authz.PENDING_OPERATOR
            code = native_runner.pairing_store.generate_code("hmp", user_id, "Synthetic AT1 owner")
            assert native_runner.pairing_store.approve_code("hmp", code) is not None
            assert context.bridge.authz_state(user_id, "default") is authz.AUTHORIZED
            assert context.is_approval_owner_device(device_id) is True
            assert (
                context.direct_send_effective() is True and context.is_approvals_available() is True
            )
            db = SessionDB(root / "home/state.db")
            sid = "synthetic-at1-empty-bot-chat"
            try:
                db.create_session(sid, "api_server")
                assert db.set_session_title(sid, "Bot Chat") and db.set_session_hidden(sid, True)
                assert db.get_messages(sid) == []
            finally:
                db.close()
            selected = await asyncio.to_thread(context.bridge.approval_test_target, "default")
            assert selected is not None and selected.live_tip_session_id == sid
            service = srv._at1_service
            endpoint = srv._at1_endpoint
            assert (
                service is not None
                and endpoint is not None
                and context.approval_test_current() is True
            )
            report["actualAt1ListenerStarted"] = True
            at1_socket = endpoint._path
            cli = importlib.import_module(module.__package__ + ".cli")
            observer = importlib.import_module(module.__package__ + ".approval_test_cli")
            codec = importlib.import_module(module.__package__ + ".approval_test_host_codec")
            from io import StringIO

            generation = context.approval_test_generation

            def reread():
                record = cli.read_listener_record(adapter._record, iid=context.iid)
                return codec.HostGeneration(record.iid, record.pid, record.nonce)

            binding = observer.ListenerBinding(adapter._record, reread(), reread)
            assert binding.generation == generation

            async def phone(method, path, payload=None):
                r, w = await asyncio.wait_for(
                    asyncio.open_connection(
                        "127.0.0.1",
                        port,
                        family=socket.AF_INET,
                        ssl=client,
                        server_hostname=None,
                        limit=8192,
                    ),
                    5,
                )
                try:
                    ssl_peer = w.get_extra_info("ssl_object")
                    assert ssl_peer.version() == "TLSv1.3"
                    assert hmac.compare_digest(
                        hashlib.sha256(ssl_peer.getpeercert(binary_form=True)).digest(),
                        hashlib.sha256(context.identity.certificate_der()).digest(),
                    )
                    raw = (
                        b""
                        if payload is None
                        else json.dumps(payload, separators=(",", ":")).encode("ascii")
                    )
                    headers = [
                        method + " " + path + " HTTP/1.1",
                        "Host: 127.0.0.1",
                        "Connection: close",
                        "HMP-Instance: " + context.iid,
                        "Authorization: Bearer " + auth_wire.b64u_encode(access),
                    ]
                    if payload is not None:
                        headers += [
                            "Content-Type: application/json",
                            "Content-Length: " + str(len(raw)),
                        ]
                    w.write(("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + raw)
                    await w.drain()
                    head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 5)
                    status = int(head.split(b" ", 2)[1])
                    lengths = [
                        int(line.split(b":", 1)[1])
                        for line in head.split(b"\r\n")
                        if line.lower().startswith(b"content-length:")
                    ]
                    assert len(lengths) == 1 and 0 <= lengths[0] <= 4096
                    body = await asyncio.wait_for(r.readexactly(lengths[0]), 5)
                    assert await asyncio.wait_for(r.read(1), 5) == b""
                    return status, json.loads(body)
                finally:
                    w.close()
                    await w.wait_closed()

            report["registeredCliMode"] = registered_cli_mode
            begin_args = [
                "hmp",
                "approval-test",
                "begin",
                "--device",
                device_id,
                "--profile",
                "default",
                "--session",
                sid,
                "--timeout-ms",
                "2000",
            ]
            if registered_cli_mode:
                report["registeredCliRefusals"] = []
                for label, args, terminal, agent in (
                    (
                        "missing-session",
                        [
                            "hmp",
                            "approval-test",
                            "begin",
                            "--device",
                            device_id,
                            "--profile",
                            "default",
                        ],
                        True,
                        False,
                    ),
                    ("noninteractive", begin_args, False, False),
                    ("agent-session", begin_args, True, True),
                ):
                    refused = await registered_cli(args, terminal=terminal, agent=agent)
                    assert refused["code"] == (2 if label == "missing-session" else 1)
                    assert refused["unixConnects"] == 0 and service._operation is None
                    report["registeredCliRefusals"].append(
                        {
                            "case": label,
                            "code": refused["code"],
                            "stdinTty": refused["stdinTty"],
                            "stdoutTty": refused["stdoutTty"],
                            "noUnixRequest": True,
                        }
                    )
            report["cases"] = []
            for choice, expected in (
                ("once", "once_acknowledged"),
                ("deny", "denied"),
                ("cancel", "cancelled"),
                ("expiry", "expired"),
            ):
                output = StringIO()
                request = codec.HostBeginRequest(generation, device_id, "default", sid, 2000)
                parsed_begin = registered_cli_mode and choice != "cancel"
                task = asyncio.create_task(
                    registered_cli(begin_args)
                    if parsed_begin
                    # The auxiliary cancel-case begin runs on the server loop.
                    # It exercises the real observer/transport but no signals;
                    # parsed begin/cancel/status handlers run on the main thread.
                    else observer.run_command(
                        binding, request, output, install_signals=not registered_cli_mode
                    )
                )
                try:
                    deadline = asyncio.get_running_loop().time() + (
                        10 if registered_cli_mode else 1.5
                    )
                    card = None
                    while card is None:
                        assert asyncio.get_running_loop().time() < deadline
                        status, projection = await phone(
                            "GET", "/hmp/v1/bots/default/approval-tests/current"
                        )
                        assert status == 200 and projection.get("v") == 1
                        card = projection.get("card")
                        if card is None:
                            await asyncio.sleep(0.01)
                    assert set(card) == {"test_id", "title", "message", "choices"}
                    assert (
                        card["title"] == "Synthetic approval test"
                        and card["message"] == "No action will run."
                        and card["choices"] == ["once", "deny"]
                    )
                    producer = service._operation.producer
                    route = producer._owned_operation.route_key
                    native_approval = sys.modules["tools.approval"]
                    if choice in ("once", "deny"):
                        status, control = await phone(
                            "POST",
                            "/hmp/v1/approval-tests/" + card["test_id"] + "/answer",
                            {"v": 1, "choice": choice},
                        )
                        assert status == 202 and control.get("result") == "accepted"
                    elif choice == "cancel":
                        # A distinct real CLI observer/control invocation over the real socket.
                        operation = output.getvalue().split()[1].removesuffix(":")
                        cancel_output = StringIO()
                        if registered_cli_mode:
                            parsed_cancel = await registered_cli(
                                ["hmp", "approval-test", "cancel", operation]
                            )
                            code = parsed_cancel["code"]
                            cancel_text = parsed_cancel["stdout"]
                            assert parsed_cancel["stdinTty"] and parsed_cancel["stdoutTty"]
                            assert parsed_cancel["unixConnects"] == 1
                        else:
                            code = await observer.run_command(
                                binding,
                                codec.HostOperationRequest(generation, "cancel", operation),
                                cancel_output,
                            )
                            cancel_text = cancel_output.getvalue()
                        assert code == 2 and "cancel requested" in cancel_text
                    result = await asyncio.wait_for(asyncio.shield(task), 7)
                    if parsed_begin:
                        assert result["stdinTty"] and result["stdoutTty"]
                        assert result["unixConnects"] == 1
                        result_code, result_text = result["code"], result["stdout"]
                    else:
                        result_code, result_text = result, output.getvalue()
                    if registered_cli_mode:
                        report.setdefault("registeredCliResults", []).append(
                            {
                                "choice": choice,
                                "code": result_code,
                                "output": result_text,
                                "nativeTerminal": None
                                if service._terminal is None
                                else service._terminal.outcome.status.value,
                                "nativeQueueEmpty": not native_approval.list_gateway_approvals(
                                    route
                                ),
                                "producerSlotReleased": producer._slot.operation is None,
                            }
                        )
                    assert result_code == 0 and ("joined " + expected + ".") in result_text
                    if registered_cli_mode:
                        operation = result_text.split()[1].removesuffix(":")
                        status_result = await registered_cli(
                            ["hmp", "approval-test", "status", operation]
                        )
                        assert status_result["code"] == 0
                        assert expected in status_result["stdout"]
                        assert status_result["stdinTty"] and status_result["stdoutTty"]
                        assert status_result["unixConnects"] == 1
                    status, projection = await phone(
                        "GET", "/hmp/v1/bots/default/approval-tests/current"
                    )
                    assert status == 200 and projection == {"v": 1, "card": None}
                    assert service._operation is None
                    assert native_approval.list_gateway_approvals(route) == []
                    assert producer._slot.operation is None
                    report["cases"].append(
                        {
                            "choice": choice,
                            "observed": expected,
                            "actualCliObserver": True,
                            "registeredBeginParserHandler": parsed_begin,
                            "registeredCancelParserHandler": registered_cli_mode
                            and choice == "cancel",
                            "registeredStatusParserHandler": registered_cli_mode,
                            "realPtyObserved": registered_cli_mode,
                            "kernelAuthenticatedIpc": True,
                            "actualAuthenticatedHttpCard": True,
                            "joinedCompletion": True,
                            "cardWithdrawn": True,
                            "nativeQueueEmpty": True,
                            "producerSlotReleased": True,
                        }
                    )
                finally:
                    # Never retry a begin. If observation fails, own service cleanup first.
                    if not task.done():
                        await service.shutdown()
                        await asyncio.shield(task)
            db = SessionDB(root / "home/state.db")
            try:
                assert db.get_messages(sid) == []
            finally:
                db.close()
            report.update(
                nativeMessagesUnchanged=True,
                syntheticStoreAuthority=True,
                physicalCardObserved=False,
                realPairingQualified=False,
                shellParserTtyQualified=False,
                registeredHmpParserTtyQualified=registered_cli_mode,
                nativeLauncherMainCalled=False,
                fixtureSyntheticHostIdentityPort=True,
            )
            operator_service = srv._operator_read
            report["operatorSocketStarted"] = operator_service is not None
            assert operator_service is not None
        finally:
            if srv is None and adapter._server is not None:
                srv = adapter._server
                context = srv.ctx
            if writer is not None:
                try:
                    writer.close()
                    await writer.wait_closed()
                    report["clientClosed"] = True
                except BaseException as exc:
                    cleanup.append({"operation": "client-close", "type": type(exc).__name__})
            published_server = adapter._server
            try:
                if native_runner is not None and native_constructor_complete:
                    await native_runner.stop()
                    report["nativeRunnerStopped"] = True
                else:
                    await adapter.disconnect()
                report["adapterDisconnected"] = adapter._server is None
                owners = list(native_db_owners)
                report["nativeSessionDBOwners"] = len(owners)
                report["nativeSessionDBOwnersInitialized"] = bool(owners) and all(
                    "_conn" in vars(db) and "_token_writer_thread" in vars(db) for db in owners
                )
                report["nativeSessionDBOwnersClosed"] = report[
                    "nativeSessionDBOwnersInitialized"
                ] and all(db._conn is None and db._token_writer_thread is None for db in owners)
                report["nativeRunnerResourcesReleased"] = (
                    native_runner is None and not owners
                ) or (
                    report["nativeSessionDBOwnersClosed"]
                    and native_constructor_complete
                    and native_runner._stop_task is not None
                    and native_runner._stop_task.done()
                )
            except BaseException as exc:
                cleanup.append({"operation": "adapter-disconnect", "type": type(exc).__name__})
            if srv is not None and published_server is not srv:
                try:
                    await srv.stop(notify=False)
                    report["unpublishedServerStopObserved"] = True
                except BaseException as exc:
                    cleanup.append(
                        {"operation": "unpublished-server-stop", "type": type(exc).__name__}
                    )
            pending = [
                task
                for task in asyncio.all_tasks()
                if task is not asyncio.current_task() and not task.done()
            ]
            while pending:
                results = await asyncio.gather(*pending, return_exceptions=True)
                for result in results:
                    if isinstance(result, BaseException) and not isinstance(
                        result, asyncio.CancelledError
                    ):
                        cleanup.append(
                            {"operation": "native-task-settlement", "type": type(result).__name__}
                        )
                pending = [
                    task
                    for task in asyncio.all_tasks()
                    if task is not asyncio.current_task() and not task.done()
                ]
            report["eventLoopTasksSettled"] = True
            if "at1_socket" in locals():
                report["actualAt1SocketRemoved"] = not at1_socket.exists()
            if srv is not None:
                report.update(
                    serverClosed=srv.closed.is_set(),
                    operatorWorkerDebt=srv.operator_worker_debt,
                    storeClosedByAdapter=srv.ctx.store._conn is None,
                    listenerRunnerCleared=srv._runner is None,
                )
                with srv.ctx.read_worker_budget.lock:
                    report["readWorkerBudgetEmpty"] = (
                        srv.ctx.read_worker_budget.active == 0
                        and srv.ctx.read_worker_budget.operator == 0
                        and not srv.ctx.read_worker_budget.poisoned
                    )
                report["listenerRecordRemoved"] = adapter._record is None
                if operator_service is not None:
                    try:
                        operator_service.path.lstat()
                    except FileNotFoundError:
                        report["operatorSocketRemoved"] = True
                    else:
                        report["operatorSocketRemoved"] = False
            try:
                report["disconnectedRuntimeStatus"] = await status_readback("disconnected")
            except BaseException as exc:
                cleanup.append({"operation": "native-status-readback", "type": type(exc).__name__})
            writer_idle = False
            try:
                observations, status_errors = await settle_actual_status_writer()
                report["runtimeStatusWriterSettlement"] = observations
                cleanup.extend(status_errors)
                writer_idle = True
            except BaseException as exc:
                cleanup.append(
                    {"operation": "status-writer-settlement", "type": type(exc).__name__}
                )
            report["runtimeStatusWriterIdle"] = writer_idle
            report["lifecycleCleanupErrors"] = cleanup
            safe_release = (
                report.get("nativeRunnerResourcesReleased") is True
                and writer_idle
                and (
                    srv is None
                    or (
                        all(
                            report.get(key) is True
                            for key in [
                                "serverClosed",
                                "listenerRunnerCleared",
                                "eventLoopTasksSettled",
                                "readWorkerBudgetEmpty",
                            ]
                        )
                        and report.get("operatorWorkerDebt") == 0
                    )
                )
            )
            report["lifecycleResourcesReleased"] = safe_release
            if not safe_release:
                report["phase"] = "unresolved-teardown"
                try:
                    fd = os.open(
                        root / "unresolved-teardown.json",
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                    )
                    with os.fdopen(fd, "w") as f:
                        json.dump(
                            {
                                "stage": "holding-actual-listener-store",
                                "retryAllowed": False,
                                "cleanupErrors": cleanup,
                            },
                            f,
                        )
                except BaseException:  # noqa: S110 -- diagnostic failure cannot abandon owned wait.
                    pass
                await (
                    asyncio.Event().wait()
                )  # Retain the actual listener/store; no forced release/replay.
            sys.setprofile(original_main_profile)
            if original_thread_profile is not None or native_constructor_complete:
                threading.setprofile(original_thread_profile)
            if cleanup:
                raise RuntimeError("tls_lifecycle_cleanup_refused")

    if registered_cli_mode:
        lifecycle_failures = []

        def run_native_lifecycle():
            try:
                asyncio.run(lifecycle())
            except BaseException as exc:
                lifecycle_failures.append(exc)
            finally:
                cli_jobs.put(cli_stop)

        native_thread = threading.Thread(
            target=run_native_lifecycle, name="hmp-at1-fixture-server", daemon=False
        )
        start_failure = None
        try:
            native_thread.start()
        except BaseException as exc:
            if native_thread.ident is None and not native_thread.is_alive():
                raise
            start_failure = exc
        try:
            while True:
                job = cli_jobs.get()
                if job is cli_stop:
                    break
                run_registered_cli(job)
        finally:
            native_thread.join()
        report["fixtureServerThreadJoined"] = True
        report["fixtureCliResourceDebt"] = len(cli_resource_debt)
        assert not cli_resource_debt
        if start_failure is not None:
            raise start_failure
        if lifecycle_failures:
            raise lifecycle_failures[0]
    else:
        asyncio.run(lifecycle())
    assert report.get("readyHTTPStatus") == 200
    assert all(
        report.get(key) is True
        for key in [
            "clientClosed",
            "adapterDisconnected",
            "eventLoopTasksSettled",
            "serverClosed",
            "storeClosedByAdapter",
            "listenerRunnerCleared",
            "readWorkerBudgetEmpty",
            "listenerRecordRemoved",
            "operatorSocketStarted",
            "operatorSocketRemoved",
        ]
    )
    assert report["operatorWorkerDebt"] == 0
    assert report.get("nativeRunnerResourcesReleased") is True
    assert len(report.get("cases", [])) == 4 and report.get("nativeMessagesUnchanged") is True
    assert report.get("actualAt1SocketRemoved") is True
    report["phase"] = "complete"
except BaseException as exc:
    report.update(errorType=type(exc).__name__, error=str(exc))
    try:
        report["traceback"] = traceback.format_exc()
    except BaseException as diag:
        report["tracebackErrorType"] = type(diag).__name__
finally:
    cleanup_errors = []
    if original_identity_load is not None:
        identity_module.load_or_create = original_identity_load
    report["syntheticDarwinProcAbsences"] = absent_proc[0]
    report["publicOSVersionReads"] = os_metadata[0]
    report["rootAncestorDirectoryOpens"] = root_directory_opens[0]
    report["ownedPrivateFileDescriptorChmods"] = owned_fd_chmods[0]
    report["verifiedAbsentParentManifestProbes"] = absent_parent_manifest[0]
    if loader_threads is not None:
        with loader_lock:
            workers = tuple(loader_threads)
        live = [worker for worker in workers if worker.is_alive()]
        report["nativeLoaderAbandonedCount"] = len(workers)
        if live:
            report.update(phase="loader-settlement-refused", loaderTimeoutObserved=True)
            try:
                fd = os.open(
                    root / "settlement.json",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                )
                with os.fdopen(fd, "w") as f:
                    json.dump(
                        {
                            "stage": "waiting-original-loader-workers",
                            "workerIdentifiers": [worker.ident for worker in live],
                            "retryAllowed": False,
                        },
                        f,
                    )
            except BaseException as exc:
                cleanup_errors.append(
                    {"operation": "settlement-diagnostic", "type": type(exc).__name__}
                )
            finally:
                for worker in live:
                    worker.join()
        report["nativeLoaderWorkersSettled"] = all(not worker.is_alive() for worker in workers)
    if context is not None:
        report["storeClosed"] = context.store._conn is None
        if not report["storeClosed"]:
            cleanup_errors.append(
                {"operation": "native-store-close-readback", "type": "UnprovenStoreClose"}
            )
    if manager is not None and report.get("lifecycleResourcesReleased", True) is True:
        try:
            report["unloadResult"] = manager.unload("hmp")
            report["registrationsCleared"] = (
                not manager._plugin_platform_names
                and not manager._cli_commands
                and platform_registry.get("hmp") is None
            )
            if not report["registrationsCleared"]:
                cleanup_errors.append(
                    {"operation": "registry-readback", "type": "UnclearedRegistration"}
                )
        except BaseException as exc:
            cleanup_errors.append({"operation": "manager-unload", "type": type(exc).__name__})
    if report["phase"] == "complete" and not all(
        report.get(key) is True
        for key in [
            "nativeLoaderWorkersSettled",
            "storeClosed",
            "unloadResult",
            "registrationsCleared",
        ]
    ):
        cleanup_errors.append({"operation": "cleanup-readback", "type": "UnprovenCleanup"})
    if cleanup_errors:
        report.update(phase="cleanup-refused", cleanupErrors=cleanup_errors)
    out = root / "report.json"
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(report, f, indent=2)
print(
    json.dumps(
        {
            "phase": report["phase"],
            "completed": report["phase"] == "complete",
            "errorType": report.get("errorType"),
            "report": "report.json",
        }
    )
)
if report["phase"] != "complete":
    raise SystemExit(1)

"""Controlled Linux native journey entry; no live host or ordinary CLI use.

Only the reviewed isolated controller may prepare its fresh root/source/FD helper.
Flags and actual loopback-only interfaces are checked before fixture filesystem
or Hermes/SDK effects. This entry alone is not a network sandbox or runtime grant.
"""

import asyncio
import faulthandler
import hashlib
import hmac
import importlib.util
import json
import mimetypes
import os
import socket
import ssl
import stat
import sys
import traceback
from pathlib import Path
from urllib.parse import unquote, urlsplit

if __name__ != "__main__":
    raise SystemExit("native_fixture_direct_entry_required")
if sys.flags.optimize != 0 or not sys.flags.isolated or not sys.dont_write_bytecode:
    raise SystemExit("native_presentation_fixture_flags_refused")
if sys.platform != "linux":
    raise SystemExit("native_presentation_linux_required")
if {name for _, name in socket.if_nameindex()} != {"lo"}:
    raise SystemExit("native_fixture_isolated_loopback_required")
root = Path(sys.argv[1])
sample = Path(sys.argv[2])
native = sample / "native"
hmp = sample / "hmp"
assert len(sys.argv) == 5
scenario = sys.argv[4]
assert scenario in ("matrix", "mutation")
port = int(sys.argv[3])
assert 1 <= port <= 65535
assert sys.flags.isolated and sys.dont_write_bytecode
assert root.is_absolute() and root.resolve() == root and stat.S_IMODE(root.stat().st_mode) == 0o700
assert Path(os.environ["HERMES_HOME"]) == root / "home" and Path.home() == root / "user-home"
assert root.stat().st_uid == os.geteuid()
assert {p.name for p in root.iterdir()} <= {"tmp", "child.log", "_fixture_fd_scope.py"}
assert not (root == sample or root in sample.parents or sample in root.parents)
for folder in [root / "home", root / "user-home", root / "runtime"]:
    folder.mkdir(mode=0o700)
os.umask(0o077)
fd_path = root / "_fixture_fd_scope.py"
assert fd_path.is_file() and not fd_path.is_symlink()
assert (
    hashlib.sha256(fd_path.read_bytes()).hexdigest()
    == "692ae20b7bf86016dc7d7f27a678798cf3eb54dad1d601a4376e77b058554056"
)
fd_spec = importlib.util.spec_from_file_location("_fixture_fd_scope", fd_path)
fd_scope = importlib.util.module_from_spec(fd_spec)
fd_spec.loader.exec_module(fd_scope)
(root / "home/config.yaml").write_text(
    "sessions:\n  cjk_fts: false\ngateway:\n  multiplex_profiles: true\n"
    "  profile_routes:\n    - name: hmp-default\n      platform: hmp\n"
    "      profile: default\n      guild_id: default\n    - name: hmp-beta\n"
    "      platform: hmp\n      profile: beta\n      guild_id: beta\n"
    "platforms:\n  hmp:\n    enabled: true\n    extra:\n      bind: 127.0.0.1\n"
    f"      port: {port}\n      local_media:\n        enabled: true\n"
)
os.chdir(root)
allowed = [root, native, hmp, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
absent_proc = [0]
linux_proc_reads = [0]
os_metadata = [0]
absent_parent_manifest = [0]
root_directory_opens = [0]
owned_fd_chmods = [0]


def inside(p, base):
    return p == base or base in p.parents


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
            and sys.platform == "linux"
            and os.fsdecode(path)
            in ("/proc/1/cgroup", "/proc/self/mountinfo", f"/proc/{os.getpid()}/stat")
        ):
            assert stat.S_ISREG(p.stat().st_mode)
            linux_proc_reads[0] += 1
            return
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
        # The native caller retains its own fresh FD through this synchronous audit
        # and chmod. This samples scope, never durable authority against a foreign
        # same-process actor. The complete fixture uses only reviewed synthetic homes.
        fd_scope.verify_owned_writable_fd(fd, root)
        owned_fd_chmods[0] += 1
        return
    if event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.chmod"}:
        for raw in args[:2] if event == "os.rename" else args[:1]:
            if not inside(Path(os.fsdecode(raw)).resolve(), root):
                raise RuntimeError("smoke_write_refused")


sys.addaudithook(audit)
# Same built-in-only MIME seeding as the accepted native serving fixture.
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
report["observedNetworkInterfaces"] = ["lo"]
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
                identity_module.HOST_SOURCE_LINUX, "00000000000040008000000000000001"
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
            except BaseException:
                report["diagnosticWriteFailed"] = True
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
                    except BaseException:
                        report["diagnosticWriteFailed"] = True
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

            from gateway.config import GatewayConfig as GatewayConfig
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
            connect_code = type(adapter)._connect_once.__code__
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
            # Actual Store/authenticator/TLS with synthetic authority rows.
            # This is not a pairing or general bot-authorization qualification.
            auth_crypto = importlib.import_module(module.__package__ + ".crypto")
            auth_wire = importlib.import_module(module.__package__ + ".wire")
            now = context.now()
            device_id = "a" * 32
            user_id = "synthetic_tls_authority"
            family_id = "b" * 32
            device_key = auth_crypto.generate_private_key()
            device_pub = auth_crypto.spki_der(device_key.public_key())
            context.store.insert_user(user_id, "Synthetic TLS fixture", now)
            context.store.insert_device(
                device_id,
                user_id,
                auth_crypto.spki_fingerprint(device_pub),
                device_pub,
                "Synthetic fixture",
                now,
                state="ACTIVE",
            )
            context.store.insert_token_family(family_id, device_id, now)
            # Original native per-bot pairing store, not a patched authorization return.
            from importlib import import_module

            authz = import_module(module.__package__ + ".contract").AuthzState
            initial_authz = context.bridge.authz_state(user_id, "default")
            report["nativeAuthzBeforeApproval"] = initial_authz.value
            native_source = context.bridge._source(
                chat_id="synthetic-probe", user_id=user_id, profile="default", user_name=None
            )
            report["nativeRoutedProfile"] = native_source.profile
            report["nativeRouteRejected"] = native_source.profile_route_rejected
            assert initial_authz is authz.PENDING_OPERATOR
            first_code_request_monotonic = asyncio.get_running_loop().time()
            code = native_runner.pairing_store.generate_code(
                "hmp", user_id, "Synthetic native image user"
            )
            assert (
                type(code) is str
                and native_runner.pairing_store.approve_code("hmp", code) is not None
            )
            assert context.bridge.authz_state(user_id, "default") is authz.AUTHORIZED
            report["nativeBotAuthorizationObserved"] = True
            decision = context.store.media_read_decision(context.iid, device_id)
            assert decision is not None and decision.allowed is None
            assert context.store.set_media_read(decision, allowed=True, now=now) is not None
            assert context.media_read_permission(device_id) is not None
            report["syntheticMediaGrantViaActualCAS"] = True
            assert context.bridge.authz_state(user_id, "beta") is authz.PENDING_OPERATOR
            beta_pairing = native_runner.pairing_stores["beta"]
            beta_code = beta_pairing.generate_code("hmp", user_id, "Synthetic scoped user")
            assert (
                type(beta_code) is str and beta_pairing.approve_code("hmp", beta_code) is not None
            )
            assert context.bridge.authz_state(user_id, "beta") is authz.AUTHORIZED
            report["nativeTwoProfileApprovals"] = True
            device2 = "c" * 32
            family2 = "d" * 32
            key2 = auth_crypto.generate_private_key()
            pub2 = auth_crypto.spki_der(key2.public_key())
            context.store.insert_device(
                device2,
                user_id,
                auth_crypto.spki_fingerprint(pub2),
                pub2,
                "Second synthetic device",
                now,
                state="ACTIVE",
            )
            context.store.insert_token_family(family2, device2, now)
            decision2 = context.store.media_read_decision(context.iid, device2)
            assert decision2 is not None and decision2.allowed is None
            assert context.store.set_media_read(decision2, allowed=True, now=now) is not None
            assert context.media_read_permission(device2) is not None
            access2 = auth_crypto.random_bytes(32)
            context.store.insert_access_token(
                auth_crypto.sha256(access2), family2, device2, context.iid, now + 1800
            )
            access = auth_crypto.random_bytes(32)
            expired = auth_crypto.random_bytes(32)
            refresh = auth_crypto.random_bytes(32)
            context.store.insert_access_token(
                auth_crypto.sha256(access), family_id, device_id, context.iid, now + 1800
            )
            context.store.insert_access_token(
                auth_crypto.sha256(expired), family_id, device_id, context.iid, now - 1
            )
            context.store.insert_refresh_token(auth_crypto.sha256(refresh), family_id, now)

            async def auth_request(label, token, instance, expected):
                r, w = await asyncio.wait_for(
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
                try:
                    peer = w.get_extra_info("ssl_object").getpeercert(binary_form=True)
                    assert hmac.compare_digest(
                        hashlib.sha256(peer).digest(),
                        hashlib.sha256(context.identity.certificate_der()).digest(),
                    )
                    headers = [
                        "GET /hmp/v1/media-readiness/capabilities HTTP/1.1",
                        "Host: 127.0.0.1",
                        "Connection: close",
                    ]
                    if instance is not None:
                        headers.append("HMP-Instance: " + instance)
                    if token is not None:
                        headers.append("Authorization: Bearer " + auth_wire.b64u_encode(token))
                    w.write(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
                    await w.drain()
                    head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 10)
                    status = int(head.split(b" ", 2)[1])
                    assert status == expected
                    sizes = [
                        int(x.split(b":", 1)[1].strip())
                        for x in head.split(b"\r\n")
                        if x.lower().startswith(b"content-length:")
                    ]
                    assert len(sizes) == 1 and 0 < sizes[0] <= 32768
                    payload = json.loads(await asyncio.wait_for(r.readexactly(sizes[0]), 10))
                    if expected == 200:
                        assert payload == {
                            "protocol": 1,
                            "media_readiness": True,
                            "remote_permission_write": False,
                        }
                        assert any(
                            x.lower() == b"cache-control: no-store" for x in head.split(b"\r\n")
                        )
                    report.setdefault("authenticatedTLSCases", []).append(
                        {"case": label, "status": status, "peerPinnedBeforeRequest": True}
                    )
                finally:
                    w.close()
                    await w.wait_closed()

            await auth_request("valid-access", access, context.iid, 200)
            await auth_request("missing-instance", access, None, 401)
            await auth_request("wrong-instance", access, "z" * 52, 401)
            await auth_request("missing-token", None, context.iid, 401)
            await auth_request("unknown-access", auth_crypto.random_bytes(32), context.iid, 401)
            await auth_request("expired-access", expired, context.iid, 401)
            await auth_request("refresh-not-access", refresh, context.iid, 401)
            # Actual native cache materialization and committed canonical Bot Chat rows.
            import base64
            import struct
            import zlib

            from agent.image_gen_provider import save_b64_image, success_response

            def png_chunk(kind, data):
                return (
                    struct.pack(">I", len(data))
                    + kind
                    + data
                    + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
                )

            image = (
                b"\x89PNG\r\n\x1a\n"
                + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
                + png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff"))
                + png_chunk(b"IEND", b"")
            )
            from gateway.run import _profile_runtime_scope
            from hermes_constants import get_hermes_home_override

            original_home_context = get_hermes_home_override()
            with _profile_runtime_scope(root / "home"):
                image_path = save_b64_image(
                    base64.b64encode(image).decode("ascii"), prefix="xai_grok-imagine-image"
                )
            assert get_hermes_home_override() == original_home_context
            report["nativeProducerScopeRestored"] = True
            assert image_path.read_bytes() == image and inside(image_path.resolve(), root)
            db = SessionDB(root / "home/state.db")
            try:
                sid = "synthetic-native-tls-bot-chat"
                db.create_session(sid, "api_server")
                assert db.set_session_title(sid, "Bot Chat") and db.set_session_hidden(sid, True)
                db.append_message(
                    sid,
                    "assistant",
                    tool_calls=[
                        {
                            "id": "synthetic-image-call",
                            "type": "function",
                            "function": {"name": "image_generate", "arguments": "{}"},
                        }
                    ],
                )
                result = success_response(
                    image=str(image_path),
                    model="fixture-offline",
                    prompt="SYNTHETIC_NATIVE_TLS_IMAGE_ONLY",
                    aspect_ratio="landscape",
                    provider="fixture-offline",
                )
                db.append_message(
                    sid,
                    "tool",
                    tool_name="image_generate",
                    tool_call_id="synthetic-image-call",
                    content=json.dumps(result),
                )
            finally:
                db.close()
            # Independent canonical native image in the second actually served/approved profile.
            blue = (
                b"\x89PNG\r\n\x1a\n"
                + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
                + png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\xff\xff"))
                + png_chunk(b"IEND", b"")
            )
            with _profile_runtime_scope(beta_home):
                beta_image_path = save_b64_image(
                    base64.b64encode(blue).decode("ascii"), prefix="xai_grok-imagine-image"
                )
                beta_db = SessionDB(beta_home / "state.db")
                try:
                    beta_sid = "synthetic-native-beta-chat"
                    beta_db.create_session(beta_sid, "api_server")
                    assert beta_db.set_session_title(
                        beta_sid, "Bot Chat"
                    ) and beta_db.set_session_hidden(beta_sid, True)
                    beta_db.append_message(
                        beta_sid,
                        "assistant",
                        tool_calls=[
                            {
                                "id": "synthetic-beta-image",
                                "type": "function",
                                "function": {"name": "image_generate", "arguments": "{}"},
                            }
                        ],
                    )
                    beta_result = success_response(
                        image=str(beta_image_path),
                        model="fixture-offline",
                        prompt="SYNTHETIC_BETA_ONLY",
                        aspect_ratio="landscape",
                        provider="fixture-offline",
                    )
                    beta_db.append_message(
                        beta_sid,
                        "tool",
                        tool_name="image_generate",
                        tool_call_id="synthetic-beta-image",
                        content=json.dumps(beta_result),
                    )
                finally:
                    beta_db.close()
            assert (
                get_hermes_home_override() == original_home_context
                and beta_image_path.read_bytes() == blue
            )

            async def image_get(path, token=None):
                assert path.startswith("/hmp/v1/bots/") and "\r" not in path and "\n" not in path
                r, w = await asyncio.wait_for(
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
                try:
                    peer = w.get_extra_info("ssl_object").getpeercert(binary_form=True)
                    assert hmac.compare_digest(
                        hashlib.sha256(peer).digest(),
                        hashlib.sha256(context.identity.certificate_der()).digest(),
                    )
                    headers = [
                        "GET " + path + " HTTP/1.1",
                        "Host: 127.0.0.1",
                        "Connection: close",
                        "HMP-Instance: " + context.iid,
                        "Authorization: Bearer "
                        + auth_wire.b64u_encode(access if token is None else token),
                    ]
                    w.write(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
                    await w.drain()
                    category = (
                        "presentation_avatar"
                        if "/presentation/avatar/" in path
                        else "presentation_metadata"
                        if path.endswith("/presentation")
                        else "session_messages"
                        if "/messages" in path
                        else "session_list"
                        if path.endswith("/sessions")
                        else "media_bytes"
                    )
                    profile_label = path.split("/")[4]
                    assert profile_label in ("default", "beta")
                    report["lastSyntheticRead"] = {
                        "profile": profile_label,
                        "category": category,
                        "stage": "request_sent_waiting_headers",
                    }
                    faulthandler.dump_traceback_later(8, repeat=False)
                    try:
                        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 10)
                    finally:
                        faulthandler.cancel_dump_traceback_later()
                    status = int(head.split(b" ", 2)[1])
                    report.setdefault("syntheticReadStatuses", []).append(
                        {"profile": profile_label, "category": category, "status": status}
                    )
                    sizes = [
                        int(x.split(b":", 1)[1].strip())
                        for x in head.split(b"\r\n")
                        if x.lower().startswith(b"content-length:")
                    ]
                    assert len(sizes) == 1 and 0 < sizes[0] <= 1048576
                    body = await asyncio.wait_for(r.readexactly(sizes[0]), 10)
                    return status, head, body
                finally:
                    w.close()
                    await w.wait_closed()

            # All inputs below are synthetic files in the fresh two-profile fixture only.
            presentation_objects = {}
            presentation_expected = {
                "default": (root / "home", image, "hexagon"),
                "beta": (beta_home, blue, "squircle"),
            }
            for profile, (profile_home, avatar_bytes, shape) in presentation_expected.items():
                assert inside(profile_home.resolve(), root)
                assets = profile_home / "assets"
                assets.mkdir(mode=0o700, exist_ok=True)
                assert stat.S_IMODE(assets.stat().st_mode) == 0o700 and not assets.is_symlink()
                metadata = (
                    "display_name: Synthetic profile "
                    + profile
                    + "\nui_meta:\n  hermes-bots:\n    title: Synthetic Desktop "
                    + profile
                    + "\n    shape: "
                    + shape
                    + "\n    color: '#7c3aed'\n    custom: true\n"
                    "private: SYNTHETIC_NOT_FOR_OUTPUT\n"
                ).encode()
                (profile_home / "profile.yaml").write_bytes(metadata)
                (profile_home / "profile.yaml").chmod(0o600)
                (assets / "avatar.png").write_bytes(avatar_bytes)
                (assets / "avatar.png").chmod(0o600)
            report["phase"] = "native-presentation-read"
            service = srv._presentation_service
            assert service is not None and service is adapter._presentation_owner._service
            assert service._ctx is context and context.presentation_available() is True
            report["nativePresentationServiceBound"] = True
            report["nativePresentationCases"] = []
            for profile in ("default", "beta"):
                status, head, payload = await image_get("/hmp/v1/bots/" + profile + "/presentation")
                report["nativePresentationCases"].append(
                    {
                        "profile": profile,
                        "status": status,
                        "bodySHA256": hashlib.sha256(payload).hexdigest(),
                    }
                )
                assert status == 200, ("presentation_http_status", profile, status)
                obj = json.loads(payload)
                assert (
                    obj["version"] == 1 and obj["iid"] == context.iid and obj["profile"] == profile
                )
                assert type(obj["display_name"]) is str and obj["display_name"]
                expected_avatar = presentation_expected[profile][1]
                assert (
                    obj["display_name"] == "Synthetic Desktop " + profile
                    and obj["name_source"] == "bot_title"
                )
                assert obj["character"] == {
                    "version": 1,
                    "shape": presentation_expected[profile][2],
                    "color": "#7c3aed",
                    "custom": None,
                }
                assert obj["avatar"] == {
                    "revision": hashlib.sha256(expected_avatar).hexdigest(),
                    "mime": "image/png",
                    "bytes": len(expected_avatar),
                    "width": 1,
                    "height": 1,
                }
                assert b"SYNTHETIC_NOT_FOR_OUTPUT" not in payload
                presentation_objects[profile] = obj
                assert set(obj) == {
                    "version",
                    "iid",
                    "profile",
                    "display_name",
                    "name_source",
                    "character",
                    "metadata_revision",
                    "avatar",
                    "observed_at",
                }
                assert b"cache-control: no-store" in head.lower()
            report["nativePresentationMetadataObserved"] = True
            report["nativePresentationAvatarCases"] = []

            async def presentation_idle():
                deadline = asyncio.get_running_loop().time() + 5
                # No completion event is exposed. Observe actual operations
                # under the original five-second budget; never release them here.
                while service._ops and asyncio.get_running_loop().time() < deadline:  # noqa: ASYNC110
                    await asyncio.sleep(0.005)
                assert (
                    not service._ops
                )  # No forced capacity release or source mutation with live readers.

            async def exact_avatar(profile, token, expected):
                revision = hashlib.sha256(expected).hexdigest()
                status, head, body = await image_get(
                    "/hmp/v1/bots/" + profile + "/presentation/avatar/" + revision, token
                )
                assert status == 200 and body == expected
                assert (
                    b"content-type: image/png" in head.lower()
                    and b"cache-control: no-store" in head.lower()
                )
                return {
                    "profile": profile,
                    "status": status,
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "peerPinnedBeforeRequest": True,
                }

            for label, token in (("device1", access), ("device2", access2)):
                for profile in ("default", "beta"):
                    row = await exact_avatar(profile, token, presentation_expected[profile][1])
                    row["device"] = label
                    report["nativePresentationAvatarCases"].append(row)
            # Another profile's content hash is not authority to fetch its avatar here.
            for target, foreign in (("default", "beta"), ("beta", "default")):
                revision = presentation_objects[foreign]["avatar"]["revision"]
                status, _, body = await image_get(
                    "/hmp/v1/bots/" + target + "/presentation/avatar/" + revision
                )
                report.setdefault("nativePresentationRevisionRefusals", []).append(
                    {
                        "case": "foreign-profile-revision",
                        "status": status,
                        "code": json.loads(body)["error"]["code"],
                        "target": target,
                    }
                )
                assert status == 404 and json.loads(body)["error"]["code"] == "not_found"
            report["nativePresentationForeignRevisionRefused"] = True
            await presentation_idle()
            (root / "home/assets/avatar.png").write_bytes(blue)
            old_revision = presentation_objects["default"]["avatar"]["revision"]
            status, _, body = await image_get(
                "/hmp/v1/bots/default/presentation/avatar/" + old_revision
            )
            report.setdefault("nativePresentationRevisionRefusals", []).append(
                {
                    "case": "changed-asset-old-revision",
                    "status": status,
                    "code": json.loads(body)["error"]["code"],
                }
            )
            assert status == 404 and json.loads(body)["error"]["code"] == "not_found"
            status, _, body = await image_get("/hmp/v1/bots/default/presentation")
            assert (
                status == 200
                and json.loads(body)["avatar"]["revision"] == hashlib.sha256(blue).hexdigest()
            )
            await exact_avatar("default", access, blue)
            await exact_avatar("beta", access, blue)
            await presentation_idle()
            (root / "home/assets/avatar.png").write_bytes(image)
            await exact_avatar("default", access, image)
            report["nativePresentationAvatarRevisionChangeRefusedThenReadBack"] = True
            report["nativePresentationCharacterNameParityObserved"] = True

            # Early synthetic native bot revocation, before unrelated native transcript reads.
            # The original later media/revocation matrix below remains unchanged.
            await presentation_idle()
            assert native_runner.pairing_store.revoke("hmp", user_id)
            assert context.bridge.authz_state(user_id, "default") is authz.PENDING_OPERATOR
            assert context.bridge.authz_state(user_id, "beta") is authz.AUTHORIZED
            report["earlyNativePresentationRevocationCases"] = []
            for label, token in (("device1", access), ("device2", access2)):
                for suffix in (
                    "/presentation",
                    "/presentation/avatar/" + hashlib.sha256(image).hexdigest(),
                ):
                    status, _, body = await image_get("/hmp/v1/bots/default" + suffix, token)
                    assert (
                        status == 403
                        and json.loads(body)["error"]["authz"] == authz.PENDING_OPERATOR.value
                    )
                    report["earlyNativePresentationRevocationCases"].append(
                        {
                            "device": label,
                            "kind": "avatar" if "/avatar/" in suffix else "metadata",
                            "status": status,
                        }
                    )
                await exact_avatar("beta", token, blue)
            await presentation_idle()
            from gateway.pairing import RATE_LIMIT_SECONDS

            assert RATE_LIMIT_SECONDS == 600
            cooldown_end = first_code_request_monotonic + RATE_LIMIT_SECONDS + 2
            report["phase"] = "native-reapproval-cooldown"
            while asyncio.get_running_loop().time() < cooldown_end:
                remaining = cooldown_end - asyncio.get_running_loop().time()
                (root / "progress.json").write_text(
                    json.dumps(
                        {
                            "stage": "native-reapproval-cooldown",
                            "remainingSeconds": round(remaining, 1),
                            "noClockOrPolicyBypass": True,
                        }
                    )
                )
                await asyncio.sleep(min(30, remaining))
            report["nativeReapprovalCooldownElapsedSeconds"] = (
                asyncio.get_running_loop().time() - first_code_request_monotonic
            )
            code = native_runner.pairing_store.generate_code(
                "hmp", user_id, "Synthetic avatar revocation restoration"
            )
            report["nativeReapprovalCodeGenerated"] = type(code) is str
            assert type(code) is str, "native_reapproval_code_unavailable_after_natural_cooldown"
            approved = native_runner.pairing_store.approve_code("hmp", code)
            report["nativeReapprovalAccepted"] = approved is not None
            assert approved is not None, "native_reapproval_not_accepted"
            report["phase"] = "native-presentation-read"
            assert context.bridge.authz_state(user_id, "default") is authz.AUTHORIZED
            assert context.bridge.authz_state(user_id, "beta") is authz.AUTHORIZED
            for token in (access, access2):
                await exact_avatar("default", token, image)
            await presentation_idle()
            report["earlyNativePresentationRevocationAndRestorationObserved"] = True

            status, _, body = await image_get("/hmp/v1/bots/default/sessions")
            assert status == 200
            sessions = json.loads(body)["sessions"]
            assert len(sessions) == 1
            session_ref = sessions[0]["session_ref"]
            status, _, body = await image_get(
                "/hmp/v1/bots/default/sessions/" + session_ref + "/messages"
            )
            assert status == 200
            descriptors = [row["media"] for row in json.loads(body)["messages"] if "media" in row]
            assert len(descriptors) == 1
            ref = descriptors[0]["ref"]
            status, headers, body = await image_get("/hmp/v1/bots/default/media/" + ref)
            assert status == 200 and body == image
            assert (
                b"content-type: image/png" in headers.lower()
                and b"cache-control: no-store" in headers.lower()
            )
            report.update(
                authenticatedImageFetchObserved=True,
                imageFetchScope=(
                    "one default-profile native cache image; synthetic input, "
                    "no provider/phone/fault/Linux/full-matrix qualification"
                ),
                nativeImageTLSBytesMatched=True,
                nativeImageSHA256=hashlib.sha256(body).hexdigest(),
                nativeCanonicalChatRead=True,
                nativeImageBytes=len(body),
            )

            async def descriptor(profile, token):
                status, _, body = await image_get("/hmp/v1/bots/" + profile + "/sessions", token)
                assert status == 200
                rows = json.loads(body)["sessions"]
                assert len(rows) == 1
                route = (
                    "/hmp/v1/bots/" + profile + "/sessions/" + rows[0]["session_ref"] + "/messages"
                )
                status, _, body = await image_get(route, token)
                assert status == 200
                items = [row["media"] for row in json.loads(body)["messages"] if "media" in row]
                assert len(items) == 1
                return items[0]["ref"]

            async def exact_image(profile, reference, token, expected):
                status, head, body = await image_get(
                    "/hmp/v1/bots/" + profile + "/media/" + reference, token
                )
                assert status == 200 and body == expected
                assert (
                    b"content-type: image/png" in head.lower()
                    and b"cache-control: no-store" in head.lower()
                )

            ref2 = await descriptor("default", access2)
            beta_ref = await descriptor("beta", access)
            beta_ref2 = await descriptor("beta", access2)
            cells = (
                ("device1/default", "default", ref, access, image),
                ("device2/default", "default", ref2, access2, image),
                ("device1/beta", "beta", beta_ref, access, blue),
                ("device2/beta", "beta", beta_ref2, access2, blue),
            )
            assert len({cell[2] for cell in cells}) == 4
            for _label, profile, reference, token, expected in cells:
                await exact_image(profile, reference, token, expected)
            report["nativeIsolationPositiveCells"] = [cell[0] for cell in cells]
            status, _, notfound = await image_get("/hmp/v1/bots/default/media/" + "A" * 43, access)
            assert status == 404
            report["nativeUnknownRefHTTPStatus"] = status
            report["nativeIsolationCases"] = []
            for owner_label, _, reference, _, _ in cells:
                for target_label, profile, _, token, _ in cells:
                    if owner_label == target_label:
                        continue
                    status, _, body = await image_get(
                        "/hmp/v1/bots/" + profile + "/media/" + reference, token
                    )
                    assert status == 404 and body == notfound
                    report["nativeIsolationCases"].append(
                        {
                            "referenceOwner": owner_label,
                            "caller": target_label,
                            "status": status,
                            "sameOpaqueNotFound": True,
                        }
                    )
            for _, profile, reference, token, expected in cells:
                await exact_image(profile, reference, token, expected)
            # Media decision revocation and regrant must not revive a generation-bound ref.
            current = context.store.media_read_decision(context.iid, device_id)
            assert current.allowed is True
            assert (
                context.store.set_media_read(current, allowed=False, now=context.now()) is not None
            )
            status, _, body = await image_get("/hmp/v1/bots/default/media/" + ref, access)
            assert status == 404 and body == notfound
            status, _, body = await image_get("/hmp/v1/bots/beta/media/" + beta_ref, access)
            assert status == 404 and body == notfound
            await exact_image("default", ref2, access2, image)
            await exact_image("beta", beta_ref2, access2, blue)
            current = context.store.media_read_decision(context.iid, device_id)
            assert current.allowed is False
            assert (
                context.store.set_media_read(current, allowed=True, now=context.now()) is not None
            )
            status, _, body = await image_get("/hmp/v1/bots/default/media/" + ref, access)
            assert status == 404 and body == notfound
            status, _, body = await image_get("/hmp/v1/bots/beta/media/" + beta_ref, access)
            assert status == 404 and body == notfound
            ref = await descriptor("default", access)
            beta_ref = await descriptor("beta", access)
            await exact_image("default", ref, access, image)
            await exact_image("beta", beta_ref, access, blue)
            await exact_image("default", ref2, access2, image)
            await exact_image("beta", beta_ref2, access2, blue)
            report["nativeMediaRegrantOldRefRefusedNewRefWorks"] = True
            if scenario == "matrix":
                assert native_runner.pairing_store.revoke("hmp", user_id)
                assert context.bridge.authz_state(user_id, "default") is authz.PENDING_OPERATOR
                status, _, _ = await image_get("/hmp/v1/bots/default/media/" + ref)
                assert status != 200 and status in (403, 404, 409)
                report["nativeBotRevocationRefusedImage"] = True
                status, _, _ = await image_get("/hmp/v1/bots/default/media/" + ref2, access2)
                assert status in (403, 404, 409)
                assert context.bridge.authz_state(user_id, "beta") is authz.AUTHORIZED
                await exact_image("beta", await descriptor("beta", access), access, blue)
                await exact_image("beta", beta_ref2, access2, blue)
                status, _, _ = await image_get(
                    "/hmp/v1/bots/default/presentation/avatar/" + hashlib.sha256(image).hexdigest()
                )
                assert status == 403
                await exact_avatar("beta", access, blue)
                report["nativePresentationAvatarBotRevocationIsProfileScoped"] = True
                report["nativeBotRevocationIsProfileScoped"] = True
            else:
                image_path.write_bytes(blue)
                status, _, body = await image_get("/hmp/v1/bots/default/media/" + ref, access)
                assert status == 404 and body == notfound
                await exact_image("beta", await descriptor("beta", access), access, blue)
                status, _, body = await image_get("/hmp/v1/bots/default/media/" + ref2, access2)
                assert status == 404 and body == notfound
                await exact_image("beta", beta_ref2, access2, blue)
                report["nativeChangedFileRefusedOtherProfileUnaffected"] = True
            foreign_iid = auth_crypto.spki_fingerprint(
                auth_crypto.spki_der(auth_crypto.generate_private_key().public_key())
            )
            assert foreign_iid != context.iid
            foreign_access = auth_crypto.random_bytes(32)
            context.store.insert_access_token(
                auth_crypto.sha256(foreign_access),
                family_id,
                device_id,
                foreign_iid,
                context.now() + 600,
            )
            await auth_request("stored-foreign-instance-access", foreign_access, context.iid, 401)
            await auth_request("valid-after-stored-foreign-instance", access, context.iid, 200)
            report["nativeStoredForeignInstanceTokenRefused"] = True
            report["imageFetchScope"] = (
                "two native profiles/two entitled synthetic devices; "
                "foreign refs, media generation tombstone; "
                + scenario
                + " branch only; no provider/phone/fault/Linux/full-instance matrix"
            )
            context.store.revoke_family(family_id, now)
            await auth_request("revoked-family", access, context.iid, 401)
            report.update(
                actualAuthenticatorUsed=True,
                syntheticStoreAuthority=True,
                pairingLifecycleQualified=False,
                botAuthorizationQualified=False,
                authenticatedImageFetchQualified=False,
            )
            operator_service = srv._operator_read
            report["operatorSocketStarted"] = operator_service is not None
            assert operator_service is not None
        finally:
            if srv is None and adapter._server is not None:
                srv = adapter._server
                context = srv.ctx
            if srv is None and adapter._failed_start_server is not None:
                srv = adapter._failed_start_server
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
            if srv is None:
                # Empty presentation domain is cleanup-only, never binding/GET proof.
                presentation = adapter._presentation_owner._service
                report["presentationServicePresent"] = presentation is not None
                report["presentationDrained"] = presentation is None
                report["presentationWorkerDebt"] = presentation is not None
                report["dependenciesClosedByAdapter"] = context is None

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
                presentation = srv._presentation_service
                report["presentationServicePresent"] = presentation is not None
                report["presentationDrained"] = presentation is None or (
                    presentation.drained and not presentation._ops
                )
                report["presentationWorkerDebt"] = srv.presentation_worker_debt
                report["dependenciesClosedByAdapter"] = srv._dependencies_closed
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
            safe_release = (
                safe_release
                and report.get("presentationDrained") is True
                and report.get("presentationWorkerDebt") is False
                and report.get("dependenciesClosedByAdapter") is True
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
                                "observedReport": report,
                                "pendingErrorType": (
                                    type(sys.exception()).__name__
                                    if sys.exception() is not None
                                    else None
                                ),
                                "pendingTraceback": traceback.format_exc(),
                                "qualificationClaimed": False,
                            },
                            f,
                        )
                except BaseException:
                    report["diagnosticWriteFailed"] = True
                await (
                    asyncio.Event().wait()
                )  # Retain the actual listener/store; no forced release/replay.
            sys.setprofile(original_main_profile)
            if original_thread_profile is not None or native_constructor_complete:
                threading.setprofile(original_thread_profile)
            if cleanup:
                raise RuntimeError("tls_lifecycle_cleanup_refused")

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
    assert (
        report.get("nativeImageTLSBytesMatched") is True
        and report.get("nativeRunnerResourcesReleased") is True
    )
    assert len(report.get("nativeIsolationCases", [])) == 12
    assert (
        report.get(
            "nativeBotRevocationIsProfileScoped"
            if scenario == "matrix"
            else "nativeChangedFileRefusedOtherProfileUnaffected"
        )
        is True
    )
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
    report["actualLinuxProcMetadataReads"] = linux_proc_reads[0]
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

"""Isolated native-DB serving sample, never production activation or T12 proof.

Run only in a fresh -I -B child with a reviewed source-only native archive under
root/native and HOME/HERMES_HOME/HERMES_RUNTIME_DIR under the private root. No
native imports occur on module import. Source materialization is a separate,
reviewed parent action; never execute an old temporary harness.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import stat
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from urllib.parse import unquote, urlsplit

_ROOT = Path(__file__).resolve().parents[2]
_OS_METADATA = Path("/System/Library/CoreServices/SystemVersion.plist")


def _require(ok):
    if not ok:
        raise RuntimeError("LOCAL_MEDIA_NATIVE_FIXTURE_REFUSED")


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(path, root):
    return path == root or root in path.parents


_MAX_IMPORT_ENTRIES = 20000


def _inventory_sources(base):
    """Bound every entry before collection; reject alternate import artifacts."""
    _require(base.resolve() == base and base.is_dir() and not base.is_symlink())
    stack, inventory, count, total = [base], {}, 0, 0
    while stack:
        with os.scandir(stack.pop()) as entries:
            for entry in entries:
                count += 1
                _require(count <= _MAX_IMPORT_ENTRIES and not entry.is_symlink())
                path = Path(entry.path)
                info = entry.stat(follow_symlinks=False)
                _require(info.st_uid == os.geteuid() and not info.st_mode & 0o022)
                if stat.S_ISDIR(info.st_mode):
                    _require(entry.name not in ("__pycache__", ".git"))
                    stack.append(path)
                else:
                    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
                    _require(path.suffix.lower() not in
                             (".pyc", ".pyo", ".so", ".dylib", ".dll", ".pyd",
                              ".zip", ".egg", ".whl", ".pyz"))
                    total += info.st_size
                    _require(info.st_size <= 4 * 1024 * 1024 and total <= 128 * 1024 * 1024)
                    inventory[str(path.relative_to(base))] = _digest(path)
    _require(inventory)
    return inventory


def _checked_sqlite_path(raw, root):
    text = os.fspath(raw)
    _require(type(text) is str and "\x00" not in text)
    if text == ":memory:":
        return None  # Native schema comparison uses a connection-private, fileless database.
    if text.startswith("file:"):
        parts = urlsplit(text)
        _require(parts.scheme == "file" and parts.netloc == "" and
                 parts.query == "mode=ro" and parts.fragment == "")
        decoded = unquote(parts.path, encoding="utf-8", errors="strict")
        _require("\x00" not in decoded and Path(decoded).is_absolute())
        path = Path(decoded).resolve()
        _require(path.as_uri() + "?mode=ro" == text)
    else:
        _require(Path(text).is_absolute())
        path = Path(text).resolve()
    _require(_inside(path, root))
    return path


def _check_import_origins(modules, source, hmp):
    _require(len(modules) <= 20000)
    for name, module in modules.items():
        if name == "agent" or name.startswith("agent."):
            expected = source / "agent"
        elif name.startswith("hermes_"):
            expected = source
        elif name == "hmp_plugin" or name.startswith("hmp_plugin."):
            expected = hmp / "server/hmp_plugin"
        elif name == "unit" or name.startswith("unit."):
            expected = hmp / "server/tests/unit"
        else:
            continue
        _require(type(module) is ModuleType)
        filename = vars(module).get("__file__")
        _require(type(filename) is str)
        path = Path(filename).resolve()
        _require(path.suffix == ".py" and _inside(path, expected)
                 and path.is_file() and not path.is_symlink())



def _require_fresh_source_modules(modules):
    _require(len(modules) <= 20000)
    _require(not any(name == "agent" or name.startswith("agent.") or
                     name.startswith("hermes_") or name == "hmp_plugin" or
                     name.startswith("hmp_plugin.") or name == "unit" or
                     name.startswith("unit.") for name in modules))

def _cleanup_setup(owners, native_registry, db, fx, patch, root, report):
    if not owners["workers_joined"]:
        return False  # Unsettled owners remain intact; never free beneath work.
    try:
        if db is not None:
            _require(native_registry.release(db) is True)
            report["native_database_close_observed"] = db._conn is None
    finally:
        try:
            # Scoped failure cleanup follows actual worker settlement. A sweep
            # cannot convert an unbalanced or failed measurement into success.
            swept = native_registry.close_all_under(root)
            report["scoped_native_sweep"] = swept
            _require(swept == 0)
        finally:
            try:
                partial_rig = getattr(fx, "rig", None)
                partial_env = getattr(partial_rig, "env", None)
                store = getattr(partial_env, "store", None)
                if store is not None:
                    store.close()
            finally:
                patch.undo()
    return True






def _open_writes(mode, flags):
    return (isinstance(mode, str) and any(x in mode for x in "wax+")) or (
        isinstance(flags, int) and bool(flags &
            (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))

def _absent_darwin_proc_probe(raw, writing):
    # Native directory hardening unconditionally probes Linux container files.
    # Return the ordinary Darwin absence without opening any outside file.
    return (sys.platform == "darwin" and not writing and type(raw) is str and
            raw in ("/proc/1/cgroup", "/proc/self/mountinfo", f"/proc/{os.getpid()}/stat"))


def _absent_darwin_proc_listing(raw):
    return sys.platform == "darwin" and type(raw) is str and raw == "/proc/self/fd"


def _own_darwin_fd_listing(raw):
    return sys.platform == "darwin" and type(raw) is str and raw == "/dev/fd"


def _public_os_metadata_read(raw, writing):
    if sys.platform != "darwin" or writing or type(raw) is not str or raw != str(_OS_METADATA):
        return False
    info = _OS_METADATA.lstat()
    _require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1 and
             not info.st_mode & 0o222 and info.st_size <= 65536 and
             _OS_METADATA.resolve() == _OS_METADATA)
    return True

def _refuse_with_diagnostic(denied, code):
    if len(denied) < 16:
        record = {"code": code, "source_frames": []}
        denied.append(record)  # Latch before optional diagnostics can fail.
        frame = None
        try:
            frame = sys._getframe(1)
            while frame is not None and len(record["source_frames"]) < 12:
                record["source_frames"].append((Path(frame.f_code.co_filename).name,
                                                frame.f_code.co_name, frame.f_lineno))
                frame = frame.f_back
        except BaseException:
            record["diagnostic_capture_failed"] = True
        finally:
            del frame  # Never retain frames, locals or payloads in diagnostics.
    raise PermissionError("LOCAL_MEDIA_FIXTURE_IO_REFUSED")

def _builtin_mime_types():
    """Owned fixture process only: deterministic stdlib tables, no OS MIME inputs."""
    import mimetypes

    # A cold init(files=[]) still reads knownfiles and the Windows registry.
    # Seed the builtin-only database first, then publish its tables through init.
    mimetypes.inited = True
    mimetypes._db = mimetypes.MimeTypes(filenames=())
    mimetypes.init(files=[])

def _private_directory(path):
    info = path.lstat()
    _require(path.resolve() == path and stat.S_ISDIR(info.st_mode) and
             info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700)


@contextmanager
def _binding_cell(root, fx, registry, borrowed, lock, selection, owners, index, profile):
    """Own one fresh synthetic-profile DB; restore scope only after actual closure."""
    _require(type(index) is int and 0 <= index < 6 and fx.service.stats() == (0, 0, 0))
    with lock:
        _require(borrowed["acquired"] == borrowed["released"])
    _private_directory(root)
    base = root / "binding-cells"
    base.mkdir(mode=0o700, exist_ok=True)
    _private_directory(base)
    home = base / f"cell-{index}"
    home.mkdir(mode=0o700)  # Exclusive: never reuse or follow another cell's path.
    path = home / "state.db"
    prior = (fx.native.home_path, fx.native.home,
             fx.native.world.runner.homes[profile], selection[0])
    owner = {"db": None, "closed": False, "prior": prior}
    owners.append(owner)  # Retain ownership before native allocation.
    cell_db = registry.acquire(path)
    owner["db"] = cell_db
    fx.native.home_path, fx.native.home = home, str(home)
    fx.native.world.runner.homes[profile] = home
    selection[0] = (path, cell_db)
    try:
        yield cell_db
    finally:
        # No restore/close while a borrower or original media worker remains.
        with lock:
            _require(borrowed["acquired"] == borrowed["released"])
        _require(fx.service.stats() == (0, 0, 0))
        _require(registry.release(cell_db) is True and cell_db._conn is None)
        owner["closed"] = True
        (fx.native.home_path, fx.native.home,
         fx.native.world.runner.homes[profile], selection[0]) = prior


def run_fixture(root, *, sample_memory=False, sample_binding_seed=False):
    """One native scratch DB, real routes/registry, synthetic transport authority.

    Python audit restrictions are test guards, NOT an OS sandbox or complete
    native-library IO observation. This does not qualify live startup/auth/grants.
    """
    _require(type(sample_memory) is bool and type(sample_binding_seed) is bool and
             not (sample_memory and sample_binding_seed))
    _require(sys.flags.isolated == 1 and sys.dont_write_bytecode is True)
    _require(type(root) is type(Path()) and root.is_absolute() and root.resolve() == root)
    info = root.stat()
    _require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700)
    _require(Path.cwd().resolve() == root)
    source = root / "native"
    _require((source / "hermes_state.py").is_file())
    for key, leaf in (("HOME", "user-home"), ("HERMES_HOME", "home"),
                      ("HERMES_RUNTIME_DIR", "runtime")):
        _require(os.environ.get(key) == str(root / leaf))
        (root / leaf).mkdir(mode=0o700, exist_ok=True)
    _require_fresh_source_modules(sys.modules)
    _require(root / "hmp" == _ROOT)
    pins = _inventory_sources(source)
    hmp_pins = _inventory_sources(_ROOT)
    (root / "home/config.yaml").write_text("sessions:\n  cjk_fts: false\n")
    denied = []
    absent_proc_probes = [0]
    os_metadata_reads, own_fd_listings = [0], [0]
    allowed_endpoint = [None]
    reads = (root, _ROOT, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve())

    def refuse(code):
        _refuse_with_diagnostic(denied, code)

    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            mode, flags = args[1], args[2]
            write = _open_writes(mode, flags)
            if _absent_darwin_proc_probe(args[0], write):
                absent_proc_probes[0] += 1
                raise FileNotFoundError("fixture_darwin_linux_proc_absent")
            if write and not _inside(path, root):
                refuse("write_outside_scratch")
            if _public_os_metadata_read(args[0], write):
                if os_metadata_reads[0] >= 8:
                    refuse("os_metadata_budget")
                os_metadata_reads[0] += 1
            elif not _inside(path, root) and (path.name == ".env" or not any(
                    _inside(path, permitted) for permitted in reads)):
                refuse("read_outside_fixture_sources")
        elif event in ("os.link", "os.symlink"):
            refuse("link_creation")
        elif event in ("os.rename", "os.replace"):
            if any(not _inside(Path(os.fsdecode(p)).resolve(), root) for p in args[:2]):
                refuse("rename_outside_scratch")
        elif event in ("os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.utime", "os.truncate"):
            if isinstance(args[0], (str, bytes, os.PathLike)) and not _inside(
                    Path(os.fsdecode(args[0])).resolve(), root):
                refuse("mutation_outside_scratch")
        elif event in ("os.listdir", "os.scandir"):
            if _absent_darwin_proc_listing(args[0]):
                absent_proc_probes[0] += 1
                raise FileNotFoundError("fixture_darwin_linux_proc_absent")
            if _own_darwin_fd_listing(args[0]):
                if own_fd_listings[0] >= 4096:
                    refuse("own_fd_listing_budget")
                own_fd_listings[0] += 1
                return  # Names only for this fresh child; no descriptor bytes are opened.
            if isinstance(args[0], (str, bytes, os.PathLike)) and not any(
                    _inside(Path(os.fsdecode(args[0])).resolve(), permitted)
                    for permitted in reads):
                refuse("listing_outside_fixture_sources")
        elif event == "sqlite3.connect":
            try:
                _checked_sqlite_path(args[0], root)
            except (RuntimeError, ValueError, TypeError, OSError):
                refuse("sqlite_outside_or_invalid_scratch_uri")
        elif event == "sqlite3.load_extension":
            refuse("sqlite_extension")
        elif event == "socket.bind":
            address = args[1]
            if not (isinstance(address, tuple) and address == ("127.0.0.1", 0)):
                refuse("nonfixture_bind")
        elif event == "socket.connect":
            if args[1] != allowed_endpoint[0]:
                refuse("nonfixture_connect")
        elif event in ("subprocess.Popen", "os.system", "os.fork", "os.posix_spawn"):
            refuse("process_creation")

    sys.addaudithook(audit)
    _builtin_mime_types()
    sys.path[:0] = [str(source), str(_ROOT / "server"), str(_ROOT / "server/tests")]
    import hermes_state_registry as native_registry
    import pytest
    from agent.image_gen_provider import save_b64_image, success_response
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    from hermes_constants import (
        get_hermes_home_override,
        reset_hermes_home_override,
        set_hermes_home_override,
    )
    from unit.test_s4_descriptors import PROFILE, USER
    from unit.test_s5_media_fetch import FORBIDDEN_HEADERS, VALID_PNG, VALID_PNG_B, Fx

    from hmp_plugin import local_media_candidate, local_media_file_safety, media_fetch
    from hmp_plugin.revoke import revoke_device

    _check_import_origins(dict(sys.modules), source, _ROOT)
    patch = pytest.MonkeyPatch()
    fx = Fx.__new__(Fx)  # Retain before fixture setup can open its store.
    db = None
    db_path = None
    borrowed = {"acquired": 0, "released": 0}
    lock = threading.Lock()
    report = {"schema": 1, "native_database": True, "native_registry": True,
              "synthetic_routing_authorization": True, "synthetic_compatibility_result": True,
              "actual_image_producer": False,
              "production_qualified": False, "t12_qualified": False,
              "provider_generation_executed": False}
    # No worker exists during setup. This becomes false before actual async work,
    # and true again only after original owned workers are known joined.
    owners = {"server": None, "client": None, "workers_joined": True}
    binding_selection = [None]
    binding_owners = []

    def acquire(path):
        selected_path, selected_db = binding_selection[0] or (db_path, db)
        _require(Path(path).resolve() == selected_path.resolve())
        result = native_registry.acquire(path)
        _require(result is selected_db)
        with lock:
            borrowed["acquired"] += 1
        return result

    def release(value):
        _, selected_db = binding_selection[0] or (db_path, db)
        _require(value is selected_db and native_registry.release(value) is True)
        with lock:
            borrowed["released"] += 1

    def open_binding_cell(index):
        _require(sample_binding_seed)
        return _binding_cell(root, fx, native_registry, borrowed, lock,
                             binding_selection, binding_owners, index, PROFILE)

    try:
        Fx.__init__(fx, root / "rig", patch, kind="phone", images=3)
        fx.native.world.approve(USER, "beta")  # Synthetic per-bot scope for ref-isolation test.
        db_path = fx.native.home_path / "state.db"
        _require(db_path.read_bytes() == b"")  # Only the helper's synthetic placeholder.
        db_path.unlink()
        db = native_registry.acquire(db_path)
        fx.native.world.api.acquire = acquire
        fx.native.world.api.release = release
        db.create_session("p1", "api_server")

        image_paths = {}
        materializations = [0]

        def seed_image(number, image_data=VALID_PNG):
            if number == 2:
                image_path = fx.write(number, VALID_PNG)
                content = {"success": True, "image": str(image_path)}
            else:
                before = get_hermes_home_override()
                token = set_hermes_home_override(fx.native.home_path)
                try:
                    image_path = save_b64_image(base64.b64encode(image_data).decode("ascii"),
                                               prefix="xai_grok-imagine-image")
                finally:
                    reset_hermes_home_override(token)
                _require(get_hermes_home_override() == before)
                report["producer_home_context_restored"] = True
                location = local_media_candidate.derive_cache_location(
                    str(image_path), str(fx.native.home_path))
                _require(location == (local_media_file_safety.CacheLayout.GENERATED,
                                      image_path.name) and image_path.read_bytes() == image_data)
                materializations[0] += 1
                report["native_cache_materializer"] = True
                content = success_response(image=str(image_path), model="fixture-offline",
                    prompt="SYNTHETIC_NATIVE_CACHE_VALIDATION_ONLY", aspect_ratio="landscape",
                    provider="fixture-offline")
                shadow = fx.native.home_path / "cache/images" / image_path.name
                shadow.write_bytes(VALID_PNG_B)  # A wrong namespace cannot pass the PNG control.
            image_paths[number] = image_path
            call = f"fixture-image-call-{number}"
            db.append_message("p1", "assistant", tool_calls=[{
                "id": call, "type": "function",
                "function": {"name": "image_generate", "arguments": "{}"}}])
            row = db.append_message("p1", "tool", tool_name="image_generate",
                tool_call_id=call, content=json.dumps(content))
            _require(row == number)
            return row

        tool_ids = {seed_image(number) for number in (2, 4, 6)}
        changed = {"file": False, "authorization": False}

        def change_file():
            image_paths[4].write_bytes(VALID_PNG_B)
            changed["file"] = True

        def revoke_synthetic_bot_access():
            fx.native.world.runner.approved[PROFILE].clear()
            changed["authorization"] = True

        async def scenario():
            app = fx.rig.env.app()
            memory_handlers = []
            if sample_memory:
                @web.middleware
                async def observe_memory_handler(request, handler):
                    if "/media/" in request.path:
                        memory_handlers.append(asyncio.current_task())
                    return await handler(request)
                app.middlewares.append(observe_memory_handler)
            fx.app = app
            fx._remember_media_service(app[media_fetch.MEDIA_SERVICE_KEY])
            server = TestServer(app, host="127.0.0.1")
            owners["server"] = server  # Retain before bind/start effects.
            try:
                await server.start_server()
                allowed_endpoint[0] = ("127.0.0.1", server.port)
                client = TestClient(server)
                owners["client"] = client
                try:
                    await client.start_server()
                    owner = await fx.rig.pair(client)
                    refs = await fx.mint(client, owner)
                    _require(set(refs) == tool_ids)
                    status, headers, body = await fx.get(client, refs[2], dev=owner)
                    _require(status == 200 and body == VALID_PNG)
                    _require(headers["Content-Type"] == "image/png" and
                        headers["Content-Length"] == str(len(VALID_PNG)) and
                        headers["Cache-Control"] == "no-store, private" and
                        headers["X-Content-Type-Options"] == "nosniff" and
                        all(k not in headers for k in FORBIDDEN_HEADERS))
                    report["exact_authenticated_bytes_headers"] = True
                    report["legacy_compatibility_control"] = True
                    other = await fx.rig.pair(client)
                    other_refs = await fx.mint(client, other)
                    status, _, body = await fx.get(client, other_refs[2], dev=other)
                    _require(status == 200 and body == VALID_PNG)
                    report["other_device_positive_control"] = True
                    status, _, _ = await fx.get(client, refs[2], dev=other)
                    _require(status == 404)
                    report["other_device_refused"] = True
                    status, _, _ = await fx.get(client, refs[2], dev=owner, profile="beta")
                    _require(status == 404)
                    report["other_profile_refused"] = True
                    # A positive control on each target precedes its single changed
                    # fact, so prior asset failure cannot make a refusal vacuous.
                    status, _, body = await fx.get(client, refs[4], dev=owner)
                    _require(status == 200 and body == VALID_PNG)
                    report["native_generated_cache_control"] = True
                    change_file()
                    status, _, _ = await fx.get(client, refs[4], dev=owner)
                    _require(status == 404 and changed["file"])
                    report["file_change_after_first_serve_refused"] = True
                    status, _, body = await fx.get(client, refs[6], dev=owner)
                    _require(status == 200 and body == VALID_PNG)
                    fx.after_p1.append(revoke_synthetic_bot_access)
                    status, _, _ = await fx.get(client, refs[6], dev=owner)
                    _require(status == 404 and changed["authorization"])
                    report["between_phase_authorization_change_refused"] = True
                    fx.after_p1.clear()
                    fx.native.world.approve(USER, PROFILE)
                    status, _, body = await fx.get(client, refs[6], dev=owner)
                    _require(status == 200 and body == VALID_PNG)
                    db.clear_messages("p1")
                    status, _, _ = await fx.get(client, refs[6], dev=owner)
                    _require(status == 404)
                    report["message_change_before_fetch_refused"] = True
                    fresh = seed_image(8)
                    refs = await fx.mint(client, owner)
                    _require(set(refs) == {fresh})
                    status, _, body = await fx.get(client, refs[fresh], dev=owner)
                    _require(status == 200 and body == VALID_PNG)
                    revoke_device(fx.rig.env.store, owner.device_id, now=fx.rig.env.clock.now)
                    status, _, _ = await fx.get(client, refs[fresh], dev=owner)
                    _require(status == 401)
                    report["revoked_device_refused"] = True
                    if sample_binding_seed:
                        import importlib.util

                        from unit.test_local_media_batch_binding import CHAT

                        path = _ROOT / "tools/compat/local_media_native_binding_sample.py"
                        spec = importlib.util.spec_from_file_location(
                            "_private_media_binding", path)
                        helper = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(helper)
                        report["native_binding_preparation"] = helper.run_preparation(
                            fx, open_binding_cell, user=USER, profile=PROFILE, chat=CHAT)
                        _require(len(binding_owners) == 6 and
                                 all(owner["closed"] for owner in binding_owners))
                    if sample_memory:
                        import importlib.util

                        path = _ROOT / "tools/compat/local_media_native_memory_sample.py"
                        spec = importlib.util.spec_from_file_location("_private_media_memory", path)
                        helper = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(helper)
                        # Pinned aiohttp retries idempotent requests after a stale
                        # connection by default. Never replay a cancelled sample.
                        prior_retry = client.session._retry_connection
                        _require(type(prior_retry) is bool)
                        client.session._retry_connection = False
                        try:
                            report["native_memory_observation"] = await helper.run_memory_sample(
                                fx, client, seed_image, memory_handlers, VALID_PNG)
                        finally:
                            client.session._retry_connection = prior_retry
                finally:
                    fx._close_media_admissions_and_release_gates()
                    await client.close()
            finally:
                fx._close_media_admissions_and_release_gates()
                await server.close()

        restore = fx._observe_starts()
        try:
            owners["workers_joined"] = False
            asyncio.run(scenario())
        finally:
            try:
                fx._close_owned_media_workers()
            except BaseException:
                # Retain the same pool/DB/routing owners after the observation
                # timeout. No new request, retry, work budget or successful late
                # cleanup. Preserve the original failure after actual settlement.
                workers = {thread for service in fx.owned_media_services
                           for thread in tuple(service._executor._threads)}
                while any(thread.is_alive() for thread in workers):
                    for thread in workers:
                        thread.join(0.1)
                owners["workers_joined"] = True
                raise
            else:
                owners["workers_joined"] = True
            finally:
                if owners["workers_joined"]:
                    restore()
        _require(borrowed["acquired"] > 0 and borrowed["acquired"] == borrowed["released"])
        _require(owners["server"].closed is True and fx.service.closed is True)
        report.update(listener_closed=True, workers_joined=True, borrowed_native_balanced=True,
                      native_acquires=borrowed["acquired"], native_releases=borrowed["released"],
                      descriptor_records_retained=fx.registry._audit(),
                      native_cache_materializations=materializations[0])
    finally:
        _cleanup_setup(owners, native_registry, db, fx, patch, root, report)
    _require(owners["workers_joined"] and report["native_database_close_observed"])
    if denied or (root / "home/state.db").exists():
        raise RuntimeError("fixture_final_containment_refused:" + json.dumps({
            "denial_codes": denied, "default_state_created": (root / "home/state.db").exists()}))
    _require(_inventory_sources(source) == pins and _inventory_sources(_ROOT) == hmp_pins)
    _check_import_origins(dict(sys.modules), source, _ROOT)
    os_metadata_sha = _digest(_OS_METADATA)
    report.update(audit_denials=0, synthetic_absent_linux_proc_probes=True,
                  fixture_public_os_metadata_allowed=True,
                  os_metadata_sha256=os_metadata_sha, os_metadata_reads=os_metadata_reads[0],
                  own_fd_listings=own_fd_listings[0],
                  expected_absent_proc_probes=absent_proc_probes[0],
                  source_unchanged=True, selected_source_origins_checked=True,
                  native_source_hashes=pins,
                  hmp_source_hashes=hmp_pins, runtime_executable_sha256=_digest(
                      Path(sys.executable).resolve()))
    return report

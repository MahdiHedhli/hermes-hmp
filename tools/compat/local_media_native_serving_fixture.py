"""Isolated native-DB serving sample, never production activation or T12 proof.

Run only in a fresh -I -B child with a reviewed source-only native archive under
root/native and HOME/HERMES_HOME/HERMES_RUNTIME_DIR under the private root. No
native imports occur on module import. Source materialization is a separate,
reviewed parent action; never execute an old temporary harness.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
import sys
import threading
from pathlib import Path
from types import ModuleType
from urllib.parse import unquote, urlsplit

_ROOT = Path(__file__).resolve().parents[2]


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
        if name.startswith("hermes_"):
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



def _builtin_mime_types():
    """Owned fixture process only: deterministic stdlib tables, no OS MIME inputs."""
    import mimetypes

    # A cold init(files=[]) still reads knownfiles and the Windows registry.
    # Seed the builtin-only database first, then publish its tables through init.
    mimetypes.inited = True
    mimetypes._db = mimetypes.MimeTypes(filenames=())
    mimetypes.init(files=[])

def run_fixture(root):
    """One native scratch DB, real routes/registry, synthetic transport authority.

    Python audit restrictions are test guards, NOT an OS sandbox or complete
    native-library IO observation. This does not qualify live startup/auth/grants.
    """
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
    _require(not any(name.startswith("hermes_") or name == "hmp_plugin" or
                     name.startswith("hmp_plugin.") or name == "unit" or
                     name.startswith("unit.") for name in sys.modules))
    _require(root / "hmp" == _ROOT)
    pins = _inventory_sources(source)
    hmp_pins = _inventory_sources(_ROOT)
    (root / "home/config.yaml").write_text("sessions:\n  cjk_fts: false\n")
    denied = []
    allowed_endpoint = [None]
    reads = (root, _ROOT, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve())

    def refuse(code):
        denied.append(code)
        raise PermissionError("LOCAL_MEDIA_FIXTURE_IO_REFUSED")

    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            mode, flags = args[1], args[2]
            write = (isinstance(mode, str) and any(x in mode for x in "wax+")) or (
                isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)))
            if write and not _inside(path, root):
                refuse("write_outside_scratch")
            if not _inside(path, root) and (path.name == ".env" or not any(
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
    from aiohttp.test_utils import TestClient, TestServer
    from unit.test_s4_descriptors import PROFILE, USER
    from unit.test_s5_media_fetch import FORBIDDEN_HEADERS, VALID_PNG, VALID_PNG_B, Fx

    from hmp_plugin import media_fetch
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
              "production_qualified": False, "t12_qualified": False}
    # No worker exists during setup. This becomes false before actual async work,
    # and true again only after original owned workers are known joined.
    owners = {"server": None, "client": None, "workers_joined": True}

    def acquire(path):
        _require(Path(path).resolve() == db_path.resolve())
        result = native_registry.acquire(path)
        _require(result is db)
        with lock:
            borrowed["acquired"] += 1
        return result

    def release(value):
        _require(value is db and native_registry.release(value) is True)
        with lock:
            borrowed["released"] += 1

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

        def seed_image(number):
            call = f"fixture-image-call-{number}"
            db.append_message("p1", "assistant", tool_calls=[{
                "id": call, "type": "function",
                "function": {"name": "image_generate", "arguments": "{}"}}])
            row = db.append_message("p1", "tool", tool_name="image_generate",
                tool_call_id=call, content=json.dumps({"success": True,
                "image": str(fx.image_path(number))}))
            _require(row == number)
            fx.write(row, VALID_PNG)
            return row

        tool_ids = {seed_image(number) for number in (2, 4, 6)}
        changed = {"file": False, "authorization": False}

        def change_file():
            fx.write(4, VALID_PNG_B)
            changed["file"] = True

        def revoke_synthetic_bot_access():
            fx.native.world.runner.approved[PROFILE].clear()
            changed["authorization"] = True

        async def scenario():
            app = fx.rig.env.app()
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
                      descriptor_records_retained=fx.registry._audit())
    finally:
        _cleanup_setup(owners, native_registry, db, fx, patch, root, report)
    _require(owners["workers_joined"] and report["native_database_close_observed"])
    _require(not denied and not (root / "home/state.db").exists())
    _require(_inventory_sources(source) == pins and _inventory_sources(_ROOT) == hmp_pins)
    _check_import_origins(dict(sys.modules), source, _ROOT)
    report.update(audit_denials=0, source_unchanged=True, selected_source_origins_checked=True,
                  native_source_hashes=pins,
                  hmp_source_hashes=hmp_pins, runtime_executable_sha256=_digest(
                      Path(sys.executable).resolve()))
    return report

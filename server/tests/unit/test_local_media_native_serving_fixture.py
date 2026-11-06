"""Fixture import and refusal checks; these never import/run native Hermes."""
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_serving_fixture.py"


def load():
    spec = importlib.util.spec_from_file_location("_hmp_native_media_fixture_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_is_inert_for_native_and_test_rigs():
    before = set(sys.modules)
    module = load()
    assert callable(module.run_fixture)
    added = set(sys.modules) - before
    assert not any(name.startswith(("hermes_state", "unit.test_s5")) for name in added)


def test_nonisolated_process_refuses_before_path_or_native_effects(tmp_path):
    if sys.flags.isolated:
        pytest.skip("This case checks refusal in a nonisolated parent")
    module = load()
    nonexistent = tmp_path / "not-created"
    with pytest.raises(RuntimeError, match="LOCAL_MEDIA_NATIVE_FIXTURE_REFUSED"):
        module.run_fixture(nonexistent)
    assert not nonexistent.exists()


@pytest.mark.parametrize("kind", ["path", "uri", "escaped_uri"])
def test_sqlite_guard_accepts_only_canonical_scratch_forms(tmp_path, kind):
    module = load()
    path = tmp_path / ("space ? #.db" if kind == "escaped_uri" else "state.db")
    raw = path if kind == "path" else path.as_uri() + "?mode=ro"
    assert module._checked_sqlite_path(raw, tmp_path) == path
    assert not path.exists()  # URI validation opens no database.


@pytest.mark.parametrize("case", ["lexical_escape", "outside", "authority", "extra_query",
                                  "fragment", "relative", "encoded_escape"])
def test_sqlite_uri_guard_refuses_escape_without_native_open(tmp_path, case):
    module = load()
    outside = tmp_path.parent / "not-this-fixture.db"
    inside = tmp_path / "state.db"
    raw = {
        "lexical_escape": "file:" + str(outside) + "?mode=ro",
        "outside": outside.as_uri() + "?mode=ro",
        "authority": "file://localhost" + str(inside) + "?mode=ro",
        "extra_query": inside.as_uri() + "?mode=ro&immutable=1",
        "fragment": inside.as_uri() + "?mode=ro#ignored",
        "relative": "file:state.db?mode=ro",
        "encoded_escape": "file:" + str(tmp_path) + "/%2E%2E/not-this-fixture.db?mode=ro",
    }[case]
    with pytest.raises(RuntimeError):
        module._checked_sqlite_path(raw, tmp_path)
    assert not inside.exists() and not outside.exists()


@pytest.mark.parametrize("artifact", ["bad.pyc", "bad.so", "bad.zip", "bad.pyd",
                                       "bad.whl", "bad.pyz", "__pycache__"])
def test_source_inventory_refuses_alternate_import_artifacts(tmp_path, artifact):
    module = load()
    path = tmp_path / artifact
    if artifact == "__pycache__":
        path.mkdir()
    else:
        path.write_bytes(b"not executed")
    with pytest.raises(RuntimeError):
        module._inventory_sources(tmp_path)


def test_source_inventory_refuses_symlink_directory_without_traversing(tmp_path):
    module = load()
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "other"
    outside.mkdir()
    (outside / "data.py").write_bytes(b"not executed")
    (source / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError):
        module._inventory_sources(source)


def test_source_inventory_bounds_entry_enumeration(tmp_path, monkeypatch):
    module = load()
    (tmp_path / "a.py").write_bytes(b"not executed")
    (tmp_path / "b.py").write_bytes(b"not executed")
    monkeypatch.setattr(module, "_MAX_IMPORT_ENTRIES", 1)
    with pytest.raises(RuntimeError):
        module._inventory_sources(tmp_path)


@pytest.mark.parametrize("stage", ["partial_setup", "seeded_failure", "unknown_worker",
                                   "release_error"])
def test_partial_setup_cleanup_preserves_unsettled_owners(tmp_path, stage):
    from types import SimpleNamespace

    module = load()
    effects = set()
    db = SimpleNamespace(_conn=object()) if stage != "partial_setup" else None

    def release(value):
        assert value is db
        effects.add("native_release")
        if stage == "release_error":
            raise RuntimeError("synthetic release failure")
        value._conn = None
        return True

    def sweep(root):
        assert root == tmp_path
        effects.add("scoped_sweep")
        return 0

    registry = SimpleNamespace(release=release, close_all_under=sweep)
    store = SimpleNamespace(close=lambda: effects.add("store_close"))
    fx = SimpleNamespace(rig=SimpleNamespace(env=SimpleNamespace(store=store)))
    patch = SimpleNamespace(undo=lambda: effects.add("patch_undo"))
    owners = {"workers_joined": stage != "unknown_worker"}
    report = {}
    if stage == "release_error":
        with pytest.raises(RuntimeError, match="synthetic release failure"):
            module._cleanup_setup(owners, registry, db, fx, patch, tmp_path, report)
    else:
        result = module._cleanup_setup(owners, registry, db, fx, patch, tmp_path, report)
        assert result is (stage != "unknown_worker")
    if stage == "unknown_worker":
        assert not effects and db._conn is not None and not report
    else:
        assert {"scoped_sweep", "store_close", "patch_undo"} <= effects
        assert ("native_release" in effects) is (db is not None)
        if stage == "seeded_failure":
            assert report["native_database_close_observed"] is True


@pytest.mark.parametrize("origin", ["native", "hmp", "unit", "outside", "bytecode", "fabricated"])
def test_import_origin_check_binds_private_source_roots(tmp_path, origin):
    from types import ModuleType

    module = load()
    source, hmp = tmp_path / "native", tmp_path / "hmp"
    expected = {
        "native": ("hermes_state", source / "hermes_state.py"),
        "hmp": ("hmp_plugin.bridge", hmp / "server/hmp_plugin/bridge.py"),
        "unit": ("unit.test_s5_media_fetch", hmp / "server/tests/unit/test_s5_media_fetch.py"),
        "outside": ("hmp_plugin.bridge", tmp_path / "other/bridge.py"),
        "bytecode": ("hermes_state", source / "hermes_state.pyc"),
        "fabricated": ("hermes_state", source / "not-present.py"),
    }[origin]
    if origin != "fabricated":
        expected[1].parent.mkdir(parents=True, exist_ok=True)
        expected[1].write_bytes(b"source marker, not executed")
    item = ModuleType(expected[0])
    item.__file__ = str(expected[1])
    if origin in ("outside", "bytecode", "fabricated"):
        with pytest.raises(RuntimeError):
            module._check_import_origins({expected[0]: item}, source, hmp)
    else:
        module._check_import_origins({expected[0]: item}, source, hmp)


def test_real_partial_fixture_store_is_retained_and_closed(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from . import hmp_kit
    from .test_s5_media_fetch import Fx

    module = load()
    original = hmp_kit.Env.__init__

    def fail_after_open(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("synthetic post-store setup failure")

    monkeypatch.setattr(hmp_kit.Env, "__init__", fail_after_open)
    own_patch = pytest.MonkeyPatch()
    fx = Fx.__new__(Fx)
    with pytest.raises(RuntimeError, match="synthetic post-store setup failure"):
        Fx.__init__(fx, tmp_path / "rig", own_patch, images=1)
    store = fx.rig.env.store
    assert store._conn is not None
    registry = SimpleNamespace(close_all_under=lambda root: 0)
    assert module._cleanup_setup({"workers_joined": True}, registry, None,
                                 fx, own_patch, tmp_path, {}) is True
    assert store._conn is None


@pytest.mark.parametrize("cold", [True, False])
def test_builtin_mime_setup_ignores_host_files_and_registry(tmp_path, monkeypatch, cold):
    import mimetypes

    module = load()
    host = tmp_path / "host-mime.types"
    host.write_text("application/x-private hmp_private\n")
    for name in ("inited", "_db", "suffix_map", "types_map", "encodings_map", "common_types"):
        monkeypatch.setattr(mimetypes, name, getattr(mimetypes, name))
    monkeypatch.setattr(mimetypes, "knownfiles", [str(host)])
    if cold:
        monkeypatch.setattr(mimetypes, "inited", False)
        monkeypatch.setattr(mimetypes, "_db", None)
    else:
        monkeypatch.setattr(mimetypes, "inited", True)
        warm = mimetypes.MimeTypes(filenames=())
        warm.add_type("application/x-private", ".hmp_private")
        monkeypatch.setattr(mimetypes, "_db", warm)
        assert mimetypes.guess_type("image.hmp_private") == ("application/x-private", None)

    def registry_refused(*args, **kwargs):
        raise AssertionError("fixture must not read the host MIME registry")

    monkeypatch.setattr(mimetypes.MimeTypes, "read_windows_registry", registry_refused)
    module._builtin_mime_types()
    assert mimetypes.guess_type("image.png") == ("image/png", None)
    assert mimetypes.guess_type("image.hmp_private") == (None, None)


def test_sqlite_guard_admits_only_exact_fileless_memory_form(tmp_path):
    module = load()
    assert module._checked_sqlite_path(":memory:", tmp_path) is None
    for value in ("", "memory:", "file::memory:", "file::memory:?cache=shared", b":memory:"):
        with pytest.raises((RuntimeError, TypeError)):
            module._checked_sqlite_path(value, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_audit_denial_latches_before_optional_diagnostic_failure(monkeypatch):
    module = load()
    denied = []

    def fail_capture(*args):
        raise RuntimeError("synthetic diagnostic fault")

    with (pytest.raises(PermissionError, match="LOCAL_MEDIA_FIXTURE_IO_REFUSED"),
          monkeypatch.context() as patch):
        patch.setattr(sys, "_getframe", fail_capture)
        module._refuse_with_diagnostic(denied, "read_outside_fixture_sources")
    assert denied == [{"code": "read_outside_fixture_sources", "source_frames": [],
                       "diagnostic_capture_failed": True}]

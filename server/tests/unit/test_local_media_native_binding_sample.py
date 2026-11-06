"""Preparation contract models only; no Hermes, database, file, HTTP or provider operations."""
import importlib.util
import json
import sys
import threading
import types
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_binding_sample.py"


def load():
    spec = importlib.util.spec_from_file_location("_binding_sample_guard_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DBModel:
    """Record only the proposed public call contract, never model native performance."""

    def __init__(self, *, drop_prompt=False):
        self.sessions = {}
        self.messages = []
        self.calls = []
        self.drop_prompt = drop_prompt

    def get_session(self, sid):
        self.calls.append(("get_session", sid))
        row = self.sessions.get(sid)
        return None if row is None else dict(row)

    def create_session(self, sid, source, *, parent_session_id, system_prompt):
        self.calls.append(("create_session", sid))
        self.sessions[sid] = {"id": sid, "parent_session_id": parent_session_id,
            "system_prompt": None if self.drop_prompt else system_prompt, "source": source}
        return sid

    def end_session(self, sid, reason):
        self.calls.append(("end_session", sid))
        self.sessions[sid]["end_reason"] = reason

    def set_session_hidden(self, sid, hidden):
        self.sessions[sid]["hidden"] = int(hidden)
        return True

    def set_session_title(self, sid, title):
        self.sessions[sid]["title"] = title
        return True

    def get_compression_lineage(self, root):
        return list(self.sessions)

    def resolve_resume_session_id(self, root):
        return list(self.sessions)[-1]

    def append_message(self, sid, role, **kwargs):
        row_id = len(self.messages) + 1
        self.messages.append({"id": row_id, "session_id": sid, "role": role, **kwargs})
        return row_id

    def get_messages(self, sid, *, limit):
        return [row for row in self.messages if row["session_id"] == sid][:limit]


def test_import_is_inert():
    before = set(sys.modules)
    assert callable(load().seed_native_shape)
    assert not any(name.startswith(("hermes_", "psutil", "sqlite3", "aiohttp"))
                   for name in set(sys.modules) - before)


def test_bound_modules_uses_actual_nested_listener_snapshot():
    chain = tuple(types.ModuleType(f"fixture_{index}") for index in range(7))
    assert load().bound_modules((chain, (chain[0],))) == (chain[0], chain[6])


@pytest.mark.parametrize("case", ["flat", "list", "missing", "wrong_bridge_length",
                                 "wrong_reads_length", "foreign_sidecar", "not_module"])
def test_wrong_listener_snapshot_refuses_before_using_module_attributes(case):
    chain = tuple(types.ModuleType(f"fixture_{index}") for index in range(7))
    bound = (chain, (chain[0],))
    if case == "flat":
        bound = chain
    elif case == "list":
        bound = list(bound)
    elif case == "missing":
        bound = None
    elif case == "wrong_bridge_length":
        bound = (chain[:-1], (chain[0],))
    elif case == "wrong_reads_length":
        bound = (chain, ())
    elif case == "foreign_sidecar":
        bound = (chain, (types.ModuleType("foreign"),))
    else:
        bound = ((object(), *chain[1:]), (chain[0],))
    with pytest.raises(RuntimeError):
        load().bound_modules(bound)


@pytest.mark.parametrize("kind", ["phone", "bot_chat"])
@pytest.mark.parametrize(("lineage", "prompt"), [(2, 0), (98, 0), (98, 262144)])
def test_declared_shape_has_realistic_lineage_distinct_prompts_and_both_cache_paths(
    tmp_path, kind, lineage, prompt
):
    module, db = load(), DBModel()
    missing_home = tmp_path / "not_materialized"
    report = module.seed_native_shape(db, home=str(missing_home), kind=kind,
                                     lineage_count=lineage, prompt_chars=prompt)
    assert len(db.sessions) == lineage
    assert report["verified_prompt_count"] == (lineage if prompt else 0)
    assert report["history_rows"] == len(db.messages) == 258
    tools = [row for row in db.messages if row["role"] == "tool"]
    paths = [json.loads(row["content"])["image"] for row in tools]
    assert sum("/cache/images/" in path for path in paths) == 64
    assert sum("/cache/generated/images/" in path for path in paths) == 64
    assert not missing_home.exists()
    for count in (1, 16, 128):
        selected = module.select_tool_ids(report["tool_ids"], count)
        assert selected == tuple(row["id"] for row in reversed(tools[-count:]))
    if kind == "bot_chat":
        assert db.sessions[report["root"]]["hidden"] == 1
        assert db.sessions[report["tip"]]["title"] == "Bot Chat"
    else:
        assert all("title" not in row and "hidden" not in row for row in db.sessions.values())


@pytest.mark.parametrize("over", [
    {"kind": "other"}, {"kind": None}, {"lineage_count": True}, {"lineage_count": 99},
    {"prompt_chars": False}, {"prompt_chars": 1}, {"lineage_count": 2, "prompt_chars": 262144},
    {"home": "relative"}, {"home": "/a/../b"}, {"home": "/a/./b"},
    {"home": "/a//b"}, {"home": "/a/"}, {"home": "/a\0b"}, {"home": "/"},
])
def test_bad_shape_refuses_before_first_native_call(over):
    module, db = load(), DBModel()
    options = {"home": "/private/synthetic", "kind": "phone",
               "lineage_count": 2, "prompt_chars": 0}
    options.update(over)
    with pytest.raises(RuntimeError):
        module.seed_native_shape(db, **options)
    assert db.calls == [] and db.sessions == {} and db.messages == []


def test_an_existing_last_session_refuses_before_any_write():
    module, db = load(), DBModel()
    sid = "synthetic-c6b-phone-98-0-097"
    db.sessions[sid] = {"id": sid, "kept": True}
    with pytest.raises(RuntimeError):
        module.seed_native_shape(db, home="/private/synthetic", kind="phone",
                                 lineage_count=98, prompt_chars=0)
    assert db.sessions == {sid: {"id": sid, "kept": True}} and db.messages == []
    assert all(name == "get_session" for name, _ in db.calls)


def test_missing_public_prompt_field_cannot_produce_false_large_prompt_pass():
    module, db = load(), DBModel(drop_prompt=True)
    with pytest.raises(RuntimeError):
        module.seed_native_shape(db, home="/private/synthetic", kind="phone",
                                 lineage_count=98, prompt_chars=262144)
    assert db.messages == []  # Fails actual public prompt verification, before image rows.


@pytest.mark.parametrize("bad", [True, 0, 2, 129, "128", None])
def test_undeclared_selector_count_refuses(bad):
    with pytest.raises(RuntimeError):
        load().select_tool_ids(tuple(range(1, 129)), bad)


def preparation_report():
    return {"cells": [{"kind": kind, "lineage_count": lineage, "prompt_chars": prompt,
        "verified_prompt_count": lineage if prompt else 0, "history_rows": 258,
        "legacy_rows": 64, "generated_rows": 64, "selector_counts": [1, 16, 128],
        "accepted_counts": [1, 16, 128]}
        for kind in ("bot_chat", "phone") for lineage, prompt in ((2, 0), (98, 0), (98, 262144))],
        "timing_measured": False, "allocation_measured": False, "writer_cases_run": 0,
        "databases_closed": 6}


def test_preparation_schema_requires_all_six_shapes_and_no_measurement_claim():
    load().validate_preparation_report(preparation_report())


@pytest.mark.parametrize("case", ["missing_shape", "wrong_order", "missing_prompt",
                                 "wrong_acceptance", "boolean_count", "extra_field",
                                 "timing_claim", "allocation_claim", "writer_claim",
                                 "database_not_closed"])
def test_preparation_schema_refuses_incomplete_or_overclaimed_results(case):
    report = preparation_report()
    if case == "missing_shape":
        report["cells"].pop()
    elif case == "wrong_order":
        report["cells"].reverse()
    elif case == "missing_prompt":
        report["cells"][2]["verified_prompt_count"] = 0
    elif case == "wrong_acceptance":
        report["cells"][0]["accepted_counts"] = [1, 16, 127]
    elif case == "boolean_count":
        report["cells"][0]["selector_counts"] = [True, 16, 128]
    elif case == "extra_field":
        report["cells"][0]["raw_path"] = "/not_permitted"
    elif case == "timing_claim":
        report["timing_measured"] = True
    elif case == "allocation_claim":
        report["allocation_measured"] = True
    elif case == "writer_claim":
        report["writer_cases_run"] = 1
    else:
        report["databases_closed"] = 5
    with pytest.raises(RuntimeError):
        load().validate_preparation_report(report)


def test_driver_requires_explicit_seed_mode_and_rejects_combined_modes(tmp_path):
    from .test_local_media_native_serving_driver import driver, good

    report = good()
    native, hmp, executable = (report["native_source_hashes"], report["hmp_source_hashes"],
                               report["runtime_executable_sha256"])
    report["native_binding_preparation"] = preparation_report()
    driver.validate_report(report, native, hmp, executable, sample_binding_seed=True)
    with pytest.raises(RuntimeError):
        driver.validate_report(report, native, hmp, executable)
    with pytest.raises(RuntimeError):
        driver.run_fixture(tmp_path, tmp_path, "a" * 40,
                           sample_memory=True, sample_binding_seed=True)
    assert not tuple(tmp_path.iterdir())


def cell_fixture(tmp_path, *, release_result=True, close=True):
    from .test_local_media_native_serving_fixture import load as load_fixture

    tmp_path.chmod(0o700)
    original = tmp_path / "original-profile"
    stats = [(0, 0, 0)]
    native = types.SimpleNamespace(home_path=original, home=str(original),
        world=types.SimpleNamespace(runner=types.SimpleNamespace(homes={"alpha": original})))
    fx = types.SimpleNamespace(native=native,
                               service=types.SimpleNamespace(stats=lambda: stats[0]))
    acquired, released = [], []

    def acquire(path):
        db = types.SimpleNamespace(_conn=object())
        acquired.append((path, db))
        return db

    def release(db):
        released.append(db)
        if release_result and close:
            db._conn = None
        return release_result

    registry = types.SimpleNamespace(acquire=acquire, release=release)
    borrowed, selection, owners = {"acquired": 0, "released": 0}, [None], []
    module = load_fixture()

    def context(index=0):
        return module._binding_cell(tmp_path.resolve(), fx, registry, borrowed,
                                    threading.Lock(), selection, owners, index, "alpha")

    return types.SimpleNamespace(context=context, fx=fx, original=original, stats=stats,
        borrowed=borrowed, selection=selection, owners=owners, acquired=acquired, released=released)


def test_fresh_cell_closes_before_restoring_original_scope_and_cannot_be_reused(tmp_path):
    model = cell_fixture(tmp_path)
    with model.context() as db:
        path = tmp_path / "binding-cells/cell-0/state.db"
        assert model.selection[0] == (path, db)
        assert model.fx.native.home_path == path.parent
        assert model.fx.native.world.runner.homes["alpha"] == path.parent
        assert model.released == []
    assert db._conn is None and model.released == [db] and model.owners[0]["closed"] is True
    assert model.selection == [None] and model.fx.native.home_path == model.original
    assert model.fx.native.world.runner.homes["alpha"] == model.original
    with pytest.raises(FileExistsError), model.context():
        pytest.fail("existing cell must not acquire a new database")
    assert len(model.acquired) == 1


@pytest.mark.parametrize("case", ["borrower", "worker"])
def test_cell_refuses_before_allocation_when_original_work_remains(tmp_path, case):
    model = cell_fixture(tmp_path)
    if case == "borrower":
        model.borrowed["acquired"] = 1
    else:
        model.stats[0] = (1, 1, 1)
    with pytest.raises(RuntimeError), model.context():
        pytest.fail("must refuse before entering")
    assert model.acquired == [] and model.owners == []
    assert not (tmp_path / "binding-cells").exists()


@pytest.mark.parametrize("case", ["borrower", "worker", "release_false", "connection_open"])
def test_unsettled_cell_retains_its_owner_and_scope_instead_of_closing_or_restoring(tmp_path, case):
    model = cell_fixture(tmp_path, release_result=case != "release_false",
                         close=case != "connection_open")
    with pytest.raises(RuntimeError), model.context() as db:
        if case == "borrower":
            model.borrowed["acquired"] = 1
        elif case == "worker":
            model.stats[0] = (1, 1, 1)
    assert model.owners[0]["db"] is db and model.owners[0]["closed"] is False
    assert db._conn is not None and model.selection[0][1] is db
    assert model.fx.native.home_path != model.original
    assert len(model.released) == (0 if case in ("borrower", "worker") else 1)


def test_cell_closes_and_restores_after_user_work_raises_without_converting_failure(tmp_path):
    model = cell_fixture(tmp_path)
    with pytest.raises(ValueError, match="fixed synthetic failure"), model.context() as db:
        raise ValueError("fixed synthetic failure")
    assert db._conn is None and model.owners[0]["closed"] is True
    assert model.selection == [None] and model.fx.native.home_path == model.original


def test_cell_refuses_symlinked_base_before_native_acquisition(tmp_path):
    model = cell_fixture(tmp_path)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (tmp_path / "binding-cells").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(RuntimeError), model.context():
        pytest.fail("must refuse the substituted parent")
    assert not tuple(foreign.iterdir()) and model.acquired == []


def test_binding_command_supplies_only_owned_tmpdir_without_forwarding_ambient_values(
    tmp_path, monkeypatch
):
    from .test_local_media_native_serving_driver import driver

    monkeypatch.setenv("TMPDIR", "/foreign_not_forwarded")
    monkeypatch.setenv("HERMES_SCRATCH_DIR", "/foreign_marker_not_forwarded")
    args = (tmp_path, tmp_path / "python", tmp_path / "entry.py")
    normal = driver._native_command(*args)
    seeded = driver._native_command(*args, sample_binding_seed=True)
    assert not any(arg.startswith("TMPDIR=") for arg in normal)
    assert seeded == [*normal[:-5], "TMPDIR=" + str(tmp_path / "tmp"), *normal[-5:]]
    assert all("foreign" not in arg and not arg.startswith("HERMES_SCRATCH_DIR=")
               for arg in seeded)


@pytest.mark.parametrize("case", ["valid", "foreign", "marker", "absent", "public_mode"])
def test_binding_tmpdir_guard_before_native_bootstrap(tmp_path, case):
    from .test_local_media_native_serving_fixture import load as load_fixture

    temp = tmp_path / "tmp"
    if case != "absent":
        temp.mkdir(mode=0o700)
    env = {"TMPDIR": str(temp)}
    if case == "foreign":
        env["TMPDIR"] = "/foreign_not_read"
    elif case == "marker":
        env["HERMES_SCRATCH_DIR"] = str(temp)
    elif case == "public_mode":
        temp.chmod(0o755)
    if case == "valid":
        load_fixture()._binding_tmpdir(tmp_path, env)
    else:
        with pytest.raises((RuntimeError, FileNotFoundError)):
            load_fixture()._binding_tmpdir(tmp_path, env)

"""Preparation contract models only; no Hermes, database, file, HTTP or provider operations."""
import importlib.util
import json
import sys
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
        "timing_measured": False, "allocation_measured": False, "writer_cases_run": 0}


def test_preparation_schema_requires_all_six_shapes_and_no_measurement_claim():
    load().validate_preparation_report(preparation_report())


@pytest.mark.parametrize("case", ["missing_shape", "wrong_order", "missing_prompt",
                                 "wrong_acceptance", "boolean_count", "extra_field",
                                 "timing_claim", "allocation_claim", "writer_claim"])
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
    else:
        report["writer_cases_run"] = 1
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

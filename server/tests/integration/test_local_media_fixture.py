"""Ten optional real-native/HMP fixture groups, not default-CI native qualification.

No gateway startup, installer, real-home mutation or process command is run by this module.
A future reviewed root executor provides fresh per-phase actors/rows and capture joins.
Missing descriptor means explicit optional-lane skip; a supplied malformed descriptor fails.
Native phase preparation/fault mutations must be public API or owned leaf operations under
root custody, and are unadmitted until that executor and actual graph are reviewed.
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def media_run():
    name = os.environ.get("HMP_NATIVE_MEDIA_FIXTURE_RUN")
    if name is None:
        pytest.skip("optional real-native lane requires admitted HMP_NATIVE_MEDIA_FIXTURE_RUN")
    # Future admitted bootstrap adds only the exact source fixture directory. Native tools
    # remain native; no tools-package alias or sys.path override is made by this test module.
    lib = importlib.import_module("local_media_fixture")
    expected = Path(__file__).resolve().parents[3] / "tools/fixtures/local_media_fixture.py"
    if Path(lib.__file__) != expected:
        raise RuntimeError("fixture_helper_source")
    return SimpleNamespace(document=lib.read_descriptor(Path(name)), lib=lib)


def _case(run, case):
    record = run.document["scenarios"][case]
    run.lib.validate_case(case, record)
    return record


def _actor(record, run):
    return run.lib.Actor.parse(record["actor"])


def test_nm01_closed_flag(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM01")
    lib.require(r["privateFlag"] is False and r["descriptors"] == [], "nm01_flag")
    lib.assert_refusal(
        lib.get(_actor(r, media_run), lib.media_path(r["profile"], r["ref"])),
        503,
        "media_unavailable",
    )


def test_nm02_nonowner(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM02")
    lib.require(r["approvalOwner"] is False and r["descriptors"] == [], "nm02_owner")
    lib.assert_refusal(
        lib.get(_actor(r, media_run), lib.media_path(r["profile"], r["ref"])), 404, "not_found"
    )


def test_nm03_real_bot_descriptor_and_fetch(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM03")
    lib.require(r["sessionKind"] == "bot_chat" and r["toolName"] == "image_generate", "nm03_row")
    lib.require(r["readRoutes"] == ["SES2", "SES2a"], "nm03_routes")
    lib.require(
        r["readPaths"] == lib.expected_read_paths(r["profile"], r["sessionRef"], bot=True),
        "nm03_read_routes",
    )
    for path in r["readPaths"]:
        descriptors, _ = lib.read_descriptors(_actor(r, media_run), path, r["nativeToolRowId"])
        lib.require(len(descriptors) == 1, "nm03_descriptor_count")
        lib.get(
            _actor(r, media_run), lib.media_path(r["profile"], descriptors[0]["ref"])
        ).positive()


def test_nm04_real_phone_descriptor_and_fetch(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM04")
    lib.require(r["sessionKind"] == "own_default_phone", "nm04_session")
    lib.require(r["readRoutes"] == ["RO3", "RO6", "SES2", "SES2a"], "nm04_routes")
    lib.require(
        r["readPaths"] == lib.expected_read_paths(r["profile"], r["sessionRef"], bot=False),
        "nm04_read_routes",
    )
    for path in r["readPaths"]:
        descriptors, _ = lib.read_descriptors(_actor(r, media_run), path, r["nativeToolRowId"])
        lib.require(len(descriptors) == 1, "nm04_descriptor_count")
        lib.get(
            _actor(r, media_run), lib.media_path(r["profile"], descriptors[0]["ref"])
        ).positive()


def test_nm05_native_decoys_have_no_descriptor(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM05")
    lib.require(r["decoyRolesTools"] == [["assistant", None], ["tool", "other_tool"]], "nm05_rows")
    _, rows = lib.read_descriptors(_actor(r, media_run), r["readPath"], r["nativeToolRowId"])
    decoys = [row for row in rows if row.get("id") in r["decoyNativeRowIds"]]
    lib.require(len(decoys) == 2 and all(row.get("media") is None for row in decoys), "nm05_text")
    lib.require([row["text"] for row in decoys] == r["nativeDecoyTexts"], "nm05_text_preserved")


def test_nm06_cross_binding_all_preceding_gates(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM06")
    rows = lib.run_nm06(
        {name: lib.Actor.parse(actor) for name, actor in r["actors"].items()}, r["refs"]
    )
    assert [row["case"] for row in rows] == ["NM06-D", "NM06-P", "NM06-I", "NM06-H"]


def test_nm07_real_native_grant_revoke(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM07")
    lib.require(
        r["mutationAPI"] == "PairingStore.revoke" and r["beforeFetchStatus"] == 200, "nm07_mutation"
    )
    reply = lib.get(_actor(r, media_run), lib.media_path(r["profile"], r["ref"]))
    lib.assert_refusal(reply, 403, "forbidden")
    lib.require(json.loads(reply.body).get("authz") == "pending_operator", "nm07_gate")


def test_nm08_native_session_tip_moved(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM08")
    lib.require(
        r["mutationAPI"] == "SessionStore.get_or_create_session"
        and r["beforeFetchStatus"] == 200
        and r["originalTip"] != r["liveTipId"],
        "nm08_tip",
    )
    lib.assert_refusal(
        lib.get(_actor(r, media_run), lib.media_path(r["profile"], r["ref"])), 404, "not_found"
    )


def test_nm09_owned_unsafe_leaf_refused(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM09")
    lib.require(r["beforeFetchStatus"] == 200 and r["sourcePreserved"] is True, "nm09_before")
    lib.require(set(r["faults"]) == {"symlink", "hardlink", "raster", "digest"}, "nm09_faults")
    for fault in r["faults"].values():
        lib.assert_refusal(
            lib.get(
                lib.Actor.parse(fault["actor"]), lib.media_path(fault["profile"], fault["ref"])
            ),
            404,
            "not_found",
        )


def test_nm10_shared_dart_lane_required(media_run):
    lib = media_run.lib
    r = _case(media_run, "NM10")
    lib.require(
        r["consumer"] == "local_media_fixture_test.dart" and r["rawReadCaptureSHA256"] is not None,
        "nm10_consumer_input",
    )
    # No Dart/runtime success is inferred here. Its exact reporter/custody joins are a later phase.

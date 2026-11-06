"""Closed diagnostic schema and disposable own-task Darwin experiment."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "tools/compat/native_sender_audit_fixture.py"
_SPEC = importlib.util.spec_from_file_location("native_sender_fixture_test", _SCRIPT)
fixture = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fixture
_SPEC.loader.exec_module(fixture)


def good():
    value = dict.fromkeys(fixture._BOOLS, True)
    value.update(dict.fromkeys(fixture._FALSES, False))
    value.update(schema=2, stage="observed", messages_received=2, mach_error=0, spawn_error=0,
                 production_qualified=False)
    return value


def test_closed_success_is_diagnostic_only():
    value = fixture.validate_observation(json.dumps(good()).encode())
    assert value["production_qualified"] is False


@pytest.mark.parametrize("field", sorted(fixture._BOOLS))
def test_missing_or_false_plane_never_reports_success(field):
    value = good()
    value[field] = not value[field]
    with pytest.raises(fixture.NativeSenderFixtureError):
        fixture.validate_observation(json.dumps(value).encode())


@pytest.mark.parametrize("field,value", [("schema", True), ("messages_received", True),
    ("messages_received", 1), ("mach_error", False), ("mach_error", 1),
    ("spawn_error", False), ("spawn_error", 1),
    ("stage", "receive_queued_audit"), ("untrusted_extra", True)])
def test_wrong_primitive_count_stage_or_extra_field_refuses(field, value):
    row = good()
    row[field] = value
    with pytest.raises(fixture.NativeSenderFixtureError):
        fixture.validate_observation(json.dumps(row).encode())


@pytest.mark.parametrize("raw", [b"", b"x" * (fixture._LIMIT + 1), b"[]", None,
    bytearray(b"{}"), b'{"schema":1,"schema":1}', b"\xff"])
def test_bad_input_refuses_without_coercion(raw):
    with pytest.raises(fixture.NativeSenderFixtureError):
        fixture.validate_observation(raw)


@pytest.mark.parametrize("first,second", [
    ("/usr/lib/libbsm.0.dylib", "/usr/lib/libSystem.B.dylib"),
    ("/usr/lib/libSystem.B.dylib", "/usr/lib/libbsm.0.dylib"),
])
def test_only_selected_os_libraries_are_admitted(first, second):
    raw = ("/fixture/bin:\n\t" + first + " (compatibility version 1, current version 1)\n\t" +
           second + " (compatibility version 1, current version 1)\n").encode()
    assert fixture._libraries(raw, Path("/fixture/bin")) == [first, second]


@pytest.mark.parametrize("changed", ["@rpath/libbsm.0.dylib", "/usr/local/lib/libbsm.0.dylib",
    "/fixture/private.dylib", "/usr/lib/libSystem.B.dylib"])
def test_unexpected_or_duplicate_library_is_refused(changed):
    raw = ("/fixture/bin:\n\t" + changed + " (compatibility version 1, current version 1)\n\t" +
           "/usr/lib/libSystem.B.dylib (compatibility version 1, current version 1)\n").encode()
    with pytest.raises(fixture.NativeSenderFixtureError):
        fixture._libraries(raw, Path("/fixture/bin"))


@pytest.mark.parametrize("intermediate_error", [False, True])
def test_timeout_retains_same_helper_until_wait_then_still_refuses(
        tmp_path, monkeypatch, intermediate_error):
    actors, waits = [], []

    class Process:
        def __init__(self, *args, **kwargs):
            actors.append(self)
            self._child_created = True
            self.pid = 12345  # synthetic metadata; never passed to any signal API
            self.steps = 0

        def wait(self, timeout):
            waits.append((self, timeout))
            self.steps += 1
            if self.steps == 1:
                raise fixture.subprocess.TimeoutExpired(("synthetic",), timeout)
            if intermediate_error and self.steps == 2:
                raise OSError(5, "synthetic observation error")
            return 0

    before = len(fixture._RETAINED)
    monkeypatch.setattr(fixture, "_POPEN", Process)
    monkeypatch.setattr(fixture.time, "sleep", lambda _: None)
    receipt = {"commands": []}
    with pytest.raises(fixture.subprocess.TimeoutExpired):
        fixture._owned(["synthetic-never-executed"], tmp_path, "owned", receipt)
    assert len(actors) == 1 and all(actor is actors[0] for actor, _ in waits)
    assert [timeout for _, timeout in waits] == ([12, 30, 30] if intermediate_error else [12, 30])
    record = json.loads((tmp_path / "receipt.json").read_text())["commands"][0]
    assert record["settlement_only_used"] is True and record["wait_known"] is True
    assert record["settlement_wait_active"] is False and record["returncode"] == 0
    assert len(fixture._RETAINED) == before


@pytest.mark.skipif(sys.platform != "darwin" or os.geteuid() == 0,
                    reason="actual own-task Darwin Mach ABI/helper")
def test_actual_kernel_sender_after_own_child_exit(tmp_path):
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    # Artifacts remain private for independent readback; never auto-retry.
    receipt = fixture.run_fixture(root)
    assert receipt["source_binary_sdk_unchanged"] is True
    assert receipt["production_qualified"] is False
    assert receipt["observation"]["receipt_after_sender_exit"] is True
    assert receipt["observation"]["extended_body_refused"] is True
    assert receipt["observation"]["cleanup_known"] is True
    assert not fixture._RETAINED

"""Closed own-task lifecycle observations; actual Darwin run is separate."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[3] / "tools/compat/admission_owner_native_fixture.py"
_SPEC = importlib.util.spec_from_file_location("_hmp_owner_native_test", _PATH)
fixture = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fixture
_SPEC.loader.exec_module(fixture)


def good():
    row = dict.fromkeys(fixture._FIELDS, True)
    row.update(schema=1, production_qualified=False)
    return row


@pytest.mark.parametrize("field", sorted(fixture._FIELDS))
def test_any_failed_lifecycle_plane_refuses(field):
    row = good()
    row[field] = False
    with pytest.raises(fixture.commands.NativeSenderFixtureError):
        fixture.validate(json.dumps(row).encode())


def test_closed_success_remains_nonproduction():
    assert fixture.validate(json.dumps(good()).encode())["production_qualified"] is False


@pytest.mark.parametrize("field,value", [("schema", True), ("schema", 2),
    ("production_qualified", True), ("unexpected", True), ("disposed", 1)])
def test_unknown_or_coerced_schema_refuses(field, value):
    row = good()
    row[field] = value
    with pytest.raises(fixture.commands.NativeSenderFixtureError):
        fixture.validate(json.dumps(row).encode())


@pytest.mark.skipif(sys.platform != "darwin" or os.geteuid() == 0,
                    reason="Actual nonroot Darwin own-task lifecycle only")
def test_actual_native_lifecycle(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir(mode=0o700)
    receipt = fixture.run_fixture(directory)
    assert receipt["source_binary_sdk_unchanged"] is True
    assert not fixture.commands._RETAINED


def test_complete_driver_hash_readback_without_native_commands(tmp_path, monkeypatch):
    """Catches post-run Path/string errors without executing a compiler/helper."""
    compiler = tmp_path / "compiler"
    compiler.write_bytes(b"model compiler, never executed")
    sdk = tmp_path / "sdk"
    for name in ("mach/mach.h", "mach/mach_port.h", "mach/port.h", "pthread.h", "bsm/libbsm.h"):
        path = sdk / "usr/include" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"model header")
    directory = tmp_path / "owned-model"
    directory.mkdir(mode=0o700)
    roles = []

    def model_command(argv, directory, role, receipt):
        roles.append(role)
        if role == "compiler":
            return str(compiler).encode()
        if role == "sdk":
            return str(sdk).encode()
        if role == "build":
            Path(argv[-1]).write_bytes(b"model binary, never executed")
            return b""
        if role == "libraries":
            return (str(directory / "native-owner") + ":\n"
                    "\t/usr/lib/libSystem.B.dylib (compatibility version 1, current version 1)\n"
                    "\t/usr/lib/libbsm.0.dylib (compatibility version 1, current version 1)\n"
                    ).encode()
        assert role == "native_observation"
        return json.dumps(good()).encode()

    monkeypatch.setattr(fixture.sys, "platform", "darwin")
    monkeypatch.setattr(fixture.os, "geteuid", lambda: directory.stat().st_uid)
    monkeypatch.setattr(fixture.commands, "_owned", model_command)
    receipt = fixture.run_fixture(directory)
    assert receipt["source_binary_sdk_unchanged"] is True
    assert roles == ["compiler", "sdk", "build", "libraries", "native_observation"]

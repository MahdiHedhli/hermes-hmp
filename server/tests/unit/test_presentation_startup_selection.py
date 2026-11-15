"""Private synthetic config files; no native installer approval or credentials."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from .test_presentation_gateway_activation import MODULE, SCRIPT

ARTIFACT_MODULE = MODULE.with_name("presentation_startup_artifacts.py")
SELECTION_MODULE = MODULE.with_name("presentation_startup_selection.py")
PREFIX = SCRIPT[:SCRIPT.rfind("print(json.dumps")]
SUFFIX = r'''
import hashlib, os
from pathlib import Path
mutation = sys.argv[3]
fixture = Path(sys.argv[6])
package = ModuleType("synthetic_startup")
package.__path__ = []
sys.modules[package.__name__] = package
sys.modules[package.__name__ + ".presentation_gateway_activation"] = m
for name, path in (("presentation_startup_artifacts", sys.argv[4]),
                   ("presentation_startup_selection", sys.argv[5])):
    childspec = importlib.util.spec_from_file_location(package.__name__ + "." + name, path)
    child = importlib.util.module_from_spec(childspec)
    sys.modules[childspec.name] = child
    childspec.loader.exec_module(child)
    if name == "presentation_startup_artifacts": a = child
    else: c = child
policy = "darwin-system-loader-trust" if sys.platform == "darwin" else "linux-system-loader-trust"
document = dict(schema=1, kind="HMP_GATEWAY_STARTUP_SELECTION", iid="a" * 52, protocol=2,
                algorithm="Ed25519", credential_generation="1" * 64,
                gateway_public="2" * 64, broker_public="3" * 64,
                gateway_inventory_sha256="4" * 64, broker_inventory_sha256="5" * 64,
                loader_policy=policy)
if mutation == "unknown": document["private_seed"] = "SYNTHETIC_FORBIDDEN_FIELD"
if mutation == "schema_bool": document["schema"] = True
if mutation == "protocol_bool": document["protocol"] = True
if mutation == "protocol": document["protocol"] = 1
if mutation == "algorithm": document["algorithm"] = "HMAC"
if mutation == "iid": document["iid"] = "wrong"
if mutation == "iid_noncanonical": document["iid"] = "a" * 51 + "b"
if mutation == "generation": document["credential_generation"] = "X" * 64
if mutation == "reflection": document["gateway_public"] = document["broker_public"]
if mutation == "policy": document["loader_policy"] = "arbitrary-loader"
raw = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
if mutation == "duplicate": raw = b'{"schema":1,' + raw[1:]
if mutation == "noncanonical": raw += b"\n"
if mutation == "oversize": raw = b"x" * 65537
path = fixture / "gateway-startup.json"
path.write_bytes(raw)
path.chmod(0o600)
expected = a.ExpectedArtifact(str(path), len(raw), hashlib.sha256(raw).hexdigest())
if mutation == "digest": expected = expected._replace(sha256="0" * 64)
if mutation == "wrong_name":
    target = fixture / "wrong-name.json"
    path.rename(target)
    expected = expected._replace(path=str(target))
if mutation == "leaf_mode": path.chmod(0o644)
if mutation == "directory_mode": fixture.chmod(0o755)
if mutation == "symlink":
    target = fixture / "original.json"
    path.rename(target)
    path.symlink_to(target)
if mutation == "hardlink": os.link(path, fixture / "copy.json")
actual_read, actual_close = a.os.read, a.os.close
calls, captures = [], []
if mutation == "late_load": sys.modules["gateway.run"] = ModuleType("gateway.run")
if mutation in ("read_retire", "late_read"):
    def retire_after_read(fd, count):
        result = actual_read(fd, count)
        if mutation == "read_retire": owner.retire()
        else: sys.modules["gateway.run"] = ModuleType("gateway.run")
        return result
    a.os.read = retire_after_read
if mutation == "close_unknown":
    def lost_close(fd):
        calls.append(fd)
        actual_close(fd)
        if len(calls) == 1: raise OSError("synthetic lost close acknowledgement")
    a.os.close = lost_close
foreign_fact = object()
if mutation in ("buffer_swap", "foreign_hash", "pre_fact_replacement", "hash_count_swap"):
    actual_hash = c.hashlib.sha256
    class ForeignDigest:
        def __eq__(self, other):
            calls.append("foreign equality")
            raise AssertionError("foreign digest comparison")
    class DigestResult:
        def hexdigest(self): return ForeignDigest()
    def altered_hash(data=b""):
        if data == raw:
            if mutation == "foreign_hash": return DigestResult()
            if mutation == "hash_count_swap":
                active = owner._selection_owner
                active._count_cell = (active, active._origin, active._bytes_read)
                return actual_hash(data)
            if mutation == "pre_fact_replacement":
                owner._selection_fact_cell = foreign_fact
                return actual_hash(data)
            active = owner._selection_owner
            captures.append(active._buffer)
            replacement = bytearray(b"SYNTHETIC_FOREIGN_DO_NOT_WIPE")
            active._buffer = replacement
            active._root_cell = owner._selection_cell = (owner, active, active._origin,
                                                        (active, replacement))
        return actual_hash(data)
    c.hashlib.sha256 = altered_hash
if mutation in ("final_retire", "final_replacement"):
    getpid = c.os.getpid
    replacement = object()
    def final_change():
        result = getpid()
        if owner._selection_fact_cell is not None:
            if mutation == "final_retire": owner.retire()
            else: owner._selection_fact_cell = replacement
        return result
    c.os.getpid = final_change
success = mutation in ("normal", "separate_artifacts") or mutation.startswith("history_")
try:
    loaded = c.StartupSelectionOwner.load(owner, expected)
except c.SelectionLoadError as error:
    assert not success, (mutation, str(error))
    loaded = error.failed_owner
    assert str(error) == "BI1_STARTUP_SELECTION_REFUSED"
    assert loaded is owner._selection_owner and loaded._failed and not loaded._ready
    assert loaded._selection is None
    if mutation == "final_replacement": assert owner._selection_fact_cell is replacement
    elif mutation == "pre_fact_replacement": assert owner._selection_fact_cell is foreign_fact
    else: assert owner._selection_fact_cell is None
else:
    assert success, mutation
    selection = loaded._selection
    assert type(selection) is c.GatewayStartupSelection
    assert selection.schema == document["schema"]
    assert selection.iid == document["iid"] and selection.directory == str(fixture)
    assert len(selection.gateway_public) == len(selection.broker_public) == 32
    assert owner._selection_fact_cell is loaded._selection_cell
    assert loaded._bytes_read == len(raw)
    assert str(fixture) not in repr(loaded) + repr(selection)
    if mutation == "separate_artifacts":
        code = fixture / "synthetic.py"
        code.write_bytes(b"SYNTHETIC_CODE")
        code.chmod(0o600)
        row = a.ExpectedArtifact(str(code), len(b"SYNTHETIC_CODE"),
                                 hashlib.sha256(b"SYNTHETIC_CODE").hexdigest())
        files = a.StartupArtifactOwner.observe(owner, (row,))
        assert files._ready and owner._artifact_owner is files
        assert owner._selection_owner is loaded
if mutation.startswith("history_"):
    original = loaded.retained_data()
    assert original is loaded._selection
    if mutation == "history_late": sys.modules["gateway.run"] = ModuleType("gateway.run")
    if mutation == "history_namespace":
        for name in tuple(sys.modules):
            if name.startswith(package.__name__ + "."): sys.modules[name] = ModuleType(name)
    if mutation == "history_paths": sys.path[1] = "/synthetic/later-generation/site-packages"
    if mutation == "history_thread":
        outcomes = []
        def foreign_query():
            try: loaded.retained_data()
            except c.SelectionLoadError: outcomes.append(True)
        worker = threading.Thread(target=foreign_query)
        worker.start()
        worker.join()
        assert outcomes == [True]
    if mutation in ("history_fact_drift", "history_context_drift", "history_count_drift"):
        foreign = object()
        if mutation == "history_fact_drift": owner._selection_fact_cell = foreign
        elif mutation == "history_count_drift":
            loaded._count_cell = (loaded, loaded._origin, loaded._bytes_read)
        else:
            getpid = c.os.getpid
            def change_during_context():
                result = getpid()
                owner._selection_fact_cell = foreign
                return result
            c.os.getpid = change_during_context
        try: loaded.retained_data()
        except c.SelectionLoadError: pass
        else: raise AssertionError("changed retained selection accepted")
        if mutation != "history_count_drift": assert owner._selection_fact_cell is foreign
    else:
        assert loaded.retained_data() is original
        assert loaded._ready and not loaded._failed and not owner._uncertain
assert all(row.closed or row.unknown for row in loaded._origin.records)
if mutation == "buffer_swap":
    assert captures and not captures[0]
    assert loaded._buffer == b"SYNTHETIC_FOREIGN_DO_NOT_WIPE"
else: assert not loaded._root_cell[3][1]
assert len(calls) == len(set(calls)) and "foreign equality" not in calls
try: c.StartupSelectionOwner.load(owner, expected)
except Exception: pass
else: raise AssertionError("selection recapture accepted")
for blocked_method in (c.StartupSelectionOwner.load,
                       c.StartupSelectionOwner.load_recipe_selection):
    try: blocked_method(owner, expected)
    except c.SelectionLoadError: pass
    else: raise AssertionError("alternate-version recapture accepted")
class WrongOwner(c.StartupSelectionOwner):
    @classmethod
    def _load(cls, *args):
        calls.append("subclass callback")
        raise AssertionError("subclass dispatch")
for method in (WrongOwner.load, WrongOwner.load_recipe_selection):
    try: method(owner, expected)
    except c.SelectionLoadError: pass
    else: raise AssertionError("subclass loader accepted")
assert "subclass callback" not in calls
print(json.dumps({"mutation": mutation, "passed": True, "runtime_admitted": False}))
'''


@pytest.mark.parametrize("mutation", [
    "normal", "separate_artifacts", "unknown", "schema_bool", "protocol_bool", "protocol",
    "algorithm", "iid", "iid_noncanonical", "generation", "reflection", "policy", "duplicate",
    "noncanonical",
    "oversize", "digest", "wrong_name", "leaf_mode", "directory_mode", "symlink", "hardlink",
    "read_retire", "close_unknown", "buffer_swap", "foreign_hash", "final_retire",
    "final_replacement", "pre_fact_replacement", "hash_count_swap", "late_load", "late_read",
    "history_late", "history_namespace", "history_paths", "history_thread",
    "history_fact_drift", "history_context_drift", "history_count_drift",
])
@pytest.mark.parametrize("version", [1, 2])
def test_private_selected_startup_configuration(tmp_path, mutation, version):
    if os.name != "posix" or sys.platform not in ("darwin", "linux"):
        pytest.skip("current supported POSIX startup fixture")
    suffix = SUFFIX
    if version == 2:
        suffix = suffix.replace("schema=1", "schema=2", 1).replace(
            "c.StartupSelectionOwner.load(owner, expected)",
            "c.StartupSelectionOwner.load_recipe_selection(owner, expected)")
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", PREFIX + suffix, str(MODULE), "normal", mutation,
         str(ARTIFACT_MODULE), str(SELECTION_MODULE), str(tmp_path.resolve())],
        cwd=tmp_path, env={"LANG": "C", "LC_ALL": "C"}, capture_output=True, text=True,
        timeout=10, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "mutation": mutation, "passed": True, "runtime_admitted": False,
    }


@pytest.mark.parametrize("document_version,loader_version", [(1, 2), (2, 1), (3, 1), (3, 2)])
def test_selection_version_requires_explicit_matching_loader(
    tmp_path, document_version, loader_version,
):
    suffix = SUFFIX.replace("schema=1", f"schema={document_version}", 1)
    suffix = suffix.replace("success = mutation in", "success = False and mutation in")
    if loader_version == 2:
        suffix = suffix.replace("c.StartupSelectionOwner.load(owner, expected)",
                                "c.StartupSelectionOwner.load_recipe_selection(owner, expected)")
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", PREFIX + suffix, str(MODULE), "normal", "normal",
         str(ARTIFACT_MODULE), str(SELECTION_MODULE), str(tmp_path.resolve())],
        env={"LANG": "C", "LC_ALL": "C"}, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["runtime_admitted"] is False

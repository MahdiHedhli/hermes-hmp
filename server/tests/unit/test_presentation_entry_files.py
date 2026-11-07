"""Disposable entry/wrapper file snapshots; no executed-byte/runtime admission."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2]
SCRIPT = r'''
import hashlib, json, sys
from pathlib import Path
from types import ModuleType
base, mutation = Path(sys.argv[1]), sys.argv[2]
plugin_root, entry_root = base / "hmp_plugin", base / "hmp_startup"
namespace = ModuleType("hmp_plugin")
namespace.__path__ = [str(plugin_root)]
sys.modules["hmp_plugin"] = namespace
sys.path.insert(0, str(base))
from hmp_startup.gateway_entry import GatewayEntryOwner
from hmp_startup.entry_files import EntryFileSnapshotOwner, EntryFilesError
from hmp_plugin import presentation_startup_artifacts as a
from hmp_plugin.presentation_startup_selection import StartupSelectionOwner
from hmp_plugin.presentation_gateway_recipe import GatewayRecipeOwner
from hmp_plugin.presentation_gateway_package import GatewayPackageOwner
sys.path.insert(0, str(base / "native"))
entry = GatewayEntryOwner.start()
namespace.__path__ = []
def canonical(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode("ascii")
def table(root):
    rows = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir(): rows.append(dict(path=relative, kind="directory", size=0, sha256=None))
        else:
            body = path.read_bytes()
            rows.append(dict(path=relative, kind="file", size=len(body),
                             sha256=hashlib.sha256(body).hexdigest()))
    return rows
wrapper_path = Path(__file__)
wrapper_body = wrapper_path.read_bytes()
wrapper = dict(path=str(wrapper_path), size=len(wrapper_body),
               sha256=hashlib.sha256(wrapper_body).hexdigest())
if mutation == "wrapper_conflict": wrapper["size"] += 1
plugin_document = dict(schema=1, kind="HMP_GATEWAY_PACKAGE", generation="1" * 64,
                       package=str(plugin_root), entries=table(plugin_root))
entry_document = dict(schema=1, kind="HMP_GATEWAY_ENTRY", generation="1" * 64,
                      package=str(entry_root), entries=table(entry_root), wrapper=wrapper)
if mutation == "unknown": entry_document["command"] = "SYNTHETIC_FORBIDDEN"
if mutation == "root": entry_document["package"] = str(base)
if mutation == "wrapper_path": entry_document["wrapper"]["path"] = str(base / "other.py")
children = [canonical(plugin_document), canonical(entry_document)]
for kind in ("HMP_GATEWAY_DEPENDENCIES", "HMP_GATEWAY_INTERPRETER"):
    children.append(canonical(dict(schema=1, kind=kind, generation="1" * 64)))
refs = {name:dict(size=len(body), sha256=hashlib.sha256(body).hexdigest())
        for name,body in zip(("plugin","entry","dependencies","interpreter"),children)}
recipe_raw = canonical(dict(schema=1, kind="HMP_GATEWAY_RECIPE", generation="1" * 64, **refs))
private = base / "private"
for name,body in zip(("gateway-recipe.json","gateway-package.json","gateway-entry.json",
                       "gateway-dependencies.json","gateway-interpreter.json"),
                      (recipe_raw,*children)):
    path=private/name; path.write_bytes(body); path.chmod(0o600)
selection = canonical(dict(schema=2,kind="HMP_GATEWAY_STARTUP_SELECTION",iid="a"*52,
    protocol=2,algorithm="Ed25519",credential_generation="1"*64,gateway_public="2"*64,
    broker_public="3"*64,gateway_inventory_sha256=hashlib.sha256(recipe_raw).hexdigest(),
    broker_inventory_sha256="5"*64,loader_policy=("darwin-system-loader-trust" if
    sys.platform=="darwin" else "linux-system-loader-trust")))
path=private/"gateway-startup.json"; path.write_bytes(selection); path.chmod(0o600)
configuration = StartupSelectionOwner.load_recipe_selection(entry._activation,
    a.ExpectedArtifact(str(path),len(selection),hashlib.sha256(selection).hexdigest()))
recipe = GatewayRecipeOwner.load(configuration,len(recipe_raw))
plugin = GatewayPackageOwner.verify_recipe(recipe)
if mutation == "extra": (entry_root/"unexpected.py").write_bytes(b"SYNTHETIC_EXTRA")
if mutation == "changed": (entry_root/"unused.py").write_bytes(b"CHANGED")
if mutation == "missing": (entry_root/"unused.py").unlink()
if mutation == "symlink":
    target=entry_root/"unused.py"; target.unlink(); target.symlink_to(base/"outside.py")
if mutation == "wrapper_changed": wrapper_path.write_bytes(b"CHANGED")
if mutation == "retired": entry._activation.retire()
if mutation in ("after_hash_replace", "wrapper_after_hash"):
    complete = a.StartupArtifactOwner.complete.__func__
    def replace_after_hash(cls, owner):
        result = complete(cls, owner)
        target = entry_root/"unused.py" if mutation == "after_hash_replace" else wrapper_path
        replacement = base/"replacement.py"
        replacement.write_bytes(target.read_bytes()); replacement.chmod(0o600)
        replacement.replace(target)
        return result
    a.StartupArtifactOwner.complete = classmethod(replace_after_hash)
foreign_calls = []
if mutation == "foreign_final_scan":
    getpid = a.os.getpid
    class ForeignBool:
        def __bool__(self):
            foreign_calls.append(True)
            return True
    def corrupt_final_scan():
        value = getpid()
        active = entry._activation._entry_files_owner
        if active is not None and active._inputs is not None:
            scans = active._inputs.scans
            io = active._inputs.io_slot[0]
            if io is not None and io._ready and len(scans) >= 2:
                if all(row.closed is True for row in scans): scans[0].closed = ForeignBool()
        return value
    a.os.getpid = corrupt_final_scan
if mutation == "foreign_module_name":
    actual_origins = EntryFileSnapshotOwner._origins
    class Foreign:
        def __hash__(self): return 0
        def startswith(self, *args):
            foreign_calls.append(True)
            raise AssertionError("foreign module-name method called")
    foreign = Foreign()
    def inject_module_key(owner):
        sys.modules[foreign] = ModuleType("synthetic_foreign")
        return actual_origins(owner)
    EntryFileSnapshotOwner._origins = inject_module_key
if mutation in ("scan_close_unknown", "scan_next_unknown"):
    actual_scandir = a.os.scandir
    scan_calls = []
    class Scan:
        def __init__(self, iterator): self.iterator = iterator
        def __next__(self):
            item = next(self.iterator)
            if mutation == "scan_next_unknown": raise OSError("synthetic lost entry result")
            return item
        def close(self):
            self.iterator.close()
            scan_calls.append(True)
            if mutation == "scan_close_unknown": raise OSError("synthetic lost close result")
    a.os.scandir = lambda fd: Scan(actual_scandir(fd))
retained = None
try:
    if mutation.startswith("retained_") or mutation.startswith("completion_"):
        retained = EntryFileSnapshotOwner.retain(entry,recipe,plugin)
        assert retained._ready is False and retained._inputs.io_slot == [None]
        assert entry._activation._artifact_owner is None
        assert entry._activation._entry_files_attempt_cell is None
        if mutation == "retained_changed":
            (entry_root/"unused.py").write_bytes(b"CHANGED_AFTER_RETENTION")
        if mutation == "completion_context_failure":
            actual_pid = a.os.getpid
            def fail_completion_context():
                if retained._completing: raise OSError("synthetic context failure")
                return actual_pid()
            a.os.getpid = fail_completion_context
        if mutation == "completion_attempt_swap":
            actual_pid = a.os.getpid
            def swap_completion_attempt():
                value = actual_pid()
                if retained._completing:
                    copied = tuple(list(retained._inputs.completion_attempt))
                    retained._attempt_cell = entry._activation._entry_files_attempt_cell = copied
                return value
            a.os.getpid = swap_completion_attempt
        result = EntryFileSnapshotOwner.complete(retained)
    else:
        result = EntryFileSnapshotOwner.verify(entry,recipe,plugin)
except EntryFilesError as error:
    assert mutation not in ("normal","internal_wrapper","retained_normal"), mutation
    result=error.failed_owner
    if result is not None: assert result._failed and not result._ready and result._fact_cell is None
else:
    assert mutation in ("normal","internal_wrapper","retained_normal"), mutation
    assert result._ready and result._fact_cell is entry._activation._entry_files_fact_cell
    io=result._fact_cell[2]
    assert io._origin.parent.count_cell is plugin._fact[7]
    assert io._bytes_read == plugin._bytes_read + sum(row.size for row in io._origin.expected)
    assert all(row.closed for row in io._origin.records)
    assert all(row.closed for row in result._inputs.scans)
if retained is not None:
    actual_pid = locals().get("actual_pid")
    if actual_pid is not None: a.os.getpid = actual_pid
    io = retained._inputs.io_slot[0]
    if mutation in ("completion_context_failure", "completion_attempt_swap"):
        assert io is None and entry._activation._artifact_owner is None
        assert retained._inputs.scans == []
    before_retry = None if io is None else (io._bytes_read, len(io._origin.records))
    try: EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError: pass
    else: raise AssertionError("completion replay accepted")
    if io is not None: assert before_retry == (io._bytes_read, len(io._origin.records))
    if mutation == "retained_normal": assert retained._ready and not retained._failed
    else: assert retained._failed and retained._completing
assert not foreign_calls
if mutation in ("normal", "internal_wrapper"):
    sys.path[1] = "/synthetic/later-generation/site-packages"
    sys.modules["gateway.run"] = ModuleType("gateway.run")
try: EntryFileSnapshotOwner.verify(entry,recipe,plugin)
except EntryFilesError: pass
else: raise AssertionError("entry snapshot reminted")
if mutation in ("normal", "internal_wrapper"): assert not entry._activation._uncertain
print(json.dumps({"mutation":mutation,"runtime_admitted":False}))
'''


@pytest.mark.parametrize("mutation", [
    "normal", "internal_wrapper", "unknown", "root", "wrapper_path", "wrapper_conflict",
    "extra", "changed", "missing", "symlink", "wrapper_changed", "retired",
    "after_hash_replace", "wrapper_after_hash", "foreign_module_name",
    "scan_close_unknown", "scan_next_unknown", "foreign_final_scan",
    "retained_normal", "retained_changed", "completion_context_failure", "completion_attempt_swap",
])
def test_actual_entry_and_wrapper_files(tmp_path, mutation):
    if os.name != "posix" or sys.platform not in ("darwin", "linux"):
        pytest.skip("supported POSIX entry snapshot")
    for name in ("hmp_plugin", "hmp_startup", "private", "native", "environment/site-packages"):
        (tmp_path / name).mkdir(parents=True, mode=0o700)
    for name in ("presentation_gateway_activation.py", "presentation_startup_artifacts.py",
                 "presentation_startup_selection.py", "presentation_gateway_recipe.py",
                 "presentation_gateway_package.py"):
        shutil.copyfile(SERVER / "hmp_plugin" / name, tmp_path / "hmp_plugin" / name)
    for name in ("__init__.py", "gateway_entry.py", "entry_files.py"):
        shutil.copyfile(SERVER / "hmp_startup" / name, tmp_path / "hmp_startup" / name)
    (tmp_path / "hmp_startup/unused.py").write_text("# SYNTHETIC UNUSED\n")
    (tmp_path / "outside.py").write_text("# SYNTHETIC OUTSIDE\n")
    native = tmp_path / "native"
    (native / "pm").mkdir(mode=0o700)
    (native / "pm/__init__.py").write_text("")
    (native / "pm/environments.py").write_text("def activate_dependencies():\n    pass\n")
    (native / "hermes_bootstrap.py").write_text(
        "import sys\nimport pm.environments\n"
        "sys.path.insert(1, sys.argv[1] + '/environment/site-packages')\n")
    wrapper = (tmp_path / "hmp_startup/wrapper.py" if mutation == "internal_wrapper"
               else tmp_path / "wrapper.py")
    wrapper.write_text(SCRIPT)
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(wrapper), str(tmp_path.resolve()), mutation],
        env={"LANG": "C", "LC_ALL": "C"}, capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"mutation": mutation, "runtime_admitted": False}

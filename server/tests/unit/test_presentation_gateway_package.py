"""Complete private synthetic HMP trees; not installed runtime/entry qualification."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from .test_presentation_gateway_activation import SCRIPT
from .test_presentation_startup_selection import ARTIFACT_MODULE, PREFIX, SELECTION_MODULE, SUFFIX

PACKAGE_MODULE = ARTIFACT_MODULE.with_name("presentation_gateway_package.py")
CONFIG_PREFIX = SUFFIX[:SUFFIX.rfind("print(json.dumps")]
INSERT = r'''
root = Path(sys.argv[7])
rows = []
for path in sorted(root.rglob("*")):
    relative = path.relative_to(root).as_posix()
    if path.is_dir():
        rows.append(dict(path=relative, kind="directory", size=0, sha256=None))
    else:
        data = path.read_bytes()
        rows.append(dict(path=relative, kind="file", size=len(data),
                         sha256=hashlib.sha256(data).hexdigest()))
package_mutation = sys.argv[8]
if package_mutation == "duplicate": rows.insert(1, rows[0].copy())
if package_mutation == "private_name":
    rows.append(dict(path=".env", kind="file", size=0, sha256=hashlib.sha256(b"").hexdigest()))
    rows.sort(key=lambda row: row["path"])
manifest = dict(schema=1, kind="HMP_GATEWAY_PACKAGE", generation="1" * 64,
                package=str(root), entries=rows)
if package_mutation == "generation": manifest["generation"] = "9" * 64
if package_mutation == "unknown": manifest["native_checkout_sha256"] = "0" * 64
if package_mutation == "wrong_root": manifest["package"] = str(root.parent)
manifest_raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True).encode("ascii")
'''
CONFIG_PREFIX = CONFIG_PREFIX.replace("document = dict(", INSERT + "\ndocument = dict(", 1)
CONFIG_PREFIX = CONFIG_PREFIX.replace(
    'gateway_inventory_sha256="4" * 64',
    'gateway_inventory_sha256=hashlib.sha256(manifest_raw).hexdigest()',
)
CONFIG_PREFIX = CONFIG_PREFIX.replace("document = dict(schema=1, kind=",
                                      "document = dict(schema=(2 if package_mutation == "
                                      "'selection_v2' else 1), kind=", 1)
CONFIG_PREFIX = CONFIG_PREFIX.replace(
    "c.StartupSelectionOwner.load(owner, expected)",
    "(c.StartupSelectionOwner.load_recipe_selection if package_mutation == 'selection_v2' "
    "else c.StartupSelectionOwner.load)(owner, expected)",
)
PACKAGE_SUFFIX = r'''
mutation = package_mutation
package.__path__ = [str(root)]
package_spec = importlib.util.spec_from_file_location(
    package.__name__ + ".presentation_gateway_package",
    str(root / "presentation_gateway_package.py"))
p = importlib.util.module_from_spec(package_spec)
sys.modules[package_spec.name] = p
package_spec.loader.exec_module(p)
package.__path__ = []  # fixed empty synthetic namespace after loading fixture modules
unused = root / "unused.py"
if mutation == "changed": unused.write_bytes(b"CHANGED_SYNTHETIC_CODE")
if mutation == "missing": unused.unlink()
if mutation == "extra": (root / "unexpected.py").write_bytes(b"UNLISTED_SYNTHETIC_CODE")
if mutation == "symlink":
    outside = root.parent / "outside.py"
    outside.write_bytes(b"SYNTHETIC_MUST_NOT_READ")
    unused.unlink()
    unused.symlink_to(outside)
if mutation == "directory_symlink":
    nested = root / "nested"
    outside = root.parent / "outside-directory"
    nested.rename(outside)
    nested.symlink_to(outside, target_is_directory=True)
if mutation == "private_file": (root / ".env").write_bytes(b"SYNTHETIC_MUST_NOT_READ")
if mutation == "directory_mode": (root / "nested").chmod(0o777)
if mutation == "digest": manifest_raw += b" "
if mutation == "module_origin": a.__file__ = str(root.parent / "outside.py")
if mutation == "retired_scan":
    actual_scan = p.os.scandir
    def retire_after_scan(fd):
        iterator = actual_scan(fd)
        owner.retire()
        return iterator
    p.os.scandir = retire_after_scan
if mutation == "after_hash_replace":
    actual_file = a.StartupArtifactOwner._file
    replaced = []
    def replace_after_hash(current, expected, native_registration=None):
        result = actual_file(current, expected, native_registration)
        if expected.path.endswith("/unused.py"):
            data = unused.read_bytes()
            replacement = root / "temporary-replacement.py"
            replacement.write_bytes(data)
            replacement.chmod(0o600)
            os.replace(replacement, unused)
            replaced.append(True)
        return result
    a.StartupArtifactOwner._file = replace_after_hash
foreign_fact = object()
if mutation == "pre_fact_replacement":
    actual_file = a.StartupArtifactOwner._file
    def set_foreign_fact(current, expected, native_registration=None):
        result = actual_file(current, expected, native_registration)
        owner._package_fact_cell = foreign_fact
        return result
    a.StartupArtifactOwner._file = set_foreign_fact
foreign_calls = []
if mutation in ("spec_swap", "namespace_swap"):
    origin_read = p.GatewayPackageOwner._origins
    origin_calls = []
    class ForeignLoader:
        def __eq__(self, other):
            foreign_calls.append("spec equality")
            raise AssertionError("foreign loader equality")
    def change_origins(current):
        result = origin_read(current)
        origin_calls.append(True)
        if len(origin_calls) == 1:
            if mutation == "namespace_swap": package.__path__ = []
            else:
                a.__spec__ = ModuleSpec(a.__name__, loader=ForeignLoader(), origin=a.__file__)
        return result
    p.GatewayPackageOwner._origins = change_origins
success = mutation == "normal" or mutation.startswith("history_")
try:
    checked = p.GatewayPackageOwner.verify(loaded, manifest_raw)
except p.PackageInventoryError as error:
    assert not success, str(error)
    checked = error.failed_owner
    assert str(error) == "BI1_GATEWAY_PACKAGE_REFUSED"
    if mutation == "selection_v2":
        assert checked is None and owner._package_owner is None
        assert owner._package_cell is None and owner._package_fact_cell is None
        assert loaded._ready and loaded._selection.schema == 2
    else:
        assert checked is owner._package_owner and checked._failed and not checked._ready
        assert checked._fact is None
else:
    assert success, mutation
    assert checked._ready and checked._fact[0] is checked
    assert checked._bytes_read == sum(row["size"] for row in rows)
if mutation.startswith("history_"):
    original = checked.retained_data()
    assert original.selection is loaded.retained_data()
    original_environment = original.environment
    if mutation == "history_late": sys.modules["gateway.run"] = ModuleType("gateway.run")
    if mutation == "history_namespace":
        for name in tuple(sys.modules):
            if name.startswith(package.__name__ + "."): sys.modules[name] = ModuleType(name)
    if mutation == "history_paths": sys.path[1] = "/synthetic/later-generation/site-packages"
    if mutation == "history_thread":
        outcomes = []
        def foreign_query():
            try: checked.retained_data()
            except p.PackageInventoryError: outcomes.append(True)
        worker = threading.Thread(target=foreign_query)
        worker.start()
        worker.join()
        assert outcomes == [True]
    if mutation in ("history_fact_drift", "history_context_drift"):
        foreign = object()
        if mutation == "history_fact_drift": owner._package_fact_cell = foreign
        else:
            getpid = p.os.getpid
            def replace_during_context():
                result = getpid()
                owner._package_fact_cell = foreign
                return result
            p.os.getpid = replace_during_context
        try: checked.retained_data()
        except p.PackageInventoryError: pass
        else: raise AssertionError("changed package fact accepted")
        assert owner._package_fact_cell is foreign
    else:
        assert checked.retained_data() is original
        assert original.environment == original_environment
        assert checked._ready and not checked._failed and not owner._uncertain
if mutation == "pre_fact_replacement": assert owner._package_fact_cell is foreign_fact
if checked is not None and checked._origin is not None:
    assert all(row.closed or row.unknown for row in checked._origin.records)
    assert all(row.closed or row.unknown for row in checked._origin.expected.scans)
if mutation in ("extra", "missing", "symlink", "directory_symlink", "private_file", "retired_scan"):
    assert checked._bytes_read == 0
if mutation == "after_hash_replace": assert replaced
assert foreign_calls == []
assert loaded._selection is not None  # package failure never fabricates/rewrites native approval
try: p.GatewayPackageOwner.verify(loaded, manifest_raw)
except Exception: pass
else: raise AssertionError("package verification reminted")
if mutation == "normal" or mutation.startswith("history_"):
    assert not owner._uncertain
assert "hmp_startup.gateway_entry" not in sys.modules  # legacy has no entry dependency
print(json.dumps({"mutation": mutation, "passed": True, "runtime_admitted": False}))
'''


@pytest.mark.parametrize("mutation", [
    "normal", "selection_v2", "duplicate", "private_name", "generation", "unknown", "wrong_root",
    "changed",
    "missing", "extra", "symlink", "directory_symlink", "private_file", "directory_mode",
    "digest", "module_origin", "retired_scan", "spec_swap", "namespace_swap", "after_hash_replace",
    "pre_fact_replacement", "history_late", "history_namespace", "history_paths", "history_thread",
    "history_fact_drift", "history_context_drift",
])
def test_pinned_complete_hmp_package(tmp_path, mutation):
    if os.name != "posix" or sys.platform not in ("darwin", "linux"):
        pytest.skip("supported POSIX synthetic tree")
    root = tmp_path / "hmp_plugin"
    root.mkdir(mode=0o700)
    configuration = tmp_path / "private-config"
    configuration.mkdir(mode=0o700)
    for name in ("presentation_gateway_activation.py", "presentation_startup_artifacts.py",
                 "presentation_startup_selection.py", "presentation_gateway_package.py",
                 "presentation_gateway_recipe.py"):
        shutil.copyfile(ARTIFACT_MODULE.with_name(name), root / name)
        (root / name).chmod(0o600)
    (root / "unused.py").write_text("# SYNTHETIC UNUSED CODE\n")
    (root / "nested").mkdir(mode=0o700)
    (root / "nested/data.txt").write_text("SYNTHETIC PUBLIC PACKAGE DATA\n")
    prefix = PREFIX  # actual activation fixture; no native checkout is opened
    assert SCRIPT[:SCRIPT.rfind("print(json.dumps")] == PREFIX
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", prefix + CONFIG_PREFIX + PACKAGE_SUFFIX,
         str(root / "presentation_gateway_activation.py"), "normal", "normal",
         str(root / ARTIFACT_MODULE.name), str(root / SELECTION_MODULE.name),
         str(configuration), str(root), mutation],
        cwd=tmp_path, env={"LANG": "C", "LC_ALL": "C"}, capture_output=True, text=True,
        timeout=20, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "mutation": mutation, "passed": True, "runtime_admitted": False,
    }

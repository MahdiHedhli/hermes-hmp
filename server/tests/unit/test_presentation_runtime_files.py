"""Combined original-owner snapshots over disposable synthetic file/runtime DATA."""

from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base

PREPARE = r"""
environment = base / "environment/site-packages"
stdlib_package=fake_stdlib/"sample_stdlib"
stdlib_package.mkdir(mode=0o700)
(stdlib_package/"__init__.py").write_bytes(b'SYNTHETIC_STDLIB_NOT_EXECUTED')
(stdlib_package/"runtime.pyc").write_bytes(b'SYNTHETIC_BYTECODE_NOT_EXECUTED')
(stdlib_package/"runtime.zip").write_bytes(b'SYNTHETIC_ARCHIVE_NOT_MOUNTED')
dep_root = environment / "sample_dep"
dep_root.mkdir(mode=0o700)
(dep_root / "__init__.py").write_text("VALUE = 1\n")
(dep_root / "data.json").write_bytes(b'SYNTHETIC_PUBLIC_RESOURCE')
backend = environment / "_sample_backend.so"
backend.write_bytes(b'SYNTHETIC_EXTENSION_NOT_EXECUTED')
library = base / "libsample.dylib"
library.write_bytes(b'SYNTHETIC_LIBRARY_NOT_EXECUTED')
prior_library = plugin_root / "support.so"
prior_library.write_bytes(b'SYNTHETIC_PRIOR_PLUGIN_LIBRARY')
for artifact in (backend, library, prior_library): artifact.chmod(0o600)
import sample_dep
"""
DOCUMENTS = r"""
def artifact(path):
    body = path.read_bytes()
    return dict(path=str(path), size=len(body), sha256=hashlib.sha256(body).hexdigest())
dependency = dict(schema=1, kind="HMP_GATEWAY_DEPENDENCIES", generation="1"*64,
    environment=str(environment), packages=[dict(path=str(dep_root), entries=table(dep_root))],
    files=[artifact(backend)], libraries=sorted([artifact(library),artifact(prior_library)],
    key=lambda row: row["path"]), modules=["sample_dep"])
runtime = entry.retained_data().interpreter
interpreter = dict(schema=1, kind="HMP_GATEWAY_INTERPRETER", generation="1"*64,
    runtime=dict(paths=list(runtime.paths),version=list(runtime.version),flags=list(runtime.flags),
    implementation=list(runtime.implementation),platform=runtime.platform),
    loader_policy=("darwin-system-loader-trust" if sys.platform=="darwin"
    else "linux-system-loader-trust"),
    packages=[dict(path=str(stdlib_package),entries=table(stdlib_package))],
    files=[artifact(fake_executable)])
if mutation == "runtime_cross_overlap":
    interpreter["packages"]=[dict(path=str(dep_root),entries=table(dep_root))]
if mutation == "runtime_shared":
    dependency["files"] = sorted([artifact(backend),artifact(dep_root/"data.json")],
                                  key=lambda row: row["path"])
if mutation == "runtime_conflict":
    row=artifact(dep_root/"data.json");row["sha256"]="0"*64
    dependency["files"].append(row)
if mutation == "runtime_private": dependency["files"][0]["path"]=str(environment/".ENV")
if mutation == "runtime_private_library":
    dependency["libraries"][0]["path"]=str(base/".ssh/libprivate.so")
if mutation == "runtime_private_archive":
    dependency["files"][0]["path"]=str(environment/"chats/history.zip")
if mutation == "runtime_wrong_environment": dependency["environment"] += "/changed"
if mutation == "runtime_unknown": dependency["command"]="SYNTHETIC_FORBIDDEN"
if mutation == "runtime_version": interpreter["runtime"]["version"][0] += 1
if mutation == "runtime_flag_type": interpreter["runtime"]["flags"][0] = False
if mutation == "runtime_loader_policy": interpreter["loader_policy"]="unknown"
if mutation == "runtime_no_executable": interpreter["files"]=[]
if mutation == "runtime_redundant_module": dependency["modules"]=["sample_dep","sample_dep.child"]
if mutation == "runtime_overlap":
    nested=dep_root/"nested";nested.mkdir(mode=0o700)
    (nested/"resource.bin").write_bytes(b'SYNTHETIC_RESOURCE')
    sibling=environment/"sample_dep-extra";sibling.mkdir(mode=0o700)
    (sibling/"resource.bin").write_bytes(b'SYNTHETIC_RESOURCE')
    dependency["packages"]=sorted([dict(path=str(p),entries=table(p))
        for p in (dep_root,nested,sibling)],key=lambda row:row["path"])
children.extend([canonical(dependency),canonical(interpreter)])
"""
MUTATIONS = r"""
if mutation == "runtime_interpreter_extra":
    (stdlib_package/"unexpected.py").write_bytes(b'SYNTHETIC_EXTRA')
if mutation == "runtime_interpreter_missing":(stdlib_package/"runtime.pyc").unlink()
if mutation == "runtime_extra": (dep_root/"unexpected.py").write_bytes(b'SYNTHETIC_EXTRA')
if mutation == "runtime_missing": (dep_root/"data.json").unlink()
if mutation == "runtime_changed": backend.write_bytes(b'CHANGED')
if mutation in ("runtime_executable_link","runtime_library_link"):
    selected=fake_executable if mutation == "runtime_executable_link" else library
    target=base/"synthetic-link-target";target.write_bytes(selected.read_bytes());target.chmod(0o600)
    selected.unlink();selected.symlink_to(target)
if mutation == "runtime_prior_replace":
    replacement=base/"replacement.so";replacement.write_bytes(prior_library.read_bytes())
    replacement.chmod(0o600);replacement.replace(prior_library)
if mutation == "runtime_namespace":
    sample_dep.__file__ = None
if mutation == "runtime_spec_name":sample_dep.__spec__.name = "other"
if mutation == "runtime_module_name":sample_dep.__name__ = "other"
if mutation == "runtime_parent_count_swap":
    actual_pid=a.os.getpid
    def swap_prior_count():
        value=actual_pid()
        active=entry._activation._entry_files_owner
        if active is not None and active._inputs is not None:
            plugin._count_cell=tuple([plugin,plugin._origin,plugin._bytes_read])
        return value
    a.os.getpid=swap_prior_count
if mutation == "runtime_last_context_loader":
    original_origins=EntryFileSnapshotOwner._origins
    actual_pid=a.os.getpid
    origins_finished=0
    def count_finished_origins(owner):
        global origins_finished
        value=original_origins(owner);origins_finished+=1;return value
    def final_context_loader():
        value=actual_pid()
        if origins_finished >= 2:sample_dep.__spec__.loader=object()
        return value
    EntryFileSnapshotOwner._origins=count_finished_origins
    a.os.getpid=final_context_loader
if mutation == "runtime_loader_path":sample_dep.__loader__.path += ".changed"
if mutation == "runtime_loader_name":sample_dep.__loader__.name = "other"
if mutation == "runtime_loader_custom":
    class CustomLoader:
        def __getattribute__(self,name):
            raise AssertionError("custom loader metadata must not be invoked")
    sample_dep.__loader__=sample_dep.__spec__.loader=CustomLoader()
if mutation == "runtime_loader_subclass":
    from importlib.machinery import SourceFileLoader
    class CustomSource(SourceFileLoader):pass
    sample_dep.__loader__=sample_dep.__spec__.loader=CustomSource(
        sample_dep.__name__,sample_dep.__file__)
if mutation == "runtime_loader_wrong_form":
    from importlib.machinery import SourcelessFileLoader
    sample_dep.__loader__=sample_dep.__spec__.loader=SourcelessFileLoader(
        sample_dep.__name__,sample_dep.__file__)
if mutation == "runtime_search_path":
    sample_dep.__spec__.submodule_search_locations = list(sample_dep.__path__)
if mutation in ("runtime_after_hash_replace","runtime_loader_after_hash",
                "runtime_loader_path_after_hash"):
    actual_complete = a.StartupArtifactOwner.complete.__func__
    def after_completion(cls, io):
        value = actual_complete(cls, io)
        if mutation == "runtime_after_hash_replace":
            selected=dep_root/"data.json";replacement=base/"same-bytes.bin"
            replacement.write_bytes(selected.read_bytes());replacement.chmod(0o600)
            replacement.replace(selected)
        elif mutation == "runtime_loader_path_after_hash":sample_dep.__loader__.path += ".changed"
        else: sample_dep.__spec__.loader=object()
        return value
    a.StartupArtifactOwner.complete=classmethod(after_completion)
if mutation in ("runtime_file_boundary","runtime_file_over",
                "runtime_byte_boundary","runtime_byte_over"):
    declared = {}
    for document, root in ((plugin_document,plugin_root),(entry_document,entry_root),
                           (dependency["packages"][0],dep_root)):
        for row in document["entries"]:
            if row["kind"]=="file":declared[str(root/row["path"])]=row["size"]
    for package in interpreter["packages"]:
        for row in package["entries"]:
            if row["kind"]=="file":declared[package["path"]+"/"+row["path"]]=row["size"]
    for row in [wrapper,*dependency["files"],*dependency["libraries"],*interpreter["files"]]:
        declared[row["path"]]=row["size"]
    if mutation.startswith("runtime_file_"):
        a._MAX_FILES = 6+len(declared)-(1 if mutation.endswith("over") else 0)
    else:
        # Real prior IO is retained; no fake declaration-derived prior counter is supplied.
        a._MAX_TOTAL = plugin._bytes_read + sum(size for name,size in declared.items()
            if name not in {row.path for row in plugin._origin.expected.files})
        if mutation.endswith("over"):a._MAX_TOTAL -= 1
"""


def runtime_script():
    script = base.SCRIPT
    script = script.replace(
        "entry = GatewayEntryOwner.start()",
        """
fake_executable=base/"runtime-python"
fake_executable.write_bytes(b'SYNTHETIC_INTERPRETER_NOT_EXECUTED')
fake_executable.chmod(0o600)
fake_stdlib=base/"stdlib";fake_stdlib.mkdir(mode=0o700)
sys._stdlib_dir=str(base/"environment/site-packages" if mutation=="runtime_cross_overlap"
                    else fake_stdlib)
sys.executable=str(fake_executable)
entry = GatewayEntryOwner.start()""",
        1,
    )
    script = script.replace(
        "wrapper_path = Path(__file__)", PREPARE + "\nwrapper_path = Path(__file__)", 1
    )
    old = """for kind in ("HMP_GATEWAY_DEPENDENCIES", "HMP_GATEWAY_INTERPRETER"):
    children.append(canonical(dict(schema=1, kind=kind, generation="1" * 64)))"""
    assert old in script
    script = script.replace(old, DOCUMENTS, 1)
    script = script.replace(
        "plugin = GatewayPackageOwner.verify_recipe(recipe)",
        "plugin = GatewayPackageOwner.verify_recipe(recipe)\n" + MUTATIONS,
        1,
    )
    script = script.replace(
        "EntryFileSnapshotOwner.verify(entry,recipe,plugin)",
        "EntryFileSnapshotOwner.verify_runtime_files(entry,recipe,plugin)",
    )
    script = script.replace(
        '("scan_close_unknown", "scan_next_unknown")',
        '("scan_close_unknown", "scan_next_unknown", "runtime_scan_close_unknown", '
        '"runtime_scan_next_unknown")',
    )
    script = script.replace(
        'mutation == "scan_next_unknown"',
        'mutation in ("scan_next_unknown", "runtime_scan_next_unknown")',
    )
    script = script.replace(
        'mutation == "scan_close_unknown"',
        'mutation in ("scan_close_unknown", "runtime_scan_close_unknown")',
    )
    successes = (
        "runtime_loader_path",
        "runtime_loader_name",
        "runtime_loader_custom",
        "runtime_loader_subclass",
        "runtime_loader_wrong_form",
        "runtime_loader_path_after_hash",
        "runtime_normal",
        "runtime_shared",
        "runtime_file_boundary",
        "runtime_byte_boundary",
    )
    script = script.replace('("normal","internal_wrapper","retained_normal")', repr(successes))
    script = script.replace(
        "assert io._origin.parent.count_cell is plugin._fact[7]",
        """
    plan=result._inputs.runtime_plan
    assert plan is not None and io._origin.expected is plan.pending
    assert prior_library.as_posix() not in {row.path for row in plan.pending}
    assert any(row.expected.path==str(prior_library) for row in plan.prior)
    assert io._origin.parent.count_cell is plugin._fact[7]""",
        1,
    )
    # The strict fact is forest DATA; no route, key or executed-image attestation.
    script = script.replace(
        "assert not foreign_calls\n",
        """
if mutation in ("runtime_file_boundary","runtime_byte_boundary"):
    assert result._ready
    if mutation == "runtime_byte_boundary":assert result._fact_cell[2]._bytes_read == a._MAX_TOTAL
if mutation in ("runtime_file_over","runtime_byte_over","runtime_overlap","runtime_private",
                "runtime_namespace","runtime_search_path","runtime_spec_name","runtime_module_name",
                "runtime_parent_count_swap","runtime_cross_overlap", "runtime_private_library",
                "runtime_private_archive"):
    assert entry._activation._artifact_owner is None
if mutation == "runtime_prior_replace":
    assert result._inputs.io_slot[0]._bytes_read == plugin._bytes_read
assert not foreign_calls
""",
        1,
    )
    return script


@pytest.mark.parametrize(
    "mutation",
    [
        "runtime_normal",
        "runtime_shared",
        "runtime_conflict",
        "runtime_private",
        "runtime_wrong_environment",
        "runtime_unknown",
        "runtime_version",
        "runtime_flag_type",
        "runtime_loader_policy",
        "runtime_no_executable",
        "runtime_redundant_module",
        "runtime_overlap",
        "runtime_extra",
        "runtime_missing",
        "runtime_changed",
        "runtime_executable_link",
        "runtime_library_link",
        "runtime_prior_replace",
        "runtime_namespace",
        "runtime_search_path",
        "runtime_after_hash_replace",
        "runtime_loader_after_hash",
        "runtime_file_boundary",
        "runtime_file_over",
        "runtime_byte_boundary",
        "runtime_byte_over",
        "runtime_spec_name",
        "runtime_module_name",
        "runtime_parent_count_swap",
        "runtime_last_context_loader",
        "runtime_scan_close_unknown",
        "runtime_scan_next_unknown",
        "runtime_interpreter_extra",
        "runtime_interpreter_missing",
        "runtime_cross_overlap",
        "runtime_private_library",
        "runtime_private_archive",
    ],
)
def test_combined_runtime_file_snapshot(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(base, "SCRIPT", runtime_script())
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

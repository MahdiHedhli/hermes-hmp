"""Actual selected leaf-link IO through one original owner; snapshot DATA only."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_executable_link_plan import link_script

FINISH = r'''
original_bytes=plugin._bytes_read
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
plan=retained._inputs.runtime_plan;selected=plan.executable_link
expected_total=original_bytes+sum(row.size for row in plan.pending)+2*selected.text_bytes
if mutation in ("io_byte_boundary","io_overread"):
    a._MAX_TOTAL=expected_total
if mutation == "io_hard_target":a.os.link(fake_target,base/"target-alias")
if mutation == "io_hard_link":a.os.link(fake_executable,base/"link-alias",follow_symlinks=False)
if mutation == "io_ancestor_link":
    (base/"bin").rename(base/"bin-real");(base/"bin").symlink_to(base/"bin-real")
if mutation == "io_target_mode":fake_target.chmod(0o500)
actual_link=a.os.readlink
read_calls=[];foreign_counter=None;foreign_scope=object()
if mutation in ("io_read_unknown","io_count_copy","io_scope_drift","io_read_retire",
                "io_overread"):
    def readlink_callback(name,*,dir_fd):
        global foreign_counter
        io=entry._activation._artifact_owner
        if mutation=="io_overread" and len(read_calls)==1:
            current=actual_link(name,dir_fd=dir_fd)
            a.os.symlink(current+b'x',b'changed-link',dir_fd=dir_fd)
            a.os.replace(b'changed-link',name,src_dir_fd=dir_fd,dst_dir_fd=dir_fd)
        value=actual_link(name,dir_fd=dir_fd)
        read_calls.append(len(value))
        if mutation=="io_read_unknown":raise OSError("synthetic unknown link result")
        if mutation=="io_count_copy":
            foreign_counter=tuple(list(io._count_cell));io._count_cell=foreign_counter
        if mutation=="io_scope_drift":io._scope=foreign_scope
        if mutation=="io_read_retire":entry._activation.retire()
        return value
    a.os.readlink=readlink_callback
else:
    def observed_readlink(name,*,dir_fd):
        value=actual_link(name,dir_fd=dir_fd);read_calls.append(len(value));return value
    a.os.readlink=observed_readlink
actual_file=a.StartupArtifactOwner._file
foreign_before=None
if mutation in ("io_link_replace","io_target_replace","io_after_hash_mode","io_before_copy"):
    def after_file(io,expected):
        global foreign_before
        value=actual_file(io,expected)
        if expected is selected.target:
            if mutation=="io_link_replace":
                replacement=base/"new-link";replacement.symlink_to(fake_target)
                replacement.replace(fake_executable)
            if mutation=="io_target_replace":
                replacement=base/"new-target"
                replacement.write_bytes(b'SYNTHETIC_INTERPRETER_NOT_EXECUTED')
                replacement.chmod(0o700);replacement.replace(fake_target)
            if mutation=="io_after_hash_mode":fake_target.chmod(0o500)
            if mutation=="io_before_copy":
                runtime=io._origin.runtime
                foreign_before=runtime.before[0]._replace()
                runtime.before[0]=foreign_before
        return value
    a.StartupArtifactOwner._file=after_file
actual_close=a.os.close;close_fault=False
if mutation=="io_close_unknown":
    def close_callback(fd):
        global close_fault
        io=entry._activation._artifact_owner
        actual_close(fd)
        if (io is not None and io._attempt_cell is not None and not close_fault
                and len(read_calls)==1):
            close_fault=True
            raise OSError("synthetic lost close outcome")
    a.os.close=close_callback
foreign_fact=object()
actual_recheck=a.StartupArtifactOwner.recheck_link_metadata
if mutation.startswith("io_final_"):
    def final_recheck(io):
        result=actual_recheck(io)
        if mutation=="io_final_fact":entry._activation._entry_files_fact_cell=foreign_fact
        if mutation=="io_final_loader":sample_dep.__spec__.loader=object()
        if mutation=="io_final_descriptor":io._origin.records[0].closed=False
        if mutation=="io_final_count":io._bytes_read+=1
        return result
    a.StartupArtifactOwner.recheck_link_metadata=final_recheck
successes=("link_absolute","link_relative","link_multi","link_leading_parent","io_unicode",
           "link_shared","io_shared_prior","io_byte_boundary")
try:
    checked=EntryFileSnapshotOwner.complete(retained)
except EntryFilesError:
    assert mutation not in successes,mutation
    assert retained._failed and not retained._ready
    assert entry._activation._entry_files_fact_cell is (
        foreign_fact if mutation=="io_final_fact" else None)
    io=entry._activation._artifact_owner
    assert io is not None
    if mutation.startswith("io_final_"):
        assert io._ready and io._fact_cell is not None
    else:
        assert io._failed and not io._ready and io._fact_cell is None
    if mutation=="io_final_descriptor":assert not io._origin.records[0].closed
    else:assert all(row.closed or row.unknown for row in io._origin.records)
    if mutation=="io_count_copy":
        assert io._count_cell is foreign_counter and io._unknown
        row=io._origin.runtime.reads[0]
        assert row.returned and row.unknown and row.after[2]==row.before[2]+read_calls[0]
    if mutation=="io_scope_drift":
        assert io._scope is foreign_scope and io._unknown and len(read_calls)==1
        row=io._origin.runtime.reads[0]
        assert row.after[2]==row.before[2]+read_calls[0]
        assert io._count_cell is row.before
    if mutation=="io_read_unknown":
        assert io._unknown and len(read_calls)==1
        assert io._origin.runtime.reads[0].after is None
    if mutation=="io_read_retire":assert io._unknown and len(read_calls)==1
    if mutation=="io_overread":
        assert len(read_calls)==2 and io._unknown and io._bytes_read==expected_total+1
        assert io._origin.runtime.reads[-1].after[2]==expected_total+1
    if mutation=="io_before_copy":assert io._origin.runtime.before[0] is foreign_before
    if mutation=="io_close_unknown":assert close_fault and io._unknown and len(read_calls)==1
else:
    assert mutation in successes,mutation
    io=checked._fact_cell[2];fact=io._fact_cell
    assert checked._ready and io._ready and len(fact)==5
    observation=fact[4]
    assert observation.owner is io and observation.scope is io._origin
    assert observation.source is io._origin.runtime
    assert observation.receipt.expected is selected.target
    assert observation.before.links==observation.after.links
    assert observation.before.target==observation.after.target
    assert observation.receipt.identity==observation.after.target[0]
    assert observation.count is fact[3] is io._count_cell
    assert io._bytes_read==expected_total
    assert len(read_calls)==2*len(selected.hops)
    assert sum(read_calls)==2*selected.text_bytes
    assert all(row.closed and not row.unknown for row in io._origin.records)
    assert all(row.returned and not row.unknown for row in io._origin.runtime.reads)
    assert io._origin.parent.count_cell is plugin._fact[7]
    if mutation=="io_shared_prior":
        assert observation.receipt in plan.prior
        assert selected.target not in io._origin.expected
    if mutation=="io_byte_boundary":assert io._bytes_read==a._MAX_TOTAL
try:EntryFileSnapshotOwner.complete(retained)
except EntryFilesError:pass
else:raise AssertionError("link IO completion replayed")
print(json.dumps({"mutation":mutation,"runtime_admitted":False}))
'''


def io_script():
    script = link_script()
    end = script.index('from hmp_startup import runtime_files as runtime_module')
    script = script[:end] + FINISH
    script = script.replace('mutation == "link_leading_parent"',
                            'mutation in ("link_leading_parent","io_ancestor_link")')
    script = script.replace('fake_stdlib=base/"stdlib";',
                            'if mutation=="io_unicode":fake_executable=base/"runtime-λ"\n'
                            'fake_stdlib=base/"stdlib";', 1)
    script = script.replace('fake_target=fake_stdlib/"runtime-target"',
                            'fake_target=(plugin_root if mutation=="io_shared_prior" '
                            'else fake_stdlib)/"runtime-target"')
    script = script.replace('fake_target.write_bytes(',
                            'if mutation=="io_unicode":fake_target=fake_stdlib/"runtime-π"\n'
                            'fake_target.write_bytes(', 1)
    return script


@pytest.mark.parametrize("mutation", [
    "link_absolute", "link_relative", "link_multi", "link_leading_parent", "link_shared",
    "io_unicode",
    "io_shared_prior", "io_byte_boundary", "io_link_replace", "io_target_replace",
    "io_after_hash_mode", "io_before_copy", "io_hard_target", "io_hard_link",
    "io_ancestor_link", "io_target_mode", "io_read_unknown", "io_count_copy",
    "io_read_retire", "io_overread", "io_close_unknown", "io_scope_drift",
    "io_final_fact", "io_final_loader",
    "io_final_descriptor", "io_final_count",
])
def test_original_link_and_target_io(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(base, "SCRIPT", io_script())
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

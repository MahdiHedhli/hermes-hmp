"""Actual no-follow cache absence on original artifact IO; no cache code executes."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script

CASES = ('missing_parent', 'missing_leaf', 'present_cache', 'ancestor_link', 'appears_after_hash',
         'parent_replaced', 'permission', 'not_directory', 'loop_error', 'wrong_enoent',
         'unknown_stat', 'close_unknown', 'count_copy', 'no_probe_read',
         'before_slot_late', 'before_after_slot_late', 'after_slot_late')
FINISH = r'''
import errno,os
from hmp_plugin import presentation_startup_cache as cache_module
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
inputs=retained._inputs
context=inputs.cache_context_slot[0]
row=next(row for row in context[3] if row.state=='needs_owned_absence')
cache_path=Path(row.location.path)
assert cache_path.parent==base/'__pycache__'
if case in ('missing_leaf','present_cache','appears_after_hash','parent_replaced'):
    cache_path.parent.mkdir(mode=0o700)
if case=='present_cache':cache_path.write_bytes(b'SYNTHETIC_UNAPPROVED_CACHE_NOT_EXECUTED')
if case=='ancestor_link':
    target=base/'cache-target';target.mkdir(mode=0o700);cache_path.parent.symlink_to(target)
actual_file=a.StartupArtifactOwner._file
if case in ('appears_after_hash','parent_replaced'):
    changed=False
    def after_file(self,expected):
        global changed
        result=actual_file(self,expected)
        if not changed:
            changed=True
            if case=='appears_after_hash':
                cache_path.write_bytes(b'SYNTHETIC_NEW_CACHE_NOT_EXECUTED')
            else:
                cache_path.parent.rename(base/'old-cache-parent')
                cache_path.parent.mkdir(mode=0o700)
        return result
    a.StartupArtifactOwner._file=after_file
actual_stat=a.os.stat
foreign_count=None
if case in ('permission','not_directory','loop_error','wrong_enoent','unknown_stat','count_copy'):
    def disturbed_stat(frame):
        global foreign_count
        name=frame.f_locals['name']
        io=frame.f_locals['self']
        active=(io is not None and io._origin is not None and io._origin.cache is not None)
        if active and name=='__pycache__':
            if case=='permission':raise PermissionError(errno.EACCES,'synthetic',name)
            if case=='not_directory':raise NotADirectoryError(errno.ENOTDIR,'synthetic',name)
            if case=='loop_error':raise OSError(errno.ELOOP,'synthetic',name)
            if case=='wrong_enoent':raise FileNotFoundError(errno.ENOENT,'synthetic','other')
            if case=='unknown_stat':raise OSError(errno.EIO,'synthetic',name)
            if case=='count_copy' and foreign_count is None:
                foreign_count=tuple(list(io._count_cell));io._count_cell=foreign_count
    trace_synthetic_boundary(a.StartupArtifactOwner._stat.__code__,
                             'value = os.stat(',disturbed_stat)
actual_close=a.os.close
lost=False
if case=='close_unknown':
    def lost_close(frame):
        global lost
        io=frame.f_locals['self']
        if (io is not None and io._origin.cache is not None and not lost
            and io._origin.cache.effects and not io._origin.cache.effects[-1].returned):
            lost=True;raise OSError('synthetic close acknowledgement lost')
    trace_synthetic_boundary(a.StartupArtifactOwner._close.__code__,
                             'row.closed = True',lost_close)
actual_read=a.os.read
if case=='no_probe_read':
    def code_read(frame):
        io=frame.f_locals['self']
        if io is not None and io._origin.cache is not None:
            effects=io._origin.cache.effects
            assert not effects or effects[-1].returned
    observe_synthetic_native(actual_read,a.StartupArtifactOwner._read.__code__,code_read)
replacement=object()
if case in ('before_slot_late','before_after_slot_late','after_slot_late'):
    actual_guard=a._owner_guard
    def late_slot(self):
        result=actual_guard(self)
        if type(self) is a.StartupArtifactOwner and result.cache is not None:
            cache=result.cache
            phase=1 if case=='after_slot_late' else 0
            size=(phase+1)*len(cache.paths)
            if (cache.paths and len(cache.effects)==size
                    and all(effect.returned for effect in cache.effects)):
                if phase==0 and cache.before[0] is None and cache.after[0] is None:
                    (cache.before if case=='before_slot_late' else cache.after)[0]=replacement
                elif phase==1 and cache.after[0] is None:
                    cache.after[0]=replacement
        return result
    a._owner_guard=late_slot
success=case in ('missing_parent','missing_leaf','no_probe_read')
try:checked=EntryFileSnapshotOwner.complete(retained)
except EntryFilesError:
    assert not success,case
    io=inputs.io_slot[0]
    assert io._failed and not io._ready and io._fact_cell is None
    assert io._cache_fact is None and entry._activation._artifact_fact_cell is None
    if case=='count_copy':assert io._count_cell is foreign_count
    if case in ('before_slot_late','before_after_slot_late','after_slot_late'):
        slot=io._origin.cache.before if case=='before_slot_late' else io._origin.cache.after
        assert slot[0] is replacement
    if case=='close_unknown':assert lost and any(row.unknown for row in io._origin.records)
    else:assert all(row.closed for row in io._origin.records)
else:
    assert success,case
    io=inputs.io_slot[0];fact=io._cache_fact
    assert a.StartupArtifactOwner.seal_cache_observation(io) is fact
    assert fact[0] is io and fact[1] is io._origin and fact[2] is io._origin.cache
    assert fact[3] is fact[2].before[0] and fact[4] is fact[2].after[0]
    assert fact[3].count is io._initial_count_cell and fact[4].count is io._count_cell
    assert len(fact[3].missing)==len(fact[4].missing)==1
    assert fact[3].missing==fact[4].missing
    assert fact[3].missing[0].path==str(cache_path)
    assert all(record.closed and not record.unknown for record in io._origin.records)
    assert io._bytes_read==(io._initial_count_cell[2]
        +sum(row.size for row in inputs.runtime_plan.pending)
        +2*inputs.runtime_plan.executable_link.text_bytes)
    assert not cache_path.exists()
    try:a.StartupArtifactOwner.complete(io)
    except a.ArtifactObservationError:pass
    else:raise AssertionError('probe completion replayed')
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_original_cache_absence_io(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += '\ncase=' + repr(case) + '\n' + FINISH
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

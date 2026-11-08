"""Fresh cache metadata only; no bytes or fallback authority."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('missing', 'appearance', 'symlink', 'counter_copy',
                                 'directory', 'declared', 'wrong_thread', 'replay',
                                 'final_counter', 'fact_copy', 'late_fact_copy',
                                 'stat_permission', 'stat_structure', 'open_error',
                                 'fstat_error', 'close_ack'))
def test_fresh_cache_probe(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    if case in ('directory', 'declared'):
        setup = r"""
import importlib.util
prepared_cache=Path(importlib.util.cache_from_source(str(dep_root/'__init__.py')))
prepared_cache.parent.mkdir(mode=0o700)
if CACHE_CASE=='directory':prepared_cache.mkdir(mode=0o700)
else:prepared_cache.write_bytes(b'SYNTHETIC_DECLARED_CACHE_NOT_READ')
prepared_cache.chmod(0o700 if CACHE_CASE=='directory' else 0o600)
""".replace('CACHE_CASE', repr(case))
        script = script.replace('import sample_dep\n', 'import sample_dep\n' + setup, 1)
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup import cache_probe as pm
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
old_count=checked._fact_cell[2]._count_cell
owner=RuntimeCacheProbeOwner.retain(continuation,index)
path=Path(rows[index].plan_row.location.path)
if case in ('appearance','symlink'):
    path.parent.mkdir(mode=0o700)
    if case=='appearance':path.write_bytes(b'SYNTHETIC_UNAPPROVED_CACHE')
    else:path.symlink_to(dep_root/'__init__.py')
if case in ('stat_permission','stat_structure','open_error','fstat_error','close_ack'):
    import errno
    fault_calls=[]
    if case in ('stat_permission','stat_structure'):
        def fault_stat(frame):
            name=frame.f_locals['name']
            if frame.f_locals['self'] is owner and name=='__pycache__':
                fault_calls.append(case)
                if case=='stat_permission':raise PermissionError(errno.EACCES,'synthetic',name)
                raise NotADirectoryError(errno.ENOTDIR,'synthetic',name)
        trace_synthetic_boundary(RuntimeCacheProbeOwner._stat_known.__code__,
                                 'result = os.stat(',fault_stat)
    if case=='open_error':
        def fault_open(frame):
            if frame.f_locals['self'] is owner and frame.f_locals['name']=='/':
                fault_calls.append(case)
                raise PermissionError(errno.EACCES,'synthetic','/')
        trace_synthetic_boundary(pm.StartupArtifactOwner._open.__code__,
                                 'fd = os.open(',fault_open)
    if case=='fstat_error':
        def fault_fstat(frame):
            if frame.f_locals['self'] is owner and not fault_calls:
                fault_calls.append(case)
                raise OSError(errno.EIO,'synthetic')
        trace_synthetic_boundary(pm.StartupArtifactOwner._fstat.__code__,
                                 'value = os.fstat(',fault_fstat)
    if case=='close_ack':
        close_attempts=[]
        def close_observed(frame):
            if frame.f_locals['self'] is owner:
                close_attempts.append((frame.f_locals['row'],frame.f_locals['fd']))
        observe_synthetic_native(pm.os.close,pm.StartupArtifactOwner._close.__code__,close_observed)
        def fault_close(frame):
            if frame.f_locals['self'] is owner and not fault_calls:
                fault_calls.append(case)
                raise OSError(errno.EIO,'synthetic lost close acknowledgement')
        trace_synthetic_boundary(pm.StartupArtifactOwner._close.__code__,
                                 'row.closed = True',fault_close)
if case=='counter_copy':
    actual=pm._context;contexts=0
    def replace_count():
        global contexts
        contexts+=1
        if contexts==2:owner._count_cell=tuple(list(owner._count_cell))
        return actual()
    pm._context=replace_count
if case=='final_counter':
    actual=pm._context
    def replace_final():
        if owner._started and owner._origin.records and all(
                row.closed for row in owner._origin.records):
            owner._count_cell=tuple(list(owner._count_cell))
        return actual()
    pm._context=replace_final
if case=='wrong_thread':
    import threading
    refused=[]
    def other_thread():
        try:owner.observe()
        except CacheProbeError:refused.append(True)
        else:refused.append(False)
    other=threading.Thread(target=other_thread);other.start();other.join(timeout=10)
    assert not other.is_alive() and refused==[True]
    assert not owner._started and not owner._failed
try:owner.observe()
except CacheProbeError:
    assert case in ('appearance','symlink','counter_copy','final_counter',
                    'stat_permission','stat_structure','open_error',
                    'fstat_error','close_ack') and owner._failed
    assert not owner._ready and owner._fact is None and pm._FACT is None
else:
    assert case in ('missing','directory','declared','wrong_thread','replay',
                    'fact_copy','late_fact_copy') and owner._ready
    expected=('directory' if case=='directory' else
              'declared_regular' if case=='declared' else 'missing_component')
    assert owner._fact[2].state==expected
    assert 'no-fallback-authority' in repr(owner._fact[2])
    fact=owner.current_binding()
    if case=='fact_copy':
        owner._fact=pm._FACT=tuple(list(fact))
        try:owner.current_binding()
        except CacheProbeError:pass
        else:raise AssertionError('copied completion adopted')
    if case=='late_fact_copy':
        actual=pm._context
        def replace_fact():
            copied=tuple(list(fact))
            owner._fact=pm._FACT=owner._origin.activation._runtime_cache_probe_fact=copied
            return actual()
        pm._context=replace_fact
        try:owner.current_binding()
        except CacheProbeError:assert owner._failed
        else:raise AssertionError('late copied completion adopted')
    if case=='replay':
        fact=owner._fact
        try:owner.observe()
        except CacheProbeError:pass
        else:raise AssertionError('probe replayed')
        assert owner._fact is fact
assert owner._bytes_read==0 and checked._fact_cell[2]._count_cell is old_count
if case=='open_error':
    assert fault_calls==[case] and owner._unknown
    assert len(owner._origin.records)==1
    row=owner._origin.records[0]
    assert row.attempted and row.unknown and row.fd is None and not row.close_attempted
elif case=='close_ack':
    assert fault_calls==[case] and owner._unknown
    assert len(close_attempts)==len(owner._origin.records)>1
    assert len({id(row) for row,fd in close_attempts})==len(close_attempts)
    assert all(row.fd is fd for row,fd in close_attempts)
    unknown=[row for row in owner._origin.records if row.unknown]
    assert len(unknown)==1 and unknown[0].close_attempted and not unknown[0].closed
    assert all(row.closed and row.close_attempted for row in owner._origin.records
               if row is not unknown[0])
else:
    if case in ('stat_permission','stat_structure','fstat_error'):
        assert fault_calls==[case] and not owner._unknown
        assert owner._origin.records
    assert all(row.closed and row.close_attempted and not row.unknown
               for row in owner._origin.records)
if case in ('stat_permission','stat_structure','open_error','fstat_error','close_ack'):
    calls_before=list(fault_calls)
    try:owner.observe()
    except CacheProbeError:pass
    else:raise AssertionError('failed probe replayed')
    assert fault_calls==calls_before
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

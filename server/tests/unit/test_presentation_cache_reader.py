"""Declared cache bytes only; no cache-miss fallback or payload execution."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'changed', 'wrong_thread', 'replay',
                                 'read_error', 'fact_copy', 'late_buffer', 'release_foreign',
                                 'late_effect', 'late_ledger', 'late_lifecycle',
                                 'native_count_drift', 'foreign_read_claim', 'late_owner'))
def test_declared_cache_reader(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script.replace('import sample_dep\n', 'import sample_dep\n' + r'''
import importlib.util
prepared_cache=Path(importlib.util.cache_from_source(str(dep_root/'__init__.py')))
prepared_cache.parent.mkdir(mode=0o700)
cache_payload=b'SYNTHETIC_NOT_EXECUTABLE_CACHE_ONLY' * 4096
prepared_cache.write_bytes(cache_payload);prepared_cache.chmod(0o600)
''', 1)
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup import cache_reader as cm
from hmp_startup.cache_reader import DeclaredCacheReadOwner,CacheReadError
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
old_count=checked._fact_cell[2]._count_cell
owner=DeclaredCacheReadOwner.retain(continuation,index)
assert owner._origin.native_files is continuation._source.entry_binding[0].native_files
assert owner._origin.source_digest is None
original=owner._buffer
if case=='changed':prepared_cache.write_bytes(b'X'*len(cache_payload))
if case=='wrong_thread':
    import threading
    refused=[]
    def other_thread():
        try:owner.read()
        except CacheReadError:refused.append(True)
        else:refused.append(False)
    other=threading.Thread(target=other_thread);other.start();other.join(timeout=10)
    assert not other.is_alive() and refused==[True] and not owner._started and not owner._failed
if case=='read_error':
    import errno
    read_calls=0
    def fail_after_prefix(frame):
        global read_calls
        if frame.f_locals['self'] is owner:
            read_calls+=1
            if read_calls==2:raise OSError(errno.EIO,'synthetic lost read acknowledgement')
    trace_synthetic_boundary(DeclaredCacheReadOwner._read.__code__,
                             '_require(type(data) is bytes)',fail_after_prefix)
if case in ('native_count_drift','foreign_read_claim'):
    foreign_claim=object()
    def drift_after_actual_read(frame):
        if frame.f_locals['self'] is owner:
            if case=='native_count_drift':owner._count_cell=tuple(list(owner._count_cell))
            else:owner._read_claim=foreign_claim
    trace_synthetic_boundary(DeclaredCacheReadOwner._read.__code__,
                             '_require(type(data) is bytes)',drift_after_actual_read)
if case=='late_owner':
    actual_context=cm._context
    foreign_owner=object()
    def drift_owner_after_native_return():
        if owner._read_claim is not None and not owner._reading and cm._RESULTS:
            owner._origin.activation._cache_read_owner=foreign_owner
        return actual_context()
    cm._context=drift_owner_after_native_return
if case in ('late_buffer','late_effect','late_ledger','late_lifecycle'):
    actual_context=cm._context
    def replace_after_close():
        if owner._started and owner._origin.records and all(
                row.closed for row in owner._origin.records):
            if case=='late_buffer':owner._buffer=bytearray(b'FOREIGN')
            elif case=='late_effect':
                effect=owner._origin.reads[-1]
                effect.after=tuple(list(effect.after))
            elif case=='late_ledger':
                copied=tuple(list(cm._RESULTS))
                cm._RESULTS=owner._results=owner._origin.activation._cache_read_results=copied
            else:owner._started=False
        return actual_context()
    cm._context=replace_after_close
try:owner.read()
except CacheReadError:
    assert case in ('changed','read_error','late_buffer','late_effect',
                    'late_ledger','late_lifecycle','native_count_drift',
                    'foreign_read_claim','late_owner') and owner._failed
    assert not owner._ready and owner._fact is None and cm._READY is None
    assert original==bytearray()
    if case=='read_error':
        assert owner._bytes_read==65536 and owner._unknown
        assert len(owner._origin.reads)==2 and owner._origin.reads[-1].unknown
    if case=='late_buffer':assert owner._buffer==bytearray(b'FOREIGN')
    if case=='late_owner':
        assert owner._origin.activation._cache_read_owner is foreign_owner
        assert owner._read_claim is not None and owner._unknown
    if case in ('native_count_drift','foreign_read_claim'):
        attempt=cm._ATTEMPTS[0]
        result=attempt[4][0]
        assert result[0] is attempt and result[2]==65536
        assert result[1][2]==65536 and owner._unknown and not cm._RESULTS
        if case=='foreign_read_claim':
            assert owner._read_claim is foreign_claim and owner._reading
        else:assert owner._count_cell is not attempt[3]

else:
    assert case in ('normal','wrong_thread','replay','fact_copy','release_foreign')
    fact=owner.current_binding()
    assert original==cache_payload and owner._bytes_read==len(cache_payload)
    assert fact[4] is original and fact[5].bytecode_header==cache_payload[:16]
    if case=='replay':
        try:owner.read()
        except CacheReadError:pass
        else:raise AssertionError('read replayed')
        assert owner.current_binding() is fact
    if case=='fact_copy':
        owner._fact=cm._READY=tuple(list(fact))
        try:owner.current_binding()
        except CacheReadError:pass
        else:raise AssertionError('copied completion adopted')
    if case=='release_foreign':owner._buffer=bytearray(b'FOREIGN')
    owner.release()
    assert original==bytearray() and owner._released
    if case=='release_foreign':assert owner._buffer==bytearray(b'FOREIGN')
assert checked._fact_cell[2]._count_cell is old_count
assert all(row.closed and row.close_attempted and not row.unknown for row in owner._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

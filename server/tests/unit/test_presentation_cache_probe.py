"""Fresh cache metadata only; no bytes or fallback authority."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('missing', 'appearance', 'symlink', 'counter_copy',
                                 'directory', 'declared', 'wrong_thread', 'replay',
                                 'final_counter', 'fact_copy', 'late_fact_copy'))
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
    assert case in ('appearance','symlink','counter_copy','final_counter') and owner._failed
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
assert all(row.closed and row.close_attempted and not row.unknown for row in owner._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

"""Binding only original source/cache observations; no loading or admission."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize("case", ("normal", "final_source", "final_root", "final_global",
                                 "declared_hash", "declared_mismatch", "declared_unchecked",
                                 "declared_bad_magic", "cache_directory"))
def test_bound_original_cache_inputs(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    if case.startswith('declared_') or case == 'cache_directory':
        setup = r"""
import importlib.util
cache_path=Path(importlib.util.cache_from_source(str(dep_root/'__init__.py')))
cache_path.parent.mkdir(mode=0o700)
cache_case=CASE_VALUE
if cache_case=='cache_directory':cache_path.mkdir(mode=0o700)
else:
    origin=entry._scope.interpreter.source_hash
    digest=origin.builtin(origin.key,(dep_root/'__init__.py').read_bytes())
    if cache_case in ('declared_mismatch','declared_unchecked'):digest=b'BAD_HASH'
    flags=1 if cache_case=='declared_unchecked' else 3
    magic=b'BAD!' if cache_case=='declared_bad_magic' else importlib.util.MAGIC_NUMBER
    cache_path.write_bytes(magic+flags.to_bytes(4,'little')+digest+b'SYNTHETIC_BODY_NOT_LOADED')
cache_path.chmod(0o700 if cache_case=='cache_directory' else 0o600)
""".replace('CASE_VALUE',repr(case))
        script = script.replace('import sample_dep\n', 'import sample_dep\n' + setup, 1)
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase='+repr(case)+'\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
count=checked._fact_cell[2]._count_cell
if case.startswith('final_'):
    from hmp_startup import gateway_continuation as cm
    from hmp_startup.cache_context import CacheContextOwner
    from hmp_startup.cache_selection import CacheSelectionError
    actual=CacheContextOwner.current_binding;calls=0;foreign_calls=[]
    class Foreign:
        def __getattr__(self,name):foreign_calls.append(name);raise AssertionError('foreign source')
    def late(self):
        global calls
        value=actual(self);calls+=1
        if calls==2:
            if case=='final_source':continuation._source=Foreign()
            else:
                copied=tuple(list(continuation._root));continuation._root=copied
                if case=='final_global':
                    cm._ROOT=copied
                    continuation._source.entry_binding[2][3]._continuation_cell=copied
        return value
    CacheContextOwner.current_binding=late
    try:selected_cache_input_attempts(continuation)
    except CacheSelectionError:
        assert calls==2 and foreign_calls==[]
        print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
        raise SystemExit(0)
    else:raise AssertionError('late continuation cohort accepted')
rows=selected_cache_input_attempts(continuation)
assert len(rows)>1
if case=='normal':
    assert {row.plan_row.state for row in rows}=={'tree_expected_absent','needs_owned_absence'}
    assert all(row.attempt.input=='source' and row.cache is None
               and row.header is None for row in rows)
else:
    selected=next(row for row in rows if row.plan_row.source.path==str(dep_root/'__init__.py'))
    if case=='cache_directory':
        assert selected.plan_row.state=='tree_nonfile' and selected.proof[1][1]=='directory'
        assert selected.cache is None and selected.attempt.input=='source'
    else:
        assert selected.plan_row.state=='declared'
        assert selected.cache.expected is selected.plan_row.cache
        assert selected.header is selected.cache.bytecode_header and selected.proof==()
        wanted='cache' if case in ('declared_hash','declared_unchecked') else 'source'
        assert selected.attempt.input==wanted
        if case=='declared_unchecked':assert selected.attempt.validation=='hash_unchecked'
assert all(row.source.receipt.expected is row.plan_row.source for row in rows)
assert checked._fact_cell[2]._count_cell is count
assert all('not-admission' in repr(row) for row in rows)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)


@pytest.mark.parametrize('case', ('missing', 'ancestor', 'unequal'))
def test_foreign_absence_proof_no_hooks(case):
    from hmp_startup.cache_candidates import PlannedCachePath
    from hmp_startup.cache_context import CacheInputData
    from hmp_startup.cache_selection import CacheSelectionError, _cache_proof

    from hmp_plugin.presentation_startup_artifacts import ExpectedArtifact
    from hmp_plugin.presentation_startup_cache import _CachePass, _Missing

    calls = []

    class Foreign:
        def __iter__(self):
            calls.append('iter')
            raise AssertionError('foreign iteration')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign equality')

    path = '/synthetic/__pycache__/source.pyc'
    row = CacheInputData(ExpectedArtifact('/synthetic/source.py', 1, '0' * 64),
                         PlannedCachePath(path, False), None, None, 'needs_owned_absence')
    missing = (Foreign() if case == 'missing' else
               (_Missing(path, 0, (('/synthetic', (1, 2, 3, 4, Foreign())),)),)
               if case == 'ancestor' else ())
    before = _CachePass(None, None, None, 0, missing, (), ())
    after = _CachePass(None, None, None, 1,
                       (_Missing(path, 0, ()),) if case == 'unequal' else missing, (), ())
    with pytest.raises(CacheSelectionError):
        _cache_proof(row, (), (None, None, None, before, after, None))
    assert calls == []

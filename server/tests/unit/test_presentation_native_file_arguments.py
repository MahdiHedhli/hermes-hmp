"""Foreign primitive arguments refuse at the actual entry-bound file path."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('method,position', (('_open', 0), ('_open', 1), ('_open', 2),
                                            ('_stat', 0), ('_stat', 1),
                                            ('_fstat', 0), ('_read', 0)))
@pytest.mark.parametrize('change', ('normal', 'foreign'))
def test_native_file_arguments_before_effects(tmp_path, monkeypatch, method, position, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_method=getattr(a.StartupArtifactOwner,METHOD)
calls=[];foreign_calls=[];refusals=[];violations=[]
class ForeignArgument:
    def __fspath__(self):foreign_calls.append('path');raise AssertionError('foreign path')
    def __index__(self):foreign_calls.append('index');raise AssertionError('foreign index')
    def __bool__(self):foreign_calls.append('bool');raise AssertionError('foreign bool')
    def __eq__(self,other):foreign_calls.append('eq');raise AssertionError('foreign equality')
def checked_method(target,*args):
    if type(target) is not GatewayPackageOwner or target._origin.native_files is None:
        return actual_method(target,*args)
    calls.append(True)
    count=target._count_cell;records=len(target._origin.records)
    changed=list(args)
    if CHANGE=='foreign':changed[POSITION]=ForeignArgument()
    try:return actual_method(target,*changed)
    except BaseException:
        if CHANGE=='foreign':
            refusals.append(True)
            if target._count_cell is not count or len(target._origin.records)!=records:
                violations.append('effect before argument refusal')
        raise
setattr(a.StartupArtifactOwner,METHOD,checked_method)
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
except Exception:
    assert CHANGE=='foreign' and calls and refusals
else:assert CHANGE=='normal' and calls
finally:setattr(a.StartupArtifactOwner,METHOD,actual_method)
assert foreign_calls==[] and violations==[]
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''
    injected = injected.replace('METHOD', repr(method)).replace('POSITION', str(position))
    injected = injected.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')

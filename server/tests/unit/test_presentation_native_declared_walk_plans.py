"""Original declared file walks have bounded one-shot ordered intent records."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('change', ('normal', 'replay', 'out_of_order',
                                    'progress_bool', 'already_started'))
def test_original_declared_walk_lifecycle(tmp_path, monkeypatch, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_file=a.StartupArtifactOwner._file
calls=[];refusals=[];violations=[]
def checked_file(target,expected,native_registration=None):
    if native_registration is None or type(target) is not GatewayPackageOwner:
        return actual_file(target,expected,native_registration)
    calls.append(True)
    registration=native_registration
    if CHANGE=='normal':return actual_file(target,expected,registration)
    if CHANGE=='replay':actual_file(target,expected,registration)
    if CHANGE=='progress_bool':registration.file_progress[0]=True
    if CHANGE=='already_started':registration.file_walks[0].state[0]=1
    if CHANGE=='out_of_order':
        assert len(registration.file_walks)>1
        expected=registration.file_walks[1].expected
    count=target._count_cell;records=len(target._origin.records)
    try:return actual_file(target,expected,registration)
    except BaseException:
        refusals.append(True)
        if target._count_cell is not count or len(target._origin.records)!=records:
            violations.append('effects before file-walk intent refusal')
        raise
a.StartupArtifactOwner._file=checked_file
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
except Exception:
    assert CHANGE!='normal' and calls and refusals
else:
    assert CHANGE=='normal' and calls and plugin._ready
    registration=plugin._native_scope_registration
    assert registration.file_progress==[len(registration.file_walks)]
    for index,plan in enumerate(registration.file_walks):
        assert plan.owner is plugin and plan.scope is plugin._origin
        assert plan.cell is plugin._cell and plan.root is plugin._root_cell
        assert plan.declaration is plugin._origin.expected.files
        assert plan.expected is plan.declaration[index] and plan.index==index
        assert plan.components==('/',*plan.expected.path[1:].split('/'))
        assert plan.state==[2]
finally:a.StartupArtifactOwner._file=actual_file
assert violations==[]
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')

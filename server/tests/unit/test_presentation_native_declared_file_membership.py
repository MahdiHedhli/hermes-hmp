"""Entry-bound file reads use original declaration objects before file effects."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('package', 'artifact'))
@pytest.mark.parametrize('change', ('normal', 'copied', 'unlisted', 'foreign'))
def test_declared_file_identity_before_open(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_file=a.StartupArtifactOwner._file
calls=[];foreign_calls=[];rejected=[];violations=[]
class ForeignExpected:
    def __getattr__(self,name):foreign_calls.append('get');raise AssertionError('foreign getter')
    def __eq__(self,other):foreign_calls.append('eq');raise AssertionError('foreign equality')
    def __fspath__(self):foreign_calls.append('path');raise AssertionError('foreign path')
def checked_file(target,expected,native_registration=None):
    wanted=GatewayPackageOwner if KIND=='package' else a.StartupArtifactOwner
    if native_registration is None or type(target) is not wanted:
        return actual_file(target,expected,native_registration)
    count=target._count_cell;records=len(target._origin.records)
    candidate=expected
    if CHANGE=='copied':candidate=expected._replace()
    if CHANGE=='unlisted':candidate=expected._replace(path=str(base/'UNLISTED_SYNTHETIC_FILE'))
    if CHANGE=='foreign':candidate=ForeignExpected()
    calls.append(target)
    try:return actual_file(target,candidate,native_registration)
    except BaseException:
        if CHANGE!='normal':
            rejected.append(True)
            if target._count_cell is not count or len(target._origin.records)!=records:
                violations.append('file effects before declaration refusal')
        raise
a.StartupArtifactOwner._file=checked_file
'''.replace('KIND', repr(kind)).replace('CHANGE', repr(change))
    after = r'''
try:
    plugin = GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    held_entry=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
    checked=EntryFileSnapshotOwner.complete(held_entry)
except Exception:
    assert CHANGE!='normal' and calls
else:assert CHANGE=='normal' and calls and checked._ready
finally:a.StartupArtifactOwner._file=actual_file
assert foreign_calls==[] and violations==[]
assert CHANGE=='normal' or rejected
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected + after))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')

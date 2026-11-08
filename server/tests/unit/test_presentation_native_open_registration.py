"""Actual opens keep the caller-held original registration across callbacks."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('package', 'artifact'))
@pytest.mark.parametrize('change', ('normal', 'copy', 'missing', 'post_return_copy'))
def test_actual_open_keeps_original_registration(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_open=a.StartupArtifactOwner._open;actual_walk=a._native_walk_scope
calls=[];refusals=[];violations=[];replaced=[];known=[]
wanted=GatewayPackageOwner if KIND=='package' else a.StartupArtifactOwner
def checked_open(target,name,parent,directory,native_registration=None):
    if native_registration is None or type(target) is not wanted:
        return actual_open(target,name,parent,directory,native_registration)
    calls.append(True)
    count=target._count_cell;records=len(target._origin.records)
    supplied=native_registration
    if CHANGE=='copy':supplied=supplied._replace()
    if CHANGE=='missing':supplied=None
    try:return actual_open(target,name,parent,directory,supplied)
    except BaseException:
        refusals.append(True)
        if CHANGE in ('copy','missing') and (target._count_cell is not count
                                            or len(target._origin.records)!=records):
            violations.append('descriptor acquisition before registration refusal')
        raise
def callback_walk(target,registration):
    result=actual_walk(target,registration)
    frame=sys._getframe(1)
    if (CHANGE=='post_return_copy' and type(target) is wanted and not replaced
            and frame.f_code is actual_open.__code__
            and type(frame.f_locals.get('fd')) is int):
        row=frame.f_locals['row'];fd=frame.f_locals['fd']
        assert row.fd is fd and not row.closed
        copied=registration._replace()
        target._native_scope_registration=copied
        target._origin.native_registration_slot[0]=copied
        registration.lineage.ledger.scopes[registration.index]=copied
        known.append((row,fd));replaced.append(True)
    return result
a.StartupArtifactOwner._open=checked_open;a._native_walk_scope=callback_walk
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    held_entry=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
    checked=EntryFileSnapshotOwner.complete(held_entry)
except Exception:
    assert CHANGE!='normal' and calls and refusals
else:assert CHANGE=='normal' and calls and checked._ready
finally:a.StartupArtifactOwner._open=actual_open;a._native_walk_scope=actual_walk
assert violations==[]
if CHANGE=='post_return_copy':
    assert replaced and known
    assert all(row.close_attempted and row.closed and row.unknown for row,fd in known)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('KIND', repr(kind)).replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')

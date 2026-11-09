"""Real isolated entry-to-Scope blueprint publication; not native link admission."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('fault', ('normal', 'owner', 'activation', 'io_slot', 'count', 'scope_dispatch'))
def test_actual_link_scope_last_origin_return_seals_publication(tmp_path, monkeypatch, fault):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)] + '\nfault=' + repr(fault) + '\n' + r'''
from hmp_startup import link_factory_origin as actual_origins
from hmp_plugin import presentation_link_path_policy as policy
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
original_scope_dispatch=vars(a._Scope).get('__getattribute__')
original_current_code=actual_origins.current.__code__
original_ctor_code=a._Scope.__new__.__code__
foreign_slot=object();scope_seen=[];last_returns=[];hooks=[];actual_owner=[];baseline=[]
ledger=entry._scope.native_files.ledger

def foreign(*args,**kwargs):
    hooks.append(True)
    raise AssertionError('foreign Scope dispatch ran')

def observe(frame,event,result):
    if event=='call':
        if frame.f_code not in (a.StartupArtifactOwner._retain.__func__.__code__, original_ctor_code, original_current_code):return None
        frame.f_trace_lines=False
    if event=='call' and frame.f_code is a.StartupArtifactOwner._retain.__func__.__code__:
        if frame.f_locals.get('runtime') is not None:
            baseline.append((tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes)))
    if event=='return' and frame.f_code is original_ctor_code:
        if frame.f_locals.get('native_link_blueprint') is not None:
            scope_seen.append(result)
            actual_owner.append(entry._activation._artifact_owner)
    if (event=='return' and frame.f_code is original_current_code and scope_seen
            and frame.f_back is not None and frame.f_back.f_code.co_name=='link_rejoin'
            and actual_owner[0]._origin is None):
        last_returns.append(True)
        # Fourth direct rejoin after actual Scope constructor is the last
        # callback before the inline final publication seal.
        if len(last_returns)==4:
            sys.settrace(None)
            owner=actual_owner[0]
            if fault=='owner':owner._scope=foreign_slot
            elif fault=='activation':entry._activation._artifact_cell=foreign_slot
            elif fault=='io_slot':scope_seen[0].runtime.inputs.io_slot[0]=foreign_slot
            elif fault=='count':scope_seen[0].runtime.count[0]=foreign_slot
            elif fault=='scope_dispatch':a._Scope.__getattribute__=foreign
previous=sys.gettrace();sys.settrace(observe)
refused=False
try:
    checked=EntryFileSnapshotOwner.complete(retained)
except EntryFilesError:
    refused=True
finally:
    sys.settrace(previous)
    if fault=='scope_dispatch':
        if original_scope_dispatch is None:del a._Scope.__getattribute__
        else:a._Scope.__getattribute__=original_scope_dispatch
assert len(scope_seen)==1 and len(actual_owner)==1 and len(baseline)==1
assert len(last_returns)==4 and hooks==[]
owner=actual_owner[0]
if fault=='normal':
    assert not refused and checked._ready and owner._ready
    scope=owner._origin;blueprint=scope.native_link_blueprint
    assert blueprint is scope_seen[0].native_link_blueprint
    assert blueprint.owner is owner and blueprint.runtime is scope.runtime
    assert blueprint.lineage is scope.native_files and blueprint.context is scope.context
    assert blueprint.origin is tuple.__getitem__(entry._scope.native_files,4)
    assert len(blueprint.rows)==3*(len(scope.runtime.link.hops)+1)
    assert policy._scope_blueprint_tail(blueprint) is blueprint
else:
    assert refused and retained._failed and owner._failed and not owner._ready
    assert owner._origin is None and owner._cell is owner._root_cell is None
    assert owner._scope is (foreign_slot if fault=='owner' else None)
    assert entry._activation._artifact_cell is (
        foreign_slot if fault=='activation' else (entry._activation,owner))
    if fault=='io_slot':assert scope_seen[0].runtime.inputs.io_slot[0] is foreign_slot
    if fault=='count':assert scope_seen[0].runtime.count[0] is foreign_slot
    assert baseline[0]==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
    assert scope_seen[0].native_registration_slot==[None]
    assert scope_seen[0].records==[]
    try:EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError:pass
    else:raise AssertionError('lost/refused actual publication replayed')
    assert baseline[0]==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

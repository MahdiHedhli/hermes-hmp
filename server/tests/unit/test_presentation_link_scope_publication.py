"""Real isolated entry-to-Scope blueprint publication; not native link admission."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('fault', ('normal', 'owner', 'activation', 'io_slot', 'count', 'scope_dispatch',
                                    'scope_dispatch_early', 'policy_code', 'blueprint_dispatch',
                                    'register_helper', 'need_helper', 'source_helper',
                                    'scope_blueprint_copy', 'lost_blueprint_return'))
def test_actual_link_scope_last_origin_return_seals_publication(tmp_path, monkeypatch, fault):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script.replace('entry = GatewayEntryOwner.start()',
        "import os,time\nstage_fd=os.open(base/'link-scope-stage.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\nstage_start=time.monotonic()\ndef stage(label):\n    os.write(stage_fd,(json.dumps({'stage':label,'elapsed':time.monotonic()-stage_start})+'\\n').encode())\nstage('before_entry')\nentry = GatewayEntryOwner.start()\nstage('after_entry')",1)
    script = script[:script.index(marker)] + '\nfault=' + repr(fault) + '\n' + r'''
from hmp_startup import link_factory_origin as actual_origins
from hmp_plugin import presentation_link_path_policy as policy
stage('before_link_retention')
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
stage('after_link_retention')
original_scope_dispatch=vars(a._Scope).get('__getattribute__')
original_blueprint_dispatch=vars(policy._LinkScopeBlueprint).get('__getattribute__')
selected_return=2 if fault=='scope_dispatch_early' else 4
original_current_code=actual_origins.current_started.__code__
original_ctor_code=a._Scope.__new__.__code__
original_blueprint_code=policy._new_scope_blueprint.__code__
original_retain_code=a.StartupArtifactOwner._retain.__func__.__code__
root_stage_lines={}
for line_number,line in enumerate(Path(a.__file__).read_text().splitlines(),1):
    if line_number<original_retain_code.co_firstlineno:continue
    if any(fragment in line for fragment in ('_source_current(source)',
            'current_row = link_origin', 'runtime_guard(runtime.entry',
            'classes = []', 'link_cohort = (', 'held_factory = blueprint_row',
            'link_blueprint = held_factory')):
        root_stage_lines[line_number]=line.strip()[:90]
root_stage_seen=set()
foreign_slot=object();scope_seen=[];last_returns=[];hooks=[];actual_owner=[];baseline=[]
partial_cells=[];actual_runtime=[];copied_blueprints=[];actual_blueprints=[]
ledger=entry._scope.native_files.ledger

def foreign(*args,**kwargs):
    hooks.append(True)
    raise AssertionError('foreign Scope dispatch ran')

def observe(frame,event,result):
    if event=='call':
        if (frame.f_code is not original_retain_code and frame.f_code is not original_ctor_code
                and frame.f_code is not original_current_code and frame.f_code is not original_blueprint_code):return None
        frame.f_trace_lines=(frame.f_code is original_retain_code
            or fault=='scope_blueprint_copy' and frame.f_code is original_ctor_code)
    if (event=='line' and frame.f_code is original_ctor_code and fault=='scope_blueprint_copy'
            and frame.f_locals.get('native_link_blueprint') is not None and not copied_blueprints):
        actual=frame.f_locals['native_link_blueprint'];copied=actual._replace()
        copied_blueprints.append((actual,copied))
        frame.f_locals['native_link_blueprint']=copied
    if event=='line' and frame.f_code is original_retain_code:
        if frame.f_lineno in root_stage_lines and frame.f_lineno not in root_stage_seen:
            root_stage_seen.add(frame.f_lineno);stage(root_stage_lines[frame.f_lineno])
    if event=='call' and frame.f_code is original_retain_code:
        if frame.f_locals.get('runtime') is not None:
            baseline.append((tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes)))
            actual_runtime.append(frame.f_locals['runtime'])
            stage('runtime_scope_call')
    if event=='return' and frame.f_code is original_blueprint_code:
        actual_blueprints.append(result)
        actual_owner.append(frame.f_locals['owner'])
        partial_cells.append(entry._activation._artifact_cell)
        if fault=='lost_blueprint_return':
            stage('synthetic_blueprint_return_lost');sys.settrace(None)
            raise OSError('synthetic actual blueprint return lost')
    if event=='return' and frame.f_code is original_ctor_code:
        if frame.f_locals.get('native_link_blueprint') is not None:
            scope_seen.append(result)
            stage('scope_constructor_return')
            assert actual_owner==[entry._activation._artifact_owner]
            if fault=='scope_blueprint_copy':sys.settrace(None)
    if (event=='return' and frame.f_code is original_current_code and scope_seen
            and frame.f_back is not None and frame.f_back.f_code.co_name=='link_rejoin'
            and actual_owner[0]._origin is None):
        last_returns.append(True)
        # Fourth direct rejoin after actual Scope constructor is the last
        # callback before the inline final publication seal.
        if len(last_returns)==selected_return:
            stage('last_selected_origin_return')
            sys.settrace(None)
            owner=actual_owner[0]
            if fault=='owner':owner._scope=foreign_slot
            elif fault=='activation':entry._activation._artifact_cell=foreign_slot
            elif fault=='io_slot':scope_seen[0].runtime.inputs.io_slot[0]=foreign_slot
            elif fault=='count':scope_seen[0].runtime.count[0]=foreign_slot
            elif fault in ('scope_dispatch','scope_dispatch_early'):a._Scope.__getattribute__=foreign
            elif fault=='policy_code':policy._new_policy.__code__=foreign.__code__
            elif fault=='blueprint_dispatch':policy._LinkScopeBlueprint.__getattribute__=foreign
            elif fault=='register_helper':a._register_native_scope=foreign
            elif fault=='need_helper':a._require=foreign
            elif fault=='source_helper':a._source_current=foreign
    return observe
previous=sys.gettrace();sys.settrace(observe)
refused=False
try:
    checked=EntryFileSnapshotOwner.complete(retained)
    stage('complete_return')
except EntryFilesError:
    refused=True
    stage('refused_return')
finally:
    sys.settrace(previous)
    if fault=='blueprint_dispatch':
        if original_blueprint_dispatch is None:del policy._LinkScopeBlueprint.__getattribute__
        else:policy._LinkScopeBlueprint.__getattribute__=original_blueprint_dispatch
    if fault in ('scope_dispatch','scope_dispatch_early'):
        if original_scope_dispatch is None:del a._Scope.__getattribute__
        else:a._Scope.__getattribute__=original_scope_dispatch
assert len(scope_seen)==(0 if fault=='lost_blueprint_return' else 1)
assert len(actual_owner)==len(baseline)==len(partial_cells)==len(actual_blueprints)==1
assert len(last_returns)==(0 if fault in ('scope_blueprint_copy','lost_blueprint_return') else selected_return)
assert hooks==[]
if fault=='scope_blueprint_copy':
    assert len(copied_blueprints)==1
    assert scope_seen[0].native_link_blueprint is copied_blueprints[0][1]
    assert copied_blueprints[0][0] is actual_blueprints[0]
    assert copied_blueprints[0][1] is not actual_blueprints[0]
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
        foreign_slot if fault=='activation' else partial_cells[0])
    if fault=='io_slot':assert scope_seen[0].runtime.inputs.io_slot[0] is foreign_slot
    if fault=='count':assert scope_seen[0].runtime.count[0] is foreign_slot
    assert baseline[0]==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
    if scope_seen:
        assert scope_seen[0].native_registration_slot==[None]
        assert scope_seen[0].records==[]
    assert actual_runtime[0].inputs.io_slot[0] is (foreign_slot if fault=='io_slot' else None)
    try:EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError:pass
    else:raise AssertionError('lost/refused actual publication replayed')
    assert baseline[0]==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
stage('assertions_complete')
os.close(stage_fd)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)


def test_actual_link_scope_unobserved_normal(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)] + r'''
from hmp_plugin import presentation_link_path_policy as policy
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
checked=EntryFileSnapshotOwner.complete(retained)
assert checked._ready
owner=checked._fact_cell[2];scope=owner._origin;blueprint=scope.native_link_blueprint
assert owner._ready and blueprint.owner is owner and blueprint.runtime is scope.runtime
assert blueprint.context is scope.context and blueprint.lineage is scope.native_files
assert blueprint.origin is tuple.__getitem__(entry._scope.native_files,4)
assert len(blueprint.rows)==3*(len(scope.runtime.link.hops)+1)
assert policy._scope_blueprint_tail(blueprint) is blueprint
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

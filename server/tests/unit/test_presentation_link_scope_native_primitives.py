"""Actual late native-primitive drift at both Scope publication seals."""
import ast
import json

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('publication', ('first', 'second'))
@pytest.mark.parametrize('export', ('map', 'is_not'))
def test_scope_publication_rejects_changed_native_export(
        tmp_path, monkeypatch, request, publication, export):
    tree = ast.parse((base.SERVER / 'hmp_plugin/presentation_startup_artifacts.py').read_text())
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                 and n.name == 'StartupArtifactOwner')
    retain = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == '_retain')
    calls = sorted(n.lineno for n in ast.walk(retain) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == 'link_rejoin')
    assert len(calls) >= 3
    # Two post-publication rejoins follow the final pre-publication rejoin.
    # The real observed scope/slot state below must also match the target.
    line = calls[-3] if publication == 'first' else calls[-1]
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\npublication,export,target_line=' + repr((publication, export, line)) + '\n'
    script += r'''
import builtins
from hmp_startup.entry_files import EntryFilesError
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
ledger=entry._scope.native_files.ledger
retain_code=a.StartupArtifactOwner._retain.__func__.__code__
register_code=a._register_native_scope.__code__
rejoin_code=next(c for c in retain_code.co_consts
                 if type(c) is type(retain_code) and c.co_name=='link_rejoin')
module=sys.modules['_operator'] if export=='is_not' else builtins
original=getattr(module,export)
assign=setattr
observed=[];mutated=[];foreign_calls=[];held=[];registrations=[];successful_returns=[]

def foreign(*args,**kwargs):
    foreign_calls.append(True)
    raise AssertionError('changed native primitive was dispatched')

def observe(frame,event,value):
    if mutated:
        if event=='call' and frame.f_code is register_code and frame.f_back.f_code is retain_code:
            registrations.append(True)
        if event=='return' and frame.f_code is retain_code and value is held[0][0]:
            successful_returns.append(True)
    if (event=='return' and frame.f_code is rejoin_code and not mutated
            and frame.f_back.f_code is retain_code
            and frame.f_back.f_lineno==target_line):
        context=frame.f_back.f_locals
        owner=context['owner'];source=context['runtime'];scope=context['s']
        if publication=='first':
            assert owner._scope is None and source.inputs.io_slot[0] is None
        else:
            assert owner._scope is scope and source.inputs.io_slot[0] is owner
        held.append((owner,source))
        observed.append((ledger.counts[0],ledger.counts[1],len(ledger.attempts)))
        assign(module,export,foreign)
        assert getattr(module,export) is foreign
        mutated.append(True)

prior=sys.getprofile()
assert prior is None and sys.gettrace() is None
monitor=getattr(sys,'monitoring',None)
if monitor is not None:
    monitor.use_tool_id(5,'hermes-synthetic-scope-native-primitives')
    def arm(code,offset):
        if sys._getframe(1).f_locals.get('runtime') is not None:
            sys.setprofile(observe)
    monitor.register_callback(5,monitor.events.PY_START,arm)
    monitor.set_local_events(5,retain_code,monitor.events.PY_START)
else:
    def arm(frame,event,value):
        frame.f_trace_lines=False
        if (event=='call' and frame.f_code is retain_code
                and frame.f_locals.get('runtime') is not None):
            sys.settrace(None);sys.setprofile(observe)
        return None
    sys.settrace(arm)
failed=False
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as caught:
    assert caught.failed_owner is retained
    failed=True
finally:
    sys.setprofile(prior);sys.settrace(None)
    assign(module,export,original)
    if monitor is not None:
        monitor.set_local_events(5,retain_code,0)
        monitor.register_callback(5,monitor.events.PY_START,None)
        monitor.free_tool_id(5)
assert mutated==[True] and len(observed)==1 and failed
assert foreign_calls==[]
assert registrations==[] and successful_returns==[]
assert retained._failed and not retained._ready and retained._fact_cell is None
owner,source=held[0]
assert owner._failed and not owner._ready and owner._fact_cell is None
if publication=='first':
    assert owner._scope is None and source.inputs.io_slot[0] is None
else:
    assert owner._scope is not None and source.inputs.io_slot[0] is owner
assert tuple(ledger.counts)==observed[0][:2] and len(ledger.attempts)==observed[0][2]
evidence=dict(publication=publication,export=export,mutation_completed=True,
              refused=True,foreign_calls=0,new_work=0,reserve_change=0,
              registration_calls_after_mutation=0,successful_retainer_returns=0,
              scope_published_before_refusal=publication=='second')
destination=base/'scope-native-primitive-refusal.json'
destination.write_text(json.dumps(evidence,sort_keys=True));destination.chmod(0o600)
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
    evidence = json.loads((tmp_path / 'scope-native-primitive-refusal.json').read_text())
    request.node.user_properties.append(('scope_native_primitive_evidence', json.dumps(evidence)))

"""Actual native-consumer audit costs; no performance/admission pass threshold."""
import json

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


def test_actual_native_consumer_audit_candidates(tmp_path, monkeypatch, request):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += r'''
import time,statistics
from hmp_plugin import presentation_native_link as link
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
closed=presentation_native_metadata._closed_link_engine_origin
code=closed.__code__;evidence=[];caught=[]
class StopAfterMeasurement(Exception):pass

def observe(frame,event,value):
    if event!='call' or frame.f_code is not code or evidence:return None
    owner=frame.f_locals['owner'];resource=frame.f_locals['resource']
    reg=tuple.__getitem__(resource,1);scope=reg.scope
    record=scope.native_link_audit;origin,layout=record[:2]
    ledger=reg.native_ledger
    before=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes),owner._count_cell)
    source=scope.parent;runtime=scope.runtime;inputs=runtime.inputs;cell=runtime.cell
    assert runtime.entry._inputs is inputs and runtime.entry._root_cell is cell
    samples={}
    # No authority or verdict is reused. Every sampled invocation runs the real
    # original function against the same currently valid, paused native fixture.
    for name,function,args in (
            ('full_engine',link._engine_origin_tail,(origin,)),
            ('fixed_live_engine',link._engine_live_tail,(origin,layout)),
            ('closed_selector',closed,(owner,resource))):
        values=[]
        for _ in range(24):
            started=time.perf_counter_ns();result=function(*args)
            values.append(time.perf_counter_ns()-started)
            assert result is origin
        samples[name]={'samples':len(values),'median_ns':statistics.median(values),
                       'minimum_ns':min(values),'maximum_ns':max(values)}
    assert scope is reg.scope is owner._origin is owner._scope
    assert scope.parent is source and scope.runtime is runtime
    assert runtime.entry._inputs is runtime.inputs is inputs
    assert runtime.entry._root_cell is runtime.cell is cell
    assert before==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes),owner._count_cell)
    row={'samples':samples,'actual_native_consumer':True,'no_new_native_work':True,
         'same_original_input_roots':True,'synthetic_fixture':True,
         'full_startup_pass':False,'optimized_dispatch_enabled':False,
         'benchmark_is_adversarial_qualification':False}
    p=base/'native-consumer-audit-cost.json';p.write_text(json.dumps(row));p.chmod(0o600)
    evidence.append(row)
    raise StopAfterMeasurement()
assert sys.gettrace() is None and sys.getprofile() is None
sys.settrace(observe)
try:EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as error:caught.append(error)
finally:sys.settrace(None)
assert len(evidence)==len(caught)==1 and caught[0].failed_owner is retained
assert retained._failed and not retained._ready
assert sys.gettrace() is sys.getprofile() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
    evidence = json.loads((tmp_path / 'native-consumer-audit-cost.json').read_text())
    assert evidence['actual_native_consumer'] and evidence['no_new_native_work']
    assert evidence['same_original_input_roots']
    assert all(row['samples'] == 24 for row in evidence['samples'].values())
    request.node.user_properties.append(('native_consumer_audit_cost', json.dumps(evidence)))

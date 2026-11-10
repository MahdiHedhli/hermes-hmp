"""Late entry DATA drift on the real rooted link selector; no fake admission."""
import pytest
from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('boundary', ('registration', 'checker', 'malformed_entry'))
def test_original_selector_fences_late_entry_namespace(tmp_path, monkeypatch, boundary):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)] + '\nboundary=' + repr(boundary) + '\n' + r'''
from hmp_startup import gateway_entry as em
from hmp_plugin import presentation_native_link as nl
from hmp_plugin import presentation_native_metadata as nm
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
selector=nm._closed_link_engine_origin.__code__
tail=a._native_work_registration_tail.__code__
checker=nl._engine_origin_tail.__code__
original=em._ENTRY_ORIGIN
names=vars(em)
original_record=tuple.__getitem__(original,11)
ledger=entry._scope.native_files.ledger
hooks=[];injections=[];witness=[];effects=[]
class ForeignKey:
    def __hash__(self):return hash('_ENTRY_ORIGIN')
    def __eq__(self,other):
        hooks.append('equality')
        raise AssertionError('foreign entry equality dispatched')
class ForeignEntry:
    def __getattribute__(self,name):
        hooks.append('attribute')
        raise AssertionError('foreign entry attribute dispatched')
foreign_key=ForeignKey()
def observe(frame,event,result):
    if injections:
        if event=='c_call' and any(result is entry._scope.native_files.native.operations[i]
                                   for i in (3,4,5)):
            effects.append(True)
        return
    target=checker if boundary=='checker' else tail
    if (event=='return' and frame.f_code is target and frame.f_back is not None
            and frame.f_back.f_code is selector):
        caller=frame.f_back.f_locals
        registration=caller['registration'];scope=registration.scope
        witness.append(dict(original_entry=em._ENTRY_ORIGIN is original,
            original_started=em._STARTED[5] is original,
            original_cell=em._STARTED[2] is em._CELL,
            original_record=tuple.__getitem__(scope,18) is original_record,
            original_lineage=tuple.__getitem__(registration.lineage,5) is original_record,
            real_owner=registration.owner is caller['owner'],
            original_return=(result is original_record[0]) if boundary=='checker' else result is None))
        injections.append((registration.owner,tuple(ledger.counts),len(ledger.attempts)))
        if boundary=='malformed_entry':names['_ENTRY_ORIGIN']=ForeignEntry()
        else:
            del names['_ENTRY_ORIGIN']
            names[foreign_key]=original
prior=sys.getprofile();assert prior is None and sys.gettrace() is None
sys.setprofile(observe)
failed=False
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as caught:
    failed=caught.failed_owner is retained
finally:
    sys.setprofile(prior)
    if boundary!='malformed_entry' and injections:names.pop(foreign_key)
    names['_ENTRY_ORIGIN']=original
# All evidence assertions are outside the production refusal handlers/callback.
assert len(injections)==len(witness)==1 and all(witness[0].values()),witness
assert failed and retained._failed and not retained._ready and retained._fact_cell is None
owner,counts,attempts=injections[0]
assert owner._failed and not owner._ready
assert hooks==[] and effects==[]
assert tuple(ledger.counts)==counts and len(ledger.attempts)==attempts
assert ledger.inflight==[None]
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

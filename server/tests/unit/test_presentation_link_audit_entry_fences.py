"""Late entry DATA drift on the real rooted link selector; no fake admission."""
import pytest
from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('boundary', ('registration', 'checker', 'malformed_entry', 'live_code', 'live_keyword', 'live_export', 'parent_code', 'parent_keyword', 'reg_scope', 'reg_lineage', 'reg_entry_module', 'reg_getattribute'))
def test_original_selector_fences_late_entry_namespace(tmp_path, monkeypatch, boundary):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)] + '\nboundary=' + repr(boundary) + '\n' + r'''
from hmp_startup import gateway_entry as em
from hmp_startup import link_factory_origin as pa
from hmp_plugin import presentation_native_link as nl
from hmp_plugin import presentation_native_metadata as nm
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
selector=nm._closed_link_engine_origin.__code__
tail=a._native_work_registration_tail.__code__
live_function=nl._engine_live_tail
checker=live_function.__code__
live_id=live_function.__kwdefaults__['_id']
parent_function=pa.current_started
parent_code=parent_function.__code__
parent_type=parent_function.__kwdefaults__['_type']
original=em._ENTRY_ORIGIN
names=vars(em)
original_record=tuple.__getitem__(original,11)
ledger=entry._scope.native_files.ledger
hooks=[];injections=[];witness=[];effects=[];class_restore=[]
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
def foreign(*args,**kwargs):
    raise AssertionError('foreign checker/provenance executed')
def observe(frame,event,result):
    if event=='call' and frame.f_code is foreign.__code__:hooks.append('foreign_checker')
    if injections:
        if event=='c_call' and any(result is entry._scope.native_files.native.operations[i]
                                   for i in (3,4,5)):
            effects.append(True)
        return
    target=(parent_code if boundary.startswith('parent_') else
            checker if boundary=='checker' or boundary.startswith(('live_','reg_')) else tail)
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
            original_return=(result is tuple.__getitem__(original,10) if boundary.startswith('parent_') else
                             result is original_record[0] if boundary=='checker' or boundary.startswith(('live_','reg_')) else result is None)))
        injections.append((registration.owner,tuple(ledger.counts),len(ledger.attempts)))
        if boundary=='malformed_entry':names['_ENTRY_ORIGIN']=ForeignEntry()
        elif boundary=='live_code':live_function.__code__=foreign.__code__
        elif boundary=='live_keyword':live_function.__kwdefaults__['_id']=foreign
        elif boundary=='live_export':nl._engine_live_tail=foreign
        elif boundary=='parent_code':parent_function.__code__=foreign.__code__
        elif boundary=='parent_keyword':parent_function.__kwdefaults__['_type']=foreign
        elif boundary.startswith('reg_'):
            name={'reg_scope':'scope','reg_lineage':'lineage','reg_entry_module':'entry_module',
                  'reg_getattribute':'__getattribute__'}[boundary]
            kind=type(registration);missing=object();previous=vars(kind).get(name,missing)
            class_restore.append((kind,name,previous,missing))
            def trap(*args,**kwargs):
                hooks.append('registration_getter')
                raise AssertionError('changed registration getter dispatched')
            setattr(kind,name,trap if name=='__getattribute__' else property(trap))
        else:
            del names['_ENTRY_ORIGIN']
            names[foreign_key]=original
prior=sys.getprofile();assert prior is None and sys.gettrace() is None
monitor=getattr(sys,'monitoring',None)
if monitor is not None:
    monitor.use_tool_id(5,'hermes-synthetic-selector-entry-fences')
    def arm(code,offset):
        monitor.set_local_events(5,selector,0)
        sys.setprofile(observe)
    monitor.register_callback(5,monitor.events.PY_START,arm)
    monitor.set_local_events(5,selector,monitor.events.PY_START)
else:
    def arm(frame,event,result):
        if event=='call' and frame.f_code is selector:
            sys.setprofile(observe)
    sys.setprofile(arm)
failed=False
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as caught:
    failed=caught.failed_owner is retained
finally:
    sys.setprofile(prior);sys.settrace(None)
    if monitor is not None:
        monitor.set_local_events(5,selector,0)
        monitor.register_callback(5,monitor.events.PY_START,None)
        monitor.free_tool_id(5)
    if boundary in ('registration','checker') and injections:names.pop(foreign_key)
    for kind,name,previous,missing in class_restore:
        if previous is missing:delattr(kind,name)
        else:setattr(kind,name,previous)
    nl._engine_live_tail=live_function
    live_function.__code__=checker
    live_function.__kwdefaults__['_id']=live_id
    parent_function.__code__=parent_code
    parent_function.__kwdefaults__['_type']=parent_type
    names['_ENTRY_ORIGIN']=original
# All evidence assertions are outside the production refusal handlers/callback.
assert len(injections)==len(witness)==1 and all(witness[0].values()),witness
assert failed and retained._failed and not retained._ready and retained._fact_cell is None
owner,counts,attempts=injections[0]
assert owner._failed and not owner._ready
assert hooks==[] and effects==[]
assert len(class_restore)==(1 if boundary.startswith('reg_') else 0)
assert tuple(ledger.counts)==counts and len(ledger.attempts)==attempts
assert ledger.inflight==[None]
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

"""Started entry field checks are neither actor observations nor root authority."""
import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('binding', [None, (), (None,), (None,) * 3, (None,) * 4])
def test_foreign_binding_is_not_started_entry_data(binding):
    assert artifacts._entry_graph_mirrors(binding) is False


def test_actual_started_entry_invocation_and_storage_fields(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += r'''
from hmp_startup import gateway_entry as entry_module
from hmp_plugin import presentation_gateway_activation as activation_module
import os,threading
binding=GatewayEntryOwner._retained_binding(entry);scope,cell,started=binding
probe=a._entry_graph_mirrors;ledger=scope.native_file_ledger
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
calls=[];foreign=[];rows=[]
actors=(os.getpid,os.geteuid,threading.get_ident)
def observe(frame,event,callee):
    if event=='c_call' and any(callee is actor for actor in actors):calls.append(True)
assert sys.getprofile() is None
sys.setprofile(observe)
try:
    assert probe(binding) is True
    for role,state,keys in (
        ('owner',vars(entry),('_scope','_ready','_failed','_started_cell','_activation','_bootstrap')),
        ('module',vars(entry_module),('_OWNER','_CELL','_STARTED','_START_ATTEMPTED','_ENTRY_ORIGIN')),
        ('activation',vars(activation_module),('_ENTRY_CELL',)),
        ('main',vars(scope.main),('__file__',)),
    ):
        for key in keys:
            old=state[key];state[key]=object()
            try:assert probe(binding) is False,(role,key,'replacement')
            finally:state[key]=old
            assert probe(binding) is True
            del state[key]
            try:assert probe(binding) is False,(role,key,'missing')
            finally:state[key]=old
            assert probe(binding) is True
            rows.extend(((role,key,'replacement'),(role,key,'missing')))
    copied=tuple(list(cell))
    assert copied is not cell and probe((scope,copied,started)) is False
    copied=tuple(list(started))
    assert copied is not started and probe((scope,cell,copied)) is False
    short=tuple.__new__(entry_module._Invocation,())
    assert probe((short,cell,started)) is False
    for values,index in ((ledger.counts,0),(ledger.counts,1),(ledger.inflight,0),
                         (ledger.failed,0),(ledger.phase.current,0),(ledger.phase.result,0)):
        old=values[index];values[index]=object()
        try:assert probe(binding) is False
        finally:values[index]=old
        assert probe(binding) is True
    # Failed ledger is still valid representation DATA for cleanup, not a live
    # effect allowance. This component must not be interpreted as permission.
    old=ledger.failed[0];ledger.failed[0]=True
    try:assert probe(binding) is True
    finally:ledger.failed[0]=old
    changed=scope._replace(native_files=scope.native_files._replace(entry=object()))
    changed_cell=(entry,changed);changed_started=(entry,changed,changed_cell,*started[3:])
    entry._scope=changed;entry._started_cell=entry_module._STARTED=changed_started
    entry_module._CELL=changed_cell
    try:assert probe((changed,changed_cell,changed_started)) is False
    finally:
        entry._scope=scope;entry._started_cell=entry_module._STARTED=started;entry_module._CELL=cell
    assert probe(binding) is True
    class ForeignArgument(str):
        def __eq__(self,other):
            foreign.append('argv.eq');raise AssertionError('foreign argv equality')
    old=sys.argv[0];sys.argv[0]=ForeignArgument(old)
    try:assert probe(binding) is False
    finally:sys.argv[0]=old
    assert probe(binding) is True
    armed=[False]
    class ForeignKey:
        def __hash__(self):return hash('_OWNER')
        def __eq__(self,other):
            if armed[0]:
                foreign.append('key.eq');raise AssertionError('foreign namespace equality')
            return False
    state=vars(entry_module);old=state.pop('_OWNER');key=ForeignKey();state[key]=old;armed[0]=True
    try:assert probe(binding) is False
    finally:
        armed[0]=False;del state[key];state['_OWNER']=old
    assert probe(binding) is True
finally:sys.setprofile(None)
assert calls==[] and foreign==[] and len(rows)==26,(calls,foreign,len(rows))
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
after=GatewayEntryOwner._retained_binding(entry)
assert all(old is new for old,new in zip(binding,after,strict=True))
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

"""Operator retained-field checks do not call the native default-root API."""
import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('binding', [None, (), (None,) * 3, (None,) * 4, (None,) * 5])
def test_bad_binding_is_not_approval_data(binding):
    assert artifacts._approval_graph_mirrors(binding) is False


def test_actual_operator_owner_api_read_chain_mutations(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += r'''
from hmp_startup import gateway_approval as approval_module
probe=a._approval_graph_mirrors
binding=GatewayApprovalOwner._retained_binding(approval)
scope,cell,root,fact=binding
source=scope.parent
ledger=entry._scope.native_files.ledger
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
calls=[];foreign=[];rows=[]
def observe(frame,event,callee):
    if event=='call' and frame.f_code is source.code:calls.append(True)
assert sys.getprofile() is None
sys.setprofile(observe)
try:
    assert probe(binding) is True
    mutations=[
        ('owner',vars(approval),('_origin','_scope','_cell','_root_cell','_ready','_failed',
                                '_unknown','_reading','_fact_cell','_data','_count_cell',
                                '_bytes_read','_buffer')),
        ('activation',vars(scope.activation),('_scope','_retired','_uncertain',
                                             '_approval_owner','_approval_cell','_approval_fact_cell')),
        ('module',vars(approval_module),('_OWNER','_CELL','_ROOT','_FACT')),
        ('api',source.namespace,('get_default_hermes_root','__file__','__spec__')),
        ('spec',vars(source.spec),('origin','loader')),
    ]
    for i,effect in enumerate(fact[4].reads):
        mutations.append(('read'+str(i),vars(effect),('before','after','returned','unknown')))
    for role,state,keys in mutations:
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
    # The pointer checks must not silently become content-equality joins.
    copied=tuple(list(binding[2]));bad=(scope,cell,copied,fact)
    assert copied is not root and probe(bad) is False
    buffer=approval._buffer;buffer.extend(b'x')
    try:assert probe(binding) is False
    finally:buffer.clear()
    assert probe(binding) is True
    # Fence source tuple storage even when Scope owner mirrors are coherent.
    short=tuple.__new__(approval_module._RootSource,())
    changed_scope=scope._replace(parent=short)
    changed_cell=(approval,changed_scope)
    changed_root=(scope.activation,approval,changed_scope,root[3])
    changed_fact=(approval,changed_scope,*fact[2:])
    approval._scope=approval._origin=changed_scope
    approval._cell=approval_module._CELL=changed_cell
    approval._root_cell=approval_module._ROOT=scope.activation._approval_cell=changed_root
    approval._fact_cell=approval_module._FACT=scope.activation._approval_fact_cell=changed_fact
    try:assert probe((changed_scope,changed_cell,changed_root,changed_fact)) is False
    finally:
        approval._scope=approval._origin=scope;approval._cell=approval_module._CELL=cell
        approval._root_cell=approval_module._ROOT=scope.activation._approval_cell=root
        approval._fact_cell=approval_module._FACT=scope.activation._approval_fact_cell=fact
    assert probe(binding) is True
    armed=[False]
    class ForeignKey:
        def __hash__(self):return hash('get_default_hermes_root')
        def __eq__(self,other):
            if armed[0]:
                foreign.append(True);raise AssertionError('foreign API key equality')
            return False
    state=source.namespace;key=ForeignKey();old=state.pop('get_default_hermes_root');state[key]=old
    armed[0]=True
    try:assert probe(binding) is False
    finally:
        armed[0]=False;del state[key];state['get_default_hermes_root']=old
    assert probe(binding) is True
    # CodeType.replace preserves a str subclass in co_filename. Build coherent
    # field DATA so the filename comparison is reached, rather than a preceding
    # mismatched function/code or root pointer hiding foreign equality.
    class ForeignFilename(str):
        def __eq__(self,other):
            foreign.append('filename.eq');raise AssertionError('foreign filename equality')
        def __ne__(self,other):
            foreign.append('filename.ne');raise AssertionError('foreign filename inequality')
    from types import FunctionType
    bad_code=source.code.replace(co_filename=ForeignFilename(source.native_file))
    assert type(bad_code.co_filename) is ForeignFilename
    bad_function=FunctionType(bad_code,source.namespace,source.function.__name__,
                              source.function.__defaults__,source.function.__closure__)
    bad_source=source._replace(function=bad_function,code=bad_code)
    bad_scope=scope._replace(parent=bad_source)
    bad_cell=(approval,bad_scope)
    bad_root=(scope.activation,approval,bad_scope,root[3])
    mapping={}
    def rehome(value):
        if id(value) not in mapping:mapping[id(value)]=(value[0],bad_scope,value[2])
        return mapping[id(value)]
    bad_count=rehome(fact[3]);saved_effects=[]
    for effect in fact[4].reads:
        saved_effects.append((effect,effect.before,effect.after))
        effect.before=rehome(effect.before);effect.after=rehome(effect.after)
    bad_receipt=fact[4]._replace(scope=bad_scope,count=bad_count)
    bad_fact=(approval,bad_scope,fact[2],bad_count,bad_receipt,fact[5])
    approval._scope=approval._origin=bad_scope;approval._cell=approval_module._CELL=bad_cell
    approval._root_cell=approval_module._ROOT=scope.activation._approval_cell=bad_root
    approval._count_cell=bad_count
    approval._fact_cell=approval_module._FACT=scope.activation._approval_fact_cell=bad_fact
    source.namespace['get_default_hermes_root']=bad_function
    try:
        assert probe((bad_scope,bad_cell,bad_root,bad_fact)) is False
        refused=[]
        try:approval_module._api_state(bad_source)
        except approval_module.GatewayApprovalError:refused.append(True)
        assert refused==[True]
    finally:
        source.namespace['get_default_hermes_root']=source.function
        approval._scope=approval._origin=scope;approval._cell=approval_module._CELL=cell
        approval._root_cell=approval_module._ROOT=scope.activation._approval_cell=root
        approval._count_cell=fact[3]
        approval._fact_cell=approval_module._FACT=scope.activation._approval_fact_cell=fact
        for effect,before,after in saved_effects:effect.before=before;effect.after=after
    assert foreign==[] and probe(binding) is True
finally:sys.setprofile(None)
assert calls==[] and foreign==[]
assert len(rows)==56+8*len(fact[4].reads),len(rows)
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
after=GatewayApprovalOwner._retained_binding(approval)
assert all(old is new for old,new in zip(binding,after,strict=True))
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

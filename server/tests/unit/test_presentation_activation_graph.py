"""Settled activation field DATA, with no bootstrap or actor observations."""
import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('owner', [None, (), (None,), object(), False])
def test_foreign_owner_is_not_activation_data(owner):
    assert artifacts._activation_graph_mirrors(owner) is False


def test_actual_activation_fields_and_origins_without_calls(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += r'''
from hmp_plugin import presentation_gateway_activation as activation_module
import os,threading
owner=entry._activation;scope=owner._scope;cell=activation_module._ENTRY_CELL
probe=a._activation_graph_mirrors
assert activation_module.GatewayActivationOwner.current(owner) is owner
ledger=entry._scope.native_files.ledger
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
calls=[];foreign=[];rows=[]
actors=(os.getpid,os.geteuid,threading.get_ident)
def observe(frame,event,callee):
    if event=='c_call' and any(callee is actor for actor in actors):calls.append('actor')
    if event=='call' and frame.f_code is scope.code:calls.append('bootstrap')
assert sys.getprofile() is None
sys.setprofile(observe)
try:
    assert probe(owner) is True
    observed=next(row for row in scope.origins if type(row) is activation_module._ModuleOrigin
                  and type(row.file) is str and row.spec is not None and type(row.origin) is str)
    mutations=[
        ('owner',vars(owner),('_scope','_ready','_retired','_uncertain','_capturing')),
        ('module',vars(activation_module),('_ENTRY_OWNER','_ENTRY_CELL')),
        ('bootstrap',vars(scope.pm),('activate_dependencies',)),
        ('origin',vars(observed.module),('__file__','__spec__')),
        ('spec',vars(observed.spec),('origin',)),
        ('typing',vars(activation_module),('_TYPING','_TYPING_NAMESPACE','_TYPING_MEMBERS',
                                           '_TYPING_ENTRIES','_TYPING_ALIASES','_MISSING_ALIAS')),
    ]
    for role,state,keys in mutations:
        for key in keys:
            old=state[key];state[key]=object()
            # A replaced missing sentinel can be observationally irrelevant
            # when all observed members/entries exist; test its absence below.
            try:
                if key=='_MISSING_ALIAS':
                    missing=any(value is old for _,value in
                                activation_module._TYPING_MEMBERS+activation_module._TYPING_ENTRIES)
                    assert probe(owner) is (not missing)
                else:assert probe(owner) is False,(role,key,'replacement')
            finally:state[key]=old
            assert probe(owner) is True
            del state[key]
            try:assert probe(owner) is False,(role,key,'missing')
            finally:state[key]=old
            assert probe(owner) is True
            rows.append((role,key))
    paths=scope.paths;paths.append('/SYNTHETIC_EXTRA_IMPORT_PATH')
    try:assert probe(owner) is False
    finally:paths.pop()
    assert probe(owner) is True
    old=paths[0];paths[0]=object()
    try:assert probe(owner) is False
    finally:paths[0]=old
    assert probe(owner) is True
    armed=[False]
    class ForeignKey:
        def __init__(self,name):self.name=name
        def __hash__(self):return hash(self.name)
        def __eq__(self,other):
            if armed[0]:
                foreign.append('key.eq');raise AssertionError('foreign dictionary equality')
            return False
    for state,name in ((sys.modules,'hmp_plugin.presentation_gateway_activation'),
                       (vars(scope.pm),'activate_dependencies'),
                       (vars(owner),'_scope')):
        old=state.pop(name);key=ForeignKey(name);state[key]=old;armed[0]=True
        try:assert probe(owner) is False
        finally:
            armed[0]=False;del state[key];state[name]=old
        assert probe(owner) is True
    class ForeignName(str):
        __hash__=str.__hash__
        def __eq__(self,other):
            foreign.append('name.eq');raise AssertionError('foreign module name equality')
    index=scope.origins.index(observed)
    for replacement in (observed._replace(name=ForeignName(observed.name)),
                        tuple.__new__(activation_module._ModuleOrigin,())):
        changed=list(scope.origins);changed[index]=replacement
        changed_scope=scope._replace(origins=tuple(changed))
        owner._scope=changed_scope;activation_module._ENTRY_CELL=(owner,changed_scope)
        try:assert probe(owner) is False
        finally:owner._scope=scope;activation_module._ENTRY_CELL=cell
        assert probe(owner) is True
    short=tuple.__new__(activation_module._ActivationScope,())
    owner._scope=short;activation_module._ENTRY_CELL=(owner,short)
    try:assert probe(owner) is False
    finally:owner._scope=scope;activation_module._ENTRY_CELL=cell
    assert probe(owner) is True
finally:sys.setprofile(None)
assert calls==[] and foreign==[]
assert len(rows)==17,len(rows)
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert activation_module.GatewayActivationOwner.current(owner) is owner
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

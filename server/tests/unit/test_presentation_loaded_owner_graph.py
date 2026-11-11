"""Unintegrated shared-node comparisons; not original-root or guard acceptance."""
import json

import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('left,right', [
    (None, None), ((), ()), ((None,) * 4, (None,) * 6),
    ((None,) * 5, (None,) * 5), ((None,) * 5, (None,) * 6),
    ((None,) * 4 + ((),), (None,) * 6),
])
def test_malformed_bindings_are_not_live_node_matches(left, right):
    assert artifacts._loaded_owner_graph_mirrors(left, right) is False


def test_actual_shared_node_field_mutations_have_no_native_effects(tmp_path, monkeypatch, request):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += r'''
probe=a._loaded_owner_graph_mirrors
pb=GatewayPackageOwner._retained_binding(plugin)
rb=GatewayRecipeOwner._retained_binding(recipe)
ledger=entry._scope.native_files.ledger
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert probe(pb,rb) is True
rows=[];foreign=[]
# Each mutation is applied only after canonical real loaded owners and bindings
# exist. No original validator may mask this component's result during a case.
for role,owner in (('package',plugin),('recipe',recipe),('selection',configuration)):
    state=vars(owner)
    for key,value in (('_ready',False),('_ready',1),('_failed',True),('_unknown',True),
                      ('_reading',True),('_scope',object()),('_origin',object()),
                      ('_cell',object()),('_root_cell',object()),('_count_cell',object()),
                      ('_bytes_read',True),('_bytes_read',owner._bytes_read+1)):
        old=state[key];state[key]=value
        try:assert probe(pb,rb) is False,(role,key)
        finally:state[key]=old
        assert probe(pb,rb) is True
        rows.append((role,key))
    if role!='package':
        original_buffer=state['_buffer'];state['_buffer']=bytearray(b'x')
        try:assert probe(pb,rb) is False
        finally:state['_buffer']=original_buffer
        rows.append((role,'_buffer_pointer'))
        original_buffer.extend(b'x')
        try:assert probe(pb,rb) is False
        finally:original_buffer.clear()
        rows.append((role,'_buffer_contents'))
    if role=='recipe':
        old=state['_active'];state['_active']=object()
        try:assert probe(pb,rb) is False
        finally:state['_active']=old
        rows.append((role,'_active'))
    required=('_ready','_failed','_unknown','_reading','_origin','_scope',
              '_cell','_root_cell','_count_cell','_bytes_read')
    required+=({'package':('_fact_cell','_fact'),
                'recipe':('_plan_cell','_fact_cell','_active','_buffer'),
                'selection':('_selection_cell','_selection','_buffer')}[role])
    for key in required:
        old=state.pop(key)
        try:assert probe(pb,rb) is False,(role,'missing',key)
        finally:state[key]=old
        assert probe(pb,rb) is True
        rows.append((role,'missing:'+key))
# Canonical class getters can be changed without being executed by this DATA
# projection. True here does NOT certify class/code provenance; a future caller
# must independently authenticate those before selecting any reduced guard.
old=GatewayPackageOwner.__getattribute__
def forbidden_getter(self,name):
    foreign.append(name);raise AssertionError('foreign instance getter')
GatewayPackageOwner.__getattribute__=forbidden_getter
try:assert probe(pb,rb) is True
finally:GatewayPackageOwner.__getattribute__=old
assert foreign==[]

# A missing real key plus a colliding foreign key would execute equality if
# dictionary lookups occurred before the exact-string key fence.
armed=[False]
class ForeignKey:
    def __hash__(self):return hash('_fact_cell')
    def __eq__(self,other):
        if armed[0]:
            foreign.append('foreign_key');raise AssertionError('foreign equality')
        return False
state=vars(plugin);fact=state.pop('_fact_cell');key=ForeignKey();state[key]=None
foreign.clear();armed[0]=True
try:
    assert probe(pb,rb) is False
    assert foreign==[]
finally:
    armed[0]=False
    del state[key];state['_fact_cell']=fact
assert foreign==[]
assert GatewayPackageOwner._retained_binding(plugin)[0] is pb[0]
assert GatewayRecipeOwner._retained_binding(recipe)[0] is rb[0]
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert probe(pb,rb) is True
report={'actual_loaded_owners':True,'field_fault_rows':rows,'foreign_calls':foreign,
        'native_work_unchanged':True,'production_integration':False,
        'full_graph_or_original_root_qualification':False}
p=base/'owner-graph-mirror-report.json';p.write_text(json.dumps(report));p.chmod(0o600)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
    report = json.loads((tmp_path / 'owner-graph-mirror-report.json').read_text())
    assert len(report['field_fault_rows']) == 80
    assert report['native_work_unchanged'] and report['foreign_calls'] == []
    assert report['production_integration'] is False
    request.node.user_properties.append(('shared_owner_graph_mirrors', json.dumps(report)))

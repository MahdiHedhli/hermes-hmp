"""Retained cache field comparisons, without admission or live cwd authority."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('dependent', [False, True])
def test_actual_cache_fields_refuse_changes_without_native_calls(tmp_path, monkeypatch, dependent):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    if dependent:
        script = script.replace('entry = GatewayEntryOwner.start()',
                                'physical_body=Path(__file__).read_bytes()\n'
                                '__file__="/SYNTHETIC_HMP_ROOT_SOURCE.py"\n'
                                'entry = GatewayEntryOwner.start()', 1)
        script = script.replace('wrapper_body = wrapper_path.read_bytes()',
                                'wrapper_body = physical_body', 1)
    script += '\ndependent=' + repr(dependent) + '\n'
    script += r'''
from hmp_startup import cache_context as cache
import os
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
inputs=retained._inputs;slot=inputs.cache_context_slot;fact=slot[0];owner=fact[0]
probe=a._cache_context_graph_mirrors
assert owner._source.requires_cwd is dependent
assert cache.CacheContextOwner.retained_binding(owner) is fact
ledger=entry._scope.native_files.ledger
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
calls=[];foreign=[];rows=[]
getter=os.getcwd
def observe(frame,event,callee):
    if event=='c_call' and callee is getter:calls.append(True)
assert sys.getprofile() is None
sys.setprofile(observe)
try:
    assert probe(retained) is True
    for role,state,keys in (
        ('snapshot',vars(retained),('_inputs','_root_cell','_cache_context_cell','_failed','_unknown')),
        ('cache',vars(owner),('_source','_root','_failed','_retired','_ready','_fact','_cwd','_rows')),
        ('activation',vars(recipe._scope.activation),('_entry_files_owner','_entry_files_cell')),
        ('module',vars(cache),('_OWNER','_ROOT','_FACT')),
    ):
        for key in keys:
            old=state[key]
            state[key]=object()
            try:assert probe(retained) is False,(role,key,'replacement')
            finally:state[key]=old
            assert probe(retained) is True
            del state[key]
            try:assert probe(retained) is False,(role,key,'missing')
            finally:state[key]=old
            assert probe(retained) is True
            rows.extend(((role,key,'replacement'),(role,key,'missing')))
    for replacement in (None,(),(None,)*3,tuple(list(fact))):
        slot[0]=replacement
        try:assert probe(retained) is False
        finally:slot[0]=fact
        assert probe(retained) is True
        rows.append(('slot','fact'))
    source=owner._source
    for replacement in (tuple.__new__(cache._ContextSource,()),source._replace(getter=object())):
        # Replace both root mirrors coherently: an exact schema/getter check
        # still has to refuse. This does not prove original-source custody.
        root=(owner,replacement);changed=(owner,root,owner._cwd,owner._rows)
        owner._source=replacement;owner._root=cache._ROOT=retained._cache_context_cell=root
        owner._fact=cache._FACT=slot[0]=changed
        try:assert probe(retained) is False
        finally:
            owner._source=source;owner._root=cache._ROOT=retained._cache_context_cell=fact[1]
            owner._fact=cache._FACT=slot[0]=fact
        assert probe(retained) is True
        rows.append(('source','coherent_malformed'))
    armed=[False]
    class ForeignKey:
        def __hash__(self):return hash('_cwd')
        def __eq__(self,other):
            if armed[0]:
                foreign.append(True);raise AssertionError('foreign dictionary equality')
            return False
    state=vars(owner);old=state.pop('_cwd');key=ForeignKey();state[key]=old
    armed[0]=True
    try:assert probe(retained) is False
    finally:
        armed[0]=False;del state[key];state['_cwd']=old
    assert probe(retained) is True
finally:sys.setprofile(None)
assert calls==[] and foreign==[]
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert cache.CacheContextOwner.retained_binding(owner) is fact
assert len(rows)==42,len(rows)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

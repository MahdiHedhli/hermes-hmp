"""Original-layout mutable audit and inline fidelity; not native admission."""
import ast
import copy
import gc
from pathlib import Path
import sys
import textwrap

import pytest
from hmp_startup import retained_binding_origin as selected
from hmp_startup import gateway_approval as approval
from hmp_plugin import presentation_gateway_package as package
from hmp_plugin import presentation_gateway_recipe as recipe


@pytest.mark.parametrize('fault', (
    'module_extra', 'module_missing', 'module_value', 'module_key',
    'class_extra', 'class_missing_none', 'class_member', 'class_dispatch', 'class_bases',
    'code', 'defaults', 'kw_new', 'kw_value', 'kw_extra', 'kw_missing', 'kw_key',
    'closure_cell', 'alias',
))
def test_previous_live_success_does_not_cache_mutable_state(monkeypatch, fault):
    kind=package.GatewayPackageOwner
    if fault=='class_missing_none':monkeypatch.setattr(kind,'synthetic_none',None,raising=False)
    packet,layout,_=selected.capture_bound()
    held=selected.current_live
    assert held(packet,layout) is packet
    calls=[];restore=[];restore_attributes=[]
    def foreign(*args,**kwargs):calls.append('call');raise AssertionError('foreign dependency executed')
    class Collision:
        def __init__(self,target):self.target=target
        def __hash__(self):calls.append('hash');return hash(self.target)
        def __eq__(self,other):calls.append('eq');return False
    if fault=='module_extra':monkeypatch.setattr(package,'synthetic_new',None,raising=False)
    elif fault=='module_missing':monkeypatch.delattr(package,'_require')
    elif fault=='module_value':monkeypatch.setattr(package,'_require',foreign)
    elif fault=='module_key':
        names=vars(package);restore.append((names,dict(names)))
        names.pop('_require');names[Collision('_require')]=None
    elif fault=='class_extra':monkeypatch.setattr(kind,'synthetic_new',None,raising=False)
    elif fault=='class_missing_none':
        monkeypatch.delattr(kind,'synthetic_none');monkeypatch.setattr(kind,'synthetic_alias',None,raising=False)
    elif fault=='class_member':monkeypatch.setattr(kind,'_retained_binding',foreign)
    elif fault=='class_dispatch':monkeypatch.setattr(kind,'__getattribute__',foreign,raising=False)
    elif fault=='class_bases':
        bases=tuple(list(kind.__bases__));assert bases is not kind.__bases__
        restore_attributes.append((kind,'__bases__',kind.__bases__))
        kind.__bases__=bases;assert kind.__bases__ is bases
    elif fault=='code':
        def foreign_code(*args,**kwargs):raise AssertionError('changed code executed')
        assert foreign_code.__closure__ is None
        monkeypatch.setattr(package._require,'__code__',foreign_code.__code__)
    elif fault=='defaults':monkeypatch.setattr(package._require,'__defaults__',(object(),))
    elif fault=='kw_new':monkeypatch.setattr(package._require,'__kwdefaults__',{'synthetic':None})
    elif fault.startswith('kw_'):
        names=approval._api_state.__kwdefaults__;assert '_spec_dict' in names
        restore.append((names,dict(names)))
        if fault=='kw_value':names['_spec_dict']=foreign
        elif fault=='kw_extra':names['synthetic']=None
        elif fault=='kw_missing':names.pop('_spec_dict')
        else:names.pop('_spec_dict');names[Collision('_spec_dict')]=None
    elif fault=='closure_cell':
        rows=[row for row in packet[5] if row[6] is not None]
        assert rows and rows[0][6]
        cell=rows[0][6][0];monkeypatch.setattr(cell,'cell_contents',object())
    else:monkeypatch.setattr(recipe,'GatewayActivationOwner',foreign)
    calls.clear()
    try:
        with pytest.raises(RuntimeError) as caught:held(packet,layout)
        assert type(caught.value) is RuntimeError
        assert caught.value.args==('BI1_RETAINED_HELPER_ORIGIN_REFUSED',)
        observed=tuple(calls)
    finally:
        for names,snapshot in restore:names.clear();names.update(snapshot)
        for obj,name,value in restore_attributes:setattr(obj,name,value)
    assert observed==()


def test_live_private_module_index_refuses_gc_inserted_collision_without_hash_or_eq():
    packet,layout,_=selected.capture_bound();held=selected.current_live
    assert held(packet,layout) is packet
    code=held.__code__;lines=Path(code.co_filename).read_text().splitlines()
    end=max(line for _,_,line in code.co_lines() if line is not None)
    boundary=[i+1 for i in range(code.co_firstlineno-1,end) if 'valid, observed, live_seen =' in lines[i]]
    assert len(boundary)==1
    namespace=vars(package);snapshot=dict(namespace);calls=[];fired=[];armed=False
    class Collision:
        def __hash__(self):calls.append('hash');return hash('_require')
        def __eq__(self,other):calls.append('eq');return False
    key=Collision()
    def on_gc(phase,info):
        if phase=='start' and armed and not fired:
            namespace.pop('_require');namespace[key]=None;calls.clear();fired.append(True)
    def trace(frame,event,value):
        nonlocal armed
        if frame.f_code is not code:return None
        if (event=='line' and frame.f_lineno==boundary[0] and not fired
                and frame.f_locals.get('namespace') is namespace):
            armed=True;gc.collect();armed=False
        return trace
    assert sys.gettrace() is None
    gc.callbacks.append(on_gc);sys.settrace(trace)
    try:
        with pytest.raises(RuntimeError) as caught:held(packet,layout)
        assert type(caught.value) is RuntimeError and caught.value.args==('BI1_RETAINED_HELPER_ORIGIN_REFUSED',)
        observed=tuple(calls)
    finally:
        sys.settrace(None);gc.callbacks.remove(on_gc);namespace.clear();namespace.update(snapshot)
    assert fired==[True] and observed==()


def _canonical_body(body, names, scope=False):
    class Canonical(ast.NodeTransformer):
        def visit_Name(self,node):
            name=names.get(node.id,node.id)
            return ast.copy_location(ast.Name(id=name,ctx=node.ctx),node)
        def visit_Raise(self,node):
            assert isinstance(node.cause,ast.Constant) and node.cause.value is None
            if scope:assert isinstance(node.exc,ast.Name) and node.exc.id=='refusal'
            else:
                assert isinstance(node.exc,ast.Call) and isinstance(node.exc.func,ast.Name) and node.exc.func.id=='_error'
                assert len(node.exc.args)==1 and isinstance(node.exc.args[0],ast.Constant)
                assert node.exc.args[0].value in ('BI1_LINK_FACTORY_ORIGIN_REFUSED','BI1_RETAINED_HELPER_ORIGIN_REFUSED')
            return ast.Raise(exc=ast.Name(id='REFUSE',ctx=ast.Load()),cause=ast.Constant(None))
    tree=Canonical().visit(ast.Module(body=copy.deepcopy(body),type_ignores=[]))
    return ast.dump(tree,include_attributes=False)


@pytest.mark.parametrize('target', ('parent','scope_first','scope_second'))
def test_inline_mutable_body_exactly_matches_reviewed_live_body(target):
    root=Path(selected.__file__).resolve().parents[1]
    fn=next(n for n in ast.parse(Path(selected.__file__).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='current_live')
    expected=_canonical_body(fn.body[1:-1],{})
    locals_={n.id for n in ast.walk(fn) if isinstance(n,ast.Name)}
    if target=='parent':
        text=(root/'hmp_startup/link_factory_origin.py').read_text().split('def current_started(',1)[1]
        start=text.index('    if _type(helper_bound_layout)')
        stop=text.index('    if (_type(started_owner) is not started_owner_kind',start)
        source=textwrap.dedent(text[start:stop]);prefix='helper_final_'
        names={'_type':'type','_vars':'vars','_tuple':'tuple','_len':'len','_dict':'dict','_str':'str','_any':'any','_all':'all','_zip':'zip','_set':'set','_module':'ModuleType','_function':'FunctionType','_cell':'CellType','_error':'RuntimeError','_value_error':'ValueError','helper_packet':'packet','helper_bound_layout':'bound_layout','helper_data_modules':'_MODULES','helper_data_classes':'_CLASSES','helper_data_functions':'_FUNCTIONS','helper_data_live_globals':'_LIVE_GLOBALS'}
    else:
        text=(root/'hmp_plugin/presentation_startup_artifacts.py').read_text()
        starts=[];pos=0
        while True:
            pos=text.find('                if link_raw_type(link_helper_layout)',pos)
            if pos<0:break
            starts.append(pos);pos+=1
        assert len(starts)==2
        start=starts[0 if target=='scope_first' else 1];stop=text.index('                link_pin_encoding_origin =',start)
        source=textwrap.dedent(text[start:stop]);prefix='link_hdata_'
        names={'link_raw_type':'type','link_raw_vars':'vars','link_raw_tuple':'tuple','link_raw_len':'len','link_raw_dict':'dict','link_raw_str':'str','link_raw_any':'any','link_helper_all':'all','link_raw_zip':'zip','link_helper_set':'set','link_raw_module':'ModuleType','link_raw_function':'FunctionType','link_raw_cell':'CellType','link_helper_runtime_error':'RuntimeError','link_helper_value_error':'ValueError','link_hdata_packet':'packet','link_helper_layout':'bound_layout','link_helper_modules':'_MODULES','link_helper_classes':'_CLASSES','link_helper_functions':'_FUNCTIONS','link_helper_live_globals':'_LIVE_GLOBALS'}
    for name in locals_:names.setdefault(prefix+name,name)
    assert _canonical_body(ast.parse(source).body,names,target!='parent')==expected

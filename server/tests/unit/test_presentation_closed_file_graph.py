"""Unintegrated native close DATA projection, never original receipt authority."""
import ast
import copy
import json

import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('value', [None, (), object(), 1, True, b'x'])
def test_wrong_descriptor_family_refuses_without_dispatch(value):
    assert artifacts._closed_file_graph_mirrors(value, None) is False


@pytest.mark.parametrize('width', [0, 1, 2, 4])
def test_short_or_oversized_native_descriptor_storage_refuses(width):
    value = tuple.__new__(artifacts._NativeOpenedDescriptor, (None,) * width)
    assert artifacts._closed_file_graph_mirrors(value, None) is False


def test_real_closed_receipt_fields_and_constructed_data_limit(tmp_path, monkeypatch, request):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += r'''
probe=a._closed_file_graph_mirrors
rows=[row for row in plugin._origin.records if type(row) is a._NativeOpenedDescriptor]
assert rows,'actual source-hashed package must have native descriptor receipts'
descriptor=rows[0];allocation=descriptor.allocation;close=descriptor.close
ledger=allocation.ledger
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert a._native_descriptor_closed(descriptor,ledger) is True
assert probe(descriptor,ledger) is True
scope=allocation.scope
scope_probe=a._scope_file_graph_mirrors
pb=GatewayPackageOwner._retained_binding(plugin)
rb=GatewayRecipeOwner._retained_binding(recipe)
assert scope_probe(scope) is True
assert a._loaded_owner_graph_mirrors(pb,rb) is True
faults=[]
for name,container,index,replacements in (
    ('open_raw',allocation.raw,0,(None,object())),
    ('open_result',allocation.result,0,(None,(),(object(),descriptor),(allocation,object()))),
    ('refused',allocation.refused,0,(True,1,None)),
    ('close_started',close.state,0,(False,1,None)),
    ('close_unknown',close.state,1,(True,0,None)),
    ('open_slot',close.open_slot,0,(None,object())),
    ('close_raw',close.raw,0,(close.unset,object())),
    ('close_result',close.result,0,(None,(),(object(),descriptor.fd,None),
                                  (close,object(),None),(close,descriptor.fd,object()))),
    ('attempt',ledger.attempts,allocation.index,(None,object())),
):
    original=container[index]
    for changed in replacements:
        container[index]=changed
        try:
            assert probe(descriptor,ledger) is False,name
            assert scope_probe(scope) is False,name
            assert a._loaded_owner_graph_mirrors(pb,rb) is False,name
            try:a._native_descriptor_closed(descriptor,ledger)
            except a.ArtifactObservationError:pass
            else:raise AssertionError(('original validator accepted changed field',name))
        finally:container[index]=original
        assert probe(descriptor,ledger) is True
        assert scope_probe(scope) is True
        assert a._loaded_owner_graph_mirrors(pb,rb) is True
        faults.append(name)
for name,container in (('open_raw_shape',allocation.raw),('open_result_shape',allocation.result),
                       ('refused_shape',allocation.refused),('state_shape',close.state),
                       ('closed_raw_shape',close.raw),('closed_result_shape',close.result),
                       ('open_slot_shape',close.open_slot)):
    old=container[:];container.clear()
    try:
        assert probe(descriptor,ledger) is False,name
        assert scope_probe(scope) is False,name
        assert a._loaded_owner_graph_mirrors(pb,rb) is False,name
    finally:container[:]=old
    assert probe(descriptor,ledger) is True
    assert scope_probe(scope) is True
    assert a._loaded_owner_graph_mirrors(pb,rb) is True
    faults.append(name)
assert probe(descriptor._replace(),ledger) is False
assert probe(descriptor,object()) is False
assert probe(descriptor._replace(allocation=object()),ledger) is False
assert probe(descriptor._replace(close=object()),ledger) is False
# Forge only DATA around the genuine closed fd: no native open/close/actor call.
# Both field validators can match this coherent new graph if the caller supplies
# its fake ledger as 'original'. This demonstrates why neither is authority.
fake_attempts=[]
fake_ledger=ledger._replace(attempts=fake_attempts)
reg=allocation.registration._replace(native_ledger=fake_ledger)
slot=[None]
fake_close=close._replace(registration=reg,ledger=fake_ledger,open_slot=slot,result=[None])
fake_allocation=allocation._replace(registration=reg,ledger=fake_ledger,index=0,
                                  result=[None],close=fake_close)
fake_descriptor=descriptor._replace(allocation=fake_allocation,close=fake_close)
slot[0]=fake_allocation;fake_attempts.append(fake_allocation)
fake_allocation.result[0]=(fake_allocation,fake_descriptor)
fake_close.result[0]=(fake_close,fake_descriptor.fd,None)
assert fake_ledger is not ledger and fake_allocation is not allocation
assert probe(fake_descriptor,fake_ledger) is True
assert a._native_descriptor_closed(fake_descriptor,fake_ledger) is True
assert probe(fake_descriptor,ledger) is False
# Scope closure binds the lineage's actual ledger, not a supplied fake ledger.
slot=scope.native_registration_slot;original_registration=slot[0]
for changed in (None,original_registration._replace(native_ledger=fake_ledger)):
    slot[0]=changed
    try:
        assert scope_probe(scope) is False
        assert a._loaded_owner_graph_mirrors(pb,rb) is False
    finally:slot[0]=original_registration
    assert scope_probe(scope) is True
# Unknown record protocols are not entered before the exact native type fence.
record_index=next(i for i,value in enumerate(scope.records) if value is descriptor)
unknown_calls=[]
class Unknown:
    def __getattribute__(self,name):
        unknown_calls.append(name);raise AssertionError('foreign record getter')
scope.records[record_index]=Unknown()
try:
    assert scope_probe(scope) is False
    assert a._loaded_owner_graph_mirrors(pb,rb) is False
finally:scope.records[record_index]=descriptor
assert unknown_calls==[]
legacy_faults=[]
for candidate in (configuration._origin,recipe._origin):
    if candidate.native_files is not None:continue
    assert scope_probe(candidate) is True
    legacy=next(row for row in candidate.records if type(row) is a._Descriptor)
    state=vars(legacy)
    for name,value in (('closed',False),('close_attempted',False),('unknown',True)):
        old=state[name];state[name]=value
        try:
            assert scope_probe(candidate) is False
            assert a._loaded_owner_graph_mirrors(pb,rb) is False
        finally:state[name]=old
        assert scope_probe(candidate) is True
        legacy_faults.append(name)
assert legacy_faults
scans=plugin._origin.expected.scans
assert scans,'actual complete package fixture must have scan closures'
scan_state=vars(scans[0]);scan_faults=[]
for name,value in (('closed',False),('unknown',True),('close_attempted',False)):
    old=scan_state[name];scan_state[name]=value
    try:
        assert a._loaded_owner_graph_mirrors(pb,rb) is False
        assert scope_probe(scope) is True  # file-only projection does not inspect scans
    finally:scan_state[name]=old
    old=scan_state.pop(name)
    try:assert a._loaded_owner_graph_mirrors(pb,rb) is False
    finally:scan_state[name]=old
    assert a._loaded_owner_graph_mirrors(pb,rb) is True
    scan_faults.extend((name,'missing:'+name))
# A canonical Scope type with forged short storage is still untrusted DATA.
# Install matching proposed owner mirrors only in this isolated fixture; the
# projection must refuse width before reading any Scope field.
short_scope_faults=[]
state=vars(plugin);old={name:state[name] for name in ('_scope','_origin','_cell','_root_cell')}
for width in (0,1,18,20):
    short=tuple.__new__(a._Scope,(None,)*width)
    cell=(plugin,short);root=(entry._activation,plugin,short)
    proposed=(short,cell,root,pb[3],pb[4])
    state.update(_scope=short,_origin=short,_cell=cell,_root_cell=root)
    try:assert a._loaded_owner_graph_mirrors(proposed,rb) is False
    finally:state.update(old)
    assert a._loaded_owner_graph_mirrors(pb,rb) is True
    short_scope_faults.append(width)
# Native tuple reads bypass Python getters, but this is not class-code proof.
foreign=[];kind=a._NativeOpenedDescriptor;old=kind.__getattribute__
def forbidden(self,name):
    foreign.append(name);raise AssertionError('foreign descriptor getter')
kind.__getattribute__=forbidden
try:assert probe(descriptor,ledger) is True
finally:kind.__getattribute__=old
assert foreign==[]
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert a._native_descriptor_closed(descriptor,ledger) is True
report={'actual_native_receipt':True,'field_fault_rows':faults,'native_work_unchanged':True,
        'foreign_getter_calls':foreign,'coherent_constructed_data_matches':True,
        'legacy_fault_rows':legacy_faults,'scan_fault_rows':scan_faults,
        'scope_slot_and_unknown_records_refused':True,'short_scope_faults':short_scope_faults,
        'original_ledger_qualification':False,'production_integration':False}
p=base/'closed-file-graph-report.json';p.write_text(json.dumps(report));p.chmod(0o600)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
    report = json.loads((tmp_path / 'closed-file-graph-report.json').read_text())
    assert len(report['field_fault_rows']) == 33
    assert report['native_work_unchanged'] and report['foreign_getter_calls'] == []
    assert report['coherent_constructed_data_matches']
    assert len(report['legacy_fault_rows']) == 6
    assert len(report['scan_fault_rows']) == 6
    assert report['scope_slot_and_unknown_records_refused']
    assert report['short_scope_faults'] == [0, 1, 18, 20]
    assert report['original_ledger_qualification'] is False
    request.node.user_properties.append(('closed_file_graph', json.dumps(report)))


@pytest.mark.parametrize('width', [0, 4, 18, 20])
def test_scope_storage_is_checked_before_fields(width):
    value = tuple.__new__(artifacts._Scope, (None,) * width)
    assert artifacts._scope_file_graph_mirrors(value) is False


def _inline_body(function, prefix, arguments):
    local = {n.id for n in ast.walk(function)
             if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    local.update(a.arg for a in function.args.args)
    names = {name: arguments.get(name, prefix + name) for name in local}

    class Rename(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id in names:
                return ast.copy_location(ast.Name(names[node.id], node.ctx), node)
            return node

        def visit_Return(self, node):
            if isinstance(node.value, ast.Constant) and node.value.value is False:
                return node
            if isinstance(node.value, ast.Constant) and node.value.value is True:
                return ast.Pass()
            return ast.If(ast.Compare(self.visit(node.value), [ast.IsNot()], [ast.Constant(True)]),
                          [ast.Return(ast.Constant(False))], [])

    return [Rename().visit(n) for n in copy.deepcopy(function.body[1:])]


def test_inlined_closure_predicates_match_their_canonical_source():
    # This checks maintained generated copies, not the canonical predicates'
    # semantics. Actual receipt faults above independently exercise those.
    tree = ast.parse((base.SERVER / 'hmp_plugin/presentation_startup_artifacts.py').read_text())
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    closed = functions['_closed_file_graph_mirrors']
    scope = functions['_scope_file_graph_mirrors']
    loaded = functions['_loaded_owner_graph_mirrors']
    native_for = next(n for n in ast.walk(scope) if isinstance(n, ast.For)
                      and isinstance(n.target, ast.Name) and n.target.id == 'row'
                      and any(isinstance(v, ast.Name) and v.id == 'closed_allocation'
                              for v in ast.walk(n)))
    expected = _inline_body(closed, 'closed_', {'descriptor': 'row', 'original_ledger': 'ledger'})
    assert (ast.dump(ast.Module(native_for.body[-len(expected):], []))
            == ast.dump(ast.Module(expected, [])))
    outer = next(n for n in loaded.body if isinstance(n, ast.For))
    expected = _inline_body(scope, 'files_', {'scope': 'scope'})
    assert (ast.dump(ast.Module(outer.body[-len(expected):], []))
            == ast.dump(ast.Module(expected, [])))
    for function in (scope, loaded):
        assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                       and n.func.id in ('_closed_file_graph_mirrors', '_scope_file_graph_mirrors',
                                         '_require', '_native_descriptor_closed')
                       for n in ast.walk(function))

"""Actual original-input custody fence; not full native traversal acceptance."""
import ast

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('fault', ('normal', 'copy', 'foreign', 'short',
                                  'scope', 'cell', 'root', 'fact',
                                  'selection_scope', 'selection_cell',
                                  'selection_root', 'selection_fact'))
def test_original_input_package_members_before_policy_capture(tmp_path, monkeypatch, fault):
    text = (base.SERVER / 'hmp_plugin/presentation_startup_artifacts.py').read_text()
    tree = ast.parse(text)
    lines = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                        'input_package_binding', 'source_check'):
                    lines[target.id] = node.lineno
                if isinstance(target, ast.Tuple) and any(
                        isinstance(item, ast.Name) and item.id == 'source_check'
                        for item in target.elts):
                    lines['source_check'] = node.lineno
    assert set(lines) == {'input_package_binding', 'source_check'}
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\nfault,inject_line,passed_line=' + repr((
        fault, lines['input_package_binding'], lines['source_check'])) + '\n'
    script += r'''
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
ledger=entry._scope.native_files.ledger
retain_code=a.StartupArtifactOwner._retain.__func__.__code__
scope_code=a._Scope.__new__.__code__
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
injected=[];passed=[];scopes=[];foreign=[]
class StopAtVerifiedFence(Exception):pass
class Foreign:
    def __getattribute__(self,name):
        foreign.append(name);raise AssertionError('foreign binding getter')
    def __iter__(self):
        foreign.append('iter');raise AssertionError('foreign binding iterator')

def observe(frame,event,result):
    if event=='call':
        if frame.f_code not in (retain_code,scope_code):return None
        frame.f_trace_lines=frame.f_code is retain_code
    if event=='line' and frame.f_code is retain_code:
        if frame.f_lineno==inject_line and not injected:
            source=frame.f_locals['source'];binding=source.binding
            assert frame.f_locals['runtime_inputs'].plugin is source.owner
            assert len(binding)==5 and len(binding[4])==4
            changed=list(binding)
            if fault=='foreign':candidate=Foreign()
            elif fault=='short':candidate=binding[:4]
            else:
                index={'scope':0,'cell':1,'root':2,'fact':3}.get(fault)
                if index is not None:changed[index]=object()
                if fault.startswith('selection_'):
                    parent=list(binding[4]);parent[{
                        'selection_scope':0,'selection_cell':1,
                        'selection_root':2,'selection_fact':3}[fault]]=object()
                    changed[4]=tuple(parent)
                candidate=tuple(changed)
            replacement=source if fault=='normal' else source._replace(binding=candidate)
            frame.f_locals['source']=replacement
            injected.append((source,replacement))
        if frame.f_lineno==passed_line:
            assert frame.f_locals['source'] is injected[0][1]
            if fault=='copy':assert injected[0][1] is not injected[0][0]
            passed.append(True)
            raise StopAtVerifiedFence()
    if event=='return' and frame.f_code is scope_code:
        scopes.append(result)
    return observe
caught=[]
previous=sys.gettrace();sys.settrace(observe)
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as error:caught.append(error)
finally:sys.settrace(previous)
assert len(caught)==1 and type(caught[0]) is EntryFilesError
assert caught[0].failed_owner is retained
assert len(injected)==1
assert bool(passed)==(fault in ('normal','copy'))
assert not foreign and not scopes
assert retained._failed and not retained._ready
owner=entry._activation._artifact_owner
assert owner is not None and owner._failed and not owner._ready
assert owner._origin is owner._scope is owner._cell is owner._root_cell is None
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

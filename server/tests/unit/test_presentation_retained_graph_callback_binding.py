"""Late package-source replacement must not reach native Scope publication."""
import ast

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('site', ('factory_return', 'parent_return', 'first', 'second'))
@pytest.mark.parametrize('fault', ('source_copy', 'binding_copy', 'foreign'))
def test_original_package_source_survives_callbacks(tmp_path, monkeypatch, site, fault):
    tree = ast.parse((base.SERVER / 'hmp_plugin/presentation_startup_artifacts.py').read_text())
    kind = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                and n.name == 'StartupArtifactOwner')
    retain = next(n for n in kind.body if isinstance(n, ast.FunctionDef) and n.name == '_retain')
    rejoin = next(
        n for n in ast.walk(retain) if isinstance(n, ast.FunctionDef) and n.name == 'link_rejoin')
    guards = sorted(n.lineno for n in ast.walk(retain) if isinstance(n, ast.If)
                    and any(isinstance(v, ast.Compare) and isinstance(v.left, ast.Name)
                            and v.left.id == 'source'
                            and len(v.ops) == 1 and isinstance(v.ops[0], ast.IsNot)
                            and len(v.comparators) == 1
                            and isinstance(v.comparators[0], ast.Name)
                            and v.comparators[0].id == 'original_package_source'
                            and n not in tuple(ast.walk(rejoin))
                            for v in ast.walk(n.test)))
    assert len(guards) == 2
    factory = next(n for n in ast.walk(retain) if isinstance(n, ast.Assign)
                   and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                   and n.value.func.id == 'held_factory')
    calls = sorted(n.lineno for n in ast.walk(retain) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == 'link_rejoin')
    parent_return = next(n.lineno for n in ast.walk(rejoin) if isinstance(n, ast.For)
                         and isinstance(n.target, ast.Name) and n.target.id == 'row')
    target = (parent_return if site == 'parent_return' else
              next(line for line in calls if line > factory.end_lineno)
              if site == 'factory_return' else guards[site == 'second'])
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\nsite,fault,target=' + repr((site, fault, target)) + '\n'
    script += r'''
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
ledger=entry._scope.native_files.ledger
retain_code=a.StartupArtifactOwner._retain.__func__.__code__
register_code=a._register_native_scope.__code__
rejoin_code=next(c for c in retain_code.co_consts if type(c) is type(retain_code) and c.co_name=='link_rejoin')
target_code=rejoin_code if site=='parent_return' else retain_code
changed=[];foreign=[];later_registration=[];successful_return=[];caught=[]
class Foreign:
    def __getattribute__(self,name):
        foreign.append(name);raise AssertionError('foreign package source getter')
    def __getitem__(self,key):
        foreign.append(key);raise AssertionError('foreign package source index')

def observe(frame,event,result):
    if changed:
        if event=='call' and frame.f_code is register_code:
            later_registration.append(True)
        if event=='return' and frame.f_code is retain_code and result is changed[0][2]:
            successful_return.append(True)
    if event=='call':
        if frame.f_code is not target_code and frame.f_code is not retain_code:return None
        frame.f_trace_lines=True
    if event=='line' and frame.f_code is target_code and frame.f_lineno==target and not changed:
        original=frame.f_locals['source'];owner=frame.f_locals['owner']
        assert frame.f_locals['original_package_source'] is original
        assert frame.f_locals['runtime_inputs'].plugin is original.owner
        assert (owner._scope is None)==(site!='second')
        if fault=='source_copy':replacement=original._replace()
        elif fault=='binding_copy':replacement=original._replace(binding=tuple(list(original.binding)))
        else:replacement=Foreign()
        assert replacement is not original
        changed.append((original,replacement,owner,tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes)))
        frame.f_locals['source']=replacement
    elif event=='line' and frame.f_code is target_code and changed:
        assert frame.f_locals['source'] is changed[0][1], 'trace replacement did not reach actual retainer'
    return observe
previous=sys.gettrace();sys.settrace(observe)
try:EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as error:caught.append(error)
finally:sys.settrace(previous)
assert len(changed)==1 and len(caught)==1
assert type(caught[0]) is EntryFilesError and caught[0].failed_owner is retained
original,replacement,owner,counts,attempts,scopes=changed[0]
assert retained._failed and not retained._ready and owner._failed and not owner._ready
assert not foreign and not later_registration and not successful_return
assert counts==tuple(ledger.counts) and attempts==len(ledger.attempts) and scopes==len(ledger.scopes)
assert '_native_scope_registration' not in vars(owner)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

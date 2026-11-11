"""Actual closed-selector input/root custody; deliberate prefix stop, not startup."""
import ast

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('site', ('before', 'parent_return', 'engine_return'))
@pytest.mark.parametrize('fault', ('normal', 'inputs_copy', 'cell_copy'))
def test_actual_selector_retains_snapshot_inputs(tmp_path, monkeypatch, site, fault):
    tree = ast.parse((base.SERVER / 'hmp_plugin/presentation_native_metadata.py').read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == '_closed_link_engine_origin')
    body = function.body
    if site == 'before':
        capture = next(i for i, n in enumerate(body) if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'snapshot_names'
                               for t in n.targets))
        target, passed = body[capture + 1].lineno, body[capture + 2].lineno
    else:
        name = 'validator' if site == 'parent_return' else 'check'
        call = next(i for i, n in enumerate(body) if isinstance(n, ast.Expr)
                    and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                            and c.func.id == name for c in ast.walk(n)))
        target, passed = body[call + 1].lineno, body[call + 2].lineno
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\nsite,fault,target,passed=' + repr((site, fault, target, passed)) + '\n'
    script += r'''
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
selector=presentation_native_metadata._closed_link_engine_origin
code=selector.__code__
ledger=entry._scope.native_files.ledger
injected=[];reached=[];caught=[]
class StopAtCustodyFence(Exception):pass

def observe(frame,event,value):
    if event=='call':
        if frame.f_code is not code:return None
        frame.f_trace_lines=True
    if event=='line' and frame.f_code is code:
        if frame.f_lineno==target and not injected:
            names=frame.f_locals['snapshot_names']
            inputs=frame.f_locals['original_inputs'];cell=frame.f_locals['snapshot_cell']
            assert names['_inputs'] is inputs and names['_root_cell'] is cell
            assert frame.f_locals['original_scope'].runtime.inputs is inputs
            baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
            if fault=='inputs_copy':
                candidate=inputs._replace()
                assert candidate is not inputs
                names['_inputs']=candidate
            elif fault=='cell_copy':
                candidate=tuple(list(cell))
                assert candidate is not cell
                names['_root_cell']=candidate
            injected.append(baseline)
        elif frame.f_lineno==passed and injected:
            reached.append(True)
            raise StopAtCustodyFence()
    return observe
previous=sys.gettrace();assert previous is None
sys.settrace(observe)
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as error:caught.append(error)
finally:sys.settrace(previous)
assert len(injected)==1 and len(caught)==1
assert caught[0].failed_owner is retained
assert bool(reached) is (fault=='normal'),(site,fault,reached)
assert injected[0]==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert retained._failed and not retained._ready
assert entry._activation._artifact_owner._failed
assert sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

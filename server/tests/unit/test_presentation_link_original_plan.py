"""Copied native runtime plans must refuse before actual Scope publication."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('fault', ('plan_copy', 'coherent_link_copy'))
def test_original_input_plan_is_required_before_scope_publication(tmp_path, monkeypatch, fault):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)] + '\nfault=' + repr(fault) + '\n' + r'''
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
source_ctor=a._RuntimeSource.__new__.__code__;scope_ctor=a._Scope.__new__.__code__
source_builder=a._runtime_source.__code__;retain_code=a.StartupArtifactOwner._retain.__func__.__code__
ledger=entry._scope.native_files.ledger
changes=[];returns=[];scopes=[];baseline=[]

def observe(frame,event,result):
    if event=='call':
        if frame.f_code is not source_ctor and frame.f_code is not scope_ctor and frame.f_code is not retain_code:
            return None
        frame.f_trace_lines=frame.f_code is source_ctor
        if frame.f_code is retain_code and frame.f_locals.get('runtime') is not None:
            baseline.append((tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes)))
    if (event=='line' and frame.f_code is source_ctor
            and frame.f_back is not None and frame.f_back.f_code is source_builder and not changes):
        local=frame.f_locals;original=local['plan'];link=original.executable_link
        copied_link=link._replace() if fault=='coherent_link_copy' else link
        copied=original._replace(executable_link=copied_link)
        changes.append((original,link,copied,copied_link))
        local['plan']=copied;local['link']=copied_link
    if event=='return' and frame.f_code is source_ctor:
        if frame.f_back is not None and frame.f_back.f_code is source_builder:
            returns.append(result)
    if event=='return' and frame.f_code is scope_ctor:
        if frame.f_locals.get('native_link_blueprint') is not None:
            scopes.append(result);sys.settrace(None)
    return observe
previous=sys.gettrace();sys.settrace(observe)
refused=False
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError:
    refused=True
finally:sys.settrace(previous)
assert len(changes)==len(returns)==len(baseline)==1
original,link,copied,copied_link=changes[0]
actual=returns[0]
assert actual.plan is copied and actual.plan is not original
assert actual.link is copied_link and copied.executable_link is copied_link
assert actual.inputs.runtime_plan is original and original.executable_link is link
assert copied.pending is original.pending
if fault=='coherent_link_copy':assert copied_link is not link
assert refused and retained._failed and not retained._ready
owner=entry._activation._artifact_owner
assert owner is not None and owner._failed and not owner._ready
assert scopes==[], 'copied runtime plan reached actual Scope construction'
assert owner._scope is owner._origin is owner._cell is owner._root_cell is None
assert actual.inputs.io_slot==[None]
assert baseline[0]==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
try:EntryFileSnapshotOwner.complete(retained)
except EntryFilesError:pass
else:raise AssertionError('copied-plan refusal replayed')
assert baseline[0]==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

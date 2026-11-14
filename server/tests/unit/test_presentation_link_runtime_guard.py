"""Actual synthetic startup refusals at both Link guard sites.

No mock returns an authority verdict. The original guard/runtime audit must
reject changed retained state before a selected metadata/readlink C call.
"""
import pytest
import json

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


CASES = [(site, 'before_guard', fault)
         for site in ('resource', 'lifetime')
         for fault in ('nested_parent', 'package_history', 'copied_plan', 'entry_root', 'retired')]
CASES += [(site, 'actor_return', 'copied_plan')
          for site in ('resource', 'lifetime')]


@pytest.mark.parametrize('site,boundary,fault', CASES)
def test_original_link_guard_rejects_changed_runtime_before_native_work(
        tmp_path, monkeypatch, request, site, boundary, fault):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\nsite,boundary,fault=' + repr((site, boundary, fault)) + '\n'
    script += r'''
from hmp_plugin import presentation_native_link as native_link
from hmp_startup.entry_files import EntryFilesError
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
lineage=entry._scope.native_files
ledger=lineage.ledger
operations=lineage.native.operations
guard_code=a.StartupArtifactOwner._guard.__code__
runtime_code=a._runtime_current.__code__
parent_code=a._source_current.__code__
site_code=(native_link._resource_tail if site=='resource'
           else native_link._lifetime_tail).__code__
observed=[];effects=[];runtime_checks=[];parent_checks=[];closes=[];mutation_complete=[]

def inject(frame):
    owner=frame.f_locals['self']
    scope=owner._origin
    source=scope.runtime
    execution=owner._native_link_execution
    opcode=execution.definitions[execution.cursor[0].position][0]
    assert opcode==(5 if boundary=='actor_return' else 4)
    observed.append((ledger.counts[0],ledger.counts[1],len(ledger.attempts),opcode))
    closes.extend((descriptor.close,descriptor.fd)
                  for descriptor in owner._native_link_execution.opened)
    if fault=='nested_parent':
        attempt=source.inputs.completion_attempt
        activation=source.inputs.recipe_binding[0].activation
        assert activation._entry_files_attempt_cell is attempt
        replacement=tuple([*attempt])
        activation._entry_files_attempt_cell=replacement
        assert replacement is not attempt and replacement==attempt
    elif fault=='package_history':
        # Instance history is not part of the engine's code/default pins. The
        # real runtime parent walk must reject this changed package inventory.
        scans=source.inputs.plugin._origin.expected.scans
        assert scans and scans[0].closed is True and scans[0].unknown is False
        scans[0].closed=False
        assert scans[0].closed is False
    elif fault=='copied_plan':
        copied=type(source.plan)(*source.plan)
        assert copied is not source.plan and copied==source.plan
        source.entry._inputs=source.inputs._replace(runtime_plan=copied)
        assert source.entry._inputs.runtime_plan is copied
    elif fault=='entry_root':
        source.entry._root_cell=tuple([*source.cell])
        assert source.entry._root_cell is not source.cell
    else:
        scope.activation.retire()
        assert scope.activation._retired is True
    mutation_complete.append(True)

def observe(frame,event,value):
    if observed and event=='c_call' and any(value is call for call in operations[3:]):
        effects.append(True)
    if (event=='call' and frame.f_code is runtime_code
            and frame.f_back.f_code is guard_code and observed):
        runtime_checks.append(True)
    if (event=='call' and frame.f_code is parent_code
            and frame.f_back.f_code is guard_code and observed):
        parent_checks.append(True)
    if (not observed and frame.f_code is guard_code
            and frame.f_back.f_code is site_code):
        if boundary=='before_guard' and event=='call':
            inject(frame)
        elif (boundary=='actor_return' and event=='c_return'
              and value is lineage.native.actor_calls[2]):
            inject(frame)

prior=sys.getprofile()
assert prior is None and sys.gettrace() is None
monitor=getattr(sys,'monitoring',None)
def selected(frame):
    if boundary!='actor_return':return True
    resource=(frame.f_locals['resource'] if site=='resource'
              else frame.f_locals['consumer'].operation.resource)
    return type(resource) is a._NativeLinkBytesResource
if monitor is not None:
    monitor.use_tool_id(5,'hermes-synthetic-link-runtime-guard')
    def enter(code,offset):
        if not observed and selected(sys._getframe(1)):sys.setprofile(observe)
    monitor.register_callback(5,monitor.events.PY_START,enter)
    monitor.set_local_events(5,site_code,monitor.events.PY_START)
else:
    def enter(frame,event,value):
        frame.f_trace_lines=False
        if event=='call' and frame.f_code is site_code and selected(frame):
            sys.settrace(None)
            sys.setprofile(observe)
        return None
    sys.settrace(enter)
error=None;checked=None
try:
    checked=EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as caught:
    assert caught.failed_owner is retained
    error=type(caught).__name__
finally:
    sys.setprofile(prior)
    sys.settrace(None)
    if monitor is not None:
        monitor.set_local_events(5,site_code,0)
        monitor.register_callback(5,monitor.events.PY_START,None)
        monitor.free_tool_id(5)
assert len(observed)==1, (site,boundary,fault,observed,error)
assert mutation_complete==[True], (site,boundary,fault,mutation_complete)
assert error=='EntryFilesError' and checked is None
assert retained._failed and not retained._ready and retained._fact_cell is None
assert effects==[], (site,boundary,fault,effects)
if fault=='package_history':
    assert parent_checks and not runtime_checks
elif fault!='retired':
    assert runtime_checks, (site,boundary,fault,runtime_checks)
used,reserved,attempts,opcode=observed[0]
# Only existing reserved descriptor cleanup may consume work after refusal.
assert ledger.counts[0]-used==reserved-ledger.counts[1]
assert len(ledger.attempts)==attempts
assert ledger.counts[1]==0
assert len(closes)==reserved
for close,fd in closes:
    assert close.state==[True,False] and close.raw[0] is None
    receipt=close.result[0]
    assert type(receipt) is tuple and len(receipt)==3
    assert receipt[0] is close and receipt[1] is fd and receipt[2] is None
evidence=dict(site=site,boundary=boundary,fault=fault,operation=opcode,refused=True,
              original_guard_runtime_checks=len(runtime_checks),
              original_guard_package_checks=len(parent_checks),
              selected_native_calls_after_mutation=len(effects),
              new_work=ledger.counts[0]-used,cleanup=reserved-ledger.counts[1],
              reserved_after=ledger.counts[1])
destination=base/'link-runtime-guard-refusal.json'
destination.write_text(json.dumps(evidence,sort_keys=True));destination.chmod(0o600)
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
    evidence = json.loads((tmp_path / 'link-runtime-guard-refusal.json').read_text())
    request.node.user_properties.append(('link_runtime_guard_evidence', json.dumps(evidence)))

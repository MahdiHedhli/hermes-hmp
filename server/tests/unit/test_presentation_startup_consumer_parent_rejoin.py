"""Late old-parent corruption cannot cross the fused post-observation audit."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('scan_unknown', 'scan_close_attempt'))
def test_post_observation_parent_rejoin(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += '\nparent_case=' + repr(case) + '\n'
    script += r'''
import os
from hmp_plugin import presentation_startup_probe as probe
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
row=next(row for row in retained._inputs.cache_context_slot[0][3]
         if row.state=='needs_owned_absence')
Path(row.location.path).parent.mkdir(mode=0o700)
changed=[];before=[];native_after=[]
prior_trace,prior_profile=sys.gettrace(),sys.getprofile()
def corrupt_parent(frame):
    execution=frame.f_locals['execution']
    if changed or not execution.history:return
    scan=execution.plan.source.inputs.plugin._origin.expected.scans[0]
    assert scan.closed and scan.close_attempted and not scan.unknown
    before.append((execution.registration.native_ledger,
                   len(execution.registration.native_ledger.attempts)))
    if parent_case=='scan_unknown':scan.unknown=True
    else:scan.close_attempted=False
    changed.append(True)
def actual_metadata(frame):
    if changed:native_after.append(True)
# Observe literal stat/fstat C calls, not a mirror of intent accounting.
stat_call,fstat_call=os.stat,os.fstat
def profile_metadata(frame,event,arg):
    if event=='c_call' and (arg is stat_call or arg is fstat_call):
        actual_metadata(frame)
trace_synthetic_boundary(probe._consumer_tail.__code__,
    '_execution_tail(execution)  # Rejoin full mutable parent state',corrupt_parent)
sys.setprofile(profile_metadata)
refused=False
try:
    try:EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError:refused=True
finally:
    sys.settrace(prior_trace);sys.setprofile(prior_profile)
assert changed==[True] and refused and native_after==[]
ledger,count=before[0]
assert len(ledger.attempts)==count
assert retained._inputs.io_slot[0]._failed
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

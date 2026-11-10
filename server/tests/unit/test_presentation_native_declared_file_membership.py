"""Entry-bound file reads use original declaration objects before file effects."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('package', 'artifact'))
@pytest.mark.parametrize('change', ('normal', 'copied', 'unlisted', 'foreign'))
def test_declared_file_identity_before_open(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_file=a.StartupArtifactOwner._file
calls=[];foreign_calls=[];rejected=[];violations=[];mutations=[];confirmed=[]
from hmp_plugin.presentation_gateway_package import PackageInventoryError
class ForeignExpected:
    def __getattr__(self,name):foreign_calls.append('get');raise AssertionError('foreign getter')
    def __eq__(self,other):foreign_calls.append('eq');raise AssertionError('foreign equality')
    def __fspath__(self):foreign_calls.append('path');raise AssertionError('foreign path')
wanted=GatewayPackageOwner if KIND=='package' else a.StartupArtifactOwner
active={};native_calls=[];file_code=actual_file.__code__;open_code=a.StartupArtifactOwner._open.__code__
def observe(frame,event,callee):
    if (event=='c_call' and frame.f_code is open_code
            and callee is frame.f_locals.get('open_call')):native_calls.append(True)
def traced(frame,event,value):
    if frame.f_code is not file_code:return None
    if event=='call':
        values=frame.f_locals;target=values['self'];expected=values['expected']
        supplied=values['native_registration']
        if supplied is None or type(target) is not wanted:return None
        ledger=supplied.native_ledger
        calls.append(target)
        # Observe native effects only after the selected declaration is bound.
        # Earlier legitimate inventory reads are outside this refusal interval.
        if CHANGE!='normal':
            sys.setprofile(observe)
            if local_monitor:monitor.set_events(5,monitor.events.RAISE)
        active[id(frame)]=(target,target._count_cell,len(target._origin.records),
                           len(native_calls),ledger,tuple(ledger.counts),len(ledger.attempts))
        candidate=expected
        if CHANGE=='copied':candidate=expected._replace()
        if CHANGE=='unlisted':candidate=expected._replace(path=str(base/'UNLISTED_SYNTHETIC_FILE'))
        if CHANGE=='foreign':candidate=ForeignExpected()
        if CHANGE!='normal':
            values['expected']=candidate
            mutations.append((expected,candidate))
        return traced
    if id(frame) not in active:return None
    if event=='exception' and CHANGE!='normal':
        target,count,records,opens,ledger,counts,attempts=active[id(frame)]
        if frame.f_locals['expected'] is mutations[-1][1] and mutations[-1][0] is not mutations[-1][1]:
            confirmed.append(mutations[-1])
        rejected.append(True)
        if (target._count_cell is not count or len(target._origin.records)!=records
                or len(native_calls)!=opens or tuple(ledger.counts)!=counts
                or len(ledger.attempts)!=attempts):
            violations.append('file effects before declaration refusal')
    if event=='return':active.pop(id(frame),None)
    return traced
prior_trace=sys.gettrace();prior_profile=sys.getprofile()
assert prior_trace is None and prior_profile is None
local_monitor=sys.version_info >= (3,13) and hasattr(sys,'monitoring')
if local_monitor:
    # CPython3.13+ exposes a write-through frame-locals proxy. Local monitoring
    # avoids tracing every unrelated Python call before the selected method.
    monitor=sys.monitoring
    monitor.use_tool_id(5,'hermes-synthetic-declaration')
    def monitor_start(code,offset):traced(sys._getframe(1),'call',None)
    def monitor_raise(code,offset,error):traced(sys._getframe(1),'exception',None)
    def monitor_return(code,offset,result):traced(sys._getframe(1),'return',result)
    monitor.register_callback(5,monitor.events.PY_START,monitor_start)
    monitor.register_callback(5,monitor.events.RAISE,monitor_raise)
    monitor.register_callback(5,monitor.events.PY_RETURN,monitor_return)
    monitor.set_local_events(5,file_code,
        monitor.events.PY_START|monitor.events.PY_RETURN)
else:sys.settrace(traced)
'''.replace('KIND', repr(kind)).replace('CHANGE', repr(change))
    after = r'''
try:
    plugin = GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    held_entry=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
    checked=EntryFileSnapshotOwner.complete(held_entry)
except Exception as caught:
    assert CHANGE!='normal' and calls
    if KIND=='package':
        assert type(caught) is PackageInventoryError and caught.failed_owner is calls[0]
        assert calls[0]._failed
    else:
        assert type(caught) is EntryFilesError and caught.failed_owner is held_entry
        assert held_entry._failed
else:assert CHANGE=='normal' and calls and checked._ready
finally:
    sys.settrace(prior_trace);sys.setprofile(prior_profile)
    if local_monitor:
        monitor.set_local_events(5,file_code,0)
        monitor.set_events(5,0)
        for event in (monitor.events.PY_START,monitor.events.RAISE,monitor.events.PY_RETURN):
            monitor.register_callback(5,event,None)
        monitor.free_tool_id(5)
assert foreign_calls==[] and violations==[]
assert CHANGE=='normal' or (rejected and mutations and len(confirmed)==len(mutations))
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change)).replace('KIND', repr(kind))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected + after))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')

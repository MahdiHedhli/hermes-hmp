"""Actual native cleanup survives retired work mirrors without a second close."""
from __future__ import annotations

import ast

import pytest


@pytest.mark.parametrize('change', ('normal', 'close_alias', 'actor_alias',
                                    'root_retired', 'copied_row', 'malformed_allocation',
                                    'malformed_scope', 'wrong_thread', 'duplicate'))
def test_original_reserved_close(tmp_path, monkeypatch, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_open=a.StartupArtifactOwner._open;actual_close=a.StartupArtifactOwner._close
acted=[];completed=[];close_calls=[];foreign_calls=[];known=[];restores=[]
class Finished(Exception):pass
class Foreign:
    def __getattr__(self,name):
        foreign_calls.append('get');raise AssertionError('foreign allocation getter')
def foreign(*args,**kwargs):
    foreign_calls.append(True);raise AssertionError('late alias invoked')
def native_observed(frame):
    close_calls.append(frame.f_locals['fd'])
def checked_open(target,name,parent,directory,native_registration=None):
    row,fd=actual_open(target,name,parent,directory,native_registration)
    if type(target) is not GatewayPackageOwner or native_registration is None or acted:
        return row,fd
    acted.append(True);known.append(row)
    ledger=native_registration.native_ledger
    before=tuple(ledger.counts)
    native=native_registration.native_origin
    observe_synthetic_native(native.operations[2],a._close_native_file_known.__code__,native_observed)
    if CHANGE=='close_alias':
        for namespace in (a.os,native.native):
            restores.append((namespace,'close',getattr(namespace,'close')))
            setattr(namespace,'close',foreign)
    elif CHANGE=='actor_alias':
        restores.append((a.os,'getpid',a.os.getpid));a.os.getpid=foreign
    elif CHANGE=='root_retired':target._root_cell=object()
    elif CHANGE=='wrong_thread':
        profile=sys.getprofile();refused=[]
        def other_thread():
            sys.setprofile(profile)
            try:actual_close(target,row,fd,target._origin,target._root_cell)
            except a._NativeActorMismatchError:refused.append(True)
            finally:sys.setprofile(None)
        thread=a.threading.Thread(target=other_thread);thread.start();thread.join(timeout=10)
        assert not thread.is_alive() and refused==[True]
        assert close_calls==[] and tuple(ledger.counts)==before
        assert row.close.state==[False,False] and ledger.failed==[False]
    elif CHANGE=='malformed_scope':
        fake_scope=target._origin._replace(native_files=Foreign())
        supplied=row._replace(allocation=row.allocation._replace(scope=fake_scope))
        try:actual_close(target,supplied,fd,fake_scope,target._root_cell)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('foreign scope lineage reached')
        assert close_calls==[] and tuple(ledger.counts)==before
    elif CHANGE in ('copied_row','malformed_allocation'):
        supplied=(row._replace() if CHANGE=='copied_row'
                  else row._replace(allocation=Foreign()))
        try:actual_close(target,supplied,fd,target._origin,target._root_cell)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('copied actual result accepted')
        assert close_calls==[] and tuple(ledger.counts)==before
    actual_close(target,row,fd,target._origin,target._root_cell)
    assert len(close_calls)==1 and close_calls[0] is fd
    assert ledger.counts==[before[0]+1,before[1]-1]
    assert row.closed and row.close_attempted and not row.unknown
    assert a._native_descriptor_closed(row,ledger)
    if CHANGE=='duplicate':
        after=tuple(ledger.counts)
        try:actual_close(target,row,fd,target._origin,target._root_cell)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('duplicate close accepted')
        assert len(close_calls)==1 and tuple(ledger.counts)==after
    completed.append(True)
    raise Finished()
a.StartupArtifactOwner._open=checked_open
try:GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
except Exception:assert completed==[True] and acted and known and len(close_calls)==1
else:raise AssertionError('bounded cleanup scenario did not stop')
finally:
    a.StartupArtifactOwner._open=actual_open
    for namespace,name,value in reversed(restores):setattr(namespace,name,value)
assert not foreign_calls
assert all(row.closed and row.close_attempted for row in known)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))
    ast.parse(injected)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')


@pytest.mark.parametrize('change', ('append', 'replace', 'early_close',
                                    'wrapper_alloc_failure'))
def test_actual_open_result_keeps_original_custody(tmp_path, monkeypatch, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_open=a.StartupArtifactOwner._open
changed=[];allocations=[];close_calls=[];completed=[];violations=[]
foreign=object()
class AllocationFailed(Exception):pass
def native_closed(frame):close_calls.append(frame.f_locals['fd'])
def observed_open(frame):
    if type(frame.f_locals.get('self')) is not GatewayPackageOwner or changed:return
    allocation=frame.f_locals['allocation'];records=frame.f_locals['records']
    allocations.append(allocation);changed.append(True)
    if CHANGE=='append':records.append(foreign)
    elif CHANGE=='replace':records[frame.f_locals['record_index']]=foreign
def early_close(frame):
    if (CHANGE not in ('early_close','wrapper_alloc_failure') or changed
            or type(frame.f_locals.get('self')) is not GatewayPackageOwner):
        return
    allocation=frame.f_locals['allocation'];fd=frame.f_locals['fd']
    allocations.append(allocation);changed.append(True)
    if CHANGE=='wrapper_alloc_failure':raise AllocationFailed()
    before=tuple(allocation.ledger.counts)
    try:a._close_native_file_known(frame.f_locals['self'],allocation,fd,allocation.ledger)
    except a.ArtifactObservationError:pass
    else:violations.append('premature close accepted')
    if close_calls or tuple(allocation.ledger.counts)!=before:
        violations.append('premature close consumed capacity')
    completed.append(True)
native=GatewayEntryOwner._native_file_lineage(entry).native
observe_synthetic_native(native.operations[2],a._close_native_file_known.__code__,native_closed)
original_profile=sys.getprofile()
def result_profile(frame,event,arg):
    original_profile(frame,event,arg)
    if (CHANGE in ('append','replace') and event=='c_return' and arg is native.operations[0]
            and frame.f_code is actual_open.__code__):observed_open(frame)
sys.setprofile(result_profile)
trace_synthetic_boundary(actual_open.__code__,'descriptor = _NativeOpenedDescriptor(',early_close)
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    if CHANGE=='early_close':
        assert completed==[True] and not violations and changed
except Exception:
    assert CHANGE!='early_close' and changed and allocations
else:assert CHANGE=='early_close'
finally:sys.setprofile(original_profile)
assert not violations
if CHANGE!='early_close':
    allocation=allocations[0]
    if CHANGE in ('append','replace'):
        assert any(row is foreign for row in allocation.scope.records)
    else:assert any(row is allocation.pending for row in allocation.scope.records)
    assert allocation.result[0] is None
    assert type(allocation.raw[0]) is int
    assert close_calls==[allocation.raw[0]]
    assert allocation.close.state==[True,False] and allocation.close.raw[0] is None
else:
    assert allocations[0].close.state==[True,False]
    assert allocations[0].close.raw[0] is None and close_calls
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))
    ast.parse(injected)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')


@pytest.mark.parametrize('point', ('before_prepare', 'pre_rejoin', 'before_append',
                                   'after_append', 'after_used', 'after_reserved'))
@pytest.mark.parametrize('fault', ('interrupted', 'mismatch'))
def test_open_reservation_interruption_retains_failure(tmp_path, monkeypatch, point, fault):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    fragments = {'before_prepare': 'preparation = _NativeFilePreparation(',
                 'pre_rejoin': '_native_work_origin_tail(owner, registration, native)',
                 'before_append': 'attempts.append(allocation)',
                 'after_append': 'counts[0] = used + 1',
                 'after_used': 'counts[1] = reserved + 1',
                 'after_reserved': 'return allocation'}
    injected = r'''
fired=[];originals=[];file_calls=[]
class Interrupted(Exception):pass
def interrupt(frame):
    if fired or type(frame.f_locals.get('owner')) is not GatewayPackageOwner:return
    originals.append(dict(frame.f_locals))
    fired.append(True);raise FAULT()
def observed(frame):file_calls.append(True)
native=GatewayEntryOwner._native_file_lineage(entry).native
observe_synthetic_native(native.operations[0],a.StartupArtifactOwner._open.__code__,observed)
observe_synthetic_native(native.operations[2],a._close_native_file_known.__code__,observed)
trace_synthetic_boundary(a._allocate_native_file_open.__code__,FRAGMENT,interrupt)
try:GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
except Exception:pass
else:raise AssertionError('interrupted preparation admitted')
assert fired==[True] and file_calls==[]
held=originals[0];preparation=held['preparation'];allocation=held.get('allocation')
ledger=held['ledger'];registration=held['registration']
assert ledger.failure[0] is (preparation if preparation is not None else held['token'])
assert ledger.failed==[True] and ledger.inflight==[None]
used,reserved=held['used'],held['reserved']
expected=(used+(POINT in ('after_used','after_reserved')),
          reserved+(POINT=='after_reserved'))
assert tuple(ledger.counts)==expected
if preparation is not None:assert preparation.allocation[0] is allocation
appended=POINT in ('after_append','after_used','after_reserved')
assert len(ledger.attempts)==held['index']+appended
if appended:assert ledger.attempts[held['index']] is allocation
before=(tuple(ledger.counts),tuple(ledger.attempts))
try:a._native_scope_current(held['owner'],registration)
except a.ArtifactObservationError:pass
else:raise AssertionError('sticky failure admitted new work')
assert tuple(ledger.counts)==before[0]
assert all(x is y for x,y in zip(ledger.attempts,before[1],strict=True))
if allocation is not None:
    assert allocation.raw==[None] and allocation.close.raw[0] is allocation.close.unset
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('FRAGMENT', repr(fragments[point])).replace('POINT', repr(point))
    injected = injected.replace(
        'FAULT', 'Interrupted' if fault == 'interrupted' else 'a._NativeActorMismatchError')
    ast.parse(injected)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')


@pytest.mark.parametrize(('point', 'fault'), [
    (point, fault)
    for point in ('before_actor', 'after_actor', 'after_attempt', 'after_debit', 'after_raw')
    for fault in ('interrupted', 'mismatch')
    if (point, fault) != ('before_actor', 'mismatch')
])
def test_close_transition_interruption_never_replays(tmp_path, monkeypatch, point, fault):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    fragments = {
        'before_actor': ('_native_actor_context(close.actor_calls, '
                         'close.actor_modules, close.context)'),
        'after_actor': 'and close.reservation is token and close.close_call is close_call',
        'after_attempt': 'counts[0], counts[1] = used_after, reserved_after',
        'after_debit': 'value = close_call(fd)',
        'after_raw': 'close.result[0] = (close, fd, value)',
    }
    injected = r'''
actual_open=a.StartupArtifactOwner._open;actual_close=a.StartupArtifactOwner._close
fired=[];completed=[];known=[];close_calls=[];held=[]
class Interrupted(Exception):pass
class Finished(Exception):pass
def interrupt(frame):
    if fired:return
    held.append(dict(frame.f_locals));fired.append(True);raise FAULT()
def observed(frame):close_calls.append(frame.f_locals['fd'])
def checked_open(target,name,parent,directory,native_registration=None):
    row,fd=actual_open(target,name,parent,directory,native_registration)
    if type(target) is not GatewayPackageOwner or native_registration is None or known:
        return row,fd
    known.append(row);ledger=native_registration.native_ledger;before=tuple(ledger.counts)
    observe_synthetic_native(native_registration.native_origin.operations[2],
                             a._close_native_file_known.__code__,observed)
    trace_synthetic_boundary(a._close_native_file_known.__code__,FRAGMENT,interrupt)
    try:actual_close(target,row,fd,target._origin,target._root_cell)
    except FAULT:pass
    else:raise AssertionError('interrupted close admitted')
    assert fired==[True] and row.close.state[1] is True
    assert ledger.failed==[True] and ledger.failure[0] is row.close and ledger.inflight==[None]
    debited=POINT in ('after_debit','after_raw')
    assert tuple(ledger.counts)==(before[0]+debited,before[1]-debited)
    assert row.close.state[0] is (POINT not in ('before_actor','after_actor'))
    assert len(close_calls)==(POINT=='after_raw')
    if POINT=='after_raw':assert row.close.raw[0] is None
    else:assert row.close.raw[0] is row.close.unset
    after=tuple(ledger.counts)
    try:actual_close(target,row,fd,target._origin,target._root_cell)
    except a.ArtifactObservationError:pass
    else:raise AssertionError('unknown close replayed')
    assert tuple(ledger.counts)==after and len(close_calls)==(POINT=='after_raw')
    completed.append(True);raise Finished()
a.StartupArtifactOwner._open=checked_open
try:GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
except Exception:assert completed==[True]
else:raise AssertionError('bounded close interruption did not stop')
finally:a.StartupArtifactOwner._open=actual_open
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('FRAGMENT', repr(fragments[point])).replace('POINT', repr(point))
    injected = injected.replace(
        'FAULT', 'Interrupted' if fault == 'interrupted' else 'a._NativeActorMismatchError')
    ast.parse(injected)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')

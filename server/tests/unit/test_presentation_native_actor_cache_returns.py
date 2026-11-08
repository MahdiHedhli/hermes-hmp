"""Final actor C-return faults at the two distinct cache work boundaries."""
from __future__ import annotations

import ast

import pytest


@pytest.mark.parametrize('boundary', ('read', 'probe'))
@pytest.mark.parametrize('change', ('normal', 'registration', 'native_alias'))
def test_cache_actor_return_refuses_changed_originals(tmp_path, monkeypatch, boundary, change):
    from . import test_presentation_cache_probe as probe
    from . import test_presentation_cache_reader as reader
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    is_read = boundary == 'read'
    marker = '\ntry:owner.read()\n' if is_read else '\ntry:owner.observe()\n'
    injected = r'''
actual_method=MODULE.OWNER.METHOD
native_calls=[];changed=[];foreign_calls=[];restore=[]
def foreign(*args,**kwargs):
    foreign_calls.append(True);raise AssertionError('foreign file function')
def native_observed(frame):
    if frame.f_locals.get('self') is owner:native_calls.append(True)
observe_synthetic_native(MODULE.os.NATIVE,actual_method.__code__,native_observed)
original_profile=sys.getprofile()
def actor_profile(frame,event,arg):
    original_profile(frame,event,arg)
    if event!='c_return' or frame.f_code is not MODULE._native_actor_context.__code__:
        return
    caller=frame.f_back
    if caller.f_code is not actual_method.__code__ or caller.f_locals.get('self') is not owner:
        return
    registration=caller.f_locals['native_registration']
    if changed or arg is not registration.native_origin.actor_calls[2] or CHANGE=='normal':
        return
    if CHANGE=='registration':owner._native_scope_registration=registration._replace()
    else:
        restore.append(MODULE.os.NATIVE);MODULE.os.NATIVE=foreign
    changed.append(True)
sys.setprofile(actor_profile)
try:owner.ACTION()
except ERROR:
    assert CHANGE!='normal' and changed and not native_calls
else:
    assert CHANGE=='normal' and native_calls and owner._ready
finally:
    sys.setprofile(original_profile)
    if restore:MODULE.os.NATIVE=restore[0]
assert not foreign_calls
assert all(row.close_attempted and row.closed for row in owner._origin.records)
if CHANGE!='normal':assert owner._bytes_read==0
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''
    replacements = {
        'MODULE': 'cm' if is_read else 'pm',
        'OWNER': 'DeclaredCacheReadOwner' if is_read else 'RuntimeCacheProbeOwner',
        'METHOD': '_read' if is_read else '_stat_known',
        'NATIVE': 'read' if is_read else 'stat',
        'ACTION': 'read' if is_read else 'observe',
        'ERROR': 'CacheReadError' if is_read else 'CacheProbeError',
        'CHANGE': repr(change),
    }
    for key, value in replacements.items():
        injected = injected.replace(key, value)
    ast.parse(injected)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        prefix = runner.SCRIPT[:runner.SCRIPT.index(marker)]
        monkeypatch.setattr(runner, 'SCRIPT', prefix + injected)
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    if is_read:
        reader.test_declared_cache_reader(tmp_path, monkeypatch, 'normal')
    else:
        probe.test_fresh_cache_probe(tmp_path, monkeypatch, 'missing')

"""Resource preparation over an actual original opened synthetic descriptor."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'copied_descriptor', 'copied_registration',
                                 'foreign_descriptor', 'unexpected_name'))
def test_original_metadata_resource(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.runtime_reader import RuntimeSourceReadOwner
from hmp_plugin import presentation_startup_artifacts as a
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeSourceReadOwner.retain(continuation,index)
seen=[];foreign_calls=[]
class Foreign:
    def __getattr__(self,name):
        foreign_calls.append(name)
        raise AssertionError('foreign descriptor getter')
def prepare(frame):
    if frame.f_locals['self'] is not owner or seen:return
    held=frame.f_locals['native_walk']
    registration=frame.f_locals['native_registration']
    descriptor=frame.f_locals['row']
    assert type(descriptor) is a._NativeOpenedDescriptor and len(held)==6
    ledger=registration.native_ledger
    counts=tuple(ledger.counts);attempts=len(ledger.attempts)
    phase=registration.native_phase
    progress=held[5].progress
    assert progress==[0,None] and phase.current[0] is phase.idle
    candidate=descriptor;candidate_registration=registration;name=None
    if case=='copied_descriptor':candidate=descriptor._replace()
    elif case=='copied_registration':candidate_registration=registration._replace()
    elif case=='foreign_descriptor':candidate=Foreign()
    elif case=='unexpected_name':name='UNRELATED_COMPONENT'
    try:
        resource=a._prepare_native_metadata_resource(
            owner,candidate_registration,held,candidate,name)
    except a.ArtifactObservationError:
        assert case!='normal'
    else:
        assert case=='normal' and resource.descriptor is descriptor
        assert resource.metadata is held[5] and resource.held_walk is held
        assert resource.arguments[0] is descriptor.fd
        assert resource.site==(4,'directory',0) and resource.ordinal==0
    assert counts==tuple(ledger.counts) and len(ledger.attempts)==attempts
    assert progress==[0,None] and held[5].progress is progress
    assert phase.current[0] is phase.idle and phase.result[0] is None
    assert foreign_calls==[] and not owner._failed and not owner._unknown
    seen.append(True)
trace_synthetic_boundary(a.StartupArtifactOwner._file.__code__,
                         'info = StartupArtifactOwner._fstat(self, fd, s, native_registration)',
                         prepare)
owner.read()
assert seen==[True] and owner._ready
assert owner.completed_binding()[4] is owner._original_buffer
owner.release()
assert owner._original_buffer==bytearray()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

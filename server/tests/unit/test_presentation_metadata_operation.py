"""Operation preparation over an actual original opened synthetic descriptor."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'copied_descriptor', 'copied_registration',
                                 'foreign_descriptor', 'unexpected_name'))
def test_original_metadata_operation(tmp_path, monkeypatch, case):
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
from hmp_plugin import presentation_native_metadata as m
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
        operation=m._prepare_metadata_operation(owner,resource)
        assert type(operation) is m._MetadataOperation and operation.resource is resource
        assert operation.callee is registration.native_origin.operations[4]
        assert operation.arguments is resource.arguments and operation.attempts is ledger.attempts
        assert operation.index==attempts and operation.budget[0] is ledger.counts
        assert operation.budget[1:]==(counts[0],counts[1],counts[0]+1)
        assert operation.state==[False,False,False] and operation.ended==[False]
        result=operation.result
        assert result.attempt[0] is operation and result.consumer==[None]
        assert result.raw[0] is result.unset and result.category==[None]
        assert result.snapshot==result.acknowledged==result.envelope==[None]
        consumer=m._prepare_directory_consumer(owner,operation)
        assert type(consumer) is m._DirectoryConsumer and consumer.operation is operation
        assert consumer.resource is resource and result.consumer[0] is consumer
        assert consumer.consumption==consumer.commit==[None]
        assert consumer.owner_type is type(owner)
        assert consumer.material is owner._origin.material_origin[0]
        assert consumer.material_code is owner._origin.material_origin[1]
        assert consumer.file_function is a.StartupArtifactOwner._file
        assert consumer.file_code is a.StartupArtifactOwner._file.__code__
        try:m._prepare_directory_consumer(owner,operation)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('directory consumer rebound')
        assert result.consumer[0] is consumer
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


@pytest.mark.parametrize('field', ('resource', 'site', 'arguments'))
def test_operation_preparation_does_not_invoke_foreign_fields(field):
    from hmp_plugin import presentation_native_metadata as metadata
    from hmp_plugin import presentation_startup_artifacts as artifacts

    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign getter')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length')

        def __getitem__(self, index):
            calls.append('index')
            raise AssertionError('foreign index')

    owner = object()
    if field == 'resource':
        resource = Foreign()
    else:
        values = dict.fromkeys(artifacts._NativeMetadataResource._fields)
        values.update(owner=owner, site=(4, 'directory', 0), arguments=(1234,))
        values[field] = Foreign()
        resource = artifacts._NativeMetadataResource(**values)
    with pytest.raises(artifacts.ArtifactObservationError):
        metadata._prepare_metadata_operation(owner, resource)
    assert calls == []


def test_directory_consumer_preparation_refuses_foreign_operation():
    from hmp_plugin import presentation_native_metadata as metadata
    from hmp_plugin import presentation_startup_artifacts as artifacts

    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign operation getter')

    with pytest.raises(artifacts.ArtifactObservationError):
        metadata._prepare_directory_consumer(object(), Foreign())
    assert calls == []

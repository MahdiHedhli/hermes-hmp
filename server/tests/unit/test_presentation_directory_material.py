"""Consumer-constructor return drift refuses before result ownership publication."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('material_code', 'class_alias', 'file_registry'))
def test_directory_constructor_return_material_drift(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from types import ModuleType
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.runtime_reader import RuntimeSourceReadOwner
from hmp_plugin import presentation_startup_artifacts as a
from hmp_plugin import presentation_native_metadata as m
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeSourceReadOwner.retain(continuation,index)
seen=[];injected=[];restore=[]
def no_action(self):return None
def drift(frame):
    if injected:return
    consumer=frame.f_locals['consumer']
    assert consumer.owner is owner
    if case=='material_code':
        original=consumer.material.__code__
        consumer.material.__code__=no_action.__code__
        restore.append(lambda:setattr(consumer.material,'__code__',original))
    elif case=='class_alias':
        namespace=vars(consumer.material_module);name=type(owner).__name__
        original=namespace[name];namespace[name]=object()
        restore.append(lambda:namespace.__setitem__(name,original))
    else:
        name='hmp_plugin.presentation_startup_artifacts'
        original=sys.modules[name];sys.modules[name]=ModuleType(name)
        restore.append(lambda:sys.modules.__setitem__(name,original))
    injected.append(True)
trace_synthetic_boundary(m._prepare_directory_consumer.__code__,
                         '_require(_resource_tail(owner, resource) is resource',drift)
def prepare(frame):
    if frame.f_locals['self'] is not owner or seen:return
    resource=a._prepare_native_metadata_resource(
        owner,frame.f_locals['native_registration'],frame.f_locals['native_walk'],
        frame.f_locals['row'])
    operation=m._prepare_metadata_operation(owner,resource)
    counts=tuple(operation.ledger.counts);attempts=len(operation.ledger.attempts)
    refused=False
    try:m._prepare_directory_consumer(owner,operation)
    except a.ArtifactObservationError:refused=True
    finally:
        for action in reversed(restore):action()
    assert injected==[True] and refused
    assert operation.result.consumer[0] is None
    assert operation.result.raw[0] is operation.result.unset
    assert counts==tuple(operation.ledger.counts) and len(operation.ledger.attempts)==attempts
    assert operation.phase.current[0] is operation.phase.idle
    assert operation.resource.metadata.progress==[0,None]
    seen.append(True)
trace_synthetic_boundary(a.StartupArtifactOwner._file.__code__,
                         'info = StartupArtifactOwner._fstat(self, fd, s, native_registration)',
                         prepare)
owner.read()
assert seen==[True] and owner._ready and not owner._failed and not owner._unknown
owner.release()
assert owner._original_buffer==bytearray()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

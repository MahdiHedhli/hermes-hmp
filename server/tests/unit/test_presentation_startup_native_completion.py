"""Full native entry completion without synthetic trace/profile instrumentation."""
from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


def test_native_startup_completion_without_observer(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += r'''
from hmp_plugin import presentation_startup_probe as probe
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
inputs=retained._inputs
row=next(row for row in inputs.cache_context_slot[0][3]
         if row.state=='needs_owned_absence')
Path(row.location.path).parent.mkdir(mode=0o700)
assert sys.gettrace() is None and sys.getprofile() is None
checked=EntryFileSnapshotOwner.complete(retained)
io=inputs.io_slot[0]
assert io._ready and not io._failed and not io._unknown
assert io._cache_fact is not None and io._fact_cell is not None
assert entry._activation._artifact_fact_cell is io._fact_cell
assert io._startup_probe_execution is None
source=io._origin.cache
assert source.before[0] is not None and source.after[0] is not None
assert source.before[0].phase==0 and source.after[0].phase==1
assert len(source.effects)==2*len(source.paths)>0
for effect in source.effects:
    assert effect.returned and not effect.unknown
    assert type(effect.native_finish) is probe._ProbeFinish
    assert effect.native_finish.execution.finished==[True]
    assert effect.native_finish.execution.failed==[False]
assert sys.gettrace() is None and sys.getprofile() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

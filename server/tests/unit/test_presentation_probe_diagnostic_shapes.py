"""Synthetic malformed stat reports never become acknowledged cache absence."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('wrong_errno', 'bool_errno', 'foreign_errno',
                                 'wrong_filename', 'foreign_filename', 'subclass',
                                 'permission', 'base_oserror', 'constructor_failure'))
def test_probe_diagnostic_shape_refusal(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ndiagnostic_case=' + repr(case) + '\n'
    script += r'''
import gc,os,errno
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
from hmp_plugin import presentation_native_metadata as metadata
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
faults=[];hooks=[];diagnostics=[];after_native=[];held=[];snapshots=[];references=[]
class Foreign:
    def __eq__(self,other):hooks.append('eq');raise AssertionError('foreign equality')
    def __bool__(self):hooks.append('bool');raise AssertionError('foreign bool')
    def __index__(self):hooks.append('index');raise AssertionError('foreign index')
    def __fspath__(self):hooks.append('path');raise AssertionError('foreign path')
class MissingSubclass(FileNotFoundError):
    @property
    def errno(self):hooks.append('errno');raise AssertionError('subclass errno')
    @property
    def filename(self):hooks.append('filename');raise AssertionError('subclass filename')
def observed(_frame):
    # This isolated script has one active probe. Observe every later metadata C call.
    if faults:after_native.append(True)
reg=owner._origin.native_registration_slot[0]
for call in reg.native_origin.operations[3:5]:
    observe_synthetic_native(call,metadata._produce_directory_metadata.__code__,observed)
prior=sys.getprofile();constructor_code=metadata._ReportedMissingMetadataReturn.__new__.__code__
def profile(frame,event,arg):
    if prior is not None:prior(frame,event,arg)
    if event=='call' and frame.f_code is constructor_code:diagnostics.append(True)
sys.setprofile(profile)
def inject(_frame):
    # Do not materialize producer f_locals: older CPython can retain that debugger
    # snapshot in an exception cycle even after the real fast locals are cleared.
    execution=owner._probe_execution
    if execution is None or faults:return
    consumer=execution.pending[0]
    assert type(consumer) is metadata._ProbeConsumer and consumer.execution is execution
    operation=consumer.operation
    assert type(operation) is metadata._MetadataOperation and operation.owner is owner
    assert operation.registration is reg and reg.native_ledger.inflight[0] is operation
    name=operation.arguments[0]
    if name!='__pycache__':return
    faults.append(True);held.extend(owner._origin.records)
    snapshots.append((operation,tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts)))
    references.append(operation.result.custody_slot[0].reference)
    if diagnostic_case=='constructor_failure':raise RuntimeError('SYNTHETIC_DIAGNOSTIC_CONSTRUCTOR_LOSS_ONLY')
    if diagnostic_case=='permission':raise PermissionError(errno.EACCES,'synthetic',name)
    if diagnostic_case=='subclass':raise MissingSubclass(errno.ENOENT,'synthetic',name)
    if diagnostic_case=='base_oserror':
        error=OSError();error.errno=errno.ENOENT;error.filename=name
        raise error
    number=(errno.EACCES if diagnostic_case=='wrong_errno' else
            True if diagnostic_case=='bool_errno' else
            Foreign() if diagnostic_case=='foreign_errno' else errno.ENOENT)
    filename=('SYNTHETIC_OTHER_COMPONENT' if diagnostic_case=='wrong_filename' else
              Foreign() if diagnostic_case=='foreign_filename' else name)
    raise FileNotFoundError(number,'synthetic',filename)
fragment=('missing = _ReportedMissingMetadataReturn(' if diagnostic_case=='constructor_failure' else
          'raw = callee(arguments[0], dir_fd=')
trace_synthetic_boundary(metadata._produce_directory_metadata.__code__,fragment,inject)
old_gc=gc.isenabled();gc.disable();refused=False
try:
    try:
        try:owner.observe()
        except CacheProbeError:refused=True
    finally:
        sys.setprofile(prior)
    assert not gc.isenabled()
    assert len(snapshots)==1
    operation,budget,attempts=snapshots[0]
    facts={'case':diagnostic_case,'faults':len(faults),'refused':refused,
           'foreign_hooks':list(hooks),'diagnostic_constructors':len(diagnostics),
           'native_after_fault':len(after_native),'known':len(held),'closed':sum(row.closed for row in held),
           'raw_alive':sum(ref() is not None for ref in references),'fact_published':owner._fact is not None}
    path=Path(sys.argv[1])/'probe-diagnostic-shape-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
    assert faults==[True] and refused and owner._failed and not owner._ready
    assert hooks==[] and diagnostics==[] and after_native==[]
    assert owner._fact is None and owner._origin.activation._runtime_cache_probe_fact is None
    assert operation.ended==[True] and operation.state==[True,False,True]
    assert operation.result.acknowledged==[None]
    assert held and all(row.closed and row.close_attempted and not row.unknown for row in held)
    assert reg.native_ledger.counts==[budget[0]+len(held),budget[1]-len(held)]
    assert len(reg.native_ledger.attempts)==attempts and reg.native_ledger.failed==[True]
    assert all(ref() is None for ref in references) and owner._bytes_read==0
finally:
    if old_gc:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

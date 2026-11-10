"""Executable-link acceptance through the actual isolated startup caller.

These checks intentionally cover the unfinished native traversal, rather than
using the passing policy/encoding DATA tests as evidence of image delivery.
All filesystem input is synthetic and lives in the disposable child fixture.
"""
from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


def test_actual_native_link_traversal_contract(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += r'''
import gc,weakref
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
lineage=entry._scope.native_files
ledger=lineage.ledger
operations=lineage.native.operations
path_code=a.StartupArtifactOwner._link_path.__code__
observed=[];capsules=[]

def observe(frame,event,callee):
    if event!='c_call':return
    if callee is operations[3]:opcode=3
    elif callee is operations[4]:opcode=4
    elif callee is operations[5]:opcode=5
    else:return
    # Observe real native effects only while the actual fixed link caller is
    # on the stack. Bootstrap/source/cache observations cannot satisfy this.
    parent=frame
    for _ in range(64):
        if parent is None:return
        if parent.f_code is path_code:break
        parent=parent.f_back
    else:return
    observed.append((opcode,ledger.inflight[0],ledger.counts[0],ledger.phase.current[0]))
    if opcode==5 and ledger.inflight[0] is not None:
        actual=ledger.inflight[0]
        result=actual.result
        origin=result.custody_origin
        payload=result.custody_link[0]
        cells=tuple(member.__get__(payload,origin.payload_type) for member in origin.members)
        # Weak payload reference and raw slot identities, never the raw-bearing
        # payload/producer frame itself. GC cannot disguise an owned cycle.
        capsules.append((actual,weakref.ref(payload),cells,result.unset))

previous=sys.getprofile()
assert previous is None and sys.gettrace() is None
codes=(a.StartupArtifactOwner._stat.__code__,a.StartupArtifactOwner._fstat.__code__,
       a.StartupArtifactOwner._readlink.__code__,
       presentation_native_metadata._produce_directory_metadata.__code__)
monitor=getattr(sys,'monitoring',None)
gc_was_enabled=gc.isenabled();gc.disable()
floor_path=[]
if monitor is None:
    # Older CPython lacks local C monitoring. Observe actual C calls for the
    # first complete hop path, then remove both observers before later startup
    # work. This is explicitly a subset, not all-phase floor qualification.
    def floor_path_return(frame,event,value):
        if event=='return':
            sys.setprofile(previous)
            sys.settrace(None)
            floor_path.append('returned')
        return floor_path_return
    def floor_trace(frame,event,value):
        if event=='call' and frame.f_code is path_code and not floor_path:
            floor_path.append('entered')
            frame.f_trace_lines=False
            sys.setprofile(observe)
            return floor_path_return
        return None
    sys.settrace(floor_trace)
else:
    monitor.use_tool_id(5,'hermes-synthetic-native-link-contract')
    def local_call(code,offset,callee,arg0):
        frame=sys._getframe(1)
        assert frame.f_code is code
        observe(frame,'c_call',callee)
    monitor.register_callback(5,monitor.events.CALL,local_call)
    for code in codes:monitor.set_local_events(5,code,monitor.events.CALL)
try:
    checked=EntryFileSnapshotOwner.complete(retained)
finally:
    if monitor is None:
        sys.setprofile(previous)
        sys.settrace(None)
    else:
        for code in codes:monitor.set_local_events(5,code,0)
        monitor.register_callback(5,monitor.events.CALL,None)
        monitor.free_tool_id(5)

# Completion is asserted OUTSIDE any refusal handler: preflight rejection or
# a swallowed callback exception must never make an admission test green.
assert checked._ready and not checked._failed
owner=checked._fact_cell[2]
runtime=owner._origin.runtime
assert owner._ready and not owner._failed and not owner._unknown
assert owner._origin.native_files is lineage
assert owner._origin.native_link_blueprint is not None
assert all(a._descriptor_closed_in_scope(row,owner._origin) for row in owner._origin.records)
metadata=[row for row in observed if row[0] in (3,4)]
links=[row for row in observed if row[0]==5]
assert metadata
if monitor is None:
    assert floor_path==['entered','returned'] and len(links)==1
else:
    assert len(links)==2*len(runtime.link.hops)>0
assert len(runtime.reads)==2*len(runtime.link.hops)
assert runtime.before[0] is not None and runtime.after[0] is not None
assert all(row.attempted and row.returned and not row.unknown for row in runtime.reads)

typed_metadata=sum(row[1] is not None and getattr(row[1],'operation',None)==row[0]
                   for row in metadata)
typed_links=sum(row[1] is not None and getattr(row[1],'operation',None)==5
                for row in links)
raw_records=sum(type(getattr(row,'data',None)) is bytes for row in runtime.reads)
raw_snapshots=sum(type(getattr(row,'data',None)) is bytes
                  for snapshot in (runtime.before[0],runtime.after[0])
                  for row in snapshot.reads)
violations=[]
if typed_metadata!=len(metadata):violations.append('metadata_admission')
if typed_links!=len(links):violations.append('readlink_admission')
if raw_records or raw_snapshots:violations.append('raw_retirement')
evidence=dict(metadata_calls=len(metadata),typed_metadata_calls=typed_metadata,
              readlink_calls=len(links),typed_readlink_calls=typed_links,
              retained_raw_records=raw_records,retained_raw_snapshots=raw_snapshots,
              completed=True,violations=violations,
              observer_scope=('first_hop_before' if monitor is None else 'all_link_paths'))
evidence_path=base/'native-link-contract.json'
evidence_path.write_text(json.dumps(evidence,sort_keys=True))
evidence_path.chmod(0o600)

if typed_metadata==len(metadata):
    for opcode,actual,used,phase in metadata:
        assert actual.operation==opcode and actual.callee is operations[opcode]
        assert type(actual.index) is int and 0<=actual.index<len(ledger.attempts)
        assert ledger.attempts[actual.index] is actual and actual.result.attempt[0] is actual
        assert actual.budget[3]==used
        assert phase is ledger.phase.active
        assert actual.result.acknowledged[0] is not None
if typed_links==len(links):
    for opcode,actual,used,phase in links:
        assert actual.operation==5 and actual.callee is operations[5]
        assert type(actual.index) is int and 0<=actual.index<len(ledger.attempts)
        assert ledger.attempts[actual.index] is actual and actual.result.attempt[0] is actual
        assert actual.budget[3]==used
        assert phase is ledger.phase.active
        assert actual.result.acknowledged[0] is not None
if not raw_records and not raw_snapshots:
    for row in runtime.reads:
        assert type(row.length) is int and row.length==len(row.hop.target)
        assert row.acknowledgement is not None
    assert len(capsules)==len(links) and not gc.isenabled()
    for actual,reference,cells,unset in capsules:
        assert actual.result.acknowledged[0] is not None
        assert reference() is None
        assert type(actual.result.custody_link) is list and len(actual.result.custody_link)==1
        assert actual.result.custody_link[0] is None
        assert all(type(cell) is list and len(cell)==1 for cell in cells)
        assert cells[0][0] is unset
        assert cells[1][0] is cells[2][0] is cells[3][0] is None
        assert cells[4][0] is not None and type(cells[4][0]) is not bytes
if gc_was_enabled:gc.enable()
assert violations==[], evidence
assert sys.gettrace() is None and sys.getprofile() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

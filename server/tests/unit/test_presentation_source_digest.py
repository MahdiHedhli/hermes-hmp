"""Original package and pending source reads, never runtime admission."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize("case", ("normal", "owner_foreign", "context_foreign",
                                 "expected_foreign", "buffer_swap", "count_copy",
                                 "read_record_copy", "read_result_copy", "split_reads",
                                 "hash_lost_ack", "replay", "coherent_read_copy",
                                 "read_entry_copy", "final_hash_copy",
                                 "final_read_copy", "final_context_remove",
                                 "linear_reads", "late_old_read"))
def test_original_source_digest_reads(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    assert 'GatewayPackageOwner.verify_recipe(recipe)' in script
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'plugin = GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)'
    assert marker in script
    disturbance = r"""
from hmp_plugin import presentation_source_digest as sd
source_case=CASE_VALUE
positive_cases=('normal','split_reads','replay','final_hash_copy',
                'final_read_copy','final_context_remove','linear_reads')
foreign_calls=[]
replacement=bytearray(b'SYNTHETIC_REPLACEMENT')
captured=[]
actual_append=sd.append
class Foreign:
    def __getattr__(self,name):foreign_calls.append(name);raise AssertionError('foreign getter')
    def __iter__(self):foreign_calls.append('iter');raise AssertionError('foreign iteration')
def disturbed(root,buffer,chunk,observations):
    actual_append(root,buffer,chunk,observations)
    if (root is not None and not captured and source_case not in positive_cases
        and (source_case!='late_old_read' or root.effect.consumed>=3)):
        captured.append(root)
        if source_case=='owner_foreign':root.effect.owner=Foreign()
        if source_case=='expected_foreign':root.effect.expected=Foreign()
        if source_case=='context_foreign':
            root.effect.context=root.context._replace(effects=Foreign())
        if source_case=='buffer_swap':root.effect.buffer=replacement
        if source_case=='count_copy':root.owner._count_cell=tuple(list(root.owner._count_cell))
        if source_case=='read_record_copy':
            read=root.reads[-1]
            root.scope.reads[read.index]=a._ReadEffect(read.before,read.record.after,True,False)
        if source_case=='read_result_copy':
            read=root.reads[-1];old=read.result[0]
            read.result[0]=(tuple(list(old[0])),old[1])
        if source_case=='coherent_read_copy':
            read=root.reads[-1];old=read.result[0];copied=tuple(list(old[0]))
            read.record.after=copied;read.result[0]=(copied,old[1])
            root.owner._count_cell=copied
        if source_case=='read_entry_copy':root.reads[-1]=root.reads[-1]._replace()
        if source_case=='late_old_read':
            read=root.reads[0];old=read.result[0];copy=tuple(list(old[0]))
            read.record.after=copy;read.result[0]=(copy,old[1])



sd.append=disturbed
read_result_calls=0
actual_read_result=sd._read_result
if source_case=='linear_reads':
    def counted(*args):
        global read_result_calls
        read_result_calls+=1
        return actual_read_result(*args)
    sd._read_result=counted
actual_finish=sd.finish
if source_case=='hash_lost_ack':
    def lost(root,buffer,count,observations):
        actual_finish(root,buffer,count,observations)
        raise OSError('synthetic lost hash acknowledgement')
    sd.finish=lost
if source_case in ('split_reads','linear_reads','late_old_read'):
    actual_read=a.os.read
    def split(fd,count):return actual_read(fd,min(count,257))
    a.os.read=split
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
except Exception:
    assert source_case not in positive_cases
    root=captured[0]
    assert root.buffer==bytearray() and root.effect.cleared
    assert not entry._activation._package_owner._ready
    assert entry._activation._package_owner._failed
    assert entry._activation._package_fact_cell is None
    assert foreign_calls==[]
    if source_case=='late_old_read':assert root.effect.returned
    if source_case=='hash_lost_ack':
        assert root.effect.attempted and root.effect.returned and root.effect.unknown
        before=(root.effect.result,root.effect.after,len(root.reads))
        try:actual_finish(root,root.buffer,root.effect.after,[])
        except sd.SourceDigestError:pass
        else:raise AssertionError('hash replay')
        assert before==(root.effect.result,root.effect.after,len(root.reads))
    assert replacement==bytearray(b'SYNTHETIC_REPLACEMENT')
    print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
    raise SystemExit(0)
""".replace('CASE_VALUE',repr(case))
    script = script.replace(marker, disturbance, 1)

    script = script[:script.rfind('print(json.dumps')]
    script += r'''
context=plugin._origin.source_digest
assert context is not None and checked._fact_cell[2]._origin.source_digest is context
receipts=(*plugin._fact[4],*checked._fact_cell[3][2])
count=0
for receipt in receipts:
    if not receipt.expected.path.endswith('.py'):
        assert receipt.source_hash==b'' and receipt.source_digest is None
        continue
    fact=receipt.source_digest
    assert sd.seal_fact(fact) is fact
    root=fact.root
    effect=root.effect
    assert effect.context is context and effect.owner is receipt.owner
    assert effect.expected is receipt.expected and effect.scope is receipt.scope
    assert effect.attempted and effect.returned and effect.cleared and not effect.unknown
    assert effect.buffer==bytearray() and effect.result is receipt.source_hash
    assert len(receipt.source_hash)==8
    assert effect.after[2]-effect.before[2]==receipt.expected.size
    assert receipt.source_hash==context.interpreter.source_hash.builtin(
        context.interpreter.source_hash.key,Path(receipt.expected.path).read_bytes())
    assert root.reads[-1].result[0][1]==0
    assert effect.consumed==len(root.reads)
    if source_case=='replay':
        try:actual_finish(root,root.buffer,effect.after,[])
        except sd.SourceDigestError:pass
        else:raise AssertionError('cleared hash replay')
    count+=1
assert count>1 and len(context.effects)==count
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.bytecode_headers import selected_source_hashes
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
if source_case.startswith('final_'):
    api=continuation._source.approval_binding[0].parent
    actual_path=api.namespace['Path']
    target=next(receipt.source_digest for receipt in receipts
                if receipt.expected.path.endswith('.py'))
    callbacks=0
    def native_boundary(value):
        global callbacks
        callbacks+=1
        if callbacks==2:
            if source_case=='final_hash_copy':
                target.root.effect.result=bytes(bytearray(target.source_hash))
            elif source_case=='final_read_copy':
                read=target.root.reads[0];old=read.result[0];copy=tuple(list(old[0]))
                read.record.after=copy;read.result[0]=(copy,old[1])
            else:
                context.effects[:]=[root for root in context.effects if root is not target.root]
        return actual_path(value)
    api.namespace['Path']=native_boundary
    try:selected_source_hashes(continuation)
    except sd.SourceDigestError:
        assert callbacks==2
        print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
        raise SystemExit(0)
    else:raise AssertionError('late source fact drift accepted')
selected=selected_source_hashes(continuation)
assert len(selected)==count
assert {id(row.receipt) for row in selected}=={
    id(row) for row in receipts if row.expected.path.endswith('.py')}
assert all(row.fact.root.context is context for row in selected)
if source_case=='linear_reads':
    total_reads=sum(len(root.reads) for root in context.effects)
    assert total_reads>100 and read_result_calls<=10*total_reads+100

print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)


def test_source_digest_malformed_metadata_no_hooks():
    from hmp_plugin import presentation_source_digest as sd

    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign getter')

        def __iter__(self):
            calls.append('iter')
            raise AssertionError('foreign iteration')

    foreign = Foreign()
    checks = (
        lambda: sd.current(foreign, foreign),
        lambda: sd.begin(foreign, foreign, foreign),
        lambda: sd.fact(foreign, foreign, foreign, foreign, b'12345678', (), []),
        lambda: sd.seal_fact(sd.SourceDigestFact(foreign, (), b'12345678', ())),
    )
    for check in checks:
        with pytest.raises(sd.SourceDigestError):
            check()
    assert calls == []


def test_legacy_source_receipts_refuse_selection(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script[:script.rfind('print(json.dumps')]
    script += r"""
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.bytecode_headers import selected_source_hashes,BytecodeHeaderError
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
try:selected_source_hashes(continuation)
except BytecodeHeaderError:pass
else:raise AssertionError('legacy source receipt accepted')
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
"""
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)


@pytest.mark.parametrize('case', ('none', 'foreign'))
def test_explicit_source_digest_entry_required(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    assert marker in script
    refusal = r"""
from hmp_plugin.presentation_gateway_package import PackageInventoryError
foreign_calls=[]
class Foreign:
    def __getattr__(self,name):foreign_calls.append(name);raise AssertionError('foreign entry')
candidate=None if CASE_VALUE=='none' else Foreign()
original_count=recipe._bytes_read
try:GatewayPackageOwner.verify_recipe_source_hashes(recipe,candidate)
except PackageInventoryError:
    assert foreign_calls==[] and entry._activation._package_fact_cell is None
    owner=entry._activation._package_owner
    if CASE_VALUE=='none':assert owner is None
    else:
        assert owner is not None and owner._failed and not owner._ready
        assert owner._origin is None and owner._bytes_read==original_count
else:raise AssertionError('invalid explicit source entry accepted')
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
""".replace('CASE_VALUE',repr(case))
    script = script.replace(marker, refusal, 1)
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

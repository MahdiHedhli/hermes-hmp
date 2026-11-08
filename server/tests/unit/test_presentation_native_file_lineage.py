"""Original entry-lineage identity; no file-effect or fallback qualification."""
from __future__ import annotations

import pytest

from . import test_presentation_gateway_entry as base

CASES = ('normal', 'copied_context', 'foreign_context', 'copied_scope',
         'foreign_scope', 'legacy_scope')
BODY = r'''
from hmp_plugin.presentation_source_digest import retain,current,SourceDigestError
from hmp_plugin.presentation_startup_artifacts import _Scope,_HashedArtifact
assert _HashedArtifact._fields==('owner','scope','expected','identity','sha256',
    'bytecode_header','source_hash','source_digest','source_mtime')
receipt=_HashedArtifact(None,None,None,(),'',b'',b'',None,123)
assert receipt.source_mtime==123 and receipt.source_digest is None
lineage=GatewayEntryOwner._native_file_lineage(owner)
assert lineage is owner._scope.native_files
assert lineage.entry is owner and lineage.native is owner._scope.interpreter.native_io
assert lineage.context is owner._scope.context
calls=[]
class Foreign:
    def __getattr__(self,name):calls.append('get');raise AssertionError('foreign getter')
    def __eq__(self,other):calls.append('eq');raise AssertionError('foreign equality')
context=retain(owner,owner._activation)
assert context.native_files is lineage
case=LINEAGE_CASE
if case=='copied_context':context=context._replace(native_files=lineage._replace())
if case=='foreign_context':context=context._replace(native_files=Foreign())
scope=_Scope(owner._activation,owner._activation._scope,(),lineage.context,[],
             source_digest=context,native_files=lineage)
if case=='copied_scope':scope=scope._replace(native_files=lineage._replace())
if case=='foreign_scope':scope=scope._replace(native_files=Foreign())
if case=='legacy_scope':scope=scope._replace(source_digest=None,native_files=None)
try:current(context,scope)
except SourceDigestError:assert case!='normal'
else:assert case=='normal'
assert calls==[]
assert GatewayEntryOwner._native_file_lineage(owner) is lineage
'''


@pytest.mark.parametrize('case', CASES)
def test_original_native_file_lineage(tmp_path, monkeypatch, case):
    marker = 'assert getattr(entry, "bootstrap_effect_count", 0) =='
    assert base.SCRIPT.count(marker) == 1
    injected = BODY.replace('LINEAGE_CASE', repr(case))
    monkeypatch.setattr(base, 'SCRIPT', base.SCRIPT.replace(marker, injected + '\n' + marker))
    base.test_original_invocation_through_bootstrap(tmp_path, 'normal')


@pytest.mark.parametrize('kind', ('probe', 'reader'))
@pytest.mark.parametrize('replacement', ('copy', 'foreign'))
def test_retained_scope_rejects_wrong_native_lineage(tmp_path, monkeypatch, kind, replacement):
    from . import test_presentation_cache_probe as probe
    from . import test_presentation_cache_reader as reader
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    klass, error, module = (('RuntimeCacheProbeOwner', 'CacheProbeError', 'pm')
                            if kind == 'probe' else
                            ('DeclaredCacheReadOwner', 'CacheReadError', 'cm'))
    marker = f'owner={klass}.retain(continuation,index)'
    injection = r'''
foreign_calls=[]
class ForeignLineage:
    def __getattr__(self,name):foreign_calls.append('get');raise AssertionError('foreign getter')
    def __eq__(self,other):foreign_calls.append('eq');raise AssertionError('foreign equality')
expected_lineage=entry._scope.native_files
bad_lineage=expected_lineage._replace() if REPLACEMENT=='copy' else ForeignLineage()
scope_type=MODULE._Scope
actual_new=scope_type.__new__
def changed_scope(kind,*args,**kwargs):
    result=actual_new(kind,*args,**kwargs)
    return result._replace(native_files=bad_lineage)
scope_type.__new__=staticmethod(changed_scope)
try:
    try:CLASS.retain(continuation,index)
    except ERROR as refused:
        failed=refused.failed_owner
        assert failed is MODULE._OWNER and failed._failed
        assert failed._origin.native_files is bad_lineage
        assert failed._origin.records==[] and failed._bytes_read==0
        assert failed._started is False
    else:raise AssertionError('substituted lineage constructor accepted')
finally:scope_type.__new__=actual_new
assert foreign_calls==[]
assert checked._fact_cell[2]._count_cell is old_count
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('REPLACEMENT', repr(replacement)).replace('MODULE', module)
    injection = injection.replace('CLASS', klass).replace('ERROR', error)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injection))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    if kind == 'probe':
        probe.test_fresh_cache_probe(tmp_path, monkeypatch, 'missing')
    else:
        reader.test_declared_cache_reader(tmp_path, monkeypatch, 'normal')

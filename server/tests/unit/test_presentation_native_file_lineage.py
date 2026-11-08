"""Original entry-lineage identity; no file-effect or fallback qualification."""
from __future__ import annotations

import pytest

from . import test_presentation_gateway_entry as base

CASES = ('normal', 'copied_context', 'foreign_context', 'copied_scope',
         'foreign_scope', 'legacy_scope')
BODY = r'''
from hmp_plugin.presentation_source_digest import retain,current,SourceDigestError
from hmp_plugin.presentation_startup_artifacts import _Scope
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

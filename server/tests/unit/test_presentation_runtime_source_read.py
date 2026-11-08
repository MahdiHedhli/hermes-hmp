"""Fresh source phase with original continuation and isolated synthetic files."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'changed_source', 'buffer_swap', 'repeat',
                                 'initial_context', 'context_buffer_swap', 'release_swap',
                                 'wrong_release_context', 'foreign_expected',
                                 'retain_context_buffer_swap', 'same_length_buffer',
                                 'parent_source_swap', 'count_copy', 'source_fact_copy'))
def test_runtime_source_read(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.runtime_reader import RuntimeSourceReadOwner, RuntimeReadError
from hmp_startup.cache_selection import selected_cache_input_attempts
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
old_count=checked._fact_cell[2]._count_cell
if case=='retain_context_buffer_swap':
    from hmp_startup import runtime_reader as rr
    actual_context=rr._context
    replacement=bytearray(b'PRESERVE_RETAIN_REPLACEMENT')
    def swap_retain():
        rr._OWNER._original_buffer=rr._OWNER._buffer=replacement
        return actual_context()
    rr._context=swap_retain
    try:RuntimeSourceReadOwner.retain(continuation,index)
    except RuntimeReadError as exc:
        assert exc.failed_owner._failed and replacement==b'PRESERVE_RETAIN_REPLACEMENT'
        assert checked._fact_cell[2]._count_cell is old_count
        print(json.dumps({'mutation':mutation,'runtime_admitted':False}));raise SystemExit(0)
    else:raise AssertionError('retain adopted replacement buffer')
owner=RuntimeSourceReadOwner.retain(continuation,index)
assert owner._origin.native_files is continuation._source.entry_binding[0].native_files
assert owner._origin.source_digest.native_files is owner._origin.native_files
original=owner._original_buffer
if case=='changed_source':(dep_root/'__init__.py').write_bytes(b'CHANGED_SYNTHETIC_SOURCE_ONLY\n')
if case in ('count_copy','source_fact_copy'):
    from hmp_plugin.presentation_startup_artifacts import StartupArtifactOwner
    actual_file=StartupArtifactOwner._file
    def replace_after(self,expected,native_registration=None):
        receipt=actual_file(self,expected,native_registration)
        if self is owner:
            copied=tuple(list(owner._count_cell))
            if case=='count_copy':owner._count_cell=copied
            else:receipt=receipt._replace(source_digest=receipt.source_digest._replace(count=copied))
        return receipt
    StartupArtifactOwner._file=replace_after
if case=='same_length_buffer':
    actual_append=RuntimeSourceReadOwner._append
    def poison(self,data):
        actual_append(self,data)
        if self is owner and self._buffer:self._buffer[0]^=1
    RuntimeSourceReadOwner._append=poison
if case=='parent_source_swap':
    foreign_calls=[]
    class Foreign:
        def __getattr__(self,name):foreign_calls.append(name);raise AssertionError('foreign source')
    continuation._source=Foreign()
if case=='foreign_expected':
    from hmp_plugin.presentation_startup_artifacts import StartupArtifactOwner, ExpectedArtifact
    try:StartupArtifactOwner._file(owner,ExpectedArtifact('/unapproved/no-read',0,'0'*64))
    except Exception:pass
    else:raise AssertionError('unapproved expected artifact accepted')
    assert owner._origin.records==[]
if case in ('initial_context','context_buffer_swap'):
    from hmp_startup import runtime_reader as rr
    actual_context=rr._context
    def disturb():
        if case=='context_buffer_swap':
            owner._original_buffer=owner._buffer=bytearray(b'FOREIGN_CONTEXT_BUFFER')
            return actual_context()
        return (-1,-1,-1)
    rr._context=disturb
if case=='buffer_swap':
    from hmp_plugin.presentation_startup_artifacts import StartupArtifactOwner
    actual=StartupArtifactOwner._read
    replacement=bytearray(b'PRESERVE_REPLACEMENT')
    def swap(self,fd,count,s,native_registration=None):
        data=actual(self,fd,count,s,native_registration)
        if self is owner:self._buffer=replacement
        return data
    StartupArtifactOwner._read=swap
try:owner.read()
except RuntimeReadError:
    assert case in ('changed_source','buffer_swap','initial_context','context_buffer_swap',
                    'parent_source_swap','same_length_buffer','count_copy','source_fact_copy')
    assert len(original)==0 and owner._failed is True
    if case=='parent_source_swap':assert foreign_calls==[]
    if case=='buffer_swap':assert replacement==b'PRESERVE_REPLACEMENT'
    if case=='initial_context':
        rr._context=actual_context
        try:owner.read()
        except RuntimeReadError:pass
        else:raise AssertionError('failed initial attempt retried')
else:
    assert case in ('normal','repeat','release_swap','wrong_release_context','foreign_expected')
    assert owner._ready and bytes(original)==(dep_root/'__init__.py').read_bytes()
    assert owner._bytes_read==len(original)
    if case=='repeat':
        try:owner.read()
        except RuntimeReadError:pass
        else:raise AssertionError('replayed runtime read')
    if case=='release_swap':
        replacement=bytearray(b'PRESERVE_RELEASE_REPLACEMENT')
        owner._original_buffer=owner._buffer=replacement
    if case=='wrong_release_context':
        from hmp_startup import runtime_reader as rr
        actual_context=rr._context;rr._context=lambda:(-1,-1,-1)
        try:owner.release()
        except RuntimeReadError:pass
        else:raise AssertionError('foreign context released source')
        assert len(original)>0 and not owner._released
        rr._context=actual_context
    owner.release();assert len(original)==0
    if case=='release_swap':assert replacement==b'PRESERVE_RELEASE_REPLACEMENT'
assert checked._fact_cell[2]._count_cell is old_count
assert all(row.closed and row.close_attempted and not row.unknown for row in owner._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)


def test_legacy_artifact_dispatch_does_not_import_runtime_reader(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    script = tmp_path / 'legacy_dispatch.py'
    script.write_text("""
import sys
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
from hmp_plugin.presentation_startup_artifacts import (
    StartupArtifactOwner,_configuration,_append_configuration,_root)
assert 'hmp_startup.runtime_reader' not in sys.modules
owner=StartupArtifactOwner.__new__(StartupArtifactOwner)
assert _configuration(owner) is False
_append_configuration(owner,b'')
marker=object()
assert _root(owner,SimpleNamespace(_artifact_cell=marker)) is marker
from hmp_plugin.presentation_source_digest import _types
from hmp_plugin.presentation_startup_artifacts import ExpectedArtifact,_Scope
scope=_Scope(None,None,(),(),[])
_types(owner,scope,ExpectedArtifact('/synthetic/source.py',0,'0'*64))
assert 'hmp_startup.runtime_reader' not in sys.modules
""")
    result = subprocess.run([sys.executable, '-I', '-B', str(script),
                             str(Path(__file__).resolve().parents[2])],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr

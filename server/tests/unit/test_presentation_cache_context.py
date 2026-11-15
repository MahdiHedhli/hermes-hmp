"""Actual pre-IO owner and CWD metadata; no selected root source/cache is opened."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script

CASES = ('normal', 'independent_chdir', 'root_normal', 'root_chdir', 'root_callback_chdir',
         'root_cwd_deleted', 'wrong_thread', 'wrong_process', 'copied_fact',
         'coherent_callback_copy', 'continuation_copy', 'declared_cache', 'cache_directory',
         'foreign_entry_binding')
FINISH = r'''
from hmp_startup.cache_context import CacheContextOwner,CacheContextError
from hmp_startup import cache_context as cache_module
import os,threading
os.chdir(base)
foreign_calls=[]
if case=='foreign_entry_binding':
    original_retain=CacheContextOwner.retain.__func__
    class ForeignScope:
        def __getattr__(self,name):
            foreign_calls.append(name);raise AssertionError('foreign scope metadata')
    def malformed(cls,snapshot):
        inputs=snapshot._inputs
        binding=(ForeignScope(),*inputs.entry_binding[1:])
        changed=inputs._replace(entry_binding=binding)
        snapshot._inputs=changed
        snapshot._root_cell=(snapshot,changed)
        inputs.recipe_binding[0].activation._entry_files_cell=snapshot._root_cell
        return original_retain(cls,snapshot)
    CacheContextOwner.retain=classmethod(malformed)
if case=='root_cwd_deleted':
    gone=base/'deleted-cwd';gone.mkdir(mode=0o700);os.chdir(gone);gone.rmdir()
try:retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
except EntryFilesError as error:
    assert case in ('root_cwd_deleted','foreign_entry_binding')
    retained=error.failed_owner
    ctx=cache_module._OWNER
    assert retained._inputs.io_slot[0] is None and foreign_calls==[]
    if case=='foreign_entry_binding':
        assert ctx is None and retained._inputs.cache_context_slot[0] is None
    else:
        assert ctx._failed and not ctx._ready
        os.chdir(base)
        try:CacheContextOwner.current_binding(ctx)
        except CacheContextError:pass
        else:raise AssertionError('failed context resumed')
else:
    assert case not in ('root_cwd_deleted','foreign_entry_binding')
    inputs=retained._inputs
    fact=inputs.cache_context_slot[0];ctx=fact[0]
    assert type(ctx) is CacheContextOwner and ctx._ready and not ctx._failed
    assert CacheContextOwner.current_binding(ctx) is fact
    assert inputs.io_slot[0] is None and retained._attempt_cell is None
    assert fact[1] is retained._cache_context_cell
    assert all(row.state in ('declared','tree_expected_absent','tree_nonfile',
                              'needs_owned_absence') for row in fact[3])
    assert any(row.state=='needs_owned_absence' for row in fact[3])
    assert any(row.state=='tree_expected_absent' for row in fact[3])
    if case.startswith('root'):
        selected=next(row for row in fact[3] if row.source.path=='/SYNTHETIC_HMP_ROOT_SOURCE.py')
        assert selected.location.cwd_dependent and type(fact[2]) is str
        assert fact[2]==os.getcwd()
        assert selected.location.path.startswith(fact[2].rstrip('/')+'/__pycache__/')
    else:assert fact[2] is None and not ctx._source.requires_cwd
    if case in ('declared_cache','cache_directory'):
        selected=next(row for row in fact[3] if row.source.path==str(dep_root/'__init__.py'))
        assert selected.state==('declared' if case=='declared_cache' else 'tree_nonfile')
        assert (selected.cache is not None) is (case=='declared_cache')
    if case=='wrong_thread':
        refused=[]
        def wrong():
            try:CacheContextOwner.current_binding(ctx)
            except CacheContextError:refused.append(True)
        thread=threading.Thread(target=wrong);thread.start();thread.join()
        assert refused==[True] and not ctx._failed
        assert CacheContextOwner.current_binding(ctx) is fact
    if case=='wrong_process':
        pid=os.fork()
        if pid==0:
            try:
                try:CacheContextOwner.current_binding(ctx)
                except CacheContextError:pass
                else:raise AssertionError('foreign process accepted')
                assert not ctx._failed
                os._exit(0)
            except BaseException:os._exit(3)
        waited,status=os.waitpid(pid,0);assert waited==pid and status==0
        assert CacheContextOwner.current_binding(ctx) is fact
    oldcwd=os.getcwd()
    if case in ('root_chdir','independent_chdir','root_callback_chdir'):
        other=base/'alternate-cwd';other.mkdir(mode=0o700)
        if case=='root_callback_chdir':
            actual_pid=cache_module.os.getpid
            def change_cwd():
                value=actual_pid();os.chdir(other);return value
            cache_module.os.getpid=change_cwd
        else:os.chdir(other)
    if case=='copied_fact':
        replacement=tuple(list(fact));ctx._fact=inputs.cache_context_slot[0]=replacement
    if case=='coherent_callback_copy':
        actual_pid=cache_module.os.getpid
        def copy_context():
            value=actual_pid()
            newroot=tuple(list(ctx._root))
            newfact=(ctx,newroot,ctx._cwd,ctx._rows)
            ctx._root=cache_module._ROOT=retained._cache_context_cell=newroot
            ctx._fact=cache_module._FACT=inputs.cache_context_slot[0]=newfact
            return value
        cache_module.os.getpid=copy_context
    if case in ('root_chdir','root_callback_chdir','copied_fact','coherent_callback_copy'):
        try:CacheContextOwner.current_binding(ctx)
        except CacheContextError:pass
        else:raise AssertionError('changed original context accepted')
        assert ctx._failed
        os.chdir(oldcwd)
        try:CacheContextOwner.current_binding(ctx)
        except CacheContextError:pass
        else:raise AssertionError('failed context resurrected')
    elif case=='continuation_copy':
        from hmp_startup.gateway_continuation import (
            GatewayContinuationOwner,GatewayContinuationError)
        checked=EntryFileSnapshotOwner.complete(retained)
        continued=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
        replacement=tuple(list(fact))
        ctx._fact=cache_module._FACT=inputs.cache_context_slot[0]=replacement
        try:GatewayContinuationOwner.current_binding(continued)
        except GatewayContinuationError:pass
        else:raise AssertionError('continuation adopted replacement cache fact')
        assert continued._failed
    else:
        assert CacheContextOwner.current_binding(ctx) is fact
        os.chdir(oldcwd)
    if case!='continuation_copy':assert inputs.io_slot[0] is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_original_preio_cache_context(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    if case.startswith('root'):
        script = script.replace('entry = GatewayEntryOwner.start()',
                                'physical_body=Path(__file__).read_bytes()\n'
                                '__file__="/SYNTHETIC_HMP_ROOT_SOURCE.py"\n'
                                'entry = GatewayEntryOwner.start()', 1)
        script = script.replace('wrapper_body = wrapper_path.read_bytes()',
                                'wrapper_body = physical_body', 1)
    if case in ('declared_cache', 'cache_directory'):
        setup = ('import importlib.util\n'
                 'cache_path=Path(importlib.util.cache_from_source(str(dep_root/"__init__.py")))\n'
                 'cache_path.parent.mkdir(mode=0o700)\n')
        setup += ('cache_path.write_bytes(b"SYNTHETIC_CACHE_NOT_EXECUTED")\n'
                  if case == 'declared_cache' else 'cache_path.mkdir(mode=0o700)\n')
        script = script.replace('import sample_dep\n', 'import sample_dep\n' + setup, 1)
    script += '\ncase=' + repr(case) + '\n' + FINISH
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

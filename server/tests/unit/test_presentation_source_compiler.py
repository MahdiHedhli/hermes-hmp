"""Owned compilation of synthetic admitted source; no payload execution."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'source_changed', 'syntax_error', 'audit_refuse',
                                 'audit_builtin', 'audit_buffer', 'audit_count',
                                 'wrong_actor', 'wrong_thread', 'initial_guard', 'replay',
                                 'fact_copy', 'final_fact_copy', 'reentrant'))
def test_owned_source_compilation(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    if case == 'syntax_error':
        script = script.replace('import sample_dep\n',
                                'import sample_dep\n'
                                '(dep_root/"__init__.py").write_text('
                                '"def SYNTHETIC_PRIVATE_SYNTAX(\\n")\n', 1)
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
import builtins
from types import CodeType
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.runtime_reader import RuntimeSourceReadOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup import source_compiler as cm
from hmp_startup.source_compiler import SourceCompilationOwner,SourceCompileError
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
source=RuntimeSourceReadOwner.retain(continuation,index).read()
read=source.completed_binding();buffer=read[4];path=read[5].expected.path
owner=SourceCompilationOwner.retain(source)
original_compile=builtins.compile;events=[];foreign=[]
def audit(event,args):
    if event!='compile' or args[1]!=path:return
    events.append('compile')
    assert type(args[0]) is bytes
    if case=='audit_refuse':raise RuntimeError('SYNTHETIC_AUDIT_REFUSAL')
    if case=='audit_builtin':
        def replacement(*args,**kwargs):
            foreign.append(True);raise AssertionError('foreign compiler')
        builtins.compile=replacement
    if case=='audit_buffer':buffer[0]^=1
    if case=='audit_count':source._count_cell=tuple(list(source._count_cell))
    if case=='reentrant':
        try:owner.compile()
        except SourceCompileError:pass
        else:raise AssertionError('reentrant compilation')
sys.addaudithook(audit)
if case=='source_changed':buffer[0]^=1
if case=='wrong_actor':
    actual_context=cm._context;cm._context=lambda:(-1,-1,-1)
    try:owner.compile()
    except SourceCompileError:pass
    else:raise AssertionError('wrong actor admitted')
    assert not owner._failed and not owner._started and len(buffer)>0 and events==[]
    cm._context=actual_context
if case=='wrong_thread':
    import threading
    failures=[]
    def other_thread():
        try:owner.compile()
        except SourceCompileError:failures.append(True)
        else:failures.append(False)
    other=threading.Thread(target=other_thread);other.start();other.join(timeout=10)
    assert not other.is_alive() and failures==[True]
    assert not owner._started and not owner._failed and len(buffer)>0 and events==[]
if case=='initial_guard':
    actual_context=cm._context;contexts=0
    def fail_after_admission():
        global contexts
        contexts+=1
        return actual_context() if contexts==1 else (-1,-1,-1)
    cm._context=fail_after_admission
try:owner.compile()
except SourceCompileError as exc:
    assert case in ('source_changed','syntax_error','audit_refuse','audit_builtin','audit_buffer',
                    'audit_count','initial_guard')
    assert owner._failed and owner._started and not owner._ready
    assert exc.__context__ is None and not foreign
    assert 'SYNTHETIC_PRIVATE_SYNTAX' not in str(exc)
    tb=exc.__traceback__
    while tb:
        if tb.tb_frame.f_code.co_name=='compile':
            assert tb.tb_frame.f_locals['snapshot'] is None
            assert tb.tb_frame.f_locals['digest'] is None
            assert tb.tb_frame.f_locals['code'] is None
        tb=tb.tb_next
    assert events==([] if case in ('source_changed','initial_guard') else ['compile'])
    assert len(buffer)==0
    builtins.compile=original_compile
    try:owner.compile()
    except SourceCompileError:pass
    else:raise AssertionError('failed compilation replayed')
else:
    assert case in ('normal','replay','fact_copy','final_fact_copy','reentrant',
                    'wrong_actor','wrong_thread')
    fact=owner.current_binding()
    assert type(fact[3]) is CodeType and fact[3].co_filename==path
    assert fact[4] is read and source.historical_binding() is read
    assert len(buffer)==0 and source._released and events==['compile']
    if case=='replay':
        try:owner.compile()
        except SourceCompileError:pass
        else:raise AssertionError('successful compilation replayed')
        assert events==['compile'] and owner.current_binding() is fact
    if case=='final_fact_copy':
        actual_context=cm._context
        def copy_fact():
            copied=tuple(list(cm._FACT));cm._FACT=owner._fact=owner._scope.effect.fact=copied
            return actual_context()
        cm._context=copy_fact
        try:owner.current_binding()
        except SourceCompileError:pass
        else:raise AssertionError('final fact copy adopted')
    if case=='fact_copy':
        owner._fact=tuple(list(fact))
        try:owner.current_binding()
        except SourceCompileError:pass
        else:raise AssertionError('copied compiled fact adopted')
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

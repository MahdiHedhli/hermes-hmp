"""Interpreter/native export checks execute no loader, compiler or syscall."""
import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('name', ['_interpreter_graph_mirrors', '_native_io_graph_mirrors'])
@pytest.mark.parametrize('origin', [None, (), (None,), object()])
def test_foreign_origin_has_no_runtime_metadata(name, origin):
    assert getattr(artifacts, name)(origin) is False


def test_actual_interpreter_and_native_exports_without_effects(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += r'''
from hmp_startup import gateway_entry as entry_module
import os,threading
origin=entry._scope.interpreter;native=origin.native_io
probe=a._interpreter_graph_mirrors;io_probe=a._native_io_graph_mirrors
assert entry_module._interpreter_current(origin) is origin
ledger=entry._scope.native_file_ledger
baseline=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
calls=[];foreign=[];rows=[]
native_functions=(*native.operations,*native.actor_calls,origin.source_hash.builtin,
                  origin.source_compile.compiler,origin.cache_decode.loads,origin.cache_decode.fix_filename)
python_codes=(origin.source_hash.code,origin.source_compile.code,origin.cache_decode.code)
def observe(frame,event,callee):
    if event=='c_call' and any(callee is fn for fn in native_functions):calls.append('native')
    if event=='call' and any(frame.f_code is code for code in python_codes):calls.append('loader')
assert sys.getprofile() is None
sys.setprofile(observe)
try:
    assert probe(origin) is True and io_probe(native) is True
    assert probe(origin._replace(data=origin.data._replace())) is True
    assert io_probe(native._replace()) is True
    class ClassState:
        def __init__(self,kind):self.kind=kind
        def __getitem__(self,key):return vars(self.kind)[key]
        def __setitem__(self,key,value):type.__setattr__(self.kind,key,value)
        def __delitem__(self,key):type.__delattr__(self.kind,key)
    mutations=[
        ('sys',probe,origin,vars(sys),('implementation','version_info','flags','hexversion',
            'executable','prefix','exec_prefix','base_prefix','base_exec_prefix','_stdlib_dir',
            'platform','pycache_prefix','dont_write_bytecode')),
        ('implementation',probe,origin,vars(origin.implementation),('name','cache_tag')),
        ('util',probe,origin,vars(origin.bytecode_module),('MAGIC_NUMBER',)),
        ('imp',probe,origin,vars(origin.cache_policy.module),('check_hash_based_pycs','source_hash',
                                                            '_fix_co_filename')),
        ('hash-key',probe,origin,vars(origin.source_hash.key_owner),(origin.source_hash.key_name,)),
        ('loader',probe,origin,ClassState(origin.source_hash.loader_type),('get_code','source_to_code')),
        ('frozen',probe,origin,vars(origin.source_hash.module),('_imp','marshal','_code_type',
                                                             '_compile_bytecode','SourceLoader')),
        ('compiler',probe,origin,origin.source_compile.namespace,('compile',)),
        ('marshal',probe,origin,vars(origin.cache_decode.marshal_module),('loads',)),
        ('os',io_probe,native,vars(native.namespace),('name','open','read','close','stat','fstat','readlink',
            'O_RDONLY','O_NOFOLLOW','O_CLOEXEC','O_NONBLOCK','O_DIRECTORY','stat_result','error',
            'getpid','geteuid')),
        ('posix',io_probe,native,vars(native.native),('open','read','close','stat','fstat','readlink',
            'O_RDONLY','O_NOFOLLOW','O_CLOEXEC','O_NONBLOCK','O_DIRECTORY','stat_result','error',
            'getpid','geteuid')),
        ('threading',io_probe,native,vars(native.thread_namespace),('get_ident',)),
        ('_thread',io_probe,native,vars(native.thread_native),('get_ident',)),
        ('errors',io_probe,native,vars(entry_module.builtins),('OSError','FileNotFoundError','PermissionError')),
    ]
    for role,check,value,state,keys in mutations:
        for key in keys:
            old=state[key];state[key]=object()
            try:assert check(value) is False,(role,key,'replacement')
            finally:state[key]=old
            assert check(value) is True
            del state[key]
            try:assert check(value) is False,(role,key,'missing')
            finally:state[key]=old
            assert check(value) is True
            rows.extend(((role,key,'replacement'),(role,key,'missing')))
    class Foreign(str):
        def __eq__(self,other):
            foreign.append('eq');raise AssertionError('foreign equality')
        def __ne__(self,other):
            foreign.append('ne');raise AssertionError('foreign inequality')
    for function,check,value in ((native.operations[0],io_probe,native),
                                 (origin.source_hash.builtin,probe,origin),
                                 (origin.source_compile.function,probe,origin),
                                 (origin.cache_decode.function,probe,origin)):
        old=function.__module__;function.__module__=Foreign(old)
        try:assert check(value) is False
        finally:function.__module__=old
        assert check(value) is True
    for label,check,value in (('_InterpreterOrigin',probe,origin),
                              ('_NativeIOOrigin',io_probe,native)):
        short=tuple.__new__(getattr(entry_module,label),())
        assert check(short) is False
    armed=[False]
    class ForeignKey:
        def __hash__(self):return hash('source_hash')
        def __eq__(self,other):
            if armed[0]:
                foreign.append('key.eq');raise AssertionError('foreign key equality')
            return False
    state=vars(origin.cache_policy.module);old=state.pop('source_hash');key=ForeignKey();state[key]=old
    armed[0]=True
    try:assert probe(origin) is False
    finally:
        armed[0]=False;del state[key];state['source_hash']=old
    assert probe(origin) is True
finally:sys.setprofile(None)
assert calls==[] and foreign==[]
assert len(rows)==130,len(rows)
assert baseline==(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
assert entry_module._interpreter_current(origin) is origin
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

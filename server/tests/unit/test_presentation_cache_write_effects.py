"""Observe actual SourceLoader write effects without filesystem writes or execution."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CASES = ('timestamp_hit', 'hash_hit', 'absent', 'directory', 'bad_magic', 'short',
         'timestamp_stale', 'flags2_stale', 'hash_checked_stale', 'hash_unchecked_always',
         'writes_disabled', 'stat_unavailable', 'source_error', 'compile_error',
         'body_error', 'writer_not_implemented', 'writer_permission_error')
SCRIPT = r'''
import _imp, importlib.util, json, marshal, sys
from types import CodeType
sys.path.insert(0,sys.argv[1])
from hmp_startup.gateway_entry import _interpreter
origin=_interpreter().source_hash
case=sys.argv[2]
source=b'SYNTHETIC_WRITE_EFFECT_ONLY = 1\n'
path='/synthetic/write_effect.py';target=importlib.util.cache_from_source(path)
mtime=1700000000;flags=0;digest=origin.builtin(origin.key,source)
if case in ('hash_hit','hash_checked_stale'):flags=3
if case=='hash_unchecked_always':flags=1
if case=='flags2_stale':flags=2
header=importlib.util.MAGIC_NUMBER+flags.to_bytes(4,'little')
if flags&1:header+=digest if case=='hash_hit' else b'BAD_HASH'
else:
    header+=(mtime if case=='timestamp_hit' else 0).to_bytes(4,'little')
    header+=len(source).to_bytes(4,'little')
if case=='bad_magic':header=b'BAD!'+header[4:]
if case=='short':header=header[:15]
code=compile(source,path,'exec')
cache=header if case=='short' else header+(b'' if case=='body_error' else marshal.dumps(code))
# body_error must select a valid header before failing unmarshalling.
if case=='body_error':
    cache=importlib.util.MAGIC_NUMBER+(0).to_bytes(4,'little')
    cache+=mtime.to_bytes(4,'little')+len(source).to_bytes(4,'little')
reads=[];compiled=[];writes=[]
class Loader(origin.loader_type):
    def get_filename(self,name):return path
    def path_stats(self,p):
        assert p==path
        if case=='stat_unavailable':raise OSError('synthetic stat refusal')
        return {'mtime':mtime,'size':len(source)}
    def get_data(self,p):
        reads.append(p);assert p in (path,target)
        if p==path:
            if case=='source_error':raise PermissionError('synthetic source refusal')
            return source
        if case in ('absent','writes_disabled','source_error','compile_error',
                    'writer_not_implemented','writer_permission_error'):
            raise FileNotFoundError('synthetic absence')
        if case=='directory':raise IsADirectoryError('synthetic directory')
        return cache
    def source_to_code(self,data,p,*,_optimize=-1):
        compiled.append(data)
        if case=='compile_error':raise SyntaxError('synthetic compile refusal')
        return super().source_to_code(data,p,_optimize=_optimize)
    def _cache_bytecode(self,source_path,cache_path,data):
        assert source_path==path and cache_path==target
        writes.append(bytes(data))
        if case=='writer_not_implemented':raise NotImplementedError
        if case=='writer_permission_error':raise PermissionError('synthetic writer refusal')
old_mode=_imp.check_hash_based_pycs;old_write=sys.dont_write_bytecode
error=None
try:
    _imp.check_hash_based_pycs='always' if case=='hash_unchecked_always' else 'default'
    sys.dont_write_bytecode=case=='writes_disabled'
    try:result=origin.function(Loader(),'synthetic_write_effect')
    except (PermissionError,SyntaxError,EOFError) as exc:error=type(exc).__name__
    else:assert type(result) is CodeType
finally:
    _imp.check_hash_based_pycs=old_mode;sys.dont_write_bytecode=old_write
expected_error={'source_error':'PermissionError','compile_error':'SyntaxError',
                'body_error':'EOFError','writer_permission_error':'PermissionError'}.get(case)
assert error==expected_error,(case,error)
no_write=case in ('timestamp_hit','hash_hit','writes_disabled','stat_unavailable',
                 'source_error','compile_error','body_error')
assert len(writes)==(0 if no_write else 1),(case,len(writes))
if writes:
    data=writes[0];assert data[:4]==importlib.util.MAGIC_NUMBER
    actual_flags=int.from_bytes(data[4:8],'little')
    expected_flags=3 if case=='hash_checked_stale' else 1 if case=='hash_unchecked_always' else 0
    assert actual_flags==expected_flags,(case,actual_flags)
    if expected_flags:assert data[8:16]==digest
    else:
        assert int.from_bytes(data[8:12],'little')==mtime
        assert int.from_bytes(data[12:16],'little')==len(source)
    assert type(marshal.loads(data[16:])) is CodeType
if case=='stat_unavailable':assert target not in reads
assert len(compiled)==(0 if case in ('timestamp_hit','hash_hit','body_error','source_error') else 1)
if case=='timestamp_hit':assert path not in reads
if case=='hash_hit':assert reads.count(path)==1
print(json.dumps({'case':case,'writeAttempts':len(writes),'payloadExecuted':False,'cacheFilesystemWrites':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_actual_source_loader_write_effects(tmp_path, case):
    script = tmp_path / 'write_effect.py'
    script.write_text(SCRIPT)
    server = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, '-I', '-B', str(script), str(server), case],
        text=True, capture_output=True, timeout=20, env={'LANG': 'C', 'LC_ALL': 'C'},
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed['case'] == case and observed['payloadExecuted'] is False
    assert observed['cacheFilesystemWrites'] is False

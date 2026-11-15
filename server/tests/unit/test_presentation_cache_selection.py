"""Actual CPython input attempts over synthetic code; no payload execution."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CASES = (
    'timestamp', 'flags2', 'mtime_mismatch', 'size_mismatch', 'mtime_wrap', 'size_wrap',
    'negative_time', 'rounded_time', 'short', 'magic', 'bad_flags',
    'hash1_match_default', 'hash1_mismatch_default', 'hash1_mismatch_always',
    'hash1_mismatch_never', 'hash1_match_always', 'hash1_match_never',
    'hash3_match_default', 'hash3_mismatch_default', 'hash3_mismatch_always',
    'hash3_mismatch_never', 'hash3_match_always', 'absent', 'nonfile', 'unreadable',
    'stat_unavailable', 'source_read_error', 'body_eof', 'body_noncode',
)
SCRIPT = r'''
import _imp, importlib.util, json, marshal, sys
from types import CodeType
sys.path.insert(0,sys.argv[1])
from hmp_startup.cache_selection import source_loader_input
from hmp_startup.gateway_entry import _interpreter
case=sys.argv[2]
origin=_interpreter().source_hash
source=b'SYNTHETIC_CACHE_SELECTION_ONLY = 1\n'
path='/synthetic/cache_selection.py'
cache_path=importlib.util.cache_from_source(path)
cache_code=compile(b'SYNTHETIC_CACHE_SELECTION_ONLY = 2\n',path,'exec')
source_hash=origin.builtin(origin.key,source)
mtime=1700000000.25;size=len(source);flags=0;mode='default';state='declared'
if case=='flags2':flags=2
if case=='mtime_wrap':mtime=float(2**32+17)
if case=='size_wrap':size=2**32+len(source)
if case=='negative_time':mtime=-0.5
if case=='rounded_time':mtime=1700000000+0.999999999
if case.startswith('hash'):
    kind,match,mode=case.split('_');flags=int(kind[-1])
header=(importlib.util.MAGIC_NUMBER+flags.to_bytes(4,'little')
        +(int(mtime)&0xffffffff).to_bytes(4,'little')+(size&0xffffffff).to_bytes(4,'little'))
if flags&1:
    digest=source_hash if '_match_' in case else b'BAD_HASH'
    header=header[:8]+digest
if case=='mtime_mismatch':header=header[:8]+(1).to_bytes(4,'little')+header[12:]
if case=='size_mismatch':header=header[:12]+(1).to_bytes(4,'little')
if case=='magic':header=b'BAD!'+header[4:]
if case=='bad_flags':header=header[:4]+(4).to_bytes(4,'little')+header[8:]
if case=='short':header=header[:15]
payload=marshal.dumps(cache_code)
if case=='body_eof':payload=b''
if case=='body_noncode':payload=marshal.dumps(123)
cache=header if case=='short' else header+payload
if case in ('absent','nonfile','unreadable'):state=case
if case=='source_read_error':state='absent'
stamp=None if case=='stat_unavailable' else int(mtime)
known_size=None if stamp is None else size
observed_header=cache[:16] if state=='declared' else None
attempt=source_loader_input(observed_header,importlib.util.MAGIC_NUMBER,
                            stamp,known_size,source_hash,mode,state)
reads=[];compiled=[];writes=[]
class SyntheticLoader(origin.loader_type):
    def get_filename(self,fullname):return path
    def path_stats(self,selected):
        assert selected==path
        if case=='stat_unavailable':raise OSError('synthetic stat unavailable')
        return {'mtime':mtime,'size':size}
    def get_data(self,selected):
        assert selected in (path,cache_path)
        reads.append(selected)
        if selected==path:
            if case=='source_read_error':raise PermissionError('synthetic source read refusal')
            return source
        if state=='absent':raise FileNotFoundError('synthetic cache absent')
        if state=='nonfile':raise IsADirectoryError('synthetic cache directory')
        if state=='unreadable':raise PermissionError('synthetic cache unreadable')
        return cache
    def source_to_code(self,data,selected,*,_optimize=-1):
        compiled.append(data)
        return super().source_to_code(data,selected,_optimize=_optimize)
    def set_data(self,*args,**kwargs):writes.append(True)
old=_imp.check_hash_based_pycs
try:
    _imp.check_hash_based_pycs=mode
    try:result=origin.function(SyntheticLoader(),'synthetic_cache_selection')
    except (EOFError,ImportError,PermissionError):
        if case=='source_read_error':
            assert attempt.input=='source' and path in reads
        else:
            assert case in ('body_eof','body_noncode')
            assert attempt.input=='cache' and not compiled and cache_path in reads
    else:
        assert type(result) is CodeType
        actual='source' if compiled else 'cache'
        assert actual==attempt.input,(case,actual,attempt)
        assert (1 if actual=='source' else 2) in result.co_consts
finally:_imp.check_hash_based_pycs=old
assert not writes
if case=='stat_unavailable':assert cache_path not in reads
if case=='flags2':assert attempt.validation=='timestamp'
print(json.dumps({'case':case,'inputAttempt':attempt.input,'payloadExecuted':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_actual_source_loader_input_attempt(tmp_path, case):
    script = tmp_path / 'cache_input.py'
    script.write_text(SCRIPT)
    server = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, '-I', '-B', str(script), str(server), case],
        text=True, capture_output=True, timeout=20, env={'LANG': 'C', 'LC_ALL': 'C'},
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed['case'] == case and observed['payloadExecuted'] is False


@pytest.mark.parametrize('index', range(7))
def test_cache_input_foreign_metadata_no_hooks(index):
    from hmp_startup.cache_selection import CacheSelectionError, source_loader_input

    calls = []

    class Foreign:
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign equality')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length')

        def __int__(self):
            calls.append('int')
            raise AssertionError('foreign conversion')

    values = [b'0' * 16, b'0000', 0, 1, b'0' * 8, 'default', 'declared']
    values[index] = Foreign()
    with pytest.raises(CacheSelectionError):
        source_loader_input(*values)
    assert calls == []

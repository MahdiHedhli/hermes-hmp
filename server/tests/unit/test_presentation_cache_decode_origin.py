"""Original native cache-decoder metadata; no payload execution."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CASES = ('normal', 'loads', 'fixer', 'code_type', 'function', 'code', 'marshal_alias',
         'marshal_sysmodule', 'imp_sysmodule', 'loads_metadata', 'foreign_code_type')
SCRIPT = r'''
import _imp,importlib._bootstrap_external as external,json,marshal,sys
from types import CodeType,ModuleType
sys.path.insert(0,sys.argv[1])
from hmp_startup.gateway_entry import _interpreter,_interpreter_current,GatewayEntryError
origin=_interpreter();held=origin.cache_decode;case=sys.argv[2];calls=[]
def foreign(*args,**kwargs):calls.append(True);raise AssertionError('foreign decoder')
class Foreign:
    def __eq__(self,other):calls.append('eq');raise AssertionError('foreign equality')
    def __getattr__(self,name):calls.append('getattr');raise AssertionError('foreign getter')
if case=='loads':marshal.loads=foreign
elif case=='fixer':_imp._fix_co_filename=foreign
elif case=='code_type':external._code_type=object
elif case=='function':external._compile_bytecode=foreign
elif case=='code':held.function.__code__=foreign.__code__
elif case=='marshal_alias':external.marshal=ModuleType('synthetic_foreign_marshal')
elif case=='marshal_sysmodule':sys.modules['marshal']=ModuleType('synthetic_marshal')
elif case=='imp_sysmodule':sys.modules['_imp']=ModuleType('synthetic_imp')
elif case=='loads_metadata':held.loads.__module__=Foreign()
elif case=='foreign_code_type':external._code_type=Foreign()
try:_interpreter_current(origin)
except GatewayEntryError:assert case!='normal' and calls==[]
else:assert case=='normal'
assert calls==[]
print(json.dumps({'case':case,'foreignCalls':calls,'executed':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_original_cache_decode_origin(tmp_path, case):
    script = tmp_path / 'cache_decode_origin.py'
    script.write_text(SCRIPT)
    result = subprocess.run([sys.executable, '-I', '-B', str(script),
                             str(Path(__file__).resolve().parents[2]), case],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['foreignCalls'] == []

PARITY_CASES = ('normal', 'trailing', 'eof', 'noncode', 'bad_tag', 'nested_distinct')
PARITY_SCRIPT = r'''
import json,marshal,sys
from types import CodeType
sys.path.insert(0,sys.argv[1])
from hmp_startup.gateway_entry import _interpreter,_interpreter_current
origin=_interpreter();held=origin.cache_decode;case=sys.argv[2]
source=b'def SYNTHETIC_NOT_EXECUTED():\n    return 1\n'
original=compile(source,'/synthetic/original.py','exec')
if case=='nested_distinct':
    original=original.replace(co_consts=tuple(
        item.replace(co_filename='/synthetic/distinct.py') if type(item) is CodeType else item
        for item in original.co_consts))
body=marshal.dumps(original)
if case=='trailing':body+=b'SYNTHETIC_TRAILING_BYTES'
if case=='eof':body=b''
if case=='noncode':body=marshal.dumps(123)
if case=='bad_tag':body=b'\xff'
path='/synthetic/admitted_source.py'
expected_error=None
try:expected=held.function(body,name='synthetic',bytecode_path='/synthetic/cache.pyc',source_path=path)
except (EOFError,ValueError,TypeError,ImportError) as exc:expected_error=type(exc)
actual_error=None
try:
    actual=held.loads(body)
    if type(actual) is not held.code_type:raise ImportError('synthetic non-code refusal')
    original_allocation=actual
    returned=held.fix_filename(actual,path)
    assert returned is None and actual is original_allocation
except (EOFError,ValueError,TypeError,ImportError) as exc:actual_error=type(exc)
assert expected_error is actual_error
if expected_error is None:
    assert marshal.dumps(expected)==marshal.dumps(actual)
    assert actual.co_filename==path
    nested=next(item for item in actual.co_consts if type(item) is CodeType)
    assert nested.co_filename==('/synthetic/distinct.py' if case=='nested_distinct' else path)
assert _interpreter_current(origin) is origin
print(json.dumps({'case':case,'executed':False,'bodyError':expected_error is not None}))
'''


@pytest.mark.parametrize('case', PARITY_CASES)
def test_actual_native_cache_decode_parity(tmp_path, case):
    script = tmp_path / 'cache_decode_parity.py'
    script.write_text(PARITY_SCRIPT)
    result = subprocess.run([sys.executable, '-I', '-B', str(script),
                             str(Path(__file__).resolve().parents[2]), case],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['executed'] is False

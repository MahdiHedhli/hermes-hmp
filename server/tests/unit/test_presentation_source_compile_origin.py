"""Original compiler resolution; synthetic compilation never executes code."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CASES = ('normal', 'builtin', 'global_shadow', 'function', 'code', 'function_builtins')
SCRIPT = r'''
from __future__ import annotations
import builtins,importlib._bootstrap_external as external,json,sys,types
sys.path.insert(0,sys.argv[1])
from hmp_startup.gateway_entry import _interpreter,_interpreter_current,GatewayEntryError
origin=_interpreter();held=origin.source_compile;case=sys.argv[2];calls=[]
assert held.function.__builtins__ is held.namespace is vars(builtins)
assert held.compiler is builtins.compile and 'compile' not in vars(external)
if case=='builtin':
    def replacement(*args,**kwargs):calls.append('compile');raise AssertionError('replacement')
    builtins.compile=replacement
elif case=='global_shadow':external.compile=held.compiler
elif case=='function':
    def replacement(*args,**kwargs):calls.append('method');raise AssertionError('replacement')
    external.SourceLoader.source_to_code=replacement
elif case=='code':
    def replacement(*args,**kwargs):calls.append('code');raise AssertionError('replacement')
    held.function.__code__=replacement.__code__
elif case=='function_builtins':
    namespace=vars(external);old=namespace['__builtins__']
    try:
        namespace['__builtins__']=dict(vars(builtins))
        other=types.FunctionType(held.code,namespace)
    finally:namespace['__builtins__']=old
    external.SourceLoader.source_to_code=other
try:_interpreter_current(origin)
except GatewayEntryError:assert case!='normal' and not calls
else:assert case=='normal'
print(json.dumps({'case':case,'foreignCalls':calls,'payloadExecuted':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_original_source_compile_origin(tmp_path, case):
    script = tmp_path / 'compile_origin.py'
    script.write_text(SCRIPT)
    result = subprocess.run([sys.executable, '-I', '-B', str(script),
                             str(Path(__file__).resolve().parents[2]), case],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['foreignCalls'] == []


PARITY_SCRIPT = r"""
from __future__ import annotations
import json,marshal,sys
from types import CodeType
sys.path.insert(0,sys.argv[1])
from hmp_startup.gateway_entry import _interpreter,_interpreter_current
origin=_interpreter();held=origin.source_compile
def check(value):
    if value is not True:raise AssertionError('synthetic compiler parity refused')
try:check(False)
except AssertionError:pass
else:raise RuntimeError('checks optimized away')
sources=(b'"synthetic doc"\nassert False\nSYNTHETIC_ONLY=__debug__\n',
         b'# coding: latin-1\nSYNTHETIC_ONLY="\xe9"\n',
         b'from __future__ import annotations\ndef synthetic(x: Unknown):pass\n',
         b'\xef\xbb\xbfSYNTHETIC_ONLY=1\n',
         b'def invalid(\n',b'SYNTHETIC_ONLY=1\x00\n')
for source in sources:
    path='/synthetic/native_compile_only.py'
    try:expected=held.function(None,source,path)
    except (SyntaxError,ValueError) as exc:
        expected_error=type(exc)
        try:held.compiler(source,path,'exec',flags=0,dont_inherit=True,
                          optimize=origin.flags.optimize)
        except (SyntaxError,ValueError) as actual:check(type(actual) is expected_error)
        else:raise AssertionError('native compilation error not preserved')
    else:
        actual=held.compiler(source,path,'exec',flags=0,dont_inherit=True,
                             optimize=origin.flags.optimize)
        check(type(expected) is type(actual) is CodeType)
        check(marshal.dumps(expected)==marshal.dumps(actual))
    check(_interpreter_current(origin) is origin)
print(json.dumps({'optimize':origin.flags.optimize,'cases':len(sources),'executed':False}))
"""


@pytest.mark.parametrize('optimize', (0, 1, 2))
def test_actual_native_compile_parity(tmp_path, optimize):
    script = tmp_path / 'compile_parity.py'
    script.write_text(PARITY_SCRIPT)
    command = [sys.executable, '-I', '-B']
    if optimize:
        command.append('-' + 'O' * optimize)
    command += [str(script), str(Path(__file__).resolve().parents[2])]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'optimize': optimize, 'cases': 6, 'executed': False}

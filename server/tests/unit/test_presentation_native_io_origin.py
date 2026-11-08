"""Original file-operation metadata only; no paths opened or outcomes minted."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CASES = ('normal', 'os_read', 'native_open', 'native_read', 'native_close',
         'os_flag', 'native_flag', 'flag_copy', 'os_name', 'os_module',
         'native_module', 'result_type', 'result_type_copy', 'error_base',
         'permission_error', 'permission_error_copy', 'function_metadata')
SCRIPT = r'''
import builtins,json,os,sys
from types import ModuleType
sys.path.insert(0,sys.argv[1])
from hmp_startup.gateway_entry import _interpreter,_interpreter_current,GatewayEntryError
origin=_interpreter();held=origin.native_io;case=sys.argv[2];calls=[]
def foreign(*args,**kwargs):calls.append('call');raise AssertionError('foreign file operation')
class Foreign:
    def __eq__(self,other):calls.append('eq');raise AssertionError('foreign equality')
    def __getattr__(self,name):calls.append('get');raise AssertionError('foreign metadata')
if case=='os_read':os.read=foreign
elif case.startswith('native_') and case in ('native_open','native_read','native_close'):
    vars(held.native)[case.removeprefix('native_')]=foreign
elif case=='os_flag':os.O_NOFOLLOW=Foreign()
elif case=='native_flag':vars(held.native)['O_NOFOLLOW']=-1
elif case=='flag_copy':
    copied=int(str(held.flags[2]));assert copied is not held.flags[2]
    os.O_CLOEXEC=vars(held.native)['O_CLOEXEC']=copied
elif case=='os_name':os.name=Foreign()
elif case=='os_module':sys.modules['os']=ModuleType('synthetic_os')
elif case=='native_module':
    replacement=ModuleType('posix');vars(replacement).update(vars(held.native))
    sys.modules['posix']=replacement
elif case=='result_type':os.stat_result=Foreign()
elif case=='result_type_copy':
    replacement=type('stat_result',(tuple,),{'__module__':'os'})
    os.stat_result=vars(held.native)['stat_result']=replacement
elif case=='error_base':vars(held.native)['error']=Foreign()
elif case=='permission_error':builtins.PermissionError=Foreign()
elif case=='permission_error_copy':
    builtins.PermissionError=type('PermissionError',(OSError,),{'__module__':'builtins'})
elif case=='function_metadata':held.operations[1].__module__=Foreign()
try:_interpreter_current(origin)
except GatewayEntryError:assert case!='normal' and calls==[]
else:assert case=='normal'
assert calls==[]
print(json.dumps({'case':case,'foreignCalls':calls,'fileOperationInvokedByCapture':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_original_native_io_origin(tmp_path, case):
    script = tmp_path / 'native_io_origin.py'
    script.write_text(SCRIPT)
    result = subprocess.run([sys.executable, '-I', '-B', str(script),
                             str(Path(__file__).resolve().parents[2]), case],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['foreignCalls'] == []

"""Captured actor getters are usable independently from retired work aliases."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CASES = ('normal', 'os_pid', 'os_uid', 'thread_alias', 'thread_native',
         'wrong_pid', 'wrong_uid', 'wrong_tid', 'wrong_thread',
         'wrong_functions', 'wrong_modules', 'wrong_expected')
SCRIPT = r'''
import json,os,sys,threading
sys.path.insert(0,sys.argv[1])
from hmp_startup.gateway_entry import _interpreter
from hmp_plugin.presentation_startup_artifacts import _native_actor_context,ArtifactObservationError
native=_interpreter().native_io;case=sys.argv[2];foreign_calls=[]
expected=(os.getpid(),os.geteuid(),threading.get_ident())
def foreign(*args,**kwargs):foreign_calls.append(True);raise AssertionError('foreign actor')
if case=='os_pid':os.getpid=foreign
elif case=='os_uid':os.geteuid=foreign
elif case=='thread_alias':threading.get_ident=foreign
elif case=='thread_native':vars(native.thread_native)['get_ident']=foreign
elif case=='wrong_pid':expected=(-1,expected[1],expected[2])
elif case=='wrong_uid':expected=(expected[0],-1,expected[2])
elif case=='wrong_tid':expected=(expected[0],expected[1],-1)
functions=native.actor_calls;modules=(native.native,native.thread_native)
class Foreign:
    def __getattr__(self,name):foreign_calls.append('get');raise AssertionError('getter')
    def __iter__(self):foreign_calls.append('iter');raise AssertionError('iteration')
if case=='wrong_functions':functions=Foreign()
elif case=='wrong_modules':modules=Foreign()
elif case=='wrong_expected':expected=Foreign()
refused=[]
def check():
    try:actual=_native_actor_context(functions,modules,expected)
    except ArtifactObservationError:refused.append(True)
    else:
        assert case in ('normal','os_pid','os_uid','thread_alias','thread_native')
        assert actual==expected
if case=='wrong_thread':
    thread=threading.Thread(target=check);thread.start();thread.join(timeout=10)
    assert not thread.is_alive()
else:check()
if case.startswith('wrong_'):assert refused==[True]
else:assert not refused
# Retire synthetic namespace hooks before interpreter/thread shutdown.
if case=='os_pid':os.getpid=native.actor_calls[0]
elif case=='os_uid':os.geteuid=native.actor_calls[1]
elif case=='thread_alias':threading.get_ident=native.actor_calls[2]
elif case=='thread_native':vars(native.thread_native)['get_ident']=native.actor_calls[2]
assert foreign_calls==[]
print(json.dumps({'case':case,'foreignCalls':foreign_calls,'fileOperationInvoked':False}))
'''


@pytest.mark.parametrize('case', CASES)
def test_original_actor_functions(tmp_path, case):
    script = tmp_path / 'native_actor.py'
    script.write_text(SCRIPT)
    result = subprocess.run([sys.executable, '-I', '-B', str(script),
                             str(Path(__file__).resolve().parents[2]), case],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['foreignCalls'] == []

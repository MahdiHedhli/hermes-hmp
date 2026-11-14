"""Fixed runtime prewarming and transient capture custody; no runtime admission."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2]
SCRIPT = r'''
import gc,importlib,json,sys
from pathlib import Path
from types import ModuleType
server,first,fault=sys.argv[1:]
package=ModuleType('hmp_plugin');package.__path__=[str(Path(server)/'hmp_plugin')]
sys.modules['hmp_plugin']=package;sys.path.insert(0,server)
observed=[];injected=[];calls=[]
def foreign(*args,**kwargs):
    calls.append('foreign');raise AssertionError('foreign helper called')
def observe(frame,event,value):
    if (event!='call' or frame.f_globals.get('__name__')!='hmp_startup.link_factory_origin'
            or frame.f_code.co_name!='capture'):return
    from hmp_startup import gateway_entry as entry
    required={
        'runtime_files':('RuntimeFilePlan','build_runtime_plan'),
        'cache_candidates':('PlannedCachePath','planned_cache_path'),
        'entry_files':('EntryFileSnapshotOwner','_same_package'),
        'cache_context':('CacheContextOwner','_getter_current'),
    }
    for short,names in required.items():
        module=sys.modules.get('hmp_startup.'+short)
        assert type(module) is ModuleType,short
        assert all(name in vars(module) for name in names),short
    files=sys.modules['hmp_startup.entry_files'];cache=sys.modules['hmp_startup.cache_context']
    assert files.gateway_entry is entry and files.GatewayEntryOwner is entry.GatewayEntryOwner
    assert cache.EntryFileSnapshotOwner is files.EntryFileSnapshotOwner
    assert cache._Inputs is files._Inputs and cache._same_package is files._same_package
    assert cache.GatewayEntryOwner is entry.GatewayEntryOwner
    assert cache._origin_current is entry._origin_current
    assert entry._ENTRY_ORIGIN is None
    observed.append('ready')
    if fault=='none':return
    short,kind=fault.split(':');ns=vars(sys.modules['hmp_startup.'+short])
    owner,helper=required[short];f=ns[helper]
    if kind=='code':f.__code__=foreign.__code__
    elif kind=='defaults':f.__defaults__=(object(),)
    elif kind=='kwdefaults':f.__kwdefaults__={'changed':object()}
    elif kind=='class':setattr(ns[owner],'changed_after_prewarm',object())
    else:raise AssertionError(kind)
    injected.append(fault)
assert sys.getprofile() is None and sys.gettrace() is None
sys.setprofile(observe)
try:
    importlib.import_module('hmp_startup.'+first)
except RuntimeError as error:
    assert fault!='none' and str(error)=='BI1_LINK_FACTORY_ORIGIN_REFUSED',str(error)
    refused=True
else:refused=False
finally:sys.setprofile(None)
assert observed==['ready'] and calls==[],(observed,calls)
assert refused is (fault!='none') and injected==([] if fault=='none' else [fault])
entry=sys.modules.get('hmp_startup.gateway_entry')
if entry is not None:
    assert entry._OWNER is entry._CELL is entry._STARTED is None
    assert entry._START_ATTEMPTED is False
cache=sys.modules['hmp_startup.cache_context']
assert cache._OWNER is cache._ROOT is cache._FACT is None
assert not any(name in sys.modules for name in ('hermes_bootstrap','gateway.run',
                                             'hmp_plugin.adapter','hmp_plugin.server'))
print(json.dumps({'refused':refused,'foreign_calls':0,'native_startup':False}))
'''


def run(tmp_path, first, fault):
    result = subprocess.run([sys.executable, '-I', '-B', '-c', SCRIPT,
                             str(SERVER), first, fault], cwd=tmp_path,
                            env={'LANG': 'C', 'LC_ALL': 'C'}, capture_output=True,
                            text=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('first', ('gateway_entry', 'entry_files', 'cache_context'))
def test_fixed_runtime_modules_and_aliases_ready_before_helper_capture(tmp_path, first):
    assert run(tmp_path, first, 'none') == {
        'refused': False, 'foreign_calls': 0, 'native_startup': False,
    }


@pytest.mark.parametrize('module', ('runtime_files', 'entry_files', 'cache_context', 'cache_candidates'))
@pytest.mark.parametrize('kind', ('code', 'defaults', 'kwdefaults', 'class'))
def test_prepared_runtime_drift_during_later_capture_refuses_without_dispatch(
        tmp_path, module, kind):
    assert run(tmp_path, 'gateway_entry', module + ':' + kind) == {
        'refused': True, 'foreign_calls': 0, 'native_startup': False,
    }

ALIAS_SCRIPT = r'''
import gc,importlib,json,sys
from pathlib import Path
from types import ModuleType
server,first,case=sys.argv[1:]
package=ModuleType('hmp_plugin');package.__path__=[str(Path(server)/'hmp_plugin')]
sys.modules['hmp_plugin']=package;sys.path.insert(0,server)
hooks=[];injected=[];cleanup=[];armed=False
class Foreign:
    def __eq__(self,other):
        if not armed:return False
        hooks.append('eq');raise AssertionError('foreign equality')
    def __ne__(self,other):
        if not armed:return True
        hooks.append('ne');raise AssertionError('foreign inequality')
foreign=Foreign()
key_name=('_initializing' if case=='spec-key' else
          '__module__' if case=='class-key' else '__name__')
class ForeignKey(Foreign):
    def __hash__(self):return hash(key_name)
key=ForeignKey()
def observe(frame,event,value):
    global armed
    if (frame.f_globals.get('__name__')!='hmp_startup.gateway_entry'
            or frame.f_code.co_name!='_capture_origin'):return
    if event=='return':
        armed=False
        for ns,name,old in cleanup:
            ns.pop(key);ns[name]=old
        cleanup.clear()
        return
    if event!='call' or injected:return
    ns=vars(sys.modules['hmp_startup.'+first])
    assert 'GatewayEntryOwner' not in ns
    if case=='foreign':ns['GatewayEntryOwner']=foreign
    elif case=='none':ns['GatewayEntryOwner']=None
    elif case=='same':ns['GatewayEntryOwner']=frame.f_globals['GatewayEntryOwner']
    elif case=='initialized-missing':vars(ns['__spec__'])['_initializing']=False
    elif case in ('module-key','spec-key','class-key'):
        if case=='class-key':
            kind=ns['_Inputs' if first=='entry_files' else 'CacheInputData']
            targets=[v for v in gc.get_referents(vars(kind)) if type(v) is dict]
            assert len(targets)==1
            target=targets[0]
        else:target=vars(ns['__spec__']) if case=='spec-key' else ns
        old=target.pop(key_name);target[key]=None;cleanup.append((target,key_name,old))
    else:raise AssertionError(case)
    injected.append(case);armed=True
sys.setprofile(observe)
try:importlib.import_module('hmp_startup.'+first)
except RuntimeError as error:
    assert case!='same' and str(error)=='BI1_LINK_FACTORY_ORIGIN_REFUSED',str(error)
    refused=True
else:refused=False
finally:sys.setprofile(None)
assert refused is (case!='same') and injected==[case] and hooks==[],(injected,hooks)
assert cleanup==[]
assert not any(name in sys.modules for name in ('hermes_bootstrap','gateway.run',
                                             'hmp_plugin.adapter','hmp_plugin.server'))
print(json.dumps({'refused':refused,'foreign_calls':0,'native_startup':False}))
'''


@pytest.mark.parametrize('first', ('entry_files', 'cache_context'))
@pytest.mark.parametrize('case', ('foreign', 'none', 'same', 'initialized-missing',
                                  'module-key', 'spec-key', 'class-key'))
def test_partial_aliases_never_repair_initialized_or_foreign_state(tmp_path, first, case):
    result = subprocess.run([sys.executable, '-I', '-B', '-c', ALIAS_SCRIPT,
                             str(SERVER), first, case], cwd=tmp_path,
                            env={'LANG': 'C', 'LC_ALL': 'C'}, capture_output=True,
                            text=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        'refused': case != 'same', 'foreign_calls': 0, 'native_startup': False,
    }

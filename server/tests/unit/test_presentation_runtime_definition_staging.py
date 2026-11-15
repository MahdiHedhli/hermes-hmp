"""Definition readiness at the original Entry capture, before native startup."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2]
SCRIPT = r'''
import importlib,json,sys
from pathlib import Path
from types import ModuleType
server,first=sys.argv[1:]
package=ModuleType('hmp_plugin');package.__path__=[str(Path(server)/'hmp_plugin')]
sys.modules['hmp_plugin']=package;sys.path.insert(0,server)
observed=[]
def observe(frame,event,value):
    if (event!='call' or frame.f_globals.get('__name__')!='hmp_startup.gateway_entry'
            or frame.f_code.co_name!='_capture_origin'):return
    for name,required in (
        ('hmp_startup.entry_files',('EntryFileSnapshotOwner','EntryFilesError','_Inputs','_same_package')),
        ('hmp_startup.cache_context',('CacheContextOwner','CacheContextError','CacheInputData',
                                    '_ContextSource','_getter_current','_rows')),
    ):
        module=sys.modules.get(name)
        if module is None:continue
        names=vars(module)
        assert all(key in names for key in required),(name,required)
        assert vars(names['__spec__']).get('_initializing') is True
        observed.append(name)
assert sys.getprofile() is None
sys.setprofile(observe)
try:importlib.import_module('hmp_startup.'+first)
finally:sys.setprofile(None)
from hmp_startup import gateway_entry as entry,entry_files as files,cache_context as cache
assert files.gateway_entry is entry and files.GatewayEntryOwner is entry.GatewayEntryOwner
assert cache.EntryFileSnapshotOwner is files.EntryFileSnapshotOwner
assert cache._Inputs is files._Inputs and cache._same_package is files._same_package
assert cache.GatewayEntryOwner is entry.GatewayEntryOwner
assert cache._origin_current is entry._origin_current
if first=='entry_files':assert observed==['hmp_startup.entry_files']
elif first=='cache_context':
    assert observed==['hmp_startup.entry_files','hmp_startup.cache_context']
else:assert observed==[]
assert entry._OWNER is entry._CELL is entry._STARTED is None
assert entry._START_ATTEMPTED is False
assert cache._OWNER is cache._ROOT is cache._FACT is None
assert not any(name in sys.modules for name in ('hermes_bootstrap','gateway.run',
                                             'hmp_plugin.adapter','hmp_plugin.server'))
assert sys.getprofile() is None
print(json.dumps({'order':first,'definitions_ready':True,'native_startup':False}))
'''


@pytest.mark.parametrize('first', ['gateway_entry', 'entry_files', 'cache_context'])
def test_runtime_definitions_precede_cycle_import_and_aliases_finish(tmp_path, first):
    result = subprocess.run([sys.executable, '-I', '-B', '-c', SCRIPT, str(SERVER), first],
                            cwd=tmp_path, env={'LANG': 'C', 'LC_ALL': 'C'},
                            capture_output=True, text=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        'order': first, 'definitions_ready': True, 'native_startup': False,
    }

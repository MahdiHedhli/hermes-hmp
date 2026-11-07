"""Original continuation DATA through real package import and fixture native startup."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from .test_presentation_entry_files import SERVER
from .test_presentation_gateway_approval import operator_composed_script

FINISH = r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner, GatewayContinuationError
from hmp_startup import gateway_continuation as continued
from hmp_startup.gateway_entry import GatewayEntryError
from types import ModuleType
import os
import hermes_constants as constants
snapshot=checked
original_io=snapshot._fact_cell[2]
original_bytes=original_io._bytes_read
original_resources=tuple(snapshot._fact_cell[2]._origin.records)
assert len(snapshot._fact_cell)==7
loose=snapshot._fact_cell[6]
assert len(loose)==len(snapshot._inputs.runtime_plan.loose)
for (path,(identity,ancestors)),expected in zip(
        loose,snapshot._inputs.runtime_plan.loose,strict=True):
    assert path is expected.path and len(identity)==9 and ancestors
foreign_calls=[]
if case=='foreign_pending':
    class ForeignPending:
        def __len__(self):
            foreign_calls.append('len');raise AssertionError('foreign pending length')
        def __iter__(self):
            foreign_calls.append('iter');raise AssertionError('foreign pending iteration')
    inputs=snapshot._inputs._replace(
        runtime_plan=snapshot._inputs.runtime_plan._replace(pending=ForeignPending()))
    snapshot._inputs=inputs
    snapshot._root_cell=entry._activation._entry_files_cell=(snapshot,inputs)
    fields=list(snapshot._fact_cell);fields[1]=inputs
    snapshot._fact_cell=entry._activation._entry_files_fact_cell=tuple(fields)
if case in ('foreign_io','foreign_file_fact'):
    class ForeignIO:
        def __getattr__(self,name):
            foreign_calls.append(name);raise AssertionError('foreign IO callback')
    replaced=list(snapshot._fact_cell)
    replaced[2 if case=='foreign_io' else 3]=ForeignIO()
    snapshot._fact_cell=entry._activation._entry_files_fact_cell=tuple(replaced)
if case=='retain_wrong_thread':
    import threading
    refused=[]
    def ineligible():
        try:GatewayContinuationOwner.retain(entry,approval,recipe,snapshot)
        except GatewayContinuationError:refused.append(True)
    thread=threading.Thread(target=ineligible);thread.start();thread.join()
    assert refused==[True] and continued._OWNER is None
    assert entry._activation._continuation_owner is None
foreign_root=None
if case in ('retain_final_argv','retain_final_start','coherent_retain_root'):
    old_snapshot=EntryFileSnapshotOwner._current
    old_recipe=GatewayRecipeOwner._loaded_binding
    phase=False
    def after_snapshot(self):
        global phase
        value=old_snapshot(self)
        phase=True
        return value
    def after_recipe(self):
        global foreign_root
        value=old_recipe(self)
        if phase:
            active=continued._OWNER
            if case=='retain_final_argv':sys.argv.append('--synthetic-drift')
            if case=='retain_final_start':
                method=vars(GatewayEntryOwner)['start'].__func__
                method.__code__=(lambda cls:None).__code__
            if case=='coherent_retain_root':
                foreign_root=tuple(list(active._root))
                active._root=continued._ROOT=entry._activation._continuation_cell=foreign_root
        return value
    EntryFileSnapshotOwner._current=after_snapshot
    GatewayRecipeOwner._loaded_binding=after_recipe
if case=='retain_loader_callback':
    def change_loader():
        if entry._activation._continuation_owner is not None:
            sys.modules['hermes_bootstrap'].__spec__.loader=object()
    constants.HOOK=change_loader
if case=='retain_late':sys.modules['gateway.run']=ModuleType('gateway.run')
if case=='retain_uncompleted':snapshot._ready=False
try:handoff=GatewayContinuationOwner.retain(entry,approval,recipe,snapshot)
except GatewayContinuationError as error:
    assert case in ('retain_late','retain_uncompleted','external_expectation','foreign_io',
        'foreign_file_fact','retain_final_argv','retain_final_start','coherent_retain_root',
        'retain_loader_callback','foreign_pending'),case
    assert error.failed_owner is entry._activation._continuation_owner
    assert error.failed_owner._failed and not error.failed_owner._ready
    assert foreign_calls==[]
    if case=='coherent_retain_root':assert continued._ROOT is foreign_root
else:
    assert case not in ('retain_late','retain_uncompleted','external_expectation','foreign_io',
        'foreign_file_fact','retain_final_argv','retain_final_start','coherent_retain_root',
        'retain_loader_callback','foreign_pending'),case
    root=handoff.current_binding()
    assert root is continued._ROOT and root[0] is handoff
    assert str(base) not in repr(handoff) and str(base) not in repr(root[2])
    foreign_fact=object()
    source=handoff._source
    originals={}
    if case in ('native_import','historical_namespace'):
        gateway=base/'native/gateway';gateway.mkdir(mode=0o700)
        (gateway/'__init__.py').write_text('')
        (gateway/'run.py').write_text('VALUE="SYNTHETIC_NATIVE_ONLY"\n')
        import gateway.run
        assert gateway.run.VALUE=='SYNTHETIC_NATIVE_ONLY'
        try:entry.current_binding()
        except GatewayEntryError:pass
        else:raise AssertionError('early entry accepted listener import')
        if case=='historical_namespace':
            assert 'hmp_plugin.cli' in sys.modules
            originals['cli']=sys.modules['hmp_plugin.cli']
            sys.modules['hmp_plugin.cli']=ModuleType('hmp_plugin.cli')
        assert handoff.current_binding() is root
        assert source.entry_binding[2][3] is entry._activation
    if case=='duplicate':
        try:GatewayContinuationOwner.retain(entry,approval,recipe,snapshot)
        except GatewayContinuationError:pass
        else:raise AssertionError('handoff recaptured')
        assert handoff.current_binding() is root
    if case=='wrong_thread':
        import threading
        results=[]
        def wrong():
            try:handoff.current_binding()
            except GatewayContinuationError:results.append(True)
        thread=threading.Thread(target=wrong);thread.start();thread.join()
        assert results==[True] and not handoff._failed
        assert handoff.current_binding() is root
    if case=='wrong_process':
        pid=os.fork()
        if pid==0:
            try:handoff.current_binding()
            except GatewayContinuationError:os._exit(0)
            else:os._exit(3)
        assert os.waitpid(pid,0)[1]==0 and not handoff._failed
        assert handoff.current_binding() is root
    if case=='native_replaced':
        originals['bootstrap']=sys.modules['hermes_bootstrap']
        sys.modules['hermes_bootstrap']=ModuleType('hermes_bootstrap')
    if case=='native_loader':
        originals['loader']=source.native[0].spec.loader
        source.native[0].spec.loader=object()
    if case=='pm_code':
        pm=entry._activation._scope.pm
        originals['code']=pm.activate_dependencies.__code__
        pm.activate_dependencies.__code__=(lambda:None).__code__
    if case=='path_drift':sys.path.append(str(base/'not-selected'))
    if case=='argv_drift':sys.argv.append('--synthetic-not-original')
    if case=='root_drift':constants.ROOT += '/changed'
    if case=='root_copy':
        replacement=tuple(list(root))
        handoff._root=entry._activation._continuation_cell=replacement
    if case=='source_copy':handoff._source=source._replace()
    if case=='fact_copy':
        originals['snapshot_fact']=snapshot._fact_cell
        snapshot._fact_cell=entry._activation._entry_files_fact_cell=tuple(list(snapshot._fact_cell))
    if case=='closed_changed':snapshot._inputs.scans[0].closed=False
    if case=='count_copy':
        io=snapshot._fact_cell[2]
        io._count_cell=tuple(list(io._count_cell))
    if case in ('last_callback','coherent_current_root','coherent_foreign_source'):
        original_pid=continued.os.getpid
        armed=False
        def arm():
            global armed
            armed=True
        constants.HOOK=arm
        def after_api():
            value=original_pid()
            if armed:
                if case=='last_callback':snapshot._fact_cell=foreign_fact
                elif case=='coherent_current_root':
                    replacement=tuple(list(root))
                    handoff._root=continued._ROOT=entry._activation._continuation_cell=replacement
                else:
                    class ForeignBinding:
                        def __getitem__(self,key):
                            foreign_calls.append(key);raise AssertionError('foreign binding read')
                    changed=source._replace(entry_binding=ForeignBinding())
                    handoff._source=changed
                    replaced=(handoff,entry._activation,changed)
                    handoff._root=continued._ROOT=entry._activation._continuation_cell=replaced
            return value
        continued.os.getpid=after_api
    failed_cases=('native_replaced','native_loader','pm_code','path_drift','argv_drift',
                  'root_drift','root_copy','source_copy','fact_copy','closed_changed','count_copy',
                  'last_callback','coherent_current_root','coherent_foreign_source')
    if case in failed_cases:
        try:handoff.current_binding()
        except GatewayContinuationError:pass
        else:raise AssertionError('drift accepted: '+case)
        assert handoff._failed and foreign_calls==[]
        if case=='root_copy':assert entry._activation._continuation_cell is replacement
        if case=='source_copy':assert handoff._source is not source
        if case=='last_callback':assert snapshot._fact_cell is foreign_fact
        if case=='native_replaced':sys.modules['hermes_bootstrap']=originals['bootstrap']
        if case=='native_loader':source.native[0].spec.loader=originals['loader']
        if case=='pm_code':pm.activate_dependencies.__code__=originals['code']
        if case=='path_drift':sys.path.pop()
        if case=='argv_drift':sys.argv.pop()
        if case=='root_drift':constants.ROOT=str(operator_root)
        handoff._root=entry._activation._continuation_cell=root
        handoff._source=source
        if case=='coherent_foreign_source':continued._ROOT=root
        if case=='fact_copy':
            snapshot._fact_cell=entry._activation._entry_files_fact_cell=originals['snapshot_fact']
        try:handoff.current_binding()
        except GatewayContinuationError:pass
        else:raise AssertionError('restored allocation resurrected')
assert original_bytes==original_io._bytes_read
assert tuple(original_io._origin.records)==original_resources
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''

CASES = (
    'normal', 'native_import', 'historical_namespace', 'duplicate', 'wrong_thread', 'wrong_process',
    'native_replaced', 'native_loader', 'pm_code', 'path_drift', 'argv_drift', 'root_drift',
    'root_copy', 'source_copy', 'fact_copy', 'closed_changed', 'count_copy', 'last_callback',
    'retain_late', 'retain_uncompleted', 'external_expectation', 'foreign_io',
    'foreign_file_fact', 'retain_wrong_thread', 'retain_final_argv', 'retain_final_start',
    'coherent_retain_root', 'coherent_current_root', 'retain_loader_callback', 'foreign_pending',
    'coherent_foreign_source',
)


def continuation_script(case):
    script, mutation = operator_composed_script('links')
    script=script[:script.rfind('print(json.dumps')]
    fake='''namespace = ModuleType("hmp_plugin")
namespace.__path__ = [str(plugin_root)]
sys.modules["hmp_plugin"] = namespace
'''
    assert fake in script
    if case in ('normal','historical_namespace'):
        script=script.replace(fake,'',1).replace('namespace.__path__ = []','',1)
    script=script.replace('"\\ndef get_default_hermes_root():\\n    return Path(ROOT)\\n"',
        '"\\nHOOK=None\\ndef get_default_hermes_root():\\n"'
        '\n    ' + '"    if HOOK is not None:HOOK()\\n    return Path(ROOT)\\n"',1)
    if case=='external_expectation':
        script=script.replace('configuration=StartupSelectionOwner.load_operator_selection(approval)',
            'configuration=StartupSelectionOwner.load_recipe_selection(entry._activation, '
            'a.ExpectedArtifact(str(path),len(selection),hashlib.sha256(selection).hexdigest()))')
        script=script.replace('assert configuration._bytes_read==len(operator_raw)+len(selection)',
            'assert configuration._bytes_read==len(selection)')
    return script+'\ncase='+repr(case)+'\n'+FINISH,mutation


@pytest.mark.parametrize('case', CASES)
def test_original_continuation(tmp_path: Path, monkeypatch, case):
    if os.name != 'posix' or os.sys.platform not in ('darwin','linux'):
        pytest.skip('supported POSIX startup continuation')
    if case not in ('normal','historical_namespace'):
        from . import test_presentation_entry_files as base

        script,mutation=continuation_script(case)
        monkeypatch.setattr(base,'SCRIPT',script)
        return base.test_actual_entry_and_wrapper_files(tmp_path,mutation)
    for name in ('hmp_plugin','hmp_startup'):
        shutil.copytree(SERVER/name,tmp_path/name,
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ('private','native','environment/site-packages'):
        (tmp_path/name).mkdir(parents=True,mode=0o700)
    native=tmp_path/'native'
    (native/'pm').mkdir(mode=0o700)
    (native/'pm/__init__.py').write_text('')
    (native/'pm/environments.py').write_text('def activate_dependencies():\n    pass\n')
    (native/'hermes_bootstrap.py').write_text('import sys\nimport pm.environments\n'
        "sys.path.insert(1,sys.argv[1]+'/environment/site-packages')\n")
    script,mutation=continuation_script(case)
    wrapper=tmp_path/'wrapper.py'
    wrapper.write_text(script)
    result=subprocess.run([os.sys.executable,'-I','-B',str(wrapper),str(tmp_path),mutation],
        capture_output=True,text=True,timeout=90,env={'LANG':'C','LC_ALL':'C'})
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)=={'mutation':mutation,'runtime_admitted':False}

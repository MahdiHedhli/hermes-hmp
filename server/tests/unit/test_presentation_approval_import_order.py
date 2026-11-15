"""Actual isolated module initialization; no bootstrap, operator files or keys."""
import json
from pathlib import Path
import subprocess
import sys

import pytest


SERVER = Path(__file__).resolve().parents[2]
SCRIPT = r'''
import json,sys
from pathlib import Path
from types import ModuleType
server,order=sys.argv[1:]
package=ModuleType('hmp_plugin')
package.__path__=[str(Path(server)/'hmp_plugin')]
sys.modules[package.__name__]=package
sys.path.insert(0,server)
ready=[];bound=[];packets=[];records=[];staged=[]
def observe(frame,event,value):
    module=frame.f_globals.get('__name__')
    if (event=='call' and module=='hmp_startup.gateway_entry'
            and frame.f_code.co_name=='_capture_origin'):
        approval=sys.modules.get('hmp_startup.gateway_approval')
        names={} if approval is None else vars(approval)
        ready.append(approval is None or all(name in names for name in
            ('GatewayApprovalOwner','GatewayApprovalError','_RootSource',
             'GatewayOperatorApproval','_api_state','_same_entry','_require')))
    if (event=='return' and module=='hmp_startup.retained_binding_origin'
            and frame.f_code.co_name=='capture_bound'):
        approval=sys.modules.get('hmp_startup.gateway_approval')
        entry=sys.modules['hmp_startup.gateway_entry']
        assert type(value) is tuple and len(value)==3
        assert type(value[1]) is tuple and len(value[1])==4
        assert value[1][0] is value[0]
        packets.append(value[0]);records.append(value)
        staged.append('_ENTRY_ORIGIN' in vars(entry) and vars(entry)['_ENTRY_ORIGIN'] is None)
        bound.append(approval is not None
            and vars(approval).get('GatewayEntryOwner') is vars(entry)['GatewayEntryOwner']
            and vars(sys.modules['hmp_plugin.presentation_startup_selection']).get(
                '_APPROVAL_OWNER_TYPE') is vars(approval)['GatewayApprovalOwner'])
assert sys.getprofile() is None and sys.gettrace() is None
sys.setprofile(observe)
try:
    if order=='selection':
        from hmp_plugin import presentation_startup_selection
        from hmp_startup import gateway_entry as entry
        from hmp_startup import gateway_approval as approval
    elif order=='approval':
        from hmp_startup import gateway_approval as approval
        from hmp_startup import gateway_entry as entry
    else:
        from hmp_startup import gateway_entry as entry
        from hmp_startup import gateway_approval as approval
finally:sys.setprofile(None)
assert ready==[True] and bound==[True] and staged==[True],(ready,bound,staged)
assert type(entry._ENTRY_ORIGIN) is entry._EntryOrigin
assert entry._ENTRY_ORIGIN.link_policy[0][6][6] is packets[0]
assert entry._ENTRY_ORIGIN.link_policy[0][6][7] is records[0]
assert approval.GatewayEntryOwner is entry.GatewayEntryOwner
assert all(vars(approval)[name] is None for name in ('_OWNER','_CELL','_ROOT','_FACT'))
assert entry._OWNER is None and entry._CELL is None and entry._STARTED is None
assert not any(name in sys.modules for name in ('hermes_bootstrap','gateway.run',
    'hmp_plugin.adapter','hmp_plugin.server'))
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps(dict(order=order,definitions_ready=True,alias_bound_before_helpers=True,
    operator_loaded=False,bootstrap_started=False)))
'''


@pytest.mark.parametrize('order', ('entry', 'approval', 'selection'))
def test_approval_definitions_and_entry_alias_exist_before_original_helper_capture(tmp_path, order):
    result = subprocess.run([sys.executable, '-I', '-B', '-c', SCRIPT, str(SERVER), order],
                            cwd=tmp_path, env={'LANG': 'C', 'LC_ALL': 'C'},
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == dict(order=order, definitions_ready=True,
        alias_bound_before_helpers=True, operator_loaded=False, bootstrap_started=False)


FAULT_SCRIPT = r'''
import sys
from pathlib import Path
from types import ModuleType
server,case=sys.argv[1:]
package=ModuleType('hmp_plugin')
package.__path__=[str(Path(server)/'hmp_plugin')]
sys.modules[package.__name__]=package
sys.path.insert(0,server)
hooks=[];injected=[];armed=True
class Foreign:
    def __eq__(self, other):
        if not armed:return False
        hooks.append('eq');raise AssertionError('foreign equality')
    def __ne__(self, other):
        if not armed:return True
        hooks.append('ne');raise AssertionError('foreign inequality')
foreign=Foreign()
key_hash=hash('_initializing' if case=='foreign-spec-key' else '__name__')
class ForeignKey(Foreign):
    def __hash__(self):return key_hash
foreign_key=ForeignKey()
def observe(frame,event,value):
    global armed
    label=next((v for k,v in frame.f_globals.items()
                if type(k) is str and k=='__name__'),None)
    if type(label) is not str:return
    if (event=='call' and label=='hmp_startup.gateway_entry'
            and frame.f_code.co_name=='_capture_origin' and not injected
            and case!='foreign-spec-key'):
        ns=vars(sys.modules['hmp_startup.gateway_approval'])
        owner=frame.f_globals['GatewayEntryOwner']
        if case=='foreign-key':
            del ns['__name__'];ns[foreign_key]=None
        elif case=='foreign-name':ns['__name__']=foreign
        elif case=='foreign-class-module':ns['GatewayApprovalOwner'].__module__=foreign
        elif case=='none-alias':ns['GatewayEntryOwner']=None
        elif case=='foreign-alias':ns['GatewayEntryOwner']=foreign
        elif case=='same-alias':ns['GatewayEntryOwner']=owner
        elif case=='incomplete':del ns['_api_state']
        injected.append(case)
    # Restore only after validation has returned, so importlib cleanup is not
    # itself the caller of the deliberately invalid spec key.
    if (event=='return' and label=='hmp_startup.gateway_entry'
            and frame.f_code.co_name=='_capture_origin' and case=='foreign-spec-key' and injected):
        spec_values=vars(vars(sys.modules['hmp_startup.gateway_approval'])['__spec__'])
        armed=False
        spec_values.pop(foreign_key);spec_values['_initializing']=True
        armed=True
    if (event=='return' and label=='hmp_startup.retained_binding_origin'
            and frame.f_code.co_name=='capture_bound' and case=='late-alias'):
        vars(sys.modules['hmp_startup.gateway_approval'])['GatewayEntryOwner']=foreign
        injected.append(case)
def trace_spec(frame,event,value):
    global armed
    if frame.f_code.co_name!='_capture_origin':return None
    if (event=='line' and not injected and 'approval_spec_values' in frame.f_locals):
        spec_values=frame.f_locals['approval_spec_values']
        armed=False
        del spec_values['_initializing'];spec_values[foreign_key]=None
        armed=True
        injected.append(case)
    return trace_spec
try:
    sys.setprofile(observe)
    if case=='foreign-spec-key':sys.settrace(trace_spec)
    from hmp_startup import gateway_approval as approval
    from hmp_startup import gateway_entry as entry
    sys.setprofile(None)
    if case=='initialized-missing':
        del vars(approval)['GatewayEntryOwner']
        entry._capture_origin()
    assert case=='same-alias', 'missing refusal'
except RuntimeError as error:
    assert case!='same-alias'
    assert error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',),error.args
finally:
    sys.setprofile(None)
    sys.settrace(None)
assert not hooks,hooks
assert case=='initialized-missing' or injected
print('REFUSED_WITHOUT_FOREIGN_HOOKS' if case!='same-alias' else 'SAME_ALIAS_ACCEPTED')
'''


@pytest.mark.parametrize('case', ('foreign-spec-key', 'foreign-key', 'foreign-name', 'foreign-class-module', 'none-alias',
    'foreign-alias', 'incomplete', 'initialized-missing', 'late-alias', 'same-alias'))
def test_approval_initialization_refuses_invalid_metadata_without_foreign_hooks(tmp_path, case):
    script = FAULT_SCRIPT
    result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(SERVER), case],
                            cwd=tmp_path, env={'LANG': 'C', 'LC_ALL': 'C'},
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ('SAME_ALIAS_ACCEPTED' if case == 'same-alias'
                                    else 'REFUSED_WITHOUT_FOREIGN_HOOKS')


SELECTION_RECAPTURE = r'''
import sys
from pathlib import Path
from types import ModuleType
server,case=sys.argv[1:]
package=ModuleType('hmp_plugin');package.__path__=[str(Path(server)/'hmp_plugin')]
sys.modules['hmp_plugin']=package;sys.path.insert(0,server)
from hmp_startup import gateway_entry as entry
from hmp_plugin import presentation_startup_selection as selection
replacement=object() if case=='foreign' else None
if case=='missing':del vars(selection)['_APPROVAL_OWNER_TYPE']
else:vars(selection)['_APPROVAL_OWNER_TYPE']=replacement
if case=='forged-root':vars(entry)['_ENTRY_ORIGIN']=None
try:entry._capture_origin()
except RuntimeError as error:assert error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',)
else:raise AssertionError('initialized alias repaired')
if case=='missing':assert '_APPROVAL_OWNER_TYPE' not in vars(selection)
else:assert vars(selection)['_APPROVAL_OWNER_TYPE'] is replacement
assert entry._OWNER is None and entry._STARTED is None
assert 'hermes_bootstrap' not in sys.modules
print('NO_ALIAS_REPAIR')
'''


@pytest.mark.parametrize('case', ('none', 'foreign', 'missing', 'forged-root'))
def test_initialized_selection_alias_is_not_repaired(tmp_path, case):
    result = subprocess.run([sys.executable, '-I', '-B', '-c', SELECTION_RECAPTURE,
                             str(SERVER), case], cwd=tmp_path,
                            env={'LANG': 'C', 'LC_ALL': 'C'}, capture_output=True,
                            text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'NO_ALIAS_REPAIR'


SELECTION_IMPORT_FAULT = r'''
import sys
from pathlib import Path
from types import ModuleType
server,case=sys.argv[1:]
package=ModuleType('hmp_plugin');package.__path__=[str(Path(server)/'hmp_plugin')]
sys.modules['hmp_plugin']=package;sys.path.insert(0,server)
mutated=[];foreign_calls=[]
def foreign(*args,**kwargs):raise AssertionError('changed prepared definition executed')
def trace(frame,event,value):
    if event=='call' and frame.f_code is foreign.__code__:foreign_calls.append(True)
    if frame.f_code.co_name!='_capture_origin':return None
    if event=='line' and 'selection_module' in frame.f_locals and not mutated:
        approval=sys.modules['hmp_startup.gateway_approval']
        if case=='code':approval.GatewayApprovalOwner._retained_binding.__code__=foreign.__code__
        elif case=='getter':approval.GatewayApprovalOwner.__getattribute__=foreign
        elif case=='closure':approval.GatewayApprovalError.__init__.__closure__[0].cell_contents=object()
        elif case=='kwdefaults':approval.GatewayApprovalOwner._retained_binding.__kwdefaults__={'changed':True}
        elif case=='own-require':frame.f_globals['_require'].__code__=foreign.__code__
        mutated.append(case)
    return trace
sys.settrace(trace)
try:
    try:from hmp_startup import gateway_entry
    except RuntimeError as error:assert error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',)
    else:raise AssertionError('prepared metadata drift accepted')
finally:sys.settrace(None)
assert mutated==[case] and foreign_calls==[],(mutated,foreign_calls)
assert 'hermes_bootstrap' not in sys.modules
print('PREPARED_DEFINITIONS_REFUSED')
'''


@pytest.mark.parametrize('case', ('code', 'getter', 'closure', 'kwdefaults', 'own-require'))
def test_selection_import_cannot_renominate_prepared_definitions(tmp_path, case):
    result = subprocess.run([sys.executable, '-I', '-B', '-c', SELECTION_IMPORT_FAULT,
                             str(SERVER), case], cwd=tmp_path,
                            env={'LANG': 'C', 'LC_ALL': 'C'}, capture_output=True,
                            text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'PREPARED_DEFINITIONS_REFUSED'

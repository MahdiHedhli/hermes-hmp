"""Actual primitive and coherent layout-root drift at both publication seals."""
import ast
import json

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('publication', ('first', 'second'))
@pytest.mark.parametrize('export', ('map', 'is_not', 'layout_graft', 'audit_graft', 'helper_graft', 'helper_checker', 'helper_projection_schema', 'api_spec_dict_default', 'record_path_dispatch', 'record_receipt_dispatch', 'record_read_effect_dispatch', 'selection_approval_alias', 'selection_code', 'selection_error_code', 'activation_code', 'activation_error_code', 'artifact_error_code', 'artifact_error_new', 'artifact_error_getattribute', 'artifact_error_setattr', 'artifact_error_owner_property', 'artifact_owner_getattribute', 'artifact_owner_setattr', 'artifact_owner_dict_subclass', 'artifact_descriptor_code', 'artifact_allocation_code', 'artifact_expected_code', 'artifact_allocation_dispatch', 'execution_sum', 'execution_ord', 'entry_getattribute', 'entry_subclass_dict'))
def test_scope_publication_rejects_changed_primitive_or_layout_root(
        tmp_path, monkeypatch, request, publication, export):
    tree = ast.parse((base.SERVER / 'hmp_plugin/presentation_startup_artifacts.py').read_text())
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                 and n.name == 'StartupArtifactOwner')
    retain = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == '_retain')
    calls = sorted(n.lineno for n in ast.walk(retain) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == 'link_rejoin')
    assert len(calls) >= 3
    # Two post-publication rejoins follow the final pre-publication rejoin.
    # The real observed scope/slot state below must also match the target.
    line = calls[-3] if publication == 'first' else calls[-1]
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\npublication,export,target_line=' + repr((publication, export, line)) + '\n'
    script += r'''
import builtins
from hmp_startup.entry_files import EntryFilesError
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
ledger=entry._scope.native_files.ledger
retain_code=a.StartupArtifactOwner._retain.__func__.__code__
register_code=a._register_native_scope.__code__
rejoin_code=next(c for c in retain_code.co_consts
                 if type(c) is type(retain_code) and c.co_name=='link_rejoin')
module=sys.modules['_operator'] if export=='is_not' else builtins
export_name=export if export in ('map','is_not') else 'map'
original=getattr(module,export_name)
assign=setattr
observed=[];mutated=[];foreign_calls=[];held=[];registrations=[];successful_returns=[]
hook_restore=[];class_restore=[];helper_restore=[];missing=object()
helper_code_restore=[];kw_restore=[];late_helper_code=None
member_restore=[];refusal_records=[];builtin_restore=[]
artifact_error_kind=a.ArtifactObservationError
artifact_owner_kind=a.StartupArtifactOwner
native_error_dict=BaseException.__dict__['__dict__'].__get__
native_error_context=BaseException.__dict__['__context__'].__get__
native_error_cause=BaseException.__dict__['__cause__'].__get__
native_error_args=BaseException.__dict__['args'].__get__
native_owner_dict=vars(artifact_owner_kind)['__dict__'].__get__

def foreign(*args,**kwargs):
    foreign_calls.append(True)
    raise AssertionError('changed native primitive was dispatched')

def observe(frame,event,value):
    global late_helper_code
    if mutated:
        if event=='call' and frame.f_code is late_helper_code:
            foreign_calls.append(True)
        if event=='call' and frame.f_code is register_code and frame.f_back.f_code is retain_code:
            registrations.append(True)
        if event=='return' and frame.f_code is retain_code and value is held[0][0]:
            successful_returns.append(True)
        if (event=='return' and frame.f_code is retain_code
                and (export.startswith(('artifact_','execution_','record_','api_')) or export=='selection_approval_alias')):
            error=frame.f_locals.get('refusal')
            assert error is not None
            values=native_error_dict(error,artifact_error_kind)
            refusal_records.append(dict(exact_error_type=type(error) is artifact_error_kind,
                exact_owner=values.get('failed_owner') is held[0][0],
                fixed_args=native_error_args(error,artifact_error_kind)==('BI1_STARTUP_ARTIFACTS_REFUSED',),
                context_cleared=native_error_context(error,artifact_error_kind) is None,
                cause_cleared=native_error_cause(error,artifact_error_kind) is None,
                native_failed_marker=native_owner_dict(held[0][0],artifact_owner_kind).get('_failed') is True))
    if (event=='return' and frame.f_code is rejoin_code and not mutated
            and frame.f_back.f_code is retain_code
            and frame.f_back.f_lineno==target_line):
        context=frame.f_back.f_locals
        owner=context['owner'];source=context['runtime'];scope=context['s']
        if publication=='first':
            assert owner._scope is None and source.inputs.io_slot[0] is None
        else:
            assert owner._scope is scope and source.inputs.io_slot[0] is owner
        held.append((owner,source))
        observed.append((ledger.counts[0],ledger.counts[1],len(ledger.attempts)))
        if export in ('entry_getattribute','entry_subclass_dict'):
            entry_owner=source.inputs.entry
            entry_kind=type(entry_owner)
            if export=='entry_getattribute':
                previous=vars(entry_kind).get('__getattribute__',missing)
                hook_restore.append((entry_kind,previous))
                assign(entry_kind,'__getattribute__',foreign)
                assert vars(entry_kind)['__getattribute__'] is foreign
            else:
                class ChangedEntry(entry_kind):
                    __dict__=property(foreign)
                class_restore.append((entry_owner,entry_kind))
                object.__setattr__(entry_owner,'__class__',ChangedEntry)
                assert type(entry_owner) is ChangedEntry
        elif export=='helper_checker':
            component=context['link_helper_origin'][0]
            helper_restore.append((component,'current',component.current))
            assign(component,'current',foreign)
            assert component.current is foreign
        elif export=='helper_projection_schema':
            component=context['link_helper_origin'][0]
            previous=component._LIVE_GLOBALS
            helper_restore.append((component,'_LIVE_GLOBALS',previous))
            assign(component,'_LIVE_GLOBALS',((),(),(),()))
            assert component._LIVE_GLOBALS is not previous
        elif export in ('execution_sum','execution_ord'):
            name=export.split('_',1)[1]
            builtin_restore.append((name,getattr(builtins,name)))
            late_helper_code=foreign.__code__
            assign(builtins,name,foreign)
            assert vars(builtins)[name] is foreign
        elif export=='artifact_owner_dict_subclass':
            class ChangedOwner(artifact_owner_kind):
                __slots__=()
                __dict__=property(foreign)
            class_restore.append((owner,artifact_owner_kind))
            late_helper_code=foreign.__code__
            object.__setattr__(owner,'__class__',ChangedOwner)
            assert type(owner) is ChangedOwner
        elif export in ('artifact_descriptor_code','artifact_allocation_code','artifact_expected_code'):
            name={'artifact_descriptor_code':'_descriptor_closed_in_scope',
                  'artifact_allocation_code':'_native_file_allocation_original',
                  'artifact_expected_code':'_expected'}[export]
            function=getattr(a,name)
            helper_code_restore.append((function,function.__code__))
            late_helper_code=foreign.__code__
            assign(function,'__code__',late_helper_code)
            assert function.__code__ is late_helper_code
        elif export=='artifact_allocation_dispatch':
            selected=a._NativeOpenAllocation
            member_restore.append((selected,'__getattribute__',
                vars(selected).get('__getattribute__',missing)))
            late_helper_code=foreign.__code__
            assign(selected,'__getattribute__',foreign)
            assert vars(selected)['__getattribute__'] is foreign
        elif export.startswith('artifact_') and export!='artifact_error_code':
            selected=(artifact_owner_kind if export.startswith('artifact_owner_') else artifact_error_kind)
            leaf=('owner_property' if export=='artifact_error_owner_property' else
                  export.rsplit('_',1)[1])
            name={'new':'__new__','getattribute':'__getattribute__',
                  'setattr':'__setattr__','owner_property':'failed_owner'}[leaf]
            member_restore.append((selected,name,vars(selected).get(name,missing)))
            late_helper_code=foreign.__code__
            replacement=(staticmethod(foreign) if leaf=='new' else
                         property(foreign) if leaf=='owner_property' else foreign)
            assign(selected,name,replacement)
            assert vars(selected)[name] is replacement
        elif export=='api_spec_dict_default':
            selected=sys.modules['hmp_startup.gateway_approval']._api_state
            class ForeignDescriptor:
                def __getattribute__(self,name):return foreign()
            defaults=selected.__kwdefaults__
            kw_restore.append((defaults,'_spec_dict',defaults['_spec_dict']))
            defaults['_spec_dict']=ForeignDescriptor()
        elif export.startswith('record_'):
            name={'record_path_dispatch':'OperatorApprovalPath',
                  'record_receipt_dispatch':'_OperatorFileReceipt',
                  'record_read_effect_dispatch':'_ReadEffect'}[export]
            selected=getattr(a,name)
            member_restore.append((selected,'__getattribute__',vars(selected).get('__getattribute__',missing)))
            late_helper_code=foreign.__code__
            assign(selected,'__getattribute__',foreign)
            assert vars(selected)['__getattribute__'] is foreign
        elif export=='selection_approval_alias':
            selected=sys.modules['hmp_plugin.presentation_startup_selection']
            helper_restore.append((selected,'_APPROVAL_OWNER_TYPE',selected._APPROVAL_OWNER_TYPE))
            assign(selected,'_APPROVAL_OWNER_TYPE',foreign)
            assert selected._APPROVAL_OWNER_TYPE is foreign
        elif export in ('selection_code','selection_error_code','activation_code','activation_error_code','artifact_error_code'):
            selected=(a if export=='artifact_error_code' else
                sys.modules['hmp_plugin.presentation_gateway_activation'
                if export.startswith('activation') else 'hmp_plugin.presentation_startup_selection'])
            if export in ('selection_code','activation_code'):
                function=(selected.GatewayActivationOwner._retained_scope
                    if export=='activation_code' else selected._approved_recipe)
                late_helper_code=foreign.__code__
            else:
                class ChangedError(Exception):
                    def __init__(self,*args,**kwargs):
                        __class__
                        raise AssertionError('changed selection error dispatched')
                function=(selected.ArtifactObservationError.__init__ if export=='artifact_error_code' else
                    selected.ActivationCaptureError.__init__
                    if export=='activation_error_code' else selected.SelectionLoadError.__init__)
                late_helper_code=ChangedError.__init__.__code__
            assert len(function.__code__.co_freevars)==len(late_helper_code.co_freevars)
            helper_code_restore.append((function,function.__code__))
            assign(function,'__code__',late_helper_code)
            assert function.__code__ is late_helper_code
        elif export in ('layout_graft','audit_graft','helper_graft'):
            parent=context['link_origin']
            engine=parent[0][4]
            layout=engine[5]
            if export=='layout_graft':
                copied_layout=tuple(list(layout))
                copied_engine=(*engine[:5],copied_layout)
                copied_record=(copied_engine,copied_layout,parent[0][7][2])
                copied_environment=(*parent[0][:4],copied_engine,copied_layout,parent[0][6],copied_record)
            elif export=='audit_graft':
                copied_record=tuple(list(parent[0][7]))
                assert copied_record is not parent[0][7]
                copied_environment=(*parent[0][:7],copied_record)
            else:
                helper=parent[0][6]
                copied_packet=tuple(list(helper[6]))
                copied_helper=(*helper[:6],copied_packet)
                copied_environment=(*parent[0][:6],copied_helper,*parent[0][7:])
                assert copied_packet is not helper[6] and copied_helper is not helper
            copied_parent=(copied_environment,*parent[1:])
            lineage=context['native_files']
            copied_lineage=lineage._replace(link_policy=copied_parent, audit_record=copied_environment[7])
            entry_owner=source.inputs.entry
            invocation=entry_owner._scope
            copied_invocation=invocation._replace(native_files=copied_lineage)
            assert copied_parent is not parent
            if export=='layout_graft':assert copied_layout is not layout
            assert copied_parent[0][4][5] is copied_parent[0][5]
            assert copied_lineage.link_policy is copied_parent
            assert copied_lineage.audit_record is copied_parent[0][7]
            assert copied_parent[0][7][0] is copied_parent[0][4]
            assert copied_parent[0][7][1] is copied_parent[0][5]
            assign(entry_owner,'_scope',copied_invocation)
            assert entry_owner._scope is copied_invocation
        else:
            assign(module,export,foreign)
            assert getattr(module,export) is foreign
        mutated.append(True)

prior=sys.getprofile()
assert prior is None and sys.gettrace() is None
monitor=getattr(sys,'monitoring',None)
if monitor is not None:
    monitor.use_tool_id(5,'hermes-synthetic-scope-native-primitives')
    def arm(code,offset):
        if sys._getframe(1).f_locals.get('runtime') is not None:
            sys.setprofile(observe)
    monitor.register_callback(5,monitor.events.PY_START,arm)
    monitor.set_local_events(5,retain_code,monitor.events.PY_START)
else:
    def arm(frame,event,value):
        frame.f_trace_lines=False
        if (event=='call' and frame.f_code is retain_code
                and frame.f_locals.get('runtime') is not None):
            sys.settrace(None);sys.setprofile(observe)
        return None
    sys.settrace(arm)
failed=False
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as caught:
    assert caught.failed_owner is retained
    failed=True
finally:
    sys.setprofile(prior);sys.settrace(None)
    for name,previous in builtin_restore:assign(builtins,name,previous)
    for component,name,previous in helper_restore:assign(component,name,previous)
    for function,previous in helper_code_restore:assign(function,'__code__',previous)
    for defaults,key,previous in kw_restore:defaults[key]=previous
    for selected,name,previous in member_restore:
        if previous is missing:delattr(selected,name)
        else:assign(selected,name,previous)
    for instance,entry_kind in class_restore:
        object.__setattr__(instance,'__class__',entry_kind)
    for entry_kind,previous in hook_restore:
        if previous is missing:delattr(entry_kind,'__getattribute__')
        else:assign(entry_kind,'__getattribute__',previous)
    assign(module,export_name,original)
    if monitor is not None:
        monitor.set_local_events(5,retain_code,0)
        monitor.register_callback(5,monitor.events.PY_START,None)
        monitor.free_tool_id(5)
assert mutated==[True] and len(observed)==1 and failed
assert foreign_calls==[]
if (export.startswith(('artifact_','execution_','record_','api_')) or export=='selection_approval_alias'):
    assert len(refusal_records)==1 and all(refusal_records[0].values()),refusal_records
assert registrations==[] and successful_returns==[]
assert retained._failed and not retained._ready and retained._fact_cell is None
owner,source=held[0]
assert owner._failed and not owner._ready and owner._fact_cell is None
if publication=='first':
    assert owner._scope is None and source.inputs.io_slot[0] is None
else:
    assert owner._scope is not None and source.inputs.io_slot[0] is owner
assert tuple(ledger.counts)==observed[0][:2] and len(ledger.attempts)==observed[0][2]
evidence=dict(publication=publication,export=export,mutation_completed=True,
              refused=True,foreign_calls=0,new_work=0,reserve_change=0,
              registration_calls_after_mutation=0,successful_retainer_returns=0,
              scope_published_before_refusal=publication=='second')
if (export.startswith(('artifact_','execution_','record_','api_')) or export=='selection_approval_alias'):evidence['private_refusal']=refusal_records[0]
destination=base/'scope-native-primitive-refusal.json'
destination.write_text(json.dumps(evidence,sort_keys=True));destination.chmod(0o600)
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
    evidence = json.loads((tmp_path / 'scope-native-primitive-refusal.json').read_text())
    request.node.user_properties.append(('scope_native_primitive_evidence', json.dumps(evidence)))

"""Synthetic native decode/fix only; no payload execution or fallback."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'trailing', 'eof', 'badtag', 'noncode',
                                 'wrong_thread', 'replay', 'load_slot_swap', 'late_load_fact',
                                 'foreign_buffer', 'fix_slot_swap', 'late_fix_fact',
                                 'later_filename', 'nested', 'late_filename', 'loads_substitute',
                                 'fix_substitute', 'helper_substitute', 'foreign_metadata'))
def test_owned_selected_cache_decode(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    setup = r'''
import importlib.util,marshal
from types import CodeType
cache_case=CACHE_CASE
prepared_cache=Path(importlib.util.cache_from_source(str(dep_root/'__init__.py')))
prepared_cache.parent.mkdir(mode=0o700)
synthetic_code=compile('sentinel = 17\ndef nested():\n    return 19\n',
                       'SYNTHETIC_BEFORE_FIX','exec',dont_inherit=True)
if cache_case=='nested':
    distinct=compile('sentinel = 23','SYNTHETIC_DISTINCT','exec',dont_inherit=True)
    synthetic_code=synthetic_code.replace(co_consts=synthetic_code.co_consts+(distinct,))
cache_body=marshal.dumps({'synthetic':1} if cache_case=='noncode' else synthetic_code)
if cache_case=='trailing':cache_body+=b'SYNTHETIC_TRAILING_DATA'
if cache_case=='eof':cache_body=b''
if cache_case=='badtag':cache_body=b'!'
st=(dep_root/'__init__.py').stat()
cache_header=(importlib.util.MAGIC_NUMBER+b'\0\0\0\0'
              +(int(st.st_mtime)&0xffffffff).to_bytes(4,'little')
              +(st.st_size&0xffffffff).to_bytes(4,'little'))
prepared_cache.write_bytes(cache_header+cache_body);prepared_cache.chmod(0o600)
'''.replace('CACHE_CASE', repr(case))
    script = script.replace('import sample_dep\n', 'import sample_dep\n' + setup, 1)
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_reader import DeclaredCacheReadOwner
from hmp_startup import cache_decoder as dm
from hmp_startup.cache_decoder import SelectedCacheDecodeOwner,CacheDecodeError
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
old_count=checked._fact_cell[2]._count_cell
reader=DeclaredCacheReadOwner.retain(continuation,index).read()
original=reader._buffer
owner=SelectedCacheDecodeOwner.retain(reader)
effect=owner._scope.effects
if case=='wrong_thread':
    import threading
    refused=[]
    def other_thread():
        try:owner.decode()
        except CacheDecodeError:refused.append(True)
        else:refused.append(False)
    other=threading.Thread(target=other_thread);other.start();other.join(timeout=10)
    assert not other.is_alive() and refused==[True] and not owner._started and not owner._failed
if case=='load_slot_swap':
    foreign_slot=['FOREIGN']
    def audit_hook(event,args):
        if event=='marshal.loads' and owner._started:effect.load_slot=foreign_slot
    sys.addaudithook(audit_hook)
if case in ('loads_substitute','fix_substitute','helper_substitute','foreign_metadata'):
    foreign_calls=[]
    def foreign(*args,**kwargs):
        foreign_calls.append('call')
        raise AssertionError('foreign decoder called')
    class ForeignMetadata:
        def __getattribute__(self,name):
            foreign_calls.append('get')
            raise AssertionError('foreign metadata accessed')
        def __call__(self,*args,**kwargs):
            foreign_calls.append('call')
            raise AssertionError('foreign metadata called')
    if case in ('loads_substitute','foreign_metadata'):
        changed_module=owner._scope.decoder.marshal_module;changed_name='loads'
    elif case=='fix_substitute':
        changed_module=owner._scope.decoder.native;changed_name='_fix_co_filename'
    else:
        changed_module=owner._scope.decoder.module;changed_name='_compile_bytecode'
    original_function=vars(changed_module)[changed_name]
    vars(changed_module)[changed_name]=ForeignMetadata() if case=='foreign_metadata' else foreign
if case=='late_filename':
    actual_actor=dm._actor
    def change_filename_before_publication():
        if effect.release_returned:
            owner._scope.decoder.fix_filename(owner._scope.load_slot[0][1],
                                               'SYNTHETIC_CALLBACK_DRIFT')
        return actual_actor()
    dm._actor=change_filename_before_publication
if case in ('late_load_fact','foreign_buffer','fix_slot_swap','late_fix_fact'):
    actual_actor=dm._actor
    def drift_after_return():
        if effect.load_returned and not effect.fix_attempted:
            if case=='late_load_fact':
                copied=tuple(list(dm._LOAD))
                dm._LOAD=owner._scope.load_slot[0]=copied
            elif case=='foreign_buffer':reader._buffer=bytearray(b'FOREIGN')
        if effect.fix_returned:
            if case=='fix_slot_swap':effect.fix_slot=['FOREIGN']
            elif case=='late_fix_fact':
                copied=tuple(list(dm._FIX))
                dm._FIX=owner._scope.fix_slot[0]=copied
        return actual_actor()
    dm._actor=drift_after_return
try:owner.decode()
except CacheDecodeError:
    assert case in ('eof','badtag','noncode','load_slot_swap','late_load_fact',
                    'foreign_buffer','fix_slot_swap','late_fix_fact','late_filename',
                    'loads_substitute','fix_substitute','helper_substitute',
                    'foreign_metadata') and owner._failed
    assert not owner._ready and owner._fact is None and dm._FACT is None
    assert original==bytearray()
    if case in ('eof','badtag','noncode'):
        assert effect.load_attempted and not effect.fix_attempted
        assert effect.load_returned is (case=='noncode')
    if case=='load_slot_swap':
        assert effect.load_slot is foreign_slot and foreign_slot==['FOREIGN']
        assert type(owner._scope.load_slot[0][1]) is CodeType
    if case=='fix_slot_swap':
        assert effect.fix_slot==['FOREIGN'] and owner._scope.fix_slot[0][2] is None
    if case=='foreign_buffer':assert reader._buffer==bytearray(b'FOREIGN')
    if case=='late_filename':
        assert owner._scope.load_slot[0][1].co_filename=='SYNTHETIC_CALLBACK_DRIFT'
    if case in ('loads_substitute','fix_substitute','helper_substitute','foreign_metadata'):
        vars(changed_module)[changed_name]=original_function
        assert foreign_calls==[] and not effect.load_attempted and not effect.fix_attempted

else:
    assert case in ('normal','trailing','wrong_thread','replay','later_filename','nested')
    fact=owner.historical_binding();code=fact[3]
    assert type(code) is CodeType and code.co_filename==str(dep_root/'__init__.py')
    assert effect.load_attempted and effect.load_returned and effect.fix_attempted
    assert effect.fix_returned and fact[6][2] is None and reader._released
    assert original==bytearray() and dm._INPUT is None and owner._payload is None
    if case=='nested':
        nested_codes=tuple(item for item in code.co_consts if type(item) is CodeType)
        assert any(item.co_filename==str(dep_root/'__init__.py') for item in nested_codes)
        assert any(item.co_filename=='SYNTHETIC_DISTINCT' for item in nested_codes)
    if case=='replay':
        try:owner.decode()
        except CacheDecodeError:pass
        else:raise AssertionError('native decode replayed')
        assert owner.historical_binding() is fact
    if case=='later_filename':
        owner._scope.decoder.fix_filename(code,'SYNTHETIC_LATER_MUTATION')
        assert owner.historical_binding() is fact
        assert code.co_filename=='SYNTHETIC_LATER_MUTATION'
assert checked._fact_cell[2]._count_cell is old_count
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

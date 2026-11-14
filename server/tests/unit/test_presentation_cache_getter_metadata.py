"""Getter metadata refuses foreign protocols before any actual cwd observation."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script

CASES = ('valid', 'independent', 'module_foreign', 'module_subclass', 'module_number',
         'os_key_foreign', 'native_key_foreign', 'registry_key_foreign',
         'wrong_getter', 'short_source', 'foreign_source')


@pytest.mark.parametrize('case', CASES)
def test_metadata_protocol_refusal_without_cwd_call(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup import cache_context as cache
import os
native=sys.modules['posix'];getter=os.getcwd
source=cache._ContextSource(None,None,None,None,None,True,getter,os,native)
foreign=[];native_calls=[];armed=[False]
original_module=getter.__module__
class Foreign:
    def __eq__(self,other):
        foreign.append('module.eq');raise AssertionError('foreign module equality')
class ForeignString(str):
    def __eq__(self,other):
        foreign.append('module.eq');raise AssertionError('foreign string equality')
class ForeignKey:
    def __init__(self,name):self.name=name
    def __hash__(self):return hash(self.name)
    def __eq__(self,other):
        if armed[0]:
            foreign.append('key.eq');raise AssertionError('foreign key equality')
        return False
class ForeignSource:
    def __getattribute__(self,name):
        foreign.append('source.getter');raise AssertionError('foreign source getter')
restore=None
if case=='independent':
    source=source._replace(requires_cwd=False,getter=None,os_module=None,posix_module=None)
elif case=='module_foreign':getter.__module__=Foreign()
elif case=='module_subclass':getter.__module__=ForeignString('posix')
elif case=='module_number':getter.__module__=7
elif case in ('os_key_foreign','native_key_foreign','registry_key_foreign'):
    names,keyname=({'os_key_foreign':(vars(os),'getcwd'),
                    'native_key_foreign':(vars(native),'getcwd'),
                    'registry_key_foreign':(sys.modules,'os')}[case])
    old=names.pop(keyname);key=ForeignKey(keyname);names[key]=old
    restore=(names,keyname,old,key)
elif case=='wrong_getter':source=source._replace(getter=os.getpid)
elif case=='short_source':source=tuple.__new__(cache._ContextSource,())
elif case=='foreign_source':source=ForeignSource()
def observe(frame,event,callee):
    if event=='c_call' and callee is getter:native_calls.append(True)
assert sys.getprofile() is None
refused=[];armed[0]=True
sys.setprofile(observe)
try:
    try:cache._getter_current(source)
    except cache.CacheContextError:refused.append(True)
finally:
    sys.setprofile(None);armed[0]=False
    getter.__module__=original_module
    if restore is not None:
        names,keyname,old,key=restore;del names[key];names[keyname]=old
assert refused==([] if case in ('valid','independent') else [True]),case
assert foreign==[] and native_calls==[],(case,foreign,native_calls)
assert sys.getprofile() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

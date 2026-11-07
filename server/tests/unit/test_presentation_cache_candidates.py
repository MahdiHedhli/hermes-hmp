"""Compare planned paths with real isolated CPython; never load a cache artifact."""
from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2]
SCRIPT = r'''
import importlib.util,json,os,sys
sys.path.insert(0,sys.argv[1])
from hmp_startup.cache_candidates import planned_cache_path,CacheCandidateError
case=json.loads(sys.argv[2])
if type(case) is list:
    source,prefix,optimize=case
    sys.pycache_prefix=prefix
    actual=importlib.util.cache_from_source(
        source,optimization='' if optimize==0 else str(optimize))
    actual=os.path.abspath(actual)
    planned=planned_cache_path(source,sys.implementation.cache_tag,optimize,prefix,os.getcwd())
    assert planned.path==actual,(planned.path,actual)
    assert planned.cwd_dependent is (source.rsplit('/',1)[0]=='')
    assert actual not in repr(planned)
else:
    calls=[]
    class Foreign:
        def __str__(self):calls.append('str');raise AssertionError('foreign coercion')
        def __eq__(self,other):calls.append('eq');raise AssertionError('foreign equality')
    values=['/pkg/mod.py',sys.implementation.cache_tag,0,None,os.getcwd()]
    changes={
      'foreign_source':(0,Foreign()),'foreign_tag':(1,Foreign()),
      'foreign_optimize':(2,Foreign()),'foreign_prefix':(3,Foreign()),
      'foreign_cwd':(4,Foreign()),'bool_optimize':(2,True),
      'negative_optimize':(2,-1),'huge_optimize':(2,2**100),
      'tag_separator':(1,'tag/escape'),'relative_prefix':(3,'relative'),
      'dot_prefix':(3,'/cache/../other'),'private_source':(0,'/secrets/code.py'),
      'private_cache':(3,'/.ssh/cache'),'not_source':(0,'/pkg/mod.pyc'),
      'root_needs_cwd':(0,'/mod.py')}
    index,value=changes[case];values[index]=value
    if case=='root_needs_cwd':values[4]=None
    try:planned_cache_path(*values)
    except CacheCandidateError as error:assert str(error)=='BI1_CACHE_CANDIDATE_REFUSED'
    else:raise AssertionError('unqualified input accepted')
    assert calls==[]
assert not any(name in sys.modules for name in
               ('hermes_bootstrap','gateway.run','hmp_plugin.server'))
print(json.dumps({'passed':True,'planned_candidate_loaded':False,'admitted':False}))
'''

SOURCES = ('/root.py', '/.py', '/pkg/mod.py', '/pkg/a.b.py', '/pkg/with space.py', '/pkg/café.py')
PARITY = tuple(itertools.product(SOURCES, (None, '/cache', '/'), (0, 1, 2, 10)))
REFUSALS = ('foreign_source', 'foreign_tag', 'foreign_optimize', 'foreign_prefix', 'foreign_cwd',
            'bool_optimize', 'negative_optimize', 'huge_optimize', 'tag_separator',
            'relative_prefix', 'dot_prefix', 'private_source', 'private_cache',
            'not_source', 'root_needs_cwd')


@pytest.mark.parametrize('case', (*PARITY, *REFUSALS))
def test_planned_source_cache_path(tmp_path, case):
    completed = subprocess.run([sys.executable, '-I', '-B', '-c', SCRIPT, str(SERVER),
                                json.dumps(case)], cwd=tmp_path, capture_output=True,
                               text=True, timeout=10, check=False)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {'passed': True, 'planned_candidate_loaded': False,
                                           'admitted': False}

"""Actual loader hash-key comparison over synthetic code, never executed."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = r'''
import _imp, importlib.util, json, marshal, sys
from types import CodeType
sys.path.insert(0, sys.argv[1])
from hmp_startup.gateway_entry import _interpreter, _interpreter_current
origin = _interpreter()
hash_origin = origin.source_hash
source = b'SYNTHETIC_SOURCE_HASH_VALIDATION_ONLY = 1\n'
path = '/synthetic/source_hash_validation.py'
code = compile(source, path, 'exec')
cache = (importlib.util.MAGIC_NUMBER + (3).to_bytes(4, 'little')
         + hash_origin.builtin(hash_origin.key, source) + marshal.dumps(code))
calls = []
actual_builtin = _imp.source_hash
actual_mode = _imp.check_hash_based_pycs
actual_utility = importlib.util.source_hash
if sys.argv[2] == 'utility_replaced':
    def forbidden_utility(*args): raise AssertionError('utility selected loader key')
    importlib.util.source_hash = forbidden_utility
class SyntheticLoader(hash_origin.loader_type):
    def get_filename(self, fullname): return path
    def path_stats(self, selected):
        assert selected == path
        return {'mtime': 1, 'size': len(source)}
    def get_data(self, selected):
        return source if selected == path else cache
    def set_data(self, *args, **kwargs): raise AssertionError('cache write')
def observe(key, data):
    calls.append((key, data))
    return actual_builtin(key, data)
try:
    _imp.check_hash_based_pycs = 'always'
    _imp.source_hash = observe
    result = hash_origin.function(SyntheticLoader(), 'synthetic_source_hash_validation')
finally:
    _imp.source_hash = actual_builtin
    _imp.check_hash_based_pycs = actual_mode
    importlib.util.source_hash = actual_utility
assert type(result) is CodeType and result.co_code == code.co_code
assert calls == [(hash_origin.key, source)]
assert _interpreter_current(origin) is origin
print(json.dumps({'actualLoaderHashCalls': len(calls), 'executedCode': False}))
'''


@pytest.mark.parametrize('case', ('normal', 'utility_replaced'))
def test_actual_loader_source_hash_key(tmp_path, case):
    script = tmp_path / 'source_hash_probe.py'
    script.write_text(SCRIPT)
    server = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, '-I', '-B', str(script), str(server), case],
        text=True, capture_output=True, timeout=20, env={'LANG': 'C', 'LC_ALL': 'C'},
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'actualLoaderHashCalls': 1, 'executedCode': False}

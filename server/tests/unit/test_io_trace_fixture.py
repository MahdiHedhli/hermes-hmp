"""Observe only original code; keep direct route registration without code hashing."""
from __future__ import annotations

import json
import subprocess
import sys

from .io_trace_fixture import TRACE_HELPERS

SCRIPT = r'''
import json, sys
from pathlib import Path
from types import FunctionType
seen = []
def target(value):
    return value + 1

def second(value):
    return value * 2

original = target.__code__
copied = FunctionType(original.replace(), globals())
assert copied.__code__ == original and copied.__code__ is not original

def observe_target(frame):
    seen.append(('target', frame.f_locals['value']))

def observe_second(frame):
    seen.append(('second', frame.f_locals['value']))

trace_synthetic_boundary(original, 'return value + 1', observe_target)
assert target(1) == 2
assert copied(2) == 3
# Cleanup/interruption fixtures also register routes directly after tracing starts.
_synthetic_trace_routes.setdefault(second.__code__, {})[
    synthetic_line(second.__code__, 'return value * 2')] = observe_second
assert second(4) == 8
assert target(5) == 6
sys.settrace(None)
assert target.__code__ is original
assert seen == [('target', 1), ('second', 4), ('target', 5)], seen
print(json.dumps({'observations': len(seen), 'original_code_unchanged': True}))
'''


def test_trace_routes_match_original_code_and_keep_direct_registration(tmp_path):
    script = tmp_path / 'trace_fixture.py'
    script.write_text(TRACE_HELPERS + SCRIPT)
    result = subprocess.run(
        [sys.executable, '-I', '-B', str(script)],
        env={'LANG': 'C', 'LC_ALL': 'C'},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'observations': 3, 'original_code_unchanged': True}

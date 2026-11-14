"""Actual original receipts over synthetic headers; bytecode is never executed."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script

CASES = ('timestamp', 'unchecked_hash', 'checked_hash', 'flags', 'magic', 'short',
         'magic_drift', 'module_drift')


@pytest.mark.parametrize('case', CASES)
def test_original_bytecode_headers(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script[:script.rfind('print(json.dumps')]
    old = '(stdlib_package/"runtime.pyc").write_bytes(b\'SYNTHETIC_BYTECODE_NOT_EXECUTED\')'
    assert old in script
    flags = {'unchecked_hash': 1, 'checked_hash': 3, 'flags': 2}.get(case, 0)
    header = ('b"bad!"' if case == 'magic' else 'importlib.util.MAGIC_NUMBER')
    raw = header + '+' + repr(flags.to_bytes(4, 'little')) + '+b"12345678"'
    if case == 'short':
        raw = '(' + raw + ')[:15]'
    script = script.replace(old, 'import importlib.util\n' +
                            '(stdlib_package/"runtime.pyc").write_bytes(' + raw + ')', 1)
    script += '''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.bytecode_headers import selected_bytecode_headers, BytecodeHeaderError
handoff=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
original_bytes=checked._fact_cell[2]._bytes_read
original_resources=tuple(checked._fact_cell[2]._origin.records)
'''
    script += '\ncase=' + repr(case) + '\n'
    script += '''
if case=='magic_drift':importlib.util.MAGIC_NUMBER=b"drft"
if case=='module_drift':sys.modules['importlib.util']=ModuleType('importlib.util')
try:headers=selected_bytecode_headers(handoff)
except Exception as error:
    from hmp_startup.gateway_entry import GatewayEntryError
    from hmp_startup.gateway_continuation import GatewayContinuationError
    assert type(error) in (BytecodeHeaderError,GatewayEntryError,GatewayContinuationError)
    assert case in ('flags','magic','short','magic_drift','module_drift'),case
else:
    assert case in ('timestamp','unchecked_hash','checked_hash')
    assert len(headers)==1 and headers[0].flags==''' + repr(flags) + '''
    assert headers[0].payload==b"12345678"
    assert headers[0].receipt.bytecode_header.endswith(b"12345678")
    assert '12345678' not in repr(headers[0])
assert checked._fact_cell[2]._bytes_read==original_bytes
assert tuple(checked._fact_cell[2]._origin.records)==original_resources
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)

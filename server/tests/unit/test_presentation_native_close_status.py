"""Close-status DATA is conservative and never an original-ledger permission."""
from __future__ import annotations

import pytest

from hmp_plugin import presentation_startup_artifacts as a


@pytest.mark.parametrize('case', ('complete', 'pending', 'unknown', 'refused',
                                 'foreign_close', 'foreign_state', 'foreign_result',
                                 'foreign_receipt', 'foreign_fd', 'copied_fd',
                                 'wrong_close', 'extra_receipt'))
def test_close_mirror_needs_receipt_but_cannot_grant_authority(case):
    foreign_calls = []

    class Foreign:
        def __getattr__(self, name):
            foreign_calls.append(name)
            raise AssertionError('foreign getter')

        def __len__(self):
            foreign_calls.append('len')
            raise AssertionError('foreign length')

        def __eq__(self, other):
            foreign_calls.append('eq')
            raise AssertionError('foreign equality')

    fd = 1234
    close_values = dict.fromkeys(a._NativeCloseAllocation._fields)
    close_values.update(state=[True, False], raw=[None], result=[None])
    close = a._NativeCloseAllocation(**close_values)
    allocation_values = dict.fromkeys(a._NativeOpenAllocation._fields)
    allocation_values.update(close=close, raw=[fd], result=[None], refused=[False])
    allocation = a._NativeOpenAllocation(**allocation_values)
    row = a._NativeOpenedDescriptor(allocation, fd, close)
    allocation.result[0] = (allocation, row)
    close.result[0] = (close, fd, None)
    if case == 'pending':
        close.result[0] = None
    elif case == 'unknown':
        close.state[1] = True
    elif case == 'refused':
        allocation.refused[0] = True
    elif case == 'foreign_close':
        row = row._replace(close=Foreign())
    elif case in ('foreign_state', 'foreign_result'):
        close = close._replace(**{case.removeprefix('foreign_'): Foreign()})
        allocation = allocation._replace(close=close)
        row = row._replace(allocation=allocation, close=close)
        allocation.result[0] = (allocation, row)
    elif case == 'foreign_receipt':
        close.result[0] = Foreign()
    elif case == 'foreign_fd':
        row = row._replace(fd=Foreign())
    elif case == 'copied_fd':
        copied = int(str(fd))
        assert copied is not fd
        close.result[0] = (close, copied, None)
    elif case == 'wrong_close':
        close.result[0] = (object(), fd, None)
    elif case == 'extra_receipt':
        close.result[0] = (close, fd, None, 'extra')
    assert row.closed is (case == 'complete')
    assert foreign_calls == []
    # Even a coherent constructed success mirror is not an original allocation.
    with pytest.raises(a.ArtifactObservationError):
        a._native_descriptor_closed(row, object())
    assert foreign_calls == []

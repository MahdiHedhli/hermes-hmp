"""Foreign nested metadata must not execute before original-actor admission."""
import pytest

from hmp_plugin.presentation_credential_begin_write import _BeginWriterScope
from hmp_plugin.presentation_credential_result_body import NativeResultBodyOwner, _BodyScope
from hmp_plugin.presentation_credential_result_read import (
    NativeResultEnvelopeReceiver,
    _ResultReadScope,
)
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_remote_cleanup import _TaskAllocation


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary",
    ("envelope", "envelope_scope", "write_scope", "allocation", "task"))
async def test_candidate_preflight_does_not_traverse_foreign_metadata(boundary):
    called = []

    class Foreign:
        def __getattribute__(self, key):
            called.append(key)
            raise AssertionError("foreign metadata executed")

    foreign = Foreign()
    owner = NativeResultBodyOwner.__new__(NativeResultBodyOwner)
    envelope = NativeResultEnvelopeReceiver.__new__(NativeResultEnvelopeReceiver)
    allocation = _TaskAllocation(foreign, None)
    writer = _BeginWriterScope._make([None] * len(_BeginWriterScope._fields))
    writer = writer._replace(allocation=foreign if boundary == "allocation" else allocation)
    reader = _ResultReadScope._make([None] * len(_ResultReadScope._fields))
    reader = reader._replace(write_scope=foreign if boundary == "write_scope" else writer)
    scope = _BodyScope._make([None] * len(_BodyScope._fields))
    scope = scope._replace(envelope=foreign if boundary == "envelope" else envelope,
        envelope_scope=foreign if boundary == "envelope_scope" else reader)
    owner._scope = owner._scope_origin = scope
    envelope._scope_origin = reader
    envelope._body_owner_snapshot = owner
    # Refusal must happen before private candidate access, poisoning or withdrawal.
    with pytest.raises(FrameError):
        owner.current_candidate()
    assert called == []
    assert "_failed" not in vars(owner) and "_retired" not in vars(owner)

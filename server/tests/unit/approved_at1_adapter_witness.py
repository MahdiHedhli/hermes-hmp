"""Exact test-only inverse of approved AT1 adapter integration; no detector exemptions."""
from __future__ import annotations

import hashlib

APPROVED_PRE_AT1_ADAPTER_SHA256 = "f8a5d6a196c3e4622db50dd04303df2eb401467f87feab894d663ab93f68b3a3"
APPROVED_AT1_ADAPTER_SHA256 = "daa6d401e087d2ae265b1b7199aec4c00c46e2236772fbd14cb49a45d325c101"

EDIT_0_ACCEPTED = r'''import secrets
import sys
import threading
'''
EDIT_0_PREVIOUS = r'''import secrets
import threading
'''
EDIT_0_SHA256 = "55f3bbf3a055c56557ccf12e25200aaa9688a972151eb82b840262b16bef7cce"

EDIT_1_ACCEPTED = r'''    return ctx


_AT1_ADAPTER_MODULE = sys.modules[__name__]
_AT1_PLUGIN_MODULE = sys.modules[__package__]


class HmpAdapter(BasePlatformAdapter):
'''
EDIT_1_PREVIOUS = r'''    return ctx


class HmpAdapter(BasePlatformAdapter):
'''
EDIT_1_SHA256 = "21c7e4fcd5ee85c3f95071d49559f788c9856d04d4c6d7d550fe4c172e030013"

EDIT_2_ACCEPTED = r'''            push_relay_factory=lambda: RelayClient(ctx.identity),
            approval_test_owners=(_AT1_PLUGIN_MODULE, _AT1_ADAPTER_MODULE),
        )
        try:
            await srv.start()
'''
EDIT_2_PREVIOUS = r'''            push_relay_factory=lambda: RelayClient(ctx.identity),
        )
        try:
            await srv.start()
'''
EDIT_2_SHA256 = "8d84d33f8c768d34c066784e5b97edfe8cfd6d08223fc8eed9288f2be9dacb88"

EDIT_3_ACCEPTED = r'''            else:
                self._known_profiles = tuple(profiles) if profiles is not None else None
                await srv.start_approval_test(self._record, self._nonce)
            if ctx.bridge is not None:
'''
EDIT_3_PREVIOUS = r'''            else:
                self._known_profiles = tuple(profiles) if profiles is not None else None
            if ctx.bridge is not None:
'''
EDIT_3_SHA256 = "8a55295de8b6b25274e3c0ec02febe83a57a02a257d78d37e6f890c35df47932"

EDIT_4_ACCEPTED = r'''    async def disconnect(self) -> None:
        await self._cancel_profile_refresh()
        srv = self._server
        if srv is not None:
            # Keep the current pointer/record/dependencies while actual teardown
            # owns cleanup. Cancellation or unknown join must prevent replacement.
            await srv.stop(notify=False)
            if self._server is srv:
                self._server = None
            self._drop_record()
            self._close_generation(srv.ctx)
            srv.ctx.store.close()
        else:
            self._drop_record()
        self._mark_disconnected()

'''
EDIT_4_PREVIOUS = r'''    async def disconnect(self) -> None:
        await self._cancel_profile_refresh()
        srv, self._server = self._server, None
        self._drop_record()
        if srv is not None:
            await srv.stop(notify=False)
            self._close_generation(srv.ctx)
            srv.ctx.store.close()
        self._mark_disconnected()

'''
EDIT_4_SHA256 = "2c439e0b84714628358c66ab7603fc480ce1ebac66ae2e6e4dc3058b8119d226"

APPROVED_ADAPTER_EDITS = (
    (EDIT_0_ACCEPTED, EDIT_0_PREVIOUS, EDIT_0_SHA256),
    (EDIT_1_ACCEPTED, EDIT_1_PREVIOUS, EDIT_1_SHA256),
    (EDIT_2_ACCEPTED, EDIT_2_PREVIOUS, EDIT_2_SHA256),
    (EDIT_3_ACCEPTED, EDIT_3_PREVIOUS, EDIT_3_SHA256),
    (EDIT_4_ACCEPTED, EDIT_4_PREVIOUS, EDIT_4_SHA256),
)


def reverse_approved_at1_adapter(source: str) -> str:
    """Reject changed/duplicate/relocated exact sites; retain other source for the detector."""
    # These two adjacent lines are OUTSIDE EDIT_1_ACCEPTED. Moving that whole
    # substring elsewhere cannot carry this independently source-backed site.
    before = '    log_event("adapter_open", outcome=result.status.value)\n'
    after = "    def __init__(self, config: Any) -> None:\n"
    assert source.count(before + EDIT_1_ACCEPTED + after) == 1
    for accepted, previous, expected_hash in APPROVED_ADAPTER_EDITS:
        assert hashlib.sha256(accepted.encode()).hexdigest() == expected_hash
        assert source.count(accepted) == 1
        source = source.replace(accepted, previous, 1)
    assert "_AT1_ADAPTER_MODULE" not in source
    assert "_AT1_PLUGIN_MODULE" not in source
    assert "start_approval_test(" not in source
    return source

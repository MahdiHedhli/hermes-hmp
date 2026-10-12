from types import SimpleNamespace

import pytest

from hmp_plugin.approval_test_authority import target_current
from hmp_plugin.approval_test_producer import TargetBinding
from hmp_plugin.contract import AuthzState, DirectSendEndpoint, WriteGate, WriteGateState


@pytest.mark.parametrize("failure", [None, "instance", "inactive", "user", "owner", "send",
                                     "phone", "grant", "session", "closed", "endpoint"])
def test_each_current_authority_gate_is_required(failure) -> None:
    target = TargetBinding("synthetic-instance", "synthetic-user", "default", "synthetic-tip",
                           "synthetic-device")
    device = {"state": "REVOKED" if failure == "inactive" else "ACTIVE",
              "user_id": "other" if failure == "user" else target.user_id}
    ctx = SimpleNamespace(
        iid="other" if failure == "instance" else target.instance_id,
        prompt_store=SimpleNamespace(closed=failure == "closed", phone_closed=False),
        store=SimpleNamespace(get_device=lambda _: device),
        is_approval_owner_device=lambda _: failure != "owner",
        direct_send_effective=lambda: failure != "send",
        is_phone_chat_available=lambda: failure != "phone",
        write_gate=lambda: WriteGate(state=WriteGateState.OPEN, reason=None),
        bridge=SimpleNamespace(
            direct_send_endpoint=lambda _: (None if failure == "endpoint" else DirectSendEndpoint(
                host="127.0.0.1", port=9, api_key="synthetic-key", path_prefix="")),
            authz_state=lambda *_: (AuthzState.PENDING_OPERATOR if failure == "grant"
                                   else AuthzState.AUTHORIZED),
            resolve_bot_chat=lambda _: SimpleNamespace(
                live_tip_session_id="other" if failure == "session" else target.session_id),
        ),
    )
    assert target_current(ctx, target) is (failure is None)


def test_device_revoked_during_native_session_lookup_refuses_admission() -> None:
    target = TargetBinding("synthetic-instance", "synthetic-user", "default", "synthetic-tip",
                           "synthetic-device")
    device = {"state": "ACTIVE", "user_id": target.user_id}
    def canonical(_):
        device["state"] = "REVOKED"
        return SimpleNamespace(live_tip_session_id=target.session_id)
    ctx = SimpleNamespace(
        iid=target.instance_id, prompt_store=SimpleNamespace(closed=False, phone_closed=False),
        store=SimpleNamespace(get_device=lambda _: dict(device)),
        is_approval_owner_device=lambda _: True, direct_send_effective=lambda: True,
        is_phone_chat_available=lambda: True,
        write_gate=lambda: WriteGate(state=WriteGateState.OPEN, reason=None),
        bridge=SimpleNamespace(
            authz_state=lambda *_: AuthzState.AUTHORIZED, resolve_bot_chat=canonical,
            direct_send_endpoint=lambda _: DirectSendEndpoint(
                host="127.0.0.1", port=9, api_key="synthetic-key", path_prefix=""),
        ),
    )
    assert not target_current(ctx, target)

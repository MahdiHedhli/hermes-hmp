"""Read-only AT1 admission using existing device, bot and canonical-session gates."""
from __future__ import annotations

from .approval_test_producer import TargetBinding
from .contract import AuthzState, WriteGateState
from .gate import direct_send_gate
from .request_ctx import ServerContext


def target_current(ctx: ServerContext, target: TargetBinding) -> bool:
    """Run on the listener's owned worker; exceptions deny without leaking target details."""
    try:
        if type(target) is not TargetBinding or target.instance_id != ctx.iid:
            return False
        store = ctx.prompt_store
        if store is None or store.closed or store.phone_closed:
            return False
        device = ctx.store.get_device(target.device_id)
        if device is None or device["state"] != "ACTIVE" or device["user_id"] != target.user_id:
            return False
        if not ctx.is_approval_owner_device(target.device_id):
            return False
        if not ctx.direct_send_effective() or not ctx.is_phone_chat_available():
            return False
        bridge = ctx.bridge
        if (bridge is None
                or bridge.authz_state(target.user_id, target.profile) is not AuthzState.AUTHORIZED):
            return False
        operational = direct_send_gate(
            base_write_gate=ctx.write_gate(), flag_enabled=True,
            endpoint=bridge.direct_send_endpoint(target.profile),
        )
        if operational.state not in (WriteGateState.OPEN, WriteGateState.OPEN_GUARDED):
            return False
        canonical = bridge.resolve_bot_chat(target.profile)
        if canonical is None or canonical.live_tip_session_id != target.session_id:
            return False
        # Native profile/session reads can take time: recheck local authority afterwards.
        device = ctx.store.get_device(target.device_id)
        return (
            device is not None and device["state"] == "ACTIVE"
            and device["user_id"] == target.user_id
            and ctx.is_approval_owner_device(target.device_id)
            and not store.closed and not store.phone_closed
            and ctx.direct_send_effective() and ctx.is_phone_chat_available()
        )
    except Exception:
        return False


def target_for_device(ctx: ServerContext, device_id: str, profile: str,
                      session_id: str) -> TargetBinding | None:
    """Resolve user identity from host state, never from operator DATA."""
    try:
        device = ctx.store.get_device(device_id)
        if device is None or device["state"] != "ACTIVE":
            return None
        user_id = device["user_id"]
        if type(user_id) is not str or not user_id:
            return None
        target = TargetBinding(ctx.iid, user_id, profile, session_id, device_id)
        return target if target_current(ctx, target) else None
    except Exception:
        return None

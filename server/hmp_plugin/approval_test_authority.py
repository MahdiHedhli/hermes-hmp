"""Read-only AT1 admission using existing device, bot and canonical-session gates."""
from __future__ import annotations

from .approval_test_producer import TargetBinding
from .contract import AuthzState
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
        canonical = bridge.resolve_bot_chat(target.profile)
        return canonical is not None and canonical.live_tip_session_id == target.session_id
    except Exception:
        return False

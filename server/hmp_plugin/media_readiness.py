"""Closed local-image diagnostics; callers must authenticate and authorize the bot first.

This projection never opens files, resolves references, changes rights, or grants execution.
The runtime route must fence its sampled authority before disclosing this DTO.
"""
from collections.abc import Mapping


class MediaReadinessUnavailable(ValueError):
    def __init__(self):
        super().__init__("media readiness unavailable")


def host_setting(extra: object) -> str:
    """Missing opt-in is disabled; malformed/unknown configuration stays unknown."""
    if not isinstance(extra, Mapping):
        return "unknown"
    block = extra.get("local_media", {})
    if not isinstance(block, Mapping):
        return "unknown"
    value = block.get("enabled", False)
    if type(value) is not bool:
        return "unknown"
    return "enabled" if value else "disabled"


def project(*, entitlement: str, host: str, api: str) -> dict[str, object]:
    """Separate access, opt-in, and runtime availability without claiming an image exists."""
    if (type(entitlement) is not str or entitlement not in {"granted", "missing", "unknown"}
            or type(host) is not str or host not in {"enabled", "disabled", "unknown"}
            or type(api) is not str or api not in {"available", "unavailable", "unknown"}):
        raise MediaReadinessUnavailable()
    reasons = []
    if entitlement != "granted":
        reasons.append("media_read_missing" if entitlement == "missing" else "media_read_unknown")
    if host != "enabled":
        reasons.append("host_flag_disabled" if host == "disabled" else "host_flag_unknown")
    if api != "available":
        reasons.append("media_api_unavailable" if api == "unavailable" else "media_api_unknown")
    return {
        "entitlement": entitlement, "host_setting": host, "runtime_api": api,
        "operational": not reasons, "reasons": sorted(reasons),
        # No media access-request transport exists yet. Never advertise request_access or Fix.
        "action": "none" if not reasons else "contact_host_operator",
        "image_availability": "not_probed",
    }

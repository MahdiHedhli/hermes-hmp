"""Fixed, content-free permission-readiness projections (AR1).

This module contains only closed wire mapping. Operational feature gates remain in their existing
call sites; this code must not turn a readiness result into permission to execute an operation.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from . import compat

MAX_RESPONSE_BYTES = 2_048
MAX_SAFE_INTEGER = 9_007_199_254_740_991
GENERATION_RE = re.compile(r"[0-9a-f]{32}")

_CAPABILITY_REASON = {
    compat.Unavailable.HERMES_NOT_FOUND: ("hermes_not_found", "hermes_not_found"),
    compat.Unavailable.VERSION_BELOW_FLOOR: ("below_floor", "version_below_floor"),
    compat.Unavailable.DEPENDENCY_MISSING: ("dependency_missing", "dependency_missing"),
    compat.Unavailable.PROBE_FAILED: ("probe_failed", "probe_failed"),
    compat.Unavailable.REQUIRES_READ: ("requires_read", "requires_read"),
    compat.Unavailable.REQUIRES_SEND: ("requires_send", "requires_send"),
}


class ReadinessUnavailableError(Exception):
    """A fixed refusal classification with no source-provided text."""

    def __init__(self) -> None:
        super().__init__("readiness unavailable")


def capability_axis(status: object | None) -> tuple[str, str | None]:
    """Map one exact FeatureStatus; absent well-formed entry is indeterminate."""
    if status is None:
        return "unknown", "compatibility_unknown"
    if not isinstance(status, compat.FeatureStatus) or type(status.available) is not bool:
        raise ReadinessUnavailableError()
    if status.available:
        if status.reason is not None:
            raise ReadinessUnavailableError()
        return "available", None
    if status.reason is None:
        return "unknown", "compatibility_unknown"
    if not isinstance(status.reason, compat.Unavailable):
        raise ReadinessUnavailableError()
    return _CAPABILITY_REASON[status.reason]


def capability_snapshot(result: object) -> dict[str, dict[str, str]]:
    """Return only the closed global capability DTO; labels and dependencies never escape."""
    if not isinstance(result, compat.CompatResult):
        raise ReadinessUnavailableError()
    eligibility = result.eligibility
    if (
        not isinstance(eligibility, compat.Eligibility)
        or not isinstance(eligibility.features, Mapping)
    ):
        raise ReadinessUnavailableError()
    values: dict[str, dict[str, str]] = {}
    for name, feature in (("jobs", compat.Feature.JOBS), ("model", compat.Feature.MODEL)):
        axis, _reason = capability_axis(eligibility.features.get(feature))
        values[name] = {"capability": axis}
    return values


def feature_status_fields(
    *,
    capability: str,
    capability_reason: str | None,
    entitlement: str,
    host_setting: str,
    profile_api: str,
) -> dict[str, Any]:
    """Build one feature DTO from validated closed axes."""
    reasons: set[str] = {"api_not_probed"}
    if capability_reason is not None:
        reasons.add(capability_reason)
    if entitlement == "missing":
        reasons.add("controls_missing")
    elif entitlement == "unknown":
        reasons.add("controls_unknown")
    if host_setting == "disabled":
        reasons.add("host_flag_disabled")
    if profile_api == "missing":
        reasons.add("profile_api_missing")
    elif profile_api == "unknown":
        reasons.add("profile_api_unknown")

    if (
        capability in {"hermes_not_found", "below_floor", "dependency_missing"}
        or host_setting == "disabled"
        or profile_api == "missing"
    ):
        action = "plan_host_remediation"
    elif entitlement == "missing":
        action = "request_access"
    else:
        action = "check_host"
    return {
        "capability": capability,
        "entitlement": entitlement,
        "host_setting": host_setting,
        "profile_api": profile_api,
        "api_reachability": "not_probed",
        "reasons": sorted(reasons),
        "action": action,
    }


def validate_feature_axes(
    capability: str,
    entitlement: str,
    host_setting: str,
    profile_api: str,
) -> None:
    """Guard internal projection mistakes before building a response."""
    if capability not in {
        "available", "hermes_not_found", "below_floor", "dependency_missing",
        "probe_failed", "requires_read", "requires_send", "unknown",
    }:
        raise ReadinessUnavailableError()
    if entitlement not in {"granted", "missing", "unknown"}:
        raise ReadinessUnavailableError()
    if host_setting not in {"enabled", "disabled", "unknown"}:
        raise ReadinessUnavailableError()
    if profile_api not in {"configured", "missing", "unknown"}:
        raise ReadinessUnavailableError()

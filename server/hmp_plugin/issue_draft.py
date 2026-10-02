"""User-reviewed GitHub issue draft for `hermes hmp compat --issue-draft` (owner policy 2026-10-01).

Pure and offline: standard library only, no network, no subprocess, no browser. The text is printed
for the operator to read, edit and paste. Nothing is submitted, and no data goes into a URL.

Every value that can appear in a draft is on the allowlist below and is re-validated at this
helper boundary (not only by the CLI), so even a caller mistake cannot carry a profile name, device
or chat id, path, host address, key, config, message content, log line, exception text or build
fingerprint into the output. Types are checked before anything is formatted: a value of the wrong
type is replaced by a fixed word or refused with fixed text, and is never `repr`'d, `str`'d or
echoed.

Two inputs can make a draft:

- a failure HMP's own static check observed: a feature whose own Hermes dependency is actually
  missing or whose probe failed (`dependency_missing`, `probe_failed`), with HMP's own dependency
  labels; and
- an operator report, given explicitly as `--feature` plus `--failure-code`. This is the operator's
  statement about a failure they saw, for the case the static probe cannot see (an upstream HTTP
  API that answered with a failure although every probe passed). It is not an availability
  decision, grant or ledger entry, and the draft says it was reported, not observed.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from . import compat, hermes_version

ISSUES_URL = "https://github.com/MahdiHedhli/hermes-hmp/issues/new"
PASTE_LINE = f"Open {ISSUES_URL} and paste the text above."
REVIEW_LINE = "Review and edit the text above before posting. HMP has not sent anything."
NOTHING_TO_REPORT = "No HMP feature failure detected; nothing to report."

# `--feature` -> the HMP error codes (`contract.ErrorCode` values) that feature can answer with when
# its Hermes side fails. Anything else is refused, never echoed.
REPORTABLE_CODES: Mapping[str, frozenset[str]] = {
    "read": frozenset({"other"}),
    "session_browsing": frozenset({"not_found", "other"}),
    "send": frozenset({"write_gate_closed", "api_server_unavailable"}),
    "jobs": frozenset({"cron_unavailable"}),
    "model": frozenset({"model_unavailable"}),
}

# Permission, routing and authorization outcomes. They are real and have their own explanation, so
# they are never turned into a Hermes-version report. `not_found` is one of them for every feature
# except session browsing, where an absent route answers `not_found`.
OWN_REASON_CODES: frozenset[str] = frozenset(
    {"forbidden", "unauthorized", "unauthenticated", "revoked", "not_routed", "refused_allow_all"}
)

FEATURES: tuple[str, ...] = tuple(REPORTABLE_CODES)

# Canonical HMP version: semver with an optional fixed-vocabulary pre-release (`-f1`, `-rc.1`,
# `-beta2`) and a short numeric build (`+5`). Free-form suffixes are not accepted.
_HMP_VERSION_RE = re.compile(
    r"(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})"
    r"(?:-(?:alpha|beta|rc|f)(?:\.?[0-9]{1,3})?)?(?:\+[0-9]{1,8})?"
)
_SHA_RE = re.compile(r"[0-9a-f]{40}")
_OS_FAMILIES: Mapping[str, str] = {"darwin": "macOS", "linux": "Linux", "win32": "Windows"}
_PLATFORM_RE = re.compile(r"(macOS|Linux|Windows|other), Python ([0-9]{1,2})\.([0-9]{1,2})")
_MAX_PYTHON_PART = 99
_STATIC_REASONS = frozenset(
    {compat.Unavailable.DEPENDENCY_MISSING, compat.Unavailable.PROBE_FAILED}
)


def _label(spec: compat.DependencySpec) -> str:
    return f"{spec.module}.{spec.qualname}" if spec.qualname else spec.module


# HMP's own constant dependency labels, per feature. A label outside its own feature's table is
# dropped, whatever its shape.
_FEATURE_LABELS: Mapping[compat.Feature, frozenset[str]] = {
    compat.Feature.READ: frozenset(_label(s) for s in compat.READ_CORE_DEPENDENCIES),
    compat.Feature.SESSION_BROWSING: frozenset(
        _label(s) for s in compat.SESSION_BROWSING_DEPENDENCIES
    ),
    compat.Feature.SEND: frozenset(_label(s) for s in compat.DIRECT_SEND_DEPENDENCIES),
    compat.Feature.JOBS: frozenset(_label(s) for s in compat.CRON_DEPENDENCIES),
    compat.Feature.MODEL: frozenset(_label(s) for s in compat.MODEL_DEPENDENCIES),
}


def known_labels(feature: object, missing: object) -> tuple[str, ...]:
    """The members of `missing` that are HMP's own dependency labels for exactly this feature."""
    if not isinstance(feature, compat.Feature) or not isinstance(missing, tuple | list):
        return ()
    allowed = _FEATURE_LABELS[feature]
    return tuple(m for m in missing if type(m) is str and m in allowed)


def failure_detail(feature: object, status: object) -> str:
    """`reason` or `reason: label, label` for a failed feature, from fixed values only."""
    reason = getattr(status, "reason", None)
    detail = reason.value if isinstance(reason, compat.Unavailable) else "unknown"
    labels = known_labels(feature, getattr(status, "missing", ()))
    return detail + (": " + ", ".join(labels) if labels else "")


class ReportRequestError(ValueError):
    """The `--feature`/`--failure-code` pair is not an accepted report. Fixed text only."""


@dataclass(frozen=True)
class OperatorReport:
    feature: str
    failure_code: str


@dataclass(frozen=True)
class OwnReason:
    """A permission, setting or routing code: explained, never drafted."""

    feature: str
    failure_code: str


def check_report_request(feature: object, failure_code: object) -> OperatorReport | OwnReason:
    """Validate the operator's explicit report context. Raises `ReportRequestError`."""
    if not isinstance(feature, str) or feature not in REPORTABLE_CODES:
        raise ReportRequestError("unknown feature")
    if not isinstance(failure_code, str):
        raise ReportRequestError("unknown failure code")
    # Return our own constants, never the caller's objects.
    own_feature = next(k for k in REPORTABLE_CODES if k == feature)
    if failure_code in REPORTABLE_CODES[feature]:
        return OperatorReport(
            own_feature, next(c for c in REPORTABLE_CODES[feature] if c == failure_code)
        )
    if failure_code in OWN_REASON_CODES or (
        failure_code == "not_found" and feature != "session_browsing"
    ):
        own_code = failure_code if failure_code in OWN_REASON_CODES else "not_found"
        return OwnReason(own_feature, own_code)
    raise ReportRequestError("failure code does not match feature")


_T = TypeVar("_T", "OperatorReport", "OwnReason")


def _recheck(item: object, kind: type[_T]) -> _T:
    """`item` re-run through `check_report_request`; it must come out as `kind`. One fixed error
    text for every refusal, so nothing about the input is echoed."""
    if isinstance(item, kind):
        try:
            checked = check_report_request(item.feature, item.failure_code)
        except ReportRequestError:
            checked = None
        if isinstance(checked, kind):
            return checked
    raise ReportRequestError("not an accepted report")


def own_reason_text(item: object) -> str:
    """Revalidates `item` before interpolating it. Raises `ReportRequestError` (fixed text)."""
    checked = _recheck(item, OwnReason)
    return (
        f"`{checked.failure_code}` on {checked.feature} is a permission, routing or setting "
        "outcome (device controls, bot authorization, host flag or route), not evidence of a "
        "Hermes version incompatibility. No issue draft was prepared. "
        "Check `hermes hmp health check` and `hermes hmp setup check` on the host."
    )


def hmp_version(plugin_yaml: Path | None = None) -> str:
    """`version:` from the plugin manifest, or `unknown`."""
    path = plugin_yaml if plugin_yaml is not None else Path(__file__).with_name("plugin.yaml")
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                return _safe_hmp_version(line.partition(":")[2].strip().strip("\"'"))
    except (OSError, UnicodeDecodeError):
        pass
    return "unknown"


def _safe_hmp_version(value: object) -> str:
    return value if isinstance(value, str) and _HMP_VERSION_RE.fullmatch(value) else "unknown"


def _python_part(value: object, fallback: int) -> int:
    ok = type(value) is int and 0 <= value <= _MAX_PYTHON_PART
    return value if ok else fallback  # type: ignore[return-value]


def platform_text(platform: str | None = None, version_info: tuple[int, int] | None = None) -> str:
    """OS family plus Python `major.minor`; never a release string, host name or path. The family
    is looked up in a fixed table and the numbers must be small ints."""
    key = platform if platform is not None else sys.platform
    family = _OS_FAMILIES.get(key, "other") if isinstance(key, str) else "other"
    live = sys.version_info[:2]
    given = version_info if isinstance(version_info, tuple) and len(version_info) == 2 else live
    major = _python_part(given[0], live[0])
    minor = _python_part(given[1], live[1])
    return f"{family}, Python {major}.{minor}"


def _safe_platform(value: object) -> str:
    """Only a canonical, generated `<family>, Python N.N` string passes; anything else is replaced
    by the live value."""
    if isinstance(value, str) and _PLATFORM_RE.fullmatch(value):
        return value
    return platform_text()


def _safe_version(value: object) -> hermes_version.HermesVersion:
    """A rebuilt, round-tripped `HermesVersion`, or `UNKNOWN_VERSION`. Nothing from the input
    object is formatted unless its type is exact."""
    unknown = hermes_version.UNKNOWN_VERSION
    if not isinstance(value, hermes_version.HermesVersion):
        return unknown
    scheme, source, parts = value.scheme, value.source, value.parts
    if not isinstance(scheme, hermes_version.Scheme) or not isinstance(
        source, hermes_version.VersionSource
    ):
        return unknown
    if not isinstance(parts, tuple) or any(type(p) is not int for p in parts):
        return unknown
    if scheme is hermes_version.Scheme.SEMVER and len(parts) == 3:
        if source not in {hermes_version.VersionSource.LITERAL, hermes_version.VersionSource.STAMP}:
            return unknown
        text = ".".join(str(p) for p in parts)
        if hermes_version.parse_semver(text) != parts:
            return unknown
        return hermes_version.HermesVersion(scheme, parts, source)
    if scheme is hermes_version.Scheme.CALVER and len(parts) == 4:
        if source is not hermes_version.VersionSource.RELEASE_DATE:
            return unknown
        year, month, day, patch = parts
        text = f"{year}.{month}.{day}" + (f".{patch}" if patch else "")
        if hermes_version.parse_calver(text) != parts:
            return unknown
        return hermes_version.HermesVersion(scheme, parts, source)
    return unknown


def static_failures(
    eligibility: object,
) -> tuple[tuple[compat.Feature, compat.FeatureStatus], ...]:
    """Features whose own Hermes dependency is actually missing. A version below the floor, a
    missing install and a consequence of read being down are not bugs and are not drafted. Only
    real `compat.Feature` keys, `FeatureStatus` values and static reason enums count."""
    if not isinstance(eligibility, compat.Eligibility) or not isinstance(
        eligibility.features, Mapping
    ):
        return ()
    return tuple(
        (feature, status)
        for feature, status in eligibility.features.items()
        if isinstance(feature, compat.Feature)
        and isinstance(status, compat.FeatureStatus)
        and status.available is False
        and isinstance(status.reason, compat.Unavailable)
        and status.reason in _STATIC_REASONS
    )


@dataclass(frozen=True)
class Draft:
    title: str
    body: str

    def render(self) -> str:
        return f"Title: {self.title}\n\n{self.body}\n\n{REVIEW_LINE}\n{PASTE_LINE}\n"


def _version_lines(
    eligibility: compat.Eligibility | None, plugin_version: str, platform: str
) -> list[str]:
    version = _safe_version(eligibility.version if eligibility is not None else None)
    sha = eligibility.git_sha if eligibility is not None else None
    return [
        f"- hermes_version: {version.text}",
        f"- hermes_version_source: {version.source.value}",
        f"- hermes_git_sha: {sha if isinstance(sha, str) and _SHA_RE.fullmatch(sha) else 'none'}",
        f"- hmp_version: {plugin_version}",
        f"- platform: {platform}",
    ]


def build_draft(
    eligibility: object,
    report: object,
    *,
    plugin_version: str | None = None,
    platform: str | None = None,
) -> Draft | None:
    """The issue draft, or None when there is nothing to report.

    Every input is revalidated here. A `report` that is not an `OperatorReport` the request check
    accepts raises `ReportRequestError` with fixed text and nothing from it is echoed."""
    checked: OperatorReport | None = None
    if report is not None:
        checked = _recheck(report, OperatorReport)
    safe_eligibility = eligibility if isinstance(eligibility, compat.Eligibility) else None
    failures = static_failures(safe_eligibility)
    if not failures and checked is None:
        return None
    version = _safe_hmp_version(plugin_version if plugin_version is not None else hmp_version())
    plat = _safe_platform(platform if platform is not None else platform_text())

    lines = ["## Environment", *_version_lines(safe_eligibility, version, plat), ""]
    if failures:
        lines += [
            "## Observed by HMP's static dependency check",
            "",
            "HMP's own check found a Hermes API this feature needs to be missing. That is a fact "
            "about this install; it does not establish what caused it.",
            "",
        ]
        for feature, status in failures:
            labels = known_labels(feature, status.missing)
            lines += [
                f"- feature: {feature.value}",
                f"  reason: {status.reason.value if status.reason else 'unknown'}",
                f"  missing: {', '.join(labels) if labels else 'none'}",
            ]
        lines.append("")
    if checked is not None:
        lines += [
            "## Reported by the operator",
            "",
            f"- reported_feature: {checked.feature}",
            f"- reported_failure_code: {checked.failure_code}",
            "- report_origin: operator",
            "",
            "Reported by the operator, not automatically observed: the operator supplied this "
            "feature and code with `--feature` and `--failure-code`. HMP did not observe the "
            "failure, and this report does not establish that the Hermes version, HMP or "
            "anything else caused it. The same code is also returned when a host setting is "
            "off or a phone lacks controls.",
            "",
        ]
    lines += ["## What happened", "", "<describe what you did and what you expected>"]

    if checked is not None:
        title = f"HMP: {checked.feature} failure ({checked.failure_code})"
    else:
        title = f"HMP: {failures[0][0].value} unavailable on this Hermes"
    version_text = _safe_version(
        safe_eligibility.version if safe_eligibility is not None else None
    ).text
    return Draft(title=f"{title}, Hermes {version_text}", body="\n".join(lines))

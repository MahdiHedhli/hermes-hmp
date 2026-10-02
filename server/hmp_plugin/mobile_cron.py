"""Narrow, owner-gated mobile facade over Hermes's profile-scoped cron API.

This module never accepts a caller-supplied URL or forwards a raw Hermes job
record. The phone receives only fields needed to manage a scheduled prompt.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp

from . import compat
from .contract import ErrorCode, HmpError

_JOB_ID = re.compile(r"[a-f0-9]{12}\Z")
_STATUS = re.compile(r"[a-z][a-z0-9_]{0,79}\Z")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z")
_MAX_JOBS = 100
_MAX_RESPONSE_BYTES = 1_048_576
_MAX_NAME_CHARS = 200
_MAX_SCHEDULE_CHARS = 200
_MAX_PROMPT_CHARS = 5_000
_TOTAL_TIMEOUT_S = 5
_LOOPBACK = frozenset({"127.0.0.1", "::1"})
_BUILDS_PATH = Path(__file__).with_name("mobile_cron_supported_builds.json")


def qualified_build(*, root: Path | None = None, builds_path: Path = _BUILDS_PATH) -> bool:
    """Evidence only: does this install match a tested jobs sample exactly? No gate reads this;
    jobs availability comes from `compat.evaluate_eligibility` (owner policy 2026-10-01)."""
    try:
        data = json.loads(builds_path.read_text(encoding="utf-8"))
        files = data["bridge_files"]
        entries = data["builds"]
        if data["format"] != 1 or not isinstance(files, list) or not isinstance(entries, list):
            return False
        safe_files = all(
            isinstance(p, str) and p and not Path(p).is_absolute()
            and ".." not in Path(p).parts for p in files
        )
        if not files or not safe_files:
            return False
        hermes_root = root if root is not None else compat.locate_hermes_root()
        if hermes_root is None:
            return False
        identity = compat.GitFingerprintReader(files).read(hermes_root)
        if identity is None:
            return False
        return any(
            isinstance(entry, Mapping)
            and entry.get("fingerprint") == identity.fingerprint
            and entry.get("git_sha") == identity.git_sha
            and isinstance(entry.get("qualified_by"), str)
            and bool(entry["qualified_by"])
            for entry in entries
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def job_id(value: str) -> str:
    if not isinstance(value, str) or _JOB_ID.fullmatch(value) is None:
        raise HmpError(ErrorCode.BAD_REQUEST)
    return value


def _text(body: Mapping[str, Any], key: str, limit: int) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise HmpError(ErrorCode.BAD_REQUEST)
    return value.strip()


def _options(body: Mapping[str, Any], *, editing: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "deliver" in body:
        if body["deliver"] not in ("local", "bot-chat"):
            raise HmpError(ErrorCode.BAD_REQUEST)
        result["deliver"] = body["deliver"]
    if "continuity" in body:
        if type(body["continuity"]) is not bool:
            raise HmpError(ErrorCode.BAD_REQUEST)
        result["continuity"] = body["continuity"]
    if "repeat" in body:
        floor = 0 if editing else 1
        if type(body["repeat"]) is not int or not floor <= body["repeat"] <= 9999:
            raise HmpError(ErrorCode.BAD_REQUEST)
        result["repeat"] = body["repeat"] or None
    return result


def create_body(body: Mapping[str, Any]) -> dict[str, Any]:
    if not {"name", "schedule", "prompt"} <= set(body) or not set(body) <= {
        "name", "schedule", "prompt", "deliver", "continuity", "repeat",
    }:
        raise HmpError(ErrorCode.BAD_REQUEST)
    return {
        "name": _text(body, "name", _MAX_NAME_CHARS),
        "schedule": _text(body, "schedule", _MAX_SCHEDULE_CHARS),
        "prompt": _text(body, "prompt", _MAX_PROMPT_CHARS),
        "deliver": "local",
        "continuity": False,
        **_options(body),
        "paused": True,
    }


def edit_body(body: Mapping[str, Any]) -> dict[str, Any]:
    if not body or not set(body) <= {
        "name", "schedule", "prompt", "deliver", "continuity", "repeat",
    }:
        raise HmpError(ErrorCode.BAD_REQUEST)
    limits = {
        "name": _MAX_NAME_CHARS,
        "schedule": _MAX_SCHEDULE_CHARS,
        "prompt": _MAX_PROMPT_CHARS,
    }
    return {
        **{key: _text(body, key, limits[key]) for key in body if key in limits},
        **_options(body, editing=True),
    }


def _optional_text(value: Any, limit: int) -> str | None:
    return value if isinstance(value, str) and len(value) <= limit else None


def _status(value: Any) -> str | None:
    return value if isinstance(value, str) and _STATUS.fullmatch(value) else None


def _time(value: Any) -> str | None:
    return value if isinstance(value, str) and len(value) <= 64 and _TIME.fullmatch(value) else None


def project_job(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    identifier = raw.get("id")
    if not isinstance(identifier, str) or _JOB_ID.fullmatch(identifier) is None:
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    name = _optional_text(raw.get("name"), _MAX_NAME_CHARS)
    prompt = _optional_text(raw.get("prompt"), _MAX_PROMPT_CHARS)
    schedule = _optional_text(raw.get("schedule_display"), _MAX_SCHEDULE_CHARS)
    enabled = raw.get("enabled")
    if name is None or prompt is None or schedule is None or type(enabled) is not bool:
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    deliver = raw.get("deliver", "local")
    # Never echo arbitrary platform destinations, chat IDs, or URLs to a phone.
    destination = deliver if deliver in ("local", "bot-chat") else "other"
    refs = raw.get("context_from")
    continuity = isinstance(refs, list) and "self" in refs
    repeat = raw.get("repeat")
    times = repeat.get("times") if isinstance(repeat, Mapping) else None
    if type(times) is not int or not 1 <= times <= 9999:
        times = None
    return {
        "id": identifier,
        "name": name,
        "prompt": prompt,
        "schedule": schedule,
        "enabled": enabled,
        "state": _status(raw.get("state")),
        "next_run_at": _time(raw.get("next_run_at")),
        "last_run_at": _time(raw.get("last_run_at")),
        "last_status": _status(raw.get("last_status")),
        "deliver": destination,
        "continuity": continuity,
        "repeat": times,
    }


def project_response(method: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    if method == "DELETE":
        if raw.get("ok") is not True:
            raise HmpError(ErrorCode.CRON_UNAVAILABLE)
        return {"deleted": True}
    if method == "GET":
        jobs = raw.get("jobs")
        if not isinstance(jobs, list) or len(jobs) > _MAX_JOBS:
            raise HmpError(ErrorCode.CRON_UNAVAILABLE)
        return {"jobs": [project_job(job) for job in jobs]}
    return {"job": project_job(raw.get("job"))}


async def call(
    endpoint: Any, *, method: str, job: str | None = None,
    action: str | None = None, body: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Make one bounded loopback request. Never retry an uncertain write."""
    host = getattr(endpoint, "host", None)
    port = getattr(endpoint, "port", None)
    key = getattr(endpoint, "api_key", None)
    prefix = getattr(endpoint, "path_prefix", None)
    if host not in _LOOPBACK or type(port) is not int or not 1 <= port <= 65_535:
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    if not isinstance(key, str) or not key or not isinstance(prefix, str):
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    if prefix and (not prefix.startswith("/p/") or "/" in prefix[3:]):
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    if method not in {"GET", "POST", "PATCH", "DELETE"}:
        raise HmpError(ErrorCode.BAD_REQUEST)
    path = f"{prefix}/api/jobs"
    if job is not None:
        path += "/" + quote(job_id(job), safe="")
    if action is not None:
        if action not in {"pause", "resume"} or job is None:
            raise HmpError(ErrorCode.BAD_REQUEST)
        path += "/" + action
    if method == "GET" and job is None:
        # Hermes excludes paused jobs by default. A create starts paused, so
        # recovery after an ambiguous response must still be able to find it.
        path += "?include_disabled=true"
    bracketed_host = f"[{host}]" if ":" in host else host
    url = f"http://{bracketed_host}:{port}{path}"
    timeout = aiohttp.ClientTimeout(
        total=_TOTAL_TIMEOUT_S, connect=0.5, sock_connect=0.5,
        sock_read=_TOTAL_TIMEOUT_S,
    )
    try:
        async with (
            aiohttp.ClientSession(trust_env=False, timeout=timeout) as session,
            session.request(
                method, url, json=body, allow_redirects=False,
                headers={"Authorization": f"Bearer {key}"},
            ) as response,
        ):
            if response.status == 400:
                raise HmpError(ErrorCode.BAD_REQUEST)
            if response.status == 404:
                raise HmpError(ErrorCode.NOT_FOUND)
            if response.status != 200:
                raise HmpError(ErrorCode.CRON_UNAVAILABLE)
            data = await response.content.read(_MAX_RESPONSE_BYTES + 1)
    except HmpError:
        raise
    except (aiohttp.ClientError, TimeoutError, OSError) as exc:
        raise HmpError(ErrorCode.CRON_UNAVAILABLE) from exc
    if len(data) > _MAX_RESPONSE_BYTES:
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    try:
        parsed = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HmpError(ErrorCode.CRON_UNAVAILABLE) from exc
    kind = "DELETE" if method == "DELETE" else "GET" if method == "GET" and job is None else "JOB"
    return project_response(kind, parsed)

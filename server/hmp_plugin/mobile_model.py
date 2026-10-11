"""Owner-only, bounded mobile view of Hermes's profile model picker."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import aiohttp

from . import compat
from .contract import ErrorCode, HmpError

_BUILDS_PATH = Path(__file__).with_name("mobile_model_supported_builds.json")
_PROVIDER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}\Z")
_MAX_RESPONSE_BYTES = 8_388_608
_MAX_PROVIDERS = 256
_MAX_MODELS = 10_000
_MAX_MODEL_CHARS = 240
_LOOPBACK = frozenset({"127.0.0.1", "::1"})


def qualified_build(*, root: Path | None = None, builds_path: Path = _BUILDS_PATH) -> bool:
    """Evidence only: does this install match a tested model sample exactly? No gate reads this;
    model availability comes from `compat.evaluate_eligibility` (owner policy 2026-10-01)."""
    try:
        data = json.loads(builds_path.read_text(encoding="utf-8"))
        files, entries = data["bridge_files"], data["builds"]
        if data["format"] != 1 or not isinstance(files, list) or not isinstance(entries, list):
            return False
        if not files or not all(
            isinstance(p, str) and p and not Path(p).is_absolute()
            and ".." not in Path(p).parts for p in files
        ):
            return False
        hermes_root = root if root is not None else compat.locate_hermes_root()
        if hermes_root is None:
            return False
        identity = compat.GitFingerprintReader(files).read(hermes_root)
        return identity is not None and any(
            isinstance(entry, Mapping)
            and entry.get("fingerprint") == identity.fingerprint
            and entry.get("git_sha") == identity.git_sha
            and isinstance(entry.get("qualified_by"), str)
            and bool(entry["qualified_by"])
            for entry in entries
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def selection(body: Mapping[str, Any]) -> tuple[str, str]:
    if set(body) != {"provider", "model"}:
        raise HmpError(ErrorCode.BAD_REQUEST)
    provider, model = body.get("provider"), body.get("model")
    if not isinstance(provider, str) or _PROVIDER.fullmatch(provider) is None:
        raise HmpError(ErrorCode.BAD_REQUEST)
    if not isinstance(model, str) or not model or len(model) > _MAX_MODEL_CHARS:
        raise HmpError(ErrorCode.BAD_REQUEST)
    if model != model.strip() or any(ord(char) < 32 or ord(char) == 127 for char in model):
        raise HmpError(ErrorCode.BAD_REQUEST)
    return provider, model


def _safe_label(value: Any, limit: int) -> str | None:
    if not isinstance(value, str) or not value or len(value) > limit:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    return value


def project_current(raw: Any) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    provider, model = raw.get("provider"), raw.get("model")
    if not isinstance(provider, str) or not isinstance(model, str):
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    if len(provider) > 120 or len(model) > _MAX_MODEL_CHARS:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    if provider and _PROVIDER.fullmatch(provider) is None:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    if model and _safe_label(model, _MAX_MODEL_CHARS) is None:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    return {"provider": provider, "model": model}


def project_options(raw: Any) -> dict[str, Any]:
    """Allowlist the picker shape; never forward credentials, URLs, or pricing blobs."""
    if not isinstance(raw, Mapping):
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    providers = raw.get("providers")
    if not isinstance(providers, list) or len(providers) > _MAX_PROVIDERS:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    projected: list[dict[str, Any]] = []
    total = 0
    for row in providers:
        if not isinstance(row, Mapping):
            raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
        # The upstream picker also lists unconfigured providers. A phone cannot
        # configure secrets, so show only profiles already connected on the host.
        if row.get("authenticated") is not True:
            continue
        slug = row.get("slug")
        name = _safe_label(row.get("name"), 120)
        models = row.get("models")
        if not isinstance(slug, str) or _PROVIDER.fullmatch(slug) is None:
            raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
        if not isinstance(models, list):
            raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
        total += len(models)
        if total > _MAX_MODELS:
            raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
        safe_models = [_safe_label(model, _MAX_MODEL_CHARS) for model in models]
        if any(model is None for model in safe_models):
            raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
        if safe_models:
            projected.append({"provider": slug, "name": name or slug, "models": safe_models})
    return {"providers": projected}


async def options(endpoint: Any) -> dict[str, Any]:
    """Query a fixed, profile-scoped loopback route with strict transport bounds."""
    host = getattr(endpoint, "host", None)
    port = getattr(endpoint, "port", None)
    key = getattr(endpoint, "api_key", None)
    prefix = getattr(endpoint, "path_prefix", None)
    if host not in _LOOPBACK or type(port) is not int or not 1 <= port <= 65_535:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    if not isinstance(key, str) or not key or not isinstance(prefix, str):
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    if prefix and (not prefix.startswith("/p/") or "/" in prefix[3:]):
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    host_literal = f"[{host}]" if ":" in host else host
    url = f"http://{host_literal}:{port}{prefix}/api/model/options?refresh=false"
    timeout = aiohttp.ClientTimeout(total=15, connect=0.5, sock_connect=0.5, sock_read=15)
    try:
        async with (
            aiohttp.ClientSession(trust_env=False, timeout=timeout) as session,
            session.get(
                url, allow_redirects=False,
                headers={"Authorization": f"Bearer {key}"},
            ) as response,
        ):
            if response.status != 200:
                raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
            data = await response.content.read(_MAX_RESPONSE_BYTES + 1)
    except HmpError:
        raise
    except (aiohttp.ClientError, TimeoutError, OSError) as exc:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE) from exc
    if len(data) > _MAX_RESPONSE_BYTES:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    try:
        return project_options(json.loads(data))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE) from exc

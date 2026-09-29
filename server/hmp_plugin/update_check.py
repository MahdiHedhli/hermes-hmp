"""Read-only, advisory check for reviewed HMP releases.

Only fixed GitHub API endpoints are contacted. Release code is never fetched or
executed, and a candidate is never installed by this module. All remote data is
bounded and treated as untrusted. Importing this module performs no I/O.
"""

from __future__ import annotations

import base64
import json
import re
import stat
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from . import compat

API = "https://api.github.com/repos/MahdiHedhli/hermes-hmp"
MAX_RESPONSE = 512_000
TAG_RE = re.compile(r"v[0-9][A-Za-z0-9._-]{0,63}\Z")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
MANIFESTS = {
    "read bridge": "read_compat_builds.json",
    "direct send": "direct_send_supported_builds.json",
    "scheduled jobs": "mobile_cron_supported_builds.json",
    "default model": "mobile_model_supported_builds.json",
}


class UpdateCheckError(Exception):
    """Safe operator-facing failure with no remote response text or local paths."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, url: str
    ) -> Any:
        raise UpdateCheckError("GitHub redirected the update request")


def fetch_json(path: str) -> dict[str, Any]:
    """Bounded unauthenticated JSON GET against the fixed GitHub API origin."""
    pathname = path.partition("?")[0]
    segments = pathname.lstrip("/").split("/")
    if (
        not path.startswith("/")
        or path.startswith("//")
        or any(segment in ("", ".", "..") for segment in segments)
        or not re.fullmatch(r"/[A-Za-z0-9_./?=&%-]+", path)
    ):
        raise UpdateCheckError("invalid update request")
    # API is a fixed https://api.github.com origin; path is locally constructed and validated.
    request = urllib.request.Request(  # noqa: S310
        API + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "hermes-hmp-update-check"},
    )
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=5) as response:
            content = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as exc:
        raise UpdateCheckError("GitHub release metadata unavailable", status=exc.code) from None
    except (OSError, TimeoutError) as exc:
        raise UpdateCheckError("GitHub release metadata unavailable") from exc
    if len(content) > MAX_RESPONSE:
        raise UpdateCheckError("GitHub release metadata exceeds size limit")
    try:
        value = json.loads(content)
    except (ValueError, UnicodeError) as exc:
        raise UpdateCheckError("invalid GitHub release metadata") from exc
    if not isinstance(value, dict):
        raise UpdateCheckError("invalid GitHub release metadata")
    return value


def _sha(value: object) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise UpdateCheckError("invalid release commit identity")
    return value


def _release_commit(tag: str, get: Callable[[str], dict[str, Any]]) -> str:
    obj = get(f"/git/ref/tags/{tag}").get("object")
    for _ in range(3):
        if not isinstance(obj, dict):
            break
        sha = _sha(obj.get("sha"))
        if obj.get("type") == "commit":
            return sha
        if obj.get("type") != "tag":
            break
        obj = get(f"/git/tags/{sha}").get("object")
    raise UpdateCheckError("release tag does not resolve to a commit")


def _manifest(raw: dict[str, Any]) -> compat.ReadCompatList:
    """Parse only bounded bridge paths; never let release data name arbitrary host files."""
    content = raw.get("content")
    if (
        raw.get("encoding") != "base64"
        or not isinstance(content, str)
        or len(content) > MAX_RESPONSE * 2
    ):
        raise UpdateCheckError("invalid release compatibility metadata")
    try:
        decoded = base64.b64decode("".join(content.split()), validate=True)
        if len(decoded) > MAX_RESPONSE:
            raise ValueError("oversize")
        data = json.loads(decoded)
        files = data["bridge_files"]
        builds = data["builds"]
        if data.get("format") != 1 or not isinstance(files, list) or not isinstance(builds, list):
            raise ValueError("shape")
        if not 1 <= len(files) <= 64 or len(builds) > 256:
            raise ValueError("count")
        root = PurePosixPath(".")
        for item in files:
            if (
                not isinstance(item, str)
                or len(item) > 160
                or re.fullmatch(r"[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*\.py", item) is None
            ):
                raise ValueError("path")
            path = PurePosixPath(item)
            if (
                path.is_absolute()
                or path == root
                or any(part in (".", "..") for part in item.split("/"))
            ):
                raise ValueError("path")
        entries = tuple(
            compat.BuildEntry(
                fingerprint=item["fingerprint"],
                git_sha=item.get("git_sha"),
                label=item["label"],
                qualified_by=item["qualified_by"],
                qualified_at=item["qualified_at"],
                source_sha=item.get("source_sha"),
            )
            for item in builds
        )
    except (ValueError, TypeError, KeyError, AttributeError, base64.binascii.Error) as exc:
        raise UpdateCheckError("invalid release compatibility metadata") from exc
    return compat.ReadCompatList(format=1, bridge_files=tuple(files), builds=entries)


def _feature_status(manifest: compat.ReadCompatList, hermes_root: Path | None) -> str:
    if hermes_root is None:
        return "unknown (Hermes source unavailable)"
    root = hermes_root.resolve()
    total_size = 0
    for rel in manifest.bridge_files:
        try:
            path = (root / rel).resolve()
            if not path.is_relative_to(root):
                return "unknown (unsafe bridge path)"
            meta = path.stat()
            if not stat.S_ISREG(meta.st_mode) or meta.st_size > 2_000_000:
                return "unknown (bridge file unavailable)"
            total_size += meta.st_size
            if total_size > 16_000_000:
                return "unknown (bridge files exceed size limit)"
        except (OSError, ValueError):
            return "unknown (bridge path unavailable)"
    identity = compat.GitFingerprintReader(manifest.bridge_files).read(root)
    if identity is None:
        return "unknown (build unidentifiable)"
    return (
        "listed (runtime check still required)"
        if compat.match_build(identity, manifest.builds) is not None
        else "unsupported (not listed for this exact build)"
    )


@dataclass(frozen=True)
class UpdateResult:
    installed_sha: str | None
    release_sha: str | None
    tag: str | None
    pin_status: str
    hermes_sha: str | None
    compatibility: dict[str, str]


def check_update(
    *,
    get: Callable[[str], dict[str, Any]] = fetch_json,
    plugin_root: Path | None = None,
    hermes_root: Path | None = None,
) -> UpdateResult:
    """Compare immutable release commit to local pin, without changing any state."""
    plugin_root = plugin_root or Path(__file__).resolve().parents[2]
    try:
        installed = compat.resolve_git_head_sha(plugin_root)
    except (OSError, ValueError):
        installed = None
    try:
        release = get("/releases/latest")
    except UpdateCheckError as exc:
        if exc.status == 404:
            return UpdateResult(installed, None, None, "no release", None, {})
        raise
    tag = release.get("tag_name")
    if not isinstance(tag, str) or TAG_RE.fullmatch(tag) is None:
        raise UpdateCheckError("invalid release tag")
    release_sha = _release_commit(tag, get)
    if hermes_root is None:
        hermes_root = compat.locate_hermes_root()
    try:
        hermes_sha = compat.resolve_git_head_sha(hermes_root) if hermes_root else None
    except (OSError, ValueError):
        hermes_sha = None
    if installed == release_sha:
        pin_status = "current release"
    elif installed is None:
        pin_status = "unknown (installed pin unavailable)"
    else:
        try:
            comparison = get(f"/compare/{installed}...{release_sha}")
            pin_status = {
                "ahead": "newer release available",
                "behind": "installed pin is ahead of latest release",
                "identical": "current release",
                "diverged": "installed pin diverged from latest release",
            }.get(comparison.get("status"), "unknown (comparison unavailable)")
        except UpdateCheckError:
            pin_status = "unknown (comparison unavailable)"
    compatibility: dict[str, str] = {}
    for feature, filename in MANIFESTS.items():
        try:
            raw = get(f"/contents/server/hmp_plugin/{filename}?ref={release_sha}")
            compatibility[feature] = _feature_status(_manifest(raw), hermes_root)
        except UpdateCheckError:
            compatibility[feature] = "unknown (release metadata unavailable)"
    return UpdateResult(installed, release_sha, tag, pin_status, hermes_sha, compatibility)

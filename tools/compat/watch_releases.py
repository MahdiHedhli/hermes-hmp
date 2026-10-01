#!/usr/bin/env python3
"""Inventory upstream Hermes releases against HMP's reviewed bridge surface.

This is a source audit, not a compatibility grant. The scheduled workflow also runs the
real fixture matrix on the newest release in an isolated runner. A newly published tag
requires review even when its fingerprint happens to match a known build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPAT = ROOT / "server" / "hmp_plugin" / "read_compat_builds.json"
RELEASES_URL = "https://api.github.com/repos/NousResearch/hermes-agent/releases?per_page=100&page={}"
REMOTE_URL = "https://github.com/NousResearch/hermes-agent.git"
BASELINE_TAG = "v2026.8.31"
REVIEWED_TAGS = {
    "v2026.8.31": "29112bef099274229cadff79cdff7bf7b99c4b77",
    "v2026.9.7": "2237be355906fbe6065ce1815711eee52b2d646e",
    "v2026.9.11": "939e45c91d751fadd94dcd1b873ac3cb44846213",
    "v2026.9.14": "345cd2b057a452236de401d3534b8502a7465e8d",
    "v2026.9.21": "d337b736aa1e8ebecfab043842d13e4a2d2f48a3",
    "v2026.9.24": "f97608f178d1ffeca59860195ab7da295f7c8e5f",
}
SAFE_TAG = re.compile(r"v[0-9A-Za-z][0-9A-Za-z._-]{0,79}\Z")


def get_releases() -> list[dict]:
    releases: list[dict] = []
    for page in range(1, 11):
        req = urllib.request.Request(  # noqa: S310 -- fixed HTTPS GitHub API origin
            RELEASES_URL.format(page),
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "hermes-hmp-release-watch",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("GitHub releases API did not return a list")
        releases.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError("release pagination exceeded ten pages; refusing an incomplete audit")
    return releases


def git(repo: Path, *args: str, allow_missing: bool = False) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False,
    )
    if result.returncode != 0:
        if allow_missing:
            return None
        raise RuntimeError(f"git {args[0]} failed ({result.returncode})")
    return result.stdout


def inspect_tag(repo: Path, tag: str, bridge_files: list[str], builds: list[dict]) -> dict:
    if SAFE_TAG.fullmatch(tag) is None:
        return {"tag": tag, "status": "invalid_tag"}
    sha_bytes = git(
        repo, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}", allow_missing=True,
    )
    if sha_bytes is None:
        return {"tag": tag, "status": "tag_not_fetched"}
    sha = sha_bytes.decode("ascii").strip()
    digest = hashlib.sha256()
    missing: list[str] = []
    for rel in sorted(bridge_files):
        data = git(repo, "show", f"{sha}:{rel}", allow_missing=True)
        if data is None:
            missing.append(rel)
            continue
        digest.update(rel.encode("utf-8") + b"\0" + str(len(data)).encode("ascii") + b"\0" + data)
    if missing:
        return {"tag": tag, "sha": sha, "status": "bridge_files_missing", "missing": missing}
    fingerprint = digest.hexdigest()
    matching = [b for b in builds if b["fingerprint"] == fingerprint]
    exact = any(b.get("git_sha") == sha for b in matching)
    status = (
        "listed_exact_git" if exact else
        "listed_fingerprint_only" if matching else "unlisted_fingerprint"
    )
    return {"tag": tag, "sha": sha, "fingerprint": fingerprint, "status": status}


def inspect_ref(repo: Path, tag: str) -> dict:
    """Cheap inventory path: no Hermes blobs are downloaded or executed."""
    if SAFE_TAG.fullmatch(tag) is None:
        return {"tag": tag, "status": "invalid_tag"}
    sha_bytes = git(
        repo, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}", allow_missing=True,
    )
    if sha_bytes is None:
        return {"tag": tag, "status": "tag_not_fetched"}
    sha = sha_bytes.decode("ascii").strip()
    expected = REVIEWED_TAGS.get(tag)
    status = "retagged" if expected and expected != sha else (
        "reviewed_tag" if expected else "new_release"
    )
    return {"tag": tag, "sha": sha, "status": status}


def remote_tag_shas(remote: str = REMOTE_URL) -> dict[str, str]:
    """Resolve lightweight and annotated tags in one read-only remote request."""
    proc = subprocess.run(
        ["git", "ls-remote", "--tags", remote], capture_output=True, text=True, check=False,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError("cannot read public Hermes tag refs")
    direct: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if re.fullmatch(r"[0-9a-f]{40}", sha) is None or not ref.startswith("refs/tags/"):
            continue
        tag = ref[len("refs/tags/"):]
        if tag.endswith("^{}"):
            peeled[tag[:-3]] = sha
        else:
            direct[tag] = sha
    return direct | peeled


def inspect_remote_ref(refs: dict[str, str], tag: str) -> dict:
    if SAFE_TAG.fullmatch(tag) is None:
        return {"tag": tag, "status": "invalid_tag"}
    sha = refs.get(tag)
    if sha is None:
        return {"tag": tag, "status": "tag_not_fetched"}
    expected = REVIEWED_TAGS.get(tag)
    status = "retagged" if expected and expected != sha else (
        "reviewed_tag" if expected else "new_release"
    )
    return {"tag": tag, "sha": sha, "status": status}


def select_releases(releases: list[dict]) -> list[dict]:
    by_tag = {
        r.get("tag_name"): r for r in releases
        if isinstance(r, dict) and r.get("published_at")
    }
    baseline = by_tag.get(BASELINE_TAG)
    if baseline is None:
        raise ValueError(f"baseline release {BASELINE_TAG} is missing from GitHub API response")
    selected = [r for r in by_tag.values() if r["published_at"] >= baseline["published_at"]]
    return sorted(selected, key=lambda r: (r["published_at"], r["tag_name"]))


def build_report(
    repo: Path | None, releases: list[dict], *, source_audit: bool = True,
    refs: dict[str, str] | None = None,
) -> dict:
    selected = select_releases(releases)
    compat = json.loads(COMPAT.read_text(encoding="utf-8"))
    results = []
    for release in selected:
        tag = release["tag_name"]
        if source_audit:
            if repo is None:
                raise ValueError("source audit requires a local clone")
            item = inspect_tag(repo, tag, compat["bridge_files"], compat["builds"])
        elif refs is not None:
            item = inspect_remote_ref(refs, tag)
        else:
            if repo is None:
                raise ValueError("inventory requires a local clone or remote refs")
            item = inspect_ref(repo, tag)
        item["reviewed_tag"] = tag in REVIEWED_TAGS and item["status"] != "retagged"
        results.append(item)
    return {
        "format": 1,
        "baseline": BASELINE_TAG,
        "latest_tag": selected[-1]["tag_name"],
        "releases": results,
        "unreviewed_tags": [r["tag"] for r in results if not r["reviewed_tag"]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--releases-json", type=Path, help="offline release fixture")
    parser.add_argument(
        "--inventory-only", action="store_true",
        help="check tag identities without fetching source blobs (the fixture matrix follows)",
    )
    parser.add_argument(
        "--check", action="store_true", help="fail for unreviewed or unfetched tags",
    )
    args = parser.parse_args(argv)
    if args.source_repo is not None and not (args.source_repo / ".git").exists():
        parser.error("--source-repo must be a local Git clone")
    if not args.inventory_only and args.source_repo is None:
        parser.error("a full source audit requires --source-repo")
    releases = json.loads(args.releases_json.read_text()) if args.releases_json else get_releases()
    refs = remote_tag_shas() if args.inventory_only and args.source_repo is None else None
    report = build_report(
        args.source_repo, releases, source_audit=not args.inventory_only, refs=refs,
    )
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in report["releases"]:
        print(f"{item['tag']}: {item['status']}" + (" (new)" if not item["reviewed_tag"] else ""))
    if args.check and (
        report["unreviewed_tags"]
        or any(r["status"] in ("invalid_tag", "tag_not_fetched", "retagged")
               for r in report["releases"])
    ):
        print("Release review required; see the report and fixture matrix.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

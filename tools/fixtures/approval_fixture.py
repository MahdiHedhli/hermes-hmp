#!/usr/bin/env python3
"""Fixture-only approval qualification receipts (specs/005-approval-process-matrix).

Everything here writes ONLY into a disposable fixture plugin copy (`<out>/_hmp_plugin`) or a
scratch copy of an extracted Hermes build. The committed `approval_supported_builds.json` is
never touched, and the plugin runtime never reads any variable or file this module defines: the
runtime only sees the manifest file in the copy it was loaded from.

A guarded-send (direct-send) receipt never reaches this module: the two lanes have separate
installers, separate environment knobs and separate manifest files.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import _fixture_common as fc  # noqa: E402

if str(fc.SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(fc.SERVER_DIR))

from hmp_plugin import compat  # noqa: E402

APPROVAL_MANIFEST = "approval_supported_builds.json"
# Fixture tooling only (`direct_send_fixture.build_offline`). No plugin module reads it.
RECEIPT_ENV = "HMP_APPROVAL_QUALIFICATION"
RECEIPT_KIND = "approval-fixture-qualification"
# The git-install matrix mode (specs/005 amendment 2). A separate kind so an archive receipt can
# never stand in for a git one, or the reverse. Fixture tooling only; no plugin module reads it.
RECEIPT_KIND_GIT = "approval-fixture-qualification-git"
RECEIPT_KINDS = (RECEIPT_KIND, RECEIPT_KIND_GIT)
PROVISIONAL = "provisional"
REQUIRED_STAGES = (
    "identity", "boundary", "behavior", "integration", "reconnect", "timing", "stability",
)
# An approval-only Hermes file: in the approval list but outside BOTH the read and the direct-send
# fingerprints, so a swap can only move the approval lane. The in-place swap test appends an inert
# comment to it inside a scratch copy.
SWAP_FILE = "tools/approval_prompt.py"
_PLUGIN_SUFFIXES = frozenset({".py", ".json", ".yaml"})
DIRECT_MANIFEST = "direct_send_supported_builds.json"
SHA40_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
# Labels the integration fixtures already use for their default builds (the test module's BUILDS
# tuple plus everything in tools/hermes_builds/builds.yaml). A matrix label may not collide with
# one: pytest would emit duplicate or suffixed parameter IDs.
_FIXTURE_DEFAULT_LABELS = ("stock-base", "experimental", "owner-local")

# Required tests as (module, function, parameter template). `{label}` is the build label. The
# JUnit report must contain exactly this set, all passed, none skipped. Shared by the runner, the
# final-receipt validator and the tests so none of them can drift from another.
_DIRECT_SEND = "test_direct_send_fixture"
_APPROVALS = "test_approvals_fixture"
_LIFECYCLE = "test_approval_process_lifecycle"
CLOSED_REASONS = ("owner", "flag", "direct-send-list", "approval-list")
RECONNECT_SCENARIOS = ("closed_start_stays_closed", "admitted_start_close_and_restore")
REQUIRED_TESTS: tuple[tuple[str, str, str], ...] = (
    *((_DIRECT_SEND, name, "{label}") for name in (
        "test_send_reply_visible_via_ses2",
        "test_duplicate_cmid_never_runs_a_second_turn",
        "test_stale_head_refused_before_any_loopback_call",
        "test_no_bot_chat_on_a_profile_with_none",
        "test_session_busy_via_synthetic_lease",
        "test_flag_off_is_503",
        "test_non_loopback_bind_configured_closes_the_gate",
        "test_timeout_then_lookup_reaches_accepted_without_a_resend",
    )),
    *((_APPROVALS, name, "{label}") for name in (
        "test_t7_local_run_approval_unblocks_and_clarify_and_execute_code_do_not_card",
        "test_t7_desktop_held_has_no_phone_card",
        "test_t7_replay_does_not_open_a_second_stream",
        "test_t7_bot_chat_exact_id_deny_blocks_command",
        "test_t7_real_timeout_expires_wait_without_running_command",
        "test_t8_phone_approval_clarify_and_unknown_id",
        "test_t8_restart_mid_wait_does_not_apply",
        "test_t8_cross_profile_exact_id_answer_is_refused",
        "test_t8_phone_text_and_slash_never_resolve_pending_approval",
    )),
    *((_APPROVALS, "test_approvals_fixture_fails_closed", "{label}-" + why)
      for why in CLOSED_REASONS),
    *((_LIFECYCLE, name, "{label}") for name in (
        "test_direct_send_receipt_never_opens_approvals",
        "test_empty_start_stays_closed_until_full_restart",
        "test_admitted_start_entry_removal_closes_and_restore_reopens",
        "test_in_place_swap_stays_closed_until_full_restart",
    )),
    *((_LIFECYCLE, "test_listener_reconnect_never_reopens_a_closed_baseline", "{label}-" + s)
      for s in RECONNECT_SCENARIOS),
)

# Exact, ordered `open` value of every reconnect-harness step (approval_reconnect_harness.py).
RECONNECT_EXPECTED: dict[str, tuple[tuple[str, bool], ...]] = {
    "closed_start_stays_closed": (
        ("connect-empty-manifest", False),
        ("first-callback-after-entry-installed", False),
        ("reconnect-with-entry", False),
        ("reconnect-empty-again", False),
        ("reconnect-entry-restored", False),
    ),
    "admitted_start_close_and_restore": (
        ("connect-with-entry", True),
        ("callback-again-cached-probe", True),
        ("first-callback-after-removal", False),
        ("reconnect-empty-manifest", False),
        ("reconnect-wrong-fingerprint", False),
        ("first-callback-wrong-fingerprint", False),
        ("reconnect-same-entry-restored", True),
        ("first-callback-after-restore", True),
    ),
}


def required_ids(label: str) -> list[tuple[str, str]]:
    """(module, test id with parameter) for every required test of this build label."""
    return [(module, f"{name}[{param.format(label=label)}]")
            for module, name, param in REQUIRED_TESTS]


def required_test_names(label: str) -> list[str]:
    """The exact ordered `module::test[param]` list a final receipt must carry."""
    return [f"{module}::{test}" for module, test in required_ids(label)]


def default_build_labels() -> frozenset[str]:
    """Labels the default fixture builds already use. Fails closed if builds.yaml is unreadable."""
    labels = set(_FIXTURE_DEFAULT_LABELS)
    try:
        import yaml

        data = yaml.safe_load(fc.BUILDS_YAML.read_text(encoding="utf-8"))
        labels.update(str(b["label"]) for b in data["builds"])
    except (ImportError, OSError, KeyError, TypeError, ValueError) as exc:
        raise _refuse("cannot read the default fixture build labels (builds.yaml)") from exc
    return frozenset(labels)


def _refuse(message: str) -> fc.FixtureSafetyError:
    return fc.FixtureSafetyError(message)


# --------------------------------------------------------------------------------------------
# Git-install fixtures (amendment 2): an isolated, independent clone with its own `.git`.
# --------------------------------------------------------------------------------------------

# A config section that could point a clone back at another repository or pull in other config.
_GIT_CONFIG_HAZARD = re.compile(
    r"^\s*\[\s*(remote|include|includeif|url)\b", re.IGNORECASE | re.MULTILINE)
# Identity metadata compared before and after a copy. `index`, logs and locks legitimately move.
_GIT_IDENTITY_FILES = ("HEAD", "packed-refs", "config")


def build_git_head(src: Path) -> str | None:
    """The full 40-hex HEAD of `src` exactly as the runtime reads it (file reads only), or None
    when `src` has no `.git` (an extracted archive). A `.git` that cannot be resolved refuses:
    it is never treated as "no git"."""
    try:
        return compat.resolve_git_head_sha(src)
    except (OSError, ValueError) as exc:
        raise _refuse(f"the .git of {src} is present but has no resolvable HEAD") from exc


def assert_git_fixture_clone(src: Path, *, original: Path | None = None) -> str:
    """Refuse a `.git` that is not its own independent repository. Returns the HEAD SHA.

    Independent means a real directory (never a link or a `gitdir:` pointer file), holding no
    symlink at all, no alternates or commondir (objects are not borrowed), no hard-linked file (a
    `git clone --local` shares inodes with its source), no remote, include or url section in its
    config (nothing for a push or fetch to reach), and, when `original` is given, no resolution into
    the original. Reads only; nothing is written.
    """
    git = Path(src) / ".git"
    if git.is_symlink() or not git.is_dir():
        raise _refuse(f"{git} must be a real .git directory of its own (missing, link or pointer)")
    root = git.resolve()
    source = Path(original).resolve() if original is not None else None
    if source is not None and (root.is_relative_to(source) or source.is_relative_to(root)):
        raise _refuse("the fixture .git resolves into the original source; refusing")
    for name in ("objects/info/alternates", "commondir"):
        if (git / name).exists() or (git / name).is_symlink():
            raise _refuse(f"the fixture .git borrows from another repository ({name})")
    for current, dirs, files in os.walk(git, followlinks=False):
        for name in (*dirs, *files):
            path = Path(current, name)
            if path.is_symlink():
                raise _refuse(f"the fixture .git contains a symlink: {path}")
            if path.is_file() and path.stat().st_nlink > 1:
                raise _refuse(
                    f"the fixture .git shares a hard-linked file with another tree: {path} "
                    "(clone with --no-local)")
    config = git / "config"
    text = config.read_text(encoding="utf-8", errors="replace") if config.is_file() else ""
    if _GIT_CONFIG_HAZARD.search(text):
        raise _refuse("the fixture .git config names a remote, include or url (remove it)")
    head = build_git_head(Path(src))
    if head is None or not SHA40_RE.fullmatch(head):
        raise _refuse("the fixture .git HEAD is not a full 40-hex commit")
    return head


def independent_git_head(src: Path) -> str | None:
    """The HEAD of `src` for binding into an entry: None for an archive (no `.git` at all), else
    only after `assert_git_fixture_clone`, so a linked worktree, pointer file or borrowed object
    store can never lend its HEAD. A dangling `.git` link is refused, not read as an archive."""
    git = Path(src) / ".git"
    if not (git.exists() or git.is_symlink()):
        return None
    return assert_git_fixture_clone(Path(src))


def git_identity_digest(src: Path) -> str:
    """SHA-256 over the clone's identity metadata: HEAD, packed-refs, config, every loose ref, and
    the object file listing (path and size). Never the index, logs or locks, which legitimately
    change. Two copies of one fixture have equal digests."""
    git = Path(src) / ".git"
    digest = hashlib.sha256()
    names = [git / n for n in _GIT_IDENTITY_FILES]
    if (git / "refs").is_dir():
        names += sorted(p for p in (git / "refs").rglob("*") if p.is_file())
    for path in names:
        rel = path.relative_to(git).as_posix().encode("utf-8")
        data = path.read_bytes() if path.is_file() else b"\0absent"
        digest.update(rel + b"\0" + str(len(data)).encode("ascii") + b"\0" + data)
    objects = git / "objects"
    listing = sorted(
        (p.relative_to(git).as_posix(), p.stat().st_size) for p in objects.rglob("*") if p.is_file()
    ) if objects.is_dir() else []
    for rel, size in listing:
        digest.update(f"{rel}\0{size}\0".encode())
    return digest.hexdigest()


def plugin_source_digest(plugin_dir: Path | None = None) -> str:
    """SHA-256 over the plugin's source and manifests (relative path, length, bytes), so a final
    receipt goes stale when the plugin under test changes."""
    root = (plugin_dir or fc.SERVER_DIR / "hmp_plugin").resolve()
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix not in _PLUGIN_SUFFIXES or "__pycache__" in path.parts:
            continue
        data = path.read_bytes()
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0" + str(len(data)).encode("ascii") + b"\0")
        digest.update(data)
    return digest.hexdigest()


def approval_fingerprint(src: Path, files: Sequence[str]) -> str | None:
    return compat.compute_read_bridge_fingerprint(src, files)


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _refuse(f"approval receipt absent or malformed: {path.name}") from exc
    if not isinstance(raw, dict):
        raise _refuse(f"approval receipt is malformed: {path.name}")
    return raw


def _lane_files(
    plugin_dir: Path | None, name: str, explicit: Sequence[str] | None
) -> list[str]:
    """A lane's ordered files: the caller's own, else the plugin copy's (or tracked) manifest."""
    if explicit is not None:
        return list(explicit)
    path = (plugin_dir or fc.SERVER_DIR / "hmp_plugin") / name
    try:
        files = json.loads(path.read_text(encoding="utf-8"))["bridge_files"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _refuse(f"cannot read the {name} boundary to recheck the receipt") from exc
    if not isinstance(files, list) or not files or not all(isinstance(f, str) for f in files):
        raise _refuse(f"the {name} boundary is malformed")
    return files


def _validate_evidence(
    evidence: object, entry: compat.BuildEntry, build: fc.BuildInfo, fingerprint: str,
    plugin_dir: Path | None, read_files: Sequence[str] | None,
    direct_files: Sequence[str] | None, head: str | None = None,
) -> None:
    """Accidental-staleness checks on a FINAL receipt. A JSON file cannot authenticate that the
    tests ran: this is trusted local evidence, not tamper-proof certification. `head` is the
    build's resolved git HEAD (None for an extracted archive): the evidence kind must be the one
    for that source, so an archive receipt never qualifies a git install or the reverse."""
    expected_kind = RECEIPT_KIND if head is None else RECEIPT_KIND_GIT
    if not isinstance(evidence, dict) or evidence.get("kind") not in RECEIPT_KINDS:
        raise _refuse("approval receipt evidence is missing or malformed")
    if evidence.get("kind") != expected_kind:
        source = "an archive" if head is None else "a git"
        raise _refuse(
            f"approval receipt kind {evidence.get('kind')} does not match {source} build")
    if head is None:
        if evidence.get("git_sha") is not None:
            raise _refuse("an archive approval receipt must not carry a git_sha")
    elif evidence.get("git_sha") != head or evidence.get("git_sha") != entry.git_sha:
        raise _refuse("approval receipt git_sha differs from the build's git HEAD")
    stages = evidence.get("stages")
    if (
        evidence.get("complete") is not True
        or not isinstance(stages, dict)
        or set(stages) != set(REQUIRED_STAGES)
        or not all(value is True for value in stages.values())
    ):
        raise _refuse("approval receipt is incomplete: every required stage must have passed")
    if evidence.get("label") != build.label or evidence.get("approval_fingerprint") != fingerprint:
        raise _refuse("approval receipt evidence belongs to another build (cross-build)")
    source_sha = evidence.get("source_sha")
    if (
        not isinstance(source_sha, str) or not SHA40_RE.fullmatch(source_sha)
        or source_sha != entry.source_sha
    ):
        raise _refuse("approval receipt source_sha is missing, malformed or differs from the entry")
    if evidence.get("upstream_verified") is not True:
        raise _refuse("a final approval receipt needs an upstream-verified source identity")
    if evidence.get("required_tests") != required_test_names(build.label):
        raise _refuse("approval receipt required_tests is not the exact required ordered set")
    junit = evidence.get("junit_sha256")
    if not isinstance(junit, str) or not SHA256_RE.fullmatch(junit):
        raise _refuse("approval receipt carries no valid JUnit digest")
    if evidence.get("plugin_sha256") != plugin_source_digest(plugin_dir):
        raise _refuse("approval receipt is stale: the plugin source changed since it was issued")
    for key, name, explicit in (
        ("read_fingerprint", compat.READ_COMPAT_FILE, read_files),
        ("direct_send_fingerprint", DIRECT_MANIFEST, direct_files),
    ):
        current = compat.compute_read_bridge_fingerprint(
            build.src_dir, _lane_files(plugin_dir, name, explicit))
        if current is None or evidence.get(key) != current:
            raise _refuse(f"approval receipt is stale: the {key} differs")


def validate_approval_receipt(
    receipt: Path,
    build: fc.BuildInfo,
    *,
    target_files: Sequence[str],
    final: bool | None = None,
    plugin_dir: Path | None = None,
    read_files: Sequence[str] | None = None,
    direct_files: Sequence[str] | None = None,
) -> dict[str, Any]:
    """The receipt's single build entry, or `FixtureSafetyError`.

    Rejects an absent, malformed, wrong-schema, wrong-boundary, cross-build or stale receipt.
    `final=None` treats a receipt carrying `evidence` as final and any other as provisional.
    The schema is the runtime parser's own, never a weaker copy of it. A final receipt is also
    rechecked against the CURRENT read and direct-send boundaries (the plugin's own manifests
    unless the caller passes the lists) for every consumer. This catches stale or accidental
    receipts only; it is not authentication and grants no runtime admission.
    """
    raw = _load_json_object(receipt)
    try:
        parsed = compat.load_read_compat_list(receipt)
    except (TypeError, ValueError) as exc:
        raise _refuse("invalid approval fixture qualification schema") from exc
    if list(parsed.bridge_files) != list(target_files):
        raise _refuse("approval qualification file boundary differs from the target manifest")
    if len(parsed.builds) != 1:
        raise _refuse("approval receipt must carry exactly one build (cross-build refused)")
    entry = parsed.builds[0]
    if entry.label != build.label:
        raise _refuse("approval receipt is for another build label (cross-build)")
    fingerprint = compat.compute_read_bridge_fingerprint(build.src_dir, target_files)
    if fingerprint is None or entry.fingerprint != fingerprint:
        raise _refuse("no exact approval fixture qualification for this build (stale source)")
    # The runtime matches a git install only to an entry with the same git_sha, and an install
    # without git only to a fingerprint-only one. Require exactly that here, so a mismatched
    # archive/git receipt is refused instead of installing an entry the gate would never match.
    git_path = build.src_dir / ".git"
    if git_path.exists() or git_path.is_symlink():
        head: str | None = assert_git_fixture_clone(build.src_dir)
        if entry.git_sha != head or entry.source_sha != head:
            raise _refuse("git receipt git_sha and source_sha must both equal the build's git HEAD")
    else:
        head = None
        if entry.git_sha is not None:
            raise _refuse("a git receipt cannot qualify a build with no .git (git_sha is set)")
    evidence = raw.get("evidence")
    is_final = (evidence is not None) if final is None else final
    if is_final:
        if PROVISIONAL in entry.qualified_by:
            raise _refuse("a final approval receipt cannot carry provisional provenance")
        _validate_evidence(
            evidence, entry, build, fingerprint, plugin_dir, read_files, direct_files, head
        )
    elif PROVISIONAL not in entry.qualified_by:
        raise _refuse("a provisional approval receipt must say so in qualified_by")
    return dict(raw["builds"][0])


def approval_manifest_path(out: Path) -> Path:
    root = Path(out).resolve()
    target = root / "_hmp_plugin" / APPROVAL_MANIFEST
    if not target.resolve().is_relative_to(root):
        raise fc.FixtureSafetyError("approval manifest destination escaped the fixture copy")
    return target


def _read_target(out: Path) -> tuple[Path, dict[str, Any]]:
    fc.assert_outside_real_home(out, "approval fixture destination")
    target = approval_manifest_path(out)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _refuse("approval manifest is absent or malformed in the fixture copy") from exc
    files = data.get("bridge_files") if isinstance(data, dict) else None
    if not isinstance(files, list) or not files or not all(isinstance(f, str) for f in files):
        raise _refuse("fixture approval manifest has no usable bridge_files boundary")
    return target, data


def _write(target: Path, data: dict[str, Any]) -> None:
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def install_approval_fixture_entry(
    build: fc.BuildInfo,
    out: Path,
    receipt: Path,
    *,
    final: bool | None = None,
    plugin_dir: Path | None = None,
    read_files: Sequence[str] | None = None,
    direct_files: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Write the receipt's entry into the fixture copy's OWN approval manifest, after exact
    validation against that manifest's ordered file list and this build's current bytes."""
    target, data = _read_target(out)
    entry = validate_approval_receipt(
        receipt, build, target_files=data["bridge_files"], final=final,
        plugin_dir=plugin_dir, read_files=read_files, direct_files=direct_files,
    )
    data["builds"] = [entry]
    _write(target, data)
    return entry


def remove_approval_fixture_entry(out: Path) -> None:
    """Empty the fixture copy's approval list (the committed shipped state)."""
    target, data = _read_target(out)
    data["builds"] = []
    _write(target, data)


def rebind_fixture_entry(build: fc.BuildInfo, out: Path, *, note: str) -> tuple[str, str]:
    """Re-issue the single fixture entry for this build's CURRENT approval fingerprint, after a
    disposable-copy source change. Returns (old, new) fingerprints. Fixture copy only."""
    target, data = _read_target(out)
    builds = data.get("builds")
    if not isinstance(builds, list) or len(builds) != 1 or not isinstance(builds[0], dict):
        raise _refuse("rebind needs exactly one installed fixture entry")
    old = dict(builds[0])
    # A source swap moves the fingerprint, never the git identity: the entry keeps its git_sha and
    # the copy's HEAD must still equal it (a swap that moved HEAD is not this fixture).
    head = independent_git_head(build.src_dir)
    if head != old.get("git_sha"):
        raise _refuse("rebind: the build's git HEAD no longer matches the entry's git_sha")
    fingerprint = compat.compute_read_bridge_fingerprint(build.src_dir, data["bridge_files"])
    if fingerprint is None:
        raise _refuse("cannot fingerprint the approval files of the swapped copy")
    new = {
        **old,
        "fingerprint": fingerprint,
        "qualified_by": f"{PROVISIONAL} fixture-only {note}",
        "qualified_at": datetime.now(UTC).isoformat(),
    }
    try:  # the runtime's own field validation
        compat.BuildEntry(
            fingerprint=new["fingerprint"], git_sha=new.get("git_sha"), label=new["label"],
            qualified_by=new["qualified_by"], qualified_at=new["qualified_at"],
            source_sha=new.get("source_sha"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _refuse("invalid rebound approval entry") from exc
    data["builds"] = [new]
    _write(target, data)
    return str(old.get("fingerprint")), fingerprint


def install_from_env(build: fc.BuildInfo, out: Path, receipt: str | None) -> dict[str, Any] | None:
    """`direct_send_fixture.build_offline`'s hook: `receipt` is the value of `RECEIPT_ENV`."""
    if not receipt:
        return None
    return install_approval_fixture_entry(build, out, Path(receipt))


# --------------------------------------------------------------------------------------------
# Disposable copy of an extracted build, for the in-place source swap only.
# --------------------------------------------------------------------------------------------

_RETARGET_LIMIT = 2_000_000


def _within(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root)


def assert_copy_contained(dest: Path, original: Path) -> None:
    """Refuse a copied tree whose symlinks could reach outside it. Runs BEFORE any write.

    `copytree(symlinks=True)` keeps links verbatim, and a link is judged only by its last path
    component elsewhere, so a directory link (`.venv`, `bin`, `site-packages`, `tools`) pointing
    into the original would make a later retarget or swap write land in the original build. Every
    symlinked directory, and every dangling link, must resolve inside `dest`. A link to a FILE
    outside `dest` (a venv's `bin/python3` to a system interpreter) is normal: it is read and
    executed, never rewritten. One resolving into the `original` build is still refused.
    """
    root, source = dest.resolve(), original.resolve()
    for current, dirs, files in os.walk(dest, followlinks=False):
        for name in (*dirs, *files):
            path = Path(current, name)
            if not path.is_symlink():
                continue
            target = path.resolve()
            inside = target.is_relative_to(root)
            if target.is_relative_to(source) and not inside:
                raise _refuse(f"copy contains a link into the original build: {path}")
            if inside:
                continue
            if not path.exists():
                raise _refuse(f"copy contains a dangling link leaving the copy: {path}")
            if path.is_dir():
                raise _refuse(f"copy contains a directory link leaving the copy: {path}")


def _retarget_candidates(venv: Path, root: Path) -> list[Path]:
    """Every copied-venv file that may carry the original path, validated before any write."""
    if venv.is_symlink() or not venv.is_dir() or not _within(venv, root):
        raise _refuse("the copied venv is missing, a link, or outside the copy")
    candidates = [venv / "pyvenv.cfg"]
    bin_dir = venv / "bin"
    candidates += list(bin_dir.glob("*")) if bin_dir.is_dir() else []
    for site in venv.glob("lib/python*/site-packages"):
        candidates += [
            *site.glob("__editable__*"), *site.glob("*.pth"),
            *site.glob("*.dist-info/direct_url.json"),
        ]
    bin_dir_real = bin_dir.resolve()
    checked: list[Path] = []
    for path in candidates:
        if path.is_symlink():
            # Only `bin/*` links (an interpreter) are tolerated, and they are never written.
            if path.parent.resolve() != bin_dir_real:
                raise _refuse(f"refusing a symlinked retarget candidate: {path}")
            continue
        if path.exists() and not _within(path, root):
            raise _refuse(f"retarget candidate resolves outside the copy: {path}")
        checked.append(path)
    return checked


def _retarget_file(path: Path, root: Path, old: bytes, new: bytes) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > _RETARGET_LIMIT:
        return
    if not _within(path, root):
        raise _refuse(f"refusing to write outside the copy: {path}")
    data = path.read_bytes()
    if old in data:
        path.write_bytes(data.replace(old, new))


def _retarget_venv(venv: Path, old_src: Path, new_src: Path) -> None:
    """Point the COPIED venv's editable finder, `.pth` source entries, console-script shebangs and
    metadata at the copy, so the copy cannot import (or execute) the original tree. Every path is
    validated as inside the copy before the first write."""
    root = new_src.resolve()
    old, new = str(old_src).encode(), str(new_src).encode()
    for path in _retarget_candidates(venv, root):
        _retarget_file(path, root, old, new)


def verify_copy_isolation(build: fc.BuildInfo, original_src: Path) -> None:
    """The copy's interpreter must import Hermes modules from the copy, never the original."""
    scratch = Path(tempfile.mkdtemp(prefix="hmp-copy-check-", dir=str(build.src_dir.parent)))
    try:
        fc.assert_outside_real_home(scratch, "copy isolation check home")
        env = fc.clean_hermes_env(
            extra={"HERMES_HOME": str(scratch), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        code = (
            "import gateway.pairing as a, tools.approval as b; print(a.__file__); print(b.__file__)"
        )
        proc = subprocess.run(
            [str(build.venv_python), "-c", code],
            cwd=str(scratch), env=env, capture_output=True, text=True, timeout=120, check=False,
        )
        paths = [Path(line).resolve() for line in proc.stdout.splitlines() if line.strip()]
        new_src, old_src = build.src_dir.resolve(), Path(original_src).resolve()
        if (
            proc.returncode != 0
            or len(paths) != 2
            or not all(p.is_relative_to(new_src) for p in paths)
            or any(p.is_relative_to(old_src) for p in paths)
        ):
            raise _refuse(
                "the copied build does not import from itself; refusing to mutate it: "
                f"rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr[-400:]!r}"
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _verify_git_copy(original: Path, dest: Path) -> None:
    """A git fixture's copy owns a separate `.git` with the same identity metadata; an archive
    copy must not have grown one. Runs before the copy is used (the swap only mutates a listed
    source file, never `.git`)."""
    original_git = (original / ".git").exists() or (original / ".git").is_symlink()
    if not original_git:
        if (dest / ".git").exists() or (dest / ".git").is_symlink():
            raise _refuse("an archive copy unexpectedly contains a .git")
        return
    head = assert_git_fixture_clone(original)
    if assert_git_fixture_clone(dest, original=original) != head:
        raise _refuse("the copied .git HEAD differs from the original")
    if git_identity_digest(dest) != git_identity_digest(original):
        raise _refuse("the copied .git metadata differs from the original")


def copy_build_for_mutation(
    builds_dir: Path, label: str, dest_builds_dir: Path, *, files: Sequence[str] = (),
) -> fc.BuildInfo:
    """Fresh copy of `<builds_dir>/<label>/src` at `<dest_builds_dir>/<label>/src`.

    The original is only read. The copy's venv is re-pointed at itself and verified; with `files`,
    the copy's fingerprint must equal the original's before anything is mutated.
    """
    original = (Path(builds_dir) / label / "src").resolve()
    dest = (Path(dest_builds_dir) / label / "src").resolve()
    fc.assert_outside_real_home(dest, "mutation copy")
    fc.assert_never_real_hermes_dir(dest, "mutation copy")
    if dest.exists() or dest.is_relative_to(original) or original.is_relative_to(dest):
        raise _refuse("mutation copy must be a fresh directory disjoint from the original build")
    if (original / ".git").exists() or (original / ".git").is_symlink():
        assert_git_fixture_clone(original)  # an unsafe source is refused before any copy or write
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        original, dest, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    try:
        assert_copy_contained(dest, original)  # before ANY write, so a refusal leaves the original
        _retarget_venv(dest / ".venv", original, dest)  # exactly as it was
    except fc.FixtureSafetyError:
        shutil.rmtree(dest, ignore_errors=True)  # never follows links
        raise
    try:
        _verify_git_copy(original, dest)
    except fc.FixtureSafetyError:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    build = fc.resolve_build(Path(dest_builds_dir), label)
    verify_copy_isolation(build, original)
    if files and (
        compat.compute_read_bridge_fingerprint(original, files)
        != compat.compute_read_bridge_fingerprint(dest, files)
    ):
        raise _refuse("mutation copy differs from the original before any mutation")
    return build


def mutate_swap_file(build: fc.BuildInfo, approval_files: Sequence[str],
                     *other_lane_files: Sequence[str]) -> str:
    """Append an inert comment to the approval-only SWAP_FILE inside a scratch copy.

    `other_lane_files` are the read and direct-send lists; the swap file must lie outside them.
    """
    if SWAP_FILE not in approval_files or any(SWAP_FILE in lane for lane in other_lane_files):
        raise _refuse(f"{SWAP_FILE} is not an approval-only file for this boundary")
    root = build.src_dir.resolve()
    path = root / SWAP_FILE
    if not path.is_file() or path.is_symlink():
        raise _refuse(f"{SWAP_FILE} is missing from the mutation copy")
    if any(p.is_symlink() for p in path.parents if p.is_relative_to(root) and p != root) or (
        not _within(path, root)
    ):
        raise _refuse(f"{SWAP_FILE} resolves outside the mutation copy; refusing to write")
    with path.open("ab") as handle:
        handle.write(b"\n# hmp fixture in-place swap (approval-only, inert)\n")
    return SWAP_FILE

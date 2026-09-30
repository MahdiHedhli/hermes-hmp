"""Real compat-gate readers (T023): the git-metadata SHA reader, the read-bridge fingerprint,
`read_compat_builds.json` loading, and the dependency probe. `test_compat_gate.py` and
`test_compat_matching.py` already cover `CompatGate`'s fixed evaluation order and the CS-19
matching rule with injected readers/probes; this file covers what actually implements
`BuildIdentityReader`, the JSON loader and the probe, including against the real T004-extracted
Hermes builds (`tools/hermes_builds/extract.py`), which have no `.git` and so only ever exercise
the fingerprint path (research R8, CS-21).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from hmp_plugin import compat as compat_mod
from hmp_plugin.compat import (
    BuildIdentity,
    DependencySpec,
    GitFingerprintReader,
    _resolve_gitdir,  # white-box test of the git-metadata parser
    approval_build_qualified,
    compute_read_bridge_fingerprint,
    direct_send_build_qualified,
    load_read_compat_list,
    probe_read_dependencies,
    resolve_git_head_sha,
)

BRIDGE_FILES = ("a.py", "sub/b.py")


def test_direct_send_requires_its_own_exact_build_and_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "hermes"
    source.mkdir()
    (source / "send.py").write_text("def send(): pass\n", encoding="utf-8")
    git_dir = source / ".git"
    git_dir.mkdir()
    sha = "a" * 40
    (git_dir / "HEAD").write_text(sha + "\n", encoding="utf-8")
    fingerprint = compute_read_bridge_fingerprint(source, ["send.py"])
    assert fingerprint is not None
    manifest = tmp_path / "direct-send.json"
    manifest.write_text(json.dumps({
        "format": 1,
        "bridge_files": ["send.py"],
        "builds": [{
            "label": "fixture", "fingerprint": fingerprint, "git_sha": sha,
            "qualified_by": "test", "qualified_at": "2026-09-29",
        }],
    }), encoding="utf-8")
    calls: list[str] = []

    def probe(*, hermes_root: Path, bridge_files: tuple[str, ...]) -> tuple[str, ...]:
        calls.append(str(hermes_root))
        assert bridge_files == ("send.py",)
        return ()

    monkeypatch.setattr(compat_mod, "probe_direct_send_dependencies", probe)
    read_identity = BuildIdentity("f" * 64, sha)
    assert direct_send_build_qualified(
        read_identity, hermes_root=source, compat_path=manifest
    )
    assert len(calls) == 1
    assert not direct_send_build_qualified(
        BuildIdentity("f" * 64, "b" * 40), hermes_root=source, compat_path=manifest
    )
    assert len(calls) == 1  # no Hermes probe for another Git commit
    (source / "send.py").write_text("def send(): return 1\n", encoding="utf-8")
    assert not direct_send_build_qualified(
        read_identity, hermes_root=source, compat_path=manifest
    )
    assert len(calls) == 1  # no probe for a changed write surface
    (source / "send.py").write_text("def send(): pass\n", encoding="utf-8")
    monkeypatch.setattr(
        compat_mod, "probe_direct_send_dependencies", lambda **_: ("missing dependency",)
    )
    assert not direct_send_build_qualified(
        read_identity, hermes_root=source, compat_path=manifest
    )
    assert not direct_send_build_qualified(None, hermes_root=source, compat_path=manifest)


# --------------------------------------------------------------------------------------------
# Approval qualification lane (draft, fail closed; specs/004-approval-qualification-lane)
# --------------------------------------------------------------------------------------------

_SHA = "a" * 40


def _approval_fixture(tmp_path: Path, *, listed: bool = True) -> tuple[Path, Path, BuildIdentity]:
    """A fake Hermes tree with one approval file and an optional exact-build listing."""
    source = tmp_path / "hermes"
    (source / "tools").mkdir(parents=True)
    (source / "tools" / "approval.py").write_text("def resolve(): pass\n", encoding="utf-8")
    git_dir = source / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text(_SHA + "\n", encoding="utf-8")
    fingerprint = compute_read_bridge_fingerprint(source, ["tools/approval.py"])
    assert fingerprint is not None
    builds = (
        [{
            "label": "fixture", "fingerprint": fingerprint, "git_sha": _SHA,
            "qualified_by": "test", "qualified_at": "2026-09-30",
        }]
        if listed
        else []
    )
    manifest = tmp_path / "approval.json"
    manifest.write_text(
        json.dumps({"format": 1, "bridge_files": ["tools/approval.py"], "builds": builds}),
        encoding="utf-8",
    )
    return source, manifest, BuildIdentity("f" * 64, _SHA)


def _spy_approval_probe(
    monkeypatch: pytest.MonkeyPatch, result: tuple[str, ...] = ()
) -> list[tuple[Path, tuple[str, ...]]]:
    calls: list[tuple[Path, tuple[str, ...]]] = []

    def probe(*, hermes_root: Path, bridge_files: tuple[str, ...]) -> tuple[str, ...]:
        calls.append((hermes_root, tuple(bridge_files)))
        return result

    monkeypatch.setattr(compat_mod, "probe_approval_dependencies", probe)
    return calls


def test_shipped_approval_list_is_empty_and_covers_the_direct_send_files() -> None:
    package = Path(compat_mod.__file__).parent
    shipped = load_read_compat_list(package / "approval_supported_builds.json")
    send = load_read_compat_list(package / "direct_send_supported_builds.json")
    assert shipped.builds == ()
    assert set(send.bridge_files) < set(shipped.bridge_files)
    assert list(shipped.bridge_files) == sorted(shipped.bridge_files)
    assert all(not f.startswith("/") and ".." not in f for f in shipped.bridge_files)
    assert {
        f"{dependency.module.replace('.', '/')}.py"
        for dependency in compat_mod.APPROVAL_DEPENDENCIES
    } <= set(shipped.bridge_files)
    assert {
        "tools/approval_detection.py",
        "tools/approval_floors.py",
        "tools/approval_prompt.py",
        "tools/approval_smart.py",
        "tools/clarify_tool.py",
        "gateway/session_context.py",
        "gateway/hosted_room_execution_policy.py",
        "agent/terminal_approval_batch.py",
        "gateway/platforms/api_server_openai_routes.py",
        "gateway/platforms/api_server_room_dispatch.py",
        "gateway/status.py",
        "hermes_cli/config.py",
    } <= set(shipped.bridge_files)


def test_empty_approval_list_qualifies_nothing_and_probes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, manifest, identity = _approval_fixture(tmp_path, listed=False)
    calls = _spy_approval_probe(monkeypatch)
    def unexpected_read(*args: object, **kwargs: object) -> None:
        pytest.fail("an empty approval list must not inspect Hermes source")

    monkeypatch.setattr(compat_mod, "locate_hermes_root", unexpected_read)
    monkeypatch.setattr(compat_mod.GitFingerprintReader, "read", unexpected_read)
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=manifest)
    assert calls == []
    shipped = approval_build_qualified(identity, hermes_root=source)  # the real shipped list
    assert shipped is False
    assert calls == []


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        json.dumps({"format": 2, "bridge_files": [], "builds": []}),
        json.dumps({"format": 1, "bridge_files": "tools/approval.py", "builds": []}),
        json.dumps({"format": 1, "bridge_files": ["tools/approval.py"], "builds": {}}),
        json.dumps({
            "format": 1,
            "bridge_files": ["tools/approval.py"],
            "builds": [{"label": "x"}],
        }),
        json.dumps({"format": 1, "bridge_files": [], "builds": []}),
    ],
)
def test_malformed_approval_list_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    source, manifest, identity = _approval_fixture(tmp_path)
    manifest.write_text(content, encoding="utf-8")
    calls = _spy_approval_probe(monkeypatch)
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=manifest)
    assert calls == []


def test_missing_approval_list_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _, identity = _approval_fixture(tmp_path)
    calls = _spy_approval_probe(monkeypatch)
    assert not approval_build_qualified(
        identity, hermes_root=source, compat_path=tmp_path / "absent.json"
    )
    assert calls == []


def test_listed_build_with_no_bridge_files_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, manifest, identity = _approval_fixture(tmp_path)
    manifest.write_text(
        json.dumps({
            "format": 1,
            "bridge_files": [],
            "builds": [{
                "label": "fixture",
                "fingerprint": "f" * 64,
                "git_sha": _SHA,
                "qualified_by": "test",
                "qualified_at": "2026-09-30",
            }],
        }),
        encoding="utf-8",
    )
    calls = _spy_approval_probe(monkeypatch)
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=manifest)
    assert calls == []


def test_listed_build_with_passing_probe_is_qualified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, manifest, identity = _approval_fixture(tmp_path)
    calls = _spy_approval_probe(monkeypatch)
    assert approval_build_qualified(identity, hermes_root=source, compat_path=manifest)
    assert calls == [(source, ("tools/approval.py",))]
    assert not approval_build_qualified(None, hermes_root=source, compat_path=manifest)


def test_missing_approval_source_file_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, manifest, identity = _approval_fixture(tmp_path)
    (source / "tools" / "approval.py").unlink()
    calls = _spy_approval_probe(monkeypatch)
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=manifest)
    assert calls == []


def test_changed_approval_source_sha_mismatch_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, manifest, identity = _approval_fixture(tmp_path)
    calls = _spy_approval_probe(monkeypatch)
    (source / "tools" / "approval.py").write_text("def resolve(): return 1\n", encoding="utf-8")
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=manifest)
    assert calls == []  # changed fingerprint: no exact match, so nothing was probed
    (source / "tools" / "approval.py").write_text("def resolve(): pass\n", encoding="utf-8")
    moved = BuildIdentity("f" * 64, "b" * 40)  # read identity at another commit
    assert not approval_build_qualified(moved, hermes_root=source, compat_path=manifest)
    assert calls == []
    no_git = BuildIdentity("f" * 64, None)
    assert not approval_build_qualified(no_git, hermes_root=source, compat_path=manifest)
    assert calls == []


def test_approval_probe_failure_or_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, manifest, identity = _approval_fixture(tmp_path)
    _spy_approval_probe(monkeypatch, ("tools.approval.resolve_gateway_approval",))
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=manifest)

    def boom(**_: object) -> tuple[str, ...]:
        raise RuntimeError("probe exploded")

    monkeypatch.setattr(compat_mod, "probe_approval_dependencies", boom)
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=manifest)


def test_approval_probe_uses_only_approval_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[object] = []

    def fake(*, hermes_root: Path | None, bridge_files: object, specs: object) -> tuple[str, ...]:
        seen.append(specs)
        return ()

    monkeypatch.setattr(compat_mod, "probe_read_dependencies", fake)
    compat_mod.probe_approval_dependencies(hermes_root=tmp_path, bridge_files=("x.py",))
    compat_mod.probe_direct_send_dependencies(hermes_root=tmp_path, bridge_files=("x.py",))
    assert seen == [compat_mod.APPROVAL_DEPENDENCIES, compat_mod.DIRECT_SEND_DEPENDENCIES]
    assert compat_mod.APPROVAL_DEPENDENCIES is not compat_mod.DIRECT_SEND_DEPENDENCIES
    assert {(s.module, s.qualname) for s in compat_mod.DIRECT_SEND_DEPENDENCIES} == {
        ("hermes_cli.active_sessions", "active_session_registry_snapshot"),
        ("hermes_state", "SessionDB.get_session_by_title"),
        ("hermes_state", "SessionDB.get_compression_lineage"),
    }


def test_approval_and_guarded_send_qualification_are_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, approval_manifest, identity = _approval_fixture(tmp_path / "a")
    # A guarded-send manifest over the same tree, listing the exact build.
    send_manifest = tmp_path / "send.json"
    send_manifest.write_text(approval_manifest.read_text(encoding="utf-8"), encoding="utf-8")
    empty_manifest = tmp_path / "empty.json"
    empty_manifest.write_text(
        json.dumps({"format": 1, "bridge_files": ["tools/approval.py"], "builds": []}),
        encoding="utf-8",
    )
    approval_calls = _spy_approval_probe(monkeypatch)
    send_calls: list[str] = []

    def send_probe(*, hermes_root: Path, bridge_files: tuple[str, ...]) -> tuple[str, ...]:
        send_calls.append(str(hermes_root))
        return ()

    monkeypatch.setattr(compat_mod, "probe_direct_send_dependencies", send_probe)

    # Guarded send qualified, approvals not: an empty approval list never borrows the send list.
    assert direct_send_build_qualified(identity, hermes_root=source, compat_path=send_manifest)
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=empty_manifest)
    assert approval_calls == []

    # Approvals qualified, guarded send not.
    assert approval_build_qualified(identity, hermes_root=source, compat_path=approval_manifest)
    assert not direct_send_build_qualified(identity, hermes_root=source, compat_path=empty_manifest)
    assert send_calls == [str(source)]  # only the earlier send check probed; approvals never did

    # A failing approval probe leaves guarded-send qualification untouched, and vice versa.
    _spy_approval_probe(monkeypatch, ("missing",))
    assert not approval_build_qualified(identity, hermes_root=source, compat_path=approval_manifest)
    assert direct_send_build_qualified(identity, hermes_root=source, compat_path=send_manifest)
    monkeypatch.setattr(
        compat_mod, "probe_direct_send_dependencies", lambda **_: ("missing",)
    )
    _spy_approval_probe(monkeypatch)
    assert approval_build_qualified(identity, hermes_root=source, compat_path=approval_manifest)
    assert not direct_send_build_qualified(identity, hermes_root=source, compat_path=send_manifest)


def _write_bridge_files(root: Path) -> None:
    (root / "a.py").write_text("A = 1\n")
    (root / "sub").mkdir()
    (root / "sub" / "b.py").write_text("B = 2\n")


# --------------------------------------------------------------------------------------------
# compute_read_bridge_fingerprint (R8 step 3)
# --------------------------------------------------------------------------------------------


def test_fingerprint_is_deterministic(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    fp1 = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    fp2 = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    assert fp1 == fp2
    assert fp1 is not None
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)


def test_fingerprint_ignores_bridge_files_list_order(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    fp_forward = compute_read_bridge_fingerprint(tmp_path, list(BRIDGE_FILES))
    fp_reversed = compute_read_bridge_fingerprint(tmp_path, list(reversed(BRIDGE_FILES)))
    assert fp_forward == fp_reversed


def test_fingerprint_changes_with_content(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    before = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    (tmp_path / "a.py").write_text("A = 2\n")
    after = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    assert before != after


def test_fingerprint_none_on_missing_file(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("A = 1\n")
    # "sub/b.py" is never created.
    assert compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES) is None


def test_fingerprint_distinguishes_path_from_content_boundary(tmp_path: Path) -> None:
    # A naive `path + content` concatenation could collide two different splits of the same
    # bytes; the length-prefixed encoding must not.
    (tmp_path / "x").write_text("ab")
    (tmp_path / "y").write_text("")
    fp1 = compute_read_bridge_fingerprint(tmp_path, ["x", "y"])

    (tmp_path / "x").write_text("a")
    (tmp_path / "y").write_text("b")
    fp2 = compute_read_bridge_fingerprint(tmp_path, ["x", "y"])
    assert fp1 != fp2


# --------------------------------------------------------------------------------------------
# resolve_git_head_sha (R8 steps 2, 5): file-reads-only git metadata parsing
# --------------------------------------------------------------------------------------------


def _init_git_dir(root: Path, *, head_ref: str = "refs/heads/main") -> Path:
    git_dir = root / ".git"
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "HEAD").write_text(f"ref: {head_ref}\n")
    return git_dir


def test_no_git_directory_is_none(tmp_path: Path) -> None:
    assert resolve_git_head_sha(tmp_path) is None


def test_loose_ref_resolves(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path)
    sha = "a" * 40
    (git_dir / "refs" / "heads" / "main").write_text(sha + "\n")
    assert resolve_git_head_sha(tmp_path) == sha


def test_detached_head_resolves(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    sha = "b" * 40
    (git_dir / "HEAD").write_text(sha + "\n")
    assert resolve_git_head_sha(tmp_path) == sha


def test_packed_refs_fallback(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path)  # ref file for refs/heads/main never created
    sha = "c" * 40
    (git_dir / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\n"
        f"{sha} refs/heads/main\n"
        f"{'d' * 40} refs/heads/other\n"
    )
    assert resolve_git_head_sha(tmp_path) == sha


def test_symbolic_ref_chain(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path, head_ref="refs/heads/alias")
    sha = "e" * 40
    (git_dir / "refs" / "heads" / "alias").write_text("ref: refs/heads/main\n")
    (git_dir / "refs" / "heads" / "main").write_text(sha + "\n")
    assert resolve_git_head_sha(tmp_path) == sha


def test_ref_cycle_raises(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path, head_ref="refs/heads/a")
    (git_dir / "refs" / "heads" / "a").write_text("ref: refs/heads/b\n")
    (git_dir / "refs" / "heads" / "b").write_text("ref: refs/heads/a\n")
    with pytest.raises(ValueError, match="cycle"):
        resolve_git_head_sha(tmp_path)


def test_unresolvable_ref_raises(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)  # refs/heads/main never created, no packed-refs
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_empty_head_raises(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_malformed_head_raises(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("not a ref and not a sha\n")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_linked_worktree_gitdir_file(tmp_path: Path) -> None:
    """`.git` as a file pointer (a linked worktree), with `commondir` pointing back at the main
    git dir where `refs`/`packed-refs` actually live."""
    main_git = tmp_path / "main" / ".git"
    (main_git / "refs" / "heads").mkdir(parents=True)
    sha = "1234567890abcdef1234567890abcdef12345678"
    (main_git / "refs" / "heads" / "main").write_text(sha + "\n")

    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
    linked_gitdir = tmp_path / "main" / ".git" / "worktrees" / "worktree"
    linked_gitdir.mkdir(parents=True)
    (linked_gitdir / "HEAD").write_text("ref: refs/heads/main\n")
    (linked_gitdir / "commondir").write_text("../..\n")
    (worktree_root / ".git").write_text(f"gitdir: {linked_gitdir}\n")

    assert resolve_git_head_sha(worktree_root) == sha


def test_malformed_gitdir_file_raises(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("not a gitdir pointer\n")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_gitdir_file_pointing_nowhere_raises(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("gitdir: does/not/exist\n")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_resolve_gitdir_common_dir_defaults_to_worktree(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    dirs = _resolve_gitdir(tmp_path)
    assert dirs.worktree == git_dir
    assert dirs.common == git_dir


# --------------------------------------------------------------------------------------------
# GitFingerprintReader: the real BuildIdentityReader
# --------------------------------------------------------------------------------------------


def test_reader_no_git_gives_fingerprint_only_identity(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    reader = GitFingerprintReader(BRIDGE_FILES)
    identity = reader.read(tmp_path)
    assert identity is not None
    assert identity.git_sha is None
    assert len(identity.fingerprint) == 64


def test_reader_with_git_gives_both(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    sha = "f" * 40
    (git_dir / "HEAD").write_text(sha + "\n")
    reader = GitFingerprintReader(BRIDGE_FILES)
    identity = reader.read(tmp_path)
    assert identity is not None
    assert identity.git_sha == sha


def test_reader_missing_bridge_file_is_unidentifiable(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("A = 1\n")
    reader = GitFingerprintReader(BRIDGE_FILES)
    assert reader.read(tmp_path) is None


def test_reader_unresolvable_git_is_unidentifiable(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("garbage\n")
    reader = GitFingerprintReader(BRIDGE_FILES)
    assert reader.read(tmp_path) is None


def test_reader_is_stable_across_calls(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    reader = GitFingerprintReader(BRIDGE_FILES)
    first = reader.read(tmp_path)
    second = reader.read(tmp_path)
    assert first == second


# --------------------------------------------------------------------------------------------
# load_read_compat_list
# --------------------------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data))


def test_load_valid_list(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    _write_json(
        path,
        {
            "format": 1,
            "bridge_files": ["a.py", "b.py"],
            "builds": [
                {
                    "git_sha": "a" * 40,
                    "fingerprint": "b" * 64,
                    "label": "stock",
                    "qualified_by": "run-1",
                    "qualified_at": "2026-01-01",
                }
            ],
        },
    )
    result = load_read_compat_list(path)
    assert result.bridge_files == ("a.py", "b.py")
    assert len(result.builds) == 1
    assert result.builds[0].label == "stock"


def test_load_empty_builds(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    _write_json(path, {"format": 1, "bridge_files": [], "builds": []})
    result = load_read_compat_list(path)
    assert result.builds == ()


def test_load_the_committed_read_compat_builds_json() -> None:
    """The real, shipped file: the research R8 `bridge_files`, always non-empty, and (T064) a
    non-empty `builds` list -- reproducibility against a fresh T063 run is checked separately,
    below, gated on extracted builds being available (`test_committed_read_compat_builds_
    reproduces_a_fresh_t063_run`)."""
    path = Path(__file__).resolve().parents[2] / "hmp_plugin" / "read_compat_builds.json"
    result = load_read_compat_list(path)
    assert len(result.builds) > 0, "T064 must populate read_compat_builds.json's builds list"
    assert len(result.bridge_files) > 0
    assert "hermes_constants.py" in result.bridge_files


@pytest.mark.parametrize(
    "data",
    [
        {},  # missing format
        {"format": 2, "bridge_files": [], "builds": []},  # wrong format
        {"format": 1, "bridge_files": "not-a-list", "builds": []},
        {"format": 1, "bridge_files": [1, 2], "builds": []},
        {"format": 1, "bridge_files": [], "builds": "not-a-list"},
        {"format": 1, "bridge_files": [], "builds": [{"fingerprint": "x" * 64}]},  # missing label
        {"format": 1, "bridge_files": [], "builds": ["not-an-object"]},
    ],
)
def test_load_malformed_list_raises(tmp_path: Path, data: object) -> None:
    path = tmp_path / "list.json"
    _write_json(path, data)
    with pytest.raises(ValueError):
        load_read_compat_list(path)


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_read_compat_list(tmp_path / "does-not-exist.json")


def test_load_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("{not valid json")
    with pytest.raises(ValueError):
        load_read_compat_list(path)


# --------------------------------------------------------------------------------------------
# probe_read_dependencies: synthetic tree exercising the real dependency table's mechanics
# (module import, qualname resolution, signature shape, bridge_files containment)
# --------------------------------------------------------------------------------------------


@pytest.fixture()
def synthetic_module_tree(tmp_path: Path):
    root = tmp_path / "src"
    root.mkdir()
    (root / "good_mod.py").write_text(
        "class Widget:\n"
        "    def method(self, x):\n"
        "        return x\n"
        "\n"
        "def free_function(a, b=1):\n"
        "    return a + b\n"
    )
    (root / "outside_mod.py").write_text("VALUE = 1\n")
    sys.path.insert(0, str(root))
    for name in ("good_mod", "outside_mod"):
        sys.modules.pop(name, None)
    try:
        yield root
    finally:
        sys.path.remove(str(root))
        for name in ("good_mod", "outside_mod"):
            sys.modules.pop(name, None)


def test_probe_all_present_and_contained(synthetic_module_tree: Path) -> None:
    specs = (
        DependencySpec("good_mod", "Widget"),
        DependencySpec("good_mod", "Widget.method"),
        DependencySpec("good_mod", "free_function"),
    )
    missing = probe_read_dependencies(
        hermes_root=synthetic_module_tree,
        bridge_files=("good_mod.py",),
        specs=specs,
    )
    assert missing == ()


def test_probe_missing_module(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("does_not_exist_mod"),)
    missing = probe_read_dependencies(
        hermes_root=synthetic_module_tree, bridge_files=("good_mod.py",), specs=specs
    )
    assert missing == ("does_not_exist_mod",)


def test_probe_missing_attribute(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("good_mod", "NoSuchClass"),)
    missing = probe_read_dependencies(
        hermes_root=synthetic_module_tree, bridge_files=("good_mod.py",), specs=specs
    )
    assert missing == ("good_mod.NoSuchClass",)


def test_probe_missing_nested_attribute(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("good_mod", "Widget.no_such_method"),)
    missing = probe_read_dependencies(
        hermes_root=synthetic_module_tree, bridge_files=("good_mod.py",), specs=specs
    )
    assert missing == ("good_mod.Widget.no_such_method",)


def test_probe_module_outside_bridge_files_is_missing(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("outside_mod"),)
    # outside_mod.py exists and imports fine, but it is not in the allowed bridge_files list.
    missing = probe_read_dependencies(
        hermes_root=synthetic_module_tree, bridge_files=("good_mod.py",), specs=specs
    )
    assert missing == ("outside_mod",)


def test_probe_never_calls_anything(synthetic_module_tree: Path) -> None:
    (synthetic_module_tree / "dangerous_mod.py").write_text(
        "def free_function():\n    raise RuntimeError('must never be called by the probe')\n"
    )
    sys.modules.pop("dangerous_mod", None)
    try:
        specs = (DependencySpec("dangerous_mod", "free_function"),)
        missing = probe_read_dependencies(
            hermes_root=synthetic_module_tree,
            bridge_files=("dangerous_mod.py",),
            specs=specs,
        )
        assert missing == ()  # imported and shape-checked, never invoked
    finally:
        sys.modules.pop("dangerous_mod", None)


def test_probe_unwraps_decorated_internals(synthetic_module_tree: Path) -> None:
    """A `@contextmanager` internal (like `gateway.run._profile_runtime_scope`) is defined in
    its own module, not in `contextlib.py`: the probe unwraps it before the CS-21 check. Its
    stdlib wrapper layer (`contextlib.py` itself) never needs to be listed."""
    (synthetic_module_tree / "scoped_mod.py").write_text(
        "import contextlib\n"
        "from outside_mod import passthrough\n"
        "\n"
        "@contextlib.contextmanager\n"
        "def scope(home):\n"
        "    yield home\n"
        "\n"
        "@passthrough\n"
        "def wrapped(x):\n"
        "    return x\n"
        "\n"
        "from outside_mod import elsewhere\n"
    )
    (synthetic_module_tree / "outside_mod.py").write_text(
        "import functools\n"
        "VALUE = 1\n"
        "def passthrough(fn):\n"
        "    @functools.wraps(fn)\n"
        "    def inner(*a, **k):\n"
        "        return fn(*a, **k)\n"
        "    return inner\n"
        "def elsewhere():\n"
        "    return 1\n"
    )
    for name in ("scoped_mod", "outside_mod"):
        sys.modules.pop(name, None)
    try:
        import inspect as _inspect

        import scoped_mod  # type: ignore[import-not-found]

        assert _inspect.getsourcefile(scoped_mod.scope).endswith("contextlib.py")  # the trap
        specs = (DependencySpec("scoped_mod", "scope"),)
        assert (
            probe_read_dependencies(
                hermes_root=synthetic_module_tree, bridge_files=("scoped_mod.py",), specs=specs
            )
            == ()
        )
        # SR-3: `wrapped`'s OUTER layer (`passthrough`'s `inner`) is defined in outside_mod.py,
        # not scoped_mod.py -- the wrapper code is what actually runs. Checking only the
        # innermost, unwrapped function (the old behavior) would let it pass with outside_mod.py
        # left out of bridge_files entirely; every layer must be checked.
        specs = (DependencySpec("scoped_mod", "wrapped"),)
        assert probe_read_dependencies(
            hermes_root=synthetic_module_tree, bridge_files=("scoped_mod.py",), specs=specs
        ) == ("scoped_mod.wrapped",)
        assert (
            probe_read_dependencies(
                hermes_root=synthetic_module_tree,
                bridge_files=("scoped_mod.py", "outside_mod.py"),
                specs=specs,
            )
            == ()
        )
        # Unwrapping never hides a real definition outside the list.
        specs = (DependencySpec("scoped_mod", "elsewhere"),)
        assert probe_read_dependencies(
            hermes_root=synthetic_module_tree, bridge_files=("scoped_mod.py",), specs=specs
        ) == ("scoped_mod.elsewhere",)
    finally:
        sys.modules.pop("scoped_mod", None)


def test_probe_treats_a_wrapped_cycle_as_missing(synthetic_module_tree: Path) -> None:
    """SR-3 problem 2: `inspect.unwrap` raises `ValueError` on a `__wrapped__` cycle, which the
    old code caught and turned into `None`, then fell back to the (listed) module file -- passing
    silently. The new check must fail closed instead."""
    (synthetic_module_tree / "cyclic_mod.py").write_text(
        "def a(x):\n"
        "    return x\n"
        "def b(x):\n"
        "    return x\n"
        "a.__wrapped__ = b\n"
        "b.__wrapped__ = a\n"
    )
    sys.modules.pop("cyclic_mod", None)
    try:
        specs = (DependencySpec("cyclic_mod", "a"),)
        assert probe_read_dependencies(
            hermes_root=synthetic_module_tree, bridge_files=("cyclic_mod.py",), specs=specs
        ) == ("cyclic_mod.a",)
    finally:
        sys.modules.pop("cyclic_mod", None)


def test_probe_treats_an_undeterminable_source_as_missing(synthetic_module_tree: Path) -> None:
    """SR-3 problem 2: an object `inspect.getsourcefile` cannot place (a `functools.partial`, a
    callable instance, a C function) must never fall back to the module's own (listed) file."""
    (synthetic_module_tree / "partial_mod.py").write_text(
        "import functools\n"
        "def base(x, y):\n"
        "    return x + y\n"
        "curried = functools.partial(base, 1)\n"
    )
    sys.modules.pop("partial_mod", None)
    try:
        specs = (DependencySpec("partial_mod", "curried"),)
        assert probe_read_dependencies(
            hermes_root=synthetic_module_tree, bridge_files=("partial_mod.py",), specs=specs
        ) == ("partial_mod.curried",)
    finally:
        sys.modules.pop("partial_mod", None)


def test_probe_without_bridge_files_skips_containment(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("outside_mod"),)
    missing = probe_read_dependencies(hermes_root=synthetic_module_tree, specs=specs)
    assert missing == ()


def test_probe_default_specs_is_read_dependencies_table() -> None:
    import inspect as _inspect

    from hmp_plugin.compat import READ_DEPENDENCIES

    default = _inspect.signature(probe_read_dependencies).parameters["specs"].default
    assert default is READ_DEPENDENCIES
    assert len(READ_DEPENDENCIES) > 0


# --------------------------------------------------------------------------------------------
# Real T004-extracted builds (research R10; no .git -> fingerprint-only path, CS-19/CS-21).
# Gated on the same HMP_HERMES_BUILDS_DIR extraction location tools/ci/check_all.sh uses; skipped
# (not failed) when it has not been produced, exactly like test_register.py's HMP_HERMES_SRC gate.
#
# T035 (worker f1/w-refclient): the default is namespaced by this checkout's own worktree
# directory name, the same change and for the same reason as tools/ci/check_all.sh's default (see
# that file: a single fixed "$TMPDIR/hermes_bot_mobile_hermes_builds" shared by every worktree on
# the host makes concurrent F1 workers race each other's extractions). Both defaults derive the
# same path for the same worktree because both key off the worktree directory's basename, so a
# worker that extracted once via check_all.sh's default still finds it here without setting
# HMP_HERMES_BUILDS_DIR explicitly. An explicit HMP_HERMES_BUILDS_DIR (as the F1 worker rules'
# "Load limits" require -- a private extraction under the worker's own scratchpad) always wins.
# --------------------------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BUILDS_DIR = (
    Path(tempfile.gettempdir()) / f"hermes_bot_mobile_hermes_builds-{_REPO_ROOT.name}"
)
_BUILDS_DIR = Path(os.environ.get("HMP_HERMES_BUILDS_DIR", str(_DEFAULT_BUILDS_DIR)))
_STOCK_SRC = _BUILDS_DIR / "stock-base" / "src"
_EXPERIMENTAL_SRC = _BUILDS_DIR / "experimental" / "src"
# Machine-local optional builds (tools/hermes_builds/builds.yaml); see the T064 reproduction test.
_MACHINE_LOCAL_LABELS = (
    "owner-local", "upstream", "v921-git", "v924-archive", "v924-git",
    "omarchy-y520-git",
)

_extracted_builds_reason = (
    f"no T004 extraction at {_BUILDS_DIR} "
    f"(run: python3 tools/hermes_builds/extract.py --out {_BUILDS_DIR} "
    "--builds stock-base,experimental --skip-venv)"
)


def _committed_bridge_files() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "hmp_plugin" / "read_compat_builds.json"
    return load_read_compat_list(path).bridge_files


@pytest.mark.skipif(not _STOCK_SRC.is_dir(), reason=_extracted_builds_reason)
def test_real_build_has_no_git_and_uses_fingerprint_path() -> None:
    assert not (_STOCK_SRC / ".git").exists()
    reader = GitFingerprintReader(_committed_bridge_files())
    identity = reader.read(_STOCK_SRC)
    assert identity is not None
    assert identity.git_sha is None  # CS-19: no .git -> only a fingerprint-only entry can match
    assert len(identity.fingerprint) == 64


@pytest.mark.skipif(not _STOCK_SRC.is_dir(), reason=_extracted_builds_reason)
def test_real_build_fingerprint_is_stable_across_reads() -> None:
    bridge_files = _committed_bridge_files()
    reader = GitFingerprintReader(bridge_files)
    first = reader.read(_STOCK_SRC)
    second = reader.read(_STOCK_SRC)
    third = compute_read_bridge_fingerprint(_STOCK_SRC, bridge_files)
    assert first is not None
    assert first == second
    assert first.fingerprint == third


@pytest.mark.skipif(
    not (_STOCK_SRC.is_dir() and _EXPERIMENTAL_SRC.is_dir()), reason=_extracted_builds_reason
)
def test_real_builds_have_distinct_fingerprints() -> None:
    bridge_files = _committed_bridge_files()
    stock_fp = compute_read_bridge_fingerprint(_STOCK_SRC, bridge_files)
    experimental_fp = compute_read_bridge_fingerprint(_EXPERIMENTAL_SRC, bridge_files)
    assert stock_fp is not None
    assert experimental_fp is not None
    assert stock_fp != experimental_fp


@pytest.mark.skipif(not _STOCK_SRC.is_dir(), reason=_extracted_builds_reason)
def test_real_build_every_bridge_file_present() -> None:
    """A missing listed file would make the build unidentifiable (R8 step 5) — confirm the
    committed list actually resolves against a real extracted tree, file by file, so a failure
    here points at exactly which file is missing rather than just "fingerprint is None"."""
    missing = [f for f in _committed_bridge_files() if not (_STOCK_SRC / f).is_file()]
    assert missing == []


@pytest.mark.skipif(
    not (_STOCK_SRC.is_dir() and _EXPERIMENTAL_SRC.is_dir()), reason=_extracted_builds_reason
)
def test_gate_end_to_end_against_real_builds_fingerprint_only_path() -> None:
    """CS-19's "no .git -> fingerprint-only entry" case, driven by the real fingerprint of a real
    extracted build rather than a synthetic identity."""
    from hmp_plugin.compat import BuildEntry, CompatGate, ReadCompatList

    bridge_files = _committed_bridge_files()
    stock_fp = compute_read_bridge_fingerprint(_STOCK_SRC, bridge_files)
    assert stock_fp is not None

    entry = BuildEntry(
        fingerprint=stock_fp,
        git_sha=None,
        label="stock-base (test)",
        qualified_by="test_compat",
        qualified_at="2026-01-01",
    )
    compat_list = ReadCompatList(format=1, bridge_files=bridge_files, builds=(entry,))
    reader = GitFingerprintReader(bridge_files)

    def real_root() -> Path:
        return _STOCK_SRC

    supported = CompatGate(reader, compat_list, probe=lambda: (), root_locator=real_root)
    result = supported.evaluate()
    assert result.supported, result

    # The experimental build's fingerprint is different, so it is unlisted -> unsupported, and
    # the probe (which would import Hermes) must never even run.
    calls = {"n": 0}

    def counting_probe() -> tuple[str, ...]:
        calls["n"] += 1
        return ()

    def experimental_root() -> Path:
        return _EXPERIMENTAL_SRC

    unsupported = CompatGate(
        reader, compat_list, probe=counting_probe, root_locator=experimental_root
    )
    result = unsupported.evaluate()
    assert not result.supported
    assert calls["n"] == 0


@pytest.mark.skipif(
    not (_STOCK_SRC.is_dir() and _EXPERIMENTAL_SRC.is_dir()), reason=_extracted_builds_reason
)
def test_committed_read_compat_builds_reproduces_a_fresh_t063_run(tmp_path: Path) -> None:
    """T064 acceptance: an independent re-run of T063's `tools/compat/run_matrix.py` must
    reproduce every entry in the committed `read_compat_builds.json` -- this replaces the old "the
    committed list starts empty" placeholder assertion now that T064 has populated it. Slow (spins
    up a real gateway per build); skipped like the rest of this file's real-build tests unless
    T004's extraction has already been run."""
    path = Path(__file__).resolve().parents[2] / "hmp_plugin" / "read_compat_builds.json"
    committed = load_read_compat_list(path)
    assert len(committed.builds) > 0, "read_compat_builds.json's builds list is still empty"

    run_matrix = Path(__file__).resolve().parents[3] / "tools" / "compat" / "run_matrix.py"
    json_out = tmp_path / "matrix.json"
    # A machine-local optional build (builds.yaml `optional: true`, e.g. `owner-local`) can only be
    # re-run where its clone exists; everywhere else it is left out of the re-run and of the
    # comparison below. Every other committed entry must still be reproduced.
    machine_local = {
        label for label in _MACHINE_LOCAL_LABELS if not (_BUILDS_DIR / label / "src").is_dir()
    }
    expected = [entry for entry in committed.builds if entry.label not in machine_local]
    labels = sorted({entry.label for entry in expected})
    # A present `git_install` build (e.g. `owner-local`) records its git SHA from its clone, which
    # lives outside the located `_refs`; `HMP_HERMES_REFS_DIR` names that directory (the same one
    # given to extract.py / run_matrix.py `--refs-dir`).
    refs_dir = os.environ.get("HMP_HERMES_REFS_DIR")
    result = subprocess.run(
        [
            sys.executable, str(run_matrix),
            "--builds-dir", str(_BUILDS_DIR),
            "--out", str(tmp_path / "scratch"),
            "--builds", ",".join(labels),
            "--json-out", str(json_out),
            *(("--refs-dir", refs_dir) if refs_dir else ()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"run_matrix.py failed:\n{result.stdout}\n{result.stderr}"
    fresh = json.loads(json_out.read_text(encoding="utf-8"))
    fresh_by_label = {e["label"]: e for e in fresh["candidate_entries"]}
    for entry in expected:
        assert entry.label in fresh_by_label, (
            f"{entry.label!r} in read_compat_builds.json was not reproduced by a fresh T063 run "
            f"(fresh qualified labels: {sorted(fresh_by_label)})"
        )
        fresh_entry = fresh_by_label[entry.label]
        assert fresh_entry["fingerprint"] == entry.fingerprint, entry.label
        assert fresh_entry["git_sha"] == entry.git_sha, entry.label

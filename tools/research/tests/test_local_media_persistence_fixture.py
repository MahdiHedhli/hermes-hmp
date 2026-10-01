"""Tests for tools/research/local_media_persistence_fixture.py (G1 persistence characterization).

Unit tests need no native build. The `native` test runs all five scenarios once against the pinned
independent build and skips when it is absent (local-only, like the other build-bound fixture
tests). All data is synthetic; only closed metadata is asserted.
"""

from __future__ import annotations

import ast
import json
import os
import struct
import subprocess
import sys
import textwrap
import time
import tracemalloc
import zlib
from pathlib import Path
from typing import Any

import local_media_persistence_fixture as fx
import pytest

NATIVE_AVAILABLE = (fx.DEFAULT_NATIVE_SRC / ".venv" / "bin" / "python").is_file()
native = pytest.mark.skipif(not NATIVE_AVAILABLE, reason="pinned native build not present")


def test_synthetic_png_is_valid() -> None:
    data = fx.synthetic_png()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    at, kinds = 8, []
    while at < len(data):
        (length,) = struct.unpack(">I", data[at : at + 4])
        kind, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + length]
        (crc,) = struct.unpack(">I", data[at + 8 + length : at + 12 + length])
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        kinds.append(kind)
        at += 12 + length
    assert kinds == [b"IHDR", b"IDAT", b"IEND"]


def test_long_prompt_exceeds_both_hmp_caps() -> None:
    assert fx.hmp_cap("TOOL_OUTPUT_CAP") == 4000
    assert fx.hmp_cap("TOOL_ARGUMENTS_CAP") == 500
    assert len(fx.LONG_PROMPT) > fx.hmp_cap("TOOL_OUTPUT_CAP")


def test_child_environment_is_allowlist_only(tmp_path: Path) -> None:
    env = fx.child_environment(fx.scratch_layout(tmp_path))
    assert not [k for k in env if any(t in k.upper() for t in fx.ENV_MARK_KEYS)]
    assert all(
        str(tmp_path) in v
        for k, v in env.items()
        if k.startswith(("HERMES_", "XDG_")) or k == "HOME"
    )


def test_fixture_does_not_import_product_or_hermes_at_module_level() -> None:
    tree = ast.parse(Path(fx.__file__).read_text())
    top = {
        n.module.split(".")[0]
        if isinstance(n, ast.ImportFrom) and n.module
        else a.name.split(".")[0]
        for n in tree.body
        if isinstance(n, ast.Import | ast.ImportFrom)
        for a in (n.names if isinstance(n, ast.Import) else [None])
    }
    assert not top & {"hmp_plugin", "gateway", "agent", "tools", "hermes_state", "tui_gateway"}


def test_classify_send_is_closed() -> None:
    assert fx.classify_send(fx.FINAL_TEXT) == "model_final_text"
    assert fx.classify_send("anything else") == "other"


def test_write_private_is_0600(tmp_path: Path) -> None:
    path = tmp_path / "x"
    fx.write_private(path, "{}")
    assert oct(path.stat().st_mode & 0o777) == "0o600"


GIT_TEST_ENV = {
    "PATH": "/usr/bin:/bin",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}
CANARY_MODULES = ("hermes_state", "gateway", "agent", "tui_gateway", "tools")


def make_source(root: Path, *, git: bool = True) -> Path:
    """A fake native source whose importable modules would write a canary file if ever imported."""
    src = root / "src"
    src.mkdir(parents=True)
    for name in CANARY_MODULES:
        (src / f"{name}.py").write_text(f"open({str(root / 'canary')!r}, 'a').write({name!r})\n")
    (src / "tracked.txt").write_text("x\n")
    if git:
        for cmd in (
            ["init", "-q"],
            ["add", "."],
            ["-c", "commit.gpgsign=false", "commit", "-qm", "x"],
        ):
            subprocess.run(["git", "-C", str(src), *cmd], check=True, env=GIT_TEST_ENV)  # noqa: S607 - fixed `git` argv
    return src


def head_of(src: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(src), "rev-parse", "HEAD"],  # noqa: S607 - fixed `git` argv
        check=True,
        capture_output=True,
        text=True,
        env=GIT_TEST_ENV,
    ).stdout.strip()


@pytest.fixture
def no_launch(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Any child launch is recorded and fails the test; git helper calls are unaffected."""
    launched: list[list[str]] = []

    def spy(argv: list[str], **kwargs: object) -> object:
        launched.append(argv)
        raise AssertionError("child subprocess must not start")

    monkeypatch.setattr(fx, "_spawn_child", spy)
    return launched


def assert_nothing_started(root: Path, launched: list[list[str]], path_before: list[str]) -> None:
    assert launched == []
    assert not (root / "canary").exists()
    assert not [m for m in CANARY_MODULES if m in sys.modules]
    assert sys.path == path_before


def refuse(
    root: Path, launched: list[list[str]], reason: str, src: Path, evidence: Path | None = None
) -> None:
    before = list(sys.path)
    with pytest.raises(fx.FixtureSafetyError) as info:
        fx.run_parent(src, ("desktop",), evidence or root / "evidence")
    assert info.value.reason == reason
    assert not (evidence or root / "evidence").exists()
    assert_nothing_started(root, launched, before)


def test_parent_refuses_missing_git(tmp_path: Path, no_launch: list[list[str]]) -> None:
    refuse(tmp_path, no_launch, "source_git_missing", make_source(tmp_path, git=False))


def test_parent_refuses_symlinked_source(tmp_path: Path, no_launch: list[list[str]]) -> None:
    real = make_source(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(real)
    refuse(tmp_path, no_launch, "source_is_symlink", link)


def test_parent_refuses_symlinked_git_dir(tmp_path: Path, no_launch: list[list[str]]) -> None:
    src = make_source(tmp_path)
    (tmp_path / "gitdir").mkdir()
    (src / ".git").rename(tmp_path / "gitdir" / "real")
    (src / ".git").symlink_to(tmp_path / "gitdir" / "real")
    refuse(tmp_path, no_launch, "source_git_symlink", src)


def test_parent_refuses_unresolvable_git(tmp_path: Path, no_launch: list[list[str]]) -> None:
    src = make_source(tmp_path, git=False)
    (src / ".git").mkdir()  # a directory that is not a repository
    refuse(tmp_path, no_launch, "source_git_unresolvable", src)


def test_parent_refuses_head_mismatch(tmp_path: Path, no_launch: list[list[str]]) -> None:
    refuse(tmp_path, no_launch, "source_head_mismatch", make_source(tmp_path))


def test_parent_refuses_dirty_tree(
    tmp_path: Path, no_launch: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    src = make_source(tmp_path)
    monkeypatch.setattr(fx, "EXPECTED_NATIVE_HEAD", head_of(src))
    (src / "tracked.txt").write_text("changed\n")
    refuse(tmp_path, no_launch, "source_tree_dirty", src)


def test_clean_pinned_source_passes_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = make_source(tmp_path)
    monkeypatch.setattr(fx, "EXPECTED_NATIVE_HEAD", head_of(src))
    fx.validate_native_src(src)


def test_parent_refuses_source_inside_installed_or_live_home(
    tmp_path: Path, no_launch: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    installed = tmp_path / "installed-hermes"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(fx, "REAL_HERMES_MARKER", installed)
    for parent in (installed, home / ".hermes"):
        src = make_source(parent / "work")
        monkeypatch.setattr(
            fx, "EXPECTED_NATIVE_HEAD", head_of(src)
        )  # pinned and clean: only the location refuses
        refuse(tmp_path, no_launch, "source_inside_real_hermes_home", src)


def test_parent_refuses_real_user_hermes_path_without_touching_it(
    tmp_path: Path, no_launch: list[list[str]]
) -> None:
    refuse(
        tmp_path,
        no_launch,
        "source_inside_real_hermes_home",
        Path(os.path.expanduser("~")) / ".hermes" / "hermes-agent-not-opened",
    )


def test_symlink_into_installed_home_is_refused(
    tmp_path: Path, no_launch: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = tmp_path / "installed-hermes"
    installed.mkdir()
    monkeypatch.setattr(fx, "REAL_HERMES_MARKER", installed)
    link = tmp_path / "link"
    link.symlink_to(installed)
    refuse(tmp_path, no_launch, "source_inside_real_hermes_home", link)


def test_interpreter_may_resolve_only_to_shared_tools_or_the_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = tmp_path / "installed-hermes"
    monkeypatch.setattr(fx, "REAL_HERMES_MARKER", installed)
    src = tmp_path / "src"
    (src / ".venv" / "bin").mkdir(parents=True)
    python = src / ".venv" / "bin" / "python"
    for target_dir, allowed in (
        (installed / "tools" / "py" / "bin", True),
        (installed / "hermes-agent" / "venv" / "bin", False),
        (tmp_path / "elsewhere", False),
    ):
        target_dir.mkdir(parents=True)
        target = target_dir / "python3"
        target.write_text("#!/bin/sh\n")
        python.unlink(missing_ok=True)
        python.symlink_to(target)
        if allowed:
            fx.validate_interpreter(src)
        else:
            with pytest.raises(fx.FixtureSafetyError) as info:
                fx.validate_interpreter(src)
            assert info.value.reason == "interpreter_outside_allowed_roots"


def child_scratch(root: Path) -> Path:
    scratch = root / "scratch"
    scratch.mkdir(mode=0o700)
    for path in fx.scratch_layout(scratch).values():
        path.mkdir(parents=True, exist_ok=True)
    return scratch


def test_child_cli_refuses_bad_source_before_importing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = make_source(tmp_path)  # wrong HEAD
    scratch = child_scratch(tmp_path)
    layout = fx.scratch_layout(scratch)
    monkeypatch.setenv("HOME", str(layout["home"]))
    monkeypatch.setenv("HERMES_HOME", str(layout["hermes_root"]))
    before = list(sys.path)
    assert (
        fx.main(
            ["child", "--native-src", str(src), "--root", str(scratch), "--scenario", "desktop"]
        )
        == 2
    )
    assert_nothing_started(tmp_path, [], before)
    assert not (scratch / "result.json").exists()


def test_child_cli_refuses_unsafe_scratch_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = make_source(tmp_path)
    monkeypatch.setattr(fx, "EXPECTED_NATIVE_HEAD", head_of(src))
    good = child_scratch(tmp_path)
    layout = fx.scratch_layout(good)
    monkeypatch.setenv("HOME", str(layout["home"]))
    monkeypatch.setenv("HERMES_HOME", str(layout["hermes_root"]))
    fx.validate_scratch_root(good, src)

    link = tmp_path / "scratch-link"
    link.symlink_to(good)
    loose = tmp_path / "loose"
    loose.mkdir(mode=0o700)
    loose.chmod(0o755)
    unprepared = tmp_path / "unprepared"
    unprepared.mkdir(mode=0o700)
    installed = tmp_path / "installed-hermes" / "scratch"
    installed.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(fx, "REAL_HERMES_MARKER", tmp_path / "installed-hermes")
    cases = {
        link: "scratch_not_real_directory",
        loose: "scratch_not_private",
        unprepared: "scratch_layout_missing",
        installed: "scratch_inside_real_hermes_home",
        tmp_path / "absent": "scratch_missing",
        Path("relative"): "scratch_not_absolute",
    }
    for root, reason in cases.items():
        with pytest.raises(fx.FixtureSafetyError) as info:
            fx.validate_scratch_root(root, src)
        assert info.value.reason == reason, root

    monkeypatch.setenv("HOME", str(tmp_path))  # an ambient HOME is not the scratch HOME
    with pytest.raises(fx.FixtureSafetyError) as info:
        fx.validate_scratch_root(good, src)
    assert info.value.reason == "scratch_env_mismatch"


def test_direct_child_process_refuses_dirty_source_without_importing(tmp_path: Path) -> None:
    """A real fresh interpreter: the canary modules in the source would write a file if imported."""
    src = make_source(tmp_path)
    scratch = child_scratch(tmp_path)
    layout = fx.scratch_layout(scratch)
    env = fx.child_environment(layout)
    proc = subprocess.run(
        [
            sys.executable,
            fx.__file__,
            "child",
            "--native-src",
            str(src),
            "--root",
            str(scratch),
            "--scenario",
            "desktop",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 2 and '"REFUSED"' in proc.stdout
    assert not (tmp_path / "canary").exists() and not (scratch / "result.json").exists()


def test_evidence_path_must_be_new_and_private(
    tmp_path: Path, no_launch: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    src = make_source(tmp_path)
    monkeypatch.setattr(fx, "EXPECTED_NATIVE_HEAD", head_of(src))
    existing = tmp_path / "existing"
    existing.mkdir(mode=0o755)
    existing.chmod(0o755)
    (existing / "keep.txt").write_text("keep")
    link = tmp_path / "evidence-link"
    link.symlink_to(existing)
    for path in (existing, link, tmp_path / "tracked-file"):
        if path.name == "tracked-file":
            path.write_text("x")
        with pytest.raises(fx.FixtureSafetyError) as info:
            fx.run_parent(src, ("desktop",), path)
        assert info.value.reason == "evidence_path_exists"
    assert (
        oct(existing.stat().st_mode & 0o777) == "0o755"
        and (existing / "keep.txt").read_text() == "keep"
    )
    assert no_launch == []
    fresh = fx.prepare_evidence_dir(tmp_path / "fresh", src)
    assert oct(fresh.stat().st_mode & 0o777) == "0o700"


def test_write_private_never_reuses_or_follows(tmp_path: Path) -> None:
    old = tmp_path / "old"
    old.write_text("old")
    old.chmod(0o644)
    with pytest.raises(FileExistsError):
        fx.write_private(old, "new")
    assert (
        old.read_text() == "old" and oct(old.stat().st_mode & 0o777) == "0o644"
    )  # untouched, not "fixed"
    target = tmp_path / "target"
    target.write_text("target")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(FileExistsError):
        fx.write_private(link, "new")
    assert target.read_text() == "target"
    old_umask = os.umask(0)
    try:
        fx.write_private(tmp_path / "fresh", "{}")
    finally:
        os.umask(old_umask)
    assert oct((tmp_path / "fresh").stat().st_mode & 0o777) == "0o600"


def test_unix_socket_contact_is_refused_in_a_fresh_process(tmp_path: Path) -> None:
    """No listener exists: a refused contact raises the fixture's own error, not
    FileNotFoundError, and the counter shows the wrapper (not the OS) refused. socketpair and an
    asyncio loop still work."""
    code = textwrap.dedent(
        f"""
        import asyncio, socket, sys
        sys.path.insert(0, {str(Path(fx.__file__).parent)!r})
        import local_media_persistence_fixture as fx
        fx.install_ip_denial()
        path = {str(tmp_path / "private.sock")!r}
        refused = 0
        for call in (
            lambda s: s.connect(path),
            lambda s: s.connect_ex(path),
            lambda s: s.sendto(b"x", path),
        ):
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            try:
                call(s)
            except FileNotFoundError:
                sys.exit("reached the OS")
            except OSError as exc:
                refused += "blocked in this fixture" in str(exc)
            finally:
                s.close()
        a, b = socket.socketpair()
        a.send(b"ok")
        assert b.recv(2) == b"ok"
        a.close(); b.close()
        asyncio.run(asyncio.sleep(0))
        print(refused, fx._BLOCKED["unix_blocked"], fx._BLOCKED["ip_blocked"])
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 0, proc.stderr[-300:]
    assert proc.stdout.split() == ["3", "3", "0"]


def fake_native(tmp_path: Path, script: str) -> Path:
    src = tmp_path / "fake-src"
    (src / ".venv" / "bin").mkdir(parents=True)
    python = src / ".venv" / "bin" / "python"
    python.write_text("#!/bin/sh\n" + script)
    python.chmod(0o755)
    return src


def test_child_output_streams_to_private_files_not_parent_memory(tmp_path: Path) -> None:
    # $6 is the scratch root. 8 MB to each stream, then an oversize result file.
    src = fake_native(
        tmp_path,
        'head -c 8000000 /dev/zero | tr "\\0" x\n'
        'head -c 8000000 /dev/zero | tr "\\0" y >&2\n'
        'head -c 3000000 /dev/zero > "$6/result.json"\n',
    )
    evidence = fx.prepare_evidence_dir(tmp_path / "evidence", src)
    tracemalloc.start()
    summary = fx.run_scenario(src, "desktop", evidence)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert summary["reason"] == "child_result_oversize" and summary["status"] == "ERROR"
    assert summary["scratch_removed"]
    assert summary["child_stdout_bytes"] == 8_000_000 and summary["child_stderr_bytes"] == 8_000_000
    assert peak < 3_000_000
    for name in ("desktop.child.stdout", "desktop.child.log"):
        assert oct((evidence / name).stat().st_mode & 0o777) == "0o600"
    assert not any(name.endswith(".private.json") for name in os.listdir(evidence))


def test_child_timeout_is_hard_kills_descendants_and_cleans_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "survivor"
    src = fake_native(tmp_path, f"(sleep 3; touch {marker}) &\nsleep 30\n")
    monkeypatch.setattr(fx, "CHILD_TIMEOUT_SECONDS", 1)
    evidence = fx.prepare_evidence_dir(tmp_path / "evidence", src)
    started = time.monotonic()
    summary = fx.run_scenario(src, "desktop", evidence)
    assert time.monotonic() - started < 10
    assert summary["reason"] == "child_timeout" and summary["scratch_removed"]
    time.sleep(3.5)
    assert not marker.exists()


def test_child_result_symlink_is_refused(tmp_path: Path) -> None:
    secret = tmp_path / "outside.json"
    secret.write_text("{}")
    src = fake_native(tmp_path, f'ln -s {secret} "$6/result.json"\n')
    evidence = fx.prepare_evidence_dir(tmp_path / "evidence", src)
    summary = fx.run_scenario(src, "desktop", evidence)
    assert summary["reason"] == "child_result_unsafe" and summary["scratch_removed"]


@pytest.mark.skipif(
    not hasattr(os, "mkfifo") or not hasattr(os, "O_NONBLOCK"), reason="needs FIFOs and O_NONBLOCK"
)
def test_child_result_fifo_without_writer_is_refused_quickly(tmp_path: Path) -> None:
    fifo = tmp_path / "result.json"
    os.mkfifo(fifo)
    code = (
        "import sys, pathlib, local_media_persistence_fixture as fx\n"
        "print(fx.read_bounded_result(pathlib.Path(sys.argv[1])))\n"
    )
    start = time.monotonic()
    done = subprocess.run(
        [sys.executable, "-c", code, str(fifo)],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(fx.__file__).parent,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "(None, 'child_result_unsafe')"
    assert time.monotonic() - start < 5


@native
def test_all_scenarios_closed_metadata(tmp_path: Path) -> None:
    report = fx.run_parent(fx.DEFAULT_NATIVE_SRC, fx.SCENARIOS, tmp_path / "evidence")
    assert report["native_head_matches_expected"] and report["source_unchanged"]
    assert report["native_tree_clean_before"] and report["native_tree_clean_after"]
    for name, sc in report["scenarios"].items():
        assert sc["status"] == "COMPLETED", name
        assert all(sc["isolation"].values()), name
        identity = sc["runtime_identity"]
        assert identity["native_modules_from_independent_src"], name
        assert all(identity["native_modules_from_independent_src"].values()), name
        assert identity["modules_from_real_hermes_home_outside_interpreter_base"] == 0, name
        assert sc["scratch_removed"] and not sc["child_stderr_mentions_scratch"]
        assert sc["network"]["unix_contacts_blocked"] == 0, name
        assert sc["network"]["ip_connects_blocked"] == 0 or name.startswith("desktop")
        assert sc["provider_saves"] == 1 and sc["cache_files"]["alpha"]["count"] == 1
        assert sc["cache_files"]["root"]["count"] == 0 and sc["cache_files"]["beta"]["count"] == 0
        assert sc["root_db_sessions"] == 0 and sc["beta_db_sessions"] == 0
        assert sc["rows_alpha_db"]["assistant_call_id_matches_expected"]
    for name in ("desktop", "phone"):
        sc = report["scenarios"][name]
        row = sc["rows_alpha_db"]["tool_row_meta"][0]
        assert row["tool_name"] == "image_generate" and row["tool_call_id_matches_expected"]
        assert (
            row["raw_full_json_parses"]
            and row["raw_over_hmp_cap"]
            and not row["prefix_at_hmp_cap_parses"]
        )
        assert row["image_key_before_cap"] and row["image_in_selected_profile_cache"]
        assert sc["order"]["provider_before_tool_row_batch"]
        assert not sc["cache_file_without_authoritative_row"]
    for name in ("desktop_flushfail", "phone_flushfail"):
        sc = report["scenarios"][name]
        assert sc["cache_file_without_authoritative_row"]
        assert sc["rows_alpha_db"]["tool_rows"] == 0
        assert sc["order"]["tool_row_batch_injected_failures"] >= 1
    deferred = report["scenarios"]["desktop_deferred"]["rows_alpha_db"]
    assert deferred["assistant_call_names"] == ["tool_call"]
    assert deferred["assistant_call_bridge_underlying_is_image_generate"]
    assert (
        deferred["tool_row_names"] == ["image_generate"] and deferred["tool_name_matches_call_name"]
    )


# --------------------------------------------------------------------------------------------
# Modern `tool_call {calls: [...]}` coverage (additive to the accepted five scenarios)
# --------------------------------------------------------------------------------------------


def _assistant(calls: list[dict[str, object]], row_id: int = 1) -> dict[str, object]:
    return {"id": row_id, "role": "assistant", "content": None, "tool_calls": calls}


def _bridge_call(call_id: str, entries: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": "tool_call", "arguments": json.dumps({"calls": entries})},
    }


def _tool_row(call_id: str, name: str, content: object, row_id: int = 2) -> dict[str, object]:
    return {
        "id": row_id,
        "role": "tool",
        "tool_call_id": call_id,
        "tool_name": name,
        "content": content if isinstance(content, str) else json.dumps(content),
    }


def test_modern_scenarios_are_additive_and_do_not_repeat_the_accepted_five() -> None:
    assert not set(fx.MODERN_SCENARIOS) & set(fx.SCENARIOS)
    assert fx.ALL_SCENARIOS == fx.SCENARIOS + fx.MODERN_SCENARIOS + fx.HISTORY_SCENARIOS
    assert len(fx.SCENARIOS) == 5 and len(fx.MODERN_SCENARIOS) == 4
    for name in fx.MODERN_SCENARIOS:
        assert fx.BRIDGE_SHAPES[name][0] == "calls"
        assert fx.BRIDGE_SHAPES[name][1] == (2 if name.endswith("batch") else 1)
    assert fx.BRIDGE_SHAPES["desktop_deferred"] == ("legacy", 1)  # the accepted shape is unchanged
    surfaces = {n.split("_")[0] for n in fx.MODERN_SCENARIOS}
    assert surfaces == {"desktop", "phone"}


def test_batch_entries_use_distinct_synthetic_prompts_and_one_entry_keeps_the_long_prompt() -> None:
    one = fx.batch_entries(1)
    assert len(one) == 1 and one[0]["arguments"]["prompt"] == fx.LONG_PROMPT
    two = fx.batch_entries(2)
    assert [e["name"] for e in two] == ["image_generate", "image_generate"]
    prompts = [e["arguments"]["prompt"] for e in two]
    assert len(set(prompts)) == 2
    for tag, prompt in zip(fx.BATCH_PROMPT_TAGS, prompts, strict=True):
        assert f"-batch-{tag}-" in prompt


def test_synthetic_model_emits_the_requested_bridge_shape() -> None:
    assert fx.SyntheticModel().shape is None
    assert fx.SyntheticModel(shape=("calls", 2)).shape == ("calls", 2)
    assert fx.Ctx(Path("/nonexistent"), Path("/nonexistent"), shape=("calls", 1)).model.shape == (
        "calls",
        1,
    )


def test_cli_accepts_the_modern_scenarios_and_default_run_stays_the_accepted_five(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, ...]] = []

    def fake_parent(src: Path, scenarios: tuple[str, ...], evidence: Path | None) -> dict:
        seen.append(scenarios)
        return {}

    monkeypatch.setattr(fx, "run_parent", fake_parent)
    assert fx.main(["run", "--scenario", "phone_deferred_batch"]) == 0
    assert fx.main(["run"]) == 0
    assert seen == [("phone_deferred_batch",), fx.SCENARIOS]


def test_shape_one_entry_array_and_legacy_single_are_distinguished(tmp_path: Path) -> None:
    entry = {"name": "image_generate", "arguments": {"prompt": "p"}}
    legacy = {
        "id": "c2",
        "type": "function",
        "function": {"name": "tool_call", "arguments": json.dumps(entry)},
    }
    shaped = fx.describe_bridge_shape(
        [_assistant([_bridge_call("c1", [entry]), legacy])], [], tmp_path / "none", []
    )
    by_id = {o["id"]: o for o in shaped["outer_calls"]}
    assert by_id["c1"]["shape"] == "calls_array" and by_id["c1"]["entry_count"] == 1
    assert by_id["c2"]["shape"] == "legacy_single" and by_id["c2"]["entry_count"] == 1
    assert by_id["c1"]["entry_names_closed"] == ["image_generate"]


def test_shape_batch_with_one_shared_id_is_flagged_ambiguous_not_proof(tmp_path: Path) -> None:
    cache = tmp_path / "images"
    cache.mkdir()
    entries = [
        {"name": "image_generate", "arguments": {"prompt": f"synthetic-{i}"}} for i in range(2)
    ]
    rejected = {"error": "tool_call takes exactly one entry for local tools; you sent 2."}
    shaped = fx.describe_bridge_shape(
        [_assistant([_bridge_call("c1", entries)])],
        [_tool_row("c1", "tool_call", rejected)],
        cache,
        [],
    )
    assert shaped["underlying_call_count"] == 2 and shaped["outer_call_count"] == 1
    assert shaped["one_wrapper_result"] and not shaped["multiple_tool_rows"]
    assert shaped["shared_id_ambiguous"] is True
    assert shaped["tool_rows"][0]["error_class"] == "local_batch_rejected"
    assert shaped["tool_rows"][0]["image_field_count"] == 0 and shaped["image_field_total"] == 0
    assert shaped["outer_calls"][0]["entry_prompts_distinct"] == 2


def test_shape_counts_image_fields_anywhere_with_uniqueness_and_cache_membership(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "images"
    cache.mkdir()
    saved = [str(cache / f"g1synth-{t}-1.png") for t in fx.BATCH_PROMPT_TAGS]
    for path in saved:
        Path(path).write_bytes(fx.synthetic_png())
    (cache / "stray.png").write_bytes(fx.synthetic_png())
    entries = [{"name": "image_generate", "arguments": {}}] * 2
    result = {"results": [{"image": saved[0]}, {"image": saved[1]}, {"image": saved[1]}]}
    shaped = fx.describe_bridge_shape(
        [_assistant([_bridge_call("c1", entries)])],
        [_tool_row("c1", "tool_call", result)],
        cache,
        [{"path": p} for p in saved],
    )
    row = shaped["tool_rows"][0]
    assert row["image_field_paths"] == ["results[].image"] * 3
    assert shaped["image_field_total"] == 3 and shaped["image_values_unique"] == 2
    assert row["image_fields_absolute"] == [True] * 3 and row["image_fields_are_str"]
    assert shaped["cache_file_count"] == 3 and shaped["cache_files_referenced_by_rows"] == 2
    assert shaped["cache_files_unreferenced_by_rows"] == 1
    assert shaped["provider_saved_in_cache"] == 2 and shaped["provider_saved_distinct_names"] == 2
    assert shaped["cache_names_carry_batch_tags"] == [True, True]


def test_shape_multiple_tool_rows_with_distinct_ids_are_not_ambiguous(tmp_path: Path) -> None:
    entry = {"name": "image_generate", "arguments": {}}
    shaped = fx.describe_bridge_shape(
        [_assistant([_bridge_call("c1", [entry]), _bridge_call("c2", [entry])])],
        [_tool_row("c1", "image_generate", {"success": True}), _tool_row("c2", "x", {}, 3)],
        tmp_path / "none",
        [],
    )
    assert shaped["multiple_tool_rows"] and not shaped["one_wrapper_result"]
    assert shaped["shared_id_ambiguous"] is False
    assert shaped["tool_rows"][1]["tool_name_class"] == "other"


def test_shape_output_never_carries_prompts_paths_or_error_text(tmp_path: Path) -> None:
    secret_path = str(tmp_path / "private-dir" / "secret-name.png")
    entry = {"name": "image_generate", "arguments": {"prompt": "PRIVATE-PROMPT-TEXT"}}
    shaped = fx.describe_bridge_shape(
        [_assistant([_bridge_call("c1", [entry])])],
        [
            _tool_row(
                "c1",
                "image_generate",
                {"success": True, "image": secret_path, "prompt": "PRIVATE-PROMPT-TEXT"},
            )
        ],
        tmp_path / "private-dir",
        [{"path": secret_path}],
    )
    dumped = json.dumps(shaped)
    for needle in ("PRIVATE-PROMPT-TEXT", "private-dir", "secret-name"):
        assert needle not in dumped


def test_single_entry_observations_are_preserved_for_legacy_rows() -> None:
    names = ast.parse(Path(fx.__file__).read_text())
    inspect = next(
        n for n in ast.walk(names) if isinstance(n, ast.FunctionDef) and n.name == "inspect_rows"
    )
    keys = {
        c.slice.value
        for c in ast.walk(inspect)
        if isinstance(c, ast.Subscript)
        and isinstance(c.value, ast.Name)
        and c.value.id == "out"
        and isinstance(c.slice, ast.Constant)
    }
    assert {
        "assistant_call_names",
        "assistant_call_bridge_underlying_is_image_generate",
        "tool_row_meta",
        "tool_name_matches_call_name",
        "tool_row_names",
        "bridge_shape",
    } <= keys


@native
def test_modern_calls_array_scenarios_closed_metadata(tmp_path: Path) -> None:
    """Runs exactly the four new native cases (the accepted five are not repeated here).

    Pins the observed native outcome of build 8afa: a one-entry `calls` array is unwrapped to one
    `image_generate` execution; a two-entry local batch is rejected by the native bridge before any
    provider call. If the native behavior differs this fails; the fixture is not bent to match."""
    report = fx.run_parent(fx.DEFAULT_NATIVE_SRC, fx.MODERN_SCENARIOS, tmp_path / "evidence")
    assert report["native_head_matches_expected"] and report["source_unchanged"]
    assert report["native_tree_clean_before"] and report["native_tree_clean_after"]
    assert set(report["scenarios"]) == set(fx.MODERN_SCENARIOS)
    for name, sc in report["scenarios"].items():
        # Unchanged guard contracts.
        assert sc["status"] == "COMPLETED", name
        assert all(sc["isolation"].values()), name
        identity = sc["runtime_identity"]
        assert all(identity["native_modules_from_independent_src"].values()), name
        assert identity["modules_from_real_hermes_home_outside_interpreter_base"] == 0, name
        assert sc["scratch_removed"] and not sc["child_stderr_mentions_scratch"], name
        assert sc["network"]["unix_contacts_blocked"] == 0, name
        assert sc["network"]["ip_connects_blocked"] == 0 or name.startswith("desktop"), name
        assert sc["root_db_sessions"] == 0 and sc["beta_db_sessions"] == 0, name
        assert sc["cache_files"]["root"]["count"] == 0 and sc["cache_files"]["beta"]["count"] == 0
        assert sc["synthetic_model"]["tool_call_responses"] == 1, name
        # Causal observations common to both shapes: the model emitted one outer bridge call.
        shape = sc["rows_alpha_db"]["bridge_shape"]
        assert shape["outer_call_count"] == 1, name
        outer = shape["outer_calls"][0]
        assert outer["shape"] == "calls_array" and outer["outer_name_class"] == "tool_call", name
        assert outer["id"] == fx.CALL_ID and not outer["entry_ids_present"], name
        assert sc["rows_alpha_db"]["assistant_call_names"] == ["tool_call"], name
        assert shape["all_tool_rows_share_one_id"] and shape["tool_rows"][0]["id_is_outer_call"]
        # Provider saves, cache membership and tool-row evidence must agree with each other.
        assert shape["provider_saved_in_cache"] == sc["provider_saves"], name
        assert shape["cache_file_count"] == sc["cache_files"]["alpha"]["count"], name
        assert shape["image_field_total"] == sc["provider_saves"], name
    for name in ("desktop_deferred_calls", "phone_deferred_calls"):
        sc = report["scenarios"][name]
        shape = sc["rows_alpha_db"]["bridge_shape"]
        row = shape["tool_rows"][0]
        assert shape["underlying_call_count"] == 1 and shape["one_wrapper_result"], name
        assert not shape["shared_id_ambiguous"], name
        assert row["tool_name_class"] == "image_generate" and row["error_class"] is None, name
        assert row["json_type"] == "dict" and "image" in row["top_level_keys"], name
        assert row["image_field_paths"] == ["image"] and row["image_fields_are_str"], name
        assert row["image_fields_absolute"] == [True], name
        assert row["image_fields_are_provider_saved"] == [True], name
        assert sc["provider_saves"] == 1 and sc["cache_files"]["alpha"]["count"] == 1, name
        assert shape["cache_files_referenced_by_rows"] == 1, name
        assert sc["order"]["provider_before_tool_row_batch"], name
        assert sc["provider_saved_in_tool_thread_context"] == [
            {"home_is_alpha": True, "home_is_root": False, "thread_is_main": False}
        ], name
    desktop = report["scenarios"]["desktop_deferred_calls"]["order"]
    assert desktop["tool_row_batch_before_first_tool_completed_frame"]
    assert desktop["desktop_tool_completed_name_classes"] == ["image_generate"]
    assert desktop["desktop_tool_completed_id_is_outer_call"] == [True]
    phone = report["scenarios"]["phone_deferred_calls"]["order"]
    assert phone["tool_row_batch_before_first_reply_send"]
    # Native media delivery is keyed on the outer assistant call name, so the bridged call is not
    # auto-appended: no native media sender ran (contrast with the accepted direct Phone scenario).
    assert phone["adapter_media_calls"] == 0 and not phone["any_send_text_has_media_tag"]
    for name in ("desktop_deferred_batch", "phone_deferred_batch"):
        sc = report["scenarios"][name]
        shape = sc["rows_alpha_db"]["bridge_shape"]
        row = shape["tool_rows"][0]
        outer = shape["outer_calls"][0]
        assert outer["entry_count"] == 2 and outer["entry_prompts_distinct"] == 2, name
        assert outer["entry_names_closed"] == ["image_generate"] * 2, name
        assert shape["underlying_call_count"] == 2 and shape["tool_row_count"] == 1, name
        assert shape["one_wrapper_result"] and not shape["multiple_tool_rows"], name
        assert shape["shared_id_ambiguous"] is True, name
        assert row["tool_name_class"] == "tool_call", name
        assert row["error_class"] == "local_batch_rejected", name
        assert row["top_level_keys"] == ["error"] and row["image_field_count"] == 0, name
        assert sc["provider_saves"] == 0 and sc["cache_files"]["alpha"]["count"] == 0, name
        assert shape["image_values_unique"] == 0, name
    assert report["scenarios"]["desktop_deferred_batch"]["order"][
        "tool_row_batch_before_first_tool_completed_frame"
    ]
    assert report["scenarios"]["desktop_deferred_batch"]["order"][
        "desktop_tool_completed_name_classes"
    ] == ["tool_call"]
    assert report["scenarios"]["phone_deferred_batch"]["order"]["adapter_media_calls"] == 0


# --------------------------------------------------------------------------------------------
# G2 history lifecycle: helpers, guards and the native observations (additive; the accepted five and
# the four modern cases are not run here)
# --------------------------------------------------------------------------------------------

HISTORY_IMAGE = "/synthetic/profile/cache/images/one.png"


def _hrow(
    row_id: int, role: str, *, active: bool = True, compacted: bool = False, **fields: object
) -> dict[str, object]:
    return {"id": row_id, "role": role, "active": active, "compacted": compacted, **fields}


def _good_pair(first_id: int = 1, **flags: object) -> list[dict[str, object]]:
    call = _bridge_call(
        fx.CALL_ID, [{"name": "image_generate", "arguments": {"prompt": "synthetic prompt"}}]
    )
    result = json.dumps({"success": True, "image": HISTORY_IMAGE})
    return [
        _hrow(first_id, "assistant", content=None, tool_calls=[call], **flags),
        _hrow(
            first_id + 1,
            "tool",
            tool_call_id=fx.CALL_ID,
            tool_name="image_generate",
            content=result,
            **flags,
        ),
    ]


def test_history_scenario_is_additive_and_default_run_does_not_include_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert fx.HISTORY_SCENARIOS == ("history_lifecycle",)
    assert not set(fx.HISTORY_SCENARIOS) & (set(fx.SCENARIOS) | set(fx.MODERN_SCENARIOS))
    assert len(fx.SCENARIOS) == 5 and len(fx.MODERN_SCENARIOS) == 4
    seen: list[tuple[str, ...]] = []
    monkeypatch.setattr(fx, "run_parent", lambda src, scen, evidence: seen.append(scen) or {})
    assert fx.main(["run", "--scenario", "history_lifecycle"]) == 0
    assert fx.main(["run"]) == 0
    assert seen == [("history_lifecycle",), fx.SCENARIOS]


def test_history_scenario_adds_owning_files_to_the_fingerprint_only_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(fx, "validate_native_src", lambda src: None)
    monkeypatch.setattr(fx, "validate_interpreter", lambda src: None)
    monkeypatch.setattr(fx, "native_clean", lambda src: True)
    monkeypatch.setattr(fx, "run_scenario", lambda src, name, evidence: {"status": "COMPLETED"})

    def spy(src: Path, names: tuple[str, ...] = fx.OWNING_FILES) -> dict[str, str]:
        calls.append(names)
        return dict.fromkeys(names, "x")

    monkeypatch.setattr(fx, "fingerprint", spy)
    src = tmp_path / "src"
    fx.run_parent(src, ("desktop",), tmp_path / "e1")
    fx.run_parent(src, ("history_lifecycle",), tmp_path / "e2")
    assert calls[:2] == [fx.OWNING_FILES, fx.OWNING_FILES]
    wanted = fx.OWNING_FILES + fx.HISTORY_EXTRA_FILES
    assert calls[2:] == [wanted, wanted]
    for name in (
        "hermes_state_messages.py",
        "hermes_state_portability.py",
        "hermes_state_compression.py",
        "hermes_state_sessions.py",
        "hermes_cli/backup_restore.py",
    ):
        assert name in wanted
    assert not set(fx.OWNING_FILES) & set(fx.HISTORY_EXTRA_FILES)


def test_pair_observation_requires_the_whole_active_pair() -> None:
    assert fx.pair_observation(_good_pair(), HISTORY_IMAGE)["complete"]
    call_row, tool_row = _good_pair()
    for rows in ([call_row], [tool_row], []):
        assert not fx.pair_observation(rows, HISTORY_IMAGE)["complete"]
    # A result whose call row was retired (the half tail clone) is not a complete pair.
    retired_call = {**call_row, "active": False, "compacted": True}
    half = fx.pair_observation([retired_call, tool_row], HISTORY_IMAGE)
    assert half["active_assistant_rows_with_call"] == 0 and not half["complete"]
    assert half["active_tool_rows_with_call_id"] == 1 and half["result_success_true"]


def test_pair_observation_ignores_retired_duplicates_but_not_active_ones() -> None:
    call_row, tool_row = _good_pair(1)
    clone_call, clone_tool = _good_pair(11)
    retired = [{**r, "active": False} for r in (call_row, tool_row)]
    assert fx.pair_observation([*retired, clone_call, clone_tool], HISTORY_IMAGE)["complete"]
    ambiguous = fx.pair_observation([call_row, tool_row, clone_call, clone_tool], HISTORY_IMAGE)
    assert ambiguous["active_assistant_rows_with_call"] == 2 and not ambiguous["complete"]


def test_pair_observation_rejects_wrong_shape_name_result_and_image() -> None:
    call_row, tool_row = _good_pair()
    two_entries = _bridge_call(fx.CALL_ID, fx.batch_entries(2))
    batch = {**call_row, "tool_calls": [two_entries]}
    assert not fx.pair_observation([batch, tool_row], HISTORY_IMAGE)["complete"]
    wrapper_named = {**tool_row, "tool_name": "tool_call"}
    assert not fx.pair_observation([call_row, wrapper_named], HISTORY_IMAGE)["complete"]
    failed = {**tool_row, "content": json.dumps({"success": False, "image": HISTORY_IMAGE})}
    assert not fx.pair_observation([call_row, failed], HISTORY_IMAGE)["complete"]
    elsewhere = {**tool_row, "content": json.dumps({"success": True, "image": "/other.png"})}
    assert not fx.pair_observation([call_row, elsewhere], HISTORY_IMAGE)["complete"]
    not_json = {**tool_row, "content": "not json"}
    assert not fx.pair_observation([call_row, not_json], HISTORY_IMAGE)["complete"]
    other_id = {**tool_row, "tool_call_id": "call_other"}
    assert not fx.pair_observation([call_row, other_id], HISTORY_IMAGE)["complete"]


def test_pair_observation_states_no_eligibility_policy() -> None:
    keys = set(fx.pair_observation(_good_pair(), HISTORY_IMAGE))
    assert not {"eligible", "authorized", "grant", "token", "candidate"} & keys


def test_pair_messages_are_a_one_entry_bridge_call_with_a_linked_result() -> None:
    rows = fx.pair_messages(HISTORY_IMAGE)
    assert [r["role"] for r in rows] == ["user", "assistant", "tool", "assistant"]
    shape = fx.outer_call_shape(rows[1]["tool_calls"][0])
    assert shape["id"] == fx.CALL_ID and shape["shape"] == "calls_array"
    assert shape["entry_count"] == 1 and shape["entry_names_closed"] == ["image_generate"]
    assert rows[2]["tool_call_id"] == fx.CALL_ID and rows[2]["tool_name"] == "image_generate"
    assert len(fx.pair_messages(HISTORY_IMAGE, extra_turn=True)) == 6
    # Fresh dicts every call: native appends write ids and timestamps into the dicts they receive.
    assert fx.pair_messages(HISTORY_IMAGE)[0] is not rows[0]


def test_row_summaries_carry_no_text_paths_or_call_arguments() -> None:
    rows = [
        {**r, "id": i + 1, "active": True, "compacted": False}
        for i, r in enumerate(fx.pair_messages(HISTORY_IMAGE))
    ]
    text = json.dumps(
        {
            "rows": fx.summarize_rows(rows),
            "carriers": fx.call_carrier_counts(rows),
            "pair": fx.pair_observation(rows, HISTORY_IMAGE),
        }
    )
    for raw in (
        "synthetic request",
        "synthetic prompt",
        HISTORY_IMAGE,
        fx.FINAL_TEXT,
        "/synthetic",
    ):
        assert raw not in text
    summary = fx.summarize_rows(rows)
    assert [r["role"] for r in summary] == ["user", "assistant", "tool", "assistant"]
    assert summary[1]["call_id_in_tool_calls"] == 1 and summary[2]["tool_call_id_is_expected"]
    # Identical payloads share an identity; the id does not enter it; a changed payload differs.
    clone = {**rows[2], "id": 99}
    assert fx.row_identity(clone) == fx.row_identity(rows[2])
    assert fx.row_identity({**rows[2], "content": "{}"}) != fx.row_identity(rows[2])


def _view(rows: list[dict[str, object]]) -> dict[str, object]:
    return {"rows": fx.summarize_rows(rows)}


def test_clone_facts_separate_new_active_rows_from_reactivated_ones() -> None:
    before_rows = _good_pair(1)
    after_clone = [
        *({**r, "active": False} for r in before_rows),
        *_good_pair(11),
    ]
    facts = fx.clone_facts(_view(before_rows), _view(after_clone))
    assert facts["old_pair_all_inactive"] and facts["fresh_active_pair_rows"] == 2
    assert facts["fresh_pair_identities_equal_old"] is True
    assert facts["inactive_rows_reactivated"] == 0 and facts["fresh_ids_above_previous_max"]
    retired = [{**r, "active": False} for r in before_rows]
    reactivated = fx.clone_facts(_view(retired), _view(before_rows))
    assert reactivated["inactive_rows_reactivated"] == 2 and reactivated["fresh_active_rows"] == 0
    cleared = fx.clone_facts(_view(before_rows), _view([]))
    assert cleared["fresh_pair_identities_equal_old"] is None


def test_tool_image_in_dir_compares_paths_only(tmp_path: Path) -> None:
    inside = tmp_path / "cache"
    row = _tool_row(fx.CALL_ID, "image_generate", {"success": True, "image": str(inside / "a.png")})
    row["active"] = True
    assert fx.tool_image_in_dir([row], inside)
    assert not fx.tool_image_in_dir([row], tmp_path / "other")
    assert not (inside / "a.png").exists()  # nothing was created or opened
    row["content"] = json.dumps({"success": True, "image": 7})
    assert not fx.tool_image_in_dir([row], inside)
    assert not fx.tool_image_in_dir([], inside)


def _restore_layout(root: Path) -> tuple[Path, Path]:
    primary = root / "hermes" / "profiles" / fx.PROFILE / "state.db"
    target = primary.parent / fx.RESTORE_DIR_NAME / "state.db"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"")
    primary.write_bytes(b"")
    return primary, target


def test_restore_target_accepts_only_the_dedicated_scratch_database(tmp_path: Path) -> None:
    primary, target = _restore_layout(tmp_path)
    fx.validate_restore_target(target, tmp_path, primary)


def test_restore_target_refuses_every_other_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary, target = _restore_layout(tmp_path)

    def reason(candidate: Path, root: Path = tmp_path, prim: Path = primary) -> str:
        with pytest.raises(fx.FixtureSafetyError) as info:
            fx.validate_restore_target(candidate, root, prim)
        return info.value.reason

    assert reason(primary) == "restore_target_shape"  # the primary profile database
    assert reason(target.parent / "snapshot.db") == "restore_target_shape"
    assert reason(Path("relative") / fx.RESTORE_DIR_NAME / "state.db") == "restore_target_shape"
    assert reason(target.parent / "gone" / fx.RESTORE_DIR_NAME / "state.db") == (
        "restore_target_missing"
    )
    assert reason(target, tmp_path / "elsewhere") == "restore_target_outside_scratch"
    assert reason(target, tmp_path, target) == "restore_target_is_primary_db"
    link = tmp_path / "link"
    link.symlink_to(target)
    linked_dir = tmp_path / "x" / fx.RESTORE_DIR_NAME
    linked_dir.parent.mkdir()
    (linked_dir).symlink_to(target.parent)
    assert reason(linked_dir / "state.db") == "restore_target_is_symlink"
    (target.parent / "fake").mkdir()
    live = tmp_path / "live_home"
    live_target = live / fx.RESTORE_DIR_NAME / "state.db"
    live_target.parent.mkdir(parents=True)
    live_target.write_bytes(b"")
    monkeypatch.setenv("HMP_G1_REAL_HERMES_MARKER", str(live))
    assert reason(live_target, live.parent, primary) == "restore_target_inside_real_hermes_home"


def test_restore_target_refuses_a_symlinked_database_file(tmp_path: Path) -> None:
    primary, target = _restore_layout(tmp_path)
    real = tmp_path / "real.db"
    real.write_bytes(b"")
    target.unlink()
    target.symlink_to(real)
    with pytest.raises(fx.FixtureSafetyError) as info:
        fx.validate_restore_target(target, tmp_path, primary)
    assert info.value.reason == "restore_target_is_symlink"


def test_restore_boundary_validates_immediately_before_the_native_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary, target = _restore_layout(tmp_path)
    events: list[str] = []
    real_validate = fx.validate_restore_target

    def spy(*args: Path) -> None:
        events.append("validate")
        real_validate(*args)

    def restore(snapshot: Path, dest: Path) -> str:
        events.append("restore")
        return "done"

    monkeypatch.setattr(fx, "validate_restore_target", spy)
    snapshot = target.parent / "snapshot.db"
    assert fx.guarded_restore(restore, snapshot, target, tmp_path, primary) == "done"
    assert events == ["validate", "restore"]

    events.clear()
    with pytest.raises(fx.FixtureSafetyError):
        fx.guarded_restore(restore, snapshot, primary, tmp_path, primary)
    assert events == ["validate"]  # a refused target never reaches the native restore


def test_public_restore_state_drops_raw_device_inode_but_keeps_other_file_facts() -> None:
    state = {"views": {}, "file": {"dev_ino": [16777231, 4242], "mode": "0o600"}}
    public = fx.public_restore_state(state)
    assert public["file"] == {"mode": "0o600"}
    assert "16777231" not in json.dumps(public) and "4242" not in json.dumps(public)
    assert state["file"]["dev_ino"] == [16777231, 4242]  # the raw state is untouched


def test_run_step_labels_a_safety_refusal_apart_from_an_api_error() -> None:
    steps: dict[str, Any] = {}

    def refuse() -> None:
        raise fx.FixtureSafetyError("restore_target_outside_scratch")

    def boom() -> None:
        raise ValueError("x")

    fx.run_step(steps, "refused", refuse)
    fx.run_step(steps, "broken", boom)
    assert steps["refused"] == {
        "status": "fixture_safety_refusal",
        "reason": "restore_target_outside_scratch",
    }
    assert steps["broken"]["status"] == "api_error"


HISTORY_FUNCTIONS = (
    "call_id_carriers",
    "row_identity",
    "summarize_rows",
    "call_carrier_counts",
    "pair_observation",
    "pair_messages",
    "validate_restore_target",
    "guarded_restore",
    "tool_image_in_dir",
    "file_facts",
    "run_step",
    "HistoryLab",
    "clone_facts",
    "step_baseline",
    "step_compaction_full",
    "step_compaction_half",
    "step_replace_archive",
    "step_replace_delete",
    "step_rewind",
    "step_deactivate",
    "step_clear",
    "step_child_compression",
    "step_branch",
    "step_import",
    "restore_state",
    "step_restore",
    "drive_history",
    "run_history_child",
)


def _fixture_tree() -> ast.Module:
    return ast.parse(Path(fx.__file__).read_text())


def _history_nodes() -> list[ast.AST]:
    return [
        n
        for n in _fixture_tree().body
        if isinstance(n, ast.FunctionDef | ast.ClassDef) and n.name in HISTORY_FUNCTIONS
    ]


def test_history_code_writes_only_through_native_apis_never_copied_sqlite() -> None:
    nodes = _history_nodes()
    assert {n.name for n in nodes} == set(HISTORY_FUNCTIONS)
    for node in nodes:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute):
                assert sub.attr not in {"execute", "executemany", "executescript", "cursor"}, (
                    node.name
                )
            if isinstance(sub, ast.Import | ast.ImportFrom):
                modules = (
                    [sub.module] if isinstance(sub, ast.ImportFrom) else [a.name for a in sub.names]
                )
                assert "sqlite3" not in modules, node.name
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                upper = sub.value.upper()
                assert not any(w in upper for w in ("INSERT INTO", "UPDATE ", "DELETE FROM")), (
                    node.name
                )


def test_history_native_imports_are_function_local() -> None:
    top = {
        (a.name if isinstance(n, ast.Import) else n.module or "").split(".")[0]
        for n in _fixture_tree().body
        if isinstance(n, ast.Import | ast.ImportFrom)
        for a in (n.names if isinstance(n, ast.Import) else [None])
    }
    assert not top & {"hermes_cli", "hermes_state_errors", "tui_gateway", "gateway", "hermes_state"}


def _call_names_in_order(func: ast.FunctionDef) -> list[str]:
    calls = [(n.lineno, n.col_offset, n.func) for n in ast.walk(func) if isinstance(n, ast.Call)]
    names = []
    for _, _, f in sorted(calls, key=lambda c: (c[0], c[1])):
        if isinstance(f, ast.Name):
            names.append(f.id)
        elif isinstance(f, ast.Attribute):
            names.append(f.attr)
    return names


def test_history_child_denies_network_before_any_native_work_and_keeps_validated_entry() -> None:
    funcs = {n.name: n for n in _fixture_tree().body if isinstance(n, ast.FunctionDef)}
    order = _call_names_in_order(funcs["run_history_child"])
    assert order.index("insert") < order.index("install_ip_denial") < order.index("drive_history")
    assert order.index("isolation_checks") < order.index("drive_history")
    # The history child is reached only through run_child, which main() reaches only after both
    # validators; run_child dispatches before any model server, config write or surface import.
    main_calls = _call_names_in_order(funcs["main"])
    assert main_calls.index("validate_native_src") < main_calls.index("validate_scratch_root")
    assert main_calls.index("validate_scratch_root") < main_calls.index("run_child")
    child_calls = _call_names_in_order(funcs["run_child"])
    assert child_calls[0] == "run_history_child"


def test_history_child_allows_no_loopback_port() -> None:
    # No SyntheticModel server is started for this scenario, so the allowed-port list stays empty
    # and every IP connect, not just external ones, is denied.
    source = ast.get_source_segment(
        Path(fx.__file__).read_text(),
        next(n for n in _history_nodes() if n.name == "run_history_child"),
    )
    assert source is not None and ".start(" not in source and "write_config" not in source


@native
def test_history_lifecycle_native_observations(tmp_path: Path) -> None:
    """Runs only the new native case. Pins what build 8afa's own SessionDB APIs did to one
    synthetic image tool-call/result pair; if native behavior differs this fails and the fixture
    is not bent."""
    evidence = tmp_path / "evidence"
    report = fx.run_parent(fx.DEFAULT_NATIVE_SRC, fx.HISTORY_SCENARIOS, evidence)
    assert report["native_head_matches_expected"] and report["source_unchanged"]
    assert report["native_tree_clean_before"] and report["native_tree_clean_after"]
    assert set(report["source_fingerprints"]) == set(fx.OWNING_FILES + fx.HISTORY_EXTRA_FILES)
    sc = report["scenarios"]["history_lifecycle"]
    # Unchanged guard contracts.
    assert sc["status"] == "COMPLETED" and sc["child_exit_code"] == 0
    assert all(sc["isolation"].values())
    identity = sc["runtime_identity"]
    assert all(identity["native_modules_from_independent_src"].values())
    assert identity["native_modules_from_independent_src"]["hermes_state"] is True
    assert identity["modules_from_real_hermes_home_outside_interpreter_base"] == 0
    assert sc["scratch_removed"] and not sc["child_stderr_mentions_scratch"]
    assert sc["child_stdout_bytes"] == 0 and sc["child_stderr_bytes"] == 0
    assert sc["network"] == {
        "ip_connects_blocked": 0,
        "unix_contacts_blocked": 0,
        "loopback_synthetic_connects_allowed": 0,
    }
    # Evidence files: private, fresh, raw synthetic text only in the 0600 private file.
    assert oct(evidence.stat().st_mode & 0o777) == "0o700"
    for entry in evidence.iterdir():
        assert oct(entry.stat().st_mode & 0o777) == "0o600", entry.name
    private = (evidence / "history_lifecycle.private.json").read_text()
    public = (evidence / "report.json").read_text() + json.dumps(report)
    assert "synthetic request one" in private
    for raw in ("synthetic request", "synthetic prompt", fx.FINAL_TEXT, "synthetic_history_0001"):
        assert raw not in public
    steps = sc["steps"]
    assert not [k for k, v in steps.items() if isinstance(v, dict) and v.get("status")]

    def keys_and_numbers(node: Any, found: set[str]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                found.add(key)
                keys_and_numbers(value, found)
        elif isinstance(node, list):
            for value in node:
                keys_and_numbers(value, found)

    public_keys: set[str] = set()
    keys_and_numbers(report, public_keys)
    keys_and_numbers(json.loads((evidence / "report.json").read_text()), public_keys)
    assert "dev_ino" not in public_keys and "st_ino" not in public_keys
    identity_private = json.loads(private)["restore_file_identity"]
    for stage in ("at_snapshot", "later", "after_restore_fresh_handle"):
        dev, ino = identity_private[stage]
        assert isinstance(dev, int) and isinstance(ino, int) and ino > 0
        assert f"[{dev}, {ino}]" not in public and f'"{ino}"' not in public
        assert "dev_ino" not in steps["backup_restore"][stage]["file"]
    assert identity_private["at_snapshot"] == identity_private["after_restore_fresh_handle"]
    assert steps["cache_file_is_synthetic_png"] and steps["cache_file_unchanged_after_all_steps"]
    assert steps["native_sources"].keys() == set(fx.OWNING_FILES + fx.HISTORY_EXTRA_FILES)

    base = steps["baseline"]
    assert base["view"]["pair_active"]["complete"] and len(base["seeded_ids"]) == 4
    assert base["view"]["carriers_all_rows"] == {
        "assistant_rows_with_call": 1,
        "tool_rows_with_call_id": 1,
    }
    assert base["default_read_equals_active_rows"]

    full = steps["compaction_full_tail_clone"]
    assert full["facts"]["old_pair_flags"] == [[False, False], [False, False]]
    assert (
        full["facts"]["fresh_active_pair_rows"] == 2
        and full["facts"]["fresh_ids_above_previous_max"]
    )
    assert full["facts"]["fresh_pair_identities_equal_old"] is True
    assert full["facts"]["inactive_rows_reactivated"] == 0
    assert full["view"]["pair_active"]["complete"]
    assert full["view"]["carriers_all_rows"] == {
        "assistant_rows_with_call": 2,
        "tool_rows_with_call_id": 2,
    }
    assert full["tip_id_unchanged_while_active_ids_changed"]

    half = steps["compaction_half_tail_clone"]
    assert half["facts"]["old_pair_flags"] == [[False, True], [False, False]]
    assert half["view"]["pair_active"]["active_assistant_rows_with_call"] == 0
    assert half["view"]["pair_active"]["active_tool_rows_with_call_id"] == 1
    assert not half["view"]["pair_active"]["complete"]
    assert half["view"]["carriers_all_rows"] == {
        "assistant_rows_with_call": 1,
        "tool_rows_with_call_id": 2,
    }

    archive = steps["replace_messages_archive"]
    assert archive["diverging"]["facts"]["old_pair_flags"] == [[False, False], [False, False]]
    assert not archive["diverging"]["view"]["pair_active"]["complete"]
    assert archive["identical_prefix"]["original_ids_still_active"] == [True] * 4
    assert archive["identical_prefix"]["view"]["pair_active"]["complete"]
    assert archive["identical_prefix"]["facts"]["fresh_active_rows"] == 1

    delete = steps["replace_messages_delete"]
    assert delete["old_row_ids_still_present_in_audit_read"] == []
    assert delete["pair_carriers_after_replace"] == {
        "assistant_rows_with_call": 0,
        "tool_rows_with_call_id": 0,
    }
    assert not delete["reappended_pair_active_ids_reuse_deleted_ids"]
    assert (
        delete["reappended_identities_equal_deleted"]
        and delete["after_reappend"]["pair_active"]["complete"]
    )

    rewind = steps["rewind"]
    assert rewind["rewind_to_first_user"]["rewound_count"] == 6
    assert rewind["rewind_to_first_user"]["counts"]["rewind_count"] == 1
    assert rewind["rewind_to_first_user"]["facts"]["old_pair_flags"] == [
        [False, False],
        [False, False],
    ]
    assert (
        rewind["rewind_to_first_user"]["view"]["carriers_all_rows"]["tool_rows_with_call_id"] == 1
    )
    assert rewind["rewind_to_second_user"]["pair_survives"]
    assert rewind["rewind_to_second_user"]["pair_ids_unchanged"]

    for label, missing in (
        ("result_row", "active_tool_rows_with_call_id"),
        ("call_row", "active_assistant_rows_with_call"),
    ):
        deact = steps["deactivate_message"][label]
        assert deact["first_returned"] == 1 and deact["second_returned"] == 1
        assert (
            deact["view"]["pair_active"][missing] == 0
            and not deact["view"]["pair_active"]["complete"]
        )

    clear = steps["clear_messages"]
    assert clear["rows_after_clear_audit_read"] == 0 and not clear["reseeded_ids_reuse_cleared_ids"]
    assert clear["reseeded_pair_complete"] and clear["reseeded_identities_equal_cleared"]

    child = steps["child_compression"]
    assert child["tip_before_publish_is_parent"] and child["fresh_tip_is_child"]
    assert child["compression_tip_matches"] and child["parent_end_reason"] == "compression"
    assert child["parent_rows_unchanged_after_publish"] and child["stale_tip_pair_still_active"]
    assert child["fresh_tip_pair_active"] and child["stale_and_fresh_active_ids_disjoint"]

    branch = steps["branch"]
    desktop = branch["desktop_persist_branch"]
    assert desktop["tool_rows_copied"] == 1 and desktop["tool_call_id_columns_copied"] == 0
    assert desktop["assistant_call_columns_copied"] == 0
    assert not desktop["view"]["pair_active"]["complete"]
    assert branch["gateway_branch_row_helper_via_public_api"]["view"]["pair_active"]["complete"]
    assert branch["parent_resume_unchanged_by_branch_children"]
    assert branch["branched_from_marker_on_desktop_child"]

    imported = steps["import"]
    for label in ("same_profile_root", "with_parent_edge", "foreign_path", "non_string_image"):
        item = imported[label]
        assert item["import_ok"] and item["imported"] == 1 and item["errors"] == 0, label
        assert item["ids_disjoint_from_source"] and item["image_value_stored_verbatim"], label
    assert imported["same_profile_root"]["view"]["pair_active"]["complete"]
    assert not imported["foreign_path"]["image_in_selected_profile_cache"]
    assert not imported["non_string_image"]["image_in_selected_profile_cache"]
    assert not imported["foreign_path"]["view"]["pair_active"]["complete"]
    assert imported["resume_selector_follows_imported_parent_edge_child"]
    assert not imported["compression_tip_follows_imported_parent_edge_child"]
    assert imported["imported_session_source_and_origin"] == {
        "source_preserved": True,
        "origin_json_empty": True,
    }

    restore = steps["backup_restore"]
    assert restore["snapshot_copied"] and restore["restore_returned"]
    assert restore["same_inode_and_device"] and restore["inode_unchanged_across_later_and_restore"]
    assert (
        restore["pair_active_at_snapshot"]
        and not restore["pair_active_after_later_compaction_original_ids"]
    )
    assert restore["pair_active_after_restore_original_ids"]
    assert (
        restore["restored_views_equal_snapshot_views"]
        and restore["restored_views_differ_from_later_views"]
    )
    assert restore["conversation_generation"] == {
        "at_snapshot": None,
        "later": 1,
        "after_restore": None,
    }
    assert restore["rewind_count_rs_c"] == {"at_snapshot": 0, "later": 1, "after_restore": 0}
    assert (
        restore["file_stamp_unchanged_by_restore"]
        and restore["application_id_unchanged_by_restore"]
    )
    assert restore["old_handle_converges_with_fresh_handle"]
    assert restore["old_handle_reports_file_replaced"] is False
    assert restore["old_handle_write_after_restore"] == {"ok": True}
    assert restore["id_taken_after_restore_was_used_in_later_timeline"]
    assert restore["later_timeline_max_id_above_snapshot_max"]

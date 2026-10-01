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
    assert fx.ALL_SCENARIOS == fx.SCENARIOS + fx.MODERN_SCENARIOS
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

"""Tests for tools/research/local_media_persistence_fixture.py (G1 persistence characterization).

Unit tests need no native build. The `native` test runs all five scenarios once against the pinned
independent build and skips when it is absent (local-only, like the other build-bound fixture
tests). All data is synthetic; only closed metadata is asserted.
"""

from __future__ import annotations

import ast
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
# Lexical image-prefix evidence (distinct from the older Path(parent) comparison)
# --------------------------------------------------------------------------------------------

HOME_A = "/scratch/hermes/profiles/alpha"
HOME_B = "/scratch/hermes/profiles/beta"
PREFIX_A = fx.lexical_prefix(HOME_A)
PREFIX_B = fx.lexical_prefix(HOME_B)


def _observe(raw: object, selected: str | None = PREFIX_A) -> dict[str, object]:
    return fx.lexical_image_observation(raw, selected, PREFIX_B)


def test_lexical_prefix_is_plain_string_concatenation() -> None:
    assert PREFIX_A == HOME_A + "/cache/images/"
    assert fx.lexical_prefix(Path(HOME_A)) == PREFIX_A
    assert fx.lexical_prefix("relative/home") is None
    assert fx.lexical_prefix(object()) is None
    assert fx.lexical_prefix(None) is None


def test_lexical_accepts_exact_prefix_with_one_flat_name() -> None:
    result = _observe(PREFIX_A + "g1synth_1234.png")
    assert result["accepted"] is True
    assert result["starts_with_selected_prefix"] is True
    assert result["starts_with_other_prefix"] is False
    assert result["suffix_is_single_flat_bounded_name"] is True
    assert set(result) >= {"raw_sha256", "expected_prefix_sha256"}
    assert "scratch" not in repr({k: v for k, v in result.items() if k.endswith("sha256")})


@pytest.mark.parametrize(
    "raw",
    [
        # prefix spelling mismatches
        "/scratch/hermes/profiles/alpha/cache/images" + "g1.png",  # missing separator
        "/scratch/hermes/profiles/alpha//cache/images/g1.png",  # doubled separator
        "/scratch//hermes/profiles/alpha/cache/images/g1.png",
        "/scratch/hermes/./profiles/alpha/cache/images/g1.png",
        "/scratch/hermes/profiles/alpha/../alpha/cache/images/g1.png",
        "/scratch/hermes/profiles/alpha/cache/images/./g1.png",
        "/SCRATCH/hermes/profiles/alpha/cache/images/g1.png",  # case
        "scratch/hermes/profiles/alpha/cache/images/g1.png",  # relative
        "/private/scratch/hermes/profiles/alpha/cache/images/g1.png",  # symlink-resolved spelling
        "/scratch/hermes/profiles/alpha/cache/images/",  # empty name
        "/scratch/hermes/profiles/alpha/cache",
        "",
    ],
)
def test_lexical_refuses_prefix_spelling_mismatch(raw: str) -> None:
    assert _observe(raw)["accepted"] is False


@pytest.mark.parametrize(
    "suffix",
    [
        "sub/g1.png",  # nested
        "a/b/c.png",
        "../g1.png",
        "..",
        ".",
        "g1.png/",
        "back\\slash.png",
        "nul\x00.png",
        "ctl\n.png",
        "x" * 129,
    ],
)
def test_lexical_refuses_nested_or_unbounded_suffix(suffix: str) -> None:
    result = _observe(PREFIX_A + suffix)
    assert result["starts_with_selected_prefix"] is True
    assert result["suffix_is_single_flat_bounded_name"] is False
    assert result["accepted"] is False


def test_lexical_suffix_bound_is_pinned_to_frozen_leaf_literal() -> None:
    # frozen local_media_file_safety.MAX_NAME_BYTES / spec 011; raising the bound must fail here
    assert fx.LEXICAL_MAX_NAME_BYTES == 128


def test_lexical_suffix_bound_is_inclusive() -> None:
    assert _observe(PREFIX_A + "x" * 128)["accepted"] is True
    assert _observe(PREFIX_A + "x" * 129)["accepted"] is False
    # bound counts encoded bytes, not characters: 64 x 2 bytes = 128 accepted, 65 refused
    assert _observe(PREFIX_A + "é" * 64)["accepted"] is True
    assert _observe(PREFIX_A + "é" * 65)["accepted"] is False


def test_lexical_refuses_foreign_profile_image() -> None:
    result = _observe(PREFIX_B + "g1.png")
    assert result["accepted"] is False
    assert result["starts_with_selected_prefix"] is False
    assert result["starts_with_other_prefix"] is True


def test_lexical_never_normalizes_to_accept(tmp_path: Path) -> None:
    real = tmp_path / "home"
    (real / "cache" / "images").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(real)
    selected = fx.lexical_prefix(str(real))
    # a symlink spelling and a dot-dot spelling resolve to the same directory but are refused
    assert (
        fx.lexical_image_observation(str(link / "cache/images/g.png"), selected, None)["accepted"]
        is False
    )
    dotted = f"{real}/cache/../cache/images/g.png"
    assert os.path.realpath(dotted) == os.path.realpath(f"{real}/cache/images/g.png")
    assert fx.lexical_image_observation(dotted, selected, None)["accepted"] is False
    assert fx.lexical_image_observation(f"{real}/cache/images/g.png", selected, None)["accepted"]


@pytest.mark.parametrize("raw", [None, 5, b"/x", ["/x"]])
def test_lexical_non_string_raw_is_not_accepted(raw: object) -> None:
    assert _observe(raw)["accepted"] is False


def test_lexical_missing_expected_prefix_is_a_gap_not_a_pass() -> None:
    result = fx.lexical_image_observation(PREFIX_A + "g.png", None, PREFIX_B)
    assert result["accepted"] is False and result["prefix_available"] is False


def test_lexical_does_not_use_the_raw_value_to_derive_the_expectation() -> None:
    source = Path(fx.__file__).read_text()
    start = source.index("def lexical_image_observation")
    body = source[start : source.index("def native_lexical_prefixes")]
    for forbidden in ("resolve(", "normpath", "realpath", "abspath", "Path("):
        assert forbidden not in body


def test_native_prefix_helper_failure_is_a_recorded_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    # No native import is possible in this interpreter: the gap is recorded, never guessed.
    monkeypatch.setitem(sys.modules, "gateway.run", None)
    result = fx.native_lexical_prefixes()
    assert result["gap"] and result["gap"].startswith("helper_error:")
    assert result["selected"] is None and result["other"] is None


def test_native_prefix_helper_sentinel_is_a_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    sentinel = object()
    runner = types.SimpleNamespace(_routed_profile_home=staticmethod(lambda name: sentinel))
    module = types.ModuleType("gateway.run")
    module.GatewayRunner = runner  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gateway.run", module)
    result = fx.native_lexical_prefixes()
    assert result["gap"] == "helper_result_not_absolute_path"
    assert result["selected"] is None


def test_native_prefix_helper_matches_bridge_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    homes = {fx.PROFILE: Path(HOME_A), fx.OTHER_PROFILE: Path(HOME_B)}
    runner = types.SimpleNamespace(_routed_profile_home=staticmethod(lambda name: homes[name]))
    module = types.ModuleType("gateway.run")
    module.GatewayRunner = runner  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gateway.run", module)
    result = fx.native_lexical_prefixes()
    assert result["gap"] is None
    assert result["selected"] == PREFIX_A and result["other"] == PREFIX_B
    assert result["bridge_shape_equals_native_str"] and result["homes_differ"]


@native
def test_lexical_evidence_positive_scenarios(tmp_path: Path) -> None:
    scenarios = ("desktop", "phone", "desktop_deferred")
    report = fx.run_parent(fx.DEFAULT_NATIVE_SRC, scenarios, tmp_path / "evidence")
    assert report["source_unchanged"] and report["native_tree_clean_after"]
    for name in scenarios:
        sc = report["scenarios"][name]
        assert sc["status"] == "COMPLETED", name
        assert sc["lexical_helper"]["gap"] is None, name
        assert sc["lexical_helper"]["bridge_shape_equals_native_str"], name
        assert sc["lexical_helper"]["homes_differ"], name
        lexical = sc["rows_alpha_db"]["tool_row_meta"][0]["lexical"]
        assert lexical["accepted"] and lexical["starts_with_selected_prefix"], name
        assert not lexical["starts_with_other_prefix"], name
        assert lexical["suffix_is_single_flat_bounded_name"], name

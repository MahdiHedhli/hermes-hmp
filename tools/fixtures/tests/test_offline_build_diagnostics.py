"""`direct_send_fixture.build_offline`: scoped child environment and closed, private failure
reporting (specs/005 amendment 4). Pure unit tests: the real child here is a stub script, never a
Hermes build, gateway, model or network."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import direct_send_fixture as dsf
import pytest

SECRET = "sk-synthetic-ambient-secret-value"
BUILD_OK = {"ok": True, "build": "b", "instances": [{"profiles": [{"name": "default"}]}]}


def _stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    script = tmp_path / "stub_build.py"
    script.write_text(body, encoding="utf-8")
    monkeypatch.setattr(dsf, "BUILD_FIXTURE", script)


def _ambient(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPENAI_API_KEY", "CODEX_HOME", "HERMES_HOME", "XDG_STATE_HOME", "HMP_BROWSER_KEY",
        "HMP_DIRECT_SEND_QUALIFICATION", "HMP_APPROVAL_QUALIFICATION",
    ):
        monkeypatch.setenv(name, SECRET)


LEAK_PROBE = (
    "import os, sys, json\n"
    "leaked = sorted(k for k, v in os.environ.items() if 'synthetic-ambient' in v)\n"
    "kept = {k: os.environ[k] for k in ('HMP_HERMES_BUILDS_DIR', 'PYTHONDONTWRITEBYTECODE')"
    " if k in os.environ}\n"
    "sys.stderr.write('LEAKED=' + ','.join(leaked) + ' KEPT=' + json.dumps(kept))\n"
    "sys.exit(1)\n"
)


def test_success_parses_the_offline_build_json(tmp_path, monkeypatch) -> None:
    _stub(tmp_path, monkeypatch, f"import json; print(json.dumps({BUILD_OK!r}))\n")
    monkeypatch.delenv("HMP_DIRECT_SEND_QUALIFICATION", raising=False)
    monkeypatch.delenv("HMP_APPROVAL_QUALIFICATION", raising=False)
    info = dsf.build_offline("b", tmp_path / "out", builds_dir=str(tmp_path))
    assert info == BUILD_OK
    assert not (tmp_path / "out" / dsf.BUILD_FAILURE_OUTPUT).exists()


def test_child_env_is_the_allowlist_plus_explicit_controls(tmp_path, monkeypatch) -> None:
    _ambient(monkeypatch)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    env = dsf.offline_build_env(str(tmp_path))
    assert set(env) <= set(dsf.BUILD_ENV_ALLOWLIST) | {"HMP_HERMES_BUILDS_DIR"}
    assert env["HMP_HERMES_BUILDS_DIR"] == str(tmp_path)
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "PATH" in env
    assert SECRET not in "".join(env.values())


def test_real_child_never_sees_ambient_secrets_and_keeps_controls(tmp_path, monkeypatch) -> None:
    _ambient(monkeypatch)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    _stub(tmp_path, monkeypatch, LEAK_PROBE)
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError):
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    text = (out / dsf.BUILD_FAILURE_OUTPUT).read_text(encoding="utf-8")
    assert "LEAKED= " in text  # nothing leaked into the child
    assert '"PYTHONDONTWRITEBYTECODE": "1"' in text and str(tmp_path) in text


def test_failure_is_closed_private_and_not_retried(tmp_path, monkeypatch) -> None:
    _ambient(monkeypatch)
    calls: list[dict] = []
    real_run = subprocess.run

    def counting_run(args, **kw):
        calls.append(kw)
        return real_run(args, **kw)

    _stub(
        tmp_path, monkeypatch,
        "import sys\nprint('native-stdout-marker')\nsys.stderr.write('native-stderr-marker')\n"
        "sys.exit(7)\n",
    )
    monkeypatch.setattr(dsf.subprocess, "run", counting_run)
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    exc = caught.value
    message = str(exc)
    assert "phase=build_offline" in message and "exit_code=7" in message
    assert "private_output=retained" in message
    for forbidden in ("native-", SECRET, str(tmp_path), str(dsf.BUILD_FIXTURE), "--build"):
        assert forbidden not in message
    assert exc.__cause__ is None and exc.__suppress_context__
    assert len(calls) == 1 and calls[0]["check"] is False
    kept = out / dsf.BUILD_FAILURE_OUTPUT
    assert stat.S_IMODE(kept.stat().st_mode) == 0o600
    assert stat.S_IMODE(out.stat().st_mode) == 0o700  # created by us, private
    raw = kept.read_text(encoding="utf-8")
    assert "native-stdout-marker" in raw and "native-stderr-marker" in raw


def test_output_is_capped_to_the_tail(tmp_path, monkeypatch) -> None:
    _stub(
        tmp_path, monkeypatch,
        "import sys\nsys.stderr.write('A' * 200000 + 'TAIL-END')\nsys.exit(1)\n",
    )
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError):
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    data = (out / dsf.BUILD_FAILURE_OUTPUT).read_bytes()
    assert len(data) < dsf.BUILD_FAILURE_STREAM_CAP + 300
    assert data.rstrip().endswith(b"TAIL-END")
    assert b"200008 bytes" in data


def test_symlinked_out_is_not_followed(tmp_path, monkeypatch) -> None:
    _stub(tmp_path, monkeypatch, "import sys\nsys.stderr.write('boom')\nsys.exit(1)\n")
    target = tmp_path / "elsewhere"
    target.mkdir(mode=0o700)
    out = tmp_path / "out"
    out.symlink_to(target)
    _refused(tmp_path, out, monkeypatch)
    assert list(target.iterdir()) == []


def test_preexisting_symlink_at_the_file_name_is_not_followed(tmp_path, monkeypatch) -> None:
    _stub(tmp_path, monkeypatch, "import sys\nsys.stderr.write('boom')\nsys.exit(1)\n")
    out = tmp_path / "out"
    out.mkdir(mode=0o700)
    victim = tmp_path / "victim.txt"
    victim.write_text("keep", encoding="utf-8")
    (out / dsf.BUILD_FAILURE_OUTPUT).symlink_to(victim)
    out_fd = dsf._open_private_output_dir(out)
    assert out_fd is not None
    try:
        retained = dsf._retain_build_failure_output(out_fd, b"x", b"y")
        assert retained == "not_retained_unsafe_destination"
    finally:
        os.close(out_fd)
    assert victim.read_text(encoding="utf-8") == "keep"


def test_group_or_other_writable_out_is_not_used(tmp_path, monkeypatch) -> None:
    _stub(tmp_path, monkeypatch, "import sys\nsys.stderr.write('boom')\nsys.exit(1)\n")
    out = tmp_path / "out"
    out.mkdir()
    os.chmod(out, 0o777)  # noqa: S103 - the hostile mode under test
    _refused(tmp_path, out, monkeypatch)
    assert stat.S_IMODE(out.stat().st_mode) == 0o777
    assert list(out.iterdir()) == []


def _failing_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int = 1) -> None:
    _stub(tmp_path, monkeypatch, f"import sys\nsys.stderr.write('boom')\nsys.exit({code})\n")


def _refused(tmp_path: Path, out: Path, monkeypatch: pytest.MonkeyPatch | None = None) -> str:
    calls: list[int] = []
    real_run = subprocess.run
    if monkeypatch is not None:
        monkeypatch.setattr(
            dsf.subprocess, "run", lambda *a, **k: calls.append(1) or real_run(*a, **k)
        )
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    message = str(caught.value)
    assert "phase=build_offline_destination" in message and str(tmp_path) not in message
    assert caught.value.__cause__ is None
    if monkeypatch is not None:
        assert calls == []  # zero child calls
    return message


def test_symlinked_ancestor_is_refused_and_the_destination_is_unchanged(
    tmp_path, monkeypatch
) -> None:
    _failing_stub(tmp_path, monkeypatch)
    real = tmp_path / "real"
    (real / "out").mkdir(parents=True, mode=0o700)
    (tmp_path / "link").symlink_to(real)
    _refused(tmp_path, tmp_path / "link" / "out", monkeypatch)
    assert list((real / "out").iterdir()) == []


def test_symlinked_ancestor_with_absent_leaf_creates_nothing(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    (tmp_path / "link").symlink_to(real)
    _refused(tmp_path, tmp_path / "link" / "out", monkeypatch)
    assert list(real.iterdir()) == []  # the leaf was not created through the link


def test_missing_parent_is_not_created_and_nothing_is_written(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    _refused(tmp_path, tmp_path / "absent-parent" / "out", monkeypatch)
    assert not (tmp_path / "absent-parent").exists()


def test_dotdot_component_is_refused(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    (tmp_path / "a").mkdir(mode=0o700)
    (tmp_path / "out").mkdir(mode=0o700)
    _refused(tmp_path, tmp_path / "a" / ".." / "out", monkeypatch)
    assert list((tmp_path / "out").iterdir()) == []


def test_existing_nonprivate_out_is_left_unchanged_and_unused(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    os.chmod(out, 0o755)  # noqa: S103 - non-private mode under test
    _refused(tmp_path, out, monkeypatch)
    assert stat.S_IMODE(out.stat().st_mode) == 0o755  # final 0755 refused, never chmod-ed
    assert list(out.iterdir()) == []


def test_group_other_writable_nonsticky_ancestor_is_refused(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    parent = tmp_path / "shared"
    out = parent / "out"
    out.mkdir(parents=True, mode=0o700)
    os.chmod(parent, 0o777)  # noqa: S103 - writable ancestor under test
    _refused(tmp_path, out, monkeypatch)
    assert stat.S_IMODE(parent.stat().st_mode) == 0o777  # never chmod-ed
    assert list(out.iterdir()) == []
    assert dsf._open_private_output_dir(parent / "fresh") is None
    assert not (parent / "fresh").exists()


def test_foreign_owned_ancestor_is_refused(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    parent = tmp_path / "foreign"
    out = parent / "out"
    out.mkdir(parents=True, mode=0o700)
    parent_ino = parent.stat().st_ino
    real_fstat = os.fstat

    def fstat(fd):
        st = real_fstat(fd)
        if st.st_ino == parent_ino:
            fields = list(st)
            fields[4] = os.geteuid() + 1  # st_uid: neither root nor us
            return os.stat_result(fields)
        return st

    monkeypatch.setattr(dsf.os, "fstat", fstat)
    _refused(tmp_path, out, monkeypatch)
    assert list(out.iterdir()) == []


def test_ancestor_trust_rules_for_the_shared_temp_base_only() -> None:
    def meta(mode: int, uid: int) -> os.stat_result:
        return os.stat_result((mode, 1, 1, 1, uid, 0, 0, 0, 0, 0))

    sticky = stat.S_IFDIR | 0o1777
    assert dsf._ancestor_is_trusted(meta(sticky, 0), "/private/tmp")
    assert dsf._ancestor_is_trusted(meta(sticky, 0), "/tmp")  # noqa: S108
    assert not dsf._ancestor_is_trusted(meta(sticky, os.geteuid() + 1), "/private/tmp")
    assert not dsf._ancestor_is_trusted(meta(stat.S_IFDIR | 0o777, 0), "/private/tmp")
    # hostile: an arbitrary sticky world-writable directory is not trusted, even root-owned
    for path in ("/private/var/tmp", "/private/tmp/evil", "/srv/shared"):
        assert not dsf._ancestor_is_trusted(meta(sticky, 0), path)
        assert not dsf._ancestor_is_trusted(meta(sticky, os.geteuid()), path)
    assert dsf._ancestor_is_trusted(meta(stat.S_IFDIR | 0o755, 0), "/private")
    assert dsf._ancestor_is_trusted(meta(stat.S_IFDIR | 0o700, os.geteuid()), "/home/x")
    assert not dsf._ancestor_is_trusted(meta(stat.S_IFDIR | 0o775, os.geteuid()), "/home/x")


@pytest.mark.skipif(not os.path.isdir("/tmp"), reason="no /tmp")  # noqa: S108
def test_real_root_sticky_tmp_base_is_a_valid_ancestor() -> None:
    root = Path(tempfile.mkdtemp(dir="/tmp", prefix="hmp-diag-sticky-"))
    try:
        os.chmod(root, 0o700)
        fd = dsf._open_private_output_dir(root / "out")
        assert fd is not None
        os.close(fd)
        (root / "out").rmdir()
    finally:
        root.rmdir()


def test_existing_target_file_is_unchanged(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    out = tmp_path / "out"
    out.mkdir(mode=0o700)
    (out / dsf.BUILD_FAILURE_OUTPUT).write_text("keep", encoding="utf-8")
    out_fd = dsf._open_private_output_dir(out)
    assert out_fd is not None
    try:
        retained = dsf._retain_build_failure_output(out_fd, b"x", b"y")
        assert retained == "not_retained_unsafe_destination"
    finally:
        os.close(out_fd)
    assert (out / dsf.BUILD_FAILURE_OUTPUT).read_text(encoding="utf-8") == "keep"


@pytest.mark.skipif(
    not os.path.islink("/tmp"),  # noqa: S108
    reason="no /tmp platform alias on this host",
)
def test_the_known_tmp_alias_is_normalized_but_is_not_a_general_resolver() -> None:
    tmp_alias = "/tmp"  # noqa: S108 - the platform alias under test
    root = Path(tempfile.mkdtemp(dir=tmp_alias, prefix="hmp-diag-alias-"))
    try:
        os.chmod(root, 0o700)
        fd = dsf._open_private_output_dir(Path(tmp_alias) / root.name / "out")
        assert fd is not None
        os.close(fd)
        assert stat.S_IMODE((root / "out").stat().st_mode) == 0o700
        (root / "alias").symlink_to(root / "out")
        assert dsf._open_private_output_dir(root / "alias") is None
        assert dsf._open_private_output_dir(root / "alias" / "x") is None
    finally:
        for child in (root / "out", root / "alias"):
            if child.is_symlink():
                child.unlink()
            elif child.exists():
                child.rmdir()
        root.rmdir()


def test_write_failure_is_closed_keeps_the_native_failure_and_leaves_no_file(
    tmp_path, monkeypatch
) -> None:
    _failing_stub(tmp_path, monkeypatch, code=7)
    real_write = os.write

    def failing_write(fd, data):
        if bytes(data).startswith(b"== stdout"):
            raise OSError(28, "/private/leaky/path RAW-WRITE-ERROR")
        return real_write(fd, data)

    monkeypatch.setattr(dsf.os, "write", failing_write)
    calls: list[int] = []
    real_run = subprocess.run
    monkeypatch.setattr(
        dsf.subprocess, "run", lambda *a, **k: calls.append(1) or real_run(*a, **k)
    )
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    message = str(caught.value)
    assert "phase=build_offline" in message and "exit_code=7" in message
    assert "private_output=not_retained_write_failed" in message
    for forbidden in ("RAW-WRITE", "leaky", str(tmp_path), "boom"):
        assert forbidden not in message
    assert caught.value.__cause__ is None and caught.value.__suppress_context__
    assert len(calls) == 1  # no retry
    assert list(out.iterdir()) == []  # the incomplete file was removed


def test_close_failure_is_closed_too(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch, code=9)
    real_close = os.close

    def failing_close(fd):
        is_file = stat.S_ISREG(os.fstat(fd).st_mode)
        real_close(fd)
        if is_file:
            raise OSError(5, "/private/leaky/path RAW-CLOSE-ERROR")

    monkeypatch.setattr(dsf.os, "close", failing_close)
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    message = str(caught.value)
    assert "exit_code=9" in message and "private_output=not_retained_write_failed" in message
    assert "RAW-CLOSE" not in message and "leaky" not in message
    assert caught.value.__cause__ is None
    assert list(out.iterdir()) == []


def test_zero_progress_write_is_closed_bounded_and_keeps_the_native_exit(
    tmp_path, monkeypatch
) -> None:
    _failing_stub(tmp_path, monkeypatch, code=6)
    monkeypatch.setattr(dsf.os, "write", lambda fd, data: 0)
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    message = str(caught.value)
    assert "exit_code=6" in message and "private_output=not_retained_write_failed" in message
    assert list(out.iterdir()) == []


def test_owned_dir_fd_close_failure_does_not_replace_the_native_failure(
    tmp_path, monkeypatch
) -> None:
    _failing_stub(tmp_path, monkeypatch, code=8)
    real_close, real_run = os.close, subprocess.run
    armed: list[int] = []

    def failing_close(fd):
        is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
        real_close(fd)
        if armed and is_dir:
            raise OSError(5, "/private/leaky/path RAW-DIRCLOSE-ERROR")

    def run(*a, **k):
        result = real_run(*a, **k)
        armed.append(1)
        return result

    monkeypatch.setattr(dsf.os, "close", failing_close)
    monkeypatch.setattr(dsf.subprocess, "run", run)
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", tmp_path / "out", builds_dir=str(tmp_path))
    message = str(caught.value)
    assert "exit_code=8" in message and "private_output=retained" in message
    assert "RAW-DIRCLOSE" not in message and "leaky" not in message and str(tmp_path) not in message
    assert caught.value.__cause__ is None


def test_fresh_private_destination_is_still_created_and_used(tmp_path, monkeypatch) -> None:
    _failing_stub(tmp_path, monkeypatch)
    out = tmp_path / "fresh"
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    assert "private_output=retained" in str(caught.value)
    assert stat.S_IMODE(out.stat().st_mode) == 0o700
    assert (out / dsf.BUILD_FAILURE_OUTPUT).is_file()


def test_cleanup_never_unlinks_a_different_file_at_the_name(tmp_path, monkeypatch) -> None:
    out = tmp_path / "out"
    out.mkdir(mode=0o700)
    dir_fd = dsf._open_private_output_dir(out)
    assert dir_fd is not None
    victim = out / dsf.BUILD_FAILURE_OUTPUT

    def swap_then_fail(fd, data):
        victim.unlink()  # someone replaces the name after our create
        victim.write_text("not ours", encoding="utf-8")
        raise OSError(28, "no space")

    monkeypatch.setattr(dsf.os, "write", swap_then_fail)
    try:
        assert dsf._retain_build_failure_output(dir_fd, b"x", b"y") == "not_retained_write_failed"
    finally:
        monkeypatch.undo()
        os.close(dir_fd)
    assert victim.read_text(encoding="utf-8") == "not ours"


def test_unparseable_success_is_closed_and_the_body_is_not_in_the_error(
    tmp_path, monkeypatch
) -> None:
    _stub(tmp_path, monkeypatch, "print('CHILD-BODY-MARKER not json')\n")
    monkeypatch.delenv("HMP_DIRECT_SEND_QUALIFICATION", raising=False)
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    message = str(caught.value)
    assert "phase=build_offline_output exit_code=0" in message
    assert "CHILD-BODY-MARKER" not in message and caught.value.__cause__ is None
    assert "CHILD-BODY-MARKER" in (out / dsf.BUILD_FAILURE_OUTPUT).read_text(encoding="utf-8")


def _inner_pytest_report(tmp_path: Path, name: str, test_body: str) -> str:
    inner = tmp_path / name
    inner.mkdir()
    (inner / "test_inner.py").write_text(test_body, encoding="utf-8")
    env = {
        "PATH": os.environ["PATH"],
        "PYTHONPATH": os.pathsep.join(p for p in sys.path if p),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--rootdir", str(inner),
         "--tb=long", str(inner / "test_inner.py")],
        cwd=inner, env=env, capture_output=True, text=True, check=False,
    )
    return run.stdout + run.stderr


def test_real_pytest_failure_report_does_not_carry_the_child_body(tmp_path) -> None:
    stub = tmp_path / "stub.py"
    stub.write_text("print('CHILD-BODY-MARKER not json')\n", encoding="utf-8")
    header = (
        "import json, direct_send_fixture as dsf\nfrom pathlib import Path\n"
        f"dsf.BUILD_FIXTURE = Path({str(stub)!r})\n"
    )
    # Control: json.loads of the body (the old shape) DOES print it in pytest's long report, so
    # this harness can see a leak; the fixed build_offline must not.
    control = header + "def test_x():\n    json.loads('CHILD-BODY-MARKER not json')\n"
    assert "CHILD-BODY-MARKER" in _inner_pytest_report(tmp_path, "control", control)
    out = tmp_path / "o"
    fixed = header + f"def test_x():\n    dsf.build_offline('b', Path({str(out)!r}))\n"
    report = _inner_pytest_report(tmp_path, "fixed", fixed)
    assert "FixtureSafetyError" in report and "phase=build_offline_output" in report
    assert "CHILD-BODY-MARKER" not in report

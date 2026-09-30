"""Issue #24: `hermes hmp compat report --matrix <receipt>`.

Every value is synthetic. No real `gh`, network, Hermes install or Hermes home is touched: identity,
the committed list, the clock, the `gh` executable and the one subprocess call are injected.

The receipt is the format-1 *candidate* receipt of the ad-hoc compatibility matrix (a separate
tooling branch). These tests pin the interface this side consumes.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from hmp_plugin import cli, compat, compat_report
from hmp_plugin.compat import BuildEntry, BuildIdentity

# The writer's ten checks, spelled out literally so a change to `compat_report.CHECKS` is caught.
WRITER_CHECKS = (
    "clone_commit_matches",
    "extraction_metadata_valid",
    "extraction_metadata_commit_matches",
    "interpreter_matches",
    "source_fingerprint_matches",
    "selfcheck_passed",
    "read_suite_passed",
    "sc007_passed",
    "sc007_bound_to_candidate",
    "source_unchanged_after_run",
)
SHA = "b" * 40
FP = "a" * 64
HMP_SHA = "c" * 40
IDENTITY = BuildIdentity(fingerprint=FP, git_sha=SHA)
GH = "/usr/local/bin/gh"
LOGIN = "octo-operator"
NOW = int(datetime(2026, 9, 30, 12, 0, 0, tzinfo=UTC).timestamp())
DAY = 24 * 3600
SECRETS = (
    "/fake-account/private",
    "alice-laptop.local",
    "ghp_SECRETTOKEN0123456789",
    "Traceback (most recent call last)",
    "src-label-private",
)
ISSUE_URL = f"https://github.com/{compat_report.REPORT_REPO}/issues/24"
API_ARGV = [GH, "api", "--hostname", "github.com", "--method", "GET", "user", "--jq", ".login"]


def stamp(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Tty(io.StringIO):
    def __init__(self, text: str = "", tty: bool = True) -> None:
        super().__init__(text)
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class InterruptedStdin(Tty):
    def readline(self, *_args: Any) -> str:
        raise KeyboardInterrupt


class TypedAheadStdin(Tty):
    """A terminal with `ahead` typed before the disclosure was shown and `after` typed once the
    prompt is up. `discard` is what the real `tcflush` does: it empties `ahead` and nothing else."""

    def __init__(self, ahead: str, after: str = "") -> None:
        super().__init__("", tty=True)
        self.ahead, self.after, self.discarded = ahead, after, False

    def discard(self) -> None:
        self.ahead, self.discarded = "", True

    def readline(self, *_args: Any) -> str:
        text, self.ahead, self.after = self.ahead + self.after, "", ""
        return text.splitlines(keepends=True)[0] if text else ""


def good_receipt() -> dict[str, Any]:
    return {
        "format": 1,
        "mode": "candidate",
        "generated_at": stamp(NOW - DAY),
        "hmp_source": {"commit": HMP_SHA, "version": "1.0.0-f1", "worktree_dirty": False},
        "matrix_runtime": {"os": "Linux", "python": "3.11"},
        "candidate": {
            "label": "candidate",
            "commit": SHA,
            "python_requested": "3.11",
            "fingerprint": FP,
        },
        "checks": dict.fromkeys(WRITER_CHECKS, True),
        "read_suite_tests_run": 412,
        "sc007": {
            "label": "candidate",
            "ran": True,
            "ok": True,
            "status": "unsupported",
            "why": "hermes_build_unsupported",
            "bridge_imported": False,
        },
        "failed_stage": None,
        "candidate_passed": True,
        "runtime_dependencies": {"aiohttp": "3.9.5", "cryptography": None, "qrcode": "7.4.2"},
        "assurance": "non-adversarial compatibility evidence only; not an attestation",
    }


class FakeGh:
    """Stands in for `default_run_gh`; records argv and the environment it was handed."""

    def __init__(
        self,
        *,
        login_rc: int = 0,
        login_out: str | None = LOGIN + "\n",
        create_rc: int = 0,
        stdout: str = ISSUE_URL,
        login_none: bool = False,
        create_none: bool = False,
        create_raises: BaseException | None = None,
        logins: list[str] | None = None,
        login_raises_at: int | None = None,
    ) -> None:
        self.logins = logins  # one login per `gh api user` call, in order (last one repeats)
        self.login_raises_at = login_raises_at  # 1-based index of the login call that is Ctrl-C'd
        self.login_calls = 0
        self.login_rc, self.login_out, self.login_none = login_rc, login_out, login_none
        self.create_rc, self.stdout = create_rc, stdout
        self.create_none, self.create_raises = create_none, create_raises
        self.calls: list[list[str]] = []
        self.environs: list[Any] = []
        self.body_seen: str | None = None
        self.body_mode: int | None = None
        self.body_path: Path | None = None

    def __call__(
        self, argv: list[str], *, timeout: float, environ: Any
    ) -> subprocess.CompletedProcess[str] | None:
        assert isinstance(argv, list) and timeout > 0
        self.calls.append(argv)
        self.environs.append(environ)
        if argv[1] == "api":
            self.login_calls += 1
            if self.login_raises_at == self.login_calls:
                raise KeyboardInterrupt
            if self.login_none:
                return None
            if self.logins:
                login = self.logins[min(self.login_calls, len(self.logins)) - 1]
                return subprocess.CompletedProcess(argv, 0, login + "\n", "")
            return subprocess.CompletedProcess(argv, self.login_rc, self.login_out, "")
        self.body_path = Path(argv[argv.index("--body-file") + 1])
        self.body_seen = self.body_path.read_text(encoding="utf-8")
        self.body_mode = stat.S_IMODE(self.body_path.stat().st_mode)
        if self.create_raises is not None:
            raise self.create_raises
        if self.create_none:  # e.g. the timeout killed gh
            return None
        # A failing `gh` may echo the body it was given; that must never reach the operator.
        stderr = self.body_seen if self.create_rc else ""
        return subprocess.CompletedProcess(argv, self.create_rc, self.stdout, stderr)

    def created(self) -> bool:
        return any(call[1:3] == ["issue", "create"] for call in self.calls)


class Harness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        receipt: object | bytes | None = None,
        answer: str = "REPORT\n",
        identity: BuildIdentity | None = IDENTITY,
        builds: tuple[BuildEntry, ...] = (),
        gh: FakeGh | None = None,
        gh_path: str | None = GH,
        version: str | None = "1.0.0-f1",
        tty: bool = True,
        environ: dict[str, str] | None = None,
        mode: int = 0o600,
    ) -> None:
        self.tmp = tmp_path
        self.can_discard = True
        self.shown_at_discard: str | None = None
        self.matrix = tmp_path / "matrix.json"
        if isinstance(receipt, bytes):
            self.matrix.write_bytes(receipt)
        else:
            self.matrix.write_text(
                json.dumps(good_receipt() if receipt is None else receipt), encoding="utf-8"
            )
        self.matrix.chmod(mode)
        self.gh = gh if gh is not None else FakeGh()
        self.out = Tty(tty=tty)
        self.err = io.StringIO()
        self.identity_calls = 0
        self.temp_dir = tmp_path / "scratch"
        self.temp_dir.mkdir()

        def read_identity() -> BuildIdentity | None:
            self.identity_calls += 1
            return identity

        self.env = cli.CliEnv(
            environ={"PATH": "/usr/bin", "HOME": "/home/op", **(environ or {})},
            stdin=Tty(answer, tty=tty),
            stdout=self.out,
            stderr=self.err,
            clock=lambda: NOW,
            report_identity=read_identity,
            report_builds=lambda: builds,
            hmp_version=lambda: version,
            gh_executable=lambda: gh_path,
            run_gh=self.gh,
            discard_input=self.discard_input,
            report_temp_dir=self.temp_dir,
        )

    def discard_input(self, stdin: Any, stdout: Any) -> bool:
        """Records what was on screen when pending input was dropped."""
        self.shown_at_discard = stdout.getvalue()
        if isinstance(stdin, TypedAheadStdin):
            stdin.discard()
        return self.can_discard

    def run(self) -> int:
        args = argparse.Namespace(
            hmp_command="compat", compat_command="report", matrix=str(self.matrix)
        )
        return cli.dispatch(args, self.env)

    def assert_nothing_leaked(self) -> None:
        text = self.out.getvalue() + self.err.getvalue() + repr(self.gh.calls)
        for secret in SECRETS:
            assert secret not in text
        assert list(self.temp_dir.iterdir()) == []


def committed_lists_digest() -> str:
    digest = hashlib.sha256()
    package = Path(compat.__file__).parent
    for path in sorted(package.glob("*_builds.json")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def listed(identity: BuildIdentity) -> BuildEntry:
    return BuildEntry(
        fingerprint=identity.fingerprint,
        git_sha=identity.git_sha,
        label="listed",
        qualified_by="test",
        qualified_at="2026-09-01",
    )


# ---------------------------------------------------------------------------------------------
# Positive path: what is printed is exactly what is sent
# ---------------------------------------------------------------------------------------------


def test_consent_sends_the_exact_printed_body_through_a_gh_argument_list(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    assert h.run() == cli.EXIT_OK

    expected = {
        "advisory": compat_report.REPORT_ADVISORY,
        "hermes_git_sha": SHA,
        "read_bridge_fingerprint": FP,
        "hmp_version": "1.0.0-f1",
        "matrix_hmp_source_sha": HMP_SHA,
        "receipt_generated_at": stamp(NOW - DAY),
        "read_suite_tests_run": 412,
        "stages": dict.fromkeys(WRITER_CHECKS, "pass"),
        "matrix_os": "Linux",
        "matrix_python": "3.11",
    }
    body = f"```json\n{json.dumps(expected, indent=2, sort_keys=True)}\n```\n"
    assert h.gh.body_seen == body
    assert body.startswith("```json\n") and body.endswith("\n```\n")

    printed = h.out.getvalue()
    assert f"----- begin issue body -----\n{body}----- end issue body -----\n" in printed
    assert "MahdiHedhli/hermes-hmp" in printed and '"HMP compatibility report"' in printed
    assert f"{LOGIN}\n" in printed
    assert "unverified" in printed and "not an attestation" in printed
    # destination, login and the whole body come before the consent prompt
    prompt = printed.index("Type REPORT")
    assert printed.index("MahdiHedhli/hermes-hmp") < prompt
    assert printed.index(LOGIN) < prompt < printed.index("Report sent")
    assert printed.index("hermes_git_sha") < prompt

    login, relogin, create = h.gh.calls  # the login is read again after consent, before create
    assert login == relogin == API_ARGV
    assert create == [
        GH, "issue", "create", "--repo", "MahdiHedhli/hermes-hmp", "--title",
        "HMP compatibility report", "--body-file", str(h.gh.body_path),
    ]
    assert all(environ is h.env.environ for environ in h.gh.environs)  # one environment throughout
    assert h.gh.body_mode == 0o600
    assert h.gh.body_path is not None and not h.gh.body_path.exists()
    assert f"Report sent: {ISSUE_URL}" in printed
    assert h.err.getvalue() == ""
    h.assert_nothing_leaked()


def test_payload_marks_the_report_unverified_and_never_claims_attestation() -> None:
    payload = compat_report.build_report(
        good_receipt(), IDENTITY, version="1.0.0-f1", builds=(), now=NOW
    )
    advisory = payload["advisory"]
    assert advisory.startswith("unverified") and "not an attestation" in advisory
    assert payload["matrix_hmp_source_sha"] == HMP_SHA
    assert not {"attested", "verified", "signature"} & set(payload)


def test_unrecognized_gh_output_is_never_echoed(tmp_path: Path) -> None:
    h = Harness(tmp_path, gh=FakeGh(stdout="https://evil.example/x ghp_SECRETTOKEN0123456789"))
    assert h.run() == cli.EXIT_OK
    assert "Report sent (gh succeeded but printed no recognizable issue URL)" in h.out.getvalue()
    h.assert_nothing_leaked()


# ---------------------------------------------------------------------------------------------
# The matrix's OS and Python are reported, never the CLI host's
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("runtime", "expected"),
    [
        ({"os": "Linux", "python": "3.11"}, ("Linux", "3.11")),
        ({"os": "Darwin", "python": "3.9.6"}, ("macOS", "3.9")),
        ({"os": "macOS", "python": "3.14.0"}, ("macOS", "3.14")),
        ({"os": "other", "python": "3.10"}, ("other", "3.10")),
        ({"os": "Windows", "python": "3.12"}, ("Windows", "3.12")),
        # `platform.system()` is "" when undetermined, which the writer emits as null
        ({"os": None, "python": "3.11"}, ("other", "3.11")),
        ({"os": "FreeBSD", "python": "3.11"}, ("other", "3.11")),
        ({"os": "CYGWIN_NT-10.0-19045", "python": "3.11"}, ("other", "3.11")),
    ],
)
def test_matrix_runtime_is_reported_not_the_cli_host(
    runtime: dict[str, str], expected: tuple[str, str]
) -> None:
    receipt = good_receipt()
    receipt["matrix_runtime"] = runtime
    payload = compat_report.build_report(
        receipt, IDENTITY, version="1.0.0-f1", builds=(), now=NOW
    )
    assert (payload["matrix_os"], payload["matrix_python"]) == expected
    assert "os" not in payload and "python" not in payload
    assert not hasattr(cli.CliEnv, "report_host")  # the CLI host is not an input at all
    assert "FreeBSD" not in json.dumps(payload) and "CYGWIN" not in json.dumps(payload)


# ---------------------------------------------------------------------------------------------
# Leak prevention
# ---------------------------------------------------------------------------------------------


def test_payload_never_copies_receipt_or_host_state(tmp_path: Path) -> None:
    receipt = good_receipt()
    receipt["candidate"]["python_requested"] = "3.11"
    h = Harness(tmp_path, receipt=receipt, environ={"OPENAI_API_KEY": "sk-secretvalue"})
    assert h.run() == cli.EXIT_OK
    body = h.gh.body_seen or ""
    assert set(json.loads(body.removeprefix("```json\n").removesuffix("\n```\n"))) == {
        "advisory", "hermes_git_sha", "read_bridge_fingerprint", "hmp_version",
        "matrix_hmp_source_sha", "receipt_generated_at", "read_suite_tests_run", "stages",
        "matrix_os", "matrix_python",
    }
    for secret in (*SECRETS, "sk-secretvalue"):
        assert secret not in body
    h.assert_nothing_leaked()


def test_gh_environment_is_an_allowlist_and_pins_github_com() -> None:
    env = compat_report._gh_env(
        {
            "PATH": "/usr/bin", "HOME": "/h", "GH_TOKEN": "t", "LC_ALL": "C",
            "OPENAI_API_KEY": "secret", "HERMES_HOME": "/h/.hermes", "GH_HOST": "evil.example",
            "GH_REPO": "someone/else", "GH_ENTERPRISE_TOKEN": "x", "GH_DEBUG": "api",
            "GH_PAGER": "evil", "PAGER": "less", "GIT_SSH_COMMAND": "evil", "GH_FORCE_TTY": "1",
        }
    )
    assert env == {
        "PATH": "/usr/bin", "HOME": "/h", "GH_TOKEN": "t", "LC_ALL": "C", "GH_HOST": "github.com",
        "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1",
    }


def test_gh_environment_forwards_keyring_proxy_and_certificate_settings() -> None:
    needed = {
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "XDG_RUNTIME_DIR": "/run/user/1000",
        "SSL_CERT_DIR": "/etc/ssl/certs",
        "SSL_CERT_FILE": "/etc/ssl/cert.pem",
        "HTTP_PROXY": "http://proxy:3128", "http_proxy": "http://proxy:3128",
        "HTTPS_PROXY": "http://proxy:3128", "https_proxy": "http://proxy:3128",
        "ALL_PROXY": "socks5://proxy:1080", "all_proxy": "socks5://proxy:1080",
        "NO_PROXY": "localhost", "no_proxy": "localhost",
    }
    env = compat_report._gh_env({**needed, "AWS_SECRET_ACCESS_KEY": "s", "GH_DEBUG": "1"})
    assert {k: v for k, v in env.items() if k in needed} == needed
    assert "AWS_SECRET_ACCESS_KEY" not in env and "GH_DEBUG" not in env
    assert env["GH_HOST"] == "github.com"


def test_default_runner_uses_argument_list_without_shell_or_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def fake_run(argv: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(argv=argv, **kwargs)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(compat_report.subprocess, "run", fake_run)
    compat_report.default_run_gh([GH, "api", "user"], timeout=3, environ={"PATH": "/bin"})
    assert seen["argv"] == [GH, "api", "user"]
    assert not seen.get("shell", False)
    assert seen["stdin"] is subprocess.DEVNULL and seen["timeout"] == 3
    assert seen["env"]["GH_HOST"] == "github.com"

    def boom(*_a: Any, **_k: Any) -> None:
        raise subprocess.TimeoutExpired("gh", 1)

    monkeypatch.setattr(compat_report.subprocess, "run", boom)
    assert compat_report.default_run_gh([GH], timeout=1, environ={}) is None


# ---------------------------------------------------------------------------------------------
# Refusals: only the exact candidate receipt is accepted; nothing shown as an offer, nothing sent
# ---------------------------------------------------------------------------------------------


def _mutated(mutate: Any) -> dict[str, Any]:
    receipt = copy.deepcopy(good_receipt())
    mutate(receipt)
    return receipt


REFUSED_RECEIPTS: dict[str, dict[str, Any]] = {
    # shape and mode
    "wrong format": _mutated(lambda r: r.update(format=2)),
    "format is true": _mutated(lambda r: r.update(format=True)),
    "listing mode": _mutated(lambda r: r.update(mode="listing")),
    "mode absent": _mutated(lambda r: r.pop("mode")),
    "unknown top-level key": _mutated(lambda r: r.update(hostname="alice-laptop.local")),
    "legacy run_matrix shape": {
        "format": 1,
        "results": [{"qualified": True, "fingerprint": FP, "git_sha": SHA}],
        "candidate_entries": [],
    },
    "candidate absent": _mutated(lambda r: r.pop("candidate")),
    "candidate extra key": _mutated(lambda r: r["candidate"].update(path="/fake-account/private")),
    # freshness
    "stale receipt": _mutated(lambda r: r.update(generated_at=stamp(NOW - 7 * DAY - 1))),
    "future receipt": _mutated(lambda r: r.update(generated_at=stamp(NOW + 3600))),
    "offset timestamp": _mutated(lambda r: r.update(generated_at="2026-09-29T12:00:00+00:00")),
    "date only": _mutated(lambda r: r.update(generated_at="2026-09-29")),
    "impossible date": _mutated(lambda r: r.update(generated_at="2026-13-45T25:61:61Z")),
    "timestamp not string": _mutated(lambda r: r.update(generated_at=1_790_000_000)),
    # HMP source
    "dirty hmp source": _mutated(lambda r: r["hmp_source"].update(worktree_dirty=True)),
    "hmp dirtiness missing": _mutated(lambda r: r["hmp_source"].pop("worktree_dirty")),
    "hmp dirtiness unknown": _mutated(lambda r: r["hmp_source"].update(worktree_dirty=None)),
    "hmp dirtiness string": _mutated(lambda r: r["hmp_source"].update(worktree_dirty="false")),
    "hmp source missing": _mutated(lambda r: r.pop("hmp_source")),
    "hmp commit missing": _mutated(lambda r: r["hmp_source"].pop("commit")),
    "hmp commit malformed": _mutated(lambda r: r["hmp_source"].update(commit="C" * 40)),
    "hmp version other": _mutated(lambda r: r["hmp_source"].update(version="0.9.0")),
    # matrix runtime
    "runtime os unknown": _mutated(lambda r: r["matrix_runtime"].update(os="alice-laptop.local")),
    "runtime os empty": _mutated(lambda r: r["matrix_runtime"].update(os="")),
    "runtime os number": _mutated(lambda r: r["matrix_runtime"].update(os=1)),
    "runtime os path": _mutated(lambda r: r["matrix_runtime"].update(os="/fake-account/private")),
    "runtime os lowercase": _mutated(lambda r: r["matrix_runtime"].update(os="linux")),
    "runtime python bad": _mutated(lambda r: r["matrix_runtime"].update(python="latest")),
    "runtime missing": _mutated(lambda r: r.pop("matrix_runtime")),
    # candidate binding
    "candidate label": _mutated(lambda r: r["candidate"].update(label="src-label-private")),
    "candidate commit other": _mutated(lambda r: r["candidate"].update(commit="e" * 40)),
    "candidate commit null": _mutated(lambda r: r["candidate"].update(commit=None)),
    "candidate fingerprint other": _mutated(lambda r: r["candidate"].update(fingerprint="e" * 64)),
    "candidate python_requested": _mutated(
        lambda r: r["candidate"].update(python_requested="/fake-account/private")
    ),
    # top-level verdicts
    "failed stage": _mutated(lambda r: r.update(failed_stage="read_suite")),
    "not passed": _mutated(lambda r: r.update(candidate_passed=False)),
    "passed truthy": _mutated(lambda r: r.update(candidate_passed=1)),
    "no tests ran": _mutated(lambda r: r.update(read_suite_tests_run=0)),
    "negative tests": _mutated(lambda r: r.update(read_suite_tests_run=-1)),
    "tests boolean": _mutated(lambda r: r.update(read_suite_tests_run=True)),
    "tests string": _mutated(lambda r: r.update(read_suite_tests_run="412")),
    "tests float": _mutated(lambda r: r.update(read_suite_tests_run=412.0)),
    "tests missing": _mutated(lambda r: r.pop("read_suite_tests_run")),
    "checks extra": _mutated(lambda r: r["checks"].update(bonus=True)),
    "checks old names": _mutated(
        lambda r: r.update(
            checks=dict.fromkeys(
                (
                    "extraction", "commit", "interpreter", "full_source", "selfcheck",
                    "read_suite", "sc007_binding",
                ),
                True,
            )
        )
    ),
    "checks absent": _mutated(lambda r: r.pop("checks")),
    # sc007
    "sc007 absent": _mutated(lambda r: r.pop("sc007")),
    "sc007 label": _mutated(lambda r: r["sc007"].update(label="other")),
    "sc007 not run": _mutated(lambda r: r["sc007"].update(ran=False)),
    "sc007 failed": _mutated(lambda r: r["sc007"].update(ok=False)),
    "sc007 admitted build": _mutated(lambda r: r["sc007"].update(status="supported")),
    "sc007 other reason": _mutated(lambda r: r["sc007"].update(why="other")),
    "sc007 imported bridge": _mutated(lambda r: r["sc007"].update(bridge_imported=True)),
    "sc007 bridge unknown": _mutated(lambda r: r["sc007"].update(bridge_imported=None)),
    "sc007 log tail": _mutated(lambda r: r["sc007"].update(stderr_tail="Traceback")),
    # the writer's commentary fields must be present and well-formed
    "dependencies absent": _mutated(lambda r: r.pop("runtime_dependencies")),
    "dependencies not an object": _mutated(lambda r: r.update(runtime_dependencies=["aiohttp"])),
    "dependency version not text": _mutated(
        lambda r: r["runtime_dependencies"].update(aiohttp=3.9)
    ),
    "dependencies unbounded": _mutated(
        lambda r: r.update(runtime_dependencies={f"p{i}": "1" for i in range(65)})
    ),
    "assurance absent": _mutated(lambda r: r.pop("assurance")),
    "assurance not text": _mutated(lambda r: r.update(assurance=["x"])),
    "assurance unbounded": _mutated(lambda r: r.update(assurance="x" * 2000)),
}
for _name in WRITER_CHECKS:
    for _label, _value in (("false", False), ("truthy", 1), ("string", "true"), ("null", None)):
        REFUSED_RECEIPTS[f"check {_name} {_label}"] = _mutated(
            lambda r, n=_name, v=_value: r["checks"].update({n: v})
        )
    REFUSED_RECEIPTS[f"check {_name} missing"] = _mutated(lambda r, n=_name: r["checks"].pop(n))


@pytest.mark.parametrize("receipt", REFUSED_RECEIPTS.values(), ids=REFUSED_RECEIPTS.keys())
def test_only_the_exact_passing_candidate_receipt_is_accepted(
    tmp_path: Path, receipt: object
) -> None:
    h = Harness(tmp_path, receipt=receipt)
    assert h.run() == cli.EXIT_REFUSED
    assert "compatibility report refused" in h.err.getvalue()
    assert "Type REPORT" not in h.out.getvalue()
    assert h.gh.calls == []
    h.assert_nothing_leaked()


def test_receipt_freshness_boundary_is_seven_days() -> None:
    def build(age: int) -> None:
        receipt = good_receipt()
        receipt["generated_at"] = stamp(NOW - age)
        compat_report.build_report(receipt, IDENTITY, version="1.0.0-f1", builds=(), now=NOW)

    build(7 * DAY)
    build(0)
    build(-compat_report.MAX_CLOCK_SKEW_S)
    for age in (7 * DAY + 1, -compat_report.MAX_CLOCK_SKEW_S - 60):
        with pytest.raises(compat_report.ReportError):
            build(age)
    receipt = good_receipt()
    receipt["generated_at"] = stamp(NOW - 3600).replace("Z", ".123456Z")
    compat_report.build_report(receipt, IDENTITY, version="1.0.0-f1", builds=(), now=NOW)


@pytest.mark.parametrize(
    "receipt",
    [
        b"{not json",
        b"[]",
        b'"a string"',
        b'{"format": 1, "format": 1}',
        b'{"format": 1, "read_suite_tests_run": NaN}',
        b"\xff\xfe",
        b"[" * 100_000,
        b" " * (compat_report.MAX_RECEIPT_BYTES + 1),
    ],
    ids=["syntax", "list", "string", "duplicate-key", "nan", "not-utf8", "deep", "too-large"],
)
def test_malformed_or_oversize_receipt_is_refused(tmp_path: Path, receipt: bytes) -> None:
    h = Harness(tmp_path, receipt=receipt)
    assert h.run() == cli.EXIT_REFUSED
    assert h.gh.calls == []
    h.assert_nothing_leaked()


def test_receipt_that_is_missing_symlinked_or_a_directory_is_refused(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    real = h.matrix
    link = tmp_path / "link.json"
    link.symlink_to(real)
    for target in (tmp_path / "missing.json", link, tmp_path):
        h.matrix = target
        assert h.run() == cli.EXIT_REFUSED
    assert h.gh.calls == []
    assert str(tmp_path) not in h.err.getvalue()


@pytest.mark.parametrize("mode", [0o620, 0o660, 0o602, 0o666, 0o777])
def test_receipt_writable_by_group_or_others_is_refused(tmp_path: Path, mode: int) -> None:
    h = Harness(tmp_path, mode=mode)
    assert h.run() == cli.EXIT_REFUSED
    assert "writable by group or others" in h.err.getvalue()
    assert h.gh.calls == []


@pytest.mark.parametrize("mode", [0o400, 0o600, 0o640, 0o644])
def test_receipt_owned_by_the_user_and_not_writable_by_others_is_accepted(
    tmp_path: Path, mode: int
) -> None:
    h = Harness(tmp_path, mode=mode)
    assert h.run() == cli.EXIT_OK
    assert h.gh.created()


def test_receipt_owned_by_another_user_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = Harness(tmp_path)
    real_uid = compat_report._current_uid()
    monkeypatch.setattr(compat_report, "_current_uid", lambda: real_uid + 1)
    assert h.run() == cli.EXIT_REFUSED
    assert "owned by the current user" in h.err.getvalue()
    assert h.gh.calls == []


# ---------------------------------------------------------------------------------------------
# Host binding: identity, already-listed builds, installed HMP version
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "identity",
    [
        None,
        BuildIdentity(fingerprint=FP, git_sha=None),
        BuildIdentity(fingerprint="f" * 64, git_sha=SHA),
        BuildIdentity(fingerprint=FP, git_sha="f" * 40),
    ],
    ids=["missing", "no-git-sha", "fingerprint-differs", "commit-differs"],
)
def test_missing_or_mismatched_hermes_identity_is_refused(
    tmp_path: Path, identity: BuildIdentity | None
) -> None:
    h = Harness(tmp_path, identity=identity)
    assert h.run() == cli.EXIT_REFUSED
    assert h.gh.calls == []
    h.assert_nothing_leaked()


def test_already_listed_build_is_refused(tmp_path: Path) -> None:
    h = Harness(tmp_path, builds=(listed(IDENTITY),))
    assert h.run() == cli.EXIT_REFUSED
    assert "already listed" in h.err.getvalue()
    assert h.gh.calls == []


def test_other_listed_builds_do_not_block_a_report(tmp_path: Path) -> None:
    other = listed(BuildIdentity(fingerprint="d" * 64, git_sha="d" * 40))
    h = Harness(tmp_path, builds=(other,))
    assert h.run() == cli.EXIT_OK


def test_unreadable_compatibility_list_is_refused(tmp_path: Path) -> None:
    h = Harness(tmp_path)

    def broken() -> tuple[BuildEntry, ...]:
        raise ValueError("private detail /fake-account/private")

    h.env.report_builds = broken
    assert h.run() == cli.EXIT_REFUSED
    assert "/fake-account" not in h.err.getvalue()
    assert h.gh.calls == []


@pytest.mark.parametrize("version", [None, "", "0.9.9", "1.0.0-f2", "1.0 beta", "v" * 40])
def test_installed_hmp_version_must_match_the_receipt(tmp_path: Path, version: str | None) -> None:
    h = Harness(tmp_path, version=version)
    assert h.run() == cli.EXIT_REFUSED
    assert h.gh.calls == []


def test_bundled_manifest_version_is_reportable() -> None:
    assert compat_report.hmp_version() == "1.0.0-f1"
    assert compat_report.hmp_version(Path("/nonexistent/plugin.yaml")) is None


# ---------------------------------------------------------------------------------------------
# Non-interactive and consent gates
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("which", ["stdin", "stdout", "session"])
def test_noninteractive_or_agent_shell_sends_nothing(tmp_path: Path, which: str) -> None:
    h = Harness(tmp_path, environ={"HERMES_SESSION_ID": "x"} if which == "session" else None)
    if which == "stdin":
        h.env.stdin = Tty("REPORT\n", tty=False)
    elif which == "stdout":
        h.env.stdout = Tty(tty=False)
    assert h.run() == cli.EXIT_REFUSED
    assert h.gh.calls == []  # not even the read-only login lookup
    assert h.identity_calls == 0  # refused before reading anything local
    assert "REPORT" not in h.env.stdout.getvalue()


@pytest.mark.parametrize(
    "answer",
    [
        "", "\n", "y\n", "yes\n", "report\n", "Report\n", "REPORT now\n", "REPORTS\n", "REPOR\n",
        "REPORT", "REPORT \n", " REPORT\n", "  REPORT \n", "REPORT\r\n", "\tREPORT\n",
        "REPORT" + " " * 200 + "\n",
    ],
    ids=lambda a: repr(a[:16]),
)
def test_only_report_and_a_newline_is_consent(tmp_path: Path, answer: str) -> None:
    h = Harness(tmp_path, answer=answer)
    assert h.run() == cli.EXIT_OK
    assert not h.gh.created()
    assert "Nothing was sent." in h.out.getvalue()
    assert list(h.temp_dir.iterdir()) == []


def test_exact_report_line_is_consent(tmp_path: Path) -> None:
    h = Harness(tmp_path, answer="REPORT\n")
    assert h.run() == cli.EXIT_OK
    assert h.gh.created()
    assert compat_report.is_consent("REPORT\n")
    assert not compat_report.is_consent("REPORT \n")


def test_interrupt_at_the_prompt_sends_nothing(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.env.stdin = InterruptedStdin()
    assert h.run() == cli.EXIT_INTERRUPTED
    assert not h.gh.created()


def test_interrupt_while_discarding_early_input_sends_nothing(tmp_path: Path) -> None:
    h = Harness(tmp_path)

    def interrupted(_stdin: Any, _stdout: Any) -> bool:
        raise KeyboardInterrupt

    h.env.discard_input = interrupted
    assert h.run() == cli.EXIT_INTERRUPTED
    assert not h.gh.created()
    assert "Nothing was sent" in h.out.getvalue()


@pytest.mark.parametrize("ahead", ["REPORT\n", "REPORT\nREPORT\n", "y\nREPORT\n", "REPORT\r\n"])
def test_consent_typed_or_pasted_before_the_body_was_shown_is_discarded(
    tmp_path: Path, ahead: str
) -> None:
    h = Harness(tmp_path)
    stdin = TypedAheadStdin(ahead)
    h.env.stdin = stdin
    assert h.run() == cli.EXIT_OK
    assert stdin.discarded and not h.gh.created()
    assert "Nothing was sent." in h.out.getvalue()
    # dropped after the complete body was on screen and before the prompt was written
    shown = h.shown_at_discard or ""
    assert shown.endswith("----- end issue body -----\n")
    assert "Type REPORT" not in shown
    assert "Type REPORT" in h.out.getvalue()
    assert h.gh.calls == [API_ARGV]  # only the login lookup; no recheck without consent
    h.assert_nothing_leaked()


def test_consent_typed_after_the_prompt_still_works_and_stale_input_is_ignored(
    tmp_path: Path,
) -> None:
    h = Harness(tmp_path)
    h.env.stdin = TypedAheadStdin(ahead="no\n", after="REPORT\n")
    assert h.run() == cli.EXIT_OK
    assert h.gh.created()


def test_nothing_is_offered_when_pending_input_cannot_be_discarded(tmp_path: Path) -> None:
    h = Harness(tmp_path, answer="REPORT\n")
    h.can_discard = False
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert not h.gh.created() and h.gh.calls == [API_ARGV]
    assert "Type REPORT" not in h.out.getvalue()
    err = h.err.getvalue()
    assert "Report was not sent" in err and "discard" in err
    assert "unconfirmed" not in err.lower()
    h.assert_nothing_leaked()


def test_default_discard_is_wired_to_the_terminal_helper() -> None:
    assert cli.CliEnv().discard_input is cli._default_discard_input
    # a StringIO has no file descriptor, so the real default fails closed rather than trusting it
    assert cli._default_discard_input(io.StringIO("REPORT\n"), io.StringIO()) is False


class _FakeTermios:
    TCIFLUSH = 0
    error = OSError

    def __init__(self, *, fail_flush: bool = False, fail_drain: bool = False) -> None:
        self.calls: list[tuple[str, int]] = []
        self.fail_flush, self.fail_drain = fail_flush, fail_drain

    def tcdrain(self, fd: int) -> None:
        self.calls.append(("tcdrain", fd))
        if self.fail_drain:
            raise OSError

    def tcflush(self, fd: int, queue: int) -> None:
        self.calls.append(("tcflush", fd))
        assert queue == self.TCIFLUSH
        if self.fail_flush:
            raise OSError


class _FdStream(io.StringIO):
    def __init__(self, fd: int) -> None:
        super().__init__()
        self._fd = fd

    def fileno(self) -> int:
        return self._fd


def test_discard_pending_input_drains_output_then_flushes_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeTermios()
    monkeypatch.setitem(sys.modules, "termios", fake)
    assert compat_report.discard_pending_input(_FdStream(7), _FdStream(8)) is True
    assert fake.calls == [("tcdrain", 8), ("tcflush", 7)]


def test_discard_pending_input_still_flushes_when_the_output_is_not_a_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeTermios(fail_drain=True)
    monkeypatch.setitem(sys.modules, "termios", fake)
    assert compat_report.discard_pending_input(_FdStream(7), io.StringIO()) is True
    assert ("tcflush", 7) in fake.calls


def test_discard_pending_input_fails_closed_when_flush_fails_or_there_is_no_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "termios", _FakeTermios(fail_flush=True))
    assert compat_report.discard_pending_input(_FdStream(7), _FdStream(8)) is False
    assert compat_report.discard_pending_input(io.StringIO(), _FdStream(8)) is False  # no fileno
    assert compat_report.discard_pending_input(None, None) is False


def test_discard_pending_input_uses_the_console_where_termios_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Console:
        def __init__(self) -> None:
            self.queued = 3

        def kbhit(self) -> bool:
            return self.queued > 0

        def getwch(self) -> str:
            self.queued -= 1
            return "x"

    console = Console()
    monkeypatch.setitem(sys.modules, "termios", None)  # makes `import termios` fail
    monkeypatch.setitem(sys.modules, "msvcrt", console)
    assert compat_report.discard_pending_input(_FdStream(7), _FdStream(8)) is True
    assert console.queued == 0
    monkeypatch.setitem(sys.modules, "msvcrt", None)  # neither API: cannot discard
    assert compat_report.discard_pending_input(_FdStream(7), _FdStream(8)) is False


# ---------------------------------------------------------------------------------------------
# The effective login is re-read after consent, and Ctrl-C before create is "not sent"
# ---------------------------------------------------------------------------------------------


def test_login_change_after_consent_aborts_before_create(tmp_path: Path) -> None:
    gh = FakeGh(logins=[LOGIN, "someone-else"])
    h = Harness(tmp_path, gh=gh)
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert gh.login_calls == 2 and not gh.created()
    err = h.err.getvalue()
    assert "Report was not sent" in err and LOGIN in err and "someone-else" in err
    assert "unconfirmed" not in err.lower()
    h.assert_nothing_leaked()


@pytest.mark.parametrize(
    "gh",
    [FakeGh(logins=[LOGIN]), FakeGh(logins=[LOGIN, LOGIN, LOGIN])],
    ids=["one-login", "three-logins"],
)
def test_unchanged_login_after_consent_sends(tmp_path: Path, gh: FakeGh) -> None:
    h = Harness(tmp_path, gh=gh)
    assert h.run() == cli.EXIT_OK
    assert gh.created() and gh.login_calls == 2


def test_gh_path_that_changes_after_consent_sends_nothing(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    paths = iter([GH, "/safe/other-gh"])
    h.env.gh_executable = lambda: next(paths)
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert not h.gh.created()
    assert "GitHub CLI changed" in h.err.getvalue()


def test_interrupt_during_gh_path_recheck_sends_nothing(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    calls = 0

    def gh_path() -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return GH

    h.env.gh_executable = gh_path
    assert h.run() == cli.EXIT_INTERRUPTED
    assert not h.gh.created()
    assert "Nothing was sent" in h.out.getvalue()


class _RecheckFails(FakeGh):
    def __call__(self, argv: list[str], *, timeout: float, environ: Any) -> Any:
        if argv[1] == "api" and self.login_calls == 1:  # the second lookup
            self.login_calls += 1
            self.calls.append(argv)
            return None
        return super().__call__(argv, timeout=timeout, environ=environ)


def test_login_that_cannot_be_reread_after_consent_aborts_before_create(tmp_path: Path) -> None:
    gh = _RecheckFails()
    h = Harness(tmp_path, gh=gh)
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert not gh.created()
    assert "Report was not sent" in h.err.getvalue()
    h.assert_nothing_leaked()


def test_interrupt_during_the_preflight_login_lookup_is_not_sent(tmp_path: Path) -> None:
    gh = FakeGh(login_raises_at=1)
    h = Harness(tmp_path, gh=gh)
    assert h.run() == cli.EXIT_INTERRUPTED
    assert not gh.created()
    assert "Nothing was sent" in h.out.getvalue() and "Type REPORT" not in h.out.getvalue()
    assert "Traceback" not in h.err.getvalue() + h.out.getvalue()
    assert "unconfirmed" not in (h.err.getvalue() + h.out.getvalue()).lower()
    h.assert_nothing_leaked()


def test_interrupt_while_reading_local_state_is_not_sent(tmp_path: Path) -> None:
    h = Harness(tmp_path)

    def interrupted() -> None:
        raise KeyboardInterrupt

    h.env.report_identity = interrupted
    assert h.run() == cli.EXIT_INTERRUPTED
    assert h.gh.calls == []
    assert "Nothing was sent" in h.out.getvalue()


def test_interrupt_during_the_login_recheck_is_not_sent(tmp_path: Path) -> None:
    gh = FakeGh(login_raises_at=2)
    h = Harness(tmp_path, gh=gh)
    assert h.run() == cli.EXIT_INTERRUPTED
    assert not gh.created()
    assert "Nothing was sent" in h.out.getvalue()
    h.assert_nothing_leaked()


def test_interrupt_while_preparing_the_body_file_is_not_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(**_kwargs: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(compat_report.tempfile, "mkstemp", interrupted)
    h = Harness(tmp_path)
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert not h.gh.created()
    err = h.err.getvalue()
    assert "Report was not sent" in err and "unconfirmed" not in err.lower()


def test_only_the_read_only_login_lookup_reaches_github_before_consent(tmp_path: Path) -> None:
    h = Harness(tmp_path, answer="no\n")
    assert h.run() == cli.EXIT_OK
    assert h.gh.calls == [API_ARGV]  # no `issue list`/`search` carrying the Hermes SHA
    assert SHA not in "".join(part for call in h.gh.calls for part in call)
    printed = h.out.getvalue()
    assert "did not search for an existing report" in printed
    assert compat_report.REPORT_ISSUES_URL in printed


# ---------------------------------------------------------------------------------------------
# Preflight failures: nothing was sent, and the prompt is never shown
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("gh", "gh_path", "calls"),
    [
        (FakeGh(), None, 0),
        (FakeGh(login_rc=1), GH, 1),
        (FakeGh(login_none=True), GH, 1),
        (FakeGh(login_out=""), GH, 1),
        (FakeGh(login_out="two words\n"), GH, 1),
        (FakeGh(login_out="line1\nline2\n"), GH, 1),
        (FakeGh(login_out="x" * 80), GH, 1),
    ],
    ids=["no-gh", "unauthenticated", "gh-timeout", "empty-login", "spaces", "multiline", "long"],
)
def test_preflight_failure_says_not_sent_and_never_prompts(
    tmp_path: Path, gh: FakeGh, gh_path: str | None, calls: int
) -> None:
    before = committed_lists_digest()
    h = Harness(tmp_path, gh=gh, gh_path=gh_path)
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert len(gh.calls) == calls and not gh.created()
    err = h.err.getvalue()
    assert "Report was not sent" in err and "Compatibility is unchanged" in err
    assert "unconfirmed" not in err.lower()
    assert "Type REPORT" not in h.out.getvalue() and "hermes_git_sha" not in h.out.getvalue()
    assert committed_lists_digest() == before
    h.assert_nothing_leaked()


def test_login_lookup_is_read_only_and_pinned_to_github_com(tmp_path: Path) -> None:
    h = Harness(tmp_path, answer="")
    assert h.run() == cli.EXIT_OK
    assert h.gh.calls == [API_ARGV]
    assert h.gh.environs[0] is h.env.environ


def test_unwritable_temp_directory_is_a_preflight_failure(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.env.report_temp_dir = tmp_path / "missing-dir"
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert not h.gh.created()
    assert "Report was not sent" in h.err.getvalue()
    assert "unconfirmed" not in h.err.getvalue().lower()


# ---------------------------------------------------------------------------------------------
# Failed or unconfirmed create: delivery unconfirmed, never "not sent"
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "gh",
    [
        FakeGh(create_rc=1),
        FakeGh(create_none=True),
        FakeGh(create_raises=RuntimeError("boom ghp_SECRETTOKEN0123456789")),
        FakeGh(create_raises=KeyboardInterrupt()),
        FakeGh(create_raises=subprocess.TimeoutExpired("gh", 30)),
    ],
    ids=["nonzero-exit", "timeout-or-launch-failure", "runner-raised", "interrupt", "timeout"],
)
def test_create_failure_is_delivery_unconfirmed_never_not_sent(tmp_path: Path, gh: FakeGh) -> None:
    before = committed_lists_digest()
    bridge_loaded = "hmp_plugin.bridge" in sys.modules  # a report never imports the bridge
    h = Harness(tmp_path, gh=gh)
    assert h.run() == cli.EXIT_ENVIRONMENT
    assert gh.created()
    err = h.err.getvalue()
    assert "Delivery unconfirmed" in err
    assert compat_report.REPORT_ISSUES_URL in err and LOGIN in err
    assert "before retrying" in err
    lowered = (err + h.out.getvalue()).lower()
    assert "not sent" not in lowered and "nothing was sent" not in lowered
    assert "report sent" not in lowered
    assert "hermes_git_sha" not in err  # the body is never printed on errors
    assert "Compatibility is unchanged" in err
    assert list(h.temp_dir.iterdir()) == []
    assert committed_lists_digest() == before
    assert ("hmp_plugin.bridge" in sys.modules) == bridge_loaded
    h.assert_nothing_leaked()


# ---------------------------------------------------------------------------------------------
# CLI wiring and gh discovery
# ---------------------------------------------------------------------------------------------


def test_parser_requires_a_matrix_and_plain_compat_still_parses() -> None:
    parser = argparse.ArgumentParser()
    cli.setup_parser(parser)
    args = parser.parse_args(["compat", "report", "--matrix", "m.json"])
    assert (args.hmp_command, args.compat_command, args.matrix) == ("compat", "report", "m.json")
    with pytest.raises(SystemExit):
        parser.parse_args(["compat", "report"])
    plain = parser.parse_args(["compat"])
    assert plain.hmp_command == "compat" and plain.compat_command is None


def test_report_refuses_cleanly_without_posix_ownership(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    with mock.patch.object(compat_report, "host_supported", return_value=False):
        assert h.run() == cli.EXIT_ENVIRONMENT
    assert "requires a POSIX host" in h.err.getvalue()
    assert h.identity_calls == 0 and h.gh.calls == []


def test_plain_compat_command_is_unchanged() -> None:
    out = io.StringIO()
    result = compat.CompatResult(compat.CompatStatus.UNSUPPORTED)
    env = cli.CliEnv(stdout=out, stderr=io.StringIO(), compat=lambda: result)
    args = argparse.Namespace(hmp_command="compat", compat_command=None)
    assert cli.dispatch(args, env) == cli.EXIT_OK
    assert "Read compatibility: unsupported" in out.getvalue()


def _make_gh(directory: Path, mode: int = 0o755) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    gh = directory / "gh"
    gh.write_text("#!/bin/sh\n")
    gh.chmod(mode)
    return gh


@pytest.mark.parametrize("where", [".local/bin", "bin"])
def test_gh_in_the_users_own_bin_directory_is_accepted_even_from_the_home_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: str
) -> None:
    home = tmp_path / "home"
    gh = _make_gh(home / where)
    for cwd in (home, home / where, tmp_path):  # the cwd being the home must not matter
        monkeypatch.chdir(cwd)
        path = f"{tmp_path / 'nonexistent'}{os.pathsep}{gh.parent}"
        assert compat_report.locate_gh(path) == str(gh)


def test_gh_symlink_wrapper_runs_by_its_own_name_not_its_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # snap: /snap/bin/gh -> /usr/bin/snap, which dispatches on the name it was run as
    wrapper = _make_gh(tmp_path / "usr-bin").rename(tmp_path / "usr-bin" / "snap")
    (tmp_path / "snap-bin").mkdir()
    link = tmp_path / "snap-bin" / "gh"
    link.symlink_to(wrapper)
    monkeypatch.chdir(tmp_path)
    assert compat_report.locate_gh(str(link.parent)) == str(link)
    assert compat_report.locate_gh(str(link.parent)) != str(wrapper)
    # Homebrew: a symlink into a versioned Cellar directory
    cellar = _make_gh(tmp_path / "Cellar" / "gh" / "2.0" / "bin")
    (tmp_path / "brew-bin").mkdir()
    brew = tmp_path / "brew-bin" / "gh"
    brew.symlink_to(cellar)
    assert compat_report.locate_gh(str(brew.parent)) == str(brew)


def test_gh_missing_is_none_and_never_confused_with_unsafe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "empty").mkdir()
    assert compat_report.locate_gh(str(tmp_path / "empty")) is None
    assert compat_report.locate_gh("") is None
    assert compat_report.locate_gh(None) is None
    assert compat_report.locate_gh(str(tmp_path / "does-not-exist")) is None
    non_executable = _make_gh(tmp_path / "noexec", mode=0o644)
    assert compat_report.locate_gh(str(non_executable.parent)) is None  # not a runnable gh at all


@pytest.mark.parametrize("entry", [".", "", "bin", "./bin", "../elsewhere"])
def test_gh_found_through_a_relative_path_entry_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    cwd = tmp_path / "cwd"
    _make_gh(cwd)
    _make_gh(cwd / "bin")
    _make_gh(tmp_path / "elsewhere")
    monkeypatch.chdir(cwd)
    with pytest.raises(compat_report.SubmitError, match="not a safe executable"):
        compat_report.locate_gh(entry)


def test_a_relative_path_entry_is_not_skipped_in_favour_of_a_later_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_gh(tmp_path / "cwd")
    real = _make_gh(tmp_path / "real")
    monkeypatch.chdir(tmp_path / "cwd")
    with pytest.raises(compat_report.SubmitError, match="not a safe executable"):
        compat_report.locate_gh(f".{os.pathsep}{real.parent}")
    # a relative entry with no `gh` in it is harmless, and the absolute one is used
    (tmp_path / "cwd" / "gh").unlink()
    assert compat_report.locate_gh(f".{os.pathsep}{real.parent}") == str(real)


def test_unsafe_gh_is_refused_and_reported_as_unsafe_not_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    group_writable = _make_gh(tmp_path / "gw", mode=0o775)
    world_writable = _make_gh(tmp_path / "ww", mode=0o757)
    open_dir = _make_gh(tmp_path / "open")
    open_dir.parent.chmod(0o777)
    fine = _make_gh(tmp_path / "fine")
    for unsafe in (group_writable, world_writable, open_dir):
        with pytest.raises(compat_report.SubmitError, match="not a safe executable"):
            compat_report.locate_gh(f"{unsafe.parent}{os.pathsep}{fine.parent}")  # no fall-through
    assert compat_report.locate_gh(str(fine.parent)) == str(fine)
    # owned by somebody else (neither this user nor root)
    other_uid = os.getuid() + 1
    with pytest.raises(compat_report.SubmitError, match="not a safe executable"):
        compat_report.locate_gh(str(fine.parent), uid=other_uid)
    # a symlink to a group-writable target, and a dangling one
    link_dir = tmp_path / "links"
    link_dir.mkdir()
    (link_dir / "gh").symlink_to(group_writable)
    with pytest.raises(compat_report.SubmitError, match="not a safe executable"):
        compat_report.locate_gh(str(link_dir))
    (link_dir / "gh").unlink()
    (link_dir / "gh").symlink_to(tmp_path / "vanished")
    assert compat_report.locate_gh(str(link_dir)) is None  # dangling: not a file, so not found
    loop_dir = tmp_path / "loop"
    loop_dir.mkdir()
    (loop_dir / "gh").symlink_to(loop_dir / "gh")
    assert compat_report.locate_gh(str(loop_dir)) is None


def test_default_gh_executable_reads_the_process_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gh = _make_gh(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(gh.parent))
    assert cli._default_gh_executable() == str(gh)
    monkeypatch.setenv("PATH", "")
    assert cli._default_gh_executable() is None


def test_missing_and_unsafe_gh_are_reported_differently_and_nothing_is_sent(
    tmp_path: Path,
) -> None:
    (tmp_path / "a").mkdir()
    missing = Harness(tmp_path / "a", gh_path=None)
    assert missing.run() == cli.EXIT_ENVIRONMENT
    assert "was not found" in missing.err.getvalue()
    assert "not a safe executable" not in missing.err.getvalue()

    (tmp_path / "b").mkdir()
    unsafe = Harness(tmp_path / "b")

    def refuse() -> str:
        raise compat_report.SubmitError("the GitHub CLI (gh) is found but not a safe executable")

    unsafe.env.gh_executable = refuse
    assert unsafe.run() == cli.EXIT_ENVIRONMENT
    err = unsafe.err.getvalue()
    assert "Report was not sent" in err and "not a safe executable" in err
    assert "not found" not in err and unsafe.gh.calls == []
    assert "Type REPORT" not in unsafe.out.getvalue()


def test_default_builds_are_the_committed_read_list() -> None:
    listed_builds = compat.load_read_compat_list(
        Path(compat.__file__).with_name(compat.READ_COMPAT_FILE)
    ).builds
    assert cli._default_report_builds() == listed_builds


def test_default_identity_reads_files_without_importing_hermes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "hermes"
    root.mkdir()
    read_list = compat.load_read_compat_list(
        Path(compat.__file__).with_name(compat.READ_COMPAT_FILE)
    )
    for rel in read_list.bridge_files:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x = 1\n")
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text(SHA)
    monkeypatch.setattr(compat, "locate_hermes_root", lambda: root)
    identity = cli._default_report_identity()
    assert identity == BuildIdentity(
        fingerprint=compat.compute_read_bridge_fingerprint(root, read_list.bridge_files),
        git_sha=SHA,
    )
    monkeypatch.setattr(compat, "locate_hermes_root", lambda: None)
    assert cli._default_report_identity() is None


def test_checks_are_exactly_the_writers_ten() -> None:
    assert compat_report.CHECKS == WRITER_CHECKS
    assert len(set(WRITER_CHECKS)) == 10


def test_writer_commentary_is_required_but_never_reported() -> None:
    payload = compat_report.build_report(
        good_receipt(), IDENTITY, version="1.0.0-f1", builds=(), now=NOW
    )
    text = json.dumps(payload)
    assert "aiohttp" not in text and "non-adversarial" not in text and "assurance" not in payload


# --- cross-component contract -----------------------------------------------------------------
# The writer (`run_matrix._run_candidate_stages`) is read as text and parsed with `ast`; nothing
# from it is imported or executed, so no candidate code can run here. It is looked for in this
# tree (`tools/compat/run_matrix.py`); `HMP_MATRIX_WRITER` points at another copy, for example a
# separate worktree, and then a missing file or function is a failure, never a skip. The tests
# skip only while this tree has no candidate writer at all (for standalone branch testing);
# a `run_matrix.py` that advertises `--candidate-sha` but has no `_run_candidate_stages` fails.

REPO_ROOT = Path(__file__).resolve().parents[3]
IN_TREE_WRITER = REPO_ROOT / "tools" / "compat" / "run_matrix.py"
WRITER_FUNCTION = "_run_candidate_stages"
_SAFETY_MODULE = ("hermes_builds", "candidate_safety.py")


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    return next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name), None
    )


def _items(node: ast.AST | None) -> dict[str, ast.expr]:
    assert isinstance(node, ast.Dict), "expected a dict literal"
    out: dict[str, ast.expr] = {}
    for key, value in zip(node.keys, node.values, strict=True):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str), "non-literal key"
        assert key.value not in out, f"duplicate key {key.value}"
        out[key.value] = value
    return out


def _dict_assignments(func: ast.FunctionDef, name: str) -> list[ast.Dict]:
    found: list[ast.Dict] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            value: ast.AST | None = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = node.value if node.target.id == name else None
        else:
            continue
        if isinstance(value, ast.Dict):
            found.append(value)
    return found


def _source(node: ast.AST) -> str:
    return ast.unparse(node)


def _expr(code: str) -> str:
    return ast.unparse(ast.parse(code, mode="eval").body)


def _module_regex(tree: ast.Module, name: str) -> re.Pattern[str] | None:
    """The pattern of a top-level `NAME = re.compile("literal")`, without running anything."""
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
            and isinstance(node.value, ast.Call)
            and _source(node.value.func) == "re.compile"
            and node.value.args
            and isinstance(node.value.args[0], ast.Constant)
            and isinstance(node.value.args[0].value, str)
        ):
            return re.compile(node.value.args[0].value)
    return None


def _module_string(tree: ast.Module, name: str) -> str | None:
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return None


class Writer:
    def __init__(self, path: Path, tree: ast.Module, func: ast.FunctionDef) -> None:
        self.path, self.tree, self.func = path, tree, func
        final = func.body[-1]
        assert isinstance(final, ast.Return), f"{WRITER_FUNCTION} no longer ends in its report"
        self.top = _items(final.value)

    def section(self, key: str) -> dict[str, ast.expr]:
        return _items(self.top[key])

    def hmp_source(self) -> dict[str, ast.expr]:
        call = self.top["hmp_source"]
        assert isinstance(call, ast.Call) and _source(call) == "hmp_source_info()"
        info = _find_function(self.tree, "hmp_source_info")
        assert info is not None and isinstance(info.body[-1], ast.Return)
        return _items(info.body[-1].value)

    def safety(self) -> ast.Module | None:
        path = self.path.parent.parent.joinpath(*_SAFETY_MODULE)
        return ast.parse(path.read_text(encoding="utf-8")) if path.is_file() else None


class WriterAbsentError(Exception):
    """This tree really has no candidate writer, so the contract cannot be checked (yet)."""


def locate_writer(override: str | None, default: Path) -> Writer:
    if override:  # an explicit choice must resolve: never a silent skip
        path = Path(override)
        assert path.is_file(), "HMP_MATRIX_WRITER is set but is not a file"
    else:
        path = default
        if not path.is_file():
            raise WriterAbsentError("this tree has no tools/compat/run_matrix.py")
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    func = _find_function(tree, WRITER_FUNCTION)
    if func is None:
        assert not override, f"HMP_MATRIX_WRITER has no {WRITER_FUNCTION}"
        assert "--candidate-sha" not in text, f"{WRITER_FUNCTION} was renamed or moved"
        raise WriterAbsentError("the candidate-receipt writer is not in this tree yet")
    return Writer(path, tree, func)


@pytest.fixture
def writer() -> Writer:
    try:
        return locate_writer(os.environ.get("HMP_MATRIX_WRITER"), IN_TREE_WRITER)
    except WriterAbsentError as exc:
        pytest.skip(f"{exc}; stack the writer branch or set HMP_MATRIX_WRITER")


def test_writer_lookup_skips_only_when_the_writer_is_really_absent(tmp_path: Path) -> None:
    with pytest.raises(WriterAbsentError):
        locate_writer(None, tmp_path / "missing.py")
    listing_only = tmp_path / "run_matrix.py"
    listing_only.write_text("def main():\n    return 0\n", encoding="utf-8")
    with pytest.raises(WriterAbsentError):
        locate_writer(None, listing_only)
    # a candidate-capable script whose writer went missing is a failure, not a skip
    renamed = tmp_path / "renamed.py"
    renamed.write_text('parser.add_argument("--candidate-sha")\n', encoding="utf-8")
    with pytest.raises(AssertionError, match="renamed or moved"):
        locate_writer(None, renamed)
    # an explicit override never skips
    with pytest.raises(AssertionError, match="not a file"):
        locate_writer(str(tmp_path / "nope.py"), listing_only)
    with pytest.raises(AssertionError, match="has no"):
        locate_writer(str(listing_only), listing_only)
    stub = tmp_path / "stub.py"
    stub.write_text(f"def {WRITER_FUNCTION}():\n    return {{'format': 1}}\n", encoding="utf-8")
    assert set(locate_writer(None, stub).top) == {"format"}  # found in-tree by default
    assert set(locate_writer(str(stub), listing_only).top) == {"format"}  # and via the override


def test_the_in_tree_writer_is_looked_up_by_default() -> None:
    assert IN_TREE_WRITER == REPO_ROOT / "tools" / "compat" / "run_matrix.py"
    assert (REPO_ROOT / "server" / "hmp_plugin" / "compat_report.py").is_file()


def test_receipt_keys_match_the_candidate_writer_at_every_level(writer: Writer) -> None:
    receipt = good_receipt()
    assert set(writer.top) == set(receipt) == set(compat_report._TOP_KEYS)
    assert set(writer.hmp_source()) == set(receipt["hmp_source"]) == compat_report._HMP_SOURCE_KEYS
    assert set(writer.section("matrix_runtime")) == set(compat_report._RUNTIME_KEYS)
    assert set(writer.section("candidate")) == set(compat_report._CANDIDATE_KEYS)
    assert set(writer.section("candidate")) == set(receipt["candidate"])
    checks = _dict_assignments(writer.func, "checks")
    assert len(checks) == 1 and list(_items(checks[0])) == list(compat_report.CHECKS)
    assert all(isinstance(v, ast.Constant) and v.value is False for v in _items(checks[0]).values())
    sc007 = _dict_assignments(writer.func, "sc007")  # the initial value and the one after SC-007
    assert sc007 and all(set(_items(d)) == set(compat_report._SC007_KEYS) for d in sc007)
    assert set(receipt["sc007"]) == set(compat_report._SC007_KEYS)


def test_writer_literals_are_what_the_report_accepts(writer: Writer) -> None:
    fmt, mode = writer.top["format"], writer.top["mode"]
    assert isinstance(fmt, ast.Constant) and type(fmt.value) is int
    assert isinstance(mode, ast.Constant) and isinstance(mode.value, str)
    receipt = good_receipt()
    receipt["format"], receipt["mode"] = fmt.value, mode.value  # what the writer would emit
    compat_report.build_report(receipt, IDENTITY, version="1.0.0-f1", builds=(), now=NOW)
    assert (fmt.value, mode.value) == (1, "candidate")

    # a passing run's verdict fields: nothing failed and every check held
    assert _source(writer.top["failed_stage"]) == "failed_stage"
    assert _source(writer.top["candidate_passed"]) == _expr(
        "failed_stage is None and all(checks.values())"
    )
    assert _source(writer.top["read_suite_tests_run"]) == "tests_run"
    assert _source(writer.top["checks"]) == "checks"
    assert _source(writer.top["sc007"]) == "sc007"


def test_writer_candidate_and_sc007_values_are_what_the_report_requires(writer: Writer) -> None:
    candidate = writer.section("candidate")
    assert _source(candidate["label"]) == "CANDIDATE_LABEL"
    assert _source(candidate["commit"]) == "sha"
    assert _source(candidate["fingerprint"]) == "fingerprint"
    assert _source(candidate["python_requested"]) == "python"
    for initial in _dict_assignments(writer.func, "sc007")[:1]:
        values = _items(initial)
        assert _source(values["label"]) == "CANDIDATE_LABEL"
        assert all(_source(values[k]) == "None" for k in ("status", "why", "bridge_imported"))
    final = _items(_dict_assignments(writer.func, "sc007")[-1])
    assert _source(final["ran"]) == "True"
    assert _source(final["ok"]) == _expr('raw.get("ok") is True')
    assert _source(final["status"]) == _expr('_safe_token(raw.get("status"))')
    assert _source(final["why"]) == _expr('_safe_token(raw.get("why"))')
    assert _source(final["label"]) == _expr('raw.get("label")')

    # the SC-007 verdict the writer itself requires, read from its comparisons
    seen = {
        (_source(c.left), _source(c.comparators[0]))
        for c in ast.walk(writer.tree)
        if isinstance(c, ast.Compare) and len(c.ops) == 1
    }
    for left, right in (
        ('parsed.get("status")', '"unsupported"'),
        ('parsed.get("why")', '"hermes_build_unsupported"'),
        ('parsed.get("bridge_imported")', "False"),
        ('raw.get("label")', "CANDIDATE_LABEL"),
    ):
        assert (_expr(left), _expr(right)) in seen

    token = _module_regex(writer.tree, "_TOKEN_RE")
    assert token is not None
    assert token.fullmatch("unsupported") and token.fullmatch("hermes_build_unsupported")
    sc007 = good_receipt()["sc007"]
    assert (sc007["status"], sc007["why"], sc007["bridge_imported"]) == (
        "unsupported", "hermes_build_unsupported", False,
    )

    safety = writer.safety()
    if safety is not None:  # resolved from the sibling module by parsing, never importing
        assert _module_string(safety, "CANDIDATE_LABEL") == good_receipt()["candidate"]["label"]
        sha = _module_regex(safety, "FULL_SHA_RE")
        assert sha is not None
        for sample in ("a" * 40, "A" * 40, "a" * 39, "a" * 41, "g" * 40, "a" * 40 + "\n", ""):
            assert bool(sha.fullmatch(sample)) == bool(compat_report._SHA_RE.fullmatch(sample))


def test_writer_hmp_source_fallbacks_are_refused(writer: Writer) -> None:
    source = writer.hmp_source()
    # an unreadable commit or version is written as None, and unknown dirtiness as True
    for key in ("commit", "version"):
        node = source[key]
        assert isinstance(node, ast.IfExp) and _source(node.orelse) == "None"
    assert _source(source["worktree_dirty"]) == _expr("status is None or bool(status.strip())")
    for key, bad in (("commit", None), ("version", None), ("worktree_dirty", True)):
        receipt = good_receipt()
        receipt["hmp_source"][key] = bad
        with pytest.raises(compat_report.ReportError):
            compat_report.build_report(receipt, IDENTITY, version="1.0.0-f1", builds=(), now=NOW)


def test_writer_timestamp_and_runtime_forms_are_parseable(writer: Writer) -> None:
    stamp = next(
        n for n in ast.walk(writer.func)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "stamp" for t in n.targets)
    )
    assert "astimezone(UTC)" in _source(stamp.value)  # UTC, matching the trailing `Z`
    generated = writer.top["generated_at"]
    assert isinstance(generated, ast.Call) and isinstance(generated.func, ast.Attribute)
    assert _source(generated.func.value) == "stamp" and generated.func.attr == "strftime"
    assert len(generated.args) == 1 and isinstance(generated.args[0], ast.Constant)
    fmt = generated.args[0].value
    assert isinstance(fmt, str)
    sample = datetime.fromtimestamp(NOW - 3600, UTC).strftime(fmt)  # what the writer would emit
    assert compat_report._TIMESTAMP_RE.fullmatch(sample)
    assert compat_report._generated_at(sample, NOW) == sample

    runtime = writer.section("matrix_runtime")
    assert _source(runtime["os"]) == _expr("platform.system() or None")
    assert _source(runtime["python"]) == _expr(
        'f"{sys.version_info.major}.{sys.version_info.minor}"'
    )
    version = sys.version_info
    for system in (None, "Darwin", "Linux", "Windows", "FreeBSD"):  # `platform.system() or None`
        receipt = good_receipt()
        receipt["matrix_runtime"] = {"os": system, "python": f"{version.major}.{version.minor}"}
        payload = compat_report.build_report(
            receipt, IDENTITY, version="1.0.0-f1", builds=(), now=NOW
        )
        assert payload["matrix_python"] == f"{version.major}.{version.minor}"
        assert payload["matrix_os"] in {"macOS", "Linux", "Windows", "other"}

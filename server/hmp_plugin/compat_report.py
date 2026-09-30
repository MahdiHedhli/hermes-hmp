"""Operator-consented compatibility report for an unlisted Hermes build (issue #24).

The report is an advisory data point for HMP maintainers. It never admits a build, never edits a
compatibility list and never imports Hermes or the read bridge. Whether HMP serves a build is
decided only by `compat.CompatGate` against the committed lists.

- **Input.** One local, unsigned, format-1 *candidate* receipt written by the ad-hoc compatibility
  matrix (`mode: candidate`). Nothing else is accepted: not a `run_matrix` listing receipt, not a
  receipt with extra keys. It must be fresh (at most seven days old), free of a dirty HMP source
  tree, owned by this user and not writable by group or others, and every check in it must be
  exactly `true`. Its candidate commit and read-bridge fingerprint must equal this host's Hermes
  identity, that identity must not already be listed, and its HMP source version must equal the
  installed HMP version.
- **What the host match means.** This host's identity is its `.git` HEAD commit plus a hash of the
  read-bridge files as they are on disk. A local edit to a bridge file changes the fingerprint and
  so refuses; a local edit or untracked file anywhere else in the Hermes tree, or an uncommitted
  change that leaves HEAD in place, is covered by neither value. The match says "this commit's
  bridge files", not "this tree is exactly that commit". Likewise the HMP source is compared by
  version only: no installed source SHA exists to compare, so the matrix's HMP source commit is
  reported as claimed, never checked against what is installed.
- **Unverified.** The receipt is self-reported and unsigned. Matching it to this host is a sanity
  gate, not an attestation, and the payload says so in a fixed `advisory` field.
- **Output.** A fixed allowlist: a fixed `advisory` marker, Hermes SHA and read fingerprint (from
  this host, equal to the candidate's), HMP version, the matrix's HMP source commit, the receipt's
  `generated_at`, the read-suite test count, named check results (`stages`), and the *matrix* OS
  family and Python `major.minor` (the CLI host is not reported). Receipt log tails, labels,
  paths, hostnames and every other field are never copied. Each value is re-validated.
- **Sending.** Only through the operator's own authenticated `gh` CLI, to a fixed repository with a
  fixed title, using a 0600 temporary body file and an argument list (never a shell). The exact
  issue body is what is printed and what is sent. Before consent the only thing sent to GitHub is
  one read-only `gh api user`: in particular there is no duplicate search, which would tell GitHub
  the Hermes SHA before the operator agreed (the duplicate check is manual). Failure never changes
  a compatibility gate. A failure before `gh issue create` starts is *not sent*; once it has
  started, the outcome is *delivery unconfirmed*, because a timed-out or failed `gh` may still have
  created the issue.

Importing this module performs no I/O.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import stat
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .compat import BuildEntry, BuildIdentity, match_build

REPORT_REPO = "MahdiHedhli/hermes-hmp"
REPORT_ISSUES_URL = f"https://github.com/{REPORT_REPO}/issues"
REPORT_TITLE = "HMP compatibility report"
REPORT_CONFIRM_WORD = "REPORT"
# The whole consent line, byte for byte: padding, other case and a missing newline are not consent.
REPORT_CONFIRM_LINE = REPORT_CONFIRM_WORD + "\n"
REPORT_ADVISORY = (
    "unverified: unsigned self-reported local receipt, not an attestation; "
    "does not list or qualify any build"
)
MAX_RECEIPT_BYTES = 512_000
MAX_RECEIPT_AGE_S = 7 * 24 * 3600
MAX_CLOCK_SKEW_S = 300
MAX_TESTS_RUN = 10_000_000
GH_TIMEOUT_S = 30.0
MAX_ANSWER_CHARS = 64

# The ten checks the matrix's candidate-receipt writer emits (`run_matrix._run_candidate_stages`),
# exactly and in its order. All must be exactly true; they are reported under the same names.
CHECKS: tuple[str, ...] = (
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
# `runtime_dependencies` and `assurance` are the writer's own commentary (unpinned fixture package
# versions and a fixed disclaimer). They must be present and well-formed, and are never reported.
_TOP_KEYS = frozenset({
    "format", "mode", "generated_at", "hmp_source", "matrix_runtime", "candidate", "checks",
    "read_suite_tests_run", "sc007", "failed_stage", "candidate_passed",
    "runtime_dependencies", "assurance",
})
MAX_COMMENTARY_ITEMS = 64
MAX_COMMENTARY_CHARS = 1024
_HMP_SOURCE_KEYS = frozenset({"commit", "version", "worktree_dirty"})
_RUNTIME_KEYS = frozenset({"os", "python"})
_CANDIDATE_KEYS = frozenset({"label", "commit", "python_requested", "fingerprint"})
_SC007_KEYS = frozenset({"label", "ran", "ok", "status", "why", "bridge_imported"})

_SHA_RE = re.compile(r"[0-9a-f]{40}")
_FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")
_VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,31}")
_PYTHON_RE = re.compile(r"([0-9]{1,2})\.([0-9]{1,2})(?:\.[0-9]{1,3})?")
_PYTHON_REQUEST_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,31}")
_TIMESTAMP_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z"
)
_LOGIN_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
_ISSUE_URL_RE = re.compile(rf"https://github\.com/{re.escape(REPORT_REPO)}/issues/[0-9]{{1,9}}")
_OS_NAMES: Mapping[str, str] = {"Darwin": "macOS", "Linux": "Linux", "Windows": "Windows"}
_REPORT_OS = frozenset({*_OS_NAMES.values(), "other"})
# `platform.system()` values that are not one of the three named families. They are reported as the
# fixed word `other`, never copied; anything not listed here (a hostname, a path) still refuses.
# `platform.system()` is `""` when undetermined, which the matrix writer emits as null.
_OTHER_OS_NAMES = frozenset({
    "FreeBSD", "OpenBSD", "NetBSD", "DragonFly", "SunOS", "AIX", "HP-UX", "Java", "Android", "iOS",
    "Emscripten", "WASI",
})
_OTHER_OS_PREFIXES = ("CYGWIN_NT", "MINGW32_NT", "MINGW64_NT", "MSYS_NT")

# Forwarded to `gh` in place of the full parent environment: the launcher path, the home and config
# locations `gh` reads its own login from, its token variables, and network trust/proxy settings.
# `DBUS_SESSION_BUS_ADDRESS` and `XDG_RUNTIME_DIR` let `gh` reach a Linux desktop keyring, where its
# login usually lives. Debug, pager, repository and host controls (`GH_DEBUG`, `GH_PAGER`, `PAGER`,
# `GH_REPO`, `GH_HOST`, `GH_ENTERPRISE_TOKEN`, ...) are deliberately not forwarded.
_GH_ENV_EXACT: tuple[str, ...] = (
    "PATH", "HOME", "TMPDIR", "LANG", "GH_TOKEN", "GITHUB_TOKEN", "GH_CONFIG_DIR",
    "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS",
    "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy",
    "NO_PROXY", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR",
)


class ReportError(Exception):
    """A safe operator-facing refusal: never carries receipt content, paths or the report body."""


class SubmitError(Exception):
    """A failure before `gh issue create` started: nothing was sent. Never carries `gh` output or
    the report body."""


class DeliveryUnconfirmedError(Exception):
    """`gh issue create` was attempted and did not confirm success. The issue may exist."""


def host_supported() -> bool:
    """This report's owner checks require POSIX uid semantics."""
    return hasattr(os, "getuid")


def hmp_version(manifest: Path | None = None) -> str | None:
    """The plugin manifest's `version:`, or None when it is missing or unrecognizable."""
    path = manifest if manifest is not None else Path(__file__).with_name("plugin.yaml")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.search(r"^version:[ \t]*(\S+)[ \t]*$", text, re.MULTILINE)
    if match is None or _VERSION_RE.fullmatch(match.group(1)) is None:
        return None
    return match.group(1)


def _current_uid() -> int:
    return os.getuid()


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _refuse_constant(_name: str) -> Any:
    raise ValueError("non-finite number")


def read_receipt(path: Path) -> object:
    """Read and parse a bounded receipt from a regular, non-symlink file that this user owns and
    that neither group nor others can write."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise ReportError("cannot read the matrix receipt") from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ReportError("the matrix receipt must be a regular file")
        if info.st_uid != _current_uid():
            raise ReportError("the matrix receipt must be owned by the current user")
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ReportError("the matrix receipt must not be writable by group or others")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(MAX_RECEIPT_BYTES + 1)
    except OSError:
        raise ReportError("cannot read the matrix receipt") from None
    finally:
        os.close(fd)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ReportError("the matrix receipt exceeds the size limit")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicates,
            parse_constant=_refuse_constant,
        )
    except (ValueError, UnicodeError, RecursionError):
        raise ReportError("the matrix receipt is not valid JSON") from None


def _malformed() -> ReportError:
    return ReportError("the matrix receipt is not a well-formed format-1 candidate receipt")


def _section(receipt: Mapping[str, Any], name: str, keys: frozenset[str]) -> Mapping[str, Any]:
    value = receipt.get(name)
    if not isinstance(value, dict) or set(value) != keys:
        raise _malformed()
    return value


def _matches(value: object, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise _malformed()
    return value


def _generated_at(value: object, now: int) -> str:
    text = _matches(value, _TIMESTAMP_RE)
    try:
        moment = datetime.strptime(text.split(".")[0].removesuffix("Z"), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise _malformed() from None
    age = now - moment.replace(tzinfo=UTC).timestamp()
    if age < -MAX_CLOCK_SKEW_S:
        raise ReportError("the matrix receipt is dated in the future")
    if age > MAX_RECEIPT_AGE_S:
        raise ReportError("the matrix receipt is stale (older than 7 days); rerun the matrix")
    return text


def _matrix_runtime(runtime: Mapping[str, Any]) -> tuple[str, str]:
    os_name = runtime["os"]
    if os_name is None or (
        isinstance(os_name, str)
        and (os_name in _OTHER_OS_NAMES or os_name.startswith(_OTHER_OS_PREFIXES))
    ):
        family = "other"  # an undetermined or uncommon platform; the raw value is never copied
    elif isinstance(os_name, str) and (os_name in _REPORT_OS or os_name in _OS_NAMES):
        family = _OS_NAMES.get(os_name, os_name)
    else:
        raise _malformed()
    python = _PYTHON_RE.fullmatch(runtime["python"]) if isinstance(runtime["python"], str) else None
    if python is None:
        raise _malformed()
    return family, f"{python.group(1)}.{python.group(2)}"


def _commentary(dependencies: object, assurance: object) -> None:
    """Shape-check the writer's commentary fields; nothing from them is ever copied."""
    if (
        not isinstance(dependencies, dict)
        or len(dependencies) > MAX_COMMENTARY_ITEMS
        or not all(
            isinstance(name, str)
            and len(name) <= MAX_COMMENTARY_CHARS
            and (value is None or (isinstance(value, str) and len(value) <= MAX_COMMENTARY_CHARS))
            for name, value in dependencies.items()
        )
        or not isinstance(assurance, str)
        or len(assurance) > MAX_COMMENTARY_CHARS
    ):
        raise _malformed()


def build_report(
    receipt: object,
    identity: BuildIdentity | None,
    *,
    version: str | None,
    builds: Sequence[BuildEntry],
    now: int,
) -> dict[str, Any]:
    """The fixed-allowlist payload, or `ReportError`. Nothing is copied from the receipt except
    the validated fields below; the OS and Python reported are the *matrix's*."""
    if identity is None or identity.git_sha is None:
        raise ReportError("this Hermes build has no git SHA and read-bridge fingerprint identity")
    if match_build(identity, builds) is not None:
        raise ReportError("this Hermes build is already listed; there is nothing to report")
    if not isinstance(version, str) or _VERSION_RE.fullmatch(version) is None:
        raise ReportError("the installed HMP version is not reportable")
    if not isinstance(receipt, dict) or set(receipt) != _TOP_KEYS:
        raise _malformed()
    fmt = receipt["format"]
    if type(fmt) is not int or fmt != 1 or receipt["mode"] != "candidate":
        raise _malformed()
    generated_at = _generated_at(receipt["generated_at"], now)

    source = _section(receipt, "hmp_source", _HMP_SOURCE_KEYS)
    source_commit = _matches(source["commit"], _SHA_RE)
    if source["worktree_dirty"] is not False:
        raise ReportError("the matrix ran from a dirty or unknown HMP source tree")
    if _matches(source["version"], _VERSION_RE) != version:
        raise ReportError("the receipt's HMP source version differs from the installed HMP version")
    os_family, python = _matrix_runtime(_section(receipt, "matrix_runtime", _RUNTIME_KEYS))

    candidate = _section(receipt, "candidate", _CANDIDATE_KEYS)
    _matches(candidate["python_requested"], _PYTHON_REQUEST_RE)
    if candidate["label"] != "candidate":
        raise _malformed()
    if (
        _matches(candidate["commit"], _SHA_RE) != identity.git_sha
        or _matches(candidate["fingerprint"], _FINGERPRINT_RE) != identity.fingerprint
    ):
        raise ReportError("the receipt is for a different Hermes build than this host's")

    _commentary(receipt["runtime_dependencies"], receipt["assurance"])
    checks = receipt["checks"]
    if not isinstance(checks, dict) or set(checks) != set(CHECKS):
        raise _malformed()
    tests_run = receipt["read_suite_tests_run"]
    sc007 = _section(receipt, "sc007", _SC007_KEYS)
    passed = (
        all(checks[name] is True for name in CHECKS)
        and type(tests_run) is int
        and 0 < tests_run <= MAX_TESTS_RUN
        and sc007["label"] == "candidate"
        and sc007["ran"] is True
        and sc007["ok"] is True
        and sc007["status"] == "unsupported"
        and sc007["why"] == "hermes_build_unsupported"
        and sc007["bridge_imported"] is False
        and receipt["failed_stage"] is None
        and receipt["candidate_passed"] is True
    )
    if not passed:
        raise ReportError("the matrix receipt shows a check that did not pass")

    stages = dict.fromkeys(CHECKS, "pass")
    return {
        "advisory": REPORT_ADVISORY,
        "hermes_git_sha": identity.git_sha,
        "read_bridge_fingerprint": identity.fingerprint,
        "hmp_version": version,
        "matrix_hmp_source_sha": source_commit,
        "receipt_generated_at": generated_at,
        "read_suite_tests_run": tests_run,
        "stages": stages,
        "matrix_os": os_family,
        "matrix_python": python,
    }


def issue_body(payload: Mapping[str, Any]) -> str:
    """The whole issue body: the payload in a code fence, and nothing else. This exact string is
    printed before consent and is what `gh` receives."""
    return f"```json\n{json.dumps(payload, indent=2, sort_keys=True)}\n```\n"


def is_consent(answer: str) -> bool:
    """`REPORT` and a newline, byte for byte. Padding, case changes and EOF are not consent."""
    return answer == REPORT_CONFIRM_LINE


def _gh_env(environ: Mapping[str, str]) -> dict[str, str]:
    out = {name: environ[name] for name in _GH_ENV_EXACT if name in environ}
    out.update({name: value for name, value in environ.items() if name.startswith("LC_")})
    out.update(GH_HOST="github.com", GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1")
    return out


def default_run_gh(
    argv: list[str], *, timeout: float, environ: Mapping[str, str]
) -> subprocess.CompletedProcess[str] | None:
    """THE `gh` subprocess call: fixed argv list, no shell, no stdin, bounded time, allowlisted
    environment. `None` when it cannot start or times out."""
    try:
        return subprocess.run(  # noqa: S603 - fixed argv list, shell=False, no interpolation
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_gh_env(environ),
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _is_safe_gh(candidate: Path, uid: int) -> bool:
    """A `gh` that may be run: what it resolves to is a regular file owned by this user or root and
    not writable by group or others, and its directory is owned by this user or root and not
    world-writable. A symlink (Homebrew, snap) is fine because the *unresolved* path is what runs,
    so a wrapper that dispatches on its own name keeps working."""
    try:
        target = candidate.resolve(strict=True).stat()
        directory = candidate.parent.stat()
    except (OSError, RuntimeError):  # RuntimeError: a symlink loop on older Pythons
        return False
    if not stat.S_ISREG(target.st_mode) or target.st_uid not in (uid, 0):
        return False
    if target.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return False
    return directory.st_uid in (uid, 0) and not directory.st_mode & stat.S_IWOTH


def locate_gh(path_env: str | None, *, uid: int | None = None) -> str | None:
    """The absolute path of the `gh` the operator's shell would run, or None when there is none.

    Walks `PATH` in order like a shell and judges the first executable `gh` it meets: a relative or
    empty entry (the current directory) is refused, so a `gh` planted beside the operator cannot
    stand in, and an absolute one is accepted wherever it lives (`~/.local/bin`, `~/bin`, a snap or
    Homebrew symlink) as long as `_is_safe_gh` holds. Raises `SubmitError` (nothing sent) for an
    unsafe `gh`, so "not installed" and "installed but refused" are never confused. The path is
    absolute and unresolved; the same walk never falls through to a later, different `gh`."""
    if path_env is None:
        return None
    user = _current_uid() if uid is None else uid
    for entry in path_env.split(os.pathsep):
        candidate = os.path.join(entry, "gh")
        if not (os.path.isfile(candidate) and os.access(candidate, os.X_OK)):
            continue
        if os.path.isabs(candidate) and _is_safe_gh(Path(candidate), user):
            return candidate
        raise SubmitError(
            "the GitHub CLI (gh) was found but is not a safe executable: it must be an absolute "
            "PATH entry, owned by you or root, and not writable by group or others"
        )
    return None


def discard_pending_input(stdin: Any, stdout: Any = None) -> bool:
    """Drop terminal input that arrived before now, so text typed or pasted ahead of the prompt can
    never be read as consent. Call it after the disclosure is fully written and before the prompt.
    POSIX: wait for output to drain, then `tcflush`; Windows: drain the console buffer. Returns
    False when nothing could be discarded (no real terminal, no terminal API), and the caller must
    then not treat any answer as consent."""
    try:
        fd = stdin.fileno()
    except (AttributeError, OSError, ValueError):
        return False
    try:
        import termios
    except ImportError:
        termios = None
    if termios is not None:
        try:
            with contextlib.suppress(AttributeError, OSError, ValueError, termios.error):
                termios.tcdrain(stdout.fileno())  # let the terminal finish showing the disclosure
            termios.tcflush(fd, termios.TCIFLUSH)
        except (OSError, ValueError, termios.error):
            return False
        return True
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
    if msvcrt is not None:
        try:
            while msvcrt.kbhit():
                msvcrt.getwch()
        except OSError:
            return False
        return True
    return False


def discover_login(
    gh: str | None,
    *,
    run: Callable[..., subprocess.CompletedProcess[str] | None] = default_run_gh,
    environ: Mapping[str, str],
) -> str:
    """The GitHub login `gh issue create` would act as, via one read-only `gh api user` in the same
    environment. Doubles as the authentication check. Raises `SubmitError` (nothing sent)."""
    if gh is None:
        raise SubmitError("the GitHub CLI (gh) was not found")
    result = run(
        [gh, "api", "--hostname", "github.com", "--method", "GET", "user", "--jq", ".login"],
        timeout=GH_TIMEOUT_S,
        environ=environ,
    )
    if result is None or result.returncode != 0:
        raise SubmitError("gh could not confirm your GitHub login (run `gh auth login`)")
    login = (result.stdout or "").strip()
    if _LOGIN_RE.fullmatch(login) is None:
        raise SubmitError("gh could not confirm your GitHub login (run `gh auth login`)")
    return login


def submit_issue(
    body: str,
    *,
    gh: str | None,
    run: Callable[..., subprocess.CompletedProcess[str] | None] = default_run_gh,
    environ: Mapping[str, str],
    temp_dir: Path | None = None,
) -> str | None:
    """Create the fixed-title issue in the fixed repository with the operator's own `gh` login.

    Returns the created issue URL when `gh` printed a recognizable one. Raises `SubmitError` (fixed
    message; nothing was sent) for any failure before `gh issue create` starts, and
    `DeliveryUnconfirmedError` for any failure after: a nonzero exit, a timeout or an error can
    all follow a successful creation. `gh` output and the body never reach a message.
    """
    if gh is None:
        raise SubmitError("the GitHub CLI (gh) was not found")
    started = False  # set immediately before `gh issue create` is launched
    try:
        try:
            fd, name = tempfile.mkstemp(prefix="hmp-compat-report-", suffix=".md", dir=temp_dir)
        except OSError:
            raise SubmitError("cannot create a temporary report file") from None
        try:
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    os.fchmod(handle.fileno(), 0o600)
                    handle.write(body)
            except OSError:
                raise SubmitError("cannot write the temporary report file") from None
            argv = [
                gh, "issue", "create", "--repo", REPORT_REPO, "--title", REPORT_TITLE,
                "--body-file", name,
            ]
            started = True  # from here on the issue may exist whatever happens
            created = run(argv, timeout=GH_TIMEOUT_S, environ=environ)
        finally:
            with contextlib.suppress(OSError):
                os.unlink(name)
    except SubmitError:
        raise
    except (Exception, KeyboardInterrupt):
        if started:
            raise DeliveryUnconfirmedError from None
        raise SubmitError("interrupted or failed while preparing the report") from None
    if created is None or created.returncode != 0:
        raise DeliveryUnconfirmedError
    url = (created.stdout or "").strip().splitlines()[-1:] or [""]
    return url[0] if _ISSUE_URL_RE.fullmatch(url[0]) else None

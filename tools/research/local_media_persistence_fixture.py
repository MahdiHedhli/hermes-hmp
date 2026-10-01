#!/usr/bin/env python3
"""G1 persistence characterization fixture for host-local generated images (research, not product).

Test tooling: `server/hmp_plugin` never imports it. It observes what exact Hermes build `8afaab37`
does when a synthetic model asks `image_generate`, a synthetic provider writes a tiny valid PNG
through the real `agent.image_gen_provider.save_b64_image`, and the real agent loop persists the
turn. It introduces no media reference, route, token, manifest or wire shape.

Parent: creates private scratch and evidence directories, fingerprints the native source,
launches one child per scenario under the target build's own interpreter with a minimal
environment, deletes the scratch tree, and writes a closed-metadata report (counts, booleans,
hashes, enum strings).

Child: sets HOME/HERMES_HOME/XDG before any native import, denies every IP connect except the
child's own loopback synthetic model server, then drives one scenario:

  desktop       real `tui_gateway.server.dispatch` JSON-RPC: `session.create` (hidden "Bot Chat",
                profile alpha) then `prompt.submit` -> real `AIAgent.run_conversation`.
  desktop_flushfail   as above, with an injected failure of the native batch write of the tool row.
  phone         real `GatewayRunner._handle_message` + real `BasePlatformAdapter.handle_message`,
                source built by the real `build_source` with HMP's `scope_id`/`guild_id` = profile,
                event built as `Bridge._phone_event` does. The adapter is an inert stand-in, NOT
                `HmpAdapter`.
  phone_flushfail     as above with the injected tool-row batch write failure.
  desktop_deferred    as `desktop`, but with Hermes's default tool search on: `image_generate` is
                deferred, so the synthetic model calls the native `tool_call` bridge naming it.
  {desktop,phone}_deferred_calls   default tool search on; the model emits the modern bridge shape
                `tool_call {calls: [{name: image_generate, arguments}]}` with one entry.
  history_lifecycle   no model, provider or surface: real SessionDB writes (append_messages_batch,
                archive_and_compact, replace_messages, rewind, deactivate, clear, compression child,
                Desktop branch helper, export/import) and the native same-inode backup restore,
                observed on one synthetic image tool-call/result pair. Storage-API characterization
                only.
  {desktop,phone}_deferred_batch   as above with two entries (distinct synthetic prompts) in one
                parent `tool_call`. The native outcome (accepted, rejected, limited) is observed,
                never forced.

Replaced: the model (loopback OpenAI-compatible synthetic server) and the image provider (synthetic
`ImageGenProvider`, registered in-process, returning `success_response` with a path from the real
`save_b64_image`). Wrapped for observation only: `SessionDB.append_messages_batch` (records order
and roles; the failure scenarios make it raise for the tool-row batch) and the adapter delivery
methods.

The IP denial is Python-level instrumentation, not an OS sandbox.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pwd
import re
import resource
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import zlib
from pathlib import Path
from typing import Any

DEFAULT_NATIVE_SRC = Path(
    "/private/tmp/hmp-approval-dogfood-git-builds/approval-dogfood-8afa-git-public/src"
)
EXPECTED_NATIVE_HEAD = "8afaab3703e336d72a72c812dd2dd249f04f166a"
CHILD_TIMEOUT_SECONDS = 120
MAX_RESULT_BYTES = 2 * 1024 * 1024
TAIL_BYTES = 64 * 1024
SCAN_CHUNK = 64 * 1024
CHILD_FILE_SIZE_LIMIT = 256 * 1024 * 1024
SCENARIOS = ("desktop", "phone", "desktop_flushfail", "phone_flushfail", "desktop_deferred")
# Modern `tool_call {calls: [...]}` bridge scenarios (default tool search on). Not part of
# SCENARIOS: the accepted five are not repeated by default.
MODERN_SCENARIOS = (
    "desktop_deferred_calls",
    "phone_deferred_calls",
    "desktop_deferred_batch",
    "phone_deferred_batch",
)
# G2 native history lifecycle: SessionDB mutation/branch/compaction/import/restore APIs only, no
# model or provider. Not part of SCENARIOS or MODERN_SCENARIOS: neither earlier set is repeated.
HISTORY_SCENARIOS = ("history_lifecycle",)
ALL_SCENARIOS = SCENARIOS + MODERN_SCENARIOS + HISTORY_SCENARIOS
# Per-scenario bridge shape: None = direct call, "legacy" = `{name, arguments}`, "calls" = the
# modern `{calls: [{name, arguments}, ...]}` array, with the number of underlying entries.
BRIDGE_SHAPES: dict[str, tuple[str, int] | None] = {
    "desktop_deferred": ("legacy", 1),
    "desktop_deferred_calls": ("calls", 1),
    "phone_deferred_calls": ("calls", 1),
    "desktop_deferred_batch": ("calls", 2),
    "phone_deferred_batch": ("calls", 2),
}
HERE = Path(__file__).resolve()
HMP_CONTRACT = HERE.parents[2] / "server" / "hmp_plugin" / "contract.py"

OWNING_FILES = (
    "agent/image_gen_provider.py",
    "agent/provider_media.py",
    "agent/session_persistence.py",
    "agent/tool_dispatch_helpers.py",
    "agent/tool_executor.py",
    "tools/image_generation_tool.py",
    "gateway/run.py",
    "gateway/run_turn.py",
    "gateway/run_turn_runner.py",
    "gateway/platforms/base.py",
    "hermes_state.py",
    "hermes_state_messages.py",
    "tui_gateway/server.py",
    "tui_gateway/methods_session.py",
    "tui_gateway/methods_prompt.py",
    "tui_gateway/prompt_turn.py",
)

# Additional native files whose bytes decide the history observations; fingerprinted before and
# after only when a history scenario is requested.
HISTORY_EXTRA_FILES = (
    "hermes_state_common.py",
    "hermes_state_errors.py",
    "hermes_state_sessions.py",
    "hermes_state_compression.py",
    "hermes_state_portability.py",
    "hermes_state_rewind.py",
    "hermes_cli/backup_restore.py",
    "hermes_cli/backup_sqlite.py",
    "gateway/slash_commands_session.py",
)

REAL_HERMES_MARKER = Path("~/.hermes").expanduser()
PROFILE = "alpha"
OTHER_PROFILE = "beta"
CALL_ID = "call_synth_0001"
BATCH_PROMPT_TAGS = ("alpha", "beta")
CHAT_ID = "chat-synthetic"
USER_ID = "user-synthetic"
LONG_PROMPT_CHARS = 6000
LONG_PROMPT = ("synthetic-prompt-" * 400)[:LONG_PROMPT_CHARS]
FINAL_TEXT = "synthetic final answer"
FAIL_MARK = "G1_INJECTED_FLUSH_FAILURE"
ENV_MARK_KEYS = ("KEY", "TOKEN", "SECRET", "PASSWORD")

# --------------------------------------------------------------------------------------------
# Shared helpers (stdlib only)
# --------------------------------------------------------------------------------------------


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def synthetic_png() -> bytes:
    """A valid 1x1 RGB PNG built from stdlib pieces."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return (
            struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\x10\x20\x30")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def fingerprint(native_src: Path, names: tuple[str, ...] = OWNING_FILES) -> dict[str, str]:
    return {name: sha256_file(native_src / name) for name in names}


def hmp_cap(name: str) -> int | None:
    """A cap constant read as text from the HMP contract; the contract module is not imported."""
    match = re.search(rf"^{name}\s*=\s*(\d+)\s*$", HMP_CONTRACT.read_text(), re.M)
    return int(match.group(1)) if match else None


def hmp_tool_output_cap() -> int | None:
    return hmp_cap("TOOL_OUTPUT_CAP")


GIT_ENV = {"PATH": "/usr/bin:/bin", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}


def native_head(native_src: Path) -> str | None:
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
            ["git", "-C", str(native_src), "rev-parse", "HEAD"],  # noqa: S607 - fixed `git` argv, PATH pinned by GIT_ENV
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            stdin=subprocess.DEVNULL,
            env=GIT_ENV,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def native_clean(native_src: Path) -> bool | None:
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
            [  # noqa: S607 - fixed `git` argv, PATH pinned by GIT_ENV
                "git",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(native_src),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            stdin=subprocess.DEVNULL,
            env=GIT_ENV,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() == "" if out.returncode == 0 else None


# --------------------------------------------------------------------------------------------
# Safety gates (stdlib only; they run before any subprocess launch or native import)
# --------------------------------------------------------------------------------------------


class FixtureSafetyError(RuntimeError):
    """A refusal with a closed `reason` enum string; the message never carries a path."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def real_hermes_homes() -> list[Path]:
    """Every live Hermes home this process could name: the installed one, the current HOME's
    `.hermes`, the account's `.hermes`, and the supplied comparison marker. Resolved, not opened."""
    candidates = [REAL_HERMES_MARKER, Path(os.path.expanduser("~")) / ".hermes"]
    try:  # noqa: SIM105 - missing passwd entry is tolerated
        candidates.append(Path(pwd.getpwuid(os.getuid()).pw_dir) / ".hermes")
    except KeyError:
        pass
    if os.environ.get("HMP_G1_REAL_HERMES_MARKER"):
        candidates.append(Path(os.environ["HMP_G1_REAL_HERMES_MARKER"]))
    return sorted({c.resolve() for c in candidates}, key=str)


def _overlaps(a: Path, b: Path) -> bool:
    return a == b or b in a.parents or a in b.parents


def refuse_inside_real_hermes(path: Path, reason: str, *, containing: bool = False) -> None:
    """Refuse a path equal to or inside a live home; `containing` also refuses a path that
    holds one."""
    resolved = path.resolve()
    for home in real_hermes_homes():
        if (
            resolved == home
            or home in resolved.parents
            or (containing and resolved in home.parents)
        ):
            raise FixtureSafetyError(reason)


def validate_native_src(native_src: Path) -> None:
    """Refuse an unsafe or unpinned source before it is run or imported.

    Path facts first, git facts last."""
    if not native_src.is_absolute():
        raise FixtureSafetyError("source_not_absolute")
    refuse_inside_real_hermes(native_src, "source_inside_real_hermes_home", containing=True)
    try:
        src_stat = native_src.lstat()
    except OSError:
        raise FixtureSafetyError("source_missing") from None
    if stat.S_ISLNK(src_stat.st_mode):
        raise FixtureSafetyError("source_is_symlink")
    if not stat.S_ISDIR(src_stat.st_mode):
        raise FixtureSafetyError("source_not_directory")
    try:
        git_stat = (native_src / ".git").lstat()
    except OSError:
        raise FixtureSafetyError("source_git_missing") from None
    if stat.S_ISLNK(git_stat.st_mode):
        raise FixtureSafetyError("source_git_symlink")
    if not stat.S_ISDIR(git_stat.st_mode):
        raise FixtureSafetyError("source_git_unresolvable")
    head = native_head(native_src)
    if head is None:
        raise FixtureSafetyError("source_git_unresolvable")
    if head != EXPECTED_NATIVE_HEAD:
        raise FixtureSafetyError("source_head_mismatch")
    clean = native_clean(native_src)
    if clean is None:
        raise FixtureSafetyError("source_git_unresolvable")
    if not clean:
        raise FixtureSafetyError("source_tree_dirty")


def validate_interpreter(native_src: Path) -> None:
    """The venv python may resolve into the source itself or into the shared interpreter directory
    (`<real hermes home>/tools`). That is an interpreter fact only; any other target, including
    Hermes source under the installed home, is refused."""
    python = native_src / ".venv" / "bin" / "python"
    if not python.is_file():
        return
    target = python.resolve()
    allowed = [native_src.resolve()] + [home / "tools" for home in real_hermes_homes()]
    if not any(root == target or root in target.parents for root in allowed):
        raise FixtureSafetyError("interpreter_outside_allowed_roots")


def validate_scratch_root(root: Path, native_src: Path) -> None:
    """The child's scratch root must be a private, real, prepared directory outside any live
    home."""
    if not root.is_absolute():
        raise FixtureSafetyError("scratch_not_absolute")
    try:
        root_stat = root.lstat()
    except OSError:
        raise FixtureSafetyError("scratch_missing") from None
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise FixtureSafetyError("scratch_not_real_directory")
    if root_stat.st_uid != os.getuid() or root_stat.st_mode & 0o077:
        raise FixtureSafetyError("scratch_not_private")
    refuse_inside_real_hermes(root, "scratch_inside_real_hermes_home")
    if _overlaps(root.resolve(), native_src.resolve()):
        raise FixtureSafetyError("scratch_overlaps_source")
    layout = scratch_layout(root)
    for path in layout.values():
        try:
            mode = path.lstat().st_mode
        except OSError:
            raise FixtureSafetyError("scratch_layout_missing") from None
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise FixtureSafetyError("scratch_layout_unsafe")
    for key, name in (("HOME", "home"), ("HERMES_HOME", "hermes_root")):
        value = os.environ.get(key)
        if not value or Path(value).resolve() != layout[name].resolve():
            raise FixtureSafetyError("scratch_env_mismatch")


def prepare_evidence_dir(evidence: Path | None, native_src: Path) -> Path:
    """A brand-new 0700 directory.

    An existing path (file, directory or link) is never reused or chmodded."""
    if evidence is None:
        path = Path(tempfile.mkdtemp(prefix="hmp-g1-evidence-"))
    else:
        path = evidence if evidence.is_absolute() else Path.cwd() / evidence
        refuse_inside_real_hermes(path.parent, "evidence_inside_real_hermes_home")
        if _overlaps(path.parent.resolve() / path.name, native_src.resolve()):
            raise FixtureSafetyError("evidence_overlaps_source")
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            raise FixtureSafetyError("evidence_path_exists") from None
        except OSError:
            raise FixtureSafetyError("evidence_cannot_create") from None
    info = path.lstat()
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise FixtureSafetyError("evidence_not_private")
    return path


def scratch_layout(root: Path) -> dict[str, Path]:
    hermes_root = root / "hermes"
    return {
        "home": root / "home",
        "hermes_root": hermes_root,
        "alpha": hermes_root / "profiles" / PROFILE,
        "beta": hermes_root / "profiles" / OTHER_PROFILE,
        "xdg_config": root / "xdg" / "config",
        "xdg_data": root / "xdg" / "data",
        "xdg_cache": root / "xdg" / "cache",
        "xdg_state": root / "xdg" / "state",
        "xdg_runtime": root / "xdg" / "runtime",
        "tmp": root / "tmp",
        "cwd": root / "cwd",
    }


def child_environment(layout: dict[str, Path]) -> dict[str, str]:
    """Allow-list only: no inherited credentials, proxies, HERMES_* or XDG_* beyond these."""
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(layout["home"]),
        "HERMES_HOME": str(layout["hermes_root"]),
        "XDG_CONFIG_HOME": str(layout["xdg_config"]),
        "XDG_DATA_HOME": str(layout["xdg_data"]),
        "XDG_CACHE_HOME": str(layout["xdg_cache"]),
        "XDG_STATE_HOME": str(layout["xdg_state"]),
        "XDG_RUNTIME_DIR": str(layout["xdg_runtime"]),
        "TMPDIR": str(layout["tmp"]),
        "TIRITH_ENABLED": "false",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "LANG": "C.UTF-8",
        # A comparison marker only (never opened): the installed Hermes home, to prove nothing
        # from it loads.
        "HMP_G1_REAL_HERMES_MARKER": str(REAL_HERMES_MARKER),
    }


def open_private_exclusive(path: Path) -> int:
    """Create a brand-new 0600 file; an existing file or link at the path is refused, never
    reused."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    return fd


def write_private(path: Path, text: str) -> None:
    with os.fdopen(open_private_exclusive(path), "w") as handle:
        handle.write(text)


# --------------------------------------------------------------------------------------------
# Parent
# --------------------------------------------------------------------------------------------


def parse_child_output(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    return {"status": "ERROR", "reason": "child_output_unparseable"}


def read_tail(path: Path, limit: int = TAIL_BYTES) -> str:
    with open(path, "rb") as handle:
        size = os.fstat(handle.fileno()).st_size
        handle.seek(max(0, size - limit))
        return handle.read(limit).decode("utf-8", "replace")


def scan_stream(path: Path, needle: bytes) -> dict[str, Any]:
    """Size, line count and needle presence of a streamed file, read in fixed chunks (never
    whole)."""
    size = lines = 0
    mentions = False
    carry = b""
    last = b""
    with open(path, "rb") as handle:
        while chunk := handle.read(SCAN_CHUNK):
            size += len(chunk)
            lines += chunk.count(b"\n")
            last = chunk[-1:]
            if not mentions:
                mentions = needle in carry + chunk
                carry = (carry + chunk)[-(len(needle) - 1) :] if len(needle) > 1 else b""
    if last and last != b"\n":
        lines += 1
    return {"bytes": size, "lines": lines, "mentions": mentions}


def read_bounded_result(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """The child's result file, size-checked on the open descriptor before it is read.

    Opened non-blocking where supported so a FIFO without a writer cannot stall the parent."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return None, None
    except OSError:
        return None, "child_result_unsafe"
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            return None, "child_result_unsafe"
        if info.st_size > MAX_RESULT_BYTES:
            return None, "child_result_oversize"
        raw = handle.read(MAX_RESULT_BYTES + 1)
    if len(raw) > MAX_RESULT_BYTES:
        return None, "child_result_oversize"
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "child_result_unparseable"
    return (value, None) if isinstance(value, dict) else (None, "child_result_unparseable")


def _limit_child() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (CHILD_FILE_SIZE_LIMIT, CHILD_FILE_SIZE_LIMIT))


def _spawn_child(argv: list[str], **kwargs: Any) -> subprocess.Popen[bytes]:
    return subprocess.Popen(argv, **kwargs)  # noqa: S603 - argv is built by this fixture, no shell


def _kill_group(proc: subprocess.Popen[bytes]) -> None:
    try:  # noqa: SIM105 - best-effort cleanup; swallowing is intended
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_scenario(native_src: Path, scenario: str, evidence: Path) -> dict[str, Any]:
    python = native_src / ".venv" / "bin" / "python"
    if not python.is_file():
        return {"status": "UNAVAILABLE", "reason": "native_interpreter_missing"}
    root = Path(tempfile.mkdtemp(prefix="hmp-g1-"))
    root.chmod(0o700)
    layout = scratch_layout(root)
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
    for path in (layout["xdg_runtime"], layout["alpha"], layout["beta"], layout["hermes_root"]):
        path.chmod(0o700)
    out_path = evidence / f"{scenario}.child.stdout"
    log_path = evidence / f"{scenario}.child.log"
    summary: dict[str, Any]
    out_fd = err_fd = -1
    try:
        out_fd = open_private_exclusive(out_path)
        err_fd = open_private_exclusive(log_path)
        proc = _spawn_child(
            [
                str(python),
                str(HERE),
                "child",
                "--native-src",
                str(native_src),
                "--root",
                str(root),
                "--scenario",
                scenario,
            ],
            cwd=layout["cwd"],
            env=child_environment(layout),
            stdin=subprocess.DEVNULL,
            stdout=out_fd,
            stderr=err_fd,
            start_new_session=True,
            preexec_fn=_limit_child,
        )
        timed_out = False
        try:
            returncode = proc.wait(timeout=CHILD_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc)
            returncode = proc.wait()
        _kill_group(proc)  # no stray descendants outlive the scenario
        err_meta = scan_stream(log_path, str(root).encode())
        out_meta = scan_stream(out_path, b"")
        if timed_out:
            summary = {"status": "ERROR", "reason": "child_timeout"}
        else:
            summary, bad = read_bounded_result(root / "result.json")
            if bad:
                summary = {"status": "ERROR", "reason": bad}
            elif summary is None:
                summary = parse_child_output(read_tail(out_path))
            private = summary.pop("_private", None)
            if private:
                write_private(evidence / f"{scenario}.private.json", json.dumps(private, indent=2))
        summary["child_exit_code"] = returncode
        summary["child_stdout_bytes"] = out_meta["bytes"]
        summary["child_stderr_bytes"] = err_meta["bytes"]
        summary["child_stderr_lines"] = err_meta["lines"]
        summary["child_stderr_mentions_scratch"] = err_meta["mentions"]
    finally:
        for fd in (out_fd, err_fd):
            if fd >= 0:
                os.close(fd)
        shutil.rmtree(root, ignore_errors=True)
    summary["scratch_removed"] = not root.exists()
    return summary


def run_parent(
    native_src: Path, scenarios: tuple[str, ...], evidence: Path | None
) -> dict[str, Any]:
    validate_native_src(
        native_src
    )  # refuses before any evidence write, child launch or native import
    validate_interpreter(native_src)
    evidence = prepare_evidence_dir(evidence, native_src)
    names = OWNING_FILES + (HISTORY_EXTRA_FILES if set(scenarios) & set(HISTORY_SCENARIOS) else ())
    before = fingerprint(native_src, names)
    report: dict[str, Any] = {
        "native_head_matches_expected": True,
        "native_tree_clean_before": True,
        "hmp_tool_output_cap": hmp_tool_output_cap(),
        "hmp_tool_arguments_cap": hmp_cap("TOOL_ARGUMENTS_CAP"),
        "private_evidence_dir_mode_0700": oct(evidence.stat().st_mode & 0o777) == "0o700",
        "scenarios": {},
    }
    for scenario in dict.fromkeys(scenarios):
        report["scenarios"][scenario] = run_scenario(native_src, scenario, evidence)
    after = fingerprint(native_src, names)
    report["source_fingerprints"] = before
    report["source_unchanged"] = before == after
    report["native_tree_clean_after"] = native_clean(native_src)
    write_private(evidence / "report.json", json.dumps(report, indent=2, sort_keys=True))
    report["private_evidence_dir"] = str(evidence)
    return report


# --------------------------------------------------------------------------------------------
# Child: network denial, synthetic model, synthetic provider
# --------------------------------------------------------------------------------------------

PRIVATE: dict[str, Any] = {}
_BLOCKED = {"ip_blocked": 0, "unix_blocked": 0, "loopback_synthetic_allowed": 0}
_ALLOWED_PORT: list[int] = []


def _is_allowed(address: Any) -> bool:
    try:
        host, port = address[0], address[1]
    except (TypeError, IndexError):
        return False
    return host in ("127.0.0.1", "localhost") and bool(_ALLOWED_PORT) and port == _ALLOWED_PORT[0]


def install_ip_denial() -> None:
    """Deny every connect/send-to except the child's own loopback synthetic server.

    AF_UNIX is denied too: these scenarios need no external Unix IPC (`socketpair`, used by
    asyncio, never connects to an address and is unaffected). Python-level instrumentation, not an
    OS sandbox."""
    import socket

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create = socket.create_connection
    af_unix = getattr(socket, "AF_UNIX", None)

    def deny(counter: str) -> None:
        _BLOCKED[counter] += 1
        raise OSError("network and unix socket contact is blocked in this fixture")

    def guarded_connect(self: Any, address: Any, *a: Any, **k: Any) -> Any:
        if self.family == af_unix:
            deny("unix_blocked")
        if _is_allowed(address):
            _BLOCKED["loopback_synthetic_allowed"] += 1
            return real_connect(self, address, *a, **k)
        deny("ip_blocked")

    def guarded_connect_ex(self: Any, address: Any, *a: Any, **k: Any) -> Any:
        if self.family == af_unix:
            deny("unix_blocked")
        if _is_allowed(address):
            _BLOCKED["loopback_synthetic_allowed"] += 1
            return real_connect_ex(self, address, *a, **k)
        deny("ip_blocked")

    def guarded_sendto(self: Any, *a: Any, **k: Any) -> Any:
        deny("unix_blocked" if self.family == af_unix else "ip_blocked")

    def guarded_create(address: Any, *a: Any, **k: Any) -> Any:
        if _is_allowed(address):
            return real_create(address, *a, **k)
        deny("ip_blocked")

    socket.socket.connect = guarded_connect  # type: ignore[assignment]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[assignment]
    socket.socket.sendto = guarded_sendto  # type: ignore[assignment]
    socket.create_connection = guarded_create  # type: ignore[assignment]


class SyntheticModel:
    """Loopback OpenAI-compatible chat-completions server with a two-step script."""

    def __init__(self, shape: tuple[str, int] | None = None) -> None:
        self.shape = shape
        self.requests = 0
        self.tool_call_responses = 0
        self.final_responses = 0
        self.saw_tool_row_in_followup = False
        self._server: Any = None

    def start(self) -> int:
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        model = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # silence request logging
                return

            def do_GET(self) -> None:  # model list probes
                body = json.dumps(
                    {"object": "list", "data": [{"id": "synthetic-model", "object": "model"}]}
                )
                self._send(200, body.encode(), "application/json")

            def _send(self, status: int, raw: bytes, ctype: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                except json.JSONDecodeError:
                    body = {}
                model.requests += 1
                messages = body.get("messages") or []
                last_role = (
                    messages[-1].get("role")
                    if messages and isinstance(messages[-1], dict)
                    else None
                )
                has_tools = bool(body.get("tools"))
                call_tool = has_tools and last_role != "tool" and model.tool_call_responses == 0
                if last_role == "tool":
                    model.saw_tool_row_in_followup = True
                if call_tool:
                    model.tool_call_responses += 1
                    name, arguments = "image_generate", {"prompt": LONG_PROMPT}
                    if model.shape is not None:
                        kind, count = model.shape
                        if kind == "legacy":
                            arguments = {"name": "image_generate", "arguments": arguments}
                        else:
                            arguments = {"calls": batch_entries(count)}
                        name = "tool_call"
                    message: dict[str, Any] = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": CALL_ID,
                                "type": "function",
                                "function": {"name": name, "arguments": json.dumps(arguments)},
                            }
                        ],
                    }
                    finish = "tool_calls"
                else:
                    model.final_responses += 1
                    message = {"role": "assistant", "content": FINAL_TEXT}
                    finish = "stop"
                usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                if body.get("stream"):
                    self._stream(message, finish, usage)
                else:
                    payload = {
                        "id": "chatcmpl-synth",
                        "object": "chat.completion",
                        "created": 0,
                        "model": "synthetic-model",
                        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                        "usage": usage,
                    }
                    self._send(200, json.dumps(payload).encode(), "application/json")

            def _stream(self, message: dict[str, Any], finish: str, usage: dict[str, int]) -> None:
                chunks: list[dict[str, Any]] = []
                base = {
                    "id": "chatcmpl-synth",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": "synthetic-model",
                }
                if message.get("tool_calls"):
                    call = message["tool_calls"][0]
                    delta: dict[str, Any] = {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": call["id"],
                                "type": "function",
                                "function": {
                                    "name": call["function"]["name"],
                                    "arguments": call["function"]["arguments"],
                                },
                            }
                        ],
                    }
                else:
                    delta = {"role": "assistant", "content": message["content"]}
                chunks.append(
                    {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                )
                chunks.append(
                    {
                        **base,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
                        "usage": usage,
                    }
                )
                raw = (
                    b"".join(b"data: " + json.dumps(c).encode() + b"\n\n" for c in chunks)
                    + b"data: [DONE]\n\n"
                )
                self._send(200, raw, "text/event-stream")

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = self._server.server_address[1]
        _ALLOWED_PORT.append(port)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return port

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()


def batch_entries(count: int) -> list[dict[str, Any]]:
    """Underlying `image_generate` entries for the modern bridge array. One entry keeps the long
    prompt (comparable with the accepted scenarios); a batch uses distinct short synthetic prompts,
    each carrying a tag the synthetic provider turns into a distinct filename prefix."""
    if count == 1:
        return [{"name": "image_generate", "arguments": {"prompt": LONG_PROMPT}}]
    return [
        {"name": "image_generate", "arguments": {"prompt": f"synthetic-batch-{tag}-prompt"}}
        for tag in BATCH_PROMPT_TAGS[:count]
    ]


def write_config(home: Path, port: int, *, routes: bool, tool_search_off: bool = True) -> None:
    lines = [
        "model:",
        "  default: synthetic-model",
        "  provider: custom",
        f"  base_url: http://127.0.0.1:{port}/v1",
        "  api_key: synthetic-not-a-secret",
        "image_gen:",
        "  provider: g1synth",
        "agent:",
        "  max_turns: 4",
        *(["tools:", "  tool_search:", "    enabled: 'off'"] if tool_search_off else []),
        "platform_toolsets:",
        "  cli: [image_gen]",
        "  tui: [image_gen]",
        "  hmp: [image_gen]",
    ]
    if routes:
        lines += [
            "gateway:",
            "  multiplex_profiles: true",
            "  profile_routes:",
            f"    - {{name: hmp-{PROFILE}, platform: hmp, guild_id: {PROFILE}, "
            f"profile: {PROFILE}}}",
        ]
    (home / "config.yaml").write_text("\n".join(lines) + "\n")


class Recorder:
    """Single ordered event log. Entries are closed enums plus small integers, never content."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events: list[dict[str, Any]] = []

    def add(self, kind: str, **fields: Any) -> int:
        with self._lock:
            seq = len(self.events)
            self.events.append({"seq": seq, "kind": kind, **fields})
            return seq

    def first(self, kind: str, **match: Any) -> int | None:
        for event in self.events:
            if event["kind"] == kind and all(event.get(k) == v for k, v in match.items()):
                return event["seq"]
        return None

    def count(self, kind: str, **match: Any) -> int:
        return sum(
            1
            for e in self.events
            if e["kind"] == kind and all(e.get(k) == v for k, v in match.items())
        )


def register_synthetic_provider(recorder: Recorder, produced: list[dict[str, Any]]) -> None:
    from agent import image_gen_registry
    from agent.image_gen_provider import ImageGenProvider, save_b64_image, success_response

    png_b64 = base64.b64encode(synthetic_png()).decode()

    class SyntheticProvider(ImageGenProvider):
        @property
        def name(self) -> str:
            return "g1synth"

        @property
        def display_name(self) -> str:
            return "G1 synthetic"

        def is_available(self) -> bool:
            return True

        def default_model(self) -> str:
            return "g1-synthetic-model"

        def list_models(self) -> list[dict[str, Any]]:
            return [{"id": "g1-synthetic-model", "display": "G1 synthetic"}]

        def generate(
            self, prompt: str, aspect_ratio: str = "landscape", **kwargs: Any
        ) -> dict[str, Any]:
            from hermes_constants import get_hermes_home

            tag = next((t for t in BATCH_PROMPT_TAGS if f"-batch-{t}-" in prompt), None)
            path = save_b64_image(png_b64, prefix="g1synth" + (f"-{tag}" if tag else ""))
            produced.append(
                {
                    "path": str(path),
                    "hermes_home_at_call": str(get_hermes_home()),
                    "thread_is_main": threading.current_thread() is threading.main_thread(),
                }
            )
            recorder.add("provider_saved")
            return success_response(
                image=str(path),
                model="g1-synthetic-model",
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                provider="g1synth",
            )

    image_gen_registry.register_provider(SyntheticProvider())


def closed_tool_name(name: Any) -> str:
    """Closed class of a tool name; an unexpected name is never recorded verbatim."""
    return name if name in ("image_generate", "tool_call") else "other"


def classify_send(text: str) -> str:
    """Closed class of an outbound adapter text; the text itself is never recorded."""
    if text == FINAL_TEXT:
        return "model_final_text"
    if "No home channel is set" in text:
        return "home_channel_notice"
    if "No reply" in text and "tool result was still pending" in text:
        return "pending_tool_no_reply_notice"
    if "deliver the image attachment" in text:
        return "image_delivery_failure_notice"
    return "other"


def precheck() -> dict[str, Any]:
    """Closed booleans: is the synthetic provider selected and is `image_generate` offered."""
    out: dict[str, Any] = {}
    try:
        from tools import image_generation_tool as igt

        out["configured_provider_is_g1synth"] = igt._read_configured_image_provider() == "g1synth"
        out["check_fn_true"] = bool(igt.check_image_generation_requirements())
    except Exception as exc:
        out["error_type"] = type(exc).__name__
    try:
        import model_tools

        names = [
            d.get("function", {}).get("name")
            for d in model_tools.get_tool_definitions(quiet_mode=True)
        ]
        out["default_toolset_offers_image_generate"] = "image_generate" in names
        out["offered_tool_count"] = len(names)
    except Exception as exc:
        out["definitions_error_type"] = type(exc).__name__
    return out


def install_db_observer(recorder: Recorder, *, fail_tool_batch: bool) -> None:
    """Wrap `SessionDB.append_messages_batch`: record order/roles, optionally fail the tool-row
    batch.

    The failure scenarios raise before the native method runs, so the native write does not happen.
    This is fault injection at the native public-method boundary, not a SQLite reimplementation."""
    import sqlite3

    from hermes_state import SessionDB

    real = SessionDB.append_messages_batch

    def wrapper(
        self: Any, session_id: str, messages: list[dict[str, Any]], *a: Any, **k: Any
    ) -> Any:
        roles = [m.get("role") for m in messages if isinstance(m, dict)]
        has_tool = "tool" in roles
        recorder.add(
            "db_batch", n=len(messages), roles=",".join(str(r) for r in roles), has_tool=has_tool
        )
        if fail_tool_batch and has_tool:
            recorder.add("db_batch_injected_failure")
            raise sqlite3.OperationalError(FAIL_MARK)
        return real(self, session_id, messages, *a, **k)

    SessionDB.append_messages_batch = wrapper  # type: ignore[method-assign]


# --------------------------------------------------------------------------------------------
# Child: closed-metadata inspection (never returns content)
# --------------------------------------------------------------------------------------------


MAX_WALK_NODES = 200
MAX_WALK_DEPTH = 4
MAX_PATH_CHARS = 60


def parse_json_or_none(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw) if isinstance(raw, str) else None
    except json.JSONDecodeError:
        return None


def outer_call_shape(call: dict[str, Any]) -> dict[str, Any]:
    """Closed description of one persisted assistant call: outer name class, bridge shape and the
    underlying entry names. Prompts are only compared (distinct count), never recorded."""
    function = call.get("function") or {}
    outer_name = function.get("name")
    args = parse_json_or_none(function.get("arguments"))
    shape = "direct"
    entries: list[Any] = []
    if outer_name == "tool_call":
        if isinstance(args, dict) and isinstance(args.get("calls"), list):
            shape, entries = "calls_array", args["calls"]
        elif isinstance(args, dict) and "name" in args:
            shape, entries = "legacy_single", [args]
        else:
            shape = "other"
    entry_names = [e.get("name") if isinstance(e, dict) else None for e in entries]
    entry_args = [
        parse_json_or_none(e.get("arguments")) if isinstance(e, dict) else None for e in entries
    ]
    prompts = [a.get("prompt") for a in entry_args if isinstance(a, dict)]
    return {
        "id": call.get("id"),
        "outer_name_class": closed_tool_name(outer_name),
        "shape": shape,
        "entry_count": len(entries) if shape != "direct" else 1,
        "entry_names_closed": [closed_tool_name(n) for n in entry_names],
        "entry_prompts_distinct": len({p for p in prompts if isinstance(p, str)}),
        "entry_ids_present": any(isinstance(e, dict) and "id" in e for e in entries),
    }


def walk_image_fields(
    node: Any, path: str = "", depth: int = 0, budget: list[int] | None = None
) -> list[dict[str, Any]]:
    """Bounded walk of a parsed tool result: every string value under a key named like `*image`,
    as key-path (list positions as `[]`), type and value only as a string for the caller to
    classify. The caller never publishes the value."""
    budget = budget if budget is not None else [MAX_WALK_NODES]
    found: list[dict[str, Any]] = []
    if budget[0] <= 0 or depth > MAX_WALK_DEPTH:
        return found
    budget[0] -= 1
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if str(key).endswith("image") and isinstance(value, str):
                found.append({"path": child[:MAX_PATH_CHARS], "value": value})
            else:
                found.extend(walk_image_fields(value, child, depth + 1, budget))
    elif isinstance(node, list):
        for value in node:
            found.extend(walk_image_fields(value, f"{path}[]", depth + 1, budget))
    return found


def error_class(parsed: Any) -> str | None:
    """Closed class of a native tool error object; the message text is never recorded."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("error"), str):
        return None
    text = parsed["error"]
    if "takes exactly one entry for local tools" in text:
        return "local_batch_rejected"
    if "is not available in this session" in text:
        return "not_in_session_scope"
    return "other_error"


def describe_bridge_shape(
    assistants: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    profile_cache: Path,
    produced: list[dict[str, Any]],
) -> dict[str, Any]:
    """Array-aware linkage observations (additive to the single-entry observations)."""
    outer: list[dict[str, Any]] = []
    for row in assistants:
        parsed = parse_json_or_none(row.get("tool_calls"))
        outer.extend(outer_call_shape(c) for c in (parsed or []) if isinstance(c, dict))
    outer_ids = {o["id"] for o in outer if o["id"]}
    rows_meta: list[dict[str, Any]] = []
    image_values: list[str] = []
    for row in tools:
        content = row.get("content")
        parsed = parse_json_or_none(content)
        fields = walk_image_fields(parsed)
        image_values.extend(f["value"] for f in fields)
        rows_meta.append(
            {
                "tool_name_class": closed_tool_name(row.get("tool_name")),
                "id_is_outer_call": row.get("tool_call_id") in outer_ids,
                "json_type": type(parsed).__name__ if parsed is not None else "unparseable",
                "top_level_keys": sorted(str(k)[:40] for k in parsed)[:20]
                if isinstance(parsed, dict)
                else [],
                "error_class": error_class(parsed),
                "image_field_paths": [f["path"] for f in fields],
                "image_field_count": len(fields),
                "image_fields_are_str": all(isinstance(f["value"], str) for f in fields),
                "image_fields_absolute": [f["value"].startswith("/") for f in fields],
                "image_fields_are_provider_saved": [
                    any(f["value"] == pr["path"] for pr in produced) for f in fields
                ],
            }
        )
    cache_names = (
        sorted(p.name for p in profile_cache.iterdir() if p.is_file())
        if profile_cache.is_dir()
        else []
    )
    referenced = {Path(v).name for v in image_values}
    saved_names = [Path(pr["path"]).name for pr in produced]
    return {
        "outer_call_count": len(outer),
        "outer_calls": outer,
        "underlying_call_count": sum(o["entry_count"] for o in outer),
        "tool_row_count": len(tools),
        "tool_rows_per_outer_call": {
            str(i): sum(1 for r in tools if r.get("tool_call_id") == o["id"])
            for i, o in enumerate(outer)
        },
        "one_wrapper_result": len(outer) == 1 and len(tools) == 1,
        "multiple_tool_rows": len(tools) > 1,
        "all_tool_rows_share_one_id": len({r.get("tool_call_id") for r in tools}) == 1
        if tools
        else False,
        # More underlying entries than distinct tool-row ids: an id cannot attribute a result to
        # an entry, so a shared id is not evidence of native per-entry execution.
        "shared_id_ambiguous": sum(o["entry_count"] for o in outer)
        > len({r.get("tool_call_id") for r in tools}),
        "tool_rows": rows_meta,
        "image_field_total": len(image_values),
        "image_values_unique": len(set(image_values)),
        "cache_file_count": len(cache_names),
        "cache_names_distinct": len(set(cache_names)),
        "cache_files_referenced_by_rows": len(referenced & set(cache_names)),
        "cache_files_unreferenced_by_rows": len(set(cache_names) - referenced),
        "provider_saved_distinct_names": len(set(saved_names)),
        "provider_saved_in_cache": sum(1 for n in saved_names if n in cache_names),
        "cache_names_carry_batch_tags": [
            any(f"-{t}-" in n or n.startswith(f"g1synth-{t}") for n in cache_names)
            for t in BATCH_PROMPT_TAGS
        ],
    }


def inspect_rows(
    db_path: Path,
    session_ids: list[str],
    profile_cache: Path,
    other_cache: Path,
    produced: list[dict[str, Any]],
    cap: int | None,
) -> dict[str, Any]:
    from hermes_state import SessionDB

    out: dict[str, Any] = {"db_exists": db_path.is_file()}
    if not db_path.is_file():
        return out
    db = SessionDB(db_path, read_only=True)
    try:
        rows: list[dict[str, Any]] = []
        for sid in session_ids:
            rows.extend(db.get_messages(sid))
        out["rows_total"] = len(rows)
        out["roles"] = [r.get("role") for r in rows]
        assistants = [r for r in rows if r.get("role") == "assistant"]
        tools = [r for r in rows if r.get("role") == "tool"]
        out["assistant_rows"] = len(assistants)
        out["tool_rows"] = len(tools)
        calls: list[dict[str, Any]] = []
        for r in assistants:
            raw = r.get("tool_calls")
            parsed = raw if isinstance(raw, list) else None
            if parsed is None and isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
            for call in parsed or []:
                if isinstance(call, dict):
                    raw_args = (call.get("function") or {}).get("arguments")
                    try:
                        underlying = (
                            json.loads(raw_args).get("name") if isinstance(raw_args, str) else None
                        )
                    except (json.JSONDecodeError, AttributeError):
                        underlying = None
                    calls.append(
                        {
                            "row_id": r.get("id"),
                            "id": call.get("id"),
                            "underlying": underlying,
                            "name": (call.get("function") or {}).get("name"),
                            "args_len": len(
                                str((call.get("function") or {}).get("arguments") or "")
                            ),
                        }
                    )
        out["assistant_call_count"] = len(calls)
        out["assistant_call_id_matches_expected"] = any(c["id"] == CALL_ID for c in calls)
        out["assistant_call_name_image_generate"] = any(
            c["name"] == "image_generate" for c in calls
        )
        out["assistant_call_names"] = sorted({str(c["name"]) for c in calls})
        out["assistant_call_bridge_underlying_is_image_generate"] = any(
            c["name"] == "tool_call" and c["underlying"] == "image_generate" for c in calls
        )
        out["assistant_call_args_len_over_hmp_args_cap"] = any(
            c["args_len"] > (hmp_cap("TOOL_ARGUMENTS_CAP") or 0) for c in calls
        )
        out["assistant_call_args_len"] = [c["args_len"] for c in calls]
        tool_meta: list[dict[str, Any]] = []
        for r in tools:
            content = r.get("content")
            text = content if isinstance(content, str) else ""
            meta: dict[str, Any] = {
                "row_id": r.get("id"),
                "tool_name": r.get("tool_name"),
                "tool_call_id_matches_expected": r.get("tool_call_id") == CALL_ID,
                "raw_len": len(text),
                "raw_sha256": sha256_bytes(text.encode()),
                "raw_over_hmp_cap": cap is not None and len(text) > cap,
            }
            try:
                parsed_json = json.loads(text)
                meta["raw_full_json_parses"] = isinstance(parsed_json, dict)
            except json.JSONDecodeError:
                parsed_json = None
                meta["raw_full_json_parses"] = False
            if cap is not None:
                try:
                    json.loads(text[:cap])
                    meta["prefix_at_hmp_cap_parses"] = True
                except json.JSONDecodeError:
                    meta["prefix_at_hmp_cap_parses"] = False
            if isinstance(parsed_json, dict):
                keys = list(parsed_json.keys())
                meta["json_key_order"] = keys
                meta["success_is_true"] = parsed_json.get("success") is True
                image = parsed_json.get("image")
                meta["image_is_str"] = isinstance(image, str)
                meta["image_is_absolute"] = isinstance(image, str) and image.startswith("/")
                meta["image_key_offset_in_raw"] = text.find('"image"')
                meta["image_key_before_cap"] = cap is not None and 0 <= text.find('"image"') < cap
                meta["image_value_end_before_cap"] = (
                    cap is not None
                    and isinstance(image, str)
                    and text.find(image) >= 0
                    and text.find(image) + len(image) <= cap
                )
                meta["prompt_key_offset_in_raw"] = text.find('"prompt"')
                meta["has_host_image_key"] = "host_image" in parsed_json
                meta["has_agent_visible_image_key"] = "agent_visible_image" in parsed_json
                if isinstance(image, str):
                    p = Path(image)
                    meta["image_in_selected_profile_cache"] = p.parent == profile_cache
                    meta["image_in_other_profile_cache"] = p.parent == other_cache
                    meta["image_equals_provider_saved_path"] = any(
                        image == pr["path"] for pr in produced
                    )
                    meta["image_file_exists"] = p.is_file()
                    if p.is_file():
                        st = p.stat()
                        meta["image_file_nlink"] = st.st_nlink
                        meta["image_file_mode_octal"] = oct(st.st_mode & 0o777)
                        meta["image_file_is_symlink"] = p.is_symlink()
                        meta["image_file_sha256_matches_synthetic_png"] = sha256_file(
                            p
                        ) == sha256_bytes(synthetic_png())
            tool_meta.append(meta)
        out["tool_row_meta"] = tool_meta
        PRIVATE.setdefault("tool_rows", []).extend(
            {"row_id": t.get("id"), "tool_name": t.get("tool_name"), "content": t.get("content")}
            for t in tools
        )
        PRIVATE.setdefault("assistant_rows", []).extend(
            {
                "row_id": a.get("id"),
                "content": a.get("content"),
                "tool_calls_type": type(a.get("tool_calls")).__name__,
            }
            for a in assistants
        )
        # Order and linkage.
        if assistants and tools:
            call_row_ids = [c["row_id"] for c in calls if c["id"] == CALL_ID]
            tool_ids = [t["row_id"] for t in tool_meta if t["tool_call_id_matches_expected"]]
            out["assistant_call_row_precedes_tool_row"] = bool(
                call_row_ids and tool_ids and min(call_row_ids) < min(tool_ids)
            )
            out["tool_name_matches_call_name"] = all(
                t["tool_name"] == "image_generate"
                for t in tool_meta
                if t["tool_call_id_matches_expected"]
            )
            out["tool_row_names"] = sorted({str(t["tool_name"]) for t in tool_meta})
        out["final_assistant_text_has_media_tag"] = any(
            isinstance(r.get("content"), str) and "MEDIA:" in r["content"] for r in assistants
        )
        out["any_row_content_has_media_tag"] = any(
            isinstance(r.get("content"), str) and "MEDIA:" in r["content"] for r in rows
        )
        out["final_assistant_text_matches_model"] = any(
            r.get("content") == FINAL_TEXT for r in assistants
        )
        out["user_rows"] = sum(1 for r in rows if r.get("role") == "user")
        out["bridge_shape"] = describe_bridge_shape(assistants, tools, profile_cache, produced)
    finally:
        db.close()
    return out


def list_cache(profile_home: Path) -> dict[str, Any]:
    images = profile_home / "cache" / "images"
    files = sorted(p for p in images.iterdir() if p.is_file()) if images.is_dir() else []
    return {
        "count": len(files),
        "png_valid_magic": [p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for p in files],
    }


def session_inventory(db_path: Path) -> dict[str, Any]:
    """Closed inventory via public SessionDB methods: ids, hidden flags, titles equal to Bot
    Chat."""
    from hermes_state import SessionDB

    if not db_path.is_file():
        return {"ids": [], "meta": []}
    db = SessionDB(db_path, read_only=True)
    try:
        rows = db.list_sessions_rich(
            limit=50, include_hidden=True, include_children=True, include_archived=True
        )
        PRIVATE.setdefault("titles", {})[db_path.parent.name] = [r.get("title") for r in rows]
        meta = [
            {
                "id": r["id"],
                "hidden": bool(r.get("hidden")),
                "title_is_bot_chat": r.get("title") == "Bot Chat",
                "title_class": (
                    "bot_chat"
                    if r.get("title") == "Bot Chat"
                    else "none"
                    if not r.get("title")
                    else "other"
                ),
                "source": r.get("source"),
                "message_count": r.get("message_count"),
            }
            for r in rows
        ]
        return {"ids": [r["id"] for r in rows], "meta": meta}
    finally:
        db.close()


# --------------------------------------------------------------------------------------------
# Child: scenarios
# --------------------------------------------------------------------------------------------


class Ctx:
    def __init__(self, root: Path, native_src: Path, shape: tuple[str, int] | None = None) -> None:
        self.root = root
        self.native_src = native_src
        self.layout = scratch_layout(root)
        self.recorder = Recorder()
        self.produced: list[dict[str, Any]] = []
        self.model = SyntheticModel(shape=shape)
        self.cap = hmp_tool_output_cap()


def isolation_checks(ctx: Ctx) -> dict[str, bool]:
    layout = ctx.layout
    return {
        "home_env_in_scratch": Path(os.environ["HOME"]).resolve() == layout["home"].resolve(),
        "path_home_in_scratch": Path.home().resolve() == layout["home"].resolve(),
        "hermes_home_env_is_scratch_root": Path(os.environ["HERMES_HOME"]).resolve()
        == layout["hermes_root"].resolve(),
        "no_inherited_hermes_or_xdg_extras": not [
            k
            for k in os.environ
            if k.startswith(("HERMES_", "XDG_")) and k not in child_environment(layout)
        ],
        "no_credential_like_env": not [
            k for k in os.environ if any(t in k.upper() for t in ENV_MARK_KEYS)
        ],
        "native_src_on_path_first": sys.path[0] == str(ctx.native_src),
    }


def runtime_identity(ctx: Ctx) -> dict[str, Any]:
    """Closed facts about what was imported. The venv interpreter is a symlink into the installed
    Hermes tools directory (interpreter and stdlib only); no Hermes code may come from there."""
    real_hermes = (
        Path(os.environ.get("HMP_G1_REAL_HERMES_MARKER", ""))
        if os.environ.get("HMP_G1_REAL_HERMES_MARKER")
        else None
    )
    src = str(ctx.native_src.resolve())
    base = str(Path(sys.base_prefix).resolve())
    probes = (
        "hermes_state",
        "gateway.run",
        "agent.image_gen_provider",
        "tools.image_generation_tool",
        "tui_gateway.server",
        "agent.session_persistence",
    )
    from_src = {}
    for name in probes:
        mod = sys.modules.get(name)
        if (
            mod is None
        ):  # a surface imports only its own modules (the phone path never loads tui_gateway)
            continue
        file = getattr(mod, "__file__", None)
        from_src[name] = bool(file) and str(Path(file).resolve()).startswith(src)
    stray = 0
    if real_hermes is not None:
        marker = str(real_hermes)
        for mod in list(sys.modules.values()):
            file = getattr(mod, "__file__", None)
            if not file:
                continue
            resolved = str(Path(file).resolve())
            if resolved.startswith(marker) and not resolved.startswith(base):
                stray += 1
    return {
        "native_modules_from_independent_src": from_src,
        "interpreter_base_prefix_outside_scratch": not base.startswith(str(ctx.root.resolve())),
        "interpreter_base_prefix_under_real_hermes_tools": bool(real_hermes)
        and base.startswith(str(real_hermes)),
        "modules_from_real_hermes_home_outside_interpreter_base": stray,
        "real_hermes_marker_supplied": real_hermes is not None,
    }


def finish_common(ctx: Ctx, report: dict[str, Any]) -> None:
    report["runtime_identity"] = runtime_identity(ctx)
    report["network"] = {
        "ip_connects_blocked": _BLOCKED["ip_blocked"],
        "unix_contacts_blocked": _BLOCKED["unix_blocked"],
        "loopback_synthetic_connects_allowed": _BLOCKED["loopback_synthetic_allowed"],
    }
    report["synthetic_model"] = {
        "requests": ctx.model.requests,
        "tool_call_responses": ctx.model.tool_call_responses,
        "final_responses": ctx.model.final_responses,
        "followup_carried_tool_row": ctx.model.saw_tool_row_in_followup,
    }
    report["provider_saves"] = len(ctx.produced)
    report["provider_saved_in_tool_thread_context"] = [
        {
            "home_is_alpha": Path(p["hermes_home_at_call"]).resolve()
            == ctx.layout["alpha"].resolve(),
            "home_is_root": Path(p["hermes_home_at_call"]).resolve()
            == ctx.layout["hermes_root"].resolve(),
            "thread_is_main": p["thread_is_main"],
        }
        for p in ctx.produced
    ]
    report["event_order"] = [{k: v for k, v in e.items()} for e in ctx.recorder.events]  # noqa: C416 - intentional shallow per-event copy
    cache = {
        "alpha": list_cache(ctx.layout["alpha"]),
        "root": list_cache(ctx.layout["hermes_root"]),
        "beta": list_cache(ctx.layout["beta"]),
    }
    report["cache_files"] = cache


def drive_desktop(ctx: Ctx, report: dict[str, Any], *, fail: bool) -> None:
    import queue

    from tui_gateway import server as srv
    from tui_gateway.transport import bind_transport  # noqa: F401  (import check only)

    class Collect:
        def __init__(self) -> None:
            self.frames: queue.Queue[dict[str, Any]] = queue.Queue()

        def write(self, obj: dict[str, Any]) -> bool:
            kind = obj.get("method") or (
                "response" if "result" in obj or "error" in obj else "frame"
            )
            params = obj.get("params") if isinstance(obj.get("params"), dict) else {}
            etype = params.get("type") if isinstance(params, dict) else None
            payload = params.get("payload") if isinstance(params, dict) else None
            fields: dict[str, Any] = {}
            if etype == "tool.complete" and isinstance(payload, dict):
                fields = {
                    "tool_name_class": closed_tool_name(payload.get("name")),
                    "tool_id_is_outer_call": payload.get("tool_id") == CALL_ID,
                }
            ctx.recorder.add("desktop_frame", method=str(kind), etype=str(etype), **fields)
            self.frames.put(obj)
            return True

        def close(self) -> None:
            return None

    transport = Collect()
    resp = srv.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "session.create",
            "params": {"profile": PROFILE, "title": "Bot Chat", "hidden": True},
        },
        transport,
    )
    if resp is None:
        resp = {}
    drained = _wait_frame(transport, lambda f: f.get("id") == 1, 30) if resp == {} else resp
    result = (drained or {}).get("result") or {}
    sid = result.get("session_id")
    report["desktop_session_create_ok"] = bool(sid)
    if not sid:
        report["desktop_session_create_error_present"] = "error" in (drained or {})
        return
    session = srv._sessions.get(sid)
    ready = session["agent_ready"].wait(60) if session else False
    report["desktop_agent_ready"] = bool(ready)
    report["desktop_agent_build_error"] = bool(session and session.get("agent_error"))
    if not ready:
        return
    submit = srv.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "prompt.submit",
            "params": {"session_id": sid, "text": "synthetic request"},
        },
        transport,
    )
    report["desktop_submit_has_inline_error"] = bool(submit and "error" in submit)
    done = _wait_frame(transport, _is_complete_or_error, 90)
    report["desktop_turn_finished"] = done is not None
    time.sleep(1.0)
    key = session.get("session_key") if session else None
    agent = session.get("agent") if session else None
    sids = [s for s in {key, getattr(agent, "session_id", None)} if s]
    report["desktop_session_ids_known"] = len(sids)
    report["desktop_agent_incremental_persistence_failed"] = bool(
        getattr(agent, "_incremental_persistence_failed", False)
    )
    ctx.sids = sids  # type: ignore[attr-defined]
    ctx.db_home = ctx.layout["alpha"]  # type: ignore[attr-defined]


def _is_complete_or_error(frame: dict[str, Any]) -> bool:
    params = frame.get("params") if isinstance(frame.get("params"), dict) else {}
    return params.get("type") in ("message.complete", "error")


def _wait_frame(transport: Any, pred: Any, timeout: float) -> dict[str, Any] | None:
    import queue

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            frame = transport.frames.get(timeout=0.5)
        except queue.Empty:
            continue
        if pred(frame):
            return frame
    return None


def drive_phone(ctx: Ctx, report: dict[str, Any], *, fail: bool) -> None:
    import asyncio
    import dataclasses

    from gateway.config import Platform, PlatformConfig, load_gateway_config
    from gateway.platform_registry import PlatformEntry, platform_registry
    from gateway.platforms.base import BasePlatformAdapter
    from gateway.platforms.event import MessageEvent, MessageType
    from gateway.run import GatewayRunner

    platform_registry.register(
        PlatformEntry(
            name="hmp",
            label="HMP phone fixture",
            adapter_factory=lambda _cfg: None,
            check_fn=lambda: True,
            source="plugin",
            allowed_users_env="HMP_G1_ALLOWED_USERS",
        )
    )
    # Authorization stand-in (HMP's own authz is not exercised): multiplexed authz reads the owning
    # profile's `.env`, so the synthetic allowlist goes there and in the ambient environment.
    os.environ["HMP_G1_ALLOWED_USERS"] = USER_ID
    for home in (ctx.layout["hermes_root"], ctx.layout["alpha"]):
        (home / ".env").write_text(f"HMP_G1_ALLOWED_USERS={USER_ID}\n")
    platform = Platform("hmp")
    recorder = ctx.recorder

    class PhoneShapedAdapter(BasePlatformAdapter):
        """Inert stand-in (NOT HmpAdapter): records sends, delegates media senders to the real
        base."""

        async def connect(self, *, is_reconnect: bool = False) -> bool:
            return True

        async def disconnect(self) -> None:
            return None

        async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
            return {"name": chat_id, "type": "dm"}

        async def send(self, chat_id: str, content: str, reply_to: Any = None, **kw: Any) -> Any:
            from gateway.platforms.base import SendResult

            text = content if isinstance(content, str) else ""
            PRIVATE.setdefault("adapter_sends", []).append(text)
            recorder.add(
                "adapter_send",
                text_len=len(text),
                has_media_tag="MEDIA:" in text,
                send_class=classify_send(text),
                meta_keys=",".join(sorted((kw.get("metadata") or {}).keys())),
            )
            return SendResult(success=True, message_id="m-synth")

        async def send_image_file(self, chat_id: str, image_path: str, *a: Any, **k: Any) -> Any:
            recorder.add("adapter_send_image_file")
            return await super().send_image_file(chat_id, image_path, *a, **k)

        async def send_multiple_images(self, *a: Any, **k: Any) -> Any:
            images = a[1] if len(a) > 1 else k.get("images")
            recorder.add(
                "adapter_send_multiple_images",
                n_images=len(images) if isinstance(images, list) else None,
            )
            return await super().send_multiple_images(*a, **k)

        async def send_document(self, *a: Any, **k: Any) -> Any:
            recorder.add("adapter_send_document")
            return await super().send_document(*a, **k)

        async def send_video(self, *a: Any, **k: Any) -> Any:
            recorder.add("adapter_send_video")
            return await super().send_video(*a, **k)

    config = load_gateway_config()
    runner = GatewayRunner(config)
    adapter = PhoneShapedAdapter(PlatformConfig(enabled=True), platform)
    adapter.gateway_runner = runner
    runner.adapters[platform] = adapter
    adapter.set_session_store(runner.session_store)
    adapter.set_message_handler(runner._handle_message)
    report["phone_multiplex_on"] = bool(runner._multiplex_on())

    source = adapter.build_source(
        chat_id=CHAT_ID,
        chat_type="dm",
        user_id=USER_ID,
        user_name="synthetic",
        scope_id=PROFILE,
        guild_id=PROFILE,
    )
    report["phone_source_profile_is_alpha"] = getattr(source, "profile", None) == PROFILE
    names = {f.name for f in dataclasses.fields(MessageEvent)}
    kwargs: dict[str, Any] = {
        "text": "synthetic request",
        "message_type": MessageType.TEXT,
        "message_id": "m-phone-1",
        "source": source,
        "user_id": USER_ID,
        "user_name": "synthetic",
        "allow_gateway_control": False,
    }
    if "internal" in names:
        kwargs["internal"] = False
    if "defer_policy" in names:
        kwargs["defer_policy"] = "reject"
    event = MessageEvent(**kwargs)

    async def go() -> None:
        recorder.add("phone_handle_message_start")
        await adapter.handle_message(event)
        recorder.add("phone_handle_message_returned")
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if recorder.count("adapter_send") >= 1 and ctx.model.final_responses >= 1:
                break
            await asyncio.sleep(0.2)
        await asyncio.sleep(2.0)  # allow post-send delivery of media to be observed
        tasks = list(getattr(adapter, "_background_tasks", []) or [])
        for t in tasks:
            if not t.done():
                try:  # noqa: SIM105 - best-effort cleanup; swallowing is intended
                    await asyncio.wait_for(asyncio.shield(t), 10)
                except Exception:  # noqa: S110 - best-effort cleanup; swallowing is intended
                    pass

    asyncio.run(go())
    ticket = getattr(event, "admission_ticket", None)
    reported = getattr(getattr(ticket, "reported", None), "value", None)
    report["phone_admission_reported"] = reported if isinstance(reported, str) else None
    entry_ids: list[str] = []
    try:
        entry = runner.session_store._entries.get(next(iter(runner.session_store._entries), ""))
        if entry is not None:
            entry_ids.append(entry.session_id)
    except Exception:  # noqa: S110 - best-effort cleanup; swallowing is intended
        pass
    ctx.sids = entry_ids  # type: ignore[attr-defined]
    ctx.db_home = ctx.layout["alpha"]  # type: ignore[attr-defined]


# --------------------------------------------------------------------------------------------
# Child: G2 history lifecycle (native SessionDB APIs only; no model, provider, route or token)
# --------------------------------------------------------------------------------------------

RESTORE_DIR_NAME = "restore_probe"
HISTORY_SUMMARY = {
    "role": "user",
    "content": "synthetic compaction summary",
    "_compressed_summary": True,
}


def call_id_carriers(row: dict[str, Any]) -> list[dict[str, Any]]:
    calls = row.get("tool_calls")
    if not isinstance(calls, list):
        return []
    return [c for c in calls if isinstance(c, dict) and c.get("id") == CALL_ID]


def row_identity(row: dict[str, Any]) -> str:
    """Short hash over the payload fields a clone keeps byte-exact (never the text itself)."""
    material = json.dumps(
        [
            row.get("role"),
            row.get("content"),
            row.get("tool_calls"),
            row.get("tool_call_id"),
            row.get("tool_name"),
        ],
        sort_keys=True,
        default=str,
    )
    return sha256_bytes(material.encode())[:12]


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Closed per-row facts: id, role, flags, payload identity, call-id carriage."""
    return [
        {
            "id": r.get("id"),
            "role": r.get("role"),
            "active": bool(r.get("active")),
            "compacted": bool(r.get("compacted")),
            "identity": row_identity(r),
            "call_id_in_tool_calls": len(call_id_carriers(r)),
            "tool_call_id_is_expected": r.get("tool_call_id") == CALL_ID,
        }
        for r in rows
    ]


def call_carrier_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Rows carrying the synthetic call id, whatever their active state."""
    return {
        "assistant_rows_with_call": sum(
            1 for r in rows if r.get("role") == "assistant" and call_id_carriers(r)
        ),
        "tool_rows_with_call_id": sum(
            1 for r in rows if r.get("role") == "tool" and r.get("tool_call_id") == CALL_ID
        ),
    }


def pair_observation(rows: list[dict[str, Any]], expected_image: str) -> dict[str, Any]:
    """What an active-only reader would see for the synthetic call, as closed counts and booleans.

    Observation only: it states no eligibility policy and is not a candidate extractor or the
    reference interface. Pass active rows; inactive rows in `rows` are ignored."""
    active = [r for r in rows if r.get("active", True)]
    assistants = [r for r in active if r.get("role") == "assistant" and call_id_carriers(r)]
    tools = [r for r in active if r.get("role") == "tool" and r.get("tool_call_id") == CALL_ID]
    shape: dict[str, Any] | None = None
    if len(assistants) == 1 and len(call_id_carriers(assistants[0])) == 1:
        shape = outer_call_shape(call_id_carriers(assistants[0])[0])
    parsed = parse_json_or_none(tools[0].get("content")) if len(tools) == 1 else None
    result_ok = isinstance(parsed, dict) and parsed.get("success") is True
    image = parsed.get("image") if isinstance(parsed, dict) else None
    one_entry = (
        shape is not None
        and shape["shape"] == "calls_array"
        and shape["entry_count"] == 1
        and shape["entry_names_closed"] == ["image_generate"]
    )
    return {
        "active_assistant_rows_with_call": len(assistants),
        "active_tool_rows_with_call_id": len(tools),
        "assistant_call_is_one_entry_image_generate": one_entry,
        "tool_name_is_image_generate": len(tools) == 1
        and tools[0].get("tool_name") == "image_generate",
        "result_success_true": result_ok,
        "result_image_matches_expected": image == expected_image,
        "complete": bool(
            one_entry
            and len(tools) == 1
            and tools[0].get("tool_name") == "image_generate"
            and result_ok
            and image == expected_image
        ),
    }


def pair_messages(image_path: str, extra_turn: bool = False) -> list[dict[str, Any]]:
    """Fresh synthetic rows: user, one-entry bridge call, successful result, final answer."""
    call = {
        "id": CALL_ID,
        "type": "function",
        "function": {
            "name": "tool_call",
            "arguments": json.dumps(
                {
                    "calls": [
                        {
                            "name": "image_generate",
                            "arguments": {"prompt": "synthetic prompt"},
                        }
                    ]
                }
            ),
        },
    }
    result = {
        "success": True,
        "image": image_path,
        "model": "synthetic",
        "prompt": "synthetic prompt",
        "aspect_ratio": "square",
        "modality": "image",
        "provider": "synthetic",
    }
    rows: list[dict[str, Any]] = [
        {"role": "user", "content": "synthetic request one"},
        {"role": "assistant", "content": None, "tool_calls": [call]},
        {
            "role": "tool",
            "tool_call_id": CALL_ID,
            "tool_name": "image_generate",
            "content": json.dumps(result),
        },
        {"role": "assistant", "content": FINAL_TEXT},
    ]
    if extra_turn:
        rows += [
            {"role": "user", "content": "synthetic request two"},
            {"role": "assistant", "content": "synthetic answer two"},
        ]
    return rows


def validate_restore_target(target: Path, root: Path, primary_db: Path) -> None:
    """The only database `_safe_restore_db` may write: `<scratch>/.../restore_probe/state.db`,
    a real file, never the scenario's primary database, never in or holding a live Hermes home."""
    resolved_root = root.resolve()
    if (
        not target.is_absolute()
        or target.name != "state.db"
        or target.parent.name != RESTORE_DIR_NAME
    ):
        raise FixtureSafetyError("restore_target_shape")
    for part in (target, target.parent):
        try:
            mode = part.lstat().st_mode
        except OSError:
            raise FixtureSafetyError("restore_target_missing") from None
        if stat.S_ISLNK(mode):
            raise FixtureSafetyError("restore_target_is_symlink")
    if not stat.S_ISREG(target.lstat().st_mode):
        raise FixtureSafetyError("restore_target_not_regular")
    resolved = target.resolve()
    if resolved_root not in resolved.parents:
        raise FixtureSafetyError("restore_target_outside_scratch")
    refuse_inside_real_hermes(resolved, "restore_target_inside_real_hermes_home", containing=True)
    if resolved == primary_db.resolve():
        raise FixtureSafetyError("restore_target_is_primary_db")


def tool_image_in_dir(rows: list[dict[str, Any]], directory: Path) -> bool:
    """Whether every active result row's top-level `image` names a file directly inside `directory`
    (a path comparison only; nothing is opened)."""
    images = [
        parse_json_or_none(r.get("content"))
        for r in rows
        if r.get("active") and r.get("role") == "tool"
    ]
    return bool(images) and all(
        isinstance(i, dict)
        and isinstance(i.get("image"), str)
        and Path(i["image"]).parent == directory
        for i in images
    )


def file_facts(path: Path) -> dict[str, Any]:
    info = path.stat()
    return {"dev_ino": [info.st_dev, info.st_ino], "mode": oct(info.st_mode & 0o777)}


def run_step(steps: dict[str, Any], name: str, fn: Any) -> None:
    """One observation. A native API raising is itself an observation (closed type name only)."""
    try:
        steps[name] = fn()
    except FixtureSafetyError as exc:
        steps[name] = {"status": "fixture_safety_refusal", "reason": str(exc)}
    except Exception as exc:
        tb = traceback.extract_tb(exc.__traceback__)
        lines = [f.lineno for f in tb if f.filename == str(HERE)]
        steps[name] = {
            "status": "api_error",
            "error_type": type(exc).__name__,
            "fixture_line": lines[-1] if lines else None,
        }


class HistoryLab:
    """Disposable synthetic sessions in one scratch SessionDB, mutated only through native APIs."""

    def __init__(self, db: Any, image: str, layout: dict[str, Path]) -> None:
        self.db, self.image, self.layout = db, image, layout
        self.private: dict[str, Any] = {}

    def rows(self, sid: str) -> list[dict[str, Any]]:
        return self.db.get_messages(sid, include_inactive=True)

    def active(self, sid: str) -> list[dict[str, Any]]:
        return self.db.get_messages(sid)

    def seed(self, sid: str, *, extra_turn: bool = False, **session_kwargs: Any) -> list[int]:
        self.db.create_session(sid, source="synthetic", **session_kwargs)
        self.db.append_messages_batch(sid, pair_messages(self.image, extra_turn))
        return [int(r["id"]) for r in self.rows(sid)]

    def view(self, sid: str) -> dict[str, Any]:
        rows = self.rows(sid)
        self.private.setdefault("rows", {}).setdefault(sid, []).append(rows)
        active = [r for r in rows if r.get("active")]
        return {
            "rows": summarize_rows(rows),
            "active_read_ids": [int(r["id"]) for r in self.active(sid)],
            "carriers_all_rows": call_carrier_counts(rows),
            "pair_active": pair_observation(active, self.image),
        }

    def counts(self, sid: str) -> dict[str, Any]:
        session = self.db.get_session(sid) or {}
        return {k: session.get(k) for k in ("message_count", "tool_call_count", "rewind_count")}


def clone_facts(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two `HistoryLab.view` results of one session around a native mutation."""
    was_active = {r["id"]: r["active"] for r in before["rows"]}
    carriers = {
        r["id"]
        for r in before["rows"]
        if r["call_id_in_tool_calls"] or r["tool_call_id_is_expected"]
    }
    old_pair = [r for r in after["rows"] if r["id"] in carriers]
    fresh = [r for r in after["rows"] if r["active"] and r["id"] not in was_active]
    fresh_pair = [r for r in fresh if r["call_id_in_tool_calls"] or r["tool_call_id_is_expected"]]
    before_pair = [r for r in before["rows"] if r["id"] in carriers]
    return {
        "old_pair_flags": [[r["active"], r["compacted"]] for r in old_pair],
        "old_pair_all_inactive": all(not r["active"] for r in old_pair),
        "fresh_active_rows": len(fresh),
        "fresh_active_pair_rows": len(fresh_pair),
        "fresh_ids_above_previous_max": all(r["id"] > max(was_active) for r in fresh),
        "inactive_rows_reactivated": sum(
            1 for r in after["rows"] if r["active"] and was_active.get(r["id"]) is False
        ),
        "fresh_pair_identities_equal_old": (
            sorted(r["identity"] for r in fresh_pair) == sorted(r["identity"] for r in before_pair)
            if fresh_pair
            else None
        ),
    }


def step_baseline(lab: HistoryLab) -> dict[str, Any]:
    ids = lab.seed("s_base")
    view = lab.view("s_base")
    return {
        "seeded_ids": ids,
        "view": view,
        "counts": lab.counts("s_base"),
        "default_read_equals_active_rows": view["active_read_ids"]
        == [r["id"] for r in view["rows"] if r["active"]],
    }


def step_compaction_full(lab: HistoryLab) -> dict[str, Any]:
    """`archive_and_compact` with the pair as the concurrent tail (watermark below the call row)."""
    sid = "s_cmp_full"
    ids = lab.seed(sid)
    before = lab.view(sid)
    tip_before = lab.db.resolve_resume_session_id(sid)
    count = lab.db.archive_and_compact(sid, [dict(HISTORY_SUMMARY)], watermark=ids[0])
    tip_after = lab.db.resolve_resume_session_id(sid)
    after = lab.view(sid)
    return {
        "returned_active_count": count,
        "view": after,
        "facts": clone_facts(before, after),
        "counts": lab.counts(sid),
        "carriers_before": before["carriers_all_rows"],
        "tip_id_unchanged_while_active_ids_changed": tip_before == tip_after == sid
        and before["active_read_ids"] != after["active_read_ids"],
        "display_view_pair_carriers": call_carrier_counts(
            lab.db.get_messages(sid, include_compacted=True)
        ),
    }


def step_compaction_half(lab: HistoryLab) -> dict[str, Any]:
    """Watermark between the call row and its result: only the result (and later rows) is cloned."""
    sid = "s_cmp_half"
    ids = lab.seed(sid)
    before = lab.view(sid)
    count = lab.db.archive_and_compact(sid, [dict(HISTORY_SUMMARY)], watermark=ids[1])
    after = lab.view(sid)
    return {
        "returned_active_count": count,
        "view": after,
        "facts": clone_facts(before, after),
        "counts": lab.counts(sid),
        "display_view_pair_carriers": call_carrier_counts(
            lab.db.get_messages(sid, include_compacted=True)
        ),
    }


def step_replace_archive(lab: HistoryLab) -> dict[str, Any]:
    sid = "s_rep_arch"
    lab.seed(sid)
    before = lab.view(sid)
    lab.db.replace_messages(
        sid,
        [
            pair_messages(lab.image)[0],
            {"role": "assistant", "content": "synthetic replacement"},
        ],
        archive_dropped=True,
    )
    after = lab.view(sid)
    keep = "s_rep_keep"
    keep_ids = lab.seed(keep)
    keep_before = lab.view(keep)
    lab.db.replace_messages(
        keep,
        [*pair_messages(lab.image), {"role": "assistant", "content": "synthetic appended"}],
        archive_dropped=True,
    )
    keep_after = lab.view(keep)
    return {
        "diverging": {
            "view": after,
            "facts": clone_facts(before, after),
            "counts": lab.counts(sid),
        },
        "identical_prefix": {
            "view": keep_after,
            "facts": clone_facts(keep_before, keep_after),
            "original_ids_still_active": [
                r["active"] for r in keep_after["rows"] if r["id"] in keep_ids
            ],
            "counts": lab.counts(keep),
        },
    }


def step_replace_delete(lab: HistoryLab) -> dict[str, Any]:
    sid = "s_rep_del"
    old_ids = lab.seed(sid)
    before = lab.view(sid)
    lab.db.replace_messages(
        sid,
        [
            pair_messages(lab.image)[0],
            {"role": "assistant", "content": "synthetic replacement"},
        ],
    )
    mid = lab.view(sid)
    lab.db.append_messages_batch(sid, pair_messages(lab.image)[1:])
    again = lab.view(sid)
    again_ids = [r["id"] for r in again["rows"]]
    return {
        "after_replace": mid,
        "old_row_ids_still_present_in_audit_read": sorted(
            set(old_ids) & {r["id"] for r in mid["rows"]}
        ),
        "pair_carriers_after_replace": mid["carriers_all_rows"],
        "after_reappend": again,
        "reappended_pair_active_ids_reuse_deleted_ids": bool(
            set(old_ids[1:]) & set(again_ids[-3:])
        ),
        "reappended_identities_equal_deleted": sorted(r["identity"] for r in again["rows"][-3:])
        == sorted(r["identity"] for r in before["rows"][1:]),
        "counts": lab.counts(sid),
    }


def step_rewind(lab: HistoryLab) -> dict[str, Any]:
    early, late = "s_rew_early", "s_rew_late"
    ids = lab.seed(early, extra_turn=True)
    before = lab.view(early)
    result = lab.db.rewind_to_message(early, ids[0])
    after = lab.view(early)
    late_ids = lab.seed(late, extra_turn=True)
    late_before = lab.view(late)
    late_result = lab.db.rewind_to_message(late, late_ids[4])
    late_after = lab.view(late)
    return {
        "rewind_to_first_user": {
            "result_keys": sorted(result),
            "rewound_count": result.get("rewound_count"),
            "view": after,
            "facts": clone_facts(before, after),
            "counts": lab.counts(early),
        },
        "rewind_to_second_user": {
            "rewound_count": late_result.get("rewound_count"),
            "pair_survives": late_after["pair_active"]["complete"],
            "pair_ids_unchanged": [r["id"] for r in late_before["rows"] if r["active"]][:4]
            == [r["id"] for r in late_after["rows"] if r["active"]][:4],
            "view": late_after,
            "counts": lab.counts(late),
        },
    }


def step_deactivate(lab: HistoryLab) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, index in (("result_row", 2), ("call_row", 1)):
        sid = f"s_deact_{label}"
        ids = lab.seed(sid)
        first = lab.db.deactivate_message(sid, ids[index])
        second = lab.db.deactivate_message(sid, ids[index])
        out[label] = {
            "first_returned": first,
            "second_returned": second,
            "view": lab.view(sid),
            "counts": lab.counts(sid),
        }
    return out


def step_clear(lab: HistoryLab) -> dict[str, Any]:
    sid = "s_clear"
    old_ids = lab.seed(sid)
    before = lab.view(sid)
    lab.db.clear_messages(sid)
    cleared = lab.view(sid)
    lab.db.append_messages_batch(sid, pair_messages(lab.image))
    again = lab.view(sid)
    return {
        "rows_after_clear_audit_read": len(cleared["rows"]),
        "reseeded_ids_reuse_cleared_ids": bool(set(old_ids) & {r["id"] for r in again["rows"]}),
        "reseeded_pair_complete": again["pair_active"]["complete"],
        "reseeded_identities_equal_cleared": sorted(r["identity"] for r in again["rows"])
        == sorted(r["identity"] for r in before["rows"]),
    }


def step_child_compression(lab: HistoryLab) -> dict[str, Any]:
    """`publish_compression_child` with the pair as the parent's concurrent tail, plus the
    tip-then-read interleave: a tip chosen before publication, rows read after it."""
    parent, child = "s_cc_parent", "s_cc_child"
    ids = lab.seed(parent)
    before = lab.view(parent)
    tip_before = lab.db.resolve_resume_session_id(parent)
    lab.db.publish_compression_child(
        parent_session_id=parent,
        child_session_id=child,
        source="synthetic",
        messages=[dict(HISTORY_SUMMARY)],
        watermark=ids[0],
        require_compression_lease=False,
    )
    stale = lab.view(tip_before)
    fresh_tip = lab.db.resolve_resume_session_id(parent)
    fresh = lab.view(fresh_tip)
    model_history, display_history = lab.db.get_resume_conversations(parent)
    parent_session = lab.db.get_session(parent) or {}
    return {
        "tip_before_publish_is_parent": tip_before == parent,
        "fresh_tip_is_child": fresh_tip == child,
        "compression_tip_matches": lab.db.get_compression_tip(parent) == child,
        "parent_end_reason": parent_session.get("end_reason"),
        "parent_rows_unchanged_after_publish": stale["rows"] == before["rows"],
        "stale_tip_pair_still_active": stale["pair_active"]["complete"],
        "fresh_tip_pair_active": fresh["pair_active"]["complete"],
        "stale_and_fresh_active_ids_disjoint": not set(stale["active_read_ids"])
        & set(fresh["active_read_ids"]),
        "child_view": fresh,
        "child_counts": lab.counts(child),
        "resume_conversations_given_parent": {
            "model_history_rows": len(model_history),
            "display_history_rows": len(display_history),
            "model_history_has_call_pair": any(
                isinstance(m.get("tool_calls"), list) and m.get("tool_calls") for m in model_history
            ),
        },
    }


def step_branch(lab: HistoryLab) -> dict[str, Any]:
    """Desktop branch via the native `_persist_branch`; gateway-shaped copy via the native
    `_branch_row` helper applied through public SessionDB calls (the async `/branch` handler is
    NOT run)."""
    parent = "s_br_parent"
    lab.seed(parent)
    history = lab.active(parent)
    out: dict[str, Any] = {}
    from tui_gateway.methods_session import _BRANCH_COPY_FIELDS, _persist_branch

    _persist_branch(
        lab.db,
        "s_br_desktop",
        parent,
        "synthetic branch",
        history,
        source="synthetic",
        cwd=str(lab.layout["cwd"]),
        profile_name=PROFILE,
        model="synthetic-model",
        copy_fields=_BRANCH_COPY_FIELDS,
    )
    desktop = lab.view("s_br_desktop")
    out["desktop_persist_branch"] = {
        "view": desktop,
        "tool_rows_copied": sum(1 for r in desktop["rows"] if r["role"] == "tool"),
        "tool_call_id_columns_copied": sum(
            1 for r in desktop["rows"] if r["tool_call_id_is_expected"]
        ),
        "assistant_call_columns_copied": sum(r["call_id_in_tool_calls"] for r in desktop["rows"]),
    }
    from gateway.slash_commands_session import _branch_row

    conversation = lab.db.get_messages_as_conversation(parent)
    lab.db.create_session(
        "s_br_gateway_shape",
        source="synthetic",
        model_config={"_branched_from": parent},
        parent_session_id=parent,
    )
    lab.db.append_messages_batch(
        "s_br_gateway_shape", [_branch_row(m) for m in conversation], chunk_rows=500
    )
    gateway = lab.view("s_br_gateway_shape")
    out["gateway_branch_row_helper_via_public_api"] = {
        "history_input": "get_messages_as_conversation (not the handler's load_transcript)",
        "view": gateway,
    }
    out["parent_resume_unchanged_by_branch_children"] = (
        lab.db.resolve_resume_session_id(parent) == parent
        and lab.db.get_compression_tip(parent) == parent
    )
    out["branched_from_marker_on_desktop_child"] = "_branched_from" in str(
        (lab.db.get_session("s_br_desktop") or {}).get("model_config")
    )
    return out


def step_import(lab: HistoryLab) -> dict[str, Any]:
    parent = "s_imp_parent"
    lab.seed(parent)
    exported = lab.db.export_session(parent) or {}
    foreign = str(lab.layout["tmp"] / "outside_profile_cache.png")

    def payload(sid: str, *, parent_id: str | None, image: Any = None) -> dict[str, Any]:
        data = json.loads(json.dumps(exported, default=str))
        data["id"], data["parent_session_id"] = sid, parent_id
        if image is not None:
            for message in data["messages"]:
                if message.get("role") == "tool":
                    body = json.loads(message["content"])
                    body["image"] = image
                    message["content"] = json.dumps(body)
        return data

    out: dict[str, Any] = {"exported_message_rows": len(exported.get("messages", []))}
    source_ids = {r["id"] for r in lab.rows(parent)}
    variants = (
        ("same_profile_root", "s_imp_root", None, None, lab.image),
        ("with_parent_edge", "s_imp_child", parent, None, lab.image),
        ("foreign_path", "s_imp_foreign", None, foreign, foreign),
        ("non_string_image", "s_imp_invalid", None, 12345, 12345),
    )
    for label, sid, parent_id, override, expected in variants:
        result = lab.db.import_sessions([payload(sid, parent_id=parent_id, image=override)])
        view = lab.view(sid)
        images = [
            (parse_json_or_none(r.get("content")) or {}).get("image")
            for r in lab.rows(sid)
            if r.get("active") and r.get("role") == "tool"
        ]
        out[label] = {
            "import_ok": result.get("ok"),
            "imported": result.get("imported"),
            "errors": len(result.get("errors", [])),
            "detached": result.get("detached"),
            "view": view,
            "ids_disjoint_from_source": not source_ids & {r["id"] for r in view["rows"]},
            "image_value_stored_verbatim": images == [expected],
            "image_in_selected_profile_cache": tool_image_in_dir(
                lab.rows(sid), Path(lab.image).parent
            ),
        }
    out["resume_selector_follows_imported_parent_edge_child"] = (
        lab.db.resolve_resume_session_id(parent) == "s_imp_child"
    )
    out["compression_tip_follows_imported_parent_edge_child"] = (
        lab.db.get_compression_tip(parent) == "s_imp_child"
    )
    out["imported_session_source_and_origin"] = {
        "source_preserved": (lab.db.get_session("s_imp_root") or {}).get("source") == "synthetic",
        "origin_json_empty": not (lab.db.get_session("s_imp_root") or {}).get("origin_json"),
    }
    return out


def restore_state(lab: HistoryLab, target: Path, primary_sids: tuple[str, ...]) -> dict[str, Any]:
    """Everything the restore probe compares, read through the lab's SessionDB handle."""
    from hermes_state_errors import _STATE_DB_GENERATION_KEY

    db = lab.db
    sessions = {sid: db.get_session(sid) or {} for sid in primary_sids}
    return {
        "views": {sid: lab.view(sid) for sid in primary_sids},
        "session_fields": {
            sid: {
                k: sessions[sid].get(k)
                for k in (
                    "message_count",
                    "tool_call_count",
                    "rewind_count",
                    "end_reason",
                )
            }
            for sid in primary_sids
        },
        "conversation_generation": db.latest_conversation_boundary("synth-key-b", "synthetic"),
        "file_stamp_sha": sha256_bytes((db.get_meta(_STATE_DB_GENERATION_KEY) or "").encode())[:12],
        "application_id": getattr(db, "_db_file_application_id", None),
        "file": file_facts(target),
        "sidecars": {
            suffix: Path(str(target) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")
        },
    }


def guarded_restore(restore: Any, snapshot: Path, target: Path, root: Path, primary: Path) -> Any:
    """Re-validate the target at the restore boundary, then call the native restore."""
    validate_restore_target(target, root, primary)
    return restore(snapshot, target)


def public_restore_state(state: dict[str, Any]) -> dict[str, Any]:
    """The report copy of a restore state: raw device/inode numbers stay out of it."""
    return {
        **state,
        "file": {k: v for k, v in state["file"].items() if k != "dev_ino"},
    }


def step_restore(lab: HistoryLab, root: Path) -> dict[str, Any]:
    """Same-inode backup restore into a dedicated disposable profile database, using the native
    `_safe_copy_db` snapshot and the native `_safe_restore_db` page copy. Nothing else is
    written."""
    from hermes_cli.backup_restore import _safe_restore_db
    from hermes_cli.backup_sqlite import _safe_copy_db
    from hermes_state import SessionDB

    rdir = lab.layout["alpha"] / RESTORE_DIR_NAME
    rdir.mkdir(mode=0o700)
    target, snapshot = rdir / "state.db", rdir / "snapshot.db"
    primary = lab.layout["alpha"] / "state.db"
    old = SessionDB(target)
    rl = HistoryLab(old, lab.image, lab.layout)
    rl.seed("rs_a", session_key="synth-key-a")
    old.create_session("rs_b", source="synthetic", session_key="synth-key-b")
    rl.seed("rs_c", extra_turn=True)
    validate_restore_target(target, root, primary)
    sids = ("rs_a", "rs_b", "rs_c")
    at_snapshot = restore_state(rl, target, sids)
    copied = _safe_copy_db(target, snapshot)
    snapshot_sha = sha256_file(snapshot)[:12]

    # Later history on the same handle: compaction retires the pair, a reset boundary advances the
    # conversation generation, a rewind bumps rewind_count, and a new row takes a new id.
    first_id = int(rl.rows("rs_a")[0]["id"])
    old.archive_and_compact("rs_a", [dict(HISTORY_SUMMARY)], watermark=first_id)
    old.end_session("rs_b", "session_reset")
    c_ids = [int(r["id"]) for r in rl.rows("rs_c")]
    old.rewind_to_message("rs_c", c_ids[0])
    later = restore_state(rl, target, sids)
    later_max_id = max(int(r["id"]) for sid in sids for r in rl.rows(sid))
    later_ids = {int(r["id"]) for sid in sids for r in rl.rows(sid)}
    restored = guarded_restore(_safe_restore_db, snapshot, target, root, primary)

    reader = SessionDB(target)  # a fresh handle, as a new process would open
    fresh = HistoryLab(reader, lab.image, lab.layout)
    after_fresh = restore_state(fresh, target, sids)
    after_old = restore_state(rl, target, sids)  # the pre-restore handle, never closed
    replaced_probe = getattr(old, "_db_file_was_replaced", None)
    old_write: dict[str, Any]
    try:
        old.append_messages_batch("rs_a", [{"role": "user", "content": "synthetic after restore"}])
        old_write = {"ok": True}
    except Exception as exc:
        old_write = {"ok": False, "error_type": type(exc).__name__}
    new_id = max(int(r["id"]) for r in fresh.rows("rs_a"))
    reader.close()
    old.close()

    def same(left: dict[str, Any], right: dict[str, Any], key: str) -> bool:
        return left[key] == right[key]

    # Compare on the raw states first; the raw numbers go to the private evidence only.
    same_inode_and_device = at_snapshot["file"]["dev_ino"] == after_fresh["file"]["dev_ino"]
    inode_unchanged_across_later_and_restore = (
        later["file"]["dev_ino"] == after_fresh["file"]["dev_ino"]
    )
    PRIVATE["restore_file_identity"] = {
        "at_snapshot": at_snapshot["file"]["dev_ino"],
        "later": later["file"]["dev_ino"],
        "after_restore_fresh_handle": after_fresh["file"]["dev_ino"],
    }

    return {
        "snapshot_copied": copied,
        "snapshot_sha12": snapshot_sha,
        "restore_returned": restored,
        "at_snapshot": public_restore_state(at_snapshot),
        "later": public_restore_state(later),
        "after_restore_fresh_handle": public_restore_state(after_fresh),
        "after_restore_old_handle": public_restore_state(after_old),
        "restored_views_equal_snapshot_views": same(at_snapshot, after_fresh, "views"),
        "restored_views_differ_from_later_views": later["views"] != after_fresh["views"],
        "old_handle_converges_with_fresh_handle": after_old["views"] == after_fresh["views"],
        "same_inode_and_device": same_inode_and_device,
        "inode_unchanged_across_later_and_restore": inode_unchanged_across_later_and_restore,
        "pair_active_at_snapshot": at_snapshot["views"]["rs_a"]["pair_active"]["complete"],
        "pair_active_after_later_compaction_original_ids": any(
            r["active"] and r["call_id_in_tool_calls"]
            for r in later["views"]["rs_a"]["rows"]
            if r["id"] in {x["id"] for x in at_snapshot["views"]["rs_a"]["rows"]}
        ),
        "pair_active_after_restore_original_ids": after_fresh["views"]["rs_a"]["pair_active"][
            "complete"
        ],
        "conversation_generation": {
            "at_snapshot": at_snapshot["conversation_generation"],
            "later": later["conversation_generation"],
            "after_restore": after_fresh["conversation_generation"],
        },
        "rewind_count_rs_c": {
            "at_snapshot": at_snapshot["session_fields"]["rs_c"]["rewind_count"],
            "later": later["session_fields"]["rs_c"]["rewind_count"],
            "after_restore": after_fresh["session_fields"]["rs_c"]["rewind_count"],
        },
        "file_stamp_unchanged_by_restore": same(at_snapshot, after_fresh, "file_stamp_sha"),
        "application_id_unchanged_by_restore": same(at_snapshot, after_fresh, "application_id"),
        "old_handle_reports_file_replaced": replaced_probe() if callable(replaced_probe) else None,
        "old_handle_write_after_restore": old_write,
        "id_taken_after_restore_was_used_in_later_timeline": new_id in later_ids,
        "later_timeline_max_id_above_snapshot_max": later_max_id
        > max(int(r["id"]) for sid in sids for r in at_snapshot["views"][sid]["rows"]),
    }


def drive_history(ctx: Ctx) -> dict[str, Any]:
    from hermes_state import SessionDB

    layout = ctx.layout
    cache = layout["alpha"] / "cache" / "images"
    cache.mkdir(parents=True, mode=0o700)
    image = cache / "synthetic_history_0001.png"
    png = synthetic_png()
    with os.fdopen(open_private_exclusive(image), "wb") as handle:
        handle.write(png)
    db = SessionDB(layout["alpha"] / "state.db")
    lab = HistoryLab(db, str(image), layout)
    steps: dict[str, Any] = {
        "cache_file_is_synthetic_png": image.read_bytes() == png,
        "cache_file_sha_matches_helper": sha256_file(image) == sha256_bytes(png),
    }
    for name, fn in (
        ("baseline", lambda: step_baseline(lab)),
        ("compaction_full_tail_clone", lambda: step_compaction_full(lab)),
        ("compaction_half_tail_clone", lambda: step_compaction_half(lab)),
        ("replace_messages_archive", lambda: step_replace_archive(lab)),
        ("replace_messages_delete", lambda: step_replace_delete(lab)),
        ("rewind", lambda: step_rewind(lab)),
        ("deactivate_message", lambda: step_deactivate(lab)),
        ("clear_messages", lambda: step_clear(lab)),
        ("child_compression", lambda: step_child_compression(lab)),
        ("branch", lambda: step_branch(lab)),
        ("import", lambda: step_import(lab)),
        ("backup_restore", lambda: step_restore(lab, ctx.root)),
    ):
        run_step(steps, name, fn)
    steps["cache_file_unchanged_after_all_steps"] = image.read_bytes() == png
    steps["not_run"] = [
        "gateway_branch_handler",  # async handler needs a live runner; helper-level copy only
        "cli_branch",  # HermesCLI._handle_branch_command needs a live CLI object
        "api_server_branch",
        "rewind_user_turn",
        "compaction_with_covered_ids",
        "restore_of_snapshot_from_a_different_database_file",
        "swapped_file_new_inode",
        "concurrent_second_process",
    ]
    db.close()
    PRIVATE["history_rows"] = lab.private
    steps["native_sources"] = {
        name: sha256_file(ctx.native_src / name)[:12] for name in OWNING_FILES + HISTORY_EXTRA_FILES
    }
    return steps


def run_history_child(native_src: Path, root: Path, scenario: str) -> dict[str, Any]:
    sys.path.insert(0, str(native_src))
    os.chdir(os.environ.get("PWD", str(root / "cwd")))
    ctx = Ctx(root, native_src)
    os.umask(0o022)  # native default mode is observed, not the harness's inherited umask
    install_ip_denial()  # no loopback port is allowed: this scenario has no model server
    report: dict[str, Any] = {
        "scenario": scenario,
        "surface": "session_db_only",
        "fault_injected": False,
        "isolation": isolation_checks(ctx),
    }

    def finish() -> None:
        report["runtime_identity"] = runtime_identity(ctx)
        report["network"] = {
            "ip_connects_blocked": _BLOCKED["ip_blocked"],
            "unix_contacts_blocked": _BLOCKED["unix_blocked"],
            "loopback_synthetic_connects_allowed": _BLOCKED["loopback_synthetic_allowed"],
        }

    try:
        report["steps"] = drive_history(ctx)
        finish()
        report["status"] = "COMPLETED"
    except Exception as exc:  # closed type name and fixture line only
        tb = traceback.extract_tb(exc.__traceback__)
        fixture_lines = [f.lineno for f in tb if f.filename == str(HERE)]
        report["status"] = "ERROR"
        report["error_type"] = type(exc).__name__
        report["error_fixture_line"] = fixture_lines[-1] if fixture_lines else None
        try:  # noqa: SIM105 - best-effort cleanup; swallowing is intended
            finish()
        except Exception:  # noqa: S110 - best-effort cleanup; swallowing is intended
            pass
    return report


def run_child(native_src: Path, root: Path, scenario: str) -> dict[str, Any]:
    if scenario in HISTORY_SCENARIOS:
        return run_history_child(native_src, root, scenario)
    sys.path.insert(0, str(native_src))
    os.chdir(os.environ.get("PWD", str(root / "cwd")))
    shape = BRIDGE_SHAPES.get(scenario)
    bridge = shape is not None
    ctx = Ctx(root, native_src, shape=shape)
    ctx.sids = []  # type: ignore[attr-defined]
    ctx.db_home = ctx.layout["alpha"]  # type: ignore[attr-defined]
    os.umask(0o022)  # native default mode is observed, not the harness's inherited umask
    install_ip_denial()
    port = ctx.model.start()
    surface = "desktop" if scenario.startswith("desktop") else "phone"
    fail = scenario.endswith("flushfail")
    write_config(
        ctx.layout["hermes_root"], port, routes=(surface == "phone"), tool_search_off=not bridge
    )
    write_config(ctx.layout["alpha"], port, routes=False, tool_search_off=not bridge)
    write_config(ctx.layout["beta"], port, routes=False, tool_search_off=not bridge)
    report: dict[str, Any] = {
        "scenario": scenario,
        "surface": surface,
        "fault_injected": fail,
        "isolation": isolation_checks(ctx),
    }
    try:
        register_synthetic_provider(ctx.recorder, ctx.produced)
        install_db_observer(ctx.recorder, fail_tool_batch=fail)
        report["precheck"] = precheck()
        if surface == "desktop":
            drive_desktop(ctx, report, fail=fail)
        else:
            drive_phone(ctx, report, fail=fail)
        alpha = ctx.layout["alpha"]
        report["alpha_db"] = session_inventory(alpha / "state.db")
        report["root_db_sessions"] = len(
            session_inventory(ctx.layout["hermes_root"] / "state.db")["ids"]
        )
        report["beta_db_sessions"] = len(session_inventory(ctx.layout["beta"] / "state.db")["ids"])
        sids = [s for s in ctx.sids if s] or report["alpha_db"]["ids"]  # type: ignore[attr-defined]
        report["rows_alpha_db"] = inspect_rows(
            alpha / "state.db",
            sids,
            alpha / "cache" / "images",
            ctx.layout["beta"] / "cache" / "images",
            ctx.produced,
            ctx.cap,
        )
        root_sids = session_inventory(ctx.layout["hermes_root"] / "state.db")["ids"]
        if root_sids:
            report["rows_root_db"] = inspect_rows(
                ctx.layout["hermes_root"] / "state.db",
                root_sids,
                ctx.layout["hermes_root"] / "cache" / "images",
                ctx.layout["beta"] / "cache" / "images",
                ctx.produced,
                ctx.cap,
            )
        rec = ctx.recorder
        flush_tool = rec.first("db_batch", has_tool=True)
        tool_seq_fail = rec.first("db_batch_injected_failure")
        report["order"] = {
            "provider_saved_seq": rec.first("provider_saved"),
            "tool_row_batch_seq": flush_tool,
            "provider_before_tool_row_batch": (
                rec.first("provider_saved") is not None
                and flush_tool is not None
                and rec.first("provider_saved") < flush_tool
            ),
            "tool_row_batch_injected_failure_seq": tool_seq_fail,
            "tool_row_batch_injected_failures": rec.count("db_batch_injected_failure"),
            "db_batches_total": rec.count("db_batch"),
            "db_batches_with_tool": rec.count("db_batch", has_tool=True),
        }
        if surface == "desktop":
            tool_completed = [
                e["seq"]
                for e in rec.events
                if e["kind"] == "desktop_frame" and e.get("etype") == "tool.complete"
            ]
            report["order"]["desktop_tool_completed_frames"] = len(tool_completed)
            report["order"]["desktop_tool_completed_name_classes"] = [
                e.get("tool_name_class")
                for e in rec.events
                if e["kind"] == "desktop_frame" and e.get("etype") == "tool.complete"
            ]
            report["order"]["desktop_tool_completed_id_is_outer_call"] = [
                e.get("tool_id_is_outer_call")
                for e in rec.events
                if e["kind"] == "desktop_frame" and e.get("etype") == "tool.complete"
            ]
            report["order"]["tool_row_batch_before_first_tool_completed_frame"] = (
                flush_tool is not None and bool(tool_completed) and flush_tool < min(tool_completed)
            )
        else:
            send_seqs = [e["seq"] for e in rec.events if e["kind"] == "adapter_send"]
            media_seqs = [e["seq"] for e in rec.events if e["kind"].startswith("adapter_send_")]
            report["order"]["adapter_sends"] = len(send_seqs)
            report["order"]["adapter_media_calls"] = len(media_seqs)
            report["order"]["adapter_send_multiple_images_calls"] = rec.count(
                "adapter_send_multiple_images"
            )
            report["order"]["adapter_send_multiple_images_n_images"] = [
                e.get("n_images") for e in rec.events if e["kind"] == "adapter_send_multiple_images"
            ]
            report["order"]["adapter_send_image_file_calls"] = rec.count("adapter_send_image_file")
            report["order"]["tool_row_batch_before_first_adapter_send"] = (
                flush_tool is not None and bool(send_seqs) and flush_tool < min(send_seqs)
            )
            reply_seqs = [
                e["seq"]
                for e in rec.events
                if e["kind"] == "adapter_send" and e["send_class"] not in ("home_channel_notice",)
            ]
            report["order"]["first_send_is_home_channel_notice_before_any_db_write"] = bool(
                send_seqs
                and rec.events[send_seqs[0]]["send_class"] == "home_channel_notice"
                and (rec.first("db_batch") or 0) > send_seqs[0]
            )
            report["order"]["tool_row_batch_before_first_reply_send"] = (
                flush_tool is not None and bool(reply_seqs) and flush_tool < min(reply_seqs)
            )
            report["order"]["tool_row_batch_before_first_media_call"] = (
                flush_tool is not None and bool(media_seqs) and flush_tool < min(media_seqs)
            )
            report["order"]["any_send_text_has_media_tag"] = any(
                e.get("has_media_tag") for e in rec.events if e["kind"] == "adapter_send"
            )
        finish_common(ctx, report)
        rows = report["rows_alpha_db"]
        report["cache_file_without_authoritative_row"] = (
            report["cache_files"]["alpha"]["count"] == 1
            and rows.get("tool_rows") == 0
            and rows.get("assistant_call_id_matches_expected") is True
        )
        report["send_classes"] = [
            e["send_class"] for e in rec.events if e["kind"] == "adapter_send"
        ]
        report["status"] = "COMPLETED"
    except Exception as exc:  # closed type name and fixture line only
        tb = traceback.extract_tb(exc.__traceback__)
        fixture_lines = [f.lineno for f in tb if f.filename == str(HERE)]
        report["status"] = "ERROR"
        report["error_type"] = type(exc).__name__
        report["error_fixture_line"] = fixture_lines[-1] if fixture_lines else None
        try:  # noqa: SIM105 - best-effort cleanup; swallowing is intended
            finish_common(ctx, report)
        except Exception:  # noqa: S110 - best-effort cleanup; swallowing is intended
            pass
    finally:
        ctx.model.stop()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--native-src", type=Path, default=DEFAULT_NATIVE_SRC)
    run.add_argument("--scenario", action="append", choices=ALL_SCENARIOS)
    run.add_argument("--evidence", type=Path)
    child = sub.add_parser("child")
    child.add_argument("--native-src", type=Path, required=True)
    child.add_argument("--root", type=Path, required=True)
    child.add_argument("--scenario", choices=ALL_SCENARIOS, required=True)
    args = parser.parse_args(argv)
    if args.cmd == "child":
        try:  # validated before sys.path changes or any native import
            validate_native_src(args.native_src)
            validate_scratch_root(args.root, args.native_src)
        except FixtureSafetyError as exc:
            sys.stdout.write(json.dumps({"status": "REFUSED", "reason": exc.reason}) + "\n")
            return 2
        child_report = run_child(args.native_src, args.root, args.scenario)
        child_report["_private"] = PRIVATE
        write_private(args.root / "result.json", json.dumps(child_report, default=str))
        return 0
    try:
        report = run_parent(args.native_src, tuple(args.scenario or SCENARIOS), args.evidence)
    except FixtureSafetyError as exc:
        sys.stdout.write(json.dumps({"status": "REFUSED", "reason": exc.reason}) + "\n")
        return 2
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

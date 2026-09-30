#!/usr/bin/env python3
"""Native attachment primitive discovery fixture (specs/009-phone-attachment-native-primitives).

Test tooling, not part of the plugin: `server/hmp_plugin` never imports it. `run` creates private
scratch roots, fingerprints the exact native owning files, starts one child under the target
build's own interpreter with a minimal environment, fingerprints again, removes the scratch tree
and prints a status summary (booleans, counts, status codes; no prompts, ids, keys or paths).

The child sets HOME / HERMES_HOME / XDG / runtime roots before any native import, denies IP
socket `connect` / `connect_ex` / `sendto` / `create_connection` (AF_UNIX stays allowed), and runs
five subcases against real native code with synthetic bytes. Only model, vision and network
side effects are replaced with controlled doubles; a subcase whose path needs the full gateway,
a model or credentials is reported as EVIDENCE_GAP rather than re-implemented.

The IP denial is Python-level instrumentation, not an OS sandbox: it does not cover C-extension
sockets, subprocesses, or code that holds a socket created before the patch.
"""

from __future__ import annotations

import argparse
import asyncio
import faulthandler
import hashlib
import json
import logging
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import traceback
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_NATIVE_SRC = Path("/private/tmp/hmp-omarchy-build/src")
CHILD_TIMEOUT_SECONDS = 120

# Exact native files whose behavior this fixture observes; fingerprinted before and after.
OWNING_FILES = (
    "gateway/platforms/base.py",
    "gateway/platforms/event.py",
    "gateway/platforms/media_cache.py",
    "gateway/run.py",
    "gateway/run_inbound.py",
    "gateway/run_busy.py",
    "gateway/run_turn.py",
    "gateway/session.py",
    "agent/session_persistence.py",
    "hermes_state.py",
    "hermes_state_messages.py",
    "hermes_state_sessions.py",
)

INSTRUMENTATION_LIMITS = (
    "python_level_socket_patch_not_os_sandbox",
    "c_extension_and_subprocess_sockets_not_covered",
    "dns_resolution_not_intercepted",
)

# create_connection, connect, connect_ex and sendto; the AF_UNIX probe is not an attempt.
SELF_TEST_ATTEMPTS = 4
DENIAL_KEYS = (
    "denies_create_connection",
    "denies_connect",
    "denies_connect_ex",
    "denies_sendto",
    "af_unix_still_works",
    "self_test_attempts_counted",
)
ISOLATION_KEYS = (
    "home_env_in_scratch",
    "path_home_in_scratch",
    "hermes_home_env_in_scratch",
    "no_inherited_hermes_or_xdg_extras",
    "no_credential_like_env",
)

SENTINEL = "SYNTHETIC-SENTINEL-7f3a"


# --------------------------------------------------------------------------------------------
# Parent side: scratch roots, fingerprints, child launch. No native import happens here.
# --------------------------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(native_src: Path) -> dict[str, str]:
    return {name: sha256_file(native_src / name) for name in OWNING_FILES}


def scratch_layout(root: Path) -> dict[str, Path]:
    home = root / "home"
    return {
        "home": home,
        "hermes_home": root / "hermes" / "profiles" / "alpha",
        "xdg_config": root / "xdg" / "config",
        "xdg_data": root / "xdg" / "data",
        "xdg_cache": root / "xdg" / "cache",
        "xdg_state": root / "xdg" / "state",
        "xdg_runtime": root / "xdg" / "runtime",
        "tmp": root / "tmp",
        "cwd": root / "cwd",
    }


def child_environment(layout: dict[str, Path]) -> dict[str, str]:
    """Minimal allow-list environment: no inherited credentials, proxies, HERMES_* or XDG_*."""
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(layout["home"]),
        "HERMES_HOME": str(layout["hermes_home"]),
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
    }


def native_python(native_src: Path) -> Path:
    return native_src / ".venv" / "bin" / "python"


def run_parent(native_src: Path) -> dict[str, Any]:
    python = native_python(native_src)
    if not python.is_file():
        return {"status": "UNAVAILABLE", "reason": "native_interpreter_missing"}
    before = fingerprint(native_src)
    root = Path(tempfile.mkdtemp(prefix="hmp-att-"))
    root.chmod(0o700)
    layout = scratch_layout(root)
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
    layout["xdg_runtime"].chmod(0o700)
    summary: dict[str, Any] = {}
    try:
        proc = subprocess.run(
            [
                str(python),
                str(Path(__file__).resolve()),
                "child",
                "--native-src",
                str(native_src),
                "--root",
                str(root),
            ],
            cwd=layout["cwd"],
            env=child_environment(layout),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=CHILD_TIMEOUT_SECONDS,
            check=False,
        )
        summary = parse_child_output(proc.stdout)
        summary["child_exit_code"] = proc.returncode
        # Child stderr is never echoed; only whether it leaked a scratch path is recorded.
        summary["child_stderr_lines"] = len(proc.stderr.splitlines())
        summary["child_stderr_mentions_scratch"] = str(root) in proc.stderr
    except subprocess.TimeoutExpired:
        summary = {"status": "ERROR", "reason": "child_timeout"}
    finally:
        shutil.rmtree(root, ignore_errors=True)
    after = fingerprint(native_src)
    summary["source_fingerprints_before"] = before
    summary["source_fingerprints_after"] = after
    summary["source_unchanged"] = before == after
    summary["scratch_removed"] = not root.exists()
    summary["instrumentation_limits"] = list(INSTRUMENTATION_LIMITS)
    return summary


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


# --------------------------------------------------------------------------------------------
# Child side: runs under the native interpreter.
# --------------------------------------------------------------------------------------------

_BLOCKED_NETWORK = 0


def install_ip_denial() -> None:
    """Refuse IP connect/send in this process and count attempts. AF_UNIX is passed through."""
    import socket

    real = {
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
        "sendto": socket.socket.sendto,
    }

    def is_unix(sock: Any) -> bool:
        return sock.family == getattr(socket, "AF_UNIX", None)

    def guard(name: str) -> Callable[..., Any]:
        def guarded(self: Any, *args: Any, **kwargs: Any) -> Any:
            global _BLOCKED_NETWORK
            if is_unix(self):
                return real[name](self, *args, **kwargs)
            _BLOCKED_NETWORK += 1
            raise OSError("ip network is blocked in this fixture")

        return guarded

    for name in real:
        setattr(socket.socket, name, guard(name))

    def blocked_create_connection(*_args: Any, **_kwargs: Any) -> Any:
        global _BLOCKED_NETWORK
        _BLOCKED_NETWORK += 1
        raise OSError("ip network is blocked in this fixture")

    socket.create_connection = blocked_create_connection  # type: ignore[assignment]


def verify_ip_denial() -> dict[str, bool]:
    """The denial must demonstrably fire, and AF_UNIX must still work."""
    import socket

    global _BLOCKED_NETWORK
    start = _BLOCKED_NETWORK
    denied_create = denied_connect = denied_connect_ex = denied_sendto = False
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    except OSError:
        denied_create = True
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.connect(("127.0.0.1", 9))
    except OSError:
        denied_connect = True
    finally:
        probe.close()
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.connect_ex(("127.0.0.1", 9))
    except OSError:  # the guard raises rather than returning an errno
        denied_connect_ex = True
    finally:
        probe.close()
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp.sendto(b"x", ("127.0.0.1", 9))
    except OSError:
        denied_sendto = True
    finally:
        udp.close()
    a, b = socket.socketpair()
    try:
        a.sendall(b"ok")
        unix_ok = b.recv(2) == b"ok"
    finally:
        a.close()
        b.close()
    counted = _BLOCKED_NETWORK - start
    _BLOCKED_NETWORK = start  # self-test attempts are not native attempts
    return {
        "denies_create_connection": denied_create,
        "denies_connect": denied_connect,
        "denies_connect_ex": denied_connect_ex,
        "denies_sendto": denied_sendto,
        "af_unix_still_works": unix_ok,
        "self_test_attempts_counted": counted == SELF_TEST_ATTEMPTS,
    }


class Subcase:
    """Collects boolean checks (must all hold) and observations (recorded, not judged)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.checks: dict[str, bool] = {}
        self.observations: dict[str, Any] = {}
        self.gaps: dict[str, str] = {}
        self.error: str | None = None
        self.error_line: int | None = None

    def check(self, label: str, value: bool) -> None:
        self.checks[label] = bool(value)

    def observe(self, label: str, value: Any) -> None:
        self.observations[label] = value

    def gap(self, label: str, reason: str) -> None:
        self.gaps[label] = reason

    def status(self) -> str:
        if self.error is not None:
            return "ERROR"
        if not all(self.checks.values()):
            return "FAIL"
        return "PASS_WITH_EVIDENCE_GAP" if self.gaps else "PASS"

    def report(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "status": self.status(),
            "checks_passed": sum(self.checks.values()),
            "checks_total": len(self.checks),
            "failed_checks": sorted(k for k, v in self.checks.items() if not v),
            "observations": self.observations,
            "evidence_gaps": self.gaps,
        }
        if self.error is not None:
            out["error_type"] = self.error
            out["error_fixture_line"] = self.error_line
        return out


def synthetic_png(size: int | None = None) -> bytes:
    """A valid 1x1 RGB PNG; `size` pads it with an ancillary text chunk to exactly that length."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return (
            struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    def build(pad: int) -> bytes:
        out = b"\x89PNG\r\n\x1a\n"
        out += chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        if pad:
            out += chunk(b"tEXt", b"k\x00" + b"x" * (pad - 2))
        out += chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        return out + chunk(b"IEND", b"")

    plain = build(0)
    if size is None:
        return plain
    pad = size - len(plain) - 12  # 12 bytes of chunk framing
    if pad < 2:
        raise ValueError("requested size is below the smallest padded PNG")
    return build(pad)


def tree_files(root: Path) -> set[Path]:
    return {p for p in root.rglob("*") if p.is_file()}


def write_config(hermes_home: Path, cap: Any) -> None:
    (hermes_home / "config.yaml").write_text(
        f"gateway:\n  max_inbound_media_bytes: {cap}\n", encoding="utf-8"
    )


class ChildContext:
    def __init__(self, root: Path, native_src: Path) -> None:
        self.root = root
        self.native_src = native_src
        self.layout = scratch_layout(root)
        self.hermes_home = self.layout["hermes_home"]
        self.log_records: list[logging.LogRecord] = []
        self.runner: Any = None
        self.adapter: Any = None
        self.platform: Any = None
        self.prepared: dict[str, str] = {}


class _Capture(logging.Handler):
    def __init__(self, sink: list[logging.LogRecord]) -> None:
        super().__init__(logging.DEBUG)
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self.sink.append(record)


def assert_isolation(ctx: ChildContext) -> dict[str, bool]:
    home = ctx.layout["home"].resolve()
    return {
        "home_env_in_scratch": Path(os.environ["HOME"]).resolve() == home,
        "path_home_in_scratch": Path.home().resolve() == home,
        "hermes_home_env_in_scratch": Path(os.environ["HERMES_HOME"]).resolve()
        == ctx.hermes_home.resolve(),
        "no_inherited_hermes_or_xdg_extras": not [
            k
            for k in os.environ
            if k.startswith(("HERMES_", "XDG_")) and k not in child_environment(ctx.layout)
        ],
        "no_credential_like_env": not [
            k
            for k in os.environ
            if any(t in k.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
        ],
    }


def register_platform() -> Any:
    from gateway.config import Platform
    from gateway.platform_registry import PlatformEntry, platform_registry

    platform_registry.register(
        PlatformEntry(
            name="hmp",
            label="HMP fixture",
            adapter_factory=lambda _cfg: None,
            check_fn=lambda: True,
            source="plugin",
        )
    )
    return Platform("hmp")


def fixture_adapter_class() -> Any:
    from gateway.platforms.base import BasePlatformAdapter

    class FixtureAdapter(BasePlatformAdapter):
        """No network: every abstract hook is inert. Inherits the real busy fallback."""

        async def connect(self, *, is_reconnect: bool = False) -> bool:  # pragma: no cover
            return True

        async def disconnect(self) -> None:  # pragma: no cover
            return None

        async def send(self, chat_id: str, content: str, reply_to: Any = None, **kw: Any) -> Any:
            raise NotImplementedError  # pragma: no cover

        async def get_chat_info(self, chat_id: str) -> dict[str, Any]:  # pragma: no cover
            return {"name": chat_id, "type": "dm"}

    return FixtureAdapter


def build_runner(ctx: ChildContext) -> None:
    """A real, unstarted `GatewayRunner` with one inert adapter, as the history fixture does."""
    from gateway.config import PlatformConfig, load_gateway_config
    from gateway.run import GatewayRunner

    ctx.platform = register_platform()
    config = load_gateway_config()
    runner = GatewayRunner(config)
    adapter = fixture_adapter_class()(PlatformConfig(enabled=True), ctx.platform)
    adapter.gateway_runner = runner
    runner.adapters[ctx.platform] = adapter
    adapter.set_session_store(runner.session_store)
    ctx.runner, ctx.adapter = runner, adapter


def make_source(
    ctx: ChildContext, chat: str = "chat-synthetic", user: str = "user-synthetic"
) -> Any:
    from gateway.session import SessionSource

    return SessionSource(platform=ctx.platform, chat_id=chat, user_id=user, chat_type="dm")


# ---- subcase 1: cache helpers ---------------------------------------------------------------


def subcase_cache(ctx: ChildContext) -> Subcase:
    sc = Subcase("cache_helpers")
    from gateway.platforms import base

    os.umask(0o022)
    hermes_home = ctx.hermes_home.resolve()

    # Size cap from configuration.
    cap = 512
    write_config(ctx.hermes_home, cap)
    sc.check("configured_cap_is_read", base.get_inbound_media_max_bytes() == cap)
    images = Path(base.get_image_cache_dir())
    sc.check("image_cache_in_active_profile", images.resolve() == hermes_home / "cache" / "images")

    small = synthetic_png()
    path = Path(base.cache_image_from_bytes(small, ".png"))
    sc.check("png_under_cap_cached", path.is_file() and path.read_bytes() == small)
    sc.check("png_cached_in_profile_image_cache", path.resolve().parent == images.resolve())

    at_cap = synthetic_png(size=cap)
    sc.check("png_padding_reaches_cap_exactly", len(at_cap) == cap)
    sc.check(
        "png_exactly_at_cap_cached", Path(base.cache_image_from_bytes(at_cap, ".png")).is_file()
    )

    over = synthetic_png(size=cap + 1)
    sc.check("png_padding_reaches_cap_plus_one", len(over) == cap + 1)
    files_before_reject = tree_files(ctx.root)
    try:
        base.cache_image_from_bytes(over, ".png")
        over_rejected = False
    except ValueError:
        over_rejected = True
    sc.check("png_over_cap_rejected", over_rejected)
    sc.check("png_over_cap_writes_nothing", tree_files(ctx.root) == files_before_reject)

    bad = f"<html>{SENTINEL}</html>".encode()
    files_before_reject = tree_files(ctx.root)
    echoed = False
    try:
        base.cache_image_from_bytes(bad, ".png")
        bad_rejected = False
    except ValueError as exc:
        bad_rejected = True
        echoed = SENTINEL in str(exc)
    sc.check("invalid_magic_rejected", bad_rejected)
    sc.check("invalid_magic_writes_nothing", tree_files(ctx.root) == files_before_reject)
    sc.observe("invalid_magic_error_echoes_rejected_bytes", echoed)

    magic_only = b"\x89PNG\r\n\x1a\n" + b"not an image body"
    try:
        Path(base.cache_image_from_bytes(magic_only, ".png"))
        sc.observe("magic_prefix_alone_is_accepted_without_decode", True)
    except ValueError:
        sc.observe("magic_prefix_alone_is_accepted_without_decode", False)

    # Cap semantics for unusual values (observations; product limits must not depend on them).
    def cap_with(value: Any) -> int:
        write_config(ctx.hermes_home, value)
        return base.get_inbound_media_max_bytes()

    sc.observe("cap_zero_reads_as_unlimited", cap_with(0) == 0)
    sc.observe("cap_negative_reads_as_negative", cap_with(-1) == -1)
    try:
        base.validate_inbound_media_size(1, media_type="image", max_bytes=cap_with(-1))
        sc.observe("cap_negative_rejects_any_positive_size", False)
    except ValueError:
        sc.observe("cap_negative_rejects_any_positive_size", True)
    sc.observe(
        "cap_unparseable_falls_back_to_default",
        cap_with("not-a-number") == base.DEFAULT_INBOUND_MEDIA_MAX_BYTES,
    )
    write_config(ctx.hermes_home, cap)

    # Documents: sanitization and containment.
    docs = Path(base.get_document_cache_dir())
    sc.check(
        "document_cache_in_active_profile", docs.resolve() == hermes_home / "cache" / "documents"
    )
    payload = f"{SENTINEL} doc".encode()
    hostile = {
        "traversal": "../../escape.txt",
        "absolute": "/srv/abs-target/abs.txt",
        "nested": "a/b/c.txt",
        "parent_only": "..",
        "current_only": ".",
        "empty": "",
        "nul_byte": "n\x00ul.txt",
    }
    outside_before = tree_files(ctx.root)
    written: dict[str, Path] = {}
    for label, name in hostile.items():
        result = Path(base.cache_document_from_bytes(payload, name))
        written[label] = result
        sc.check(
            f"doc_{label}_contained",
            result.resolve().parent == docs.resolve()
            and result.name.startswith("doc_")
            and result.read_bytes() == payload,
        )
    new_files = tree_files(ctx.root) - outside_before
    sc.check(
        "doc_cases_write_only_inside_document_cache",
        {p.parent.resolve() for p in new_files} == {docs.resolve()},
    )
    sc.check(
        "doc_traversal_keeps_only_final_component",
        written["traversal"].name.endswith("_escape.txt"),
    )
    sc.check(
        "doc_dotdot_falls_back_to_generic_name", written["parent_only"].name.endswith("_document")
    )
    sc.check("doc_empty_falls_back_to_generic_name", written["empty"].name.endswith("_document"))
    sc.check("doc_nul_byte_removed", "\x00" not in written["nul_byte"].name)

    # Observations that bear on product filename policy (native keeps these in the cache name).
    backslash = Path(base.cache_document_from_bytes(payload, "a\\b.txt"))
    sc.observe("posix_backslash_not_treated_as_separator", backslash.name.endswith("_a\\b.txt"))
    newline = Path(base.cache_document_from_bytes(payload, "a\nb.txt"))
    sc.observe("newline_in_name_kept_in_cache_path", "\n" in newline.name)
    try:
        Path(base.cache_document_from_bytes(payload, "x" * 300 + ".txt"))
        sc.observe("overlong_name_raises_oserror", False)
    except OSError:
        sc.observe("overlong_name_raises_oserror", True)
    except ValueError:
        sc.observe("overlong_name_raises_oserror", False)

    # No per-document bound: a document above the image cap is accepted (tiny bytes; no allocation).
    big_doc = b"d" * (cap * 4)
    sc.observe(
        "document_above_image_cap_is_cached",
        Path(base.cache_document_from_bytes(big_doc, "big.bin")).is_file(),
    )

    # Private mode is not native behavior: with umask 022 the files are group/other readable.
    sample = written["nested"]
    sc.observe("document_file_mode_octal", oct(sample.stat().st_mode & 0o777))
    sc.observe("native_applies_no_private_chmod", (sample.stat().st_mode & 0o077) != 0)
    sc.observe("cache_dir_mode_octal", oct(docs.stat().st_mode & 0o777))
    return sc


# ---- subcase 2: MessageEvent representation -------------------------------------------------


def subcase_event(ctx: ChildContext) -> Subcase:
    sc = Subcase("message_event")
    import dataclasses

    from gateway.platforms import base
    from gateway.platforms.event import MessageEvent, MessageType
    from gateway.session import build_session_key

    source = make_source(ctx)
    path = base.cache_image_from_bytes(synthetic_png(), ".png")
    caption = "synthetic caption one"
    plain = MessageEvent(
        text=caption, message_type=MessageType.TEXT, source=source, message_id="m-plain"
    )
    event = MessageEvent(
        text=caption,
        message_type=MessageType.PHOTO,
        source=source,
        message_id="m-photo",
        media_urls=[path],
        media_types=["image/png"],
    )
    sc.check("path_held_in_media_urls", event.media_urls == [path])
    sc.check("mime_held_in_media_types", event.media_types == ["image/png"])
    sc.check("caption_held_in_text", event.text == caption)
    sc.check("inline_flags_default_empty", event.media_text_inlined == [])
    carriers = [
        f.name for f in dataclasses.fields(event) if path in repr(getattr(event, f.name, None))
    ]
    sc.check("only_media_urls_field_carries_path", carriers == ["media_urls"])
    sc.check("source_does_not_carry_path", path not in repr(dataclasses.asdict(source)))
    sc.check(
        "session_key_unchanged_by_media",
        build_session_key(event.source) == build_session_key(plain.source),
    )
    sc.check("session_key_does_not_contain_path", path not in build_session_key(event.source))
    sc.check("caption_is_not_a_command", event.get_command() is None)
    path_text = MessageEvent(text=path, message_type=MessageType.TEXT, source=source)
    sc.check("path_as_message_text_is_not_a_command", path_text.get_command() is None)
    sc.observe("event_defaults_not_accepted", getattr(event, "_gateway_accepted", None) is False)
    sc.observe("event_defaults_not_internal", event.internal is False)
    sc.observe("event_defaults_allow_gateway_control", event.allow_gateway_control is True)
    return sc


# ---- subcase 3: inbound preparation ---------------------------------------------------------


def prepare(ctx: ChildContext, event: Any, source: Any) -> str:
    runner = ctx.runner
    key = runner._session_key_for_source(source)
    result = asyncio.run(
        runner._prepare_profile_scoped_inbound_message_text(
            event=event, source=source, history=[], session_key=key
        )
    )
    return result or ""


def document_event(
    ctx: ChildContext, path: str, mime: str, flags: list[Any], text: str = ""
) -> Any:
    from gateway.platforms.event import MessageEvent, MessageType

    return MessageEvent(
        text=text,
        message_type=MessageType.DOCUMENT,
        source=make_source(ctx),
        media_urls=[path],
        media_types=[mime],
        media_text_inlined=list(flags),
    )


def subcase_prepare(ctx: ChildContext) -> Subcase:
    sc = Subcase("inbound_preparation")
    from gateway.platforms import base
    from gateway.platforms.event import MessageEvent, MessageType

    source = make_source(ctx)
    caption = "synthetic question"
    body = f"{SENTINEL} body".encode()
    txt = base.cache_document_from_bytes(body, "notes.txt")
    pdf = base.cache_document_from_bytes(b"%PDF-1.4 " + body, "paper.pdf")

    def note(path: str, mime: str, flags: list[Any]) -> str:
        return prepare(ctx, document_event(ctx, path, mime, flags, caption), source)

    t_default = note(txt, "text/plain", [])
    t_none = note(txt, "text/plain", [None])
    t_false = note(txt, "text/plain", [False])
    t_true = note(txt, "text/plain", [True])
    ctx.prepared["txt_false"] = t_false
    ctx.prepared["txt_path"] = txt
    ctx.prepared["txt_default"] = t_default

    sc.check("absent_flag_equals_none_flag", t_default == t_none)
    sc.check("absent_flag_makes_the_same_claim_as_true", t_default == t_true)
    sc.check("false_flag_changes_the_note", t_false != t_true)
    sc.check(
        "native_never_inlines_file_content",
        all(SENTINEL not in t for t in (t_default, t_false, t_true)),
    )
    sc.check("caption_kept_last", all(t.endswith(caption) for t in (t_default, t_false, t_true)))
    sc.check("note_points_at_host_cache_path", all(txt in t for t in (t_default, t_false, t_true)))

    p_default = note(pdf, "application/pdf", [])
    p_false = note(pdf, "application/pdf", [False])
    p_true = note(pdf, "application/pdf", [True])
    sc.check("binary_note_ignores_flag", p_default == p_false == p_true)
    sc.check("binary_note_differs_from_text_false_note", p_false != t_false)
    sc.check("native_never_inlines_binary_content", SENTINEL not in p_false)

    octet = note(txt, "application/octet-stream", [False])
    sc.observe("octet_stream_with_txt_extension_reads_as_text", octet == t_false)

    # Controlled containment observation: native does not check that media_urls is a cache path.
    outside = ctx.root / "outside"
    outside.mkdir(exist_ok=True)
    outside_file = outside / "elsewhere.txt"
    outside_file.write_bytes(body)
    outside_note = note(str(outside_file), "text/plain", [False])
    sc.observe("preparation_accepts_path_outside_cache", str(outside_file) in outside_note)

    injected = base.cache_document_from_bytes(body, "a\nINJECTED line.txt")
    injected_note = note(injected, "text/plain", [False])
    sc.observe(
        "filename_newline_reaches_note_text_via_path", "\nINJECTED line.txt" in injected_note
    )

    # Native vision mode with a controlled model-routing double: paths are buffered, not inlined.
    image = base.cache_image_from_bytes(synthetic_png(), ".png")
    ctx.runner._decide_image_input_mode = lambda **_kw: "native"
    photo = MessageEvent(
        text=caption,
        message_type=MessageType.PHOTO,
        source=source,
        media_urls=[image],
        media_types=["image/png"],
    )
    key = ctx.runner._session_key_for_source(source)
    photo_text = prepare(ctx, photo, source)
    state = ctx.runner._peek_session_state(key)
    buffered = list(state.persistent.native_image_paths) if state is not None else []
    sc.check("native_image_text_is_caption_only", photo_text == caption)
    sc.check("native_image_path_buffered_for_the_turn", buffered == [image])
    del ctx.runner._decide_image_input_mode

    sc.gap(
        "text_mode_image_enrichment",
        "needs the vision tool and a model/provider call; not started",
    )
    sc.gap("audio_video_notes", "outside Phone photo/file scope; not exercised")
    return sc


# ---- subcase 4: busy handling ---------------------------------------------------------------


def media_event(
    ctx: ChildContext, kind: str, message_id: str, *, text: str = "", metadata: Any = None
) -> Any:
    from gateway.platforms import base
    from gateway.platforms.event import MessageEvent, MessageType

    source = make_source(ctx)
    if kind == "photo":
        return MessageEvent(
            text=text,
            message_type=MessageType.PHOTO,
            source=source,
            message_id=message_id,
            media_urls=[base.cache_image_from_bytes(synthetic_png(), ".png")],
            media_types=["image/png"],
            metadata=dict(metadata or {}),
        )
    if kind == "document":
        return MessageEvent(
            text=text,
            message_type=MessageType.DOCUMENT,
            source=source,
            message_id=message_id,
            media_urls=[base.cache_document_from_bytes(b"doc", "d.txt")],
            media_types=["text/plain"],
            media_text_inlined=[False],
            metadata=dict(metadata or {}),
        )
    return MessageEvent(
        text=text,
        message_type=MessageType.TEXT,
        source=source,
        message_id=message_id,
        metadata=dict(metadata or {}),
    )


def subcase_busy(ctx: ChildContext) -> Subcase:
    sc = Subcase("busy_handling")
    runner, adapter = ctx.runner, ctx.adapter
    source = make_source(ctx)
    key = runner._session_key_for_source(source)

    def reset() -> None:
        adapter._pending_messages.clear()
        state = runner._session_state(key)
        state.conversation.queued_events.clear()

    # 4a: the base adapter fallback (no runner busy handler installed).
    adapter.set_busy_session_handler(None)

    def base_fallback(first: str, second: str) -> Any:
        reset()
        e1 = media_event(ctx, first, "c-1", text="cap-one")
        e2 = media_event(ctx, second, "c-2", text="cap-two")
        asyncio.run(adapter._handle_message_while_active(e1, key))
        asyncio.run(adapter._handle_message_while_active(e2, key))
        return adapter._pending_messages.get(key), e1, e2

    pending, _e1, e2 = base_fallback("photo", "photo")
    sc.check(
        "base_photo_photo_merges_to_one_pending",
        pending is not None and len(pending.media_urls) == 2,
    )
    sc.check("base_second_event_marked_accepted", e2._gateway_accepted is True)
    sc.check("base_merge_keeps_first_client_id_only", pending.message_id == "c-1")
    sc.check("base_merge_joins_captions", pending.text == "cap-one\n\ncap-two")

    pending, _e1, _e2 = base_fallback("photo", "document")
    sc.observe("base_photo_then_document_merged_into_one", len(pending.media_urls) == 2)
    sc.observe("base_merge_retypes_pending_as_photo", pending.message_type.name == "PHOTO")
    pending, _e1, _e2 = base_fallback("document", "document")
    sc.observe("base_document_then_document_merged_into_one", len(pending.media_urls) == 2)

    # 4b: the real runner queue policy, reached through the runner's own method.
    sc.check("runner_resolves_the_fixture_adapter", runner._delivery_adapter_for(source) is adapter)

    def runner_queue(first: dict[str, Any], second: dict[str, Any]) -> tuple[Any, int, Any, Any]:
        reset()
        e1 = media_event(ctx, **first)
        e2 = media_event(ctx, **second)
        runner._queue_or_replace_pending_event(key, e1)
        runner._queue_or_replace_pending_event(key, e2)
        slot = adapter._pending_messages.get(key)
        fifo = len(runner._session_state(key).conversation.queued_events)
        return slot, fifo, e1, e2

    def spec(kind: str, mid: str, **extra: Any) -> dict[str, Any]:
        return {"kind": kind, "message_id": mid, **extra}

    slot, fifo, _e1, e2 = runner_queue(
        spec("photo", "c-1", text="cap-one"), spec("photo", "c-2", text="cap-two")
    )
    sc.check("runner_photo_photo_same_scope_merges", fifo == 0 and len(slot.media_urls) == 2)
    sc.check("runner_merge_marks_second_accepted", e2._gateway_accepted is True)
    sc.check("runner_merge_keeps_first_client_id_only", slot.message_id == "c-1")

    slot, fifo, _e1, _e2 = runner_queue(
        spec("photo", "c-1", text="cap-one"), spec("text", "c-2", text="cap-two")
    )
    sc.check(
        "runner_photo_then_text_merges_text_into_caption",
        fifo == 0 and slot.text == "cap-one\n\ncap-two",
    )
    slot, fifo, _e1, _e2 = runner_queue(spec("text", "c-1", text="cap-one"), spec("photo", "c-2"))
    sc.check(
        "runner_text_then_photo_merges_and_retypes", fifo == 0 and slot.message_type.name == "PHOTO"
    )

    slot, fifo, e1, e2 = runner_queue(spec("document", "c-1"), spec("document", "c-2"))
    sc.check("runner_document_document_takes_fifo_slot", fifo == 1 and len(slot.media_urls) == 1)
    sc.check(
        "runner_fifo_second_event_marked_accepted",
        e2._gateway_accepted is True and e1._gateway_accepted is True,
    )
    slot, fifo, _e1, _e2 = runner_queue(spec("photo", "c-1"), spec("document", "c-2"))
    sc.check("runner_photo_then_document_not_merged", fifo == 1 and len(slot.media_urls) == 1)
    slot, fifo, _e1, _e2 = runner_queue(spec("document", "c-1"), spec("photo", "c-2"))
    sc.check("runner_document_then_photo_not_merged", fifo == 1 and len(slot.media_urls) == 1)

    # Matching security scope is required; differing scope is the negative control.
    same = {"gateway_session_key": "scope-a"}
    other = {"gateway_session_key": "scope-b"}
    slot, fifo, _e1, _e2 = runner_queue(
        spec("photo", "c-1", metadata=same), spec("photo", "c-2", metadata=same)
    )
    sc.check("runner_same_nonempty_scope_merges", fifo == 0 and len(slot.media_urls) == 2)
    slot, fifo, _e1, _e2 = runner_queue(
        spec("photo", "c-1", metadata=same), spec("photo", "c-2", metadata=other)
    )
    sc.check("runner_different_scope_photo_not_merged", fifo == 1 and len(slot.media_urls) == 1)

    e1 = media_event(ctx, "photo", "c-1")
    e2 = media_event(ctx, "photo", "c-2")
    e2.allow_gateway_control = False
    reset()
    runner._queue_or_replace_pending_event(key, e1)
    runner._queue_or_replace_pending_event(key, e2)
    sc.check(
        "runner_different_gateway_control_flag_not_merged",
        len(runner._session_state(key).conversation.queued_events) == 1,
    )
    reset()
    sc.gap(
        "runner_busy_handler_entry",
        "_handle_active_session_busy_message needs user authorization, busy-ack send and steer/"
        "interrupt machinery of a running gateway; only the queue policy method was run",
    )
    sc.gap(
        "hmp_defer_policy_reject", "admission ticket/defer_policy is absent from this native build"
    )
    return sc


# ---- subcase 5: durable rows ----------------------------------------------------------------


def duck_agent(session_id: str, db: Any, override: Any, timestamp: Any) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(
        session_id=session_id,
        _session_db=db,
        _persist_user_message_idx=0,
        _persist_user_message_override=override,
        _persist_user_message_timestamp=timestamp,
        _flushed_db_message_session_id=None,
        _last_flushed_db_idx=0,
        _mute_notification_reply=False,
        _pending_cli_user_message=None,
        _active_compression_lock_holder=None,
    )


def subcase_durable(ctx: ChildContext) -> Subcase:
    sc = Subcase("durable_rows")
    from agent import session_persistence as persistence
    from gateway.platforms import base
    from hermes_state import SessionDB

    db = SessionDB()
    session_id = "synthetic-session-durable"
    db.create_session(session_id, "hmp")
    source = make_source(ctx)
    caption = "synthetic caption for rows"

    def flush(message: dict[str, Any], override: Any, timestamp: Any = None) -> None:
        agent = duck_agent(session_id, db, override, timestamp)
        messages = [message]
        rows, msgs = persistence._db_flush_collect(agent, messages, None)
        persistence._db_flush_write(agent, rows, msgs, messages)

    # A: a document turn. The prepared text comes from subcase 3's real preparation.
    from gateway.platforms.event import MessageEvent, MessageType

    doc_event = MessageEvent(text=caption, message_type=MessageType.DOCUMENT, source=source)
    prepared = ctx.prepared["txt_false"]
    text, persist_text, stamp = ctx.runner._hmwa_apply_message_timestamp(doc_event, prepared)
    flush({"role": "user", "content": text, "message_id": "client-doc-1"}, persist_text, stamp)

    # B: a native-vision image turn: content is a part list, the override is caption text only.
    image_path = base.cache_image_from_bytes(synthetic_png(), ".png")
    parts = [
        {"type": "text", "text": caption},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]
    flush({"role": "user", "content": parts, "message_id": "client-img-1"}, caption)

    # C: a plain text control.
    flush({"role": "user", "content": caption, "message_id": "client-text-1"}, caption)

    rows = db.get_messages(session_id)
    sc.check("three_rows_written", len(rows) == 3)
    ids = [r.get("id") for r in rows]
    sc.check(
        "row_ids_are_increasing_ints",
        all(isinstance(i, int) for i in ids) and ids == sorted(set(ids)),
    )
    sc.observe("row_field_names", sorted(rows[0]) if rows else [])
    by_client = {r.get("platform_message_id"): r for r in rows}
    sc.check(
        "client_message_id_round_trips_as_platform_message_id",
        set(by_client) == {"client-doc-1", "client-img-1", "client-text-1"},
    )
    doc_row, img_row, text_row = rows  # insertion order: document, image, text
    sc.check("text_row_content_is_the_text", text_row["content"] == caption)
    sc.check("document_row_equals_prepared_note", doc_row["content"] == prepared)
    sc.check("document_row_carries_host_cache_path", ctx.prepared["txt_path"] in doc_row["content"])
    sc.check("image_row_does_not_carry_image_path", image_path not in img_row["content"])
    sc.check("image_row_keeps_caption", caption in img_row["content"])
    sc.check(
        "image_row_marks_image_as_screenshot_placeholder", "[screenshot]" in img_row["content"]
    )
    sc.observe("string_override_did_not_replace_part_list", img_row["content"] != caption)
    media_like = sorted(
        k for k in doc_row if any(w in k.lower() for w in ("media", "attach", "path", "url"))
    )
    sc.check("row_schema_has_no_attachment_field", not media_like)
    later = db.get_messages(session_id, after_id=ids[0])
    sc.check("after_id_keyset_read_returns_only_later_rows", [r["id"] for r in later] == ids[1:])
    sc.observe(
        "image_row_placeholder_joined_with_caption",
        img_row["content"] == f"{caption}\n[screenshot]",
    )

    sc.gap(
        "agent_turn_flush_stage",
        "the real flush helpers ran on a duck-typed agent; constructing AIAgent needs a model "
        "client. The message dict shapes (list content + string override) are assumed from the "
        "census, not produced by a real agent turn",
    )
    sc.gap(
        "hmp_read_bridge", "HMP runtime is out of scope; read-back here is the native SessionDB row"
    )
    return sc


# ---- child driver ---------------------------------------------------------------------------

SUBCASES: tuple[tuple[str, Callable[[ChildContext], Subcase]], ...] = (
    ("cache_helpers", subcase_cache),
    ("message_event", subcase_event),
    ("inbound_preparation", subcase_prepare),
    ("busy_handling", subcase_busy),
    ("durable_rows", subcase_durable),
)


def run_child(root: Path, native_src: Path) -> dict[str, Any]:
    faulthandler.dump_traceback_later(
        CHILD_TIMEOUT_SECONDS - 10, exit=True
    )  # frames only, to stderr
    ctx = ChildContext(root, native_src)
    isolation = assert_isolation(ctx)
    install_ip_denial()
    denial = verify_ip_denial()
    summary: dict[str, Any] = {"isolation": isolation, "ip_denial_self_test": denial}
    if not (all(isolation.values()) and all(denial.values())):
        summary["status"] = "ERROR"
        summary["reason"] = "isolation_or_denial_precondition_failed"
        return summary

    sys.path.insert(0, str(native_src))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = _Capture(ctx.log_records)
    root_logger.addHandler(handler)

    import hermes_constants

    summary["imports_from_native_src"] = str(Path(hermes_constants.__file__).resolve()).startswith(
        str(native_src.resolve())
    )
    summary["hermes_home_resolves_to_scratch"] = (
        Path(hermes_constants.get_hermes_home()).resolve() == ctx.hermes_home.resolve()
    )
    summary["python_version"] = ".".join(str(v) for v in sys.version_info[:3])
    build_runner(ctx)

    reports: dict[str, Any] = {}
    for name, fn in SUBCASES:
        try:
            sub = fn(ctx)
        except Exception as exc:  # report the type only: messages may carry paths or content
            sub = Subcase(name)
            sub.error = type(exc).__name__
            here = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == __file__]
            sub.error_line = here[-1].lineno if here else None
        reports[name] = sub.report()
    summary["subcases"] = reports

    scratch = str(root)
    levels: dict[str, int] = {}
    for record in ctx.log_records:
        levels[record.levelname] = levels.get(record.levelname, 0) + 1
    summary["native_log_records_by_level"] = levels
    leaking = [r for r in ctx.log_records if scratch in r.getMessage()]
    summary["native_log_records_mentioning_scratch"] = len(leaking)
    cache_root = str(ctx.hermes_home / "cache")
    summary["native_log_records_mentioning_cache_paths"] = sum(
        1 for r in ctx.log_records if cache_root in r.getMessage()
    )
    # Logger name and level only: the message itself can carry a path.
    summary["native_log_scratch_mention_sources"] = sorted(
        {f"{r.name}:{r.levelname}" for r in leaking}
    )
    summary["blocked_ip_attempts_during_run"] = _BLOCKED_NETWORK
    summary["runtime_bootstrap_dir_created"] = (ctx.hermes_home / "installs").exists()
    statuses = {r["status"] for r in reports.values()}
    summary["status"] = (
        "FAIL"
        if statuses & {"FAIL", "ERROR"} or _BLOCKED_NETWORK
        else ("PASS_WITH_EVIDENCE_GAP" if "PASS_WITH_EVIDENCE_GAP" in statuses else "PASS")
    )
    return summary


def _all_true(value: Any, keys: tuple[str, ...]) -> bool:
    return isinstance(value, dict) and all(value.get(k) is True for k in keys)


def _is_int(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


# Field name -> predicate over the field's value. A missing field counts as failed.
BOUNDARY_CHECKS: tuple[tuple[str, Callable[[Any], bool]], ...] = (
    ("status", lambda v: v in {"PASS", "PASS_WITH_EVIDENCE_GAP"}),
    ("child_exit_code", lambda v: _is_int(v, 0)),
    ("imports_from_native_src", lambda v: v is True),
    ("hermes_home_resolves_to_scratch", lambda v: v is True),
    ("isolation", lambda v: _all_true(v, ISOLATION_KEYS)),
    ("ip_denial_self_test", lambda v: _all_true(v, DENIAL_KEYS)),
    ("source_unchanged", lambda v: v is True),
    ("scratch_removed", lambda v: v is True),
    ("blocked_ip_attempts_during_run", lambda v: _is_int(v, 0)),
    ("child_stderr_lines", lambda v: _is_int(v, 0)),
    ("child_stderr_mentions_scratch", lambda v: v is False),
    ("native_log_records_mentioning_cache_paths", lambda v: _is_int(v, 0)),
)


def boundary_failure(result: dict[str, Any]) -> str | None:
    """Name of the first run boundary that did not hold (missing or malformed fails closed)."""
    for name, holds in BOUNDARY_CHECKS:
        try:
            ok = holds(result.get(name))
        except Exception:
            ok = False
        if not ok:
            return name
    return None


def disposition(result: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Output and exit code for `run`. Only field names are reported, never their values."""
    status = result.get("status")
    if status in {"UNAVAILABLE", "ERROR", "FAIL"}:
        return result, 1
    failed = boundary_failure(result)
    if failed is None:
        return result, 0
    closed = {
        "status": "ERROR",
        "reason": "run_boundary_not_held",
        "failed_boundary": failed,
        "instrumentation_limits": list(INSTRUMENTATION_LIMITS),
    }
    return closed, 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    run = sub.add_parser("run")
    run.add_argument("--native-src", type=Path, default=DEFAULT_NATIVE_SRC)
    child = sub.add_parser("child")
    child.add_argument("--native-src", type=Path, required=True)
    child.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "run":
        result, code = disposition(run_parent(args.native_src))
        print(json.dumps(result, sort_keys=True))
        return code
    print(json.dumps(run_child(args.root, args.native_src), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

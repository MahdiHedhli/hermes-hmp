#!/usr/bin/env python3
"""Causal fixtures for `local_media_active_scan` against the real native `SessionDB` (research).

Test tooling: `server/hmp_plugin` never imports it. The parent validates the exact independent
Hermes checkout (`8afaab37…`, clean before and after, owning files fingerprinted), creates a private
scratch tree and runs one child under the checkout's own `.venv` interpreter with an allow-list
environment, no network and a hard deadline. The child opens a disposable `SessionDB`, makes every
write through native methods (`append_messages_batch`, `append_message`, `deactivate_message`,
`rewind_to_message` and the native in-place transcript repair reached through
`append_messages_batch`) and runs the scanner at its seams.

Direct SQL through the native writer (`_write_rowcount`) is used ONLY where native has no writer for
the shape under test, and only in fixtures, never in the scanner: storing a malformed or `[]`
`tool_calls` blob, an in-place tool-row edit, and reactivating a row (the undo/ABA case). Each such
case carries the `test_only_sql` label in its record.

The report is closed metadata: case labels, expected/observed reasons, counts and booleans. It never
carries rows, IDs, paths, prompts or content. The IP denial is Python-level instrumentation, not an
OS sandbox.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
SCANNER_PATH = HERE.parent / "local_media_active_scan.py"
DEFAULT_NATIVE_SRC = Path(
    "/private/tmp/hmp-approval-dogfood-git-builds/approval-dogfood-8afa-git-public/src"
)
EXPECTED_NATIVE_HEAD = "8afaab3703e336d72a72c812dd2dd249f04f166a"
FINGERPRINT_FILES = (
    "hermes_state.py",
    "hermes_state_messages.py",
    "hermes_state_sessions.py",
    "agent/transcript_repair.py",
)
CHILD_TIMEOUT_SECONDS = 240
MAX_RESULT_BYTES = 1024 * 1024
CALL = "call_synthetic_0001"
IMAGE = "/synthetic/profile/cache/image.png"


class FixtureSafetyError(RuntimeError):
    pass


# --------------------------------------------------------------------------- parent


def _git(native_src: Path, *args: str) -> str:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(native_src), "GIT_CONFIG_NOSYSTEM": "1"}
    done = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["/usr/bin/git", "-C", str(native_src), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return done.stdout.strip() if done.returncode == 0 else "?"


def native_state(native_src: Path) -> dict[str, Any]:
    """HEAD match, clean tree and fingerprints of the owning files (compared before and after)."""
    prints = {}
    for name in FINGERPRINT_FILES:
        prints[name] = hashlib.sha256((native_src / name).read_bytes()).hexdigest()[:12]
    return {
        "head_matches": _git(native_src, "rev-parse", "HEAD") == EXPECTED_NATIVE_HEAD,
        "tree_clean": _git(native_src, "status", "--porcelain") == "",
        "fingerprints": prints,
    }


def validate_native_src(native_src: Path) -> Path:
    python = native_src / ".venv" / "bin" / "python"
    if not python.is_file():
        raise FixtureSafetyError("native interpreter missing")
    home = Path.home().resolve()
    for forbidden in (home / ".hermes", Path("/Users") / "Shared"):
        resolved = native_src.resolve()
        if resolved == forbidden or forbidden in resolved.parents:
            raise FixtureSafetyError("native source is inside a live Hermes home")
    state = native_state(native_src)
    if not (state["head_matches"] and state["tree_clean"]):
        raise FixtureSafetyError("native source is not the clean expected build")
    return python


def make_scratch() -> tuple[Path, dict[str, Path]]:
    root = Path(tempfile.mkdtemp(prefix="hmp-scan-")).resolve()
    root.chmod(0o700)
    real_hermes = (Path.home() / ".hermes").resolve()
    if root == real_hermes or real_hermes in root.parents:
        shutil.rmtree(root, ignore_errors=True)
        raise FixtureSafetyError("scratch inside the real Hermes home")
    layout = {
        "home": root / "home",
        "hermes": root / "hermes",
        "xdg": root / "xdg",
        "tmp": root / "tmp",
        "cwd": root / "cwd",
    }
    for path in layout.values():
        path.mkdir(mode=0o700)
    return root, layout


def child_environment(layout: dict[str, Path]) -> dict[str, str]:
    """Allow-list only: no inherited credentials, proxies, HERMES_* or XDG_* beyond these."""
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(layout["home"]),
        "HERMES_HOME": str(layout["hermes"]),
        "XDG_CONFIG_HOME": str(layout["xdg"] / "config"),
        "XDG_DATA_HOME": str(layout["xdg"] / "data"),
        "XDG_CACHE_HOME": str(layout["xdg"] / "cache"),
        "XDG_STATE_HOME": str(layout["xdg"] / "state"),
        "TMPDIR": str(layout["tmp"]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "LANG": "C.UTF-8",
    }


def _limit_child() -> None:
    size = 512 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))


def run_parent(native_src: Path = DEFAULT_NATIVE_SRC) -> dict[str, Any]:
    python = validate_native_src(native_src)
    before = native_state(native_src)
    root, layout = make_scratch()
    try:
        report = _spawn(python, native_src, root, layout)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    after = native_state(native_src)
    report["native"] = {
        "head_matches": before["head_matches"] and after["head_matches"],
        "tree_clean_before": before["tree_clean"],
        "tree_clean_after": after["tree_clean"],
        "owning_files_unchanged": before["fingerprints"] == after["fingerprints"],
        "fingerprints": after["fingerprints"],
    }
    report["scratch_removed"] = not root.exists()
    return report


def _spawn(
    python: Path, native_src: Path, root: Path, layout: dict[str, Path]
) -> dict[str, Any]:
    out_path, err_path = root / "child.out", root / "child.err"
    with (
        open(
            os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
        ) as out,
        open(
            os.open(err_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
        ) as err,
    ):
        proc = subprocess.Popen(  # noqa: S603 - argv built here, no shell
            [
                str(python),
                str(HERE),
                "child",
                "--native-src",
                str(native_src),
                "--root",
                str(root),
            ],
            cwd=layout["cwd"],
            env=child_environment(layout),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
            preexec_fn=_limit_child,
        )
        timed_out = False
        try:
            code = proc.wait(timeout=CHILD_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            code = -1
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)
        if timed_out:
            proc.wait()
    result_path = root / "result.json"
    result: dict[str, Any] = {
        "status": "ERROR",
        "reason": "child_timeout" if timed_out else "no_result",
    }
    if result_path.is_file() and result_path.stat().st_size <= MAX_RESULT_BYTES:
        result = json.loads(result_path.read_text())
    stderr_text = err_path.read_bytes()
    result["child_exit_code"] = code
    result["child_stdout_bytes"] = out_path.stat().st_size
    result["child_stderr_bytes"] = len(stderr_text)
    result["child_stderr_mentions_scratch"] = str(root).encode() in stderr_text
    return result


# --------------------------------------------------------------------------- child helpers


def install_network_denial(counter: dict[str, int]) -> None:
    import socket

    def deny(*_a: Any, **_k: Any) -> Any:
        counter["blocked"] += 1
        raise OSError("network is blocked in this fixture")

    socket.socket.connect = deny  # type: ignore[assignment]
    socket.socket.connect_ex = deny  # type: ignore[assignment]
    socket.socket.sendto = deny  # type: ignore[assignment]
    socket.create_connection = deny  # type: ignore[assignment]


def load_scanner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "local_media_active_scan", SCANNER_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def call(call_id: str, name: str, arguments: Any) -> dict[str, Any]:
    text = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": text},
    }


def direct_calls(call_id: str = CALL) -> list[dict[str, Any]]:
    return [call(call_id, "image_generate", {"prompt": "synthetic"})]


def bridge_calls(call_id: str = CALL, entries: Any = None) -> list[dict[str, Any]]:
    entries = (
        [{"name": "image_generate", "arguments": {"prompt": "synthetic"}}]
        if entries is None
        else entries
    )
    return [call(call_id, "tool_call", {"calls": entries})]


def result_text(**overrides: Any) -> str:
    body: dict[str, Any] = {
        "success": True,
        "image": IMAGE,
        "model": "synthetic",
        "provider": "synthetic",
    }
    body.update(overrides)
    return json.dumps({k: v for k, v in body.items() if v is not _DROP})


_DROP = object()


def assistant(calls: Any = None, content: str | None = None) -> dict[str, Any]:
    return {"role": "assistant", "content": content, "tool_calls": calls}


def tool(
    call_id: str = CALL, name: str = "image_generate", content: str | None = None
) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "tool_name": name,
        "content": result_text() if content is None else content,
    }


def user(text: str = "synthetic request") -> dict[str, Any]:
    return {"role": "user", "content": text}


def filler(count: int) -> list[dict[str, Any]]:
    return [
        user(f"filler {i}") if i % 2 == 0 else assistant(None, f"ok {i}")
        for i in range(count)
    ]


class Lab:
    """Disposable synthetic sessions in one scratch SessionDB; writes go through native methods."""

    def __init__(self, db: Any) -> None:
        self.db = db
        self.count = 0
        self.test_only_sql_used = False

    def session(self, **kwargs: Any) -> str:
        self.count += 1
        sid = f"scan-{self.count:04d}"
        self.db.create_session(sid, source="synthetic", **kwargs)
        return sid

    def add(self, sid: str, rows: list[dict[str, Any]]) -> list[int]:
        before = set(self.db.get_active_message_ids(sid))
        self.db.append_messages_batch(sid, rows)
        return [i for i in self.db.get_active_message_ids(sid) if i not in before]

    def tool_id(self, sid: str, call_id: str = CALL) -> int:
        """The last `image_generate` tool row for the call ID, else the last tool row for it."""
        rows = [r for r in self.db.get_messages(sid) if r["role"] == "tool"]
        rows = [r for r in rows if r["tool_call_id"] == call_id]
        return ([r for r in rows if r["tool_name"] == "image_generate"] or rows)[-1][
            "id"
        ]

    def assistant_id(self, sid: str) -> int:
        return [r["id"] for r in self.db.get_messages(sid) if r["tool_calls"]][-1]

    def row_declaring(self, sid: str, call_id: str) -> int:
        rows = self.db.get_messages(sid)
        return next(
            r["id"]
            for r in rows
            if r["tool_calls"] and r["tool_calls"][0]["id"] == call_id
        )

    def test_only_sql(self, sql: str, params: tuple[Any, ...]) -> int:
        """TEST ONLY: native has no writer for these shapes. Never part of the scanner."""
        self.test_only_sql_used = True
        return self.db._write_rowcount(sql, params)

    def scan(
        self, mod: Any, sid: str, row_id: Any, *, seam: Any = None, tip: Any = None
    ) -> Any:
        return mod.scan_active_set(
            self.db, sid, row_id, current_tip=tip or (lambda: sid), seam=seam
        )


# --------------------------------------------------------------------------- cases

CASES: list[tuple[str, str, Callable[[Any, Lab], Any]]] = []


def case(
    name: str, expected: str
) -> Callable[[Callable[[Any, Lab], Any]], Callable[[Any, Lab], Any]]:
    def register(fn: Callable[[Any, Lab], Any]) -> Callable[[Any, Lab], Any]:
        CASES.append((name, expected, fn))
        return fn

    return register


def pair_session(
    lab: Lab, rows: list[dict[str, Any]] | None = None, *, calls: Any = None
) -> str:
    sid = lab.session()
    lab.add(
        sid,
        rows
        if rows is not None
        else [user(), assistant(calls or direct_calls()), tool()],
    )
    return sid


def simple(name: str, expected: str, rows: Callable[[], list[dict[str, Any]]]) -> None:
    @case(name, expected)
    def run(mod: Any, lab: Lab) -> Any:
        sid = pair_session(lab, rows())
        return lab.scan(mod, sid, lab.tool_id(sid))


def _with_pair(
    *before: dict[str, Any], calls: Any = None, tool_row: dict[str, Any] | None = None
):
    return [
        user(),
        *before,
        assistant(calls or direct_calls()),
        tool_row or tool(),
        assistant(None, "done"),
    ]


# Positive shapes (native G1 call shapes).
simple("direct_positive", "ok", lambda: _with_pair())
simple("bridge_one_entry_positive", "ok", lambda: _with_pair(calls=bridge_calls()))
simple(
    "bridge_unique_inner_id_positive",
    "ok",
    lambda: _with_pair(
        calls=bridge_calls(entries=[{"name": "image_generate", "id": "inner-1"}])
    ),
)
simple(
    "bridge_multi_entry_ambiguous",
    "bridge_ambiguous",
    lambda: _with_pair(
        calls=bridge_calls(
            entries=[{"name": "image_generate"}, {"name": "image_generate"}]
        )
    ),
)
simple(
    "bridge_legacy_single_positive",
    "ok",
    lambda: _with_pair(
        calls=[call(CALL, "tool_call", {"name": "image_generate", "arguments": {}})]
    ),
)
simple(
    "bridge_other_entry_unsupported",
    "shape_unsupported",
    lambda: _with_pair(calls=bridge_calls(entries=[{"name": "terminal"}])),
)
simple(
    "other_outer_function_unsupported",
    "shape_unsupported",
    lambda: _with_pair(calls=[call(CALL, "terminal", {})]),
)


@case("native_empty_calls_write_null_positive", "ok")
def _empty_calls(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab, _with_pair(assistant([], "no calls")))
    stored_null = all(
        r["tool_calls"] is None
        for r in lab.db.get_messages(sid)
        if r["role"] == "assistant" and r["content"] == "no calls"
    )
    outcome = lab.scan(mod, sid, lab.tool_id(sid))
    return outcome if stored_null else None


# Uniqueness across the entire active set, regardless of tool name or the 256 window.
simple(
    "duplicate_tool_row_outside_window",
    "duplicate_tool_row",
    lambda: [
        user(),
        assistant([call(CALL, "terminal", {})]),
        tool(CALL, "terminal", "{}"),
        *filler(300),
        assistant(direct_calls()),
        tool(),
    ],
)
simple(
    "duplicate_tool_row_after_selected",
    "duplicate_tool_row",
    lambda: [*_with_pair(), tool(CALL, "terminal", "{}")],
)
simple(
    "duplicate_declaration_outside_window",
    "declaration_ambiguous",
    lambda: [
        user(),
        assistant([call(CALL, "terminal", {})]),
        *filler(300),
        assistant(direct_calls()),
        tool(),
    ],
)
simple(
    "duplicate_inner_declaration_outside_window",
    "declaration_ambiguous",
    lambda: [
        user(),
        assistant(bridge_calls("other", [{"name": "terminal", "id": CALL}])),
        *filler(300),
        assistant(direct_calls()),
        tool(),
    ],
)
simple("declaration_missing", "declaration_missing", lambda: [user(), tool()])
simple(
    "assistant_not_before_tool",
    "assistant_not_before_tool",
    lambda: [user(), tool(), assistant(direct_calls())],
)

# Malformed or uncertain assistant tool_calls anywhere in the active set refuse globally.
for _name, _calls, _expected in (
    ("element_not_mapping", ["x"], "tool_calls_uncertain"),
    (
        "element_without_id",
        [{"function": {"name": "terminal"}}],
        "tool_calls_uncertain",
    ),
    ("empty_id", [call("", "terminal", {})], "tool_calls_uncertain"),
    ("id_over_256", [call("x" * 257, "terminal", {})], "tool_calls_uncertain"),
    ("id_with_nul", [call("a\0b", "terminal", {})], "tool_calls_uncertain"),
    ("id_unpaired_surrogate", [call("a\ud800b", "terminal", {})], "malformed"),
    ("function_missing", [{"id": "c1", "type": "function"}], "tool_calls_uncertain"),
    (
        "function_not_mapping",
        [{"id": "c1", "function": "terminal"}],
        "tool_calls_uncertain",
    ),
    ("function_name_empty", [call("c1", "", {})], "tool_calls_uncertain"),
    (
        "bridge_args_not_json",
        [call("c1", "tool_call", "not json")],
        "tool_calls_uncertain",
    ),
    (
        "bridge_args_not_object",
        [call("c1", "tool_call", "[1]")],
        "tool_calls_uncertain",
    ),
    ("bridge_args_no_calls", [call("c1", "tool_call", "{}")], "tool_calls_uncertain"),
    ("bridge_entry_not_mapping", bridge_calls("c1", ["x"]), "tool_calls_uncertain"),
    (
        "bridge_inner_id_invalid",
        bridge_calls("c1", [{"name": "terminal", "id": ""}]),
        "tool_calls_uncertain",
    ),
    (
        "bridge_args_over_64k",
        [call("c1", "tool_call", json.dumps({"calls": [], "pad": "a" * 70000}))],
        "tool_calls_uncertain",
    ),
    (
        "calls_over_64_in_row",
        [call(f"c{i}", "terminal", {}) for i in range(65)],
        "declaration_limit",
    ),
):
    simple(f"malformed_{_name}", _expected, lambda c=_calls: _with_pair(assistant(c)))


@case("malformed_non_list_calls", "tool_calls_uncertain")
def _non_list(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab, _with_pair(assistant([call("c1", "terminal", {})])))
    other = lab.row_declaring(sid, "c1")
    lab.test_only_sql(
        "UPDATE messages SET tool_calls = ? WHERE id = ?", ('{"id": "c1"}', other)
    )
    return lab.scan(mod, sid, lab.tool_id(sid))


for _name, _blob in (
    ("stored_empty_list", "[]"),
    ("stored_garbage_blob", "{{not json"),
):

    def _stored(mod: Any, lab: Lab, blob: str = _blob) -> Any:
        sid = pair_session(lab, _with_pair(assistant([call("c1", "terminal", {})])))
        other = lab.row_declaring(sid, "c1")
        lab.test_only_sql(
            "UPDATE messages SET tool_calls = ? WHERE id = ?", (blob, other)
        )
        return lab.scan(mod, sid, lab.tool_id(sid))

    CASES.append((f"malformed_{_name}", "tool_calls_uncertain", _stored))

# Limits: rows, declared calls, budget.
for _label, _count, _expected in (
    ("4096_rows", 4096, "ok"),
    ("4097_rows", 4097, "too_many_rows"),
):

    def _rows(mod: Any, lab: Lab, count: int = _count) -> Any:
        sid = pair_session(
            lab, [user(), assistant(direct_calls()), tool(), *filler(count - 3)]
        )
        return lab.scan(mod, sid, lab.tool_id(sid))

    CASES.append((f"rows_{_label}", _expected, _rows))


def _declared_rows(full_rows: int, extra: int) -> list[dict[str, Any]]:
    rows = [
        assistant([call(f"d{r}-{i}", "terminal", {}) for i in range(64)])
        for r in range(full_rows)
    ]
    rows.append(assistant([call(f"e{i}", "terminal", {}) for i in range(extra)]))
    return [user(), *rows, assistant(direct_calls()), tool()]


# 63 full rows + 63 + the selected call = exactly 4096 declared; one more is refused.
simple("declared_4096_total_edge", "ok", lambda: _declared_rows(63, 63))
simple("declared_4097_total", "declaration_limit", lambda: _declared_rows(63, 64))


def _budget_session(lab: Lab, pad: int) -> str:
    return pair_session(
        lab,
        [
            user(),
            assistant([call("pad", "terminal", {"p": "a" * pad})]),
            assistant(direct_calls()),
            tool(),
        ],
    )


@case("budget_exact_edge_accepted", "ok")
def _budget_exact(mod: Any, lab: Lab) -> Any:
    sid = _budget_session(lab, 0)
    base = lab.scan(mod, sid, lab.tool_id(sid)).stats["budget_used"]
    sid = _budget_session(lab, mod.BUDGET_BYTES - base)
    outcome = lab.scan(mod, sid, lab.tool_id(sid))
    return outcome if outcome.stats["budget_used"] == mod.BUDGET_BYTES else None


@case("budget_edge_plus_one_refused", "budget_exceeded")
def _budget_over(mod: Any, lab: Lab) -> Any:
    sid = _budget_session(lab, 0)
    base = lab.scan(mod, sid, lab.tool_id(sid)).stats["budget_used"]
    sid = _budget_session(lab, mod.BUDGET_BYTES - base + 1)
    return lab.scan(mod, sid, lab.tool_id(sid))


# Selected row and result checks.
simple(
    "result_error_key",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content=result_text(error="nope"))),
)
simple(
    "result_success_false",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content=result_text(success=False))),
)
simple(
    "result_success_not_bool",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content=result_text(success="true"))),
)
simple(
    "result_image_missing",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content=result_text(image=_DROP))),
)
simple(
    "result_image_not_string",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content=result_text(image=["x"]))),
)
simple(
    "result_image_over_4096",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content=result_text(image="/" + "a" * 4096))),
)
simple(
    "result_image_nul",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content=result_text(image="/a\0b"))),
)
simple(
    "result_not_json",
    "result_not_candidate",
    lambda: _with_pair(tool_row=tool(content="plain text")),
)
simple(
    "result_over_64k",
    "result_too_large",
    lambda: _with_pair(tool_row=tool(content=result_text(pad="a" * 70000))),
)
simple(
    "tool_name_mismatch",
    "tool_name_mismatch",
    lambda: _with_pair(tool_row=tool(name="terminal")),
)
simple(
    "media_text_in_assistant_is_not_authority",
    "declaration_missing",
    lambda: [user(), assistant(None, f"MEDIA:{IMAGE}"), tool()],
)


@case("selected_is_not_a_tool_row", "selected_not_tool")
def _not_tool(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab)
    return lab.scan(mod, sid, lab.assistant_id(sid))


@case("selected_deactivated", "selected_not_active")
def _deactivated(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab)
    row = lab.tool_id(sid)
    lab.db.deactivate_message(sid, row)
    return lab.scan(mod, sid, row)


@case("selected_in_retired_parent_not_in_tip", "selected_not_active")
def _parent_row(mod: Any, lab: Lab) -> Any:
    parent = pair_session(lab)
    row = lab.tool_id(parent)
    child = lab.session(parent_session_id=parent)
    lab.add(child, [user("child"), assistant(None, "child reply")])
    return lab.scan(mod, child, row)


@case("selected_id_bool_refused", "invalid_argument")
def _bool_id(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab)
    return lab.scan(mod, sid, True)


# Changes between reads (real native writes at the seam).
def _mid_page(name: str, expected: str, act: Callable[[Lab, str], None]) -> None:
    @case(name, expected)
    def run(mod: Any, lab: Lab) -> Any:
        sid = pair_session(
            lab, [user(), assistant(direct_calls()), tool(), *filler(400)]
        )
        fired: list[int] = []

        def seam(phase: str, index: int) -> None:
            if phase == "page" and index == 1 and not fired:
                fired.append(1)
                act(lab, sid)

        return lab.scan(mod, sid, lab.tool_id(sid), seam=seam)


_mid_page(
    "append_between_pages",
    "rows_changed",
    lambda lab, sid: lab.db.append_message(sid, "user", "late"),
)
_mid_page(
    "deactivate_between_pages",
    "rows_changed",
    lambda lab, sid: lab.db.deactivate_message(
        sid, lab.db.get_active_message_ids(sid)[200]
    ),
)
_mid_page(
    "rewind_between_pages",
    "rows_changed",
    lambda lab, sid: lab.db.rewind_to_message(
        sid, [r["id"] for r in lab.db.get_messages(sid) if r["role"] == "user"][100]
    ),
)


@case("deactivate_before_final_id_list", "rows_changed")
def _before_ids1(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab, [user(), assistant(direct_calls()), tool(), *filler(10)])

    def seam(phase: str, _index: int) -> None:
        if phase == "ids1":
            lab.db.deactivate_message(sid, lab.db.get_active_message_ids(sid)[-1])

    return lab.scan(mod, sid, lab.tool_id(sid), seam=seam)


@case("tip_change_midpage", "tip_changed")
def _tip_change(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab, [user(), assistant(direct_calls()), tool(), *filler(400)])
    other = lab.session(parent_session_id=sid)
    state = {"tip": sid}

    def seam(phase: str, index: int) -> None:
        if phase == "page" and index == 1:
            state["tip"] = other

    return lab.scan(mod, sid, lab.tool_id(sid), seam=seam, tip=lambda: state["tip"])


@case("tip_changed_before_first_read", "tip_changed")
def _tip_first(mod: Any, lab: Lab) -> Any:
    sid = pair_session(lab)
    return lab.scan(mod, sid, lab.tool_id(sid), tip=lambda: "other")


# Recheck after the hypothetical file read.
def _claim(
    mod: Any, lab: Lab, rows: list[dict[str, Any]] | None = None
) -> tuple[str, Any]:
    sid = pair_session(lab, rows if rows is not None else _with_pair(*filler(6)))
    outcome = lab.scan(mod, sid, lab.tool_id(sid))
    return sid, outcome.claim if outcome.ok else None


def _recheck_case(
    name: str, expected: str, mutate: Callable[[Lab, str, Any], Any], *, tip: Any = None
) -> None:
    @case(name, expected)
    def run(mod: Any, lab: Lab) -> Any:
        sid, claim = _claim(mod, lab)
        if claim is None:
            return None
        mutate(lab, sid, claim)
        return mod.recheck(lab.db, claim, current_tip=tip or (lambda: sid))


def _noop(_lab: Lab, _sid: str, _claim: Any) -> None:
    return None


def _repair(lab: Lab, sid: str, claim: Any) -> None:
    """The real native blank-assistant in-place content repair, via the public batch append."""
    lab.db.append_messages_batch(
        sid,
        [
            {
                "role": "assistant",
                "_row_id": claim.assistant_row_id,
                "content": "repaired text",
            }
        ],
    )


def _tool_edit(lab: Lab, sid: str, claim: Any) -> None:
    lab.test_only_sql(
        "UPDATE messages SET content = ? WHERE id = ?",
        (result_text(image="/synthetic/other.png"), claim.tool_row_id),
    )


def _calls_edit(lab: Lab, sid: str, claim: Any) -> None:
    lab.test_only_sql(
        "UPDATE messages SET tool_calls = ? WHERE id = ?",
        (json.dumps(direct_calls("changed")), claim.assistant_row_id),
    )


def _unrelated(lab: Lab, claim: Any) -> int:
    return next(
        i
        for i in claim.active_ids
        if i not in (claim.tool_row_id, claim.assistant_row_id)
    )


def _deact_unrelated(lab: Lab, sid: str, claim: Any) -> None:
    lab.db.deactivate_message(sid, _unrelated(lab, claim))


def _undo_unrelated(lab: Lab, sid: str, claim: Any) -> None:
    row = _unrelated(lab, claim)
    lab.db.deactivate_message(sid, row)
    lab.test_only_sql("UPDATE messages SET active = 1 WHERE id = ?", (row,))


def _swap_unrelated(lab: Lab, sid: str, claim: Any) -> None:
    lab.test_only_sql(
        "UPDATE messages SET content = ? WHERE id = ?",
        ("swapped", _unrelated(lab, claim)),
    )


_recheck_case("recheck_unchanged", "ok", _noop)
_recheck_case("recheck_assistant_content_repair_accepted", "ok", _repair)
_recheck_case("recheck_tool_row_changed", "selected_changed", _tool_edit)
_recheck_case("recheck_assistant_tool_calls_changed", "selected_changed", _calls_edit)
_recheck_case(
    "recheck_append",
    "rows_changed",
    lambda lab, sid, _c: lab.db.append_message(sid, "user", "x"),
)
_recheck_case("recheck_deactivate_unrelated", "rows_changed", _deact_unrelated)
_recheck_case(
    "recheck_deactivate_selected",
    "rows_changed",
    lambda lab, sid, c: lab.db.deactivate_message(sid, c.tool_row_id),
)
_recheck_case("recheck_identical_restore_reevaluates_ok", "ok", _undo_unrelated)
_recheck_case("recheck_unrelated_content_swap_not_detected", "ok", _swap_unrelated)
_recheck_case("recheck_tip_changed", "tip_changed", _noop, tip=lambda: "other")


@case("public_values_carry_no_private_text", "ok")
def _public(mod: Any, lab: Lab) -> Any:
    sid, claim = _claim(mod, lab)
    outcome = mod.recheck(lab.db, claim, current_tip=lambda: sid)
    shown = (
        repr(outcome) + repr(claim) + json.dumps(outcome.report()) + repr(outcome.claim)
    )
    leaked = any(secret in shown for secret in (CALL, IMAGE, sid, "synthetic"))
    return None if leaked else outcome


# --------------------------------------------------------------------------- child main


def run_child(native_src: Path, root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(native_src))
    os.chdir(os.environ.get("PWD", str(root / "cwd")))
    counter = {"blocked": 0}
    install_network_denial(counter)
    mod = load_scanner()
    import hermes_state  # the checkout's own module (sys.path[0])

    db = hermes_state.SessionDB(db_path=root / "hermes" / "state.db")
    lab = Lab(db)
    records: list[dict[str, Any]] = []
    try:
        for name, expected, fn in CASES:
            try:
                outcome = fn(mod, lab)
                observed = (
                    outcome.reason
                    if outcome is not None
                    else "fixture_precondition_failed"
                )
                stats = dict(outcome.stats) if outcome is not None else {}
            except Exception as exc:  # closed type name only
                observed, stats = f"fixture_error_{type(exc).__name__}", {}
            records.append(
                {
                    "case": name,
                    "expected": expected,
                    "observed": observed,
                    "match": observed == expected,
                    "stats": stats,
                }
            )
    finally:
        db.close()
    modules = [getattr(m, "__file__", None) or "" for m in sys.modules.values()]
    native_prefix = str(native_src)
    return {
        "status": "COMPLETED",
        "cases": records,
        "case_count": len(records),
        "mismatches": [r["case"] for r in records if not r["match"]],
        "hermes_state_from_checkout": str(
            Path(hermes_state.__file__).resolve()
        ).startswith(native_prefix),
        "no_module_from_real_hermes_home": not any(
            str(Path.home() / ".hermes") in m for m in modules
        ),
        "test_only_sql_used": lab.test_only_sql_used,
        "network_connects_blocked": counter["blocked"],
        "scanner_limits": {
            "page": mod.PAGE_LIMIT,
            "rows": mod.MAX_ACTIVE_ROWS,
            "budget": mod.BUDGET_BYTES,
        },
        "reasons_covered": sorted({r["observed"] for r in records}),
    }


def child_main(native_src: Path, root: Path) -> int:
    try:
        report = run_child(native_src, root)
    except Exception as exc:  # closed type name and fixture line only
        lines = [
            f.lineno
            for f in traceback.extract_tb(exc.__traceback__)
            if f.filename == str(HERE)
        ]
        report = {
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error_fixture_line": lines[-1:],
        }
    fd = os.open(root / "result.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with open(fd, "w") as handle:
        json.dump(report, handle)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--native-src", type=Path, default=DEFAULT_NATIVE_SRC)
    run.add_argument("--evidence", type=Path, required=True)
    child = sub.add_parser("child")
    child.add_argument("--native-src", type=Path, required=True)
    child.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "child":
        return child_main(args.native_src, args.root)
    args.evidence.mkdir(mode=0o700, parents=True, exist_ok=True)
    report = run_parent(args.native_src)
    target = args.evidence / "active_scan.report.json"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with open(fd, "w") as handle:
        json.dump(report, handle, indent=2)
    bad = report.get("mismatches") or report.get("status") != "COMPLETED"
    print(
        json.dumps({k: report.get(k) for k in ("status", "case_count", "mismatches")})
    )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

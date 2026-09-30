#!/usr/bin/env python3
"""Evidence-only probe of the session-chat approval path in a REAL Hermes checkout.

Runs the real `APIServerAdapter._handle_session_chat_stream`, its executor hop, the real
`tools.approval.check_all_command_guards` and the real `POST /v1/runs/{id}/approval` handler.
Only the model is faked: its "tool call" asks the real guard about a synthetic command and
records what the guard decided. No command is executed, no socket is opened (the handlers are
awaited directly and the SSE response is a recorder), the tirith scanner is replaced by an
allow-stub so nothing can be fetched or spawned, and HERMES_HOME is a disposable directory.

This is qualification evidence for one exact Hermes source. It does not enable approvals, add a
fingerprint, or certify compatibility.

Limits: the disconnect scenario only simulates the interrupt flag (a fake agent's `interrupt()`
sets it on the fake agent thread); it does not prove a real agent thread is unblocked. Upstream
still accepts an API-key answer without `request_id`, and `all`/`resolve_all`, so the probe does
NOT show upstream requires an ID: HMP must enforce the exact request_id itself.
Run it with the Hermes interpreter:

    <hermes-venv>/bin/python tools/compat/session_chat_approval_probe.py --hermes-src <export>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from bridge_files import _isolate_hermes_home, _refuse_real_home

SYNTHETIC_COMMAND = "rm -rf /hmp-synthetic-approval-probe-target"
SYNTHETIC_PROMPT = "synthetic approval probe prompt"
KEY = "hmp-synthetic-api-key"
WAIT_S = 15.0


class Check:
    """Collects named pass/fail results so one run reports every gap, not just the first."""

    def __init__(self) -> None:
        self.results: dict[str, bool] = {}
        self.duplicates: list[str] = []

    def __call__(self, name: str, ok: bool, detail: str = "") -> None:
        if name in self.results:
            self.duplicates.append(name)
            ok = False  # a repeated name would silently overwrite earlier evidence
        self.results[name] = bool(ok)
        if not ok:
            print(f"FAIL {name}: {detail}", file=sys.stderr)


class Recorder:
    """Stands in for `web.StreamResponse`: records SSE frames, optionally simulates a drop."""

    def __init__(self, *, drop_after_approval: bool = False) -> None:
        self.events: list[tuple[str, dict]] = []
        self.approval_seen = asyncio.Event()
        self.drop_after_approval = drop_after_approval

    async def prepare(self, request) -> None:
        pass

    async def write(self, payload: bytes) -> None:
        name, data = None, None
        for line in payload.decode().splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if name is not None and data is not None:
            self.events.append((name, data))
        if name == "approval.request":
            self.approval_seen.set()
            if self.drop_after_approval:
                raise ConnectionResetError("simulated client disconnect")

    def names(self) -> list[str]:
        return [name for name, _ in self.events]


def make_request(*, match_info: dict, body: dict | None = None, key: str | None = KEY):
    request = MagicMock()
    request.headers = {"Authorization": f"Bearer {key}"} if key else {}
    request.match_info = match_info
    request.json = AsyncMock(return_value=body if body is not None else {})
    request.query = {}
    return request


class Harness:
    """One disposable adapter + session per scenario; a fake model asks the real guard."""

    def __init__(self, api: SimpleNamespace, tmp: Path, label: str) -> None:
        self.api = api
        self.guard_results: list[dict] = []
        self.executed: list[
            str
        ] = []  # the fake executor's record; nothing is ever spawned
        self.blocked = threading.Event()
        self.finished = threading.Event()
        self.worker_thread: int | None = None
        self.interrupted = threading.Event()
        self.db = api.state.SessionDB(tmp / f"{label}.db")
        self.adapter = api.server.APIServerAdapter(
            api.config.PlatformConfig(enabled=True, extra={"key": KEY})
        )
        self.adapter._session_db = self.db
        self.session_id = self.db.create_session(f"probe-{label}", "api_server")
        harness = self

        class FakeAgent:
            session_prompt_tokens = session_completion_tokens = session_total_tokens = 0
            provider, model = "synthetic", "synthetic"

            def __init__(self) -> None:
                self.session_id = harness.session_id

            def interrupt(self, message=None) -> None:
                harness.interrupted.set()
                if harness.worker_thread is not None:
                    api.interrupt.set_interrupt(
                        True, harness.worker_thread, reason="synthetic disconnect"
                    )

            def run_conversation(
                self, user_message, conversation_history, task_id, **_kw
            ):
                harness.worker_thread = threading.get_ident()
                harness.blocked.set()
                try:
                    verdict = api.approval.check_all_command_guards(
                        SYNTHETIC_COMMAND, "local"
                    )
                    harness.guard_results.append(verdict)
                    if verdict.get("approved"):
                        harness.executed.append(
                            SYNTHETIC_COMMAND
                        )  # recorded, never run
                    return {
                        "final_response": "synthetic turn over",
                        "session_id": harness.session_id,
                    }
                finally:
                    api.interrupt.set_interrupt(False, harness.worker_thread)
                    harness.finished.set()

        self.adapter._create_agent = lambda **kwargs: FakeAgent()

    async def start(self, recorder: Recorder) -> asyncio.Task:
        request = make_request(
            match_info={"session_id": self.session_id},
            body={"message": SYNTHETIC_PROMPT},
        )
        with patch(
            "gateway.platforms.api_server.web.StreamResponse", return_value=recorder
        ):
            task = asyncio.create_task(
                self.adapter._handle_session_chat_stream(request)
            )
            await asyncio.wait_for(recorder.approval_seen.wait(), WAIT_S)
        return task

    async def answer(
        self, run_id: str, body: dict, *, key: str | None = KEY, profile=None
    ):
        request = make_request(match_info={"run_id": run_id}, body=body, key=key)
        token = self.api.server._api_request_profile.set(profile) if profile else None
        try:
            response = await self.adapter._handle_run_approval(request)
        finally:
            if token is not None:
                self.api.server._api_request_profile.reset(token)
        return response.status, json.loads(response.text)

    def pending(self, run_id: str) -> int:
        return len(self.api.approval.list_gateway_approvals(run_id))

    def leaked_state(self, run_id: str) -> list[str]:
        api, adapter = self.api, self.adapter
        leaks = []
        if run_id in adapter._run_approval_sessions:
            leaks.append("run_approval_sessions")
        if run_id in adapter._active_run_agents:
            leaks.append("active_run_agents")
        if run_id in api.approval._gateway_queues:
            leaks.append("gateway_queue")
        if run_id in api.approval._gateway_notify_cbs:
            leaks.append("gateway_notify")
        if api.approval.pending_gateway_approval_count():
            leaks.append("pending_count")
        return leaks


def use_aiohttp_overlay(overlay: Path) -> None:
    """Make an out-of-tree aiohttp (and its pure-Python fallbacks) importable.

    The pinned Hermes test environment omits the `messaging` extra, so `web` is None there and
    the real handler cannot run. The overlay is a scratch directory; the interpreter's own
    environment is never modified. Compiled extensions are disabled because a cached wheel may
    not match this interpreter's ABI.
    """
    for name in ("AIOHTTP", "MULTIDICT", "YARL", "FROZENLIST", "PROPCACHE"):
        os.environ[f"{name}_NO_EXTENSIONS"] = "1"
    sys.path.append(str(overlay))


def load_api(src: Path) -> SimpleNamespace:
    import importlib

    sys.path.insert(0, str(src))
    try:
        import aiohttp  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "GAP: aiohttp is not importable in this interpreter, so gateway.platforms.api_server "
            f"has no `web` and _handle_session_chat_stream cannot run ({exc}). "
            "Pass --aiohttp-overlay <dir> or use an environment with Hermes's messaging extra."
        ) from exc
    return SimpleNamespace(
        **{
            name: importlib.import_module(module)
            for name, module in {
                "server": "gateway.platforms.api_server",
                "config": "gateway.config",
                "state": "hermes_state",
                "approval": "tools.approval",
                "interrupt": "tools.interrupt",
            }.items()
        }
    )


async def scenario_request_and_deny(api, tmp, check: Check) -> None:
    h = Harness(api, tmp, "deny")
    recorder = Recorder()
    task = await h.start(recorder)
    request_events = [e for name, e in recorder.events if name == "approval.request"]
    check("request.emitted_once", len(request_events) == 1, str(recorder.names()))
    event = request_events[0]
    request_id, run_id = event.get("request_id"), event.get("run_id")
    check(
        "request.request_id_nonempty",
        isinstance(request_id, str) and bool(request_id.strip()),
    )
    check(
        "request.run_id_nonempty", isinstance(run_id, str) and run_id.startswith("run_")
    )
    choices = event.get("choices")
    check(
        "request.choices_offer_once_and_deny",
        isinstance(choices, list) and {"once", "deny"} <= set(choices),
        str(choices),
    )
    check(
        "request.status_waiting",
        h.adapter._run_statuses.get(run_id, {}).get("status") == "waiting_for_approval",
    )
    check("request.pending_exactly_one", h.pending(run_id) == 1)
    check("request.model_blocked_not_executed", h.blocked.is_set() and not h.executed)
    seen = h.adapter._run_statuses[run_id].get("approval", {})
    check("request.status_carries_same_id", seen.get("request_id") == request_id)

    # Wrong request id, wrong run id, wrong key, wrong profile: none may resolve or unblock.
    status, body = await h.answer(run_id, {"choice": "once", "request_id": "wrong-id"})
    check(
        "wrong_request_id.rejected",
        status == 409 and body["error"]["code"] == "approval_not_pending",
        f"{status} {body}",
    )
    status, _ = await h.answer(
        "run_" + "0" * 32, {"choice": "once", "request_id": request_id}
    )
    check("wrong_run_id.rejected", status == 404, str(status))
    status, _ = await h.answer(
        run_id, {"choice": "once", "request_id": request_id}, key="wrong-key"
    )
    check("wrong_key.rejected", status == 401, str(status))
    status, _ = await h.answer(
        run_id, {"choice": "once", "request_id": request_id}, profile="other"
    )
    check("wrong_profile.rejected_no_profile_key", status == 401, str(status))
    with patch.object(h.adapter, "_expected_api_key", return_value=KEY):
        # Same credential presented under another profile: ownership alone must refuse it.
        status, _ = await h.answer(
            run_id, {"choice": "once", "request_id": request_id}, profile="other"
        )
    check("wrong_profile.rejected_by_run_ownership", status == 404, str(status))
    check(
        "wrong_answers.left_pending",
        h.pending(run_id) == 1 and not h.executed and not h.finished.is_set(),
    )
    status, _ = await h.answer(run_id, {"choice": "bogus", "request_id": request_id})
    check("invalid_choice.rejected", status == 400, str(status))

    status, body = await h.answer(run_id, {"choice": "deny", "request_id": request_id})
    check(
        "deny.accepted_exact_id",
        status == 200
        and body.get("resolved") == 1
        and body.get("request_id") == request_id,
        f"{status} {body}",
    )
    await asyncio.wait_for(task, WAIT_S)
    verdict = h.guard_results[0] if h.guard_results else {}
    check(
        "deny.guard_not_approved",
        verdict.get("approved") is False
        and verdict.get("outcome") == "denied"
        and verdict.get("user_consent") is False,
        str(verdict),
    )
    check("deny.no_execution", not h.executed)
    check(
        "deny.stream_terminal",
        recorder.names()[-1] == "done" and "run.completed" in recorder.names(),
        str(recorder.names()),
    )
    status, body = await h.answer(run_id, {"choice": "once", "request_id": request_id})
    check(
        "replay.rejected",
        status == 409 and body["error"]["code"] == "approval_not_active",
        f"{status} {body}",
    )
    check(
        "deny.no_leaked_state", not h.leaked_state(run_id), str(h.leaked_state(run_id))
    )
    h.db.close()


async def scenario_exact_once(api, tmp, check: Check) -> None:
    """Positive control: the same route with the exact id does release the fake executor."""
    h = Harness(api, tmp, "once")
    recorder = Recorder()
    task = await h.start(recorder)
    event = next(e for name, e in recorder.events if name == "approval.request")
    status, body = await h.answer(
        event["run_id"], {"choice": "once", "request_id": event["request_id"]}
    )
    check(
        "once.accepted_exact_id",
        status == 200 and body.get("resolved") == 1,
        f"{status} {body}",
    )
    await asyncio.wait_for(task, WAIT_S)
    check(
        "once.guard_approved_fake_executor_only",
        h.guard_results
        and h.guard_results[0].get("approved") is True
        and h.executed == [SYNTHETIC_COMMAND],
    )
    check("once.no_leaked_state", not h.leaked_state(event["run_id"]))
    h.db.close()


async def scenario_disconnect(api, tmp, check: Check) -> None:
    """A dropped stream interrupts the turn; the pending approval is withdrawn, never granted."""
    h = Harness(api, tmp, "disconnect")
    recorder = Recorder(drop_after_approval=True)
    task = await h.start(recorder)
    try:
        await asyncio.wait_for(task, WAIT_S)
    except TimeoutError:
        check(
            "disconnect.handler_returned", False, "handler still waiting after the drop"
        )
        api.approval.unregister_gateway_notify(next(iter(h.adapter._run_statuses)))
        h.finished.wait(WAIT_S)
        return
    run_id = next(iter(h.adapter._run_statuses))
    check("disconnect.handler_returned", True)
    check("disconnect.agent_interrupted", h.interrupted.is_set())
    check("disconnect.turn_finished", h.finished.is_set())
    verdict = h.guard_results[0] if h.guard_results else {}
    check(
        "disconnect.guard_not_approved", verdict.get("approved") is False, str(verdict)
    )
    check("disconnect.no_execution", not h.executed)
    check(
        "disconnect.no_leaked_state",
        not h.leaked_state(run_id),
        str(h.leaked_state(run_id)),
    )
    # The real id: a made-up one would pass even if the original request were still pending.
    request_id = next(e for n, e in recorder.events if n == "approval.request")[
        "request_id"
    ]
    status, body = await h.answer(run_id, {"choice": "once", "request_id": request_id})
    check(
        "disconnect.late_answer_rejected",
        status == 409 and body["error"]["code"] == "approval_not_active",
        f"{status} {body}",
    )
    api.interrupt.set_interrupt(False, h.worker_thread)
    h.db.close()


async def run_all(api, tmp: Path) -> Check:
    check = Check()
    # Ask-mode is what a running gateway exports at startup; api_server depends on it for this
    # route (tools.approval._presence). The scanner stub keeps tirith from fetching or spawning.
    with (
        patch.dict("os.environ", {"HERMES_EXEC_ASK": "1"}),
        patch.object(
            api.approval,
            "_tirith_scan",
            return_value={"action": "allow", "findings": [], "summary": ""},
        ),
    ):
        matched, _, _ = api.approval.detect_dangerous_command(SYNTHETIC_COMMAND)
        check("guard.synthetic_command_is_dangerous", matched)
        for scenario in (
            scenario_request_and_deny,
            scenario_exact_once,
            scenario_disconnect,
        ):
            await scenario(api, tmp, check)
    return check


def main() -> int:
    if not __debug__:
        raise RuntimeError("qualification requires assertions enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-src", type=Path, required=True)
    parser.add_argument(
        "--aiohttp-overlay",
        type=Path,
        default=None,
        help="scratch dir holding aiohttp when the interpreter lacks it",
    )
    args = parser.parse_args()
    _refuse_real_home(args.hermes_src)
    if args.aiohttp_overlay is not None:
        use_aiohttp_overlay(args.aiohttp_overlay)
    with (
        _isolate_hermes_home(),
        tempfile.TemporaryDirectory(prefix="hmp-session-approval-") as tmp,
    ):
        # Upstream defaults to smart mode, which first asks an auxiliary model. Pin the human path
        # in the disposable home so the probe can never attempt a model call.
        (Path(os.environ["HERMES_HOME"]) / "config.yaml").write_text(
            "approvals:\n  mode: manual\n  timeout: 30\n"
        )
        api = load_api(args.hermes_src)
        check = asyncio.run(run_all(api, Path(tmp)))
    results = check.results
    ok = bool(results) and all(results.values()) and not check.duplicates
    print(
        json.dumps(
            {"checks": results, "duplicates": check.duplicates, "ok": ok},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

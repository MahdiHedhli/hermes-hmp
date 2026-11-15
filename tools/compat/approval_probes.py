#!/usr/bin/env python3
"""F3 behavioral qualification against REAL Hermes, in its interpreter and isolated home.

No gateway, sockets, model, credentials, or tool execution. Only prompt queues and inbound
routing are exercised. Test doubles replace delivery/turn scheduling, never the security guards
or prompt resolvers. Control-enabled comparisons ensure each harness can resolve its waiter.
Run with --hermes-src <export>; never use the live home as an import-time configuration root.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
import threading
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bridge_files import _isolate_hermes_home, _refuse_real_home


def load_api(src: Path) -> SimpleNamespace:
    sys.path.insert(0, str(src))
    return SimpleNamespace(**{
        name: importlib.import_module(module)
        for name, module in {
            "event": "gateway.platforms.event", "base": "gateway.platforms.base",
            "busy": "gateway.run_busy", "inbound": "gateway.run_inbound",
            "approval": "tools.approval", "wait": "tools.approval_gateway_wait",
            "clarify": "tools.clarify_gateway", "session": "gateway.session",
            "config": "gateway.config", "interrupt": "tools.interrupt",
        }.items()
    })


def plaintext_approval_resolver(mixin: type) -> tuple[dict, dict]:
    """Read the active approval words from either known Hermes resolver shape."""
    method = getattr(mixin, "_plaintext_approval_words", None)
    if method is not None:
        names = ("_PLAINTEXT_APPROVAL_EXTRA_WORDS", "_PLAINTEXT_APPROVAL_INPUT_KEYS")
        missing = [name for name in names if not hasattr(mixin, name)]
        if missing or not callable(method):
            raise RuntimeError(f"approval resolver method unusable; missing {missing}")
        attrs = {name: getattr(mixin, name) for name in names}
        words = method(SimpleNamespace(**attrs))
        attrs["_plaintext_approval_words"] = method
    elif hasattr(mixin, "_PLAINTEXT_APPROVAL_WORDS"):
        words = mixin._PLAINTEXT_APPROVAL_WORDS
        attrs = {"_PLAINTEXT_APPROVAL_WORDS": words}
    else:
        raise RuntimeError("no known plaintext approval resolver in target build")
    if not isinstance(words, dict) or not words:
        raise RuntimeError("plaintext approval word set is empty or not a mapping")
    for word, match in words.items():
        if (not isinstance(word, str) or not word.strip() or not isinstance(match, tuple)
                or len(match) != 2 or not all(isinstance(part, str) for part in match)
                or match[0] not in ("approve", "deny")):
            raise RuntimeError("plaintext approval word set is malformed")
    return dict(words), attrs


def make_runner(attrs: dict, **handlers) -> SimpleNamespace:
    """Bind a method-style resolver to the fake runner without changing its source."""
    runner = SimpleNamespace(**{k: v for k, v in attrs.items()
                                if k != "_plaintext_approval_words"}, **handlers)
    if "_plaintext_approval_words" in attrs:
        runner._plaintext_approval_words = partial(attrs["_plaintext_approval_words"], runner)
    return runner


async def control_disabled_input(api: SimpleNamespace) -> None:
    """Slash, active-language approval words, and clarify text stay pending."""
    key = "hmp-qualification-session"
    source = api.session.SessionSource(
        platform=api.config.Platform.LOCAL, chat_id="fixture-chat", user_id="fixture-user",
    )
    words, resolver_attrs = plaintext_approval_resolver(api.busy.GatewayBusySessionMixin)
    words = list(words)
    slash_confirm_words = ["ok", "confirm", "cancel", "remember", "nevermind"]
    inputs = ["/approve", "/approve all", "/approve always", "/deny", "/stop", "/reset",
              *words, *slash_confirm_words, "1", "A", "Other", "fixture free text"]
    for choices in (["A", "B"], None):
        for text in inputs:
            entry = api.wait._ApprovalEntry({"request_id": "approval-one"})
            api.approval._gateway_queues[key] = [entry]
            clarify = api.clarify.register("clarify-one", key, "Fixture?", choices)
            assert api.approval.has_blocking_approval(key)
            event = api.event.MessageEvent(text=text, source=source, allow_gateway_control=False)
            assert not event.is_command() and event.get_command() is None

            async def approve(event):
                api.approval.resolve_gateway_approval(key, "once")

            runner = make_runner(
                resolver_attrs,
                _handle_approve_command=approve, _handle_deny_command=approve,
                _delivery_adapter_for=lambda source: None,
                _hm_update_prompt_reply=lambda *args: None,
                _hm_slash_confirm_reply=AsyncMock(return_value=None),
                _pending_event_audio_paths=lambda event: [],
                _prepare_clarify_reply_text=AsyncMock(return_value=text),
            )
            inbound = api.inbound.GatewayInboundMixin
            runner._hm_clarify_reply = partial(inbound._hm_clarify_reply, runner)

            async def busy(event, session_key, runner=runner):
                await api.busy.GatewayBusySessionMixin._route_plaintext_approval_while_busy(
                    runner, event, session_key)
                return True  # delivery/scheduling boundary; no new model turn

            async def inline(event, runner=runner, inbound=inbound, **kwargs):
                if event.get_command() in ("approve", "deny"):
                    await approve(event)
                else:
                    await inbound._hm_pending_reply_intercepts(runner, event, source, key)

            inline = AsyncMock(side_effect=inline)
            base = api.base.BasePlatformAdapter
            adapter = SimpleNamespace(
                name="fixture", _message_handler=inline, _canonicalize=lambda source: None,
                _drop_unresolved=lambda event: False, _event_session_key=lambda event: key,
                _heal_stale_session_lock=lambda key: None, _active_sessions={key: object()},
                _busy_session_handler=busy, _dispatch_inline_reply=inline,
                _dispatch_active_session_command=AsyncMock(),
                _discard_text_debounce=lambda key: None,
            )
            adapter._handle_message_while_active = partial(
                base._handle_message_while_active, adapter)
            try:
                await base.handle_message(adapter, event)
                # Also exercise the runner intercept independently of the base adapter guard.
                await inbound._hm_pending_reply_intercepts(runner, event, source, key)
                assert not entry.event.is_set() and entry.result is None
                assert not clarify.event.is_set() and clarify.response is None
                adapter._dispatch_active_session_command.assert_not_awaited()
                inline.assert_not_awaited()
                assert event.text == text
                # Positive controls: same real busy and clarify paths can resolve these entries.
                event.allow_gateway_control = True
                event.text = text if text in words else "yes"
                assert await api.busy.GatewayBusySessionMixin._route_plaintext_approval_while_busy(
                    runner, event, key)
                assert entry.event.is_set() and entry.result == "once"
                runner._prepare_clarify_reply_text = AsyncMock(
                    return_value="1" if choices else "reply")
                event.text = "1" if choices else "reply"
                await base.handle_message(adapter, event)
                assert clarify.event.is_set()
                slash_entry = api.wait._ApprovalEntry({"request_id": "slash-control"})
                api.approval._gateway_queues[key] = [slash_entry]
                event.text = "/approve"
                await base.handle_message(adapter, event)
                assert slash_entry.event.is_set() and slash_entry.result == "once"
            finally:
                api.approval._gateway_queues.pop(key, None)
                api.clarify.resolve_gateway_clarify("clarify-one", "cleanup")
                api.clarify.wait_for_response("clarify-one", 0.001)


def exact_request_id(api: SimpleNamespace) -> None:
    """Wrong session/id and replay resolve nothing; second ID leaves the first untouched."""
    key = "hmp-qualification-session"
    first, second = [api.wait._ApprovalEntry({"request_id": rid}) for rid in ("first", "second")]
    api.approval._gateway_queues[key] = [first, second]
    try:
        resolve = api.approval.resolve_gateway_approval
        assert resolve("foreign-session", "once", request_id="second") == 0
        assert resolve(key, "once", request_id="missing") == 0
        assert not first.event.is_set() and not second.event.is_set()
        assert resolve(key, "deny", request_id="second") == 1
        assert second.event.is_set() and second.result == "deny"
        assert not first.event.is_set() and first.result is None
        assert resolve(key, "once", request_id="second") == 0
        assert resolve(key, "once", request_id="first") == 1
        assert first.event.is_set() and first.result == "once"
        assert api.approval.list_gateway_approvals(key) == []
    finally:
        api.approval._gateway_queues.pop(key, None)


def _blocking_wait(api: SimpleNamespace, key: str, request_id: str):
    """Run Hermes' real blocking approval wait on a worker thread, as the agent thread does.

    Returns (thread, box, published). `box["tid"]` is the worker's thread id (the interrupt
    target) and `box["result"]` the wait's decision dict once it ends.
    """
    box: dict = {}
    published = threading.Event()
    data = {"command": "true", "pattern_key": "hmp-probe", "request_id": request_id}

    def notify(payload: dict) -> None:
        box["payload"] = payload
        published.set()

    def work() -> None:
        box["tid"] = threading.current_thread().ident
        try:
            box["result"] = api.wait._await_gateway_decision(key, notify, data)
        except Exception as exc:  # surfaced to the probe, never swallowed
            box["error"] = repr(exc)

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread, box, published


def interrupted_wait_fails_closed(api: SimpleNamespace) -> None:
    """An interrupt ends a pending approval wait as a deny with a cancel cause, never approval."""
    key, request_id = "hmp-qualification-interrupt", "interrupt-one"
    thread, box, published = _blocking_wait(api, key, request_id)
    try:
        assert published.wait(10), f"wait never published its prompt: {box}"
        assert [e["request_id"] for e in api.approval.list_gateway_approvals(key)] == [request_id]
        api.interrupt.set_interrupt(True, box["tid"], reason="fixture interrupt")
        thread.join(15)
        assert not thread.is_alive(), "interrupt did not end the approval wait"
        assert "error" not in box, box
        result = box["result"]
        assert result["choice"] == "deny" and result.get("cancelled"), result
        assert api.approval.list_gateway_approvals(key) == []
        assert api.approval.resolve_gateway_approval(key, "once", request_id=request_id) == 0
    finally:
        api.interrupt.set_interrupt(False, box.get("tid"))
        api.approval._gateway_queues.pop(key, None)


def timed_out_wait_fails_closed(api: SimpleNamespace) -> None:
    """A wait that outlives approvals.timeout ends unresolved with no choice; a late answer by
    the expired request ID resolves nothing."""
    key, request_id = "hmp-qualification-timeout", "timeout-one"
    context = api.wait._ctx
    original = context._get_approval_timeout
    context._get_approval_timeout = lambda: 0.5
    try:
        thread, box, published = _blocking_wait(api, key, request_id)
        assert published.wait(10), f"wait never published its prompt: {box}"
        thread.join(15)
        assert not thread.is_alive(), "approval timeout did not end the wait"
        assert "error" not in box, box
        result = box["result"]
        assert result["resolved"] is False and result["choice"] is None, result
        assert api.approval.list_gateway_approvals(key) == []
        assert api.approval.resolve_gateway_approval(key, "once", request_id=request_id) == 0
    finally:
        context._get_approval_timeout = original
        api.approval._gateway_queues.pop(key, None)


def main() -> int:
    if not __debug__:
        raise RuntimeError("qualification requires assertions enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-src", type=Path, required=True)
    args = parser.parse_args()
    _refuse_real_home(args.hermes_src)
    with _isolate_hermes_home():
        api = load_api(args.hermes_src)
        asyncio.run(control_disabled_input(api))
        exact_request_id(api)
        interrupted_wait_fails_closed(api)
        timed_out_wait_fails_closed(api)
    print(json.dumps({"control_ok": True, "exact_id_ok": True,
                      "interrupt_ok": True, "timeout_ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

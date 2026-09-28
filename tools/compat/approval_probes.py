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
            "config": "gateway.config",
        }.items()
    })


async def control_disabled_input(api: SimpleNamespace) -> None:
    """Slash, every bare approval word, and choice/free-text clarify stay pending."""
    key = "hmp-qualification-session"
    source = api.session.SessionSource(
        platform=api.config.Platform.LOCAL, chat_id="fixture-chat", user_id="fixture-user",
    )
    words = list(api.busy.GatewayBusySessionMixin._PLAINTEXT_APPROVAL_WORDS)
    inputs = ["/approve", "/approve all", "/approve always", "/deny", "/stop", "/reset",
              *words, "1", "A", "Other", "fixture free text"]
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

            runner = SimpleNamespace(
                _PLAINTEXT_APPROVAL_WORDS=api.busy.GatewayBusySessionMixin._PLAINTEXT_APPROVAL_WORDS,
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
                event.text = "yes"
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
    print(json.dumps({"control_ok": True, "exact_id_ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Spec 034 fences through the real `adapter.open_components` (R9, R10, N20, N21, N22, N33).

The adapter module is imported against stand-ins for Hermes's documented platform API, the compat
gate is replaced by a gate that reports chosen eligibility, and the Phone helpers are fake
modules installed for the test only. No Hermes code runs and no real home is touched.
"""

from __future__ import annotations

import importlib
import logging
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import compat, direct_send, identity, prompts
from hmp_plugin.compat import Eligibility, Feature, FeatureStatus, Unavailable
from hmp_plugin.hermes_version import HermesVersion, Scheme, VersionSource
from hmp_plugin.logging_policy import LOGGER_NAME
from hmp_plugin.prompts import PromptRow, PromptStore

from .hmp_kit import HOST, identity_kwargs
from .test_approvals import IID, PROFILE, REQ, RUN, USER, FakeResolver, _answer, _frame

FLOOR = HermesVersion(Scheme.SEMVER, (0, 21, 5), VersionSource.LITERAL)


class _Base:
    def __init__(self, config: Any, platform: Any) -> None:
        self.config, self.platform = config, platform

    def _mark_connected(self, **_k: Any) -> None: ...
    def _mark_disconnected(self) -> None: ...
    def _set_fatal_error(self, *_a: Any, **_k: Any) -> None: ...


@pytest.fixture()
def adapter_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.ModuleType]:
    gateway = types.ModuleType("gateway")
    config = types.ModuleType("gateway.config")
    platforms = types.ModuleType("gateway.platforms")
    base = types.ModuleType("gateway.platforms.base")
    config.Platform = lambda name: ("platform", name)  # type: ignore[attr-defined]
    base.BasePlatformAdapter = _Base  # type: ignore[attr-defined]
    base.SendResult = lambda success, **_k: types.SimpleNamespace(success=success)  # type: ignore[attr-defined]
    for name, mod in (
        ("gateway", gateway),
        ("gateway.config", config),
        ("gateway.platforms", platforms),
        ("gateway.platforms.base", base),
    ):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delitem(sys.modules, "hmp_plugin.adapter", raising=False)
    module = importlib.import_module("hmp_plugin.adapter")
    yield module
    sys.modules.pop("hmp_plugin.adapter", None)


class _Runner:
    def served_profile_names(self) -> list[str]:
        return []


def _eligibility(**closed: Unavailable) -> Eligibility:
    features = {f: FeatureStatus(True) for f in Feature}
    for name, reason in closed.items():
        features[Feature(name)] = FeatureStatus(False, reason)
    return Eligibility(FLOOR, None, features)


def _open(
    adapter_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    eligibility: Eligibility | None,
    *,
    supported: bool = True,
):
    kwargs = identity_kwargs(tmp_path)
    custody = identity.resolve_custody(
        env=kwargs["env"], hermes_root=kwargs["hermes_root"], binding_root=kwargs["binding_root"]
    )
    real = identity.load_or_create
    monkeypatch.setattr(adapter_module.identity, "resolve_custody", lambda *_a, **_k: custody)
    monkeypatch.setattr(
        adapter_module.identity,
        "load_or_create",
        lambda store, **_k: real(
            store,
            env=kwargs["env"],
            hermes_root=kwargs["hermes_root"],
            binding_root=kwargs["binding_root"],
            host_id=lambda: HOST,
        ),
    )

    class Gate:
        def evaluate(self) -> Any:
            status = compat.CompatStatus.SUPPORTED if supported else compat.CompatStatus.UNSUPPORTED
            return compat.CompatResult(status, eligibility=eligibility)

    monkeypatch.setattr(adapter_module.compat, "default_gate", lambda **_k: Gate())
    adapter = types.SimpleNamespace(
        gateway_runner=_Runner(), config=types.SimpleNamespace(extra={})
    )
    return adapter, adapter_module.open_components(adapter)


def _phone_modules(monkeypatch: pytest.MonkeyPatch) -> dict[str, types.ModuleType]:
    approval = types.ModuleType("tools.approval")
    context = types.ModuleType("tools.approval_context")
    clarify = types.ModuleType("tools.clarify_gateway")
    approval.list_gateway_approvals = lambda key: [{"request_id": REQ}]
    approval.resolve_gateway_approval = lambda *a, **k: 1
    context._get_approval_timeout = lambda: 300
    clarify.get_clarify_timeout = lambda: 3600
    clarify.resolve_gateway_clarify = lambda cid, text: True
    clarify.mark_awaiting_text = lambda cid: True
    for name, module in (
        ("tools.approval", approval),
        ("tools.approval_context", context),
        ("tools.clarify_gateway", clarify),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    return {"approval": approval, "context": context, "clarify": clarify}


# --------------------------------------------------------------------------------------------
# Availability is bound once, from eligibility, and defaults closed (R5, N33)
# --------------------------------------------------------------------------------------------


def test_members_follow_the_eligibility_evaluation(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _phone_modules(monkeypatch)
    _adapter, ctx = _open(adapter_module, monkeypatch, tmp_path / "all", _eligibility())
    assert ctx.is_approvals_available() is True and ctx.is_phone_chat_available() is True
    assert isinstance(ctx.prompt_store, prompts.PromptStore)
    ctx.store.close()

    _adapter, ctx = _open(
        adapter_module,
        monkeypatch,
        tmp_path / "phone-closed",
        _eligibility(phone_chat=Unavailable.DEPENDENCY_MISSING),
    )
    assert ctx.is_approvals_available() is True  # Bot Chat does not depend on the Phone helpers
    assert ctx.is_phone_chat_available() is False
    ctx.store.close()

    _adapter, ctx = _open(
        adapter_module,
        monkeypatch,
        tmp_path / "send-closed",
        _eligibility(send=Unavailable.DEPENDENCY_MISSING, approvals=Unavailable.REQUIRES_SEND,
                     phone_chat=Unavailable.REQUIRES_SEND),
    )
    assert ctx.is_approvals_available() is False and ctx.is_phone_chat_available() is False
    ctx.store.close()


def test_no_eligibility_or_an_unsupported_read_opens_neither_member(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _phone_modules(monkeypatch)
    _adapter, ctx = _open(adapter_module, monkeypatch, tmp_path / "none", None)
    assert ctx.is_approvals_available() is False and ctx.is_phone_chat_available() is False
    ctx.store.close()
    _adapter, ctx = _open(
        adapter_module, monkeypatch, tmp_path / "unsupported", _eligibility(), supported=False
    )
    assert ctx.bridge is None and ctx.prompt_store is None
    assert ctx.is_approvals_available() is False and ctx.is_phone_chat_available() is False
    ctx.store.close()


def test_phone_chat_stays_closed_when_its_helpers_cannot_be_bound(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "tools.approval", None)  # eligibility said yes; imports fail
    _adapter, ctx = _open(adapter_module, monkeypatch, tmp_path, _eligibility())
    assert ctx.is_phone_chat_available() is False
    assert ctx.is_approvals_available() is True
    ctx.store.close()


def test_the_producer_hooks_follow_phone_chat_availability(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _phone_modules(monkeypatch)
    adapter, ctx = _open(adapter_module, monkeypatch, tmp_path, _eligibility())
    assert adapter._hmp_hooks.phone_available() is True
    ctx.prompt_store.close_phone_chat(ctx.now())
    assert adapter._hmp_hooks.phone_available() is False
    ctx.store.close()


# --------------------------------------------------------------------------------------------
# Binding fence (R10, D6, N22)
# --------------------------------------------------------------------------------------------


def _seed_rows(ctx: Any) -> tuple[PromptRow, PromptRow]:
    bot = PromptRow(
        iid=ctx.iid, user_id=USER, profile=PROFILE, request_id=REQ, kind="approval",
        surface="bot_chat", choices=("once", "deny"), run_id=RUN, observed_at=1,
    )
    phone = PromptRow(
        iid=ctx.iid, user_id=USER, profile=PROFILE, request_id=REQ + "p", kind="approval",
        surface="phone_chat", choices=("once", "deny"), session_key="sess", observed_at=1,
    )
    ctx.prompt_store.put(bot)
    ctx.prompt_store.put(phone)
    return bot, phone


def test_n22_a_rebound_helper_closes_the_local_phone_generation_only(
    adapter_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    modules = _phone_modules(monkeypatch)
    _adapter, ctx = _open(adapter_module, monkeypatch, tmp_path, _eligibility())
    bot, phone = _seed_rows(ctx)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    modules["approval"].list_gateway_approvals = lambda key: []  # rebound after listener open
    with pytest.raises(prompts.HelperChangedError):
        ctx.bridge.list_gateway_approvals("sess")

    assert ctx.prompt_store.phone_closed is True
    assert ctx.is_phone_chat_available() is False  # closed until the next listener open
    assert ctx.is_approvals_available() is True  # Bot Chat eligibility is independent
    assert phone.status == "expired" and bot.status == "open"
    # Local invalidation only: nothing says Hermes's request ended, and nothing was stored as a
    # native stale answer.
    assert phone.stored_status is None and phone.stored_body is None
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "event=approval_binding outcome=changed" in messages
    # Phone rows cannot come back into this generation, and its sessions are forgotten.
    ctx.prompt_store.put(
        PromptRow(iid=ctx.iid, user_id=USER, profile=PROFILE, request_id="again", kind="approval",
                  surface="phone_chat", choices=("once",), session_key="sess")
    )
    assert ctx.prompt_store.get((ctx.iid, USER, PROFILE, "again")) is None
    ctx.prompt_store.remember_session("sess", ctx.iid, USER, PROFILE, "chat")
    assert ctx.prompt_store.owner_of_session("sess") is None
    ctx.store.close()


def test_n22_the_closed_generation_answers_phone_rows_as_unavailable_not_expired(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A request already in flight when the rebinding is noticed reports `api_server_unavailable`
    (no `applied`), never an authoritative `409 stale`."""
    import asyncio

    from hmp_plugin import server

    modules = _phone_modules(monkeypatch)
    _adapter, ctx = _open(adapter_module, monkeypatch, tmp_path, _eligibility())
    _bot, phone = _seed_rows(ctx)
    modules["approval"].resolve_gateway_approval = lambda *a, **k: 1  # rebound
    resolver = server._LivePromptResolver(ctx, None)
    verdict = asyncio.run(resolver.resolve_approval(phone, "once"))
    assert verdict == "unavailable"
    assert phone.status == "expired"  # the closure expired HMP's own row locally
    ctx.store.close()


# --------------------------------------------------------------------------------------------
# Listener generations and process restarts (R9, N20, N21)
# --------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_n20_a_stream_bound_to_an_older_generation_cannot_reach_a_newer_one(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _phone_modules(monkeypatch)
    _adapter, ctx1 = _open(adapter_module, monkeypatch, tmp_path / "g1", _eligibility())
    old_store = ctx1.prompt_store
    bind = direct_send.StreamBind(
        store=old_store, iid=ctx1.iid, user_id=USER, profile=PROFILE, now=ctx1.now, timeout_s=300
    )

    # Listener reconnect: generation 1 stops, generation 2 opens in the same process.
    adapter_module.HmpAdapter._close_generation(ctx1)
    _adapter2, ctx2 = _open(adapter_module, monkeypatch, tmp_path / "g2", _eligibility())
    new_store = ctx2.prompt_store
    assert new_store is not old_store and old_store.closed and not new_store.closed

    async def parts():
        yield _frame("run.started", {"run_id": RUN})
        yield _frame(
            "approval.request",
            {"run_id": RUN, "request_id": REQ, "command": "rm -rf /x", "choices": ["once", "deny"]},
        )
        yield _frame("assistant.completed", {"content": "ok", "session_id": "s1"})
        yield _frame("run.completed", {"run_id": RUN})
        yield _frame("done", {})

    await direct_send.consume_sse(parts(), bind=bind)
    for store in (old_store, new_store):
        assert store.get((ctx1.iid, USER, PROFILE, REQ)) is None
        assert store.get((ctx2.iid, USER, PROFILE, REQ)) is None
        assert store.list_visible(ctx2.iid, USER, PROFILE) == ()
    assert ctx1.is_approvals_available() is False  # the old context answers nothing either
    ctx1.store.close()
    ctx2.store.close()


def test_n20_rows_of_an_older_generation_are_never_listed_or_answerable(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import asyncio

    _phone_modules(monkeypatch)
    _adapter, ctx1 = _open(adapter_module, monkeypatch, tmp_path / "g1", _eligibility())
    _seed_rows(ctx1)
    assert len(ctx1.prompt_store.list_visible(ctx1.iid, USER, PROFILE)) == 2
    adapter_module.HmpAdapter._close_generation(ctx1)
    assert ctx1.prompt_store.list_visible(ctx1.iid, USER, PROFILE) == ()
    resolver = FakeResolver()
    result = asyncio.run(_answer(ctx1.prompt_store, resolver, {"choice": "once"}, iid=ctx1.iid))
    assert result.status == 409 and result.body["applied"] is False  # expired locally
    assert resolver.calls == []
    ctx1.store.close()


def test_n21_a_process_restart_drops_every_row_and_nothing_can_be_applied() -> None:
    """Rows are process memory: a restart builds a fresh store (Hermes's own waits die with the
    same gateway process). The old request id is unknown and no Hermes call is made."""
    import asyncio

    before = PromptStore(clock=lambda: 1)
    before.put(
        PromptRow(iid=IID, user_id=USER, profile=PROFILE, request_id=REQ, kind="approval",
                  surface="bot_chat", choices=("once",), run_id=RUN)
    )
    after = PromptStore(clock=lambda: 2)  # the restarted process
    resolver = FakeResolver()
    result = asyncio.run(_answer(after, resolver, {"choice": "once"}))
    assert result.status == 404 and result.body["error"]["code"] == "not_found"
    assert resolver.calls == [] and not after._rows


def test_closing_a_generation_is_idempotent_and_expires_every_row() -> None:
    store = PromptStore(clock=lambda: 1)
    row = PromptRow(iid=IID, user_id=USER, profile=PROFILE, request_id=REQ, kind="approval",
                    surface="bot_chat", choices=("once",), run_id=RUN)
    store.put(row)
    store.close(5)
    store.close(6)
    assert row.status == "expired" and row.settled_at == 5
    store.put(
        PromptRow(iid=IID, user_id=USER, profile=PROFILE, request_id="x", kind="approval",
                  surface="bot_chat", choices=("once",), run_id=RUN)
    )
    assert store.get((IID, USER, PROFILE, "x")) is None


def test_the_disconnect_path_closes_the_generation(
    adapter_module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import asyncio

    _phone_modules(monkeypatch)
    _adapter, ctx = _open(adapter_module, monkeypatch, tmp_path, _eligibility())
    hmp = adapter_module.HmpAdapter(types.SimpleNamespace(extra={}))
    stopped: list[bool] = []

    class Srv:
        def __init__(self) -> None:
            self.ctx = ctx

        async def stop(self, *, notify: bool) -> None:
            stopped.append(notify)

    hmp._server = Srv()
    asyncio.run(hmp.disconnect())
    assert stopped == [False] and ctx.prompt_store.closed is True

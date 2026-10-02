"""Spec 015 T040 (I-6): the shared visibility seam and AP-3 equivalence.

Three layers:

1. A frozen oracle. `handle_prompts_list`, `PromptStore.list_visible` and `list_prompts` below are
   copied verbatim from the git object `150bd0f` (`git show 150bd0f:server/hmp_plugin/...`). The
   differential grid runs the oracle and the new route over identical state at the real aiohttp
   route (bearer middleware, gates, limiter) with a scripted clock, and compares status, serialized
   body bytes, the `ctx.now()` sample count, every Hermes-facing call, the resulting store state and
   the non-diagnostic log lines. The one permitted difference is the multiplicity of
   `bridge_exception` diagnostic lines when an injected member callable raises (NI-6.5).
2. Route-level pins for the exact clock and call sequence of plan section 2.4.
3. Store-level pins for the pure predicate, `view_row`, `view_visible`, the retention mask, aliasing
   and `include_wire` exposure, and the legacy live-row APIs.

No threads, sleeps or timers: every lock probe is a non-blocking acquire that fails the test
cleanly. Nothing here imports Hermes.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import json
import logging
import re
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient

from hmp_plugin import prompts as real_prompts
from hmp_plugin import server
from hmp_plugin.bridge import BridgeError
from hmp_plugin.contract import (
    IDEMPOTENCY_RETENTION_S,
    RATE_PROMPT_READ_PER_MIN_PER_DEVICE,
    ErrorCode,
    HmpError,
)
from hmp_plugin.logging_policy import LOGGER_NAME, log_event
from hmp_plugin.prompts import (
    ALL_OPEN,
    EXPIRY_GRACE_S,
    HelperUnavailableError,
    HttpResult,
    MemberState,
    PromptRow,
    PromptStore,
    RowView,
    VisibleSet,
    wire_prompt,
)
from hmp_plugin.request_ctx import ServerContext
from hmp_plugin.server import (
    _prompt_result,
    _require,
    _require_approvals_gate,
    bearer,
    context,
    json_response,
    require_bot_authorized,
)

from .hmp_kit import T0, Device, Env, pair, run, url
from .test_approvals import RUN, _arm

BOT = "b"
OTHER_BOT = "other-bot"
OTHER_USER = "hmpu_" + "ee" * 16
RET = IDEMPOTENCY_RETENTION_S
# The default (unscripted) grid clock offsets.
KEY = ("iid_" + "a" * 48, "hmpu_" + "ab" * 16, "default", "req_" + "12" * 16)


# ============================================================================================
# 1. The frozen 150bd0f oracle (verbatim from the git object)
# ============================================================================================

# --- 150bd0f: server/hmp_plugin/prompts.py, `PromptStore.list_visible` (as a method) -----------
class _OracleStore:
    """Delegates everything to the real store except `list_visible`, which is the 150bd0f body."""

    def __init__(self, real: PromptStore) -> None:
        self._real = real

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)

    def list_visible(
        self, iid: str, user_id: str, profile: str, *, now: int | None = None
    ) -> tuple[PromptRow, ...]:
        self.purge(int(self._clock()) if now is None else now)
        held = self.desktop_held(iid, user_id, profile)
        with self._guard:
            rows = [
                row
                for row in self._rows.values()
                if row.status == "open"
                and (row.iid, row.user_id, row.profile) == (iid, user_id, profile)
            ]
        if held:
            rows = [row for row in rows if row.surface != "bot_chat"]
        return tuple(rows)



# --- 150bd0f: server/hmp_plugin/prompts.py, `list_prompts` -----------------------------------
def list_prompts(
    store: PromptStore, *, iid: str, user_id: str, profile: str, now: int
) -> HttpResult:
    store.purge(now)
    rows = store.list_visible(iid, user_id, profile, now=now)
    return HttpResult(
        200,
        {
            "prompts": [wire_prompt(row) for row in rows],
            "desktop_held": store.desktop_held(iid, user_id, profile),
        },
    )

# The oracle handler reaches `prompts` as a module global; give it the 150bd0f surface it used.
prompts = types.SimpleNamespace(
    HelperUnavailableError=HelperUnavailableError,
    HttpResult=HttpResult,
    list_prompts=list_prompts,
)


# --- 150bd0f: server/hmp_plugin/server.py, `handle_prompts_list` ------------------------------
async def handle_prompts_list(request: web.Request) -> web.Response:
    """AP-3: `GET /bots/{p}/prompts`."""
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    if not ctx.is_approval_owner_device(who.device_id):
        raise HmpError(ErrorCode.NOT_FOUND)
    ctx.limiter.check(
        "prompt_reads", who.device_id, RATE_PROMPT_READ_PER_MIN_PER_DEVICE, ctx.now()
    )
    await asyncio.to_thread(require_bot_authorized, _require(ctx.bridge), who.user_id, profile)
    await _require_approvals_gate(ctx, profile, member=None)
    store = ctx.prompt_store
    if store is None:
        return json_response({"prompts": [], "desktop_held": False})
    rows = store.list_visible(ctx.iid, who.user_id, profile, now=ctx.now())
    sessions = {
        row.session_key
        for row in rows
        if row.kind == "approval" and row.session_key and row.surface == "phone_chat"
    }
    if sessions and ctx.is_phone_chat_available():
        for session_key in sessions:
            try:
                pending = await asyncio.to_thread(ctx.bridge.list_gateway_approvals, session_key)
            except prompts.HelperUnavailableError:
                # Unavailable is not proof the waiter is gone: the row stays as it was.
                log_event("approval_helper", outcome="unavailable")
                continue
            store.reconcile_approvals(
                session_key,
                {item["request_id"] for item in pending if "request_id" in item},
                ctx.now(),
            )
    result = prompts.list_prompts(
        store, iid=ctx.iid, user_id=who.user_id, profile=profile, now=ctx.now()
    )
    # Only rows of an available member are shown. A closed member lists nothing of its own.
    shown = [
        item
        for item in result.body["prompts"]  # type: ignore[attr-defined]
        if ctx.approval_surface_available(str(item.get("surface")))
    ]
    return _prompt_result(prompts.HttpResult(200, {**result.body, "prompts": shown}))


# ============================================================================================
# The differential engine
# ============================================================================================


@dataclass(frozen=True)
class R:
    """One stored row. Times are offsets from T0."""

    rid: str
    surface: str = "bot_chat"
    kind: str = "approval"
    status: str = "open"
    expires: int | None = 300
    settled: int | None = None
    cause: str | None = None
    user: str = "me"
    profile: str = BOT
    session: str | None = None
    lock: bool = False


def B(rid: str, **kw: Any) -> R:  # noqa: N802
    return R(rid, surface="bot_chat", **kw)


def P(rid: str, **kw: Any) -> R:  # noqa: N802
    return R(rid, surface="phone_chat", **kw)


def C(rid: str, **kw: Any) -> R:  # noqa: N802
    return R(rid, surface="phone_chat", kind="clarify", **kw)


@dataclass(frozen=True)
class S:
    """One scenario. `clock` offsets are consumed in order by the handler's `ctx.now()` calls
    (limiter, `t1`, one per reconciled session, `t2`); the last value repeats."""

    rows: tuple[R, ...] = ()
    held: bool = False
    approvals: Any = True  # True / False / "raise"
    phone: Any = True
    fence: str | None = None  # "close" | "phone"
    lister: str = "keep"  # keep | omit | partial | unavailable | unavailable_first | bridge_error
    clock: tuple[int, ...] = (0, 10)
    flag: bool = True
    store: bool = True
    owner: bool = True


@dataclass
class Out:
    status: int
    body: bytes
    samples: int
    calls: dict[str, list[Any]]
    state: list[Any]
    logs: list[str]
    recon: list[tuple[str, tuple[str, ...], int]]
    purges: list[int]


class ScriptClock:
    def __init__(self, script: tuple[int, ...]) -> None:
        self.script = script
        self.armed = False
        self.samples = 0

    def __call__(self) -> int:
        if not self.armed:
            return T0
        index = self.samples
        self.samples += 1
        return T0 + self.script[min(index, len(self.script) - 1)]


class _Collect(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == LOGGER_NAME:  # not the access logger: it carries a wall-clock duration
            self.lines.append(record.getMessage())


def _raiser(_tag: str) -> Callable[[], bool]:
    def boom() -> bool:
        raise RuntimeError("member read failed")

    return boom


def _user_of(env: Env, dev: Device) -> str:
    row = (
        env.store._require_conn()
        .execute("SELECT user_id FROM devices WHERE device_id = ?", (dev.device_id,))
        .fetchone()
    )
    return str(row["user_id"])


def _make(env: Env, user_id: str, r: R) -> PromptRow:
    phone = r.surface == "phone_chat"
    approval = r.kind == "approval"
    return PromptRow(
        iid=env.iid,
        user_id=user_id if r.user == "me" else OTHER_USER,
        profile=r.profile,
        request_id=r.rid,
        kind=r.kind,
        surface=r.surface,
        choices=("once", "deny") if approval else ("Ship", "Wait"),
        command="rm -rf /x" if approval else None,
        description="d" if approval else None,
        question=None if approval else "Ship?",
        run_id=None if phone else RUN,
        session_key=(r.session or "sess-phone") if phone else None,
        observed_at=T0,
        expires_at=None if r.expires is None else T0 + r.expires,
    )


def _populate(env: Env, user_id: str, s: S) -> None:
    store = env.ctx.prompt_store
    for r in s.rows:
        row = _make(env, user_id, r)
        store.put(row)
        if r.status != "open":
            row.status = r.status
            row.settled_at = T0 + (r.settled or 0)
            row.settle_cause = r.cause
        if r.lock:
            store._lock_users[(row.iid, row.user_id, row.profile, row.request_id)] = 1
    if s.held:
        store.set_desktop_held(env.iid, user_id, BOT)
    if s.fence == "close":
        store.close(T0)
    elif s.fence == "phone":
        store.close_phone_chat(T0)


def _drive(
    tmp: Path,
    s: S,
    *,
    oracle: bool,
    pre: Callable[[Env, PromptStore], None] | None = None,
) -> Out:
    tmp.mkdir(parents=True, exist_ok=True)
    env = Env(tmp)
    _arm(env, flag=s.flag)
    real_store = PromptStore(clock=lambda: T0)
    calls: dict[str, list[Any]] = {"endpoint": [], "list": []}
    clock = ScriptClock(s.clock)
    out: dict[str, Any] = {}
    original_endpoint = env.bridge.direct_send_endpoint

    def endpoint(*args: Any, **kwargs: Any) -> Any:
        calls["endpoint"].append(args)
        return original_endpoint(*args, **kwargs)

    env.bridge.direct_send_endpoint = endpoint  # type: ignore[method-assign]

    def lister(session_key: str) -> Any:
        calls["list"].append(session_key)
        if s.lister == "bridge_error":
            raise BridgeError()
        if s.lister == "unavailable" or (
            s.lister == "unavailable_first" and len(calls["list"]) == 1
        ):
            raise HelperUnavailableError("fixed")
        if s.lister == "omit":
            return []
        ids = [
            {"request_id": row.request_id}
            for row in real_store._rows.values()
            if row.kind == "approval" and row.session_key == session_key
        ]
        return ids[:1] if s.lister == "partial" else ids

    env.bridge.list_gateway_approvals = lister  # type: ignore[method-assign]
    env.ctx.prompt_store = real_store if not oracle else _OracleStore(real_store)  # type: ignore[assignment]
    if not s.store:
        env.ctx.prompt_store = None
    env.ctx.clock = clock  # type: ignore[assignment]
    env.ctx.approvals_available = _raiser("a") if s.approvals == "raise" else (lambda: s.approvals)
    env.ctx.phone_chat_available = _raiser("p") if s.phone == "raise" else (lambda: s.phone)

    recon: list[tuple[str, tuple[str, ...], int]] = []
    purges: list[int] = []
    original_reconcile = real_store.reconcile_approvals
    original_purge = real_store.purge

    def reconcile(session_key: str, pending: set[str], now: int) -> None:
        recon.append((session_key, tuple(sorted(pending)), now))
        original_reconcile(session_key, pending, now)

    def purge(now: int) -> None:
        purges.append(now)
        original_purge(now)

    real_store.reconcile_approvals = reconcile  # type: ignore[method-assign]
    real_store.purge = purge  # type: ignore[method-assign]
    handler = _Collect()
    logger = logging.getLogger(LOGGER_NAME)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = (
            (lambda: frozenset({dev.device_id})) if s.owner else (lambda: frozenset())
        )
        _populate(env, _user_of(env, dev), s)
        if pre is not None:
            pre(env, real_store)
        original_owner = env.ctx.is_approval_owner_device

        def arming(device_id: str) -> bool:
            clock.armed = True
            return original_owner(device_id)

        env.ctx.is_approval_owner_device = arming  # type: ignore[method-assign]
        recon.clear()
        purges.clear()
        calls["endpoint"].clear()
        calls["list"].clear()
        previous = logger.level
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            resp = await client.get(url(f"/bots/{BOT}/prompts"), headers=env.headers(dev))
            out["status"], out["body"] = resp.status, await resp.read()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous)

    saved = server.handle_prompts_list
    if oracle:
        server.handle_prompts_list = handle_prompts_list  # type: ignore[assignment]
    try:
        run(env, scenario)
    finally:
        server.handle_prompts_list = saved  # type: ignore[assignment]
    state = [
        (key[3], row.status, row.settled_at, row.settle_cause)
        for key, row in real_store._rows.items()
    ]
    return Out(
        status=out["status"],
        body=out["body"],
        samples=clock.samples,
        calls={**calls, "spy": list(env.bridge.calls)},
        state=[*state, ("held", len(real_store._desktop))],
        logs=handler.lines,
        recon=list(recon),
        purges=list(purges),
    )


def _without_diagnostics(lines: list[str]) -> list[str]:
    """Drop `bridge_exception` lines (NI-6.5) and the source-frame labels of `handler_error`, which
    name where the exception passed (the oracle lives in this module; the route in `server.py`)."""
    return [
        re.sub(r" at=\S+ last=\S+", "", line)
        for line in lines
        if "event=bridge_exception" not in line
    ]


def _both(tmp_path: Path, s: S) -> tuple[Out, Out]:
    new = _drive(tmp_path / "new", s, oracle=False)
    old = _drive(tmp_path / "old", s, oracle=True)
    assert new.status == old.status
    assert new.body == old.body  # serialized bytes, never dict equality
    assert new.samples == old.samples
    assert new.calls == old.calls
    assert new.recon == old.recon
    assert new.state == old.state
    assert _without_diagnostics(new.logs) == _without_diagnostics(old.logs)
    return new, old


def _ids(out: Out) -> list[str]:
    return [item["request_id"] for item in json.loads(out.body)["prompts"]]


def _held(out: Out) -> bool:
    return bool(json.loads(out.body)["desktop_held"])


# --------------------------------------------------------------------------------------------
# The NI-6.5 grid, at the real route, against the 150bd0f oracle
# --------------------------------------------------------------------------------------------

MIXED = (
    B("a1"),
    P("b1", session="s1"),
    C("c1", session="s1"),
    B("d1"),
    P("e1", session="s2"),
    C("f1", session="s2"),
)


def test_oracle_matches_a_frozen_expected_body(tmp_path: Path) -> None:
    """Pins the harness itself: the oracle and the new route both list this exact order."""
    new, old = _both(tmp_path, S(rows=MIXED, clock=(0, 10, 11, 12, 13)))
    assert (new.status, _ids(new)) == (200, ["a1", "b1", "c1", "d1", "e1", "f1"])
    assert old.samples == 5  # limiter, t1, two sessions, t2
    assert not _held(new)


def test_empty_store(tmp_path: Path) -> None:
    new, _ = _both(tmp_path, S())
    assert json.loads(new.body) == {"prompts": [], "desktop_held": False}
    assert new.samples == 3  # limiter, t1, t2


def test_body_key_order_and_serialization(tmp_path: Path) -> None:
    new, _ = _both(tmp_path, S(rows=(B("a1"), C("c1", session="s1"))))
    parsed = json.loads(new.body)
    assert list(parsed) == ["prompts", "desktop_held"]
    assert [list(item) for item in parsed["prompts"]] == [
        ["kind", "surface", "request_id", "expires_at", "choices", "command", "description"],
        ["kind", "surface", "request_id", "expires_at", "question", "multi_select",
         "awaiting_text", "choices"],
    ]


def test_mixed_status_rows_list_only_open_rows_in_insertion_order(tmp_path: Path) -> None:
    rows = (
        B("a1", status="resolved", settled=0),
        B("b1"),
        P("c1", status="expired", settled=0, session="s1"),
        P("d1", session="s1"),
        C("e1", session="s1"),
        B("f1", status="expired", settled=0),
    )
    new, _ = _both(tmp_path, S(rows=rows, clock=(0, 10, 11, 12)))
    assert _ids(new) == ["b1", "d1", "e1"]


@pytest.mark.parametrize("t1", [30, 31])
@pytest.mark.parametrize("t2", [30, 31])
def test_expiry_grace_boundary_at_both_phases(tmp_path: Path, t1: int, t2: int) -> None:
    rows = (B("a1", expires=100), P("b1", expires=100, session="s1"))
    script = (0, 100 + t1) + ((100 + t1,) if t1 == 30 else ()) + (100 + t2,)
    new, _ = _both(tmp_path, S(rows=rows, clock=script))
    listed = _ids(new)
    if t1 == 31 or t2 == 31:
        assert listed == []
    else:
        assert listed == ["a1", "b1"]  # `expires_at + 30` is listed; `+ 31` is not


def test_grace_boundary_exact_values_for_route(tmp_path: Path) -> None:
    for offset, expect in ((EXPIRY_GRACE_S, ["a1"]), (EXPIRY_GRACE_S + 1, [])):
        new, _ = _both(
            tmp_path / str(offset), S(rows=(B("a1", expires=100),), clock=(0, 100 + offset))
        )
        assert _ids(new) == expect


def test_null_expiry_never_expires_locally(tmp_path: Path) -> None:
    rows = (B("a1", expires=None), P("b1", expires=None, session="s1"))
    new, _ = _both(tmp_path, S(rows=rows, clock=(0, 5 * RET)))
    assert _ids(new) == ["a1", "b1"]


def test_desktop_held_hides_bot_chat_and_keeps_phone(tmp_path: Path) -> None:
    rows = (B("a1"), P("b1", session="s1"), C("c1", session="s1"), B("d1"))
    new, _ = _both(tmp_path, S(rows=rows, held=True, clock=(0, 10, 11, 12)))
    assert _ids(new) == ["b1", "c1"] and _held(new)


@pytest.mark.parametrize("approvals", [True, False])
@pytest.mark.parametrize("phone", [True, False])
def test_each_member_state(tmp_path: Path, approvals: bool, phone: bool) -> None:
    rows = (B("a1"), P("b1", session="s1"), C("c1", session="s1"), B("d1"))
    new, _ = _both(
        tmp_path, S(rows=rows, approvals=approvals, phone=phone, clock=(0, 10, 11, 12))
    )
    expected = (["a1", "d1"] if approvals else []) + (["b1", "c1"] if phone else [])
    if not approvals and not phone:
        assert new.status == 503  # the surface gate closes before the seam
    else:
        assert sorted(_ids(new)) == sorted(expected)
        if approvals and phone:
            assert _ids(new) == ["a1", "b1", "c1", "d1"]  # insertion order, not grouped


@pytest.mark.parametrize("fence", ["close", "phone"])
def test_closed_and_phone_closed_generations(tmp_path: Path, fence: str) -> None:
    rows = (B("a1"), P("b1", session="s1"), C("c1", session="s1"))
    new, _ = _both(tmp_path, S(rows=rows, fence=fence))
    if fence == "close":
        assert new.status == 503  # both members closed with the generation
    else:
        assert _ids(new) == ["a1"]


def test_other_users_and_profiles_are_not_listed(tmp_path: Path) -> None:
    rows = (
        B("a1"),
        B("b1", user="other"),
        B("c1", profile=OTHER_BOT),
        P("d1", user="other", session="s9"),
        P("e1", session="s1"),
    )
    new, _ = _both(tmp_path, S(rows=rows, clock=(0, 10, 11, 12)))
    assert _ids(new) == ["a1", "e1"]


@pytest.mark.parametrize(
    "lister", ["keep", "omit", "partial", "unavailable", "unavailable_first"]
)
def test_phone_reconciliation_omit_keep_and_unavailable(tmp_path: Path, lister: str) -> None:
    rows = (B("a1"), P("b1", session="s1"), P("b2", session="s1"), P("c1", session="s2"))
    new, _ = _both(tmp_path, S(rows=rows, lister=lister, clock=(0, 10, 11, 12, 13)))
    listed = _ids(new)
    if lister in {"keep", "unavailable", "unavailable_first"}:
        assert listed[0] == "a1" and "b1" in listed
    if lister == "omit":
        assert listed == ["a1"]
    if lister == "partial":
        assert "b2" not in listed  # only the first request per session survives
    assert len(new.calls["list"]) == 2  # one listing per distinct session


def test_a_bridge_error_from_a_non_list_listing_still_propagates(tmp_path: Path) -> None:
    rows = (P("b1", session="s1"), P("c1", session="s2"))
    new, old = _both(tmp_path, S(rows=rows, lister="bridge_error"))
    assert new.status == old.status and new.status != 200
    assert len(new.calls["list"]) == 1  # the loop did not continue past the failure
    assert all(row[1] == "open" for row in new.state if row[0] != "held")
    assert new.recon == []


def test_helper_unavailable_keeps_the_row_and_logs_the_fixed_outcome(tmp_path: Path) -> None:
    rows = (P("b1", session="s1"), P("c1", session="s2"))
    new, _ = _both(tmp_path, S(rows=rows, lister="unavailable", clock=(0, 10, 11, 12)))
    assert _ids(new) == ["b1", "c1"] and new.recon == []
    assert new.logs.count("event=approval_helper outcome=unavailable") == 2


def test_helper_unavailable_for_the_first_session_still_reconciles_the_second(
    tmp_path: Path,
) -> None:
    rows = (P("b1", session="s1"), P("c1", session="s2"))
    new, _ = _both(tmp_path, S(rows=rows, lister="unavailable_first", clock=(0, 10, 20, 30)))
    assert len(new.recon) == 1 and new.recon[0][2] == T0 + 20  # its own fresh sample


@pytest.mark.parametrize(
    ("approvals", "phone"), [("raise", True), (True, "raise"), ("raise", "raise")]
)
def test_a_raising_member_callable_fails_closed_with_the_same_body(
    tmp_path: Path, approvals: Any, phone: Any
) -> None:
    rows = (B("a1"), P("b1", session="s1"), B("c1"))
    new, old = _both(tmp_path, S(rows=rows, approvals=approvals, phone=phone, clock=(0, 10, 11)))
    # Only the number of `bridge_exception` diagnostics may differ; the body does not.
    assert new.body == old.body
    raised = len([x for x in (approvals, phone) if x == "raise"])
    # The seam asks each member once per request.
    assert (
        len([x for x in new.logs if "event=bridge_exception" in x])
        <= len([x for x in old.logs if "event=bridge_exception" in x]) + raised
    )
    if approvals == "raise" and phone == "raise":
        assert new.status == 503
    elif approvals == "raise":
        assert _ids(new) == ["b1"]
    else:
        assert _ids(new) == ["a1", "c1"]


def test_raising_member_diagnostic_multiplicity_is_per_member_not_per_item(
    tmp_path: Path,
) -> None:
    rows = (B("a1"), B("b1"), B("c1"))
    new, old = _both(tmp_path, S(rows=rows, phone="raise"))
    new_diag = [x for x in new.logs if "event=bridge_exception" in x]
    old_diag = [x for x in old.logs if "event=bridge_exception" in x]
    # Gate (member=None) asks both members; then the seam asks each member once.
    # `150bd0f` asked the member once per listed item (three, but only after the surface check
    # let a row through); the seam asks once per member per request. Neither may change the body.
    assert len(new_diag) >= 1 and len(old_diag) <= 3
    assert _ids(new) == ["a1", "b1", "c1"]


def test_retention_boundary_deletes_exactly_as_the_oracle_does(tmp_path: Path) -> None:
    rows = (
        B("a1", status="resolved", settled=-RET),  # now - settled_at == RET: deleted
        B("b1", status="resolved", settled=-RET + 1),  # one second short: kept (not listed)
        B("c1", status="expired", settled=-RET, lock=True),  # active lock: kept
        B("d1"),
    )
    new, _ = _both(tmp_path, S(rows=rows, clock=(0, 0)))
    kept = [row[0] for row in new.state if row[0] != "held"]
    assert kept == ["b1", "c1", "d1"] and _ids(new) == ["d1"]


def test_first_phase_purge_expires_rows_and_second_phase_runs_again(tmp_path: Path) -> None:
    rows = (B("a1", expires=100), B("b1", expires=500))
    new, _ = _both(tmp_path, S(rows=rows, clock=(0, 100 + 31, 500 + 31)))
    assert _ids(new) == []
    assert [(row[1], row[2], row[3]) for row in new.state if row[0] != "held"] == [
        ("expired", T0 + 131, "local_expiry"),
        ("expired", T0 + 531, "local_expiry"),
    ]


@pytest.mark.parametrize(
    "s",
    [
        S(flag=False, rows=(B("a1"),)),
        S(owner=False, rows=(B("a1"),)),
        S(store=False),
        S(approvals=False, phone=False, rows=(B("a1"),)),
    ],
    ids=["flag_off", "non_owner", "no_store", "both_members_closed"],
)
def test_gate_order_and_early_returns(tmp_path: Path, s: S) -> None:
    new, _ = _both(tmp_path, s)
    if s.store is False:
        assert (new.status, json.loads(new.body)) == (200, {"prompts": [], "desktop_held": False})
        assert new.samples == 1  # only the limiter sampled the clock
    else:
        assert new.status in (404, 503)
        assert new.samples <= 1 and new.calls["list"] == []


def test_the_gate_runs_before_the_seam(tmp_path: Path) -> None:
    new, _ = _both(tmp_path, S(approvals=False, phone=False, rows=(B("a1"),)))
    assert new.status == 503 and new.purges == []  # nothing purged, no view built


# --------------------------------------------------------------------------------------------
# 2. The exact clock and call sequence at the route (plan 2.4)
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("flip", ["hold", "release"])
def test_desktop_held_flipped_during_reconciliation_comes_from_the_final_snapshot(
    tmp_path: Path, flip: str
) -> None:
    """The Desktop-held marker changes while the awaited Phone listing runs. `desktop_held` and the
    Bot Chat rows must both come from the final snapshot, not from the reconcile candidates."""
    holds = flip == "hold"

    def flipper(env: Env, store: PromptStore) -> None:
        user_id = next(iter(store._rows.values())).user_id
        original = env.bridge.list_gateway_approvals

        def lister(session_key: str) -> Any:
            change = store.set_desktop_held if holds else store.clear_desktop_held
            change(env.iid, user_id, BOT)  # runs on the listing's worker thread
            return original(session_key)

        env.bridge.list_gateway_approvals = lister  # type: ignore[method-assign]

    s = S(rows=(B("a1"), P("b1", session="s1")), held=not holds, clock=(0, 10, 11, 12))
    new = _drive(tmp_path / "new", s, oracle=False, pre=flipper)
    old = _drive(tmp_path / "old", s, oracle=True, pre=flipper)
    assert new.calls["list"] == ["s1"] and new.state[-1] == ("held", 1 if holds else 0)
    assert (_held(new), _ids(new)) == ((True, ["b1"]) if holds else (False, ["a1", "b1"]))
    assert _held(new) == ("a1" not in _ids(new))  # one snapshot: the flag matches the rows
    assert new.body == old.body


def test_clock_sequence_purge_once_per_phase_and_fresh_reconcile_samples(tmp_path: Path) -> None:
    rows = (B("a1"), P("b1", session="s1"), P("c1", session="s2"))
    new = _drive(tmp_path, S(rows=rows, lister="omit", clock=(0, 10, 20, 30, 40)), oracle=False)
    t = lambda n: T0 + n  # noqa: E731
    assert new.samples == 5  # limiter, t1, one per reconciled session, t2
    assert new.purges == [t(10), t(40)]  # one purge per phase, at t1 and t2
    assert [r[2] for r in new.recon] == [t(20), t(30)]  # each call samples the clock afresh
    assert {r[0] for r in new.recon} == {"s1", "s2"}  # (set order is not part of the contract)
    at = {session: now for session, _pending, now in new.recon}
    assert {row[0]: (row[1], row[2], row[3]) for row in new.state if row[0] != "held"} == {
        "a1": ("open", None, None),
        "b1": ("expired", at["s1"], "phone_listing_omitted"),
        "c1": ("expired", at["s2"], "phone_listing_omitted"),
    }
    assert _ids(new) == ["a1"]


def test_view_visible_calls_use_t1_all_open_then_t2_fresh_members(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []

    def watch(env: Env, store: PromptStore) -> None:
        original = store.view_visible

        def spy(*args: Any, **kwargs: Any) -> VisibleSet:
            seen.append(dict(kwargs))
            return original(*args, **kwargs)

        store.view_visible = spy  # type: ignore[method-assign]

    rows = (B("a1"), P("b1", session="s1"))
    _drive(
        tmp_path,
        S(rows=rows, approvals=True, phone=False, clock=(0, 10, 11, 12)),
        oracle=False,
        pre=watch,
    )
    assert len(seen) == 2
    assert seen[0]["now"] == T0 + 10 and seen[0]["members"] == ALL_OPEN
    assert seen[1]["now"] == T0 + 11 and seen[1]["members"] == MemberState(True, False)
    assert seen[0]["include_wire"] is True and seen[1]["include_wire"] is True


def test_members_are_evaluated_once_each_outside_guard_after_reconciliation(
    tmp_path: Path,
) -> None:
    probes: list[tuple[str, bool]] = []
    order: list[str] = []

    def hook(env: Env, store: PromptStore) -> None:
        def probe(tag: str, value: bool) -> Callable[[], bool]:
            def read() -> bool:
                free = store._guard.acquire(blocking=False)  # fail cleanly, never block
                if free:
                    store._guard.release()
                probes.append((tag, free))
                order.append(tag)
                return value

            return read

        env.ctx.approvals_available = probe("approvals", True)
        env.ctx.phone_chat_available = probe("phone", True)
        original = store.reconcile_approvals

        def reconcile(*args: Any) -> None:
            order.append("reconcile")
            original(*args)

        store.reconcile_approvals = reconcile  # type: ignore[method-assign]

    new = _drive(
        tmp_path,
        S(rows=(B("a1"), P("b1", session="s1")), clock=(0, 10, 11, 12)),
        oracle=False,
        pre=hook,
    )
    assert new.status == 200 and probes and all(free for _tag, free in probes)
    # After the last reconciliation, `approval_members_now` asks the two members exactly once each.
    tail = order[order.index("reconcile") + 1 :]
    assert tail.count("approvals") == 1 and tail.count("phone") == 1


# ============================================================================================
# 3. Store-level pins
# ============================================================================================


def _row(request_id: str = "r1", surface: str = "bot_chat", **kw: Any) -> PromptRow:
    fields: dict[str, Any] = {
        "iid": KEY[0], "user_id": KEY[1], "profile": KEY[2], "request_id": request_id,
        "kind": "approval", "surface": surface, "choices": ("once", "deny"), "command": "ls",
        "description": "list", "expires_at": 1_000, "observed_at": 900,
    }
    if surface == "phone_chat":
        fields["session_key"] = "sess-1"
    else:
        fields["run_id"] = RUN
    fields.update(kw)
    return PromptRow(**fields)


def _store(*rows: PromptRow) -> PromptStore:
    def no_clock() -> float:
        raise AssertionError("a view must never sample the store clock")

    store = PromptStore(clock=no_clock)
    for row in rows:
        store.put(row)
    return store


def _key(row: PromptRow) -> tuple[str, str, str, str]:
    return (row.iid, row.user_id, row.profile, row.request_id)


def test_open_now_is_exactly_the_purge_rule() -> None:
    row = _row(expires_at=1_000)
    assert real_prompts.row_open_now(row, 1_000 + EXPIRY_GRACE_S) is True  # grace is inclusive
    assert real_prompts.row_open_now(row, 1_000 + EXPIRY_GRACE_S + 1) is False
    assert real_prompts.row_open_now(_row(expires_at=None), 10**12) is True
    assert real_prompts.row_open_now(_row(status="resolved"), 0) is False
    assert real_prompts.row_open_now(_row(status="expired"), 0) is False
    store = _store(row)
    store.purge(1_000 + EXPIRY_GRACE_S)
    assert row.status == "open"  # purge keeps what open_now keeps
    store.purge(1_000 + EXPIRY_GRACE_S + 1)
    assert row.status == "expired"  # and expires what open_now rejects


def test_hidden_now_is_computed_whatever_the_status() -> None:
    for status in ("open", "resolved", "expired"):
        bot = _row(status=status)
        phone = _row(surface="phone_chat", status=status)
        assert real_prompts.row_hidden_now(bot, True, ALL_OPEN) is True
        assert real_prompts.row_hidden_now(phone, True, ALL_OPEN) is False  # held is Bot Chat only
        assert real_prompts.row_hidden_now(bot, False, MemberState(False, True)) is True
        assert real_prompts.row_hidden_now(bot, False, MemberState(True, False)) is False
        assert real_prompts.row_hidden_now(phone, False, MemberState(True, False)) is True
        assert real_prompts.row_hidden_now(phone, False, MemberState(False, True)) is False
        assert real_prompts.row_hidden_now(bot, False, ALL_OPEN) is False


def test_view_row_returns_a_frozen_snapshot_with_every_flag() -> None:
    row = _row(settle_cause=None)
    store = _store(row)
    view = store.view_row(_key(row), now=1_000, members=ALL_OPEN)
    assert isinstance(view, RowView) and dataclasses.is_dataclass(view)
    assert (view.key, view.kind, view.surface, view.status) == (
        _key(row), "approval", "bot_chat", "open"
    )
    assert (view.generation, view.settle_cause, view.expires_at) == (store.generation, None, 1_000)
    assert (view.held, view.open_now, view.hidden_now, view.visible_now) == (
        False, True, False, True
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        view.status = "resolved"  # type: ignore[misc]
    hash(view)  # hashable: wire is excluded


def test_view_row_missing_key_is_none() -> None:
    assert _store().view_row(KEY, now=0, members=ALL_OPEN) is None


def test_view_row_never_exposes_the_session_key_or_wire() -> None:
    row = _row(surface="phone_chat")
    view = _store(row).view_row(_key(row), now=1_000, members=ALL_OPEN)
    assert view is not None and view.session_key is None and view.wire is None


def test_default_view_visible_leaves_wire_and_session_key_none() -> None:
    row = _row(surface="phone_chat")
    shown = _store(row).view_visible(KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN)
    assert [(v.session_key, v.wire) for v in shown.rows] == [(None, None)]


def test_include_wire_populates_wire_and_session_key_only_when_true() -> None:
    row = _row(surface="phone_chat")
    store = _store(row)
    shown = store.view_visible(
        KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN, include_wire=True
    )
    (view,) = shown.rows
    assert view.session_key == "sess-1"
    owned = {**view.wire, "choices": list(view.wire["choices"])}  # type: ignore[index]
    assert owned == wire_prompt(row)
    off = store.view_visible(
        KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN, include_wire=False
    )
    assert off.rows[0].wire is None and off.rows[0].session_key is None


def test_view_visible_returns_every_triple_row_in_insertion_order_with_flags() -> None:
    rows = (
        _row("a1"),
        _row("b1", surface="phone_chat", status="resolved", settled_at=5),
        _row("c1", status="expired", settled_at=5),
        _row("d1", expires_at=100),  # past grace at now=1_000
        _row("e1", surface="phone_chat"),
        _row("x1", user_id="hmpu_" + "ff" * 16),
        _row("y1", profile="other"),
    )
    store = _store(*rows)
    shown = store.view_visible(KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN)
    assert [v.key[3] for v in shown.rows] == ["a1", "b1", "c1", "d1", "e1"]
    assert [(v.status, v.open_now, v.visible_now) for v in shown.rows] == [
        ("open", True, True),
        ("resolved", False, False),
        ("expired", False, False),
        ("open", False, False),  # open in storage but past its grace now
        ("open", True, True),
    ]
    assert shown.held is False and isinstance(shown.rows, tuple)


def test_hidden_flag_is_reported_for_settled_rows_too() -> None:
    rows = (_row("a1", status="resolved", settled_at=5), _row("b1", surface="phone_chat",
                                                                status="expired", settled_at=5))
    store = _store(*rows)
    store.set_desktop_held(KEY[0], KEY[1], KEY[2])
    shown = store.view_visible(KEY[0], KEY[1], KEY[2], now=1_000, members=MemberState(True, False))
    assert shown.held is True
    assert [(v.hidden_now, v.visible_now, v.held) for v in shown.rows] == [
        (True, False, True),  # held Bot Chat
        (True, False, True),  # Phone member closed
    ]
    only = store.view_row(_key(rows[0]), now=1_000, members=ALL_OPEN)
    assert only is not None and only.hidden_now and only.held and not only.open_now


def test_held_and_rows_come_from_one_guard_section_without_callables() -> None:
    store = _store(_row("a1"))
    store.set_desktop_held(KEY[0], KEY[1], KEY[2])
    free: list[bool] = []

    def members_probe() -> MemberState:
        ok = store._guard.acquire(blocking=False)
        if ok:
            store._guard.release()
        free.append(ok)
        return ALL_OPEN

    shown = store.view_visible(
        KEY[0], KEY[1], KEY[2], now=1_000, members=members_probe()
    )
    assert free == [True] and shown.held is True and shown.rows[0].hidden_now is True


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_retention_mask_boundary(delta: int) -> None:
    row = _row(status="resolved", settled_at=500)
    store = _store(row)
    now = 500 + RET + delta
    view = store.view_row(_key(row), now=now, members=ALL_OPEN)
    shown = store.view_visible(KEY[0], KEY[1], KEY[2], now=now, members=ALL_OPEN)
    if delta >= 0:  # now - settled_at >= IDEMPOTENCY_RETENTION_S
        assert view is None and shown.rows == ()
    else:
        assert view is not None and len(shown.rows) == 1
    assert _key(row) in store._rows  # the mask never deletes


def test_retention_mask_exempts_an_active_lock_user_and_never_masks_unsettled_rows() -> None:
    locked = _row("a1", status="expired", settled_at=0)
    unsettled = _row("b1")
    store = _store(locked, unsettled)
    store._lock_users[_key(locked)] = 1
    far = 10 * RET
    assert store.view_row(_key(locked), now=far, members=ALL_OPEN) is not None
    assert store.view_row(_key(unsettled), now=far, members=ALL_OPEN) is not None
    assert [v.key[3] for v in store.view_visible(
        KEY[0], KEY[1], KEY[2], now=far, members=ALL_OPEN).rows] == ["a1", "b1"]
    del store._lock_users[_key(locked)]
    assert store.view_row(_key(locked), now=far, members=ALL_OPEN) is None
    assert store.view_row(_key(unsettled), now=far, members=ALL_OPEN) is not None


def test_retention_mask_agrees_with_what_purge_deletes() -> None:
    for settled_ago, lock in ((RET, False), (RET - 1, False), (RET, True), (10 * RET, True)):
        row = _row(status="expired", settled_at=0)
        store = _store(row)
        if lock:
            store._lock_users[_key(row)] = 1
        masked = store.view_row(_key(row), now=settled_ago, members=ALL_OPEN) is None
        store.purge(settled_ago)
        assert masked is (_key(row) not in store._rows)


def _snapshot(store: PromptStore) -> Any:
    return (
        {k: (id(r), dataclasses.astuple(r)) for k, r in store._rows.items()},
        list(store._rows),
        dict(store._locks),
        dict(store._lock_users),
        set(store._desktop),
        dict(store._sessions),
        dict(store._observations),
        (store.closed, store.phone_closed),
    )


def test_the_seam_mutates_nothing() -> None:
    rows = (
        _row("a1", expires_at=100),  # past grace: purge would expire it
        _row("b1", status="resolved", settled_at=0),  # retention-masked: purge would delete it
        _row("c1", surface="phone_chat"),
        _row("d1", status="expired", settled_at=0),
    )
    store = _store(*rows)
    store._locks[_key(rows[1])] = asyncio.Lock()
    before = _snapshot(store)
    now = RET + 5
    for members in (ALL_OPEN, MemberState(False, False)):
        for include_wire in (False, True):
            store.view_visible(
                KEY[0], KEY[1], KEY[2], now=now, members=members, include_wire=include_wire
            )
        for row in rows:
            store.view_row(_key(row), now=now, members=members)
    assert _snapshot(store) == before
    assert rows[0].status == "open" and rows[0].settle_cause is None  # never expired by a view


def test_views_do_not_alias_the_live_row() -> None:
    row = _row(surface="phone_chat", kind="clarify", choices=("Ship", "Wait"), question="Q?",
               command=None, description=None, awaiting_text=False, multi_select=False)
    store = _store(row)
    (view,) = store.view_visible(
        KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN, include_wire=True
    ).rows
    frozen = (view, dict(view.wire), view.status, view.settle_cause)
    row.awaiting_text = True
    row.status = "resolved"
    row.settle_cause = "answer_applied"
    row.choices = ("changed",)
    row.question = "changed"
    assert (view, dict(view.wire), view.status, view.settle_cause) == frozen
    assert view.wire["awaiting_text"] is False and view.wire["choices"] == ("Ship", "Wait")


def test_wire_is_a_read_only_mapping_with_a_tuple_of_choices() -> None:
    row = _row()
    store = _store(row)
    (view,) = store.view_visible(
        KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN, include_wire=True
    ).rows
    assert type(view.wire) is MappingProxyType
    assert isinstance(view.wire["choices"], tuple)
    with pytest.raises(TypeError):
        view.wire["command"] = "x"  # type: ignore[index]
    with pytest.raises(AttributeError):
        view.wire["choices"].append("x")  # type: ignore[union-attr]
    with pytest.raises(dataclasses.FrozenInstanceError):
        view.wire = {}  # type: ignore[misc]


def test_two_views_never_share_a_wire_or_choices_object() -> None:
    row = _row()
    store = _store(row)
    first = store.view_visible(
        KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN, include_wire=True
    ).rows[0]
    second = store.view_visible(
        KEY[0], KEY[1], KEY[2], now=1_000, members=ALL_OPEN, include_wire=True
    ).rows[0]
    assert first.wire is not second.wire
    assert first.wire["choices"] is not second.wire["choices"]
    assert first.wire["choices"] is not row.choices
    assert first == second and hash(first) == hash(second)  # wire is outside compare and hash


def test_view_visible_is_stable_across_a_following_purge() -> None:
    row = _row(expires_at=100)
    store = _store(row)
    view = store.view_visible(KEY[0], KEY[1], KEY[2], now=100, members=ALL_OPEN).rows[0]
    store.purge(100 + EXPIRY_GRACE_S + 1)
    assert row.status == "expired" and view.status == "open" and view.visible_now


def test_legacy_list_visible_still_returns_live_rows_and_purges() -> None:
    live = _row("a1", expires_at=None)
    expiring = _row("b1", expires_at=50)
    stale = _row("c1", status="resolved", settled_at=0)
    held_row = _row("d1", surface="phone_chat", expires_at=None)
    store = _store(live, expiring, stale, held_row)
    store.set_desktop_held(KEY[0], KEY[1], KEY[2])
    rows = store.list_visible(KEY[0], KEY[1], KEY[2], now=RET)
    assert rows == (held_row,) and rows[0] is held_row  # live object, held filter applied
    assert expiring.status == "expired" and _key(stale) not in store._rows  # RO-3 purge semantics
    assert isinstance(rows, tuple)


def test_legacy_list_visible_uses_the_store_clock_when_now_is_omitted() -> None:
    row = _row(expires_at=10)
    store = PromptStore(clock=lambda: 10 + EXPIRY_GRACE_S + 1)
    store.put(row)
    assert store.list_visible(KEY[0], KEY[1], KEY[2]) == ()
    assert row.status == "expired"


def test_legacy_signatures_are_unchanged() -> None:
    assert str(inspect.signature(PromptStore.list_visible)) == (
        "(self, iid: 'str', user_id: 'str', profile: 'str', *, now: 'int | None' = None)"
        " -> 'tuple[PromptRow, ...]'"
    )
    params = inspect.signature(real_prompts.list_prompts).parameters
    assert list(params) == ["store", "iid", "user_id", "profile", "now", "members"]
    assert params["members"].default is ALL_OPEN


def test_list_prompts_default_members_keep_the_150bd0f_meaning() -> None:
    rows = (_row("a1"), _row("b1", surface="phone_chat"))
    store = _store(*rows)
    result = real_prompts.list_prompts(store, iid=KEY[0], user_id=KEY[1], profile=KEY[2], now=900)
    assert isinstance(result, HttpResult) and result.status == 200
    assert [item["request_id"] for item in result.body["prompts"]] == ["a1", "b1"]
    assert isinstance(result.body["prompts"][0]["choices"], list)  # plain wire bodies, as before
    closed = real_prompts.list_prompts(
        store, iid=KEY[0], user_id=KEY[1], profile=KEY[2], now=900, members=MemberState(False, True)
    )
    assert [item["request_id"] for item in closed.body["prompts"]] == ["b1"]
    assert list(closed.body) == ["prompts", "desktop_held"]


def test_oracle_and_new_list_visible_agree_on_a_grid() -> None:
    rows = (
        _row("a1"), _row("b1", surface="phone_chat"), _row("c1", status="resolved", settled_at=0),
        _row("d1", expires_at=10), _row("e1", surface="phone_chat", expires_at=None),
    )
    for held in (False, True):
        for now in (0, 40, 41, 500):
            new_store = _store(*[dataclasses.replace(r) for r in rows])
            old_real = _store(*[dataclasses.replace(r) for r in rows])
            old_store = _OracleStore(old_real)
            if held:
                new_store.set_desktop_held(KEY[0], KEY[1], KEY[2])
                old_real.set_desktop_held(KEY[0], KEY[1], KEY[2])
            new = new_store.list_visible(KEY[0], KEY[1], KEY[2], now=now)
            old = old_store.list_visible(KEY[0], KEY[1], KEY[2], now=now)
            assert [r.request_id for r in new] == [r.request_id for r in old]


# --------------------------------------------------------------------------------------------
# ServerContext.approval_members_now
# --------------------------------------------------------------------------------------------


def _members_ctx(**kw: Any) -> ServerContext:
    return ServerContext(identity=None, store=None, compat=None, **kw)  # type: ignore[arg-type]


def test_members_now_composes_the_existing_predicates() -> None:
    ctx = _members_ctx(approvals_available=lambda: True, phone_chat_available=lambda: True)
    assert ctx.approval_members_now() == ALL_OPEN
    assert _members_ctx().approval_members_now() == MemberState(False, False)  # default closed
    store = PromptStore(clock=lambda: 1)
    ctx = _members_ctx(approvals_available=lambda: True, phone_chat_available=lambda: True)
    ctx.prompt_store = store
    store.close_phone_chat(1)
    assert ctx.approval_members_now() == MemberState(True, False)  # the binding fence
    store.close(1)
    assert ctx.approval_members_now() == MemberState(False, False)  # the closed generation


@pytest.mark.parametrize("value", [1, "yes", None, [True], 0])
def test_members_now_opens_only_on_an_exact_true(value: Any) -> None:
    ctx = _members_ctx(approvals_available=lambda: value, phone_chat_available=lambda: value)
    assert ctx.approval_members_now() == MemberState(False, False)


def test_members_now_fails_closed_per_member_and_asks_each_once() -> None:
    asked: list[str] = []

    def phone() -> bool:
        asked.append("phone")
        return True

    def approvals() -> bool:
        asked.append("approvals")
        raise RuntimeError("boom")

    ctx = _members_ctx(approvals_available=approvals, phone_chat_available=phone)
    assert ctx.approval_members_now() == MemberState(False, True)
    assert sorted(asked) == ["approvals", "phone"]


def test_members_now_survives_a_replaced_predicate_that_raises() -> None:
    ctx = _members_ctx(approvals_available=lambda: True, phone_chat_available=lambda: True)

    def explode() -> bool:
        raise RuntimeError("boom")

    ctx.is_approvals_available = explode  # type: ignore[method-assign]
    assert ctx.approval_members_now() == MemberState(False, True)


# --------------------------------------------------------------------------------------------
# Scope: reads.py, the live-row APIs and the seam's own import surface
# --------------------------------------------------------------------------------------------


def test_the_seam_runs_no_code_that_logs_or_awaits(tmp_path: Path) -> None:
    """Views are plain synchronous functions: no coroutine, no log line, no clock read."""
    assert not inspect.iscoroutinefunction(PromptStore.view_row)
    assert not inspect.iscoroutinefunction(PromptStore.view_visible)
    store = _store(_row("a1"))
    handler = _Collect()
    logger = logging.getLogger(LOGGER_NAME)
    previous = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        store.view_visible(KEY[0], KEY[1], KEY[2], now=1, members=ALL_OPEN, include_wire=True)
        store.view_row(_key(_row("a1")), now=1, members=ALL_OPEN)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    assert handler.lines == []

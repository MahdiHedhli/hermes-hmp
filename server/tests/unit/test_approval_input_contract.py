"""Spec 015 shared contract types (T010/T011): frozen shapes only, no behavior."""

from __future__ import annotations

import dataclasses
import itertools
import threading
from types import MappingProxyType

import pytest

from hmp_plugin import prompts
from hmp_plugin.prompts import (
    ALL_OPEN,
    SETTLE_AUTHORITATIVE,
    SETTLE_NON_AUTHORITATIVE,
    ApprovalInserted,
    MemberState,
    PromptRow,
    PromptStore,
    RowView,
    VisibleSet,
    is_authoritative,
    phone_open_request,
    wire_prompt,
)

KEY = ("iid_" + "a" * 48, "hmpu_" + "ab" * 16, "default", "req_" + "12" * 16)


def _view(**overrides: object) -> RowView:
    fields: dict[str, object] = {
        "key": KEY,
        "kind": "approval",
        "surface": "bot_chat",
        "generation": 1,
        "status": "open",
        "settle_cause": None,
        "expires_at": 100,
        "held": False,
        "open_now": True,
        "hidden_now": False,
        "visible_now": True,
    }
    fields.update(overrides)
    return RowView(**fields)  # type: ignore[arg-type]


def _wire() -> dict[str, object]:
    return {
        "kind": "approval",
        "surface": "bot_chat",
        "request_id": KEY[3],
        "expires_at": 100,
        "choices": ["once", "deny"],
        "command": "ls",
        "description": "list",
    }


def _row(**overrides: object) -> PromptRow:
    fields: dict[str, object] = {
        "iid": KEY[0],
        "user_id": KEY[1],
        "profile": KEY[2],
        "request_id": KEY[3],
        "kind": "approval",
        "surface": "bot_chat",
        "choices": ("once", "deny"),
        "command": "ls",
        "description": "list",
    }
    fields.update(overrides)
    return PromptRow(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "instance",
    [
        ApprovalInserted(KEY, "bot_chat", 1, None),
        MemberState(True, False),
        _view(),
        VisibleSet(False, ()),
    ],
    ids=lambda value: type(value).__name__,
)
def test_contract_types_are_frozen_dataclasses(instance: object) -> None:
    assert dataclasses.is_dataclass(instance)
    first = dataclasses.fields(instance)[0].name  # type: ignore[arg-type]
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, first, getattr(instance, first))
    with pytest.raises(dataclasses.FrozenInstanceError):
        instance.unexpected = 1  # type: ignore[attr-defined]


def test_field_names_and_order_are_frozen() -> None:
    def names(cls: type) -> list[str]:
        return [item.name for item in dataclasses.fields(cls)]

    assert names(ApprovalInserted) == ["key", "surface", "generation", "expires_at"]
    assert names(MemberState) == ["bot_chat", "phone_chat"]
    assert names(VisibleSet) == ["held", "rows"]
    assert names(RowView) == [
        "key", "kind", "surface", "generation", "status", "settle_cause", "expires_at",
        "held", "open_now", "hidden_now", "visible_now", "session_key", "wire",
    ]


def test_cause_sets_are_exact_and_disjoint() -> None:
    assert {"answer_applied", "native_not_pending", "phone_listing_omitted"} == SETTLE_AUTHORITATIVE
    assert {
        "local_expiry", "generation_closed", "binding_fence", "run_ended", "phone_not_resolved",
        "clarify_retired",
    } == SETTLE_NON_AUTHORITATIVE
    assert isinstance(SETTLE_AUTHORITATIVE, frozenset)
    assert isinstance(SETTLE_NON_AUTHORITATIVE, frozenset)
    assert not SETTLE_AUTHORITATIVE & SETTLE_NON_AUTHORITATIVE


def test_is_authoritative_is_true_only_for_the_three_native_causes() -> None:
    for cause in SETTLE_AUTHORITATIVE:
        assert is_authoritative(cause) is True
    for cause in SETTLE_NON_AUTHORITATIVE:
        assert is_authoritative(cause) is False
    assert is_authoritative(None) is False
    for unknown in ("", "unknown", "ANSWER_APPLIED", "resolved", 1, True, ["answer_applied"], {}):
        assert is_authoritative(unknown) is False


def test_member_state_and_all_open() -> None:
    assert MemberState(bot_chat=True, phone_chat=True) == ALL_OPEN
    assert MemberState(True, False) != MemberState(False, True)
    assert hash(ALL_OPEN) == hash(MemberState(True, True))


def test_approval_inserted_carries_only_the_documented_fields() -> None:
    event = ApprovalInserted(key=KEY, surface="phone_chat", generation=3, expires_at=None)
    assert (event.key, event.surface, event.generation, event.expires_at) == (
        KEY, "phone_chat", 3, None,
    )
    assert hash(event) == hash(ApprovalInserted(KEY, "phone_chat", 3, None))


def test_prompt_row_settle_cause_is_optional_and_last() -> None:
    row = _row()
    assert row.settle_cause is None
    assert dataclasses.fields(PromptRow)[-1].name == "settle_cause"
    assert dataclasses.fields(PromptRow)[-1].default is None
    # Existing positional layout is unchanged up to `settled_at`.
    assert [f.name for f in dataclasses.fields(PromptRow)][-2:] == ["settled_at", "settle_cause"]
    assert _row(settle_cause="local_expiry").settle_cause == "local_expiry"


def test_settle_cause_is_absent_from_wire_and_phone_shapes() -> None:
    for row in (
        _row(settle_cause="answer_applied"),
        _row(kind="clarify", surface="phone_chat", question="q", settle_cause="run_ended"),
        _row(surface="phone_chat", settle_cause="phone_not_resolved"),
    ):
        assert "settle_cause" not in wire_prompt(row)
        assert "settle_cause" not in phone_open_request(row)
        assert "answer_applied" not in repr(wire_prompt(row))


def test_row_view_defaults_session_key_and_wire_to_none() -> None:
    view = _view()
    assert view.session_key is None
    assert view.wire is None


def test_row_view_is_hashable_and_wire_is_excluded_from_compare_and_hash() -> None:
    plain = _view()
    with_wire = _view(wire=_wire())
    other_wire = _view(wire={**_wire(), "command": "other"})
    assert hash(plain) == hash(with_wire) == hash(other_wire)
    assert plain == with_wire == other_wire
    assert len({plain, with_wire, other_wire}) == 1
    by_field = {f.name: f for f in dataclasses.fields(RowView)}
    assert by_field["wire"].compare is False
    assert by_field["wire"].hash is False
    assert all(f.compare and f.hash is None for n, f in by_field.items() if n != "wire")
    # Any other field still distinguishes views, including session_key.
    assert _view(session_key="k") != plain
    assert _view(settle_cause="local_expiry") != plain


def test_row_view_wire_is_an_owned_read_only_snapshot_with_tuple_choices() -> None:
    source = _wire()
    view = _view(wire=source)
    wire = view.wire
    assert isinstance(wire, MappingProxyType)
    assert isinstance(wire["choices"], tuple)
    assert dict(wire) == {**source, "choices": ("once", "deny")}
    # Owned: later changes to the supplied mapping and list do not reach the view.
    source["command"] = "changed"
    source["choices"].append("always")  # type: ignore[attr-defined]
    assert wire["command"] == "ls"
    assert wire["choices"] == ("once", "deny")
    # Read-only.
    with pytest.raises(TypeError):
        wire["command"] = "x"  # type: ignore[index]
    with pytest.raises(TypeError):
        wire["new"] = 1  # type: ignore[index]
    with pytest.raises(AttributeError):
        wire["choices"].append("x")  # type: ignore[attr-defined]


def test_row_view_wire_is_never_shared_between_views_or_with_a_row() -> None:
    row = _row()
    body = wire_prompt(row)
    first = _view(wire=body)
    second = _view(wire=body)
    assert first.wire is not second.wire
    assert first.wire is not body
    for view in (first, second):
        assert view.wire["choices"] == ("once", "deny")  # type: ignore[index]
    # Re-supplying an already frozen mapping still yields a fresh owned snapshot.
    again = _view(wire=first.wire)
    assert again.wire is not first.wire
    assert isinstance(again.wire, MappingProxyType)
    assert again.wire["choices"] == ("once", "deny")  # type: ignore[index]
    assert again.wire["choices"] is not first.wire["choices"]  # type: ignore[index]
    # The live row's own choices are untouched.
    assert row.choices == ("once", "deny")
    assert isinstance(body["choices"], list)


def test_row_view_wire_owns_choices_when_the_supplied_choices_are_already_a_tuple() -> None:
    supplied = ("once", "deny")
    source = MappingProxyType({**_wire(), "choices": supplied})
    first = _view(wire=source)
    second = _view(wire=source)
    for view in (first, second):
        assert view.wire["choices"] == ("once", "deny")  # type: ignore[index]
        assert isinstance(view.wire["choices"], tuple)  # type: ignore[index]
        assert view.wire["choices"] is not supplied  # type: ignore[index]
        assert view.wire["choices"] is not source["choices"]  # type: ignore[index]
    assert first.wire["choices"] is not second.wire["choices"]  # type: ignore[index]


def test_row_view_wire_handles_clarify_shape_without_choices() -> None:
    body = wire_prompt(_row(kind="clarify", surface="phone_chat", choices=(), question="q"))
    view = _view(kind="clarify", wire=body)
    assert "choices" not in view.wire  # type: ignore[operator]
    assert view.wire["question"] == "q"  # type: ignore[index]


def test_visible_set_rows_are_an_owned_tuple() -> None:
    rows = [_view(), _view(key=(*KEY[:3], "other"))]
    visible = VisibleSet(held=True, rows=rows)
    assert isinstance(visible.rows, tuple)
    assert visible.rows == tuple(rows)
    rows.append(_view())
    assert len(visible.rows) == 2
    assert VisibleSet(False, ()).rows == ()
    assert isinstance(VisibleSet(False, iter([_view()])).rows, tuple)  # type: ignore[arg-type]


def test_generation_tokens_are_distinct_ints_per_store() -> None:
    stores = [PromptStore() for _ in range(5)]
    tokens = [store.generation for store in stores]
    assert all(type(token) is int for token in tokens)
    assert len(set(tokens)) == len(tokens)
    assert tokens == sorted(tokens)


def test_generation_tokens_are_distinct_for_stores_built_concurrently() -> None:
    threads, per_thread = 16, 25
    barrier = threading.Barrier(threads)
    built: list[list[int]] = [[] for _ in range(threads)]

    def build(index: int) -> None:
        barrier.wait()
        for _ in range(per_thread):
            built[index].append(PromptStore().generation)

    workers = [threading.Thread(target=build, args=(i,)) for i in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    tokens = [token for chunk in built for token in chunk]
    assert len(tokens) == threads * per_thread
    assert len(set(tokens)) == len(tokens)
    for chunk in built:
        assert chunk == sorted(chunk)


def test_generation_counter_is_advanced_under_its_own_module_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock = prompts._GENERATION_LOCK
    assert type(lock) is type(threading.Lock())
    seen: list[bool] = []
    real = itertools.count(10_000)

    class Probe:
        def __iter__(self) -> Probe:
            return self

        def __next__(self) -> int:
            seen.append(lock.locked())
            return next(real)

    monkeypatch.setattr(prompts, "_GENERATION_COUNTER", Probe())
    store = PromptStore()
    assert seen == [True]
    assert store.generation == 10_000
    assert not store._guard.locked()
    assert lock is not store._guard


def test_generation_counter_is_an_itertools_count() -> None:
    assert isinstance(prompts._GENERATION_COUNTER, itertools.count)

"""The non-wire media read-result carriers (LM-8): causal guards, not a mirror of the code.

The carriers are inert. The serialization guards run against the real `request_ctx._plain`,
`wire.dump_json` and the real error middleware, and again against out-of-tree mutants that must
fail them.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import copy
import dataclasses
import hashlib
import importlib.util
import logging
import pickle
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import make_mocked_request

from hmp_plugin import local_media_sidecar as sc
from hmp_plugin import request_ctx, server, wire
from hmp_plugin.contract import (
    ERROR_MESSAGES,
    ErrorCode,
    HistoryPage,
    HistoryReset,
    ResetReason,
    Row,
    SessionSnapshot,
    SnapshotResponse,
    TailPosition,
)
from hmp_plugin.local_media_sidecar import (
    BridgeMediaRows,
    MediaCandidate,
    MediaCarrierRefusal,
    MediaOrigin,
    MediaReadResult,
    MediaRowsQuery,
    MediaSidecar,
    SidecarStatus,
)

from .fresh_import import foreign_hmp_modules, run_no_local_media_probe

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
SOURCE = (PACKAGE / "local_media_sidecar.py").read_text(encoding="utf-8")

SENTINEL = "SENTINEL-private-media-value-31c7"
DIGEST = hashlib.sha256(SENTINEL.encode()).digest()
CARRIERS = (
    "MediaCandidate",
    "MediaRowsQuery",
    "BridgeMediaRows",
    "MediaSidecar",
    "MediaReadResult",
)


# --- builders -----------------------------------------------------------------------------------


def row(i: int = 1, role: str = "tool") -> Row:
    return Row(id=i, role=role, text="t", client_message_id=None, created_at=1.0)


def candidate(i: int = 1) -> MediaCandidate:
    return MediaCandidate(i, DIGEST)


def sidecar(**over: Any) -> MediaSidecar:
    args: dict[str, Any] = {
        "status": SidecarStatus.CANDIDATES,
        "origin": MediaOrigin.OWN_CONVERSATION,
        "user_id": SENTINEL,
        "profile": SENTINEL,
        "session_id": SENTINEL,
        "query_tip": SENTINEL,
        "lineage_tip": SENTINEL,
        "candidates": (candidate(2), candidate(1)),
    }
    args.update(over)
    return MediaSidecar(**args)


def reset() -> HistoryReset:
    return HistoryReset(ResetReason.GAP)


def result() -> MediaReadResult[HistoryReset]:
    return MediaReadResult(reset(), sidecar())


def instances(mod: Any = sc) -> list[Any]:
    """One sentinel-bearing instance of every carrier class in `mod`."""
    cand = mod.MediaCandidate(7, DIGEST)
    query = mod.MediaRowsQuery(SENTINEL, SENTINEL, SENTINEL)
    side = mod.MediaSidecar(
        status=mod.SidecarStatus.CANDIDATES,
        origin=mod.MediaOrigin.BROWSED_SESSION,
        user_id=SENTINEL,
        profile=SENTINEL,
        session_id=SENTINEL,
        query_tip=SENTINEL,
        lineage_tip=SENTINEL,
        candidates=(cand,),
    )
    return [
        cand,
        query,
        mod.BridgeMediaRows((row(),), query, (cand,)),
        side,
        mod.MediaReadResult(reset(), side),
    ]


# --- the fail-closed guard, reusable against mutants --------------------------------------------


def _raises(exc: type[BaseException], fn: Callable[[], object], what: str) -> BaseException:
    try:
        fn()
    except exc as caught:
        return caught
    raise AssertionError(f"{what}: did not raise {exc.__name__}")


def carrier_guard(
    mod: Any = sc,
    plain: Callable[[Any], Any] = request_ctx._plain,
    dump: Callable[[Any], bytes] = wire.dump_json,
) -> None:
    """Every carrier survives the real serializers only by failing closed. Raises AssertionError."""
    for obj in instances(mod):
        name = type(obj).__name__
        assert not dataclasses.is_dataclass(obj), f"{name} is a dataclass"
        assert not isinstance(obj, Mapping | Sequence | tuple), f"{name} is a container"
        assert not hasattr(obj, "__dict__"), f"{name} has an instance dict"
        for dunder in ("__iter__", "__getitem__", "__len__", "__contains__"):
            assert not hasattr(obj, dunder), f"{name} has {dunder}"
        assert plain(obj) is obj, f"{name} is rewritten by _plain"
        err = _raises(TypeError, lambda obj=obj: dump(plain(obj)), f"{name} dump")
        assert str(err) == f"Object of type {name} is not JSON serializable"
        assert repr(obj) == str(obj) == format(obj) == f"{name}()", f"{name} repr is not fixed"
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            err = _raises(TypeError, lambda obj=obj, p=proto: pickle.dumps(obj, p), "pickle")
            assert str(err) == "not serializable"
        for fn in (copy.copy, copy.deepcopy):
            err = _raises(TypeError, lambda obj=obj, fn=fn: fn(obj), "copy")
            assert str(err) == "not serializable"
        slot = type(obj).__slots__[0]
        _raises(AttributeError, lambda obj=obj, s=slot: setattr(obj, s, None), f"{name} setattr")
        _raises(AttributeError, lambda obj=obj, s=slot: delattr(obj, s), f"{name} delattr")
    nested = instances(mod)[3].candidates
    assert plain(nested) == list(nested)
    err = _raises(TypeError, lambda: dump(plain(nested)), "nested candidates dump")
    assert str(err) == "Object of type MediaCandidate is not JSON serializable"


def test_real_carriers_fail_closed_under_the_real_serializers() -> None:
    carrier_guard()


# --- out-of-tree mutants must fail the guard ----------------------------------------------------

_BLOCK = r"^class {name}\(.*?(?=^class |\Z)"


def _replace_block(source: str, name: str, new: str) -> str:
    return re.sub(_BLOCK.format(name=name), new + "\n\n", source, count=1, flags=re.S | re.M)


def _drop_method(source: str, name: str) -> str:
    return re.sub(rf"    def {name}\(.*?(?=\n    def |\n\nclass )\n?", "", source, flags=re.S)


def _mut_dataclass(source: str) -> str:
    return _replace_block(
        source,
        "MediaCandidate",
        '@__import__("dataclasses").dataclass(frozen=True)\n'
        "class MediaCandidate:\n    tool_row_id: int\n    raw_digest: bytes\n",
    )


def _mut_dataclass_result(source: str) -> str:
    return _replace_block(
        source,
        "MediaReadResult",
        '@__import__("dataclasses").dataclass(frozen=True)\n'
        "class MediaReadResult(Generic[P]):\n    public: Any\n    sidecar: Any\n",
    )


def _mut_mapping(source: str) -> str:
    out = source.replace(
        "class _Carrier:", 'class _Carrier(__import__("collections.abc").abc.Mapping):'
    )
    return out.replace(
        "    __slots__ = ()\n\n    def __init_subclass__",
        "    __slots__ = ()\n\n"
        "    def __getitem__(self, key):\n        return getattr(self, key)\n\n"
        "    def __iter__(self):\n        return iter(type(self).__slots__)\n\n"
        "    def __len__(self):\n        return len(type(self).__slots__)\n\n"
        "    def __init_subclass__",
    )


def _mut_tuple(source: str) -> str:
    return _replace_block(
        source,
        "MediaCandidate",
        "class MediaCandidate(tuple):\n    __slots__ = ()\n\n"
        "    def __new__(cls, tool_row_id, raw_digest):\n"
        "        return tuple.__new__(cls, (tool_row_id, raw_digest))\n\n"
        "    tool_row_id = property(lambda self: self[0])\n"
        "    raw_digest = property(lambda self: self[1])\n",
    )


def _mut_dict(source: str) -> str:
    # Drop the empty `__slots__` from the shared base, so every instance gains a `__dict__`.
    return re.sub(r"(class _Carrier:.*?)    __slots__ = \(\)\n", r"\1", source, count=1, flags=re.S)


def _mut_repr(source: str) -> str:
    return source.replace(
        'return f"{type(self).__name__}()"',
        'return "<" + ",".join(repr(getattr(self, s)) for s in type(self).__slots__) + ">"',
    )


def _mut_pickle(source: str) -> str:
    for name in ("__reduce__", "__reduce_ex__", "__copy__", "__deepcopy__"):
        source = _drop_method(source, name)
    return source


def _mut_setattr(source: str) -> str:
    return _drop_method(source, "__setattr__")


MUTANTS = {
    "dataclass candidate": _mut_dataclass,
    "dataclass result": _mut_dataclass_result,
    "mapping base": _mut_mapping,
    "tuple candidate": _mut_tuple,
    "instance dict": _mut_dict,
    "value repr": _mut_repr,
    "pickle and copy allowed": _mut_pickle,
    "mutable": _mut_setattr,
}


@contextlib.contextmanager
def _loaded(tmp_path: Path, name: str, source: str) -> Iterator[Any]:
    path = tmp_path / f"{name}.py"  # out of tree: never inside the repository
    path.write_text(source, encoding="utf-8")
    modname = f"hmp_plugin._mutant_{name}"
    spec = importlib.util.spec_from_file_location(modname, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    try:
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop(modname, None)


def test_unmutated_copy_out_of_tree_passes_the_guard(tmp_path: Path) -> None:
    # Positive control: loading the module from another location does not itself break the guard.
    with _loaded(tmp_path, "control", SOURCE) as mod:
        carrier_guard(mod)


@pytest.mark.parametrize("label", sorted(MUTANTS))
def test_each_serialization_mutant_fails_the_guard(tmp_path: Path, label: str) -> None:
    mutated = MUTANTS[label](SOURCE)
    assert mutated != SOURCE, "the mutation did not apply"
    with _loaded(tmp_path, "mutant", mutated) as mod, pytest.raises(AssertionError):
        carrier_guard(mod)


def test_serializer_mutants_fail_the_guard() -> None:
    def leaky_dump(value: Any) -> bytes:
        import json

        def default(obj: Any) -> Any:
            if isinstance(obj, bytes):
                return obj.hex()
            return {s.lstrip("_"): getattr(obj, s) for s in type(obj).__slots__}

        return json.dumps(value, default=default, ensure_ascii=False).encode()

    def slot_plain(value: Any) -> Any:
        slots = getattr(type(value), "__slots__", None)
        if slots:
            return {s: getattr(value, s) for s in slots}
        return request_ctx._plain(value)

    with pytest.raises(AssertionError):
        carrier_guard(dump=leaky_dump)
    with pytest.raises(AssertionError):
        carrier_guard(plain=slot_plain)


# --- the actual middleware: an unwrapped carrier is a fixed 500 ---------------------------------

_FIXED_500 = {
    "error": {
        "code": "other",
        "message": ERROR_MESSAGES[ErrorCode.OTHER],
        "why": "internal_error",
    }
}


def _unwrapped() -> list[Callable[[], object]]:
    return [
        lambda: request_ctx.json_response(result()),
        lambda: request_ctx.json_response(sidecar()),
        lambda: request_ctx.json_response(candidate()),
        lambda: server._result_response(result()),
        lambda: server._result_response((200, result())),  # the (status, body) branch, F4
        lambda: server._result_response(sidecar()),
    ]


@pytest.mark.parametrize("index", range(len(_unwrapped())))
def test_unwrapped_carrier_is_a_fixed_500_with_closed_logs(
    index: int, caplog: pytest.LogCaptureFixture
) -> None:
    build = _unwrapped()[index]

    async def handler(_req: Any) -> Any:
        return build()

    async def main() -> Any:
        return await server.error_middleware(make_mocked_request("GET", "/x"), handler)

    with caplog.at_level(logging.DEBUG):
        resp = asyncio.run(main())
    assert resp.status == 500
    assert resp.body == wire.dump_json(_FIXED_500)
    assert SENTINEL not in caplog.text
    assert DIGEST.hex() not in caplog.text and repr(DIGEST) not in caplog.text
    assert "MediaReadResult" not in caplog.text and "MediaSidecar" not in caplog.text
    handler_logs = [r.getMessage() for r in caplog.records if "handler_error" in r.getMessage()]
    assert len(handler_logs) == 1
    assert re.fullmatch(
        r"event=handler_error outcome=internal_error exception_type=TypeError at=\S+ last=\S+",
        handler_logs[0],
    )


def test_a_dataclass_carrier_would_not_be_a_fixed_500(tmp_path: Path) -> None:
    # Causal control for the test above: with a dataclass carrier the same path serializes it.
    with _loaded(tmp_path, "leak", _mut_dataclass_result(SOURCE)) as mod:
        leaked = mod.MediaReadResult(reset(), SENTINEL)  # the mutant does no validation
        assert isinstance(request_ctx._plain(leaked), dict)
        body = request_ctx.json_response(leaked).body
    assert SENTINEL.encode() in body


# --- exact types, bounds and nested classes -----------------------------------------------------


class _Lookalike:
    """Same attributes as a real carrier, different class."""

    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


@pytest.mark.parametrize(
    "args",
    [
        (0, DIGEST),
        (-1, DIGEST),
        (True, DIGEST),
        (1.0, DIGEST),
        ("1", DIGEST),
        (None, DIGEST),
        (1, DIGEST[:-1]),
        (1, DIGEST + b"\x00"),
        (1, bytearray(DIGEST)),
        (1, memoryview(DIGEST)),
        (1, DIGEST.hex()),
        (1, None),
    ],
)
def test_candidate_refuses_bad_types_and_bounds(args: tuple[Any, ...]) -> None:
    with pytest.raises(MediaCarrierRefusal):
        MediaCandidate(*args)


def test_candidate_accepts_the_exact_shape_only() -> None:
    c = MediaCandidate(1, DIGEST)
    assert (c.tool_row_id, c.raw_digest) == (1, DIGEST)
    assert MediaCandidate(2**70, DIGEST).tool_row_id == 2**70

    class IntLike(int):
        pass

    class BytesLike(bytes):
        pass

    with pytest.raises(MediaCarrierRefusal):
        MediaCandidate(IntLike(3), DIGEST)
    with pytest.raises(MediaCarrierRefusal):
        MediaCandidate(3, BytesLike(DIGEST))


def test_candidate_carries_no_path_name_or_raw_content() -> None:
    c = candidate()
    assert type(c).__slots__ == ("_raw_digest", "_tool_row_id")
    assert {n for n in dir(c) if not n.startswith("_")} == {"raw_digest", "tool_row_id"}


class _StrLike(str):
    pass


@pytest.mark.parametrize("bad", ["", "x" * 257, _StrLike("ok"), None, 1, b"ok", ["ok"]], ids=repr)
def test_query_refuses_bad_strings_in_every_field(bad: Any) -> None:
    good = ("p", "s", "t")
    for i in range(3):
        args = list(good)
        args[i] = bad
        with pytest.raises(MediaCarrierRefusal):
            MediaRowsQuery(*args)


def test_query_string_bound_is_inclusive_and_counts_characters() -> None:
    assert MediaRowsQuery("x" * 256, "é" * 256, "t").session_id == "é" * 256


def test_bridge_rows_refuse_bad_nested_values() -> None:
    q = MediaRowsQuery("p", "s", "t")
    cands = (candidate(),)
    good = BridgeMediaRows((row(),), q, cands)
    assert (good.rows, good.query, good.candidates) == ((row(),), q, cands)
    bad_rows: list[Any] = [
        [row()],
        (row(), object()),
        (_Lookalike(id=1),),
        (candidate(),),
        None,
        (row(),) * (sc.MAX_ROWS + 1),
    ]
    for rows in bad_rows:
        with pytest.raises(MediaCarrierRefusal):
            BridgeMediaRows(rows, q, cands)
    for query in (_Lookalike(), None, ("p", "s", "t")):
        with pytest.raises(MediaCarrierRefusal):
            BridgeMediaRows((row(),), query, cands)  # type: ignore[arg-type]
    assert len(BridgeMediaRows((row(),) * sc.MAX_ROWS, q, ()).rows) == sc.MAX_ROWS


def test_candidate_collections_are_exact_bounded_and_unique() -> None:
    q = MediaRowsQuery("p", "s", "t")
    assert sc.MAX_CANDIDATES_PER_RESPONSE == 128
    full = tuple(candidate(i) for i in range(1, 129))
    assert BridgeMediaRows((), q, full).candidates == full
    assert sidecar(candidates=full).candidates == full
    bad: list[Any] = [
        (*full, candidate(500)),
        [candidate()],
        (candidate(), candidate()),  # duplicate row id
        (candidate(), _Lookalike(tool_row_id=2, raw_digest=DIGEST)),
        (object(),),
        None,
    ]
    for cands in bad:
        with pytest.raises(MediaCarrierRefusal):
            BridgeMediaRows((), q, cands)
        with pytest.raises(MediaCarrierRefusal):
            sidecar(candidates=cands)


class _ClassSpoof:
    """Not a `MediaCandidate`, but `isinstance` believes it is; `type()` does not."""

    def __init__(self, claimed: type = MediaCandidate) -> None:
        self.claimed = claimed
        self.reads = 0

    @property
    def __class__(self) -> type:  # type: ignore[override]
        return self.claimed

    @property
    def tool_row_id(self) -> int:
        self.reads += 1
        return 100 + self.reads

    @property
    def raw_digest(self) -> str:
        return "not-bytes"


def test_class_spoof_candidate_is_refused_by_exact_type(tmp_path: Path) -> None:
    spoof = _ClassSpoof()
    assert isinstance(spoof, MediaCandidate) and type(spoof) is not MediaCandidate
    q = MediaRowsQuery("p", "s", "t")
    for cands in ((spoof,), (candidate(), spoof)):
        with pytest.raises(MediaCarrierRefusal):
            BridgeMediaRows((), q, cands)  # type: ignore[arg-type]
        with pytest.raises(MediaCarrierRefusal):
            sidecar(candidates=cands)
    # Causal: an `isinstance` check in place of the exact-type check admits the spoof.
    needle = "type(item) is not MediaCandidate"
    assert needle in SOURCE
    mutated = SOURCE.replace(needle, "not isinstance(item, MediaCandidate)")
    with _loaded(tmp_path, "isinstance_mutant", mutated) as mod:
        mutant_spoof = _ClassSpoof(mod.MediaCandidate)
        admitted = mod.BridgeMediaRows((), mod.MediaRowsQuery("p", "s", "t"), (mutant_spoof,))
        assert len(admitted.candidates) == 1


def test_sidecar_refuses_bad_fields() -> None:
    bad: list[dict[str, Any]] = [
        {"status": "candidates"},
        {"status": None},
        {"origin": "own_conversation"},
        {"origin": SidecarStatus.NO_ROWS},
        {"user_id": ""},
        {"user_id": "x" * 257},
        {"user_id": None},
        {"profile": _StrLike("p")},
        {"profile": None},
        {"session_id": ""},
        {"query_tip": "x" * 257},
        {"lineage_tip": 5},
        {"session_id": None},  # CANDIDATES needs the session and both tips
        {"query_tip": None},
        {"lineage_tip": None},
    ]
    for over in bad:
        with pytest.raises(MediaCarrierRefusal):
            sidecar(**over)


@pytest.mark.parametrize("status", [SidecarStatus.NO_ROWS, SidecarStatus.UNSUPPORTED_BRIDGE])
def test_only_the_candidates_status_carries_candidates(status: SidecarStatus) -> None:
    with pytest.raises(MediaCarrierRefusal):
        sidecar(status=status)
    bare = sidecar(status=status, session_id=None, query_tip=None, lineage_tip=None, candidates=())
    assert bare.candidates == () and bare.status is status
    assert not bare.provenance_consistent
    # A reset page may know its session without a tip.
    assert sidecar(status=status, query_tip=None, candidates=()).session_id == SENTINEL
    with pytest.raises(MediaCarrierRefusal):
        sidecar(status=status, session_id=7, candidates=())


def test_provenance_is_derived_from_the_two_tips() -> None:
    assert sidecar().provenance_consistent is True
    assert sidecar(lineage_tip="other").provenance_consistent is False
    assert "provenance_consistent" not in MediaSidecar.__slots__


def test_sidecar_exposes_what_it_was_given() -> None:
    s = sidecar(origin=MediaOrigin.BROWSED_SESSION, user_id="u", profile="p", session_id="s")
    assert (s.status, s.origin, s.user_id, s.profile, s.session_id) == (
        SidecarStatus.CANDIDATES,
        MediaOrigin.BROWSED_SESSION,
        "u",
        "p",
        "s",
    )
    assert (s.query_tip, s.lineage_tip) == (SENTINEL, SENTINEL)
    assert [c.tool_row_id for c in s.candidates] == [2, 1]


def _wire_public_values() -> list[Any]:
    return [
        reset(),
        HistoryPage(messages=(), head_message_id=None),
        SessionSnapshot(session_ref="r", messages=(), head_message_id=None, truncated=False),
        SnapshotResponse(
            conversation_id="c",
            session_id=None,
            head_message_id=None,
            messages=(),
            turn=None,  # type: ignore[arg-type]
            partial=None,
            partial_lost=False,
            open_requests=(),
            tail=TailPosition(epoch="e", seq=0),
        ),
    ]


@pytest.mark.parametrize("public", _wire_public_values(), ids=lambda v: type(v).__name__)
def test_result_holds_the_exact_public_object_and_sidecar(public: Any) -> None:
    side = sidecar()
    r = MediaReadResult(public, side)
    assert r.public is public
    assert r.sidecar is side


def test_result_refuses_other_publics_and_sidecars() -> None:
    @dataclasses.dataclass(frozen=True)
    class SubReset(HistoryReset):
        pass

    for public in (None, {}, [], (), row(), candidate(), sidecar(), SubReset(ResetReason.GAP)):
        with pytest.raises(MediaCarrierRefusal):
            MediaReadResult(public, sidecar())
    for side in (None, candidate(), _Lookalike(), (sidecar(),)):
        with pytest.raises(MediaCarrierRefusal):
            MediaReadResult(reset(), side)  # type: ignore[arg-type]


def test_subscripted_generic_still_builds_the_exact_class() -> None:
    r = MediaReadResult[HistoryReset](reset(), sidecar())
    assert type(r) is MediaReadResult
    assert not hasattr(r, "__orig_class__")


# --- shape: immutable, slots, fixed text, no pickle ---------------------------------------------


@pytest.mark.parametrize("obj", instances(), ids=lambda o: type(o).__name__)
def test_every_carrier_is_immutable_slots_with_fixed_text(obj: Any) -> None:
    cls = type(obj)
    assert not hasattr(obj, "__dict__") and "__dict__" not in dir(obj)
    assert not hasattr(obj, "__weakref__")
    assert cls.__slots__ and all(s.startswith("_") for s in cls.__slots__)
    with pytest.raises(AttributeError):
        obj.anything = 1
    with pytest.raises(AttributeError):
        obj.__dict__  # noqa: B018
    for slot in cls.__slots__:
        with pytest.raises(AttributeError):
            setattr(obj, slot, None)
        with pytest.raises(AttributeError):
            delattr(obj, slot)
    for prop in (n for n in dir(cls) if isinstance(getattr(cls, n), property)):
        with pytest.raises(AttributeError):
            setattr(obj, prop, None)
    assert repr(obj) == str(obj) == f"{cls.__name__}()" == f"{obj}"
    assert SENTINEL not in repr(obj) and DIGEST.hex() not in repr(obj)
    assert obj == obj and hash(obj) == object.__hash__(obj)


def test_equality_and_hash_are_identity() -> None:
    a, b = candidate(), candidate()
    assert a != b and a == a
    assert len({a, b}) == 2
    assert hash(a) == object.__hash__(a)


def test_pickle_and_copy_are_blocked_without_a_value() -> None:
    carrier_guard()  # pickle/copy/deepcopy for every class and protocol, real module
    for obj in instances():
        for dump in (pickle.dumps, copy.copy, copy.deepcopy):
            with pytest.raises(TypeError, match=r"^not serializable$"):
                dump(obj)
    # A carrier cannot be rebuilt through a reduce tuple or a state dict either.
    for obj in instances():
        with pytest.raises(TypeError):
            obj.__reduce_ex__(2)
        with pytest.raises(TypeError):
            obj.__reduce__()


def test_carriers_are_not_containers_or_dataclasses() -> None:
    for obj in instances():
        assert not dataclasses.is_dataclass(obj)
        assert not isinstance(obj, Mapping | Sequence | tuple | list | dict | set)
        with pytest.raises(TypeError):
            iter(obj)
        with pytest.raises(TypeError):
            len(obj)
        with pytest.raises(TypeError):
            obj[0]
        # Not read as a (status, body) pair by the server (F4).
        assert not (isinstance(obj, tuple) and len(obj) == 2)


@pytest.mark.parametrize("name", CARRIERS)
def test_carrier_classes_cannot_be_subclassed(name: str) -> None:
    base = getattr(sc, name)
    with pytest.raises(TypeError):
        type("Sub", (base,), {})
    with pytest.raises(TypeError):
        type("Sub", (base,), {"__module__": sc.__name__})  # right module, name not in the set
    with pytest.raises(TypeError):
        type(name, (base,), {})  # the right name in another module


def test_the_shared_base_is_closed_to_new_classes() -> None:
    with pytest.raises(TypeError):
        type("Extra", (sc._Carrier,), {"__module__": sc.__name__})


def test_refusal_text_is_fixed_and_survives_reduce() -> None:
    err = MediaCarrierRefusal()
    assert str(err) == "local media carrier refused" and err.args == (str(err),)
    clone = pickle.loads(pickle.dumps(err))  # noqa: S301 - a fixed, parameterless refusal
    assert type(clone) is MediaCarrierRefusal and clone.args == err.args
    with pytest.raises(MediaCarrierRefusal) as ei:
        MediaCandidate(0, SENTINEL.encode())
    assert SENTINEL not in str(ei.value) and SENTINEL not in repr(ei.value)
    assert ei.value.__cause__ is None and ei.value.__suppress_context__


def test_refusal_never_names_the_value_for_any_bad_field() -> None:
    attempts: list[Callable[[], object]] = [
        lambda: MediaCandidate(0, DIGEST),
        lambda: MediaCandidate(1, SENTINEL.encode()),
        lambda: MediaRowsQuery(SENTINEL * 20, "s", "t"),
        lambda: sidecar(user_id=SENTINEL * 20),
        lambda: sidecar(candidates=[candidate()]),
        lambda: MediaReadResult({SENTINEL: DIGEST}, sidecar()),
    ]
    for attempt in attempts:
        with pytest.raises(MediaCarrierRefusal) as ei:
            attempt()
        assert str(ei.value) == "local media carrier refused"
        assert SENTINEL not in repr(ei.value.args)


def test_enums_are_closed() -> None:
    assert {m.value for m in MediaOrigin} == {"own_conversation", "browsed_session"}
    assert {m.value for m in SidecarStatus} == {"candidates", "no_rows", "unsupported_bridge"}


# --- protocol, imports and inertness ------------------------------------------------------------


def test_media_bridge_protocol_is_optional_and_not_runtime_probed() -> None:
    from typing import Protocol

    assert Protocol in sc.MediaReadBridge.__mro__
    assert {"latest_with_media", "after_with_media"} <= set(vars(sc.MediaReadBridge))
    with pytest.raises(TypeError):  # not runtime_checkable: nothing can isinstance-probe it
        isinstance(object(), sc.MediaReadBridge)
    from hmp_plugin.contract import ReadBridge

    assert not {"latest_with_media", "after_with_media"} & set(vars(ReadBridge))


def _imports(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    return found


def test_module_imports_only_stdlib_and_contract() -> None:
    assert _imports(SOURCE) == {"__future__", "enum", "typing", ".contract"}
    assert not [n for n in _imports(SOURCE) if "local_media" in n]


def test_import_detector_sees_a_parser_import() -> None:
    found = _imports("from . import x\nfrom .local_media_result import y")
    assert ".local_media_result" in found


def _fresh(code: str) -> subprocess.CompletedProcess[str]:
    import os

    env = {**os.environ, "PYTHONPATH": str(PACKAGE.parent)}
    return subprocess.run(
        [sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, check=False
    )


def test_existing_read_and_server_paths_load_no_media_module() -> None:
    done = run_no_local_media_probe(
        [
            "hmp_plugin",
            "hmp_plugin.server",
            "hmp_plugin.reads",
            "hmp_plugin.request_ctx",
            "hmp_plugin.wire",
            "hmp_plugin.compat",
            "hmp_plugin.cli",
        ]
    )
    assert done.returncode == 0, done.stderr[-500:]


def test_foreign_provenance_check_rejects_modules_outside_the_package(tmp_path: Path) -> None:
    import types

    foreign = tmp_path / "other" / "hmp_plugin"
    foreign.mkdir(parents=True)
    own = types.ModuleType("hmp_plugin.reads")
    own.__file__ = str(PACKAGE / "reads.py")
    pkg = types.ModuleType("hmp_plugin")
    pkg.__file__ = str(PACKAGE / "__init__.py")
    pkg.__path__ = [str(PACKAGE)]
    assert foreign_hmp_modules({"hmp_plugin": pkg, "hmp_plugin.reads": own}, str(PACKAGE)) == []

    stray = types.ModuleType("hmp_plugin.routes")
    stray.__file__ = str(foreign / "routes.py")
    bad_pkg = types.ModuleType("hmp_plugin")
    bad_pkg.__file__ = str(foreign / "__init__.py")
    bad_pkg.__path__ = [str(foreign)]
    sneaky = types.ModuleType("hmp_plugin.sneaky")  # no file: only a foreign __path__
    sneaky.__path__ = [str(PACKAGE), str(foreign)]
    sibling = types.ModuleType("hmp_plugin.x")  # name-prefix sibling of the package dir
    sibling.__file__ = str(PACKAGE) + "_evil/x.py"
    mods = {
        "hmp_plugin": bad_pkg,
        "hmp_plugin.routes": stray,
        "hmp_plugin.sneaky": sneaky,
        "hmp_plugin.x": sibling,
        "json": types.ModuleType("json"),
    }
    assert foreign_hmp_modules(mods, str(PACKAGE)) == [
        "hmp_plugin",
        "hmp_plugin.routes",
        "hmp_plugin.sneaky",
        "hmp_plugin.x",
    ]


def test_fresh_probe_fails_when_hmp_plugin_resolves_from_a_foreign_tree(tmp_path: Path) -> None:
    root = tmp_path / "foreign"
    shutil.copytree(PACKAGE, root / "hmp_plugin", ignore=shutil.ignore_patterns("__pycache__"))
    ok = run_no_local_media_probe(["hmp_plugin", "hmp_plugin.wire"])
    assert ok.returncode == 0, ok.stderr[-500:]
    done = run_no_local_media_probe(["hmp_plugin", "hmp_plugin.wire"], search_root=root)
    assert done.returncode != 0
    assert "foreign hmp_plugin" in done.stderr


def test_sidecar_import_loads_no_parser_scanner_or_registry() -> None:
    done = _fresh(
        "import sys\n"
        "import hmp_plugin.local_media_sidecar as m\n"
        "loaded = sorted(x for x in sys.modules if 'local_media' in x)\n"
        "assert loaded == ['hmp_plugin.local_media_sidecar'], loaded\n"
        "assert 'hmp_plugin.bridge' not in sys.modules and 'hmp_plugin.reads' not in sys.modules\n"
        "m.MediaCandidate(1, bytes(32))\n"
    )
    assert done.returncode == 0, done.stderr[-500:]


_SIDECAR = "local_media_sidecar"
# accepted S2b / C6b: a static import, module scope ONLY
_MODULE_SCOPE = {"local_media_candidate.py", "local_media_batch_binding.py"}
_FUNCTION_SCOPE = {"bridge.py", "reads.py"}  # S2c/S2d: only inside a function body


def _sidecar_imports(source: str) -> list[str]:
    """One scope label per import of the sidecar in `source`: `module` (a direct statement of the
    module), `function` (inside any function body) or `nested` (class/if/try/with outside every
    function)."""
    found: list[str] = []

    def visit(node: ast.AST, in_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            hit = False
            if isinstance(child, ast.Import):
                hit = any(a.name.split(".")[-1] == _SIDECAR for a in child.names)
            elif isinstance(child, ast.ImportFrom):
                named = (child.module or "").split(".")[-1] == _SIDECAR
                hit = named or any(a.name == _SIDECAR for a in child.names)
            if hit:
                if in_function:
                    found.append("function")
                else:
                    found.append("module" if isinstance(node, ast.Module) else "nested")
            visit(
                child,
                in_function or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)),
            )

    visit(ast.parse(source), False)
    return found


def _sidecar_import_allowed(filename: str, source: str) -> bool:
    if filename == "local_media_sidecar.py":
        return True
    scopes = _sidecar_imports(source)
    if filename in _MODULE_SCOPE:
        return all(scope == "module" for scope in scopes)
    if filename in _FUNCTION_SCOPE:
        return all(scope == "function" for scope in scopes)
    return not scopes


def test_no_production_module_imports_the_sidecar_outside_the_accepted_boundary() -> None:
    for path in sorted(PACKAGE.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert _sidecar_import_allowed(path.name, source), path.name


_STATIC = "from .local_media_sidecar import MediaCandidate\n"
_FORBIDDEN_FUNCTION_ONLY = {
    "module": _STATIC,
    "module_plain": "import hmp_plugin.local_media_sidecar\n",
    "module_from_package": "from . import local_media_sidecar\n",
    "class": "class B:\n    from .local_media_sidecar import MediaCandidate\n",
    "if": "if True:\n    from .local_media_sidecar import MediaCandidate\n",
    "try": (
        "try:\n    from .local_media_sidecar import MediaCandidate\nexcept ImportError:\n    pass\n"
    ),
    "function_and_module": ("def f():\n    from .local_media_sidecar import X\n" + _STATIC),
}


@pytest.mark.parametrize("filename", sorted(_FUNCTION_SCOPE))
@pytest.mark.parametrize("label", sorted(_FORBIDDEN_FUNCTION_ONLY))
def test_sidecar_guard_rejects_non_function_scope_in_bridge_and_reads(
    filename: str, label: str
) -> None:
    assert not _sidecar_import_allowed(filename, _FORBIDDEN_FUNCTION_ONLY[label])


@pytest.mark.parametrize("filename", sorted(_FUNCTION_SCOPE))
@pytest.mark.parametrize(
    "source",
    [
        "def f():\n    from .local_media_sidecar import MediaCandidate\n",
        "class B:\n    async def f(self):\n        from . import local_media_sidecar\n",
        "x = 1\n",
    ],
)
def test_sidecar_guard_allows_function_local_import_in_bridge_and_reads(
    filename: str, source: str
) -> None:
    assert _sidecar_import_allowed(filename, source)


_NOT_MODULE_SCOPE = {
    "function": "def f():\n    from .local_media_sidecar import MediaCandidate\n",
    "async_function": "async def f():\n    from . import local_media_sidecar\n",
    "class": "class B:\n    from .local_media_sidecar import MediaCandidate\n",
    "if": "if True:\n    from .local_media_sidecar import MediaCandidate\n",
    "try": (
        "try:\n    from .local_media_sidecar import MediaCandidate\nexcept ImportError:\n    pass\n"
    ),
    "with": "with x:\n    import hmp_plugin.local_media_sidecar\n",
    "module_and_function": _STATIC + "def f():\n    from . import local_media_sidecar\n",
}


@pytest.mark.parametrize("label", sorted(_NOT_MODULE_SCOPE))
def test_sidecar_guard_requires_module_scope_in_the_candidate(label: str) -> None:
    assert not _sidecar_import_allowed("local_media_candidate.py", _NOT_MODULE_SCOPE[label])


def test_sidecar_guard_accepts_the_candidate_static_import() -> None:
    assert _sidecar_import_allowed("local_media_candidate.py", _STATIC)
    assert _sidecar_import_allowed(
        "local_media_candidate.py", "from . import local_media_sidecar\n"
    )


def test_sidecar_guard_rejects_other_modules_in_every_form() -> None:
    local = "def f():\n    from .local_media_sidecar import MediaCandidate\n"
    for name in ("server.py", "local_media_result.py", "local_media_registry.py", "wire.py"):
        assert not _sidecar_import_allowed(name, _STATIC), name
        assert not _sidecar_import_allowed(name, local), name


def test_sidecar_guard_sees_the_real_accepted_imports() -> None:
    candidate = (PACKAGE / "local_media_candidate.py").read_text(encoding="utf-8")
    assert _sidecar_imports(candidate) and set(_sidecar_imports(candidate)) == {"module"}
    for name in sorted(_FUNCTION_SCOPE):
        source = (PACKAGE / name).read_text(encoding="utf-8")
        assert _sidecar_imports(source) and set(_sidecar_imports(source)) == {"function"}, name

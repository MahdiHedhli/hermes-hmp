"""S4: descriptor emission on the four read routes (spec 011; HMP v1 §7e LM-4..LM-9).

Real authenticated aiohttp requests drive the real routes over the real `Reads`, the real
`HermesReadBridge` on a synthetic native database, the real sidecar/binding modules and the real
registry bound by the adapter's real `_media_bind`. Nothing touches a live Hermes home, network,
provider or device. Expected values are hand-written, not recomputed with the code under test.

A "guard" scenario returns True only when the property holds. Each causal mutant edits ONE line of a
copy of the production source and the matching scenario must then return False, so the scenario
cannot pass vacuously. Native sidecar/binding internals are covered by their own accepted tests;
fetch (S5) is not implemented here and nothing in this file claims it.
"""

from __future__ import annotations

import ast
import asyncio
import contextvars
import dataclasses
import hashlib
import importlib
import json
import logging
import os
import re
import sys
import threading
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import bridge as BRIDGE_MODULE  # noqa: N812
from hmp_plugin import local_media_registry as real_registry
from hmp_plugin import reads as READS_MODULE  # noqa: N812
from hmp_plugin import server, wire
from hmp_plugin.contract import (
    ERROR_MESSAGES,
    ERROR_TABLE,
    ErrorCode,
    HmpError,
    WireMediaDescriptor,
    WireMessage,
)
from hmp_plugin.reads import Reads

from . import hmp_kit
from .approved_push_bridge_witness import (
    APPROVED_AT1_BRIDGE_BLOCK,
    APPROVED_PRE_AT1_BRIDGE_SHA256,
    assert_approved_s5_block,
    reverse_approved_at1_bridge,
    reverse_approved_push_diagnostics,
)
from .media_binding_world import World as PackageWorld
from .media_binding_world import install_gateway_stubs
from .test_local_media_batch_binding import USER
from .test_local_media_batch_binding import Env as NativeEnv

PACKAGE = Path(server.__file__).parent
PROFILE = "alpha"
REF_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
GATE = {"flag": True}


# ---------------------------------------------------------------------------------------------
# The rig: one paired owner device on a real listener context bound by the real adapter code.
# ---------------------------------------------------------------------------------------------


class Rig:
    def __init__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        kind: str = "phone",
        images: int = 3,
        extra_rows: bool = False,
    ) -> None:
        self.tmp_path, self.monkeypatch = tmp_path, monkeypatch
        self.native = NativeEnv(tmp_path / "n")
        self.native.world.approve(USER, PROFILE)
        self.env = hmp_kit.Env(tmp_path / "h")
        self.kind = kind
        if kind == "phone":
            self.tip = self.native.phone(("p1", "p2"), images)
            self.session = "p1"
        else:
            self.tip = self.native.bot_chat(("R", "C"), images=images)
            self.session = "R"
        if extra_rows:
            self._extra_rows()
        # The route-level reads also ask for the forward compression chain (a lineage read the
        # accepted binding tests do not need), so the synthetic native DB answers it too.
        self.native.db.get_compression_chain = self.native.db._forward  # type: ignore[attr-defined]
        for rows in self.native.db.messages.values():
            for row in rows:
                row.setdefault("active", 1)
        ctx = self.env.ctx
        self.reads = Reads(
            self.native.bridge,
            self.env.store,
            iid=self.env.iid,
            guarantees=ctx.guarantees,
            write_gate=ctx.write_gate,
            clock=self.env.clock,
            epoch="e" * 16,
        )
        ctx.bridge, ctx.reads = self.native.bridge, self.reads
        self.owners: set[str] = set()
        self.flag = True
        ctx.owner_device_ids = lambda: frozenset(self.owners)
        ctx.media_flag = lambda: self.flag
        self.adapter = self._adapter_module()
        # The module objects the bridge and `Reads` classes of THIS test process came from,
        # captured at import: another test may evict and re-import the package later.
        self.bridge_module, self.reads_module = BRIDGE_MODULE, READS_MODULE
        ctx.media_available = self.adapter._media_bind(ctx, BRIDGE_MODULE, READS_MODULE)
        assert ctx.media_registry is not None and ctx.media_modules is not None
        self.registry = ctx.media_registry
        self.ctx = ctx
        self.device: hmp_kit.Device | None = None
        self.bind_calls = 0
        self.twin_calls: list[str] = []
        real_bind = self.native.bridge.bind_media_batch

        def counted(sidecar: Any) -> Any:
            self.bind_calls += 1
            return real_bind(sidecar)

        self.real_bind = real_bind
        self.native.bridge.bind_media_batch = counted  # type: ignore[method-assign]

    def _adapter_module(self) -> types.ModuleType:
        install_gateway_stubs(self.monkeypatch)
        self.monkeypatch.delitem(sys.modules, "hmp_plugin.adapter", raising=False)
        module = importlib.import_module("hmp_plugin.adapter")
        self.monkeypatch.setitem(sys.modules, "hmp_plugin.adapter", module)
        return module

    def _extra_rows(self) -> None:
        """An assistant `MEDIA:` row, a non-image tool carrying an image-shaped result and a user
        row: none may ever carry a descriptor."""
        rows = self.native.db.messages[self.tip]
        base = max(r["id"] for r in rows) + 1
        path = f"{self.native.home}/cache/images/zz.png"
        rows.append({"id": base, "role": "assistant", "content": f"MEDIA:{path}"})
        rows.append({"id": base + 1, "role": "user", "content": f"see {path}"})
        rows.append({"id": base + 2, "role": "assistant", "tool_calls": [_call("cx")]})
        rows.append(
            {
                "id": base + 3,
                "role": "tool",
                "tool_call_id": "cx",
                "tool_name": "other_tool",
                "content": '{"success": true, "image": "' + path + '"}',
            }
        )

    # -- requests ------------------------------------------------------------------------------

    def session_ref(self, session_id: str | None = None) -> str:
        return self.env.store.mint_or_get_session_ref(
            USER, PROFILE, session_id or self.session, "sref_" + "q" * 20, self.env.clock.now
        )

    async def pair(self, client: TestClient, *, owner: bool = True) -> hmp_kit.Device:
        dev = hmp_kit.Device()
        offer = self.env.offer()
        status, body = await hmp_kit.post(client, "/pair/request", self.env.p2_body(dev, offer))
        assert status == 202, body
        dev.pairing_id, dev.ni = body["pairing_id"], wire.b64u_decode(body["ni"], length=32)
        self.env.confirm(dev, user_id=USER)
        status, body = await hmp_kit.post(client, "/pair/complete", self.env.p4_body(dev))
        assert status == 200, body
        dev.device_id, dev.refresh, dev.access = (
            body["device_id"],
            body["refresh_token"],
            body["access_token"],
        )
        if owner:
            self.owners.add(dev.device_id)
        self.device = dev
        return dev

    async def fetch(self, client: TestClient, path: str) -> tuple[int, bytes]:
        assert self.device is not None
        resp = await client.get(hmp_kit.url(path), headers=self.env.headers(self.device))
        return resp.status, await resp.read()

    def routes(self) -> dict[str, str]:
        ref = self.session_ref()
        return {
            "ro3": f"/bots/{PROFILE}/conversations/default?limit=500",
            "ro6": f"/bots/{PROFILE}/conversations/default/messages?after=0&limit=500",
            "ses2": f"/bots/{PROFILE}/sessions/{ref}/messages?limit=500",
            "ses2_paged": f"/bots/{PROFILE}/sessions/{ref}/messages?after=1&limit=500",
            "ses2a": f"/bots/{PROFILE}/sessions/{ref}/messages/from-start?limit=500",
        }

    def run(self, scenario: Callable[[TestClient, Rig], Any]) -> Any:
        out: list[Any] = []

        async def main() -> None:
            test_server = TestServer(self.env.app())
            await test_server.start_server()
            async with TestClient(test_server) as client:
                out.append(await scenario(client, self))

        asyncio.run(main())
        return out[0]


def _call(call_id: str) -> dict[str, Any]:
    from .test_local_media_active_batch import call

    return call(call_id)


def media_of(body: bytes) -> dict[int, dict[str, Any]]:
    data = json.loads(body)
    return {m["id"]: m["media"] for m in data["messages"] if "media" in m}


def tool_ids(body: bytes) -> list[int]:
    return [m["id"] for m in json.loads(body)["messages"] if m["role"] == "tool"]


def caller(rig: Rig, device_id: str) -> Any:
    return real_registry.Caller(device_id, USER, rig.env.iid, PROFILE)


# ---------------------------------------------------------------------------------------------
# Descriptors on all four read routes (and both SES-2 branches), own Phone and canonical Bot Chat
# ---------------------------------------------------------------------------------------------

EXPECTED_IDS = [6, 4, 2]  # tool rows of the three seeded images, newest first


@pytest.mark.parametrize("kind", ["phone", "bot"])
def test_every_read_route_emits_descriptors_for_the_accepted_tool_rows(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch, kind=kind, extra_rows=True)

    async def scenario(client: TestClient, rig: Rig) -> dict[str, dict[int, dict[str, Any]]]:
        dev = await rig.pair(client)
        routes = rig.routes()
        if kind == "phone":
            names = ["ro3", "ro6", "ses2", "ses2_paged", "ses2a"]
        else:  # the canonical Bot Chat is only reachable through session browsing
            names = ["ses2", "ses2_paged", "ses2a"]
        found = {}
        for name in names:
            status, body = await rig.fetch(client, routes[name])
            assert status == 200, (name, body)
            found[name] = media_of(body)
            if name == "ses2_paged":  # after=1: rows 2.. only; the row 2 is still returned
                assert 2 in found[name]
        assert dev.device_id in rig.owners
        return found

    found = rig.run(scenario)
    refs = {}
    for name, media in found.items():
        if name == "ses2_paged":
            assert set(media) == set(EXPECTED_IDS)  # tool row 2 is after cursor 1
        else:
            assert set(media) == set(EXPECTED_IDS), name
        for row_id, descriptor in media.items():
            assert set(descriptor) == {"kind", "ref"} and descriptor["kind"] == "image"
            assert REF_RE.match(descriptor["ref"])
            refs.setdefault(row_id, set()).add(descriptor["ref"])
    # Idempotent mint: every route (same binding) returned the very same ref for each row.
    assert all(len(v) == 1 for v in refs.values())
    assert rig.registry._audit() == 3  # no duplicate entries, no assistant/other-tool entry
    assert rig.bind_calls == len(found)  # exactly one batch per emitting response


@pytest.mark.parametrize("kind", ["phone", "bot"])
def test_registry_bindings_are_exact_and_kind_follows_the_proven_session(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch, kind=kind)

    async def scenario(client: TestClient, rig: Rig) -> tuple[dict[int, Any], str]:
        dev = await rig.pair(client)
        name = "ro3" if kind == "phone" else "ses2"
        status, body = await rig.fetch(client, rig.routes()[name])
        assert status == 200
        assert dev.device_id is not None
        return media_of(body), dev.device_id

    media, device_id = rig.run(scenario)
    assert set(media) == set(EXPECTED_IDS)
    for row_id, descriptor in media.items():
        snap = rig.registry.lookup(descriptor["ref"], caller(rig, device_id))
        assert snap is not None
        binding = snap.binding
        expected_kind = (
            real_registry.SessionKind.PHONE
            if kind == "phone"
            else (real_registry.SessionKind.BOT_CHAT)
        )
        assert binding.kind is expected_kind
        assert (binding.user_id, binding.profile, binding.instance_id) == (
            USER,
            PROFILE,
            rig.env.iid,
        )
        assert binding.device_id == device_id and binding.tool_row_id == row_id
        assert binding.session_id == rig.session and binding.tip == rig.tip
        assert binding.raw_digest == rig.native.digests[row_id]
        # a different device or user gets nothing for the same ref
        assert (
            rig.registry.lookup(
                descriptor["ref"], real_registry.Caller("other", USER, rig.env.iid, PROFILE)
            )
            is None
        )


def test_the_newest_128_get_descriptors_and_older_rows_get_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch, images=130)

    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        assert status == 200
        return body

    body = rig.run(scenario)
    ids = sorted(tool_ids(body))
    assert len(ids) == 130
    media = media_of(body)
    assert set(media) == set(ids[2:])  # the two oldest tool rows carry none
    assert rig.registry._audit() == 128
    assert rig.bind_calls == 1


# ---------------------------------------------------------------------------------------------
# Closed paths: exact old bytes, and no twin, batch or mint at all
# ---------------------------------------------------------------------------------------------


def _closed_variants() -> list[str]:
    return ["non_owner", "flag_off", "unavailable", "flag_truthy_not_true", "owner_removed"]


async def _baseline_bytes(client: TestClient, rig: Rig, name: str) -> bytes:
    status, body = await rig.fetch(client, rig.routes()[name])
    assert status == 200
    return body


def _spy_twins(rig: Rig) -> None:
    for name in (
        "snapshot_with_media",
        "history_with_media",
        "session_snapshot_with_media",
        "session_history_with_media",
    ):
        real = getattr(Reads, name)

        def make(real: Callable[..., Any], label: str) -> Callable[..., Any]:
            def spy(self: Any, *a: Any, **k: Any) -> Any:
                rig.twin_calls.append(label)
                return real(self, *a, **k)

            return spy

        rig.monkeypatch.setattr(Reads, name, make(real, name))


@pytest.mark.parametrize("variant", _closed_variants())
@pytest.mark.parametrize("route", ["ro3", "ro6", "ses2", "ses2_paged", "ses2a"])
def test_closed_inputs_use_the_old_read_with_exact_bytes_and_no_media_work(
    variant: str, route: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    _spy_twins(rig)

    async def scenario(client: TestClient, rig: Rig) -> tuple[bytes, bytes]:
        dev = await rig.pair(client)
        # reference bytes: the same device with the media flag off (the pre-S4 old read)
        rig.flag = False
        reference = await _baseline_bytes(client, rig, route)
        rig.flag = True
        rig.twin_calls.clear()
        rig.bind_calls = 0
        if variant == "non_owner":
            rig.owners.discard(dev.device_id)
        elif variant == "flag_off":
            rig.flag = False
        elif variant == "unavailable":
            rig.ctx.media_available = lambda: False
        elif variant == "flag_truthy_not_true":
            rig.ctx.media_flag = lambda: 1
        elif variant == "owner_removed":
            rig.ctx.owner_device_ids = lambda: frozenset()
        return reference, await _baseline_bytes(client, rig, route)

    reference, got = rig.run(scenario)
    assert got == reference and b'"media"' not in got
    assert rig.twin_calls == [] and rig.bind_calls == 0
    assert rig.registry._audit() == 0


@pytest.mark.parametrize("route", ["ro3", "ro6", "ses2", "ses2_paged", "ses2a"])
def test_open_and_closed_bytes_differ_only_by_the_media_members(
    route: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)

    async def scenario(client: TestClient, rig: Rig) -> tuple[bytes, bytes]:
        await rig.pair(client)
        rig.flag = False
        closed = await _baseline_bytes(client, rig, route)
        rig.flag = True
        return closed, await _baseline_bytes(client, rig, route)

    closed, opened = rig.run(scenario)
    assert closed != opened
    stripped = json.loads(opened)
    for message in stripped["messages"]:
        message.pop("media", None)
    assert stripped == json.loads(closed)  # no other field changed
    # the `media` object follows the previous members and leaves their order untouched
    assert re.sub(rb',"media":\{"kind":"image","ref":"[A-Za-z0-9_-]{43}"\}', b"", opened) == (
        closed
    )


def test_no_candidates_means_zero_batches_and_zero_mints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch, images=0)

    async def scenario(client: TestClient, rig: Rig) -> list[int]:
        await rig.pair(client)
        out = []
        for name in ("ro3", "ro6", "ses2", "ses2a"):
            status, body = await rig.fetch(client, rig.routes()[name])
            assert status == 200 and b'"media"' not in body
            out.append(status)
        return out

    rig.run(scenario)
    assert rig.bind_calls == 0 and rig.registry._audit() == 0


def test_a_history_reset_keeps_its_exact_bytes_and_binds_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)

    async def scenario(client: TestClient, rig: Rig) -> tuple[bytes, bytes]:
        await rig.pair(client)
        path = f"/bots/{PROFILE}/conversations/default/messages?after=99999&limit=50"
        rig.flag = False
        status, closed = await rig.fetch(client, path)
        rig.flag = True
        rig.bind_calls = 0
        status2, opened = await rig.fetch(client, path)
        assert status == status2 == 200
        return closed, opened

    closed, opened = rig.run(scenario)
    assert b'"reset"' in closed and opened == closed
    assert rig.bind_calls == 0 and rig.registry._audit() == 0


# ---------------------------------------------------------------------------------------------
# Optional failures keep the successful text and never become a text-read error or a re-read
# ---------------------------------------------------------------------------------------------


def _closed_bytes(rig: Rig, route: str) -> bytes:
    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        rig.flag = False
        out = await _baseline_bytes(client, rig, route)
        rig.flag = True
        return out

    return rig.run(scenario)  # type: ignore[no-any-return]


def _after_pairing(rig: Rig, route: str, patch: Callable[[Rig], None]) -> tuple[bytes, bytes]:
    async def scenario(client: TestClient, rig: Rig) -> tuple[bytes, bytes]:
        await rig.pair(client)
        rig.flag = False
        reference = await _baseline_bytes(client, rig, route)
        rig.flag = True
        patch(rig)
        return reference, await _baseline_bytes(client, rig, route)

    return rig.run(scenario)  # type: ignore[no-any-return]


def _bind_raises(rig: Rig) -> None:
    def boom(_sidecar: Any) -> Any:
        rig.bind_calls += 1
        raise RuntimeError("PRIVATE-bind-failure")

    rig.native.bridge.bind_media_batch = boom  # type: ignore[method-assign]


def _bind_closed(reason: str) -> Callable[[Rig], None]:
    def patch(rig: Rig) -> None:
        from hmp_plugin import local_media_batch_binding as binding_module

        def closed(sidecar: Any) -> Any:
            rig.bind_calls += 1
            counts = (len(sidecar.candidates), 0, 0, 0, 0, 0)
            return binding_module.MediaBatchBinding(sidecar, None, reason, (), counts)

        rig.native.bridge.bind_media_batch = closed  # type: ignore[method-assign]

    return patch


@pytest.mark.parametrize(
    "patch",
    [
        _bind_raises,
        _bind_closed("not_eligible"),
        _bind_closed("eligibility_uncertain"),
        _bind_closed("home_invalid"),
        _bind_closed("provenance_mismatch"),
    ],
    ids=["raises", "not_eligible", "uncertain", "home_invalid", "provenance"],
)
@pytest.mark.parametrize("route", ["ro3", "ses2a"])
def test_a_refused_or_failed_binding_keeps_the_exact_text_and_mints_nothing(
    patch: Callable[[Rig], None], route: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    reference, got = _after_pairing(rig, route, patch)
    assert got == reference
    assert rig.bind_calls == 1  # never rerun to recover
    assert rig.registry._audit() == 0


def test_a_binding_with_a_subset_of_accepted_rows_mints_exactly_that_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)

    def patch(rig: Rig) -> None:
        real = rig.real_bind

        def subset(sidecar: Any) -> Any:
            from hmp_plugin import local_media_batch_binding as binding_module

            full = real(sidecar)
            counts = (len(sidecar.candidates), 2, 1, 6, 1, 1)
            return binding_module.MediaBatchBinding(sidecar, full.kind, "ok", (6, 2), counts)

        rig.native.bridge.bind_media_batch = subset  # type: ignore[method-assign]

    _, got = _after_pairing(rig, "ro3", patch)
    assert set(media_of(got)) == {6, 2}
    assert rig.registry._audit() == 2


def test_a_text_read_failure_keeps_its_original_semantics_and_is_not_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    old_calls: list[str] = []
    real_old = Reads.snapshot

    def old_spy(self: Any, *a: Any) -> Any:
        old_calls.append("old")
        return real_old(self, *a)

    monkeypatch.setattr(Reads, "snapshot", old_spy)

    def failing(self: Any, *a: Any) -> Any:
        rig.twin_calls.append("twin")
        raise HmpError(ErrorCode.NOT_FOUND)

    monkeypatch.setattr(Reads, "snapshot_with_media", failing)

    async def scenario(client: TestClient, rig: Rig) -> tuple[int, bytes]:
        await rig.pair(client)
        return await rig.fetch(client, rig.routes()["ro3"])

    status, body = rig.run(scenario)
    assert status == 404
    assert json.loads(body)["error"]["code"] == "not_found"
    assert rig.twin_calls == ["twin"] and old_calls == [] and rig.bind_calls == 0


def test_a_generic_twin_failure_is_the_same_500_and_never_reruns_the_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    old_calls: list[str] = []
    monkeypatch.setattr(Reads, "snapshot", lambda self, *a: old_calls.append("old"))

    def failing(self: Any, *a: Any) -> Any:
        raise RuntimeError("PRIVATE-twin-failure")

    monkeypatch.setattr(Reads, "snapshot_with_media", failing)

    async def scenario(client: TestClient, rig: Rig) -> tuple[int, bytes]:
        await rig.pair(client)
        return await rig.fetch(client, rig.routes()["ro3"])

    status, body = rig.run(scenario)
    assert status == 500 and b"PRIVATE" not in body and old_calls == []
    assert json.loads(body)["error"]["code"] == "other"


# ---------------------------------------------------------------------------------------------
# Forged wrappers, sidecars, bindings and mismatched rows never mint
# ---------------------------------------------------------------------------------------------


class _Duck:
    def __init__(self, **members: Any) -> None:
        self.__dict__.update(members)


def _twin_returns(rig: Rig, mutate: Callable[[Any], Any]) -> None:
    real = Reads.snapshot_with_media

    def twin(self: Any, *a: Any) -> Any:
        return mutate(real(self, *a))

    rig.monkeypatch.setattr(Reads, "snapshot_with_media", twin)


def _forged_wrapper(result: Any) -> Any:
    return _Duck(public=result.public, sidecar=result.sidecar)


def _forged_binding(rig: Rig) -> Callable[[Any], Any]:
    def bind(sidecar: Any) -> Any:
        rig.bind_calls += 1
        return _Duck(
            sidecar=sidecar,
            ok=True,
            kind=rig.real_bind(sidecar).kind,
            accepted=(6, 4, 2),
            tip=sidecar.query_tip,
            session_id=sidecar.session_id,
        )

    return bind


def _binding_for_other_sidecar(rig: Rig) -> Callable[[Any], Any]:
    def bind(sidecar: Any) -> Any:
        rig.bind_calls += 1
        from hmp_plugin import local_media_sidecar as sc

        other = sc.MediaSidecar(
            status=sc.SidecarStatus.CANDIDATES,
            origin=sc.MediaOrigin.OWN_CONVERSATION,
            user_id=sidecar.user_id,
            profile=sidecar.profile,
            session_id=sidecar.session_id,
            query_tip=sidecar.query_tip,
            lineage_tip=sidecar.lineage_tip,
            candidates=sidecar.candidates,
        )
        return rig.real_bind(other)  # an honest binding, but for a different sidecar object

    return bind


@pytest.mark.parametrize(
    "case",
    ["forged_wrapper", "forged_binding", "binding_for_other_sidecar", "other_user_sidecar"],
)
def test_forged_wrappers_sidecars_and_bindings_mint_nothing(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)

    def patch(rig: Rig) -> None:
        if case == "forged_wrapper":
            _twin_returns(rig, _forged_wrapper)
        elif case == "forged_binding":
            rig.native.bridge.bind_media_batch = _forged_binding(rig)  # type: ignore[method-assign]
        elif case == "binding_for_other_sidecar":
            rig.native.bridge.bind_media_batch = _binding_for_other_sidecar(rig)  # type: ignore[method-assign]
        else:
            from hmp_plugin import local_media_sidecar as sc

            def other_user(result: Any) -> Any:
                s = result.sidecar
                moved = sc.MediaSidecar(
                    status=s.status,
                    origin=s.origin,
                    user_id="hmpu_" + "c" * 32,
                    profile=s.profile,
                    session_id=s.session_id,
                    query_tip=s.query_tip,
                    lineage_tip=s.lineage_tip,
                    candidates=s.candidates,
                )
                return sc.MediaReadResult(result.public, moved)

            _twin_returns(rig, other_user)

    reference, got = _after_pairing(rig, "ro3", patch)
    assert got == reference and rig.registry._audit() == 0


def test_a_foreign_wrapper_without_exact_public_text_is_a_bridge_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    _twin_returns(rig, lambda result: _Duck(public={"messages": []}, sidecar=result.sidecar))

    async def scenario(client: TestClient, rig: Rig) -> tuple[int, bytes]:
        await rig.pair(client)
        return await rig.fetch(client, rig.routes()["ro3"])

    status, body = rig.run(scenario)
    assert status == 500 and json.loads(body)["error"]["code"] == "other"
    assert rig.registry._audit() == 0


def test_an_accepted_row_that_is_not_a_returned_image_tool_row_gets_no_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)

    def rename_tool(result: Any) -> Any:
        from hmp_plugin import local_media_sidecar as sc

        public = result.public
        messages = tuple(
            dataclasses.replace(m, tool_name="web_search") if m.id == 4 else m
            for m in public.messages
        )
        return sc.MediaReadResult(dataclasses.replace(public, messages=messages), result.sidecar)

    _twin_returns(rig, rename_tool)

    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        assert status == 200
        return body

    body = rig.run(scenario)
    assert set(media_of(body)) == {6, 2}
    assert rig.registry._audit() == 2


def test_assistant_media_text_other_tools_and_user_rows_never_get_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch, extra_rows=True)

    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        assert status == 200
        return body

    body = rig.run(scenario)
    messages = json.loads(body)["messages"]
    with_media = {m["id"] for m in messages if "media" in m}
    assert with_media == set(EXPECTED_IDS)
    for m in messages:
        if m["role"] != "tool" or m.get("tool_name") != "image_generate":
            assert "media" not in m
    assert rig.registry._audit() == 3


def test_one_failed_candidate_mints_none_for_itself_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    real_mint = rig.registry.mint

    def flaky(binding: Any) -> str:
        if binding.tool_row_id == 4:
            raise real_registry.RegistryRefusal
        return real_mint(binding)  # type: ignore[no-any-return]

    rig.registry.mint = flaky

    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        assert status == 200
        return body

    body = rig.run(scenario)
    assert set(media_of(body)) == {6, 2}


# ---------------------------------------------------------------------------------------------
# No file access at mint; no await between the final recheck and the mint
# ---------------------------------------------------------------------------------------------


def test_mint_touches_no_image_or_home_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import builtins
    import io

    rig = Rig(tmp_path, monkeypatch)
    touched: list[str] = []

    def watch(owner: Any, name: str) -> None:
        real = getattr(owner, name)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if args and ("cache/images" in str(args[0]) or str(rig.native.home) in str(args[0])):
                touched.append(str(args[0]).removeprefix(str(rig.native.home)))
            return real(*args, **kwargs)

        monkeypatch.setattr(owner, name, wrapper)

    for owner, name in (
        (builtins, "open"),
        (io, "open"),
        (os, "stat"),
        (os, "lstat"),
        (os, "listdir"),
        (os, "scandir"),
        (os, "open"),
        (Path, "stat"),
        (Path, "exists"),
        (Path, "is_file"),
        (Path, "resolve"),
        (Path, "read_bytes"),
    ):
        watch(owner, name)

    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        assert status == 200
        return body

    body = rig.run(scenario)
    # Only the bridge's existing database-file check (`state.db`) is permitted; no image path, no
    # `cache/images` directory and no other home file is ever stat'ed, opened or listed.
    assert len(media_of(body)) == 3
    assert touched and set(touched) == {"/state.db"}


def _await_free(source: str, names: set[str]) -> dict[str, bool]:
    tree = ast.parse(source)
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            found[node.name] = not any(isinstance(n, ast.Await) for n in ast.walk(node))
    return found


def test_the_final_recheck_and_mint_sections_contain_no_await() -> None:
    emission = (PACKAGE / "media_emission.py").read_text(encoding="utf-8")
    checked = {"_select", "_emit", "_mint", "_mint_one", "_bind", "_fallback_public"}
    assert _await_free(emission, checked) == dict.fromkeys(checked, True)
    ctx_src = (PACKAGE / "request_ctx.py").read_text(encoding="utf-8")
    assert _await_free(ctx_src, {"media_snapshot", "is_media_available"}) == {
        "media_snapshot": True,
        "is_media_available": True,
    }
    # the one `await` in `read` is the thread hop; `_emit` runs right after it on the loop
    tree = ast.parse(emission)
    read = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "read")
    awaits = [n for n in ast.walk(read) if isinstance(n, ast.Await)]
    assert len(awaits) == 2  # old-read hop and the one media job hop; `_emit` has none
    last = read.body[-1]
    assert isinstance(last, ast.Return) and "_emit" in ast.unparse(last)


# ---------------------------------------------------------------------------------------------
# Replacement between the read and the mint, and the closure's own fence (C1)
# ---------------------------------------------------------------------------------------------


def _replace_during_bind(rig: Rig, how: str) -> None:
    real = rig.real_bind
    ctx = rig.ctx

    def swap(sidecar: Any) -> Any:
        rig.bind_calls += 1
        out = real(sidecar)
        if how == "registry_instance":
            ctx.media_registry = real_registry.LocalMediaRegistry()
        elif how == "registry_missing":
            ctx.media_registry = None
        elif how == "registry_module":
            ctx.media_registry_module = types.ModuleType("foreign_registry")
        elif how == "registry_module_missing":
            ctx.media_registry_module = None
        elif how == "outer_tuple":
            chain, reads_media = ctx.media_modules
            ctx.media_modules = (chain, reads_media)  # equal members, NOT the bound tuple
        elif how == "modules_missing":
            ctx.media_modules = None
        elif how == "bridge_cache":
            cache = rig.bridge_module._local_media_cache
            rig.bridge_module._local_media_cache = (*cache,)  # equal members, a new tuple object
        elif how == "reads_cache":
            cache = rig.reads_module._local_media_cache
            rig.reads_module._local_media_cache = (*cache,)  # equal members, a new tuple object
        return out

    rig.native.bridge.bind_media_batch = swap  # type: ignore[method-assign]


@pytest.mark.parametrize(
    "how",
    [
        "registry_instance",
        "registry_missing",
        "registry_module",
        "registry_module_missing",
        "outer_tuple",
        "modules_missing",
        "bridge_cache",
        "reads_cache",
    ],
)
def test_replacing_a_bound_object_between_read_and_mint_closes_only_this_listener(
    how: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    original = {
        "bridge": rig.bridge_module._local_media_cache,
        "reads": rig.reads_module._local_media_cache,
    }

    async def scenario(client: TestClient, rig: Rig) -> tuple[bytes, bytes, bytes]:
        await rig.pair(client)
        rig.flag = False
        reference = await _baseline_bytes(client, rig, "ro3")
        rig.flag = True
        _replace_during_bind(rig, how)
        with caplog.at_level(logging.INFO):
            first = await _baseline_bytes(client, rig, "ro3")
        # the listener stays closed for later requests, whatever is put back
        rig.bridge_module._local_media_cache = original["bridge"]
        rig.reads_module._local_media_cache = original["reads"]
        second = await _baseline_bytes(client, rig, "ro3")
        return reference, first, second

    reference, first, second = rig.run(scenario)
    assert first == reference and second == reference
    assert rig.registry._audit() == 0
    assert "media_binding_changed" in caplog.text
    assert "foreign_registry" not in caplog.text
    assert rig.ctx.media_modules is None
    assert rig.ctx.media_registry is None and rig.ctx.media_registry_module is None


@pytest.mark.parametrize(
    "late", ["flag_off", "flag_truthy", "owner_removed", "availability_closed"]
)
def test_a_gate_change_between_read_and_mint_mints_nothing(
    late: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    real = rig.real_bind

    def flip(sidecar: Any) -> Any:
        rig.bind_calls += 1
        out = real(sidecar)
        if late == "flag_off":
            rig.flag = False
        elif late == "flag_truthy":
            rig.ctx.media_flag = lambda: 1
        elif late == "owner_removed":
            rig.owners.clear()
        else:
            rig.ctx.media_available = lambda: False
        return out

    rig.native.bridge.bind_media_batch = flip  # type: ignore[method-assign]

    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        rig.flag = False
        reference = await _baseline_bytes(client, rig, "ro3")
        rig.flag = True
        got = await _baseline_bytes(client, rig, "ro3")
        assert got == reference
        return got

    rig.run(scenario)
    assert rig.registry._audit() == 0


def test_a_fresh_listener_gets_its_own_registry_and_whole_package_eviction_keeps_the_old(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    for key in [k for k in sys.modules if k.startswith("hmp_plugin.local_media_")] + [
        "hmp_plugin.bridge",
        "hmp_plugin.reads",
    ]:
        monkeypatch.delitem(sys.modules, key, raising=False)  # what a loader eviction does
    bound_before = (rig.ctx.media_modules, rig.ctx.media_registry_module, rig.ctx.media_registry)

    async def scenario(client: TestClient, rig: Rig) -> bytes:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        assert status == 200
        return body

    body = rig.run(scenario)
    assert set(media_of(body)) == set(EXPECTED_IDS)  # the old listener still mints
    assert (rig.ctx.media_modules, rig.ctx.media_registry_module, rig.ctx.media_registry) == (
        bound_before
    )
    assert all(
        a is b
        for a, b in zip(
            (rig.ctx.media_modules, rig.ctx.media_registry_module, rig.ctx.media_registry),
            bound_before,
            strict=True,
        )
    )
    other = hmp_kit.Env(tmp_path / "second").ctx
    other.bridge, other.reads = rig.native.bridge, rig.reads
    other.media_available = rig.adapter._media_bind(other, rig.bridge_module, rig.reads_module)
    assert other.media_registry is not None
    assert other.media_registry is not rig.ctx.media_registry  # independent per listener
    assert other.media_registry._audit() == 0
    snapshot = other.media_snapshot()
    assert snapshot is not None and snapshot.registry is other.media_registry


def test_the_snapshot_accessor_returns_the_exact_bound_objects_or_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch)
    ctx = rig.ctx
    snap = ctx.media_snapshot()
    assert snap is not None
    assert snap.bound is ctx.media_modules and snap.registry is ctx.media_registry
    assert snap.registry_module is ctx.media_registry_module
    assert snap.chain is ctx.media_modules[0] and snap.reads_media is ctx.media_modules[1]
    assert snap.same_as(ctx.media_snapshot())  # type: ignore[arg-type]
    assert repr(snap) == "MediaBound()"
    ctx.media_registry = object()  # foreign: the closure fences it and closes the listener
    assert ctx.media_snapshot() is None and ctx.is_media_available() is False
    # the default context binds nothing
    bare = hmp_kit.Env(tmp_path / "bare").ctx
    assert bare.media_snapshot() is None
    bare.media_available = lambda: True  # open, but with nothing bound: still None
    assert bare.media_snapshot() is None


# ---------------------------------------------------------------------------------------------
# Listener-open binding of the registry (adapter): proofs, independence, no start-up import
# ---------------------------------------------------------------------------------------------


def test_the_registry_is_bound_at_open_only_and_closed_listeners_import_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    closed = PackageWorld(tmp_path, monkeypatch, label="c", features=("read",))
    _, ctx = closed.open()
    assert ctx.media_registry is None and ctx.media_registry_module is None
    assert f"{closed.pkg}.local_media_registry" not in sys.modules
    other_dir = tmp_path / "o"
    other_dir.mkdir()
    opened = PackageWorld(other_dir, monkeypatch, label="o")
    _, octx = opened.open()
    module = opened.mod("local_media_registry")
    assert octx.media_registry_module is module
    assert type(octx.media_registry) is module.LocalMediaRegistry
    assert octx.media_snapshot() is not None


_FOREIGN_FUNCTION = (
    "\nimport json as _foreign\nLocalMediaRegistry.{name} = _foreign.dumps  # a foreign function\n"
)


@pytest.mark.parametrize("name", ["mint", "lookup", "record_first_served", "__init__"])
def test_a_registry_function_from_another_namespace_closes_the_listener(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = "            return total\n"
    edits = {"local_media_registry.py": [(anchor, anchor + _FOREIGN_FUNCTION.format(name=name))]}
    world = PackageWorld(tmp_path, monkeypatch, label="f", edits=edits)
    _, ctx = world.open()
    assert ctx.media_registry is None and ctx.media_registry_module is None
    assert ctx.is_media_available() is False and ctx.media_snapshot() is None


def _fence_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drop: str | None, label: str
) -> Any:
    edits = None
    if drop is not None:
        edits = {"adapter.py": [(drop, "")]}
    world = PackageWorld(tmp_path, monkeypatch, label=label, edits=edits)
    return world.open()[1]


_CONJUNCTS = {
    "outer": "                and ctx.media_modules is bound\n",
    "module": "                and ctx.media_registry_module is registry_module\n",
    "instance": "                and ctx.media_registry is registry\n",
}


def _swap(ctx: Any, which: str) -> None:
    if which == "outer":
        chain, reads_media = ctx.media_modules
        ctx.media_modules = (chain, reads_media)
    elif which == "module":
        ctx.media_registry_module = types.ModuleType("foreign")
    else:
        ctx.media_registry = object()


@pytest.mark.parametrize("which", sorted(_CONJUNCTS))
def test_each_new_fence_conjunct_is_causal(
    which: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_dir, mutant_dir = tmp_path / "r", tmp_path / "m"
    real_dir.mkdir()
    mutant_dir.mkdir()
    real = _fence_world(real_dir, monkeypatch, None, "r")
    assert real.is_media_available() is True
    _swap(real, which)
    assert real.is_media_available() is False and real.media_snapshot() is None
    mutant = _fence_world(mutant_dir, monkeypatch, _CONJUNCTS[which], "m")
    _swap(mutant, which)
    assert mutant.is_media_available() is True  # without the conjunct the swap is not noticed


# ---------------------------------------------------------------------------------------------
# Causal mutants of `media_emission`: one omitted line each, and the scenario must notice
# ---------------------------------------------------------------------------------------------


def _mutant_module(old: str, new: str, tag: str) -> types.ModuleType:
    source = (PACKAGE / "media_emission.py").read_text(encoding="utf-8")
    assert source.count(old) == 1, old
    module = types.ModuleType(f"hmp_plugin.media_emission_{tag}")
    module.__package__ = "hmp_plugin"
    module.__file__ = str(PACKAGE / "media_emission.py")
    exec(compile(source.replace(old, new), module.__file__, "exec"), module.__dict__)  # noqa: S102
    return module


def _scenario_owner_removed_during_bind(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    rig = Rig(tmp_path, mp)
    real = rig.real_bind

    def flip(sidecar: Any) -> Any:
        out = real(sidecar)
        rig.owners.clear()
        return out

    rig.native.bridge.bind_media_batch = flip  # type: ignore[method-assign]

    async def scenario(client: TestClient, rig: Rig) -> bool:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        return status == 200 and media_of(body) == {} and rig.registry._audit() == 0

    return bool(rig.run(scenario))


def _scenario_flag_off_during_bind(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    rig = Rig(tmp_path, mp)
    real = rig.real_bind

    def flip(sidecar: Any) -> Any:
        out = real(sidecar)
        rig.flag = False
        return out

    rig.native.bridge.bind_media_batch = flip  # type: ignore[method-assign]

    async def scenario(client: TestClient, rig: Rig) -> bool:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        return status == 200 and media_of(body) == {} and rig.registry._audit() == 0

    return bool(rig.run(scenario))


def _scenario_forged_binding(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    rig = Rig(tmp_path, mp)
    rig.native.bridge.bind_media_batch = _forged_binding(rig)  # type: ignore[method-assign]

    async def scenario(client: TestClient, rig: Rig) -> bool:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        return status == 200 and media_of(body) == {} and rig.registry._audit() == 0

    return bool(rig.run(scenario))


def _scenario_binding_for_other_sidecar(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    rig = Rig(tmp_path, mp)
    rig.native.bridge.bind_media_batch = _binding_for_other_sidecar(rig)  # type: ignore[method-assign]

    async def scenario(client: TestClient, rig: Rig) -> bool:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        return status == 200 and media_of(body) == {} and rig.registry._audit() == 0

    return bool(rig.run(scenario))


def _scenario_non_owner_never_reads_media(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    rig = Rig(tmp_path, mp)
    _spy_twins(rig)

    async def scenario(client: TestClient, rig: Rig) -> bool:
        await rig.pair(client, owner=False)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        return (
            status == 200
            and media_of(body) == {}
            and rig.twin_calls == []
            and rig.bind_calls == 0
            and rig.registry._audit() == 0
        )

    return bool(rig.run(scenario))


def _scenario_user_mismatch_sidecar(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    rig = Rig(tmp_path, mp)
    real_bind = rig.real_bind
    calls = []

    def other(sidecar: Any) -> Any:
        calls.append(1)
        return real_bind(sidecar)

    rig.native.bridge.bind_media_batch = other  # type: ignore[method-assign]
    from hmp_plugin import local_media_sidecar as sc

    real_twin = Reads.snapshot_with_media

    def twin(self: Any, *a: Any) -> Any:
        result = real_twin(self, *a)
        s = result.sidecar
        moved = sc.MediaSidecar(
            status=s.status,
            origin=s.origin,
            user_id="hmpu_" + "c" * 32,
            profile=s.profile,
            session_id=s.session_id,
            query_tip=s.query_tip,
            lineage_tip=s.lineage_tip,
            candidates=s.candidates,
        )
        return sc.MediaReadResult(result.public, moved)

    mp.setattr(Reads, "snapshot_with_media", twin)

    async def scenario(client: TestClient, rig: Rig) -> bool:
        await rig.pair(client)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        return status == 200 and media_of(body) == {} and calls == []

    return bool(rig.run(scenario))


# -- follow-up review T1: a failure in the mint section OUTSIDE the per-candidate catch ----------


def _outer_mint_failure_facts(tmp_path: Path, mp: pytest.MonkeyPatch) -> dict[str, Any]:
    """Make the real `_mint` itself raise (not one candidate's `registry.mint`): the listener's
    bound registry module loses its `SessionKind`, which `_mint` uses for every response, after the
    final gate recheck and before any candidate. The real code must still answer 200 with the exact
    text, run no second read and mint nothing."""
    rig = Rig(tmp_path, mp)
    old_calls: list[str] = []
    real_old = Reads.snapshot

    def old_spy(self: Any, *a: Any) -> Any:
        old_calls.append("old")
        return real_old(self, *a)

    mp.setattr(Reads, "snapshot", old_spy)

    async def scenario(client: TestClient, rig: Rig) -> dict[str, Any]:
        await rig.pair(client)
        rig.flag = False
        _, reference = await rig.fetch(client, rig.routes()["ro3"])
        rig.flag = True
        rig.bind_calls = 0
        old_calls.clear()
        mp.setattr(rig.ctx.media_registry_module, "SessionKind", None)
        status, body = await rig.fetch(client, rig.routes()["ro3"])
        return {"reference": reference, "status": status, "body": body}

    facts: dict[str, Any] = rig.run(scenario)
    facts.update(old_calls=list(old_calls), binds=rig.bind_calls, audit=rig.registry._audit())
    return facts


def _outer_mint_failure_problems(facts: dict[str, Any]) -> list[str]:
    problems = []
    if facts["status"] != 200:
        problems.append(f"status {facts['status']}")
    if facts["body"] != facts["reference"]:
        problems.append("text differs from the closed bytes")
    if facts["old_calls"]:
        problems.append("the read was rerun")
    if facts["binds"] != 1:
        problems.append("not exactly one batch")
    if facts["audit"] != 0:
        problems.append("a ref was minted")
    return problems


def _scenario_outer_mint_failure(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    return not _outer_mint_failure_problems(_outer_mint_failure_facts(tmp_path, mp))


# -- follow-up review T3: the twin and the batch share one worker thread and one copied context ---

_ALL_TWINS = (
    "snapshot_with_media",
    "history_with_media",
    "session_snapshot_with_media",
    "session_history_with_media",
)


def _thread_context_facts(tmp_path: Path, mp: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """For every route: the thread and `ContextVar` value the twin and the batch each observe. The
    value is set on the loop inside the request (by the flag read that selects the media path), so
    only a copied context can carry it into the worker."""
    rig = Rig(tmp_path, mp)
    var: contextvars.ContextVar[str] = contextvars.ContextVar("s4_probe", default="unset")
    current = {"route": ""}
    seen: list[tuple[str, int, str]] = []

    def flag() -> bool:
        var.set(current["route"])
        return True

    rig.ctx.media_flag = flag
    for name in _ALL_TWINS:

        def make(real: Callable[..., Any], label: str) -> Callable[..., Any]:
            def spy(self: Any, *a: Any, **k: Any) -> Any:
                seen.append((label, threading.get_ident(), var.get()))
                return real(self, *a, **k)

            return spy

        mp.setattr(Reads, name, make(getattr(Reads, name), "twin"))
    inner = rig.native.bridge.bind_media_batch

    def bind_spy(sidecar: Any) -> Any:
        seen.append(("bind", threading.get_ident(), var.get()))
        return inner(sidecar)

    rig.native.bridge.bind_media_batch = bind_spy  # type: ignore[method-assign]

    async def scenario(client: TestClient, rig: Rig) -> list[dict[str, Any]]:
        loop_thread = threading.get_ident()
        await rig.pair(client)
        out = []
        for route, path in rig.routes().items():
            current["route"] = route
            seen.clear()
            status, body = await rig.fetch(client, path)
            out.append(
                {
                    "route": route,
                    "status": status,
                    "media": len(media_of(body)),
                    "events": list(seen),
                    "loop_thread": loop_thread,
                }
            )
        return out

    facts: list[dict[str, Any]] = rig.run(scenario)
    return facts


def _thread_context_problems(facts: list[dict[str, Any]]) -> list[str]:
    problems = []
    for row in facts:
        route, events = row["route"], row["events"]
        if row["status"] != 200 or row["media"] != 3:
            problems.append(f"{route}: no descriptors")
        if [e[0] for e in events] != ["twin", "bind"]:
            problems.append(f"{route}: not one twin then one batch")
            continue
        (_, twin_thread, twin_value), (_, bind_thread, bind_value) = events
        if twin_thread != bind_thread:
            problems.append(f"{route}: different worker threads")
        if twin_thread == row["loop_thread"]:
            problems.append(f"{route}: ran on the event loop thread")
        if twin_value != route or bind_value != route:
            problems.append(f"{route}: the request ContextVar was not copied")
    return problems


def _scenario_thread_context(tmp_path: Path, mp: pytest.MonkeyPatch) -> bool:
    return not _thread_context_problems(_thread_context_facts(tmp_path, mp))


MUTANTS = {
    "owner_recheck": (
        "    if not ctx.is_approval_owner_device(who.device_id) or not ctx.media_enabled():\n"
        "        return {}\n    final",
        "    final",
        _scenario_owner_removed_during_bind,
    ),
    "flag_recheck": (
        "    if not ctx.is_approval_owner_device(who.device_id) or not ctx.media_enabled():\n"
        "        return {}\n    final",
        "    if not ctx.is_approval_owner_device(who.device_id):\n        return {}\n    final",
        _scenario_flag_off_during_bind,
    ),
    "binding_type": (
        "    if type(binding) is not binding_module.MediaBatchBinding:\n        return {}\n",
        "",
        _scenario_forged_binding,
    ),
    "binding_sidecar_identity": (
        "    if binding.sidecar is not sidecar or not binding.ok:\n",
        "    if not binding.ok:\n",
        _scenario_binding_for_other_sidecar,
    ),
    "initial_selection": (
        "        bound is None\n        or twin is None",
        "        twin is None",
        _scenario_non_owner_never_reads_media,
    ),
    "bind_user_check": (
        "    if sidecar.user_id != user_id or sidecar.profile != profile:\n        return None\n",
        "",
        _scenario_user_mismatch_sidecar,
    ),
    "emit_outer_catch": (
        "    except Exception:  # optional boundary: exactly the successful text\n"
        "        return public",
        "    except KeyboardInterrupt:  # mutant: no outer catch\n        return public",
        _scenario_outer_mint_failure,
    ),
    "job_copies_context": (
        "    got, binding = await asyncio.to_thread(job)",
        "    got, binding = await asyncio.get_running_loop().run_in_executor(None, job)",
        _scenario_thread_context,
    ),
}


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_each_emission_guard_is_causal(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, new, scenario = MUTANTS[name]
    (tmp_path / "real").mkdir()
    (tmp_path / "mut").mkdir()
    assert scenario(tmp_path / "real", monkeypatch) is True  # the real code holds the property
    monkeypatch.setattr(server, "media_emission", _mutant_module(old, new, name))
    assert scenario(tmp_path / "mut", monkeypatch) is False, name  # the mutant breaks it


def test_an_unexpected_failure_in_the_mint_section_keeps_the_exact_text_and_is_not_reread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts = _outer_mint_failure_facts(tmp_path, monkeypatch)
    assert facts["status"] == 200 and b'"media"' not in facts["body"]
    assert _outer_mint_failure_problems(facts) == []


@pytest.mark.parametrize(
    "variant", ["visible_root", "no_canonical_title", "visible_root_and_no_title"]
)
def test_a_browsed_session_that_is_neither_own_phone_nor_canonical_bot_chat_gets_no_descriptor(
    variant: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = Rig(tmp_path, monkeypatch, kind="bot")
    sessions = rig.native.db.sessions
    if variant != "no_canonical_title":
        sessions["R"]["hidden"] = 0  # a visible root is an ordinary session
    if variant != "visible_root":
        sessions["C"]["title"] = None  # no canonical Bot Chat title anywhere on the lineage

    async def scenario(client: TestClient, rig: Rig) -> dict[str, Any]:
        await rig.pair(client)
        out: dict[str, Any] = {}
        for name in ("ses2", "ses2_paged", "ses2a"):
            path = rig.routes()[name]
            rig.flag = False
            status, reference = await rig.fetch(client, path)
            rig.flag = True
            rig.bind_calls = 0
            status2, got = await rig.fetch(client, path)
            out[name] = (status, status2, reference, got, rig.bind_calls, rig.registry._audit())
        # positive control: the same session as the canonical Bot Chat does get descriptors
        sessions["R"]["hidden"] = 1
        sessions["C"]["title"] = "Bot Chat"
        status, body = await rig.fetch(client, rig.routes()["ses2"])
        out["control"] = (status, len(media_of(body)))
        return out

    out = rig.run(scenario)
    for name in ("ses2", "ses2_paged", "ses2a"):
        status, status2, reference, got, binds, audit = out[name]
        assert status == status2 == 200, name
        assert got == reference and b'"media"' not in got, name  # the exact text, no descriptor
        assert tool_ids(got), name  # the image tool rows are still returned as text
        assert binds == 1 and audit == 0, name  # one batch, which refused; nothing minted
    assert out["control"] == (200, 3)


def test_the_twin_and_the_batch_share_one_worker_thread_and_the_copied_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts = _thread_context_facts(tmp_path, monkeypatch)
    assert [row["route"] for row in facts] == ["ro3", "ro6", "ses2", "ses2_paged", "ses2a"]
    assert _thread_context_problems(facts) == []


# ---------------------------------------------------------------------------------------------
# Contract surface, bounded sidecar delta, frozen helper bytes, layout
# ---------------------------------------------------------------------------------------------


def test_the_error_code_and_message_match_the_frozen_table() -> None:
    assert ErrorCode.MEDIA_UNAVAILABLE.value == "media_unavailable"
    assert ERROR_MESSAGES[ErrorCode.MEDIA_UNAVAILABLE] == "image delivery is unavailable"
    spec = ERROR_TABLE[ErrorCode.MEDIA_UNAVAILABLE]
    assert spec.http == frozenset({503})
    doc = (PACKAGE.parents[1] / "docs/architecture/contracts/HMP_V1.md").read_text("utf-8")
    assert 'Message: "image delivery is unavailable"' in doc and "media_unavailable" in doc


def test_the_wire_descriptor_is_exactly_kind_and_ref_and_omitted_when_absent() -> None:
    from hmp_plugin.request_ctx import _plain

    assert [f.name for f in dataclasses.fields(WireMediaDescriptor)] == ["kind", "ref"]
    plain = _plain(WireMessage(1, "tool", "x", None, 1.0))
    assert "media" not in plain
    shown = _plain(
        WireMessage(1, "tool", "x", None, 1.0, media=WireMediaDescriptor("image", "A" * 43))
    )
    assert shown["media"] == {"kind": "image", "ref": "A" * 43}
    with pytest.raises(dataclasses.FrozenInstanceError):
        WireMediaDescriptor("image", "A" * 43).ref = "B" * 43  # type: ignore[misc]


def _sha(name: str) -> str:
    return hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest()


# Captured from `git show b07890e:<file>`; the nine helper modules and the bridge and reads
# implementations are byte-identical to the base, except the bounded sidecar annotation below.
BASE_HASHES = {
    "bridge.py": "7583ae6f7f4deb0de87bbdd85d1a62639a044321e566e60bd8af8f1ddc2f38e3",
    "reads.py": "58c265587566e1e9d6c0d17726fb3907eec91baa01682ebf9c095765f19a01f3",
    "local_media_active_batch.py": (
        "b30d3bcc37e246a193d00d599855b7abcc114d1a2812d8014cb7062566948ecc"
    ),
    "local_media_active_scan.py": (
        "81eb6880f396ad3c2a244c875753887332336da4c4a2a68569f3e7c455b8b4c2"
    ),
    "local_media_batch_binding.py": (
        "3be797c07296e3bf3a98e1bfdd5bf2666cbcb3b4ada99359c3108de85e5839a8"
    ),
    "local_media_candidate.py": (
        "4656d83b6adfa1a05a068f63c68111ad2147c5ce0b76b5414ad8082d4d9789d1"
    ),
    "local_media_file_safety.py": (
        "440c3cfa5c636d5d280f4cf8876f900ab9177b0421d55a8d5503fc398973ef74"
    ),
    "local_media_raster_structure.py": (
        "f293d0c1e379d20ec5d466e9a92e9c0e6b961a2a2b7009b5aac3705410b47610"
    ),
    "local_media_registry.py": ("b49e6e6205805f38144e769f742f6e3ee918536aa6dd5f66e6c8096d8f77c2b2"),
    "local_media_result.py": ("04d011cf8b805c2b285297e18f99a4ec1691f0133320948d2680d564c29b4336"),
}


@pytest.mark.parametrize("name", sorted(set(BASE_HASHES) - {"bridge.py"}))
def test_the_reads_and_nine_helpers_are_byte_identical_to_the_base(name: str) -> None:
    assert _sha(name) == BASE_HASHES[name]


def test_the_bridge_differs_from_the_base_only_by_the_s5_additions() -> None:
    """First reverse exact approved AT1 and push additions; S5 then adds exactly the
    `hashlib` and `media_payload` module imports and the
    block of three new methods (`_media_fetch_bound`, `media_fetch_phase_one`,
    `media_fetch_phase_two`) before `lineage`. Removing precisely those pieces reproduces the base
    bytes, so every old method, the proof, `bind_media_batch` and the twins are byte-identical."""
    text = reverse_approved_push_diagnostics(reverse_approved_at1_bridge(
        (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    ))
    assert text.count("import hashlib\n") == 1
    assert text.count("from . import media_payload\n") == 1
    start = text.index("    # S5: the two off-loop native phases")
    end = text.index("    def lineage(self, ref: ConversationRef) -> LineageInfo:")
    assert start < end
    block = text[start:end]
    assert_approved_s5_block(block)
    assert [
        line.strip().split("(")[0]
        for line in block.splitlines()
        if line.startswith("    def ")
    ] == ["def _media_fetch_bound", "def media_fetch_phase_one", "def media_fetch_phase_two"]
    base = text[:start] + text[end:]
    base = base.replace("import hashlib\n", "", 1).replace("from . import media_payload\n", "", 1)
    assert hashlib.sha256(base.encode()).hexdigest() == BASE_HASHES["bridge.py"]


def test_composed_bridge_witness_rejects_a_media_guard_mutation() -> None:
    text = reverse_approved_push_diagnostics(reverse_approved_at1_bridge(
        (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    ))
    start = text.index("    # S5: the two off-loop native phases")
    end = text.index("    def lineage(self, ref: ConversationRef) -> LineageInfo:", start)
    block = text[start:end]
    assert_approved_s5_block(block)
    guard = "        if type(registry_module) is not ModuleType or type(chain) is not tuple:\n"
    assert block.count(guard) == 1
    mutant = block.replace(guard, "        if False:\n", 1)
    assert mutant != block
    with pytest.raises(AssertionError):
        assert_approved_s5_block(mutant)


def test_the_sidecar_delta_is_exactly_the_protocol_annotation() -> None:
    """Reversing the two bounded edits reproduces the base bytes (sha256 below)."""
    text = (PACKAGE / "local_media_sidecar.py").read_text(encoding="utf-8")
    new_doc = (
        "    `ReadBridge` itself is unchanged. S4 calls these through `Reads` and "
        "`bind_media_batch` through\n    the descriptor routes. A bridge that cannot represent "
        "the query metadata (or a page over\n    `MAX_ROWS`) returns the exact old text-row list "
        "instead.\n"
    )
    old_doc = (
        "    `ReadBridge` itself is unchanged. The methods have no caller yet. A bridge that "
        "cannot represent\n    the query metadata (or a page over `MAX_ROWS`) returns the exact "
        "old text-row list instead.\n"
    )
    tail = "\n    def bind_media_batch(self, sidecar: MediaSidecar) -> object | None: ...\n"
    assert text.count(new_doc) == 1 and text.endswith(tail)
    base = text.replace(new_doc, old_doc)[: -len(tail)]
    assert hashlib.sha256(base.encode()).hexdigest() == (
        "e3872f8f013fc51f9e4f682d3ad96024817aa1585075433ede980649857410bf"
    )


def test_media_emission_imports_no_local_media_and_the_adapter_only_registry_and_raster() -> None:
    emission = ast.parse((PACKAGE / "media_emission.py").read_text(encoding="utf-8"))
    for node in ast.walk(emission):
        if isinstance(node, ast.ImportFrom | ast.Import):
            assert "local_media" not in ast.unparse(node)
    adapter_src = (PACKAGE / "adapter.py").read_text(encoding="utf-8")
    tree = ast.parse(adapter_src)
    owners = {}
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef):
            for node in ast.walk(fn):
                if isinstance(node, ast.ImportFrom) and "local_media" in ast.unparse(node):
                    owners.setdefault(fn.name, []).append(ast.unparse(node))
    assert owners == {
        "_media_registry_bind": ["from . import local_media_registry"],
        "_media_raster_bind": ["from . import local_media_raster_structure"],
    }


def test_the_registry_bind_function_has_no_await_sys_modules_or_file_access() -> None:
    tree = ast.parse((PACKAGE / "adapter.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree) if getattr(n, "name", "") == "_media_registry_bind")
    for node in ast.walk(fn):
        assert not isinstance(node, ast.Await)
        label = node.id if isinstance(node, ast.Name) else getattr(node, "attr", None)
        assert label not in {"importlib", "__import__", "import_module", "sys", "modules"}
        assert label not in {"open", "os", "Path", "stat", "read_text"}


@pytest.mark.parametrize("damage", ["body", "import", "duplicate", "relocate", "site"])
def test_exact_at1_bridge_restoration_refuses_every_changed_addition(damage: str) -> None:
    original = (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    block = APPROVED_AT1_BRIDGE_BLOCK
    assert original.count(block) == 1
    if damage == "body":
        changed = block.replace("type(value) is not str", "type(value) is not bytes", 1)
        assert changed != block
        mutant = original.replace(block, changed, 1)
    elif damage == "import":
        mutant = original.replace("    ApprovalTestTarget,\n",
                                  "    ApprovalTestTarget as OtherTarget,\n", 1)
    elif damage == "duplicate":
        mutant = original.replace(block, block + block, 1)
    elif damage == "relocate":
        mutant = original.replace(block, "", 1) + block
    else:
        mutant = original.replace(block, "    # displaced site\n" + block, 1)
    assert mutant != original
    with pytest.raises(AssertionError):
        reverse_approved_at1_bridge(mutant)


def test_at1_restoration_retains_the_entire_approved_pre_at1_bridge() -> None:
    original = (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    restored = reverse_approved_at1_bridge(original)
    assert hashlib.sha256(restored.encode()).hexdigest() == APPROVED_PRE_AT1_BRIDGE_SHA256


def test_at1_restoration_does_not_mask_an_old_bridge_method_change() -> None:
    original = (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    line = "    def resolve_bot_chat(self, profile: str) -> BotChatTarget | None:\n"
    assert original.count(line) == 1
    mutant = original.replace(line, line + "        raise RuntimeError('causal mutation')\n", 1)
    assert mutant != original
    restored = reverse_approved_at1_bridge(mutant)
    with pytest.raises(AssertionError):
        assert hashlib.sha256(restored.encode()).hexdigest() == APPROVED_PRE_AT1_BRIDGE_SHA256

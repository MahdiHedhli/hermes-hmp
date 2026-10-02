"""Causal regressions for independent S5 review F1/F2/F3.

Real authenticated routes use the accepted native fixture, real bridge phases, scanner, file
leaf and registry. No canned phase payloads authorize media. Namespace mutations affect only
isolated package copies; live Hermes homes, networks, accounts and devices are not used.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import threading
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import local_media_registry as registry

from .media_binding_world import World as PackageWorld
from .test_local_media_batch_binding import USER, session_row
from .test_s4_descriptors import PROFILE
from .test_s5_media_fetch import NOT_FOUND, PACKAGE, RATE_LIMITED, VALID_PNG, Fx, until


@pytest.mark.parametrize("kind", ["phone", "bot"])
def test_foreign_genuine_kind_ref_is_refused_by_phase_one(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch, kind=kind)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[6]) == VALID_PNG
        entry = fx.registry.lookup(
            refs[6], registry.Caller(dev.device_id, USER, fx.ctx.iid, PROFILE)
        )
        assert entry is not None
        other_kind = (
            registry.SessionKind.BOT_CHAT if kind == "phone" else registry.SessionKind.PHONE
        )
        forged = fx.registry.mint(dataclasses.replace(entry.binding, kind=other_kind))
        assert forged != refs[6]
        await fx.refused(client, forged)
        assert fx.p1_in == 2 and fx.p2_in == 1
        assert fx.p1_results == ["MediaPayload", "NoneType"]

    fx.run(scenario)


def test_grant_revoked_after_initial_gate_but_before_phase_one_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[4]) == VALID_PNG
        fx.p1_gate = threading.Event()
        pending = asyncio.create_task(fx.get(client, refs[6]))
        await until(lambda: fx.p1_in == 2)  # initial grant succeeded and the real worker started
        fx.native.world.runner.approved[PROFILE].discard(USER)
        fx.p1_gate.set()
        status, _headers, body = await pending
        assert (status, json.loads(body)) == (404, NOT_FOUND)
        assert fx.p1_results == ["MediaPayload", "NoneType"] and fx.p2_in == 1
        await until(lambda: fx.service.stats() == (0, 0, 0))

    fx.run(scenario)


def _change_kind(fx: Fx) -> None:
    # Canonical Bot Chat stops proving, while the exact same root/tip proves as own Phone.
    fx.native.db.sessions["R"]["hidden"] = 0
    fx.native.bind_store("R")


def _ambiguous(fx: Fx) -> None:
    fx.native.bind_store("R")  # both the canonical Bot Chat and own Phone now prove


def _uncertain(fx: Fx) -> None:
    fx.native.db.sessions["R"]["hidden"] = True  # bool is not the required exact int


def _phone_replaced(fx: Fx) -> None:
    fx.native.db.sessions["replacement"] = session_row("replacement")
    fx.native.bind_store("replacement")


FACTS = {
    "kind_changed": ("bot", _change_kind),
    "ambiguous_kind": ("bot", _ambiguous),
    "uncertain_kind": ("bot", _uncertain),
    "phone_replaced": ("phone", _phone_replaced),
}


@pytest.mark.parametrize("phase", ["one", "two"])
@pytest.mark.parametrize("fact", sorted(FACTS))
def test_full_kind_and_phone_proof_refuses_changed_native_facts_in_each_phase(
    phase: str, fact: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kind, flip = FACTS[fact]
    fx = Fx(tmp_path, monkeypatch, kind=kind)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[4]) == VALID_PNG
        if phase == "one":
            fx.p1_gate = threading.Event()
            pending = asyncio.create_task(fx.get(client, refs[6]))
            await until(lambda: fx.p1_in == 2)
            flip(fx)
            fx.p1_gate.set()
            status, _headers, body = await pending
            assert (status, json.loads(body)) == (404, NOT_FOUND)
            assert fx.p1_results == ["MediaPayload", "NoneType"] and fx.p2_in == 1
        else:
            fx.before_p2.append(lambda: flip(fx))
            await fx.refused(client, refs[6])
            assert fx.p1_results == ["MediaPayload", "MediaPayload"] and fx.p2_in == 2
        await until(lambda: fx.service.stats() == (0, 0, 0))

    fx.run(scenario)


@pytest.mark.parametrize(
    ("state", "status", "error"),
    [
        ("pending_operator", 403, {
            "code": "forbidden", "message": "forbidden", "authz": "pending_operator",
        }),
        ("refused_allow_all_transport", 403, {
            "code": "forbidden", "message": "forbidden", "authz": "refused_allow_all",
        }),
        ("refused_allow_all_profile", 403, {
            "code": "forbidden", "message": "forbidden", "authz": "refused_allow_all",
        }),
        ("not_routed", 409, {
            "code": "not_routed", "message": "bot is not served by this instance",
            "authz": "not_routed",
        }),
        ("not_served", 409, {
            "code": "not_routed", "message": "bot is not served by this instance",
            "authz": "not_served",
        }),
        ("unverifiable", 503, {
            "code": "other", "message": "request refused", "authz": "unverifiable",
            "why": "unverifiable",
        }),
    ],
)
def test_every_initial_err3_mapping_is_exact_and_precedes_the_closed_media_gate(
    state: str, status: int, error: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[4]) == VALID_PNG
        runner = fx.native.world.runner
        profile = PROFILE
        if state == "pending_operator":
            runner.approved[PROFILE].discard(USER)
        elif state == "refused_allow_all_transport":
            runner.allow_all_transport = True
        elif state == "refused_allow_all_profile":
            runner.allow_all_routed = {PROFILE}
        elif state == "unverifiable":
            runner.authz_raises = True
        else:
            profile = "lonely" if state == "not_routed" else "ghost"
        fx.rig.flag = False
        got, _headers, body = await fx.get(client, refs[6], profile=profile)
        assert (got, json.loads(body)) == (status, {"error": error})
        assert fx.p1_in == 1 and fx.p2_in == 1  # only the positive control submitted any phase

    fx.run(scenario)


def test_cancelled_phase_two_holds_actual_worker_and_buffer_until_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.p2_gate = threading.Event()
        victim = asyncio.create_task(fx.get(client, refs[6]))
        await until(lambda: fx.p2_in == 1 and len(fx.starts) == 2)
        handler = fx.tasks[-1]
        lease, _, future = fx.starts[-1]
        handler.cancel()
        await asyncio.gather(victim, return_exceptions=True)
        await until(lambda: handler.done())
        assert lease._finished and lease._payload is None
        assert fx.service.stats() == (1, 1, 1)
        assert not future.cancelled() and not future.done()
        second = asyncio.create_task(fx.get(client, refs[4]))
        await until(lambda: fx.p2_in == 2)
        status, _headers, body = await fx.get(client, refs[2])
        assert (status, json.loads(body)) == (429, RATE_LIMITED)
        fx.p2_gate.set()
        assert (await second)[0] == 200
        await until(lambda: fx.service.stats() == (0, 0, 0))
        assert future.result(5) is True  # actual native check finished; no late stream followed
        assert lease._released and lease._payload is None
        assert await fx.served(client, refs[6]) == VALID_PNG  # cancellation never recorded a CAS

    fx.run(scenario)


SPLITS = [
    ("media_fetch.py", name, None)
    for name in ("_abort", "_shaped_badly", "_not_started", "_not_found", "close_service")
] + [
    ("media_fetch.py", "MediaFetchService", "closed"),
    ("media_fetch.py", "_Lease", "__init__"),
    ("media_fetch.py", "MediaServiceRefusal", "__init__"),
    *[("media_payload.py", "MediaPayload", name) for name in ("data", "mime", "sha256", "size")],
    ("media_payload.py", "MediaPayloadRefusal", "__init__"),
    ("media_payload.py", "MediaPayload", "__setattr__"),
    ("media_payload.py", "MediaPayload", "__reduce__"),
    ("media_payload.py", "MediaPayload", "__copy__"),
]


@pytest.mark.parametrize(("filename", "name", "member"), SPLITS)
def test_foreign_orchestrator_helpers_and_private_class_accessors_close_only_that_listener(
    filename: str, name: str, member: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = (PACKAGE / filename).read_text(encoding="utf-8")
    target = name if member is None else f"{name}.{member}"
    is_property = member in ("closed", "data", "mime", "sha256", "size")
    function = f"{target}.fget" if is_property else target
    split = (
        f"\n_f = {function}\n"
        "_foreign = type(_f)(_f.__code__, dict(globals()), _f.__name__, "
        "_f.__defaults__, _f.__closure__)\n"
        f"{target} = " + ("property(_foreign)\n" if is_property else "_foreign\n")
    )
    broken_dir, good_dir = tmp_path / "broken", tmp_path / "good"
    broken_dir.mkdir()
    good_dir.mkdir()
    _, broken = PackageWorld(
        broken_dir, monkeypatch, label="split", edits={filename: [(source, source + split)]}
    ).open()
    assert not broken.is_media_available() and broken.media_snapshot() is None
    assert broken.media_fetch_module is None and broken.media_payload_module is None
    assert broken.media_registry is None
    _, good = PackageWorld(good_dir, monkeypatch, label="coherent").open()
    assert good.is_media_available() and good.media_snapshot() is not None


def test_new_module_helper_is_also_in_the_namespace_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = (PACKAGE / "media_fetch.py").read_text(encoding="utf-8")
    added = "\n_later_helper = type(_abort)(_abort.__code__, dict(globals()))\n"
    _, broken = PackageWorld(
        tmp_path, monkeypatch, label="later", edits={"media_fetch.py": [(source, source + added)]}
    ).open()
    assert not broken.is_media_available() and broken.media_snapshot() is None

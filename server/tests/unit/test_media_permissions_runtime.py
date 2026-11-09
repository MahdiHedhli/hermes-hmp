"""Independent media permissions through real descriptor/fetch fixtures; no live host."""

import argparse
import asyncio
import io
from types import SimpleNamespace

import pytest

from hmp_plugin import cli, media_operator_client, operator_read
from hmp_plugin.media_operator_protocol import MediaOperatorReply
from hmp_plugin.request_ctx import ServerContext
from hmp_plugin.store import Store

from .test_operator_read import (
    _operator_test_parent_fixture as _operator_test_parent_fixture,
)
from .test_operator_read import (
    _owned_operator_parent,
)
from .test_s5_media_fetch import Fx as FetchRig


def _decision(fx, device, allowed):
    store = fx.rig.env.store
    previous = store.media_read_decision(fx.ctx.iid, device.device_id)
    current = store.set_media_read(previous, allowed=allowed, now=fx.rig.env.clock())
    assert current is not None
    return current


def test_media_only_allow_fetches_without_approval_or_controls(tmp_path, monkeypatch):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client, owner=False)
        store = fx.rig.env.store
        store.set_owner_controls(device.device_id, allowed=False, now=fx.rig.env.clock())
        assert await fx.mint(client) == {}
        _decision(fx, device, True)
        assert not fx.ctx.is_approval_owner_device(device.device_id)
        assert not fx.ctx.is_owner_device(device.device_id)
        refs = await fx.mint(client)
        assert refs
        status, _headers, body = await fx.get(client, next(iter(refs.values())))
        assert status == 200 and body
        assert store.owner_controls_decision(device.device_id) is False
        assert device.device_id not in fx.rig.owners

    fx.run(scenario)


def test_deny_then_regrant_does_not_revive_old_references(tmp_path, monkeypatch):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client, owner=False)
        _decision(fx, device, True)
        old = next(iter((await fx.mint(client)).values()))
        _decision(fx, device, False)
        assert (await fx.get(client, old))[0] == 404
        _decision(fx, device, True)
        assert (await fx.get(client, old))[0] == 404
        new = next(iter((await fx.mint(client)).values()))
        assert new != old and (await fx.get(client, new))[0] == 200

    fx.run(scenario)


@pytest.mark.parametrize("phase", ("after_p1", "after_p2"))
def test_late_worker_result_cannot_survive_deny_regrant(tmp_path, monkeypatch, phase):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client, owner=False)
        _decision(fx, device, True)
        ref = next(iter((await fx.mint(client)).values()))

        def revoke_and_restore():
            _decision(fx, device, False)
            _decision(fx, device, True)

        getattr(fx, phase).append(revoke_and_restore)
        assert (await fx.get(client, ref))[0] == 404
        assert fx.p1_in == 1

    fx.run(scenario)


def test_explicit_media_deny_closes_legacy_owner_without_changing_other_rights(
    tmp_path,
    monkeypatch,
):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client)
        assert await fx.mint(client)
        _decision(fx, device, False)
        assert await fx.mint(client) == {}
        assert fx.ctx.is_approval_owner_device(device.device_id)
        assert fx.ctx.is_owner_device(device.device_id)

    fx.run(scenario)


def test_unversioned_legacy_owner_restore_retains_legacy_reference_behavior(tmp_path, monkeypatch):
    """Known compatibility limit: use persistent media denial for generation-safe revocation."""
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client)
        old = next(iter((await fx.mint(client)).values()))
        fx.rig.owners.remove(device.device_id)
        assert (await fx.get(client, old))[0] == 404
        fx.rig.owners.add(device.device_id)
        # A raw in-memory owner-list edit has no authoritative revision. This
        # inherited fallback behavior must not be reported as non-revival proof.
        assert (await fx.get(client, old))[0] == 200

    fx.run(scenario)


def test_operator_media_roundtrip_is_read_only_and_scoped(tmp_path):
    store = Store(tmp_path / "media.sqlite3")
    store.migrate()
    store.insert_user("user_a", "owner", 1)
    store.insert_device("dev_a", "user_a", "f" * 52, b"public", "phone", 1, state="ACTIVE")
    iid = "a" * 52
    ctx = ServerContext(SimpleNamespace(iid=iid, still_current=lambda: True), store, None)
    service = operator_read.OperatorReadService(ctx, _owned_operator_parent() / "anchor", "a" * 32)
    before = store.media_read_decision(iid, "dev_a")

    async def scenario():
        await service.start()
        try:
            reply = await asyncio.to_thread(
                operator_read.read_media_context,
                service.path,
                iid=iid,
                nonce="a" * 32,
                device_id="dev_a",
            )
            assert reply["decision"] == before._asdict()
            assert reply["effective"] is False and reply["host_enabled"] is False
        finally:
            assert await service.stop() == 0
            await service.wait_drained()

    try:
        asyncio.run(scenario())
        assert store.media_read_decision(iid, "dev_a") == before
    finally:
        store.close()


@pytest.mark.parametrize("allowed", (True, False))
def test_operator_command_confirms_and_reads_back_only_media_permission(
    tmp_path,
    monkeypatch,
    allowed,
):
    store = Store(tmp_path / "media.sqlite3")
    store.migrate()
    store.insert_user("user_a", "owner", 1)
    store.insert_device("dev_a", "user_a", "f" * 52, b"public", "phone", 1, state="ACTIVE")
    iid = "a" * 52
    ctx = SimpleNamespace(
        store=store,
        out=io.StringIO(),
        now=lambda: 10,
        custody=SimpleNamespace(anchor_dir=_owned_operator_parent() / "anchor"),
    )
    reads = []

    def live(_ctx, device_id, actual_iid):
        assert actual_iid == iid and device_id == "dev_a"
        decision = store.media_read_decision(iid, device_id)
        reads.append(decision.revision)
        return {
            "decision": decision._asdict(),
            "nonce": "a" * 32,
            "generation": "b" * 32,
            "host_enabled": False,
            "api_available": True,
            "effective": decision.allowed is True,
            "expires_ms": 2**52,
        }

    original_write = store.set_media_read
    exchanges = []

    def exchange(path, request):
        assert path.name == media_operator_client.MEDIA_OPERATOR_SOCKET_NAME
        assert request.iid == iid and request.device_id == "dev_a"
        assert request.nonce == "a" * 32 and request.generation == "b" * 32
        assert request.allowed is allowed
        exchanges.append(request)
        # Emulate the service boundary; the CLI's own Store mutator is forbidden.
        written = original_write(request.expected, allowed=request.allowed, now=10)
        return MediaOperatorReply("committed", written)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("CLI must not write Store directly")

    monkeypatch.setattr(media_operator_client, "exchange_media_decision", exchange)
    monkeypatch.setattr(store, "set_media_read", forbidden)
    monkeypatch.setattr(cli, "_load_identity", lambda _ctx: SimpleNamespace(iid=iid))
    monkeypatch.setattr(cli, "_media_operator_context", live)
    monkeypatch.setattr(
        cli,
        "_host_request_confirmation",
        lambda _ctx, token: token.startswith(
            ("ALLOW" if allowed else "DENY") + " MEDIA_READ dev_a"
        ),
    )
    try:
        action = "grant-media-read" if allowed else "deny-media-read"
        args = argparse.Namespace(devices_command=action, device_id="dev_a")
        assert cli._cmd_devices_media(ctx, args) == 0
        assert reads == [0, 0, 1] and len(exchanges) == 1
        assert store.media_read_decision(iid, "dev_a").allowed is allowed
        assert store.owner_controls_decision("dev_a") is None
    finally:
        store.close()


@pytest.mark.parametrize(
    "interruption",
    (
        "cancel",
        "nonce",
        "generation",
        "expired",
        "concurrent_decision",
        "lost_ack",
    ),
)
def test_operator_media_interruption_never_replays_or_changes_unrelated_rights(
    tmp_path,
    monkeypatch,
    interruption,
):
    store = Store(tmp_path / "media.sqlite3")
    store.migrate()
    store.insert_user("user_a", "owner", 1)
    store.insert_device("dev_a", "user_a", "f" * 52, b"public", "phone", 1, state="ACTIVE")
    iid = "a" * 52
    ctx = SimpleNamespace(
        store=store,
        out=io.StringIO(),
        now=lambda: 10,
        custody=SimpleNamespace(anchor_dir=_owned_operator_parent() / "anchor"),
    )
    initial = store.media_read_decision(iid, "dev_a")
    calls = []
    original_write = store.set_media_read
    writes = []

    def write(*args, **kwargs):
        writes.append(1)
        result = original_write(*args, **kwargs)
        if interruption == "lost_ack":
            raise OSError("synthetic lost acknowledgement after commit")
        return result

    def live(_ctx, device_id, actual_iid):
        assert device_id == "dev_a" and actual_iid == iid
        calls.append(1)
        decision = store.media_read_decision(iid, device_id)
        reply = {
            "decision": decision._asdict(),
            "nonce": "a" * 32,
            "generation": "b" * 32,
            "host_enabled": False,
            "api_available": True,
            "effective": decision.allowed is True,
            "expires_ms": 2**52,
        }
        if len(calls) == 2:
            if interruption == "nonce":
                reply["nonce"] = "c" * 32
            elif interruption == "generation":
                reply["generation"] = "d" * 32
            elif interruption == "expired":
                reply["expires_ms"] = 0
            elif interruption == "concurrent_decision":
                # Race after the live sample but before the command's CAS.
                assert original_write(decision, allowed=False, now=9) is not None
        return reply

    monkeypatch.setattr(cli, "_load_identity", lambda _ctx: SimpleNamespace(iid=iid))
    monkeypatch.setattr(cli, "_media_operator_context", live)
    monkeypatch.setattr(
        cli, "_host_request_confirmation", lambda _ctx, _token: interruption != "cancel"
    )

    def exchange(_path, request):
        written = write(request.expected, allowed=request.allowed, now=10)
        return MediaOperatorReply("conflict" if written is None else "committed", written)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("CLI must not bypass service")

    monkeypatch.setattr(media_operator_client, "exchange_media_decision", exchange)
    monkeypatch.setattr(store, "set_media_read", forbidden)
    try:
        args = argparse.Namespace(devices_command="grant-media-read", device_id="dev_a")
        with pytest.raises(cli.RefusedError) as caught:
            cli._cmd_devices_media(ctx, args)
        final = store.media_read_decision(iid, "dev_a")
        if interruption == "lost_ack":
            assert final.allowed is True and final.revision == 1
            assert len(writes) == 1 and "do not replay" in str(caught.value)
        elif interruption == "concurrent_decision":
            assert final.allowed is False and final.revision == 1
            assert len(writes) == 1 and "no decision saved" in str(caught.value)
        else:
            assert final == initial and writes == []
        assert store.owner_controls_decision("dev_a") is None
    finally:
        store.close()


@pytest.mark.parametrize(
    "outcome",
    ("unavailable", "unknown", "reply_unknown", "conflict", "refused", "bad_reply", "inspect"),
)
def test_cli_media_no_sql_fallback_or_automatic_replay(tmp_path, monkeypatch, outcome):
    store = Store(tmp_path / "media.sqlite3")
    store.migrate()
    store.insert_user("user_a", "owner", 1)
    store.insert_device("dev_a", "user_a", "f" * 52, b"public", "phone", 1, state="ACTIVE")
    iid = "a" * 52
    ctx = SimpleNamespace(
        store=store,
        out=io.StringIO(),
        now=lambda: 10,
        custody=SimpleNamespace(anchor_dir=_owned_operator_parent() / "anchor"),
    )
    initial = store.media_read_decision(iid, "dev_a")
    exchanges, confirmations = [], []

    def live(_ctx, device_id, _iid):
        assert device_id == "dev_a" and _iid == iid
        return {
            "decision": initial._asdict(),
            "nonce": "a" * 32,
            "generation": "b" * 32,
            "host_enabled": False,
            "api_available": True,
            "effective": False,
            "expires_ms": 2**52,
        }

    def confirm(_ctx, token):
        confirmations.append(token)
        return token == "ALLOW MEDIA_READ dev_a"

    def exchange(_path, request):
        exchanges.append(request)
        if outcome == "unavailable":
            raise media_operator_client.MediaOperatorUnavailableError()
        if outcome == "unknown":
            raise media_operator_client.MediaOperatorOutcomeUnknownError()
        if outcome == "bad_reply":
            return object()
        assert outcome != "inspect"
        return MediaOperatorReply("unknown" if outcome == "reply_unknown" else outcome, None)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("direct CLI SQL fallback forbidden")

    monkeypatch.setattr(cli, "_load_identity", lambda _ctx: SimpleNamespace(iid=iid))
    monkeypatch.setattr(cli, "_media_operator_context", live)
    monkeypatch.setattr(cli, "_host_request_confirmation", confirm)
    monkeypatch.setattr(media_operator_client, "exchange_media_decision", exchange)
    monkeypatch.setattr(store, "set_media_read", forbidden)
    try:
        args = argparse.Namespace(
            devices_command="media-read" if outcome == "inspect" else "grant-media-read",
            device_id="dev_a",
        )
        if outcome == "inspect":
            assert cli._cmd_devices_media(ctx, args) == 0
            assert exchanges == [] and confirmations == []
        else:
            with pytest.raises(cli.RefusedError) as caught:
                cli._cmd_devices_media(ctx, args)
            assert len(exchanges) == 1 and confirmations == ["ALLOW MEDIA_READ dev_a"]
            if outcome in {"unknown", "reply_unknown", "bad_reply"}:
                assert "do not replay" in str(caught.value)
            elif outcome == "unavailable":
                assert "no decision submitted" in str(caught.value)
        assert store.media_read_decision(iid, "dev_a") == initial
        assert store.owner_controls_decision("dev_a") is None
    finally:
        store.close()

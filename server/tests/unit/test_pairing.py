"""T025: P2 and P4 with every G-PAIRING divergence fixed (FR-009, CS-12).

- PR2-2 check order: offer errors before signature errors;
- the offer burns after `OFFER_MAX_FAILURES`;
- PR2-3 sanitization (Unicode categories, NFC, truncation, `unnamed device`), with the signature
  verified over the raw wire value;
- PR2-4 response: `isig` verifies under the pinned key, the SAS is the device's own;
- PR2-5 durable nonces: a gateway restart between P2 and P4 still completes;
- PR4-2: one test per row;
- PR4-3: an equal or lower `ts`, and `|ts - now| > CLOCK_SKEW_S`, are rejected.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import crypto, wire
from hmp_plugin.contract import (
    ACCESS_TTL_S,
    CLOCK_SKEW_S,
    DEVICE_NAME_MAX_BYTES,
    OFFER_MAX_FAILURES,
    PAIRING_CONFIRM_WINDOW_S,
    TAG_PAIR_REQ,
    TAG_PAIR_RESP,
)
from hmp_plugin.pairing import (
    UNNAMED_DEVICE,
    confirm_pairing,
    device_id_for_pairing,
    sanitize_device_name,
)
from hmp_plugin.revoke import revoke_device

from .hmp_kit import Device, Env, Offer, code, get, pair, post, run


async def p2(env: Env, client: TestClient, dev: Device, offer: Offer, **override: object):
    status, body = await post(client, "/pair/request", env.p2_body(dev, offer, **override))
    if status == 202:
        dev.pairing_id, dev.ni = body["pairing_id"], wire.b64u_decode(body["ni"], length=32)
    return status, body


async def p4(env: Env, client: TestClient, dev: Device, *, ts: int | None = None):
    return await post(client, "/pair/complete", env.p4_body(dev, ts=ts))


# --------------------------------------------------------------------------------------------------
# PR2-3 sanitization
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("category", "char"),
    [
        ("Cc", "\u0007"),
        ("Cc", "\u009b"),
        ("Cf", "\u200b"),
        ("Cf", "\u202e"),  # right-to-left override
        ("Zl", "\u2028"),
        ("Zp", "\u2029"),
        ("Co", "\ue000"),
        ("Cn", "\u0378"),
    ],
)
def test_sanitize_drops_category(category: str, char: str) -> None:
    assert unicodedata.category(char) == category
    assert sanitize_device_name(f"ph{char}one") == "phone"


def test_sanitize_applies_nfc() -> None:
    assert sanitize_device_name("cafe\u0301") == "caf\u00e9"


def test_sanitize_truncates_on_a_character_boundary() -> None:
    name = "\u00e9" * 40  # 80 bytes of UTF-8
    out = sanitize_device_name(name)
    assert len(out.encode("utf-8")) <= DEVICE_NAME_MAX_BYTES
    assert out == "\u00e9" * 32
    assert sanitize_device_name("a" * 100) == "a" * DEVICE_NAME_MAX_BYTES


@pytest.mark.parametrize("name", ["", "\u200b\u200e", "\u0000\u0001", "\u2028"])
def test_sanitize_empty_becomes_unnamed(name: str) -> None:
    assert sanitize_device_name(name) == UNNAMED_DEVICE


def test_signature_is_over_the_raw_wire_name(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = Device(name="my\u200b phone\u202e")
        status, _ = await p2(env, client, dev, env.offer())
        assert status == 202
        row = env.store.get_pairing(dev.pairing_id)
        assert row["device_name_sanitized"] == "my phone"
        # A signature over the sanitized value instead of the wire value fails.
        other = Device(name="my\u200b phone")
        offer = env.offer()
        body = env.p2_body(other, offer)
        oid_raw = wire.b64u_decode(offer.oid, length=16)
        wrong = crypto.transcript(
            TAG_PAIR_REQ, env.iid, oid_raw, crypto.sha256(offer.s), other.pub, "my phone", other.nd
        )
        body["sig"] = other.sign(wrong)
        status, reply = await post(client, "/pair/request", body)
        assert (status, code(reply)) == (401, "pair_failed")

    run(env, scenario)


def test_device_name_over_64_bytes_on_the_wire_fails(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        status, body = await p2(env, client, Device(name="x" * 65), env.offer())
        assert (status, code(body)) == (401, "pair_failed")

    run(env, scenario)


# --------------------------------------------------------------------------------------------------
# P2 order, responses and burning (PR2-2, PR2-4)
# --------------------------------------------------------------------------------------------------


def test_p2_success_response_verifies(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev, offer = Device(), env.offer()
        status, body = await p2(env, client, dev, offer)
        assert status == 202
        assert set(body) == {"pairing_id", "state", "ni", "device_sas", "confirm_by", "isig"}
        assert body["state"] == "awaiting_operator"
        assert body["confirm_by"] == env.clock.now + PAIRING_CONFIRM_WINDOW_S
        assert type(body["confirm_by"]) is int
        sas = crypto.device_sas(crypto.spki_fingerprint(dev.pub))
        assert body["device_sas"] == sas
        msg = crypto.transcript(
            TAG_PAIR_RESP,
            env.iid,
            wire.b64u_decode(offer.oid, length=16),
            dev.pub,
            dev.nd,
            dev.ni,
            wire.b64u_decode(body["pairing_id"], length=16),
            sas,
            body["confirm_by"],
        )
        spki = crypto.spki_der(env.identity.private_key().public_key())
        assert crypto.spki_fingerprint(spki) == env.iid
        assert crypto.verify(spki, wire.b64u_signature(body["isig"]), msg)
        row = env.store.get_pairing(dev.pairing_id)
        assert bytes(row["nd"]) == dev.nd and bytes(row["ni"]) == dev.ni  # PR2-5
        assert env.store.get_offer(offer.oid)["state"] == "claimed"
        # The claimed offer cannot be used again.
        status, reply = await p2(env, client, Device(), offer)
        assert (status, code(reply)) == (409, "offer_used")
        assert "device_sas" not in reply["error"]

    run(env, scenario)


def test_offer_error_is_reported_before_signature_error(tmp_path: Path) -> None:
    env = Env(tmp_path)
    bad_sig = wire.b64u_encode(b"\x30\x06\x02\x01\x01\x02\x01\x01")

    async def scenario(client: TestClient) -> None:
        expired = env.offer(ttl=10)
        env.clock.now += 11
        status, body = await p2(env, client, Device(), expired, sig=bad_sig)
        assert (status, code(body)) == (410, "offer_expired")
        used = env.offer()
        assert (await p2(env, client, Device(), used))[0] == 202
        status, body = await p2(env, client, Device(), used, sig=bad_sig)
        assert (status, code(body)) == (409, "offer_used")
        # Also before field decoding: a used offer with a malformed device key.
        status, body = await p2(env, client, Device(), used, device_pub="AAAA")
        assert (status, code(body)) == (409, "offer_used")
        # Unknown offer: uniform failure.
        unknown = Offer(wire.b64u_encode(b"\x02" * 16), b"\x00" * 32)
        status, body = await p2(env, client, Device(), unknown)
        assert (status, code(body)) == (401, "pair_failed")

    run(env, scenario)


def test_offer_burns_after_max_failures(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        offer = env.offer()
        wrong = wire.b64u_encode(b"\x09" * 32)
        for _ in range(OFFER_MAX_FAILURES):
            status, body = await p2(env, client, Device(), offer, s=wrong)
            assert (status, code(body)) == (401, "pair_failed")
        assert env.store.get_offer(offer.oid)["state"] == "burned"
        status, body = await p2(env, client, Device(), offer)  # now even a correct request
        assert (status, code(body)) == (409, "offer_used")

    run(env, scenario)


@pytest.mark.parametrize(
    "override",
    [
        {"v": 2},
        {"v": True},
        {"v": 1.0},
        {"s": "AAAA"},
        {"s": wire.b64u_encode(b"\x00" * 32) + "="},
        {"nd": wire.b64u_encode(b"\x00" * 31)},
        {"device_pub": wire.b64u_encode(b"\x00" * 91)},
        {"sig": "!!"},
        {"device_name": 5},
    ],
)
def test_malformed_fields_are_pair_failed(tmp_path: Path, override: dict[str, object]) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        status, body = await p2(env, client, Device(), env.offer(), **override)
        assert (status, code(body)) == (401, "pair_failed")

    run(env, scenario)


def test_compressed_or_p384_device_key_is_refused(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    env = Env(tmp_path)
    p256 = ec.generate_private_key(ec.SECP256R1()).public_key()
    compressed = bytes.fromhex(
        "3039301306072a8648ce3d020106082a8648ce3d030107032200"
    ) + p256.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint)
    p384 = (
        ec.generate_private_key(ec.SECP384R1())
        .public_key()
        .public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    )

    async def scenario(client: TestClient) -> None:
        for spki in (compressed, p384):
            status, body = await p2(
                env, client, Device(), env.offer(), device_pub=wire.b64u_encode(spki)
            )
            assert (status, code(body)) == (401, "pair_failed")

    run(env, scenario)


# --------------------------------------------------------------------------------------------------
# PR2-5: durable nonces across a restart
# --------------------------------------------------------------------------------------------------


def test_restart_between_p2_and_p4_still_completes(tmp_path: Path) -> None:
    env = Env(tmp_path)
    dev = Device()

    async def before(client: TestClient) -> None:
        assert (await p2(env, client, dev, env.offer()))[0] == 202

    run(env, before)
    iid = env.iid
    env.restart()
    assert env.iid == iid
    env.confirm(dev)

    async def after(client: TestClient) -> None:
        status, body = await p4(env, client, dev)
        assert status == 200, body

    run(env, after)


# --------------------------------------------------------------------------------------------------
# PR4-2: one test per row
# --------------------------------------------------------------------------------------------------


async def _pending(env: Env, client: TestClient) -> Device:
    dev = Device()
    assert (await p2(env, client, dev, env.offer()))[0] == 202
    return dev


def test_pr42_row1_denied_is_403(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        assert env.deny(dev)
        status, body = await p4(env, client, dev)
        assert (status, code(body)) == (403, "pair_denied")

    run(env, scenario)


def test_pr42_row2_expired_or_past_confirm_by_is_410(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        # (a) past confirm_by, never confirmed
        dev = await _pending(env, client)
        env.clock.now += PAIRING_CONFIRM_WINDOW_S + 1
        status, body = await p4(env, client, dev)
        assert (status, code(body)) == (410, "offer_expired")
        # (b) expired by an identity-change revocation (PR7-2 expires pending pairings)
        dev = await _pending(env, client)
        env.store.revoke_all_for_identity_change(env.clock.now)
        status, body = await p4(env, client, dev)
        assert (status, code(body)) == (410, "offer_expired")

    run(env, scenario)


def test_pr42_row3_not_yet_confirmed_is_202(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        for _ in range(2):
            env.clock.now += 2
            status, body = await p4(env, client, dev)
            assert (status, body) == (202, {"state": "awaiting_operator"})

    run(env, scenario)


def test_pr42_row4_confirmed_but_not_active_is_403(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        device_id = env.confirm(dev)
        revoke_device(env.store, device_id, now=env.clock.now)
        status, body = await p4(env, client, dev)
        assert (status, code(body)) == (403, "pair_denied")

    run(env, scenario)


def test_pr42_row5_first_issue_is_200(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        device_id = env.confirm(dev)
        status, body = await p4(env, client, dev)
        assert status == 200
        assert set(body) == {
            "device_id",
            "user_ref",
            "refresh_token",
            "access_token",
            "access_expires_at",
        }
        assert body["device_id"] == device_id == device_id_for_pairing(dev.pairing_id)
        assert body["user_ref"].startswith("hmpu_")
        assert body["access_expires_at"] == env.clock.now + ACCESS_TTL_S
        for name in ("refresh_token", "access_token"):
            raw = wire.b64u_decode(body[name], length=32)
            # PR4-4: only the hash is stored.
            table = "refresh_tokens" if name == "refresh_token" else "access_tokens"
            with env.store.transaction() as conn:
                hit = conn.execute(f"SELECT 1 FROM {table} WHERE hash = ?", (crypto.sha256(raw),))  # noqa: S608
                assert hit.fetchone() is not None
        dev.access = body["access_token"]
        status, _ = await get(client, "/bots", headers=env.headers(dev))
        assert status == 200

    run(env, scenario)


def test_pr42_row6_reissue_within_window_revokes_the_earlier_family(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first_access = dev.access
        env.clock.now += 30  # the first response was lost; the device polls again
        status, body = await p4(env, client, dev)
        assert status == 200
        assert body["access_token"] != first_access
        assert body["device_id"] == dev.device_id
        status, reply = await get(client, "/bots", headers=env.headers(dev))
        assert (status, code(reply)) == (401, "revoked")  # the earlier family
        dev.access = body["access_token"]
        status, _ = await get(client, "/bots", headers=env.headers(dev))
        assert status == 200

    run(env, scenario)


def test_pr42_row7_after_window_is_409(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.clock.now += PAIRING_CONFIRM_WINDOW_S + 1
        status, body = await p4(env, client, dev)
        assert (status, code(body)) == (409, "offer_used")
        with env.store.transaction() as conn:  # the issued family is untouched
            (live,) = conn.execute(
                "SELECT COUNT(*) FROM token_families WHERE device_id = ? AND revoked_at IS NULL",
                (dev.device_id,),
            ).fetchone()
        assert live == 1

    run(env, scenario)


def test_pr42_row8_nonces_unavailable_is_410(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        env.confirm(dev)
        with env.store.transaction() as conn:
            conn.execute(
                "UPDATE pairings SET ni = ? WHERE pairing_id = ?", (b"\x00", dev.pairing_id)
            )
        status, body = await p4(env, client, dev)
        assert (status, code(body)) == (410, "offer_expired")

    run(env, scenario)


def test_pr42_row9_other_failures_are_401(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        env.confirm(dev)
        # A signature by another key.
        body = env.p4_body(dev)
        body["sig"] = Device().sign(b"anything")
        status, reply = await post(client, "/pair/complete", body)
        assert (status, code(reply)) == (401, "pair_failed")
        # An unknown pairing.
        body = env.p4_body(dev)
        body["pairing_id"] = wire.b64u_encode(b"\x03" * 16)
        status, reply = await post(client, "/pair/complete", body)
        assert (status, code(reply)) == (401, "pair_failed")
        # Malformed members.
        for bad in ({"pairing_id": 5}, {"ts": 1.5}, {"ts": True}, {"sig": "=="}, {"ts": -1}):
            status, reply = await post(client, "/pair/complete", {**env.p4_body(dev), **bad})
            assert (status, code(reply)) == (401, "pair_failed"), bad
        status, reply = await post(client, "/pair/complete", {"ts": 1})
        assert (status, code(reply)) == (401, "pair_failed")

    run(env, scenario)


# --------------------------------------------------------------------------------------------------
# PR4-3: fresh, strictly increasing ts
# --------------------------------------------------------------------------------------------------


def test_pr43_equal_or_lower_ts_is_rejected(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        ts = env.clock.now
        assert (await p4(env, client, dev, ts=ts))[0] == 202
        for replay in (ts, ts - 1):
            status, body = await p4(env, client, dev, ts=replay)
            assert (status, code(body)) == (401, "pair_failed")
        assert (await p4(env, client, dev, ts=ts + 1))[0] == 202
        assert env.store.get_pairing(dev.pairing_id)["last_p4_ts"] == ts + 1

    run(env, scenario)


def test_pr43_skewed_ts_is_rejected(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        for ts in (env.clock.now + CLOCK_SKEW_S + 1, env.clock.now - CLOCK_SKEW_S - 1):
            status, body = await p4(env, client, dev, ts=ts)
            assert (status, code(body)) == (401, "pair_failed")
        assert env.store.get_pairing(dev.pairing_id)["last_p4_ts"] is None
        assert (await p4(env, client, dev, ts=env.clock.now + CLOCK_SKEW_S))[0] == 202

    run(env, scenario)


# --------------------------------------------------------------------------------------------------
# P3 helpers (used by the CLI, T032)
# --------------------------------------------------------------------------------------------------


def test_confirm_only_a_pending_pairing(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        assert env.deny(dev)
        env.store.insert_user("hmpu_" + "0" * 32, "l", env.clock.now)
        with pytest.raises(LookupError):
            confirm_pairing(
                env.store, dev.pairing_id, user_id="hmpu_" + "0" * 32, label="l", now=env.clock.now
            )
        late = await _pending(env, client)
        env.clock.now += PAIRING_CONFIRM_WINDOW_S + 1
        with pytest.raises(LookupError):
            env.confirm(late)
        assert env.store.get_device(device_id_for_pairing(late.pairing_id)) is None


def test_confirm_pairing_refuses_at_the_sas_mismatch_limit(tmp_path: Path) -> None:
    """SR-2 defense in depth: `confirm_pairing` itself must refuse a pairing whose
    `sas_mismatches` already reached the limit, even when called directly (bypassing the CLI's
    own pre-check), and must change nothing."""
    from hmp_plugin.contract import SAS_MAX_MISMATCHES

    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await _pending(env, client)
        with env.store.transaction() as conn:
            conn.execute(
                "UPDATE pairings SET sas_mismatches = ? WHERE pairing_id = ?",
                (SAS_MAX_MISMATCHES, dev.pairing_id),
            )
        env.store.insert_user("hmpu_" + "9" * 32, "l", env.clock.now)
        with pytest.raises(LookupError):
            confirm_pairing(
                env.store, dev.pairing_id, user_id="hmpu_" + "9" * 32, label="l", now=env.clock.now
            )
        assert env.store.get_device(device_id_for_pairing(dev.pairing_id)) is None
        assert env.store.get_pairing(dev.pairing_id)["state"] == "awaiting_operator"

    run(env, scenario)

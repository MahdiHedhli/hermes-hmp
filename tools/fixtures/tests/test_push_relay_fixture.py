"""Receiver/client seam only. These tests do not count as T029 native approval evidence."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import http.client
import json
import socket
import ssl
import time
from dataclasses import replace

import _fixture_common as fc
import push_relay_fixture as fixture
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from hmp_plugin.push_config import RelayConfig
from hmp_plugin.push_dispatch import RelayAttempt
from hmp_plugin.push_relay import RelayClient, signed_request


class SyntheticIdentity:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        spki = self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.iid = base64.b32encode(hashlib.sha256(spki).digest()).rstrip(b"=").decode().lower()

    def still_current(self):
        return True

    def private_key(self):
        return self.key


def _attempt(identity, relay):
    return RelayAttempt(
        RelayConfig(relay.url, "synthetic-relay", ("fixture-kid",), (relay.leaf_pin,)),
        identity.iid, bytes(range(32)), bytes(range(32, 64)), bytes(range(24)),
        "apns", "apns_token", "sandbox", "fixture-kid", b"synthetic-seal" * 7,
        330, 1700000000, bytes(range(16)),
    )


def _post(relay, raw, signature):
    conn = http.client.HTTPSConnection(
        "127.0.0.1", int(relay.url.split(":")[2].split("/")[0]),
        context=relay.trust_context(), timeout=3,
    )
    try:
        conn.request(
            "POST", "/base/v1/push", raw,
            {"Content-Type": "application/json", "HMP-Relay-Signature": signature},
        )
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


def test_production_transport_reaches_independently_verified_bounded_receiver(tmp_path):
    identity = SyntheticIdentity()
    with fixture.FakeHttpsRelay(tmp_path / "relay") as relay:
        assert relay.root.stat().st_mode & 0o777 == 0o700
        assert all(path.stat().st_mode & 0o777 == 0o600 for path in relay.root.iterdir())
        trust = relay.trust_context()
        assert trust.verify_mode == ssl.CERT_REQUIRED and trust.check_hostname

        async def drive():
            client = RelayClient(identity, _ssl_factory=relay.trust_context)
            try:
                attempt = _attempt(identity, relay)
                assert await client.send(attempt) == "accepted"
                assert await client.send(
                    replace(attempt, platform="fcm", addr_kind="fcm_token", env=None)
                ) == "accepted"
                # Both chain validation and the additional leaf pin are effective.
                untrusted = RelayClient(identity)
                try:
                    assert await untrusted.send(attempt) == "prewrite_failure"
                finally:
                    await untrusted.close()
                assert await client.send(
                    replace(attempt, relay=replace(attempt.relay, spki_pins=(b"x" * 32,)))
                ) == "prewrite_failure"
            finally:
                await client.close()

        asyncio.run(drive())
        observed = relay.records()
        assert len(observed) == 2
        assert observed[0]["env"] == "sandbox" and "env" not in observed[1]
        observed[0]["kind"] = "modified-copy"
        assert relay.records()[0]["kind"] == "approval"  # caller cannot change saved capture
        assert relay.status_count(202) == 2
    assert not relay.alive
    relay.close()  # idempotent teardown


def test_bad_signatures_capacity_and_stalled_peer_are_bounded(tmp_path, capfd):
    identity = SyntheticIdentity()
    relay = fixture.FakeHttpsRelay(tmp_path / "relay")
    peer = None
    try:
        raw, signature = signed_request(identity, _attempt(identity, relay))
        body = json.loads(raw)
        body["ttl_s"] += 1
        assert _post(relay, json.dumps(body).encode(), signature) == 401
        try:
            assert _post(relay, b"x" * (fixture.BODY_CAP + 1), signature) == 400
        except ConnectionResetError:
            # Early rejection deliberately does not drain an over-limit body.
            assert relay.status_count(400) == 1
        assert _post(relay, raw, signature + "=") == 400  # noncanonical b64u
        nested = b'{"nested":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}"
        assert len(nested) < fixture.BODY_CAP
        assert _post(relay, nested, signature) == 400
        assert capfd.readouterr().err == ""  # malformed JSON emits no diagnostic traceback
        assert relay.records() == ()
        for _ in range(fixture.CAPTURE_CAP):
            assert _post(relay, raw, signature) == 202
        assert _post(relay, raw, signature) == 429
        assert len(relay.records()) == fixture.CAPTURE_CAP
        assert relay.status_count(401) == 1 and relay.status_count(429) == 1
        # A peer that never even completes TLS cannot hold teardown indefinitely.
        peer = socket.create_connection(
            ("127.0.0.1", int(relay.url.split(":")[2].split("/")[0])), timeout=3
        )
        start = time.monotonic()
        relay.close()
        assert time.monotonic() - start < fixture.CONNECTION_S + 2
        assert not relay.alive
    finally:
        if peer is not None:
            peer.close()
        relay.close()
    # Never follow an existing output or write in the real home.
    with pytest.raises(FileExistsError):
        fixture.FakeHttpsRelay(tmp_path / "relay")
    with pytest.raises(fc.FixtureSafetyError):
        fixture.FakeHttpsRelay(fixture.Path.home() / "forbidden-relay-fixture")

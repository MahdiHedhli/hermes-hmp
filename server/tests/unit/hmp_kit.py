"""Shared test kit for the T024-T027 route tests: a real store and a real instance identity in
isolated temporary homes (synthetic host id), a settable clock, a reference device that signs the
`HMP1-*` transcripts, and helpers that drive P1 (as the operator CLI would), P2, P3, P4 and P5.

Nothing here touches a real Hermes home or the real host identifier. Every key is generated per
test and is test-only.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import crypto, identity, server, wire
from hmp_plugin.compat import CompatResult, CompatStatus
from hmp_plugin.contract import (
    OFFER_TTL_S,
    PATH_PREFIX,
    TAG_OFFER,
    TAG_PAIR_DONE,
    TAG_PAIR_REQ,
    TAG_SELF_REVOKE,
    TAG_TOKEN,
    OtherWhy,
)
from hmp_plugin.identity import HostId
from hmp_plugin.logging_policy import AllowListedAccessLogger
from hmp_plugin.pairing import confirm_pairing, deny_pairing
from hmp_plugin.store import Store

HOST = HostId("test-source", "synthetic-host-a")
T0 = 1_900_000_000
SUPPORTED = CompatResult(CompatStatus.SUPPORTED)
UNSUPPORTED = CompatResult(CompatStatus.UNSUPPORTED, OtherWhy.HERMES_BUILD_UNSUPPORTED)


def identity_kwargs(home: Path) -> dict[str, Any]:
    root = home / "hermes"
    return {
        "env": {"HERMES_HOME": str(root)},
        "hermes_root": root,
        "binding_root": home / "state" / "hermes-hmp",
        "host_id": lambda: HOST,
    }


@dataclass
class Clock:
    now: int = T0

    def __call__(self) -> int:
        return self.now


class SpyBridge:
    """Counts every call; answers nothing useful (reads are T028/T030)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def call(*_a: Any, **_k: Any) -> Any:
            self.calls.append(name)
            if name == "capability_versions":
                return {}
            if name == "served_profiles":
                # OD-F8 (2026-09-27): the adapter reads this once, on `connect()`, to write the
                # listener record's `profiles` field. Empty here (no bearer-route test depends on
                # a served profile existing through `SpyBridge`).
                return []
            raise AssertionError(f"unexpected bridge call {name}")

        return call


class FakeReads:
    """Stands in for `reads.Reads` (T030) so bearer routes can be exercised end to end."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def roster(self, user_id: str) -> dict[str, Any]:
        self.calls.append(("roster", user_id))
        return {"bots": []}

    # Amendment A1 (session browsing): minimal stand-ins so the generic bearer/gate plumbing
    # tests can exercise SES-1/SES-2 without a real bridge. `test_reads.py` covers the real
    # `Reads.list_sessions`/`session_snapshot`/`session_history` behavior against `fake_hermes`.
    def list_sessions(
        self, user_id: str, profile: str, *, cursor: str | None, limit: int
    ) -> dict[str, Any]:
        self.calls.append(("list_sessions", user_id))
        return {"sessions": [], "next_cursor": None}

    def session_snapshot(
        self, user_id: str, profile: str, session_ref: str, limit: int
    ) -> dict[str, Any]:
        self.calls.append(("session_snapshot", user_id))
        return {
            "session_ref": session_ref,
            "messages": [],
            "head_message_id": None,
            "truncated": False,
        }

    def session_history(
        self, user_id: str, profile: str, session_ref: str, after: int, limit: int
    ) -> dict[str, Any]:
        self.calls.append(("session_history", user_id))
        return {"messages": [], "head_message_id": None}


@dataclass
class Device:
    """A reference device: its own P-256 key (test-only) and what it learns while pairing."""

    key: Any = field(default_factory=crypto.generate_private_key)
    name: str = "test phone"
    nd: bytes = field(default_factory=lambda: crypto.random_bytes(32))
    pairing_id: str | None = None
    ni: bytes | None = None
    device_id: str | None = None
    refresh: str | None = None
    access: str | None = None
    last_ts: int = 0

    @property
    def pub(self) -> bytes:
        return crypto.spki_der(self.key.public_key())

    def sign(self, message: bytes) -> str:
        return wire.b64u_encode(crypto.sign(self.key, message))

    def next_ts(self, now: int) -> int:
        self.last_ts = max(now, self.last_ts + 1)
        return self.last_ts


@dataclass
class Offer:
    oid: str
    s: bytes


class Env:
    """One HMP instance under test: store + identity + app context."""

    def __init__(
        self, home: Path, *, compat: CompatResult = SUPPORTED, session_browsing: bool = True
    ) -> None:
        self.home = home
        self.clock = Clock()
        self.session_browsing = session_browsing
        self.kwargs = identity_kwargs(home)
        self.custody = identity.resolve_custody(
            env=self.kwargs["env"],
            hermes_root=self.kwargs["hermes_root"],
            binding_root=self.kwargs["binding_root"],
        )
        self.store_path = server.store_path(self.custody.anchor_dir)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.store_path)
        self.store.migrate()
        self.identity = identity.load_or_create(self.store, **self.kwargs, now=T0)
        self.bridge = SpyBridge()
        self.ctx = server.ServerContext(
            identity=self.identity,
            store=self.store,
            compat=compat,
            bridge=self.bridge if compat.supported else None,
            reads=FakeReads() if compat.supported else None,
            clock=self.clock,
            session_browsing_enabled=session_browsing,
        )

    @property
    def iid(self) -> str:
        return self.identity.iid

    def restart(self) -> None:
        """A gateway restart: new store connection, identity reloaded from disk, new limiter."""
        self.store.close()
        self.store = Store(self.store_path)
        self.store.migrate()
        self.identity = identity.load_or_create(self.store, **self.kwargs, now=self.clock.now)
        self.ctx = server.ServerContext(
            identity=self.identity,
            store=self.store,
            compat=self.ctx.compat,
            bridge=self.ctx.bridge,
            reads=self.ctx.reads,
            clock=self.clock,
            session_browsing_enabled=self.session_browsing,
        )

    def app(self) -> web.Application:
        return server.build_app(self.ctx)

    # ---- P1 / P3 as the operator CLI would -------------------------------------------------------

    def offer(self, *, ttl: int = OFFER_TTL_S) -> Offer:
        oid_raw, s = crypto.random_bytes(16), crypto.random_bytes(32)
        oid = wire.b64u_encode(oid_raw)
        self.store.insert_offer(oid, crypto.secret_hash(TAG_OFFER, s), self.clock.now + ttl)
        return Offer(oid, s)

    def confirm(self, dev: Device, *, user_id: str | None = None) -> str:
        user_id = user_id or "hmpu_" + crypto.random_bytes(16).hex()
        if not _user_exists(self.store, user_id):
            self.store.insert_user(user_id, "test label", self.clock.now)
        assert dev.pairing_id is not None
        return confirm_pairing(
            self.store, dev.pairing_id, user_id=user_id, label="test label", now=self.clock.now
        )

    def deny(self, dev: Device) -> bool:
        assert dev.pairing_id is not None
        return deny_pairing(self.store, dev.pairing_id, now=self.clock.now)

    # ---- wire bodies ---------------------------------------------------------------------------

    def p2_body(self, dev: Device, offer: Offer, **override: Any) -> dict[str, Any]:
        oid_raw = wire.b64u_decode(offer.oid, length=16)
        msg = crypto.transcript(
            TAG_PAIR_REQ, self.iid, oid_raw, crypto.sha256(offer.s), dev.pub, dev.name, dev.nd
        )
        body: dict[str, Any] = {
            "v": 1,
            "oid": offer.oid,
            "s": wire.b64u_encode(offer.s),
            "device_name": dev.name,
            "device_pub": wire.b64u_encode(dev.pub),
            "nd": wire.b64u_encode(dev.nd),
            "sig": dev.sign(msg),
        }
        body.update(override)
        return body

    def p4_body(self, dev: Device, *, ts: int | None = None) -> dict[str, Any]:
        assert dev.pairing_id is not None and dev.ni is not None
        ts = dev.next_ts(self.clock.now) if ts is None else ts
        pid_raw = wire.b64u_decode(dev.pairing_id, length=16)
        msg = crypto.transcript(TAG_PAIR_DONE, self.iid, pid_raw, dev.nd, dev.ni, ts)
        return {"pairing_id": dev.pairing_id, "ts": ts, "sig": dev.sign(msg)}

    def p5_body(
        self,
        dev: Device,
        *,
        refresh: str | None = None,
        ts: int | None = None,
        nonce: bytes | None = None,
        signer: Device | None = None,
        iid: str | None = None,
    ) -> dict[str, Any]:
        refresh = refresh if refresh is not None else dev.refresh
        assert refresh is not None and dev.device_id is not None
        ts = self.clock.now if ts is None else ts
        nonce = crypto.random_bytes(16) if nonce is None else nonce
        raw = wire.b64u_decode(refresh, length=32)
        msg = crypto.transcript(
            TAG_TOKEN, iid or self.iid, dev.device_id, crypto.sha256(raw), ts, nonce
        )
        return {
            "device_id": dev.device_id,
            "refresh_token": refresh,
            "ts": ts,
            "nonce": wire.b64u_encode(nonce),
            "sig": (signer or dev).sign(msg),
        }

    def self_revoke_body(self, dev: Device, *, ts: int | None = None) -> dict[str, Any]:
        assert dev.device_id is not None
        ts = self.clock.now if ts is None else ts
        msg = crypto.transcript(TAG_SELF_REVOKE, self.iid, dev.device_id, ts)
        return {"ts": ts, "sig": dev.sign(msg)}

    def headers(self, dev: Device, *, iid: str | None = None) -> dict[str, str]:
        assert dev.access is not None
        return {"Authorization": f"Bearer {dev.access}", "HMP-Instance": iid or self.iid}


def _user_exists(store: Store, user_id: str) -> bool:
    with store.transaction() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return row is not None


def url(path: str) -> str:
    return PATH_PREFIX + path


async def post(client: TestClient, path: str, body: Any, **kw: Any) -> tuple[int, Any]:
    raw = body if isinstance(body, bytes) else wire.dump_json(body)
    resp = await client.post(url(path), data=raw, **kw)
    return resp.status, await _json(resp)


async def get(client: TestClient, path: str, **kw: Any) -> tuple[int, Any]:
    resp = await client.get(url(path), **kw)
    return resp.status, await _json(resp)


async def _json(resp: Any) -> Any:
    text = await resp.text()
    return wire.parse_ijson(text.encode("utf-8"), max_bytes=1 << 20) if text else None


def run(env: Env, scenario: Callable[[TestClient], Awaitable[None]]) -> None:
    """Run `scenario(client)` against `env`'s app over plain HTTP on loopback."""

    async def main() -> None:
        test_server = TestServer(env.app())
        # The production access logger (SR-007), exactly as `HmpServer` configures it.
        await test_server.start_server(
            access_log_class=AllowListedAccessLogger,
            access_log=logging.getLogger(server.ACCESS_LOGGER_NAME),
        )
        async with TestClient(test_server) as client:
            await scenario(client)

    asyncio.run(main())


def code(body: Any) -> str | None:
    return body["error"]["code"] if isinstance(body, dict) and "error" in body else None


async def pair(env: Env, client: TestClient, dev: Device | None = None) -> Device:
    """P2 → P3 (confirm) → P4: a fully paired device with tokens."""
    dev = dev or Device()
    offer = env.offer()
    status, body = await post(client, "/pair/request", env.p2_body(dev, offer))
    assert status == 202, body
    dev.pairing_id, dev.ni = body["pairing_id"], wire.b64u_decode(body["ni"], length=32)
    env.confirm(dev)
    status, body = await post(client, "/pair/complete", env.p4_body(dev))
    assert status == 200, body
    dev.device_id, dev.refresh, dev.access = (
        body["device_id"],
        body["refresh_token"],
        body["access_token"],
    )
    return dev

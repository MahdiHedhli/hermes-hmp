"""T026: P5 and bearer auth (PR5-3..PR5-7, TR-5, research R16, CS-12, CS-13).

- reuse → family revoked and `401 revoked`;
- the retry grace survives a restart and keeps the original `access_expires_at`;
- A's token at B → `401 wrong_instance`, before any token lookup;
- the nonce is stored only after the signature verifies;
- PR5-3: an unsigned or badly signed request for a revoked device is `401 unauthenticated`;
- PR5-4: an owner mismatch leaves every token, family and device row unchanged;
- PR5-5: a changed `k_grace` → `503 retry_state_lost`;
- a store snapshot plus `k_grace` reproduces no valid token.
"""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import crypto, wire
from hmp_plugin.auth import Authenticator, bearer_token
from hmp_plugin.contract import (
    ACCESS_TTL_S,
    CLOCK_SKEW_S,
    REFRESH_ABSOLUTE_TTL_S,
    REFRESH_IDLE_TTL_S,
    REFRESH_RETRY_GRACE_S,
    TAG_GRACE,
    ErrorCode,
    HmpError,
)
from hmp_plugin.revoke import revoke_device
from hmp_plugin.tokens import PURPOSE_ACCESS, PURPOSE_REFRESH, derive_successor

from .hmp_kit import Device, Env, code, get, pair, post, run

TOKEN_TABLES = ("devices", "token_families", "refresh_tokens", "access_tokens", "pairings")


def dump(env: Env, tables: tuple[str, ...] = TOKEN_TABLES) -> dict[str, list[tuple[Any, ...]]]:
    out = {}
    with env.store.transaction() as conn:
        for table in tables:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608 - fixed names
            out[table] = sorted(tuple(r) for r in rows)
    return out


async def p5(env: Env, client: TestClient, dev: Device, **kw: Any) -> tuple[int, Any]:
    return await post(client, "/auth/token", env.p5_body(dev, **kw))


async def rotate(env: Env, client: TestClient, dev: Device) -> dict[str, Any]:
    status, body = await p5(env, client, dev)
    assert status == 200, body
    dev.refresh, dev.access = body["refresh_token"], body["access_token"]
    return body


# --------------------------------------------------------------------------------------------------
# Rotation, reuse and the retry grace (PR5-4, PR5-5)
# --------------------------------------------------------------------------------------------------


def test_rotation_issues_new_tokens(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        old_refresh, old_access = dev.refresh, dev.access
        env.clock.now += 5
        body = await rotate(env, client, dev)
        assert set(body) == {"access_token", "access_expires_at", "refresh_token"}
        assert body["access_expires_at"] == env.clock.now + ACCESS_TTL_S
        assert dev.refresh != old_refresh and dev.access != old_access
        status, _ = await get(client, "/bots", headers=env.headers(dev))
        assert status == 200
        old = env.store.get_refresh_token(crypto.sha256(wire.b64u_decode(old_refresh, length=32)))
        assert old["used_at"] == env.clock.now
        new_hash = crypto.sha256(wire.b64u_decode(dev.refresh, length=32))
        assert bytes(old["successor_hash"]) == new_hash

    run(env, scenario)


def test_reuse_revokes_the_family(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first = dev.refresh
        await rotate(env, client, dev)
        env.clock.now += REFRESH_RETRY_GRACE_S + 1
        status, body = await p5(env, client, dev, refresh=first)
        assert (status, code(body)) == (401, "revoked")
        status, body = await p5(env, client, dev)  # the successor is dead too
        assert (status, code(body)) == (401, "revoked")
        status, body = await get(client, "/bots", headers=env.headers(dev))
        assert (status, code(body)) == (401, "revoked")

    run(env, scenario)


def test_reuse_within_grace_after_the_successor_was_used_revokes(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first = dev.refresh
        await rotate(env, client, dev)
        await rotate(env, client, dev)  # the successor itself was used
        status, body = await p5(env, client, dev, refresh=first)
        assert (status, code(body)) == (401, "revoked")

    run(env, scenario)


def test_grace_retry_returns_the_same_successor(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first = dev.refresh
        body = await rotate(env, client, dev)
        env.clock.now += REFRESH_RETRY_GRACE_S  # still inside the grace
        status, again = await p5(env, client, dev, refresh=first)
        assert status == 200
        assert again == body  # same tokens, original access_expires_at
        assert again["access_expires_at"] == env.clock.now - REFRESH_RETRY_GRACE_S + ACCESS_TTL_S

    run(env, scenario)


def test_grace_retry_rechecks_liveness_against_a_revoke_landing_meanwhile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`exchange()`'s own earlier "is this family/device still live" checks run once, well before
    `_retry_or_reuse` is reached; without its own re-check, a revoke landing in that gap (an
    operator revoke, or a self-revoke from another request) would still let an in-grace retry hand
    back a working grant. There is no real concurrency in this single-process test, so the race is
    exercised directly: revoking as a side effect of the store read `exchange()` makes right before
    calling `_retry_or_reuse`, simulating a revoke that lands in exactly that gap."""
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first = dev.refresh
        await rotate(env, client, dev)  # successor established; `first` is now used, in-grace
        real_get_token_family = env.store.get_token_family

        def get_token_family_then_revoke(family_id: str) -> Any:
            row = real_get_token_family(family_id)
            revoke_device(env.store, dev.device_id, now=env.clock.now)
            return row

        monkeypatch.setattr(env.store, "get_token_family", get_token_family_then_revoke)
        status, body = await p5(env, client, dev, refresh=first)  # a grace-retry for `first`
        assert (status, code(body)) == (401, "revoked")

    run(env, scenario)


def test_reuse_path_rechecks_liveness_and_skips_a_redundant_revoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same race, on the reuse-detection branch (outside the grace, or the successor already
    used): the externally visible answer is `401 revoked` either way, but the re-check means a
    revoke that already landed is not redundantly re-applied (no second `token_families` update,
    no extra `refresh_reuse` audit row) by the reuse path's own write."""
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first = dev.refresh
        await rotate(env, client, dev)
        await rotate(env, client, dev)  # the successor itself is now also used -> reuse branch
        real_get_token_family = env.store.get_token_family

        def get_token_family_then_revoke(family_id: str) -> Any:
            row = real_get_token_family(family_id)
            revoke_device(env.store, dev.device_id, now=env.clock.now)
            return row

        monkeypatch.setattr(env.store, "get_token_family", get_token_family_then_revoke)
        with env.store.transaction() as conn:
            before_ids = {r["rowid"] for r in conn.execute("SELECT rowid FROM audit").fetchall()}
        status, body = await p5(env, client, dev, refresh=first)
        assert (status, code(body)) == (401, "revoked")
        # The injected revoke_device() call inserts its own "operator_revoke" audit row; the
        # reuse branch's own write must not additionally fire, since the live-check now short-
        # circuits it before reaching the "already handled, revoke again" UPDATE/INSERT pair.
        with env.store.transaction() as conn:
            rows = conn.execute("SELECT rowid, event FROM audit").fetchall()
        new_events = [r["event"] for r in rows if r["rowid"] not in before_ids]
        assert new_events == ["operator_revoke"]

    run(env, scenario)


def test_grace_survives_a_restart(tmp_path: Path) -> None:
    env = Env(tmp_path)
    dev = Device()
    state: dict[str, Any] = {}

    async def before(client: TestClient) -> None:
        await pair(env, client, dev)
        state["first"] = dev.refresh
        state["body"] = await rotate(env, client, dev)

    run(env, before)
    env.restart()
    env.clock.now += 10

    async def after(client: TestClient) -> None:
        status, body = await p5(env, client, dev, refresh=state["first"])
        assert status == 200
        assert body == state["body"]

    run(env, after)


def test_changed_k_grace_is_retry_state_lost(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first = dev.refresh
        await rotate(env, client, dev)
        env.custody.k_grace_path.write_bytes(b"\x07" * 32)
        status, body = await p5(env, client, dev, refresh=first)
        assert (status, code(body)) == (503, "retry_state_lost")

    run(env, scenario)


def test_missing_k_grace_is_regenerated_and_retry_state_lost(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        first = dev.refresh
        await rotate(env, client, dev)
        env.custody.k_grace_path.unlink()
        status, body = await p5(env, client, dev, refresh=first)
        assert (status, code(body)) == (503, "retry_state_lost")
        assert env.custody.k_grace_path.stat().st_size == 32
        await rotate(env, client, dev)  # the current token still rotates

    run(env, scenario)


def test_successor_derivation_is_from_the_raw_token() -> None:
    k = b"\x01" * 32
    raw = b"\x02" * 32
    expected = hmac.new(
        k,
        TAG_GRACE + crypto.length_prefixed(raw, "fam_x", "refresh"),
        hashlib.sha256,
    ).digest()
    assert derive_successor(k, raw, "fam_x", PURPOSE_REFRESH) == expected
    assert derive_successor(k, raw, "fam_x", PURPOSE_ACCESS) != expected
    with pytest.raises(ValueError):
        derive_successor(k, crypto.sha256(raw)[:31], "fam_x", PURPOSE_REFRESH)


def test_store_snapshot_plus_k_grace_reproduces_no_token(tmp_path: Path) -> None:
    env = Env(tmp_path)
    issued: list[str] = []

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        issued.extend([dev.refresh, dev.access])
        for _ in range(2):
            await rotate(env, client, dev)
            issued.extend([dev.refresh, dev.access])

    run(env, scenario)
    k_grace = env.identity.k_grace()
    with env.store.transaction() as conn:
        refresh = conn.execute("SELECT hash, family_id, successor_hash FROM refresh_tokens")
        rows = refresh.fetchall()
        access = {bytes(r[0]) for r in conn.execute("SELECT hash FROM access_tokens")}
    stored = {bytes(r["hash"]) for r in rows} | access
    stored |= {bytes(r["successor_hash"]) for r in rows if r["successor_hash"]}
    # Every derivation an attacker could run from store content alone.
    for row in rows:
        for seed in {bytes(row["hash"]), *(bytes(h) for h in stored)}:
            for purpose in (PURPOSE_REFRESH, PURPOSE_ACCESS):
                msg = crypto.transcript(TAG_GRACE, seed, str(row["family_id"]), purpose)
                guess = hmac.new(k_grace, msg, hashlib.sha256).digest()
                assert crypto.sha256(guess) not in stored
                assert wire.b64u_encode(guess) not in issued
    # No raw token, in bytes or in text, anywhere in the database file.
    blob = env.store_path.read_bytes()
    wal = env.store_path.with_name(env.store_path.name + "-wal")
    if wal.exists():
        blob += wal.read_bytes()
    for token in issued:
        assert wire.b64u_decode(token, length=32) not in blob
        assert token.encode("ascii") not in blob


# --------------------------------------------------------------------------------------------------
# PR5-3 order and disclosure
# --------------------------------------------------------------------------------------------------


def test_nonce_is_stored_only_after_the_signature_verifies(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        nonce = b"\x05" * 16
        status, body = await p5(env, client, dev, nonce=nonce, signer=Device())
        assert (status, code(body)) == (401, "unauthenticated")
        assert not env.store.nonce_seen(dev.device_id, nonce)
        assert env.store.count_p5_nonces() == 0
        await rotate_with(env, client, dev, nonce)
        assert env.store.nonce_seen(dev.device_id, nonce)
        status, body = await p5(env, client, dev, nonce=nonce)  # replay of the nonce
        assert (status, code(body)) == (401, "unauthenticated")

    async def rotate_with(env: Env, client: TestClient, dev: Device, nonce: bytes) -> None:
        status, body = await p5(env, client, dev, nonce=nonce)
        assert status == 200
        dev.refresh = body["refresh_token"]

    run(env, scenario)


def test_revoked_is_disclosed_only_to_a_signed_request(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        revoke_device(env.store, dev.device_id, now=env.clock.now)
        status, body = await p5(env, client, dev, signer=Device())  # badly signed
        assert (status, code(body)) == (401, "unauthenticated")
        unsigned = env.p5_body(dev)
        del unsigned["sig"]
        status, body = await post(client, "/auth/token", unsigned)
        assert (status, code(body)) == (401, "unauthenticated")
        status, body = await p5(env, client, dev)  # correctly signed
        assert (status, code(body)) == (401, "revoked")

    run(env, scenario)


def test_stale_ts_is_unauthenticated(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        for ts in (env.clock.now - CLOCK_SKEW_S - 1, env.clock.now + CLOCK_SKEW_S + 1):
            status, body = await p5(env, client, dev, ts=ts)
            assert (status, code(body)) == (401, "unauthenticated")
        await rotate(env, client, dev)

    run(env, scenario)


@pytest.mark.parametrize(
    "override",
    [
        {"device_id": "dev_short"},
        {"device_id": 5},
        {"refresh_token": "AAAA"},
        {"ts": 1.0},
        {"ts": True},
        {"nonce": wire.b64u_encode(b"\x00" * 15)},
        {"sig": "=="},
    ],
)
def test_malformed_members_are_uniform_401(tmp_path: Path, override: dict[str, Any]) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(client, "/auth/token", {**env.p5_body(dev), **override})
        assert (status, code(body)) == (401, "unauthenticated")

    run(env, scenario)


def test_owner_mismatch_changes_no_token_row(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        a = await pair(env, client)
        b = await pair(env, client)
        before = dump(env)
        nonces = env.store.count_p5_nonces()
        # B signs a correct request presenting A's refresh token.
        status, body = await p5(env, client, b, refresh=a.refresh)
        assert (status, code(body)) == (401, "unauthenticated")
        assert dump(env) == before
        assert env.store.count_p5_nonces() == nonces + 1  # only B's verified nonce (PR5-3 step 5)
        await rotate(env, client, a)  # A's token is still good
        await rotate(env, client, b)

    run(env, scenario)


# --------------------------------------------------------------------------------------------------
# PR5-6 binding, PR5-7 expiry, TR-5 instance header
# --------------------------------------------------------------------------------------------------


def test_refresh_token_is_never_an_access_token_and_vice_versa(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        headers = {"Authorization": f"Bearer {dev.refresh}", "HMP-Instance": env.iid}
        status, body = await get(client, "/bots", headers=headers)
        assert (status, code(body)) == (401, "unauthenticated")
        status, body = await p5(env, client, dev, refresh=dev.access)
        assert (status, code(body)) == (401, "unauthenticated")

    run(env, scenario)


def test_access_token_expiry(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.clock.now += ACCESS_TTL_S - 1
        assert (await get(client, "/bots", headers=env.headers(dev)))[0] == 200
        env.clock.now += 1
        status, body = await get(client, "/bots", headers=env.headers(dev))
        assert (status, code(body)) == (401, "unauthenticated")

    run(env, scenario)


def test_refresh_idle_expiry(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.clock.now += REFRESH_IDLE_TTL_S
        status, body = await p5(env, client, dev)
        assert (status, code(body)) == (401, "unauthenticated")

    run(env, scenario)


def test_refresh_family_absolute_expiry(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        created = env.clock.now
        step = REFRESH_IDLE_TTL_S - 86_400  # rotate before the idle limit every time
        while env.clock.now + step < created + REFRESH_ABSOLUTE_TTL_S:
            env.clock.now += step
            await rotate(env, client, dev)
        env.clock.now = created + REFRESH_ABSOLUTE_TTL_S
        status, body = await p5(env, client, dev)
        assert (status, code(body)) == (401, "unauthenticated")

    run(env, scenario)


def test_a_token_at_b_is_wrong_instance(tmp_path: Path) -> None:
    env_a = Env(tmp_path / "a")
    env_b = Env(tmp_path / "b")
    assert env_a.iid != env_b.iid
    dev = Device()

    async def at_a(client: TestClient) -> None:
        await pair(env_a, client, dev)

    run(env_a, at_a)

    async def at_b(client: TestClient) -> None:
        status, body = await get(client, "/bots", headers=env_a.headers(dev))  # pinned to A
        assert (status, code(body)) == (401, "wrong_instance")
        # Even with B's iid in the header, A's token is unknown at B.
        status, body = await get(client, "/bots", headers=env_a.headers(dev, iid=env_b.iid))
        assert (status, code(body)) == (401, "unauthenticated")
        # A's refresh token at B's P5.
        status, body = await post(client, "/auth/token", env_a.p5_body(dev))
        assert (status, code(body)) == (401, "unauthenticated")

    run(env_b, at_b)


def test_instance_header_checked_before_any_token_lookup(tmp_path: Path) -> None:
    env = Env(tmp_path)

    class CountingStore:
        def __init__(self, inner: Any) -> None:
            self.inner, self.lookups = inner, 0

        def access_authority_snapshot(self, h: bytes) -> Any:
            self.lookups += 1
            return self.inner.access_authority_snapshot(h)

        def __getattr__(self, name: str) -> Any:
            return getattr(self.inner, name)

    counting = CountingStore(env.store)
    auth = Authenticator(counting, env.iid, env.clock)
    token = "Bearer " + wire.b64u_encode(b"\x01" * 32)
    for header in (None, "", env.iid.upper(), env.iid[:-1] + "a", "x"):
        if header == env.iid:
            continue
        with pytest.raises(HmpError) as err:
            auth.authenticate(token, header)
        assert err.value.code is ErrorCode.WRONG_INSTANCE
    assert counting.lookups == 0
    with pytest.raises(HmpError) as err:
        auth.authenticate(token, env.iid)
    assert err.value.code is ErrorCode.UNAUTHENTICATED
    assert counting.lookups == 1


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "Bearer",
        "bearer " + wire.b64u_encode(b"\x01" * 32),
        "Bearer  " + wire.b64u_encode(b"\x01" * 32),
        "Bearer " + wire.b64u_encode(b"\x01" * 32) + "=",
        "Bearer " + wire.b64u_encode(b"\x01" * 31),
        "Basic abc",
    ],
)
def test_malformed_bearer(value: str | None) -> None:
    assert bearer_token(value) is None


def test_repeated_auth_headers_are_refused(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        headers = [
            ("Authorization", f"Bearer {dev.access}"),
            ("Authorization", f"Bearer {dev.access}"),
            ("HMP-Instance", env.iid),
        ]
        resp = await client.get("/hmp/v1/bots", headers=headers)
        assert resp.status == 401
        headers = [
            ("Authorization", f"Bearer {dev.access}"),
            ("HMP-Instance", env.iid),
            ("HMP-Instance", env.iid),
        ]
        resp = await client.get("/hmp/v1/bots", headers=headers)
        assert (resp.status, code(await resp.json())) == (401, "wrong_instance")

    run(env, scenario)


def test_revoked_device_bearer_is_revoked(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        revoke_device(env.store, dev.device_id, now=env.clock.now)
        status, body = await get(client, "/bots", headers=env.headers(dev))
        assert (status, code(body)) == (401, "revoked")

    run(env, scenario)


def test_rotation_is_one_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        before = dump(env)
        real = env.store.transaction

        class FailingConn:
            def __init__(self, conn: sqlite3.Connection) -> None:
                self.conn = conn

            def execute(self, sql: str, *args: Any) -> Any:
                if sql.startswith("INSERT INTO access_tokens"):
                    raise sqlite3.OperationalError("simulated failure")
                return self.conn.execute(sql, *args)

        import contextlib

        @contextlib.contextmanager
        def failing() -> Any:
            with real() as conn:
                yield FailingConn(conn)

        monkeypatch.setattr(env.store, "transaction", failing)
        status, body = await p5(env, client, dev)
        assert (status, code(body)) == (500, "other")
        monkeypatch.setattr(env.store, "transaction", real)
        assert dump(env) == before  # nothing half-rotated
        await rotate(env, client, dev)

    run(env, scenario)

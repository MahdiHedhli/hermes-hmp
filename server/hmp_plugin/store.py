"""SQLite store (WAL) and migrations per data-model.md. The ONLY module that writes the store.
No table holds message text, raw tokens, raw offer secrets or private keys. T021.

Every multi-step state change that must be atomic (PR5-4 single-transaction refresh rotation,
PR7-2/PR7-6 identity-change revocation) goes through `transaction()`, which is `BEGIN IMMEDIATE`
followed by `COMMIT` on a clean exit or `ROLLBACK` (re-raising) on any exception — so a failure
partway through a multi-statement change leaves the store exactly as it was before the change
started. Other server modules (`tokens.py`, `pairing.py`, `auth.py`, `identity.py`, ...) use the
named methods here, or `transaction()` directly for a change not yet named, but never open a
connection of their own: this module owns every write.
"""

from __future__ import annotations

import contextlib
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from pathlib import Path

from .contract import LIMITER_TABLE_MAX

SCHEMA_VERSION = 2

# Matches identity.py's DIR_MODE: the store lives beside the instance anchor, under the same
# 0700 `plugin-data/hmp/` directory (ID-2). On a fresh install nothing has created that directory
# yet -- `migrate()` is the first thing to touch it (adapter.py runs it before identity load).
DIR_MODE = 0o700

# The offer states data-model.md names explicitly (PR1-1, PR3-3).
OFFER_STATES: frozenset[str] = frozenset({"open", "claimed", "burned", "expired"})

# The device lifecycle states (data-model.md "Server identity-state transitions").
DEVICE_STATES: frozenset[str] = frozenset({"PENDING", "ACTIVE", "REVOKED"})

# The one pairing state this module treats as "still pending an outcome": the wire literal PR2-4
# returns while a pairing awaits the operator or a P4 poll. Every other pairing.py state (denied,
# expired, claimed/completed, ...) is already terminal and is left alone by
# `revoke_all_for_identity_change`. pairing.py (T025) owns the rest of the state machine; this
# module only ever compares against this one known-pending literal, never invents new states.
PAIRING_PENDING_STATE = "awaiting_operator"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    instance_epoch INTEGER NOT NULL DEFAULT 0,
    store_revocation_epoch INTEGER NOT NULL DEFAULT 0,
    schema_version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS offers (
    oid TEXT PRIMARY KEY,
    secret_hash BLOB NOT NULL,
    expires_at INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('open','claimed','burned','expired')),
    intended_user_id TEXT,
    failures INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pairings (
    pairing_id TEXT PRIMARY KEY,
    oid TEXT NOT NULL REFERENCES offers(oid),
    device_pub BLOB NOT NULL,
    device_name_sanitized TEXT NOT NULL,
    nd BLOB NOT NULL,
    ni BLOB NOT NULL,
    confirm_by INTEGER NOT NULL,
    state TEXT NOT NULL,
    sas_mismatches INTEGER NOT NULL DEFAULT 0,
    last_p4_ts INTEGER,
    first_issue_at INTEGER
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    device_fp TEXT NOT NULL,
    device_pub BLOB NOT NULL,
    label TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('PENDING','ACTIVE','REVOKED')),
    created_at INTEGER NOT NULL
);

-- A host decision for privileged phone controls. Missing rows defer to the legacy config list;
-- an explicit denial overrides that list. A new pairing receives a new device_id and never
-- inherits a previous device's decision, even if it uses the same phone or HMP user.
CREATE TABLE IF NOT EXISTS device_owner_controls (
    device_id TEXT PRIMARY KEY REFERENCES devices(device_id),
    allowed INTEGER NOT NULL CHECK (allowed IN (0, 1)),
    decided_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS token_families (
    family_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES devices(device_id),
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);

-- Tokens are stored only as SHA-256 hashes of their raw bytes (PR4-4); `successor_hash` is the
-- durable retry-grace successor hash (research R16, CS-13) -- never the raw successor, which is
-- re-derived from the raw presented token under k_grace (a secret file, never a store column).
CREATE TABLE IF NOT EXISTS refresh_tokens (
    hash BLOB PRIMARY KEY,
    family_id TEXT NOT NULL REFERENCES token_families(family_id),
    issued_at INTEGER NOT NULL,
    last_used_at INTEGER,
    used_at INTEGER,
    successor_hash BLOB
);

CREATE TABLE IF NOT EXISTS access_tokens (
    hash BLOB PRIMARY KEY,
    family_id TEXT NOT NULL REFERENCES token_families(family_id),
    device_id TEXT NOT NULL REFERENCES devices(device_id),
    iid TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);

-- LRU-bounded (TR-6); `record_p5_nonce` enforces LIMITER_TABLE_MAX. Stored only after the
-- signature verifies (PR5-3).
CREATE TABLE IF NOT EXISTS p5_nonces (
    device_id TEXT NOT NULL,
    nonce BLOB NOT NULL,
    seen_at INTEGER NOT NULL,
    PRIMARY KEY (device_id, nonce)
);

-- Never minted by a read (R11); written only by the pairing/authorize path.
CREATE TABLE IF NOT EXISTS chats (
    user_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    PRIMARY KEY (user_id, profile, conversation_id)
);

-- SR-12: no `head_row_id` column. `LineageInfo.head_row_id` (bridge.py) is used live, for each
-- read's own `head_message_id`; the persisted baseline never needs its OWN copy of it, because
-- reset detection compares `lineage_tip` and `active_row_count` only (RO-6/RO-8) -- storing it
-- here too was write-only dead data.
CREATE TABLE IF NOT EXISTS session_baselines (
    user_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    session_id TEXT NOT NULL,
    lineage_tip TEXT NOT NULL,
    active_row_count INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, profile)
);

-- Amendment A1 (session browsing, SES-1a): the opaque session_ref -> Hermes session_id mapping.
-- Minted the first time a session is included in a listing for (user_id, profile) and stable
-- thereafter, so the same Hermes session always yields the same ref, across restarts. Scoped
-- lookup: a ref presented under a different (user_id, profile) than it was minted for is not
-- found here, never disclosed as "exists but not yours" (mirrors ERR-2's `not_found`).
CREATE TABLE IF NOT EXISTS session_refs (
    ref TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    session_id TEXT NOT NULL,
    first_seen_at INTEGER NOT NULL,
    UNIQUE (user_id, profile, session_id)
);

-- Amendment A1 (SES-2): generalizes session_baselines with an extra session_id key column, one
-- row per (user, profile, other session) rather than one per (user, profile). The reset-reason
-- comparison (`reads.py`'s `_lineage_reset`) is reused unchanged against this table.
CREATE TABLE IF NOT EXISTS other_session_baselines (
    user_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    session_id TEXT NOT NULL,
    lineage_tip TEXT NOT NULL,
    active_row_count INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, profile, session_id)
);

-- Amendment F2 (direct send, HMP_V1.md §7a DS-3): reserved atomically BEFORE the loopback call to
-- api_server, never after -- closing the timing gap an "record after success" design would leave
-- open across a timeout or crash. No message text: only the SHA-256 `payload_hash` over
-- (text, expected_head) (SEC-4). `result_json` holds the wire-shaped outcome once definitive
-- (DirectSendOutcome, contract.py), so a same-cmid replay after a definitive outcome returns the
-- stored result without a second loopback call.
CREATE TABLE IF NOT EXISTS direct_send_idempotency (
    iid TEXT NOT NULL,
    user_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    cmid TEXT NOT NULL,
    payload_hash BLOB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','accepted','rejected','unknown')),
    result_json TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (iid, user_id, profile, cmid)
);

-- Amendment F3 (Phone chat, HMP_V1.md §7b AP-6): same shape as direct_send_idempotency, hash of
-- `text` only (no expected_head). No message text is stored (SEC-4).
CREATE TABLE IF NOT EXISTS phone_send_idempotency (
    iid TEXT NOT NULL,
    user_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    cmid TEXT NOT NULL,
    payload_hash BLOB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','submitted','rejected','unknown')),
    result_json TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (iid, user_id, profile, cmid)
);

CREATE TABLE IF NOT EXISTS roster_state (
    user_id TEXT PRIMARY KEY,
    served_set_hash TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);

-- SR-5: the last time the P6 inert trigger was actually sent for this (user, profile), so
-- `authorize.py` can hold a cooldown and skip re-triggering Hermes's own rate-limited pairing
-- flow inside it.
CREATE TABLE IF NOT EXISTS authorize_cooldowns (
    user_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    last_trigger_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, profile)
);

-- SEC-4: no secrets, no message text. Only an 8-char id prefix and an outcome code.
CREATE TABLE IF NOT EXISTS audit (
    ts INTEGER NOT NULL,
    event TEXT NOT NULL,
    id_prefix8 TEXT,
    outcome TEXT NOT NULL
);
"""


_CMID_COPY_SQL = (
    "INSERT INTO direct_send_idempotency_v2 "
    "(iid, user_id, profile, cmid, payload_hash, status, result_json, created_at, updated_at) "
    "SELECT iid, user_id, profile, cmid, payload_hash, status, result_json, created_at, updated_at "
    "FROM direct_send_idempotency"
)


def _widen_cmid_status(conn: sqlite3.Connection) -> None:
    """Review round 3: `unknown` is a stored status. `CREATE TABLE IF NOT EXISTS` does not alter
    a CHECK constraint already written by an earlier build, so rebuild the table when its DDL
    does not yet name `unknown`."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'direct_send_idempotency'"
    ).fetchone()
    if row is None:
        return
    ddl = row["sql"] or ""
    if "'unknown'" in ddl:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "CREATE TABLE direct_send_idempotency_v2 ("
            "iid TEXT NOT NULL, user_id TEXT NOT NULL, profile TEXT NOT NULL, cmid TEXT NOT NULL, "
            "payload_hash BLOB NOT NULL, "
            "status TEXT NOT NULL CHECK (status IN ('pending','accepted','rejected','unknown')), "
            "result_json TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, "
            "PRIMARY KEY (iid, user_id, profile, cmid))"
        )
        conn.execute(_CMID_COPY_SQL)
        conn.execute("DROP TABLE direct_send_idempotency")
        conn.execute("ALTER TABLE direct_send_idempotency_v2 RENAME TO direct_send_idempotency")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


class Store:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: sqlite3.Connection | None = None
        # One connection, `check_same_thread=False`, used from `asyncio.to_thread`.
        # sqlite3 forbids overlapping `BEGIN IMMEDIATE` on that connection. This lock serializes
        # every `transaction()` so two reserves cannot interleave their statements.
        self._write_lock = threading.Lock()

    def migrate(self) -> None:
        """Open the database (creating it if needed) and apply the schema. Idempotent: safe to
        call again against an already-migrated store.

        Creates the store's parent directory (mode 0700) first if it is missing: on a fresh
        install nothing has created `plugin-data/hmp/` yet, and `sqlite3.connect` does not create
        missing parent directories on its own. Only the *creation* is done here -- an already
        existing parent directory is left exactly as it is, never chmod'd back to 0700. Callers
        (cli.py's SR-7 `read_listener_record` check) rely on being able to detect an unsafe
        directory there and refuse; silently repairing its mode on every `migrate()` call would
        launder that check away."""
        parent = self._path.parent
        with contextlib.suppress(FileExistsError):
            parent.mkdir(mode=DIR_MODE, parents=True)
        # This connection is shared by auth/ownership readers in worker threads.
        # CPython's statement cache can mix concurrent result rows (GH-118172).
        # Never rely on that optimization for authority-binding reads.
        conn = sqlite3.connect(
            str(self._path), isolation_level=None, check_same_thread=False, cached_statements=0
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(_SCHEMA)
        _widen_cmid_status(conn)
        conn.execute(
            "INSERT OR IGNORE INTO meta (id, instance_epoch, store_revocation_epoch, "
            "schema_version) VALUES (1, 0, 0, ?)",
            (SCHEMA_VERSION,),
        )
        # The new table above is additive. Record the upgrade after it exists, including for
        # stores opened by older HMP builds with schema_version=1.
        conn.execute(
            "UPDATE meta SET schema_version = ? WHERE id = 1 AND schema_version < ?",
            (SCHEMA_VERSION, SCHEMA_VERSION),
        )
        self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Store.migrate() must run before use")
        return self._conn

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """One atomic unit of work over the raw connection (research R7: `BEGIN IMMEDIATE`).
        Commits on a clean exit; on any exception, rolls back and re-raises, so nothing the block
        did is visible afterward."""
        with self._write_lock:
            conn = self._require_conn()
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    # ------------------------------------------------------------------------------------------
    # meta / identity (ID-2; the `IdentityStore` surface `identity.py`/T022 uses)
    # ------------------------------------------------------------------------------------------

    def instance_epoch(self) -> int:
        row = (
            self._require_conn().execute("SELECT instance_epoch FROM meta WHERE id = 1").fetchone()
        )
        return int(row["instance_epoch"]) if row else 0

    def revocation_epoch(self) -> int:
        """`meta.store_revocation_epoch`. 0 on a fresh store."""
        row = (
            self._require_conn()
            .execute("SELECT store_revocation_epoch FROM meta WHERE id = 1")
            .fetchone()
        )
        return int(row["store_revocation_epoch"]) if row else 0

    def revoke_all_for_identity_change(self, now: int) -> int:
        """PR7-2 / PR7-6, as one transaction:

        - every device becomes REVOKED;
        - every token family gets `revoked_at = now` (its access tokens stop working: `auth.py`
          requires an ACTIVE device and an unrevoked family on every check);
        - every open offer becomes expired;
        - every pairing still awaiting an outcome becomes expired;
        - `meta.store_revocation_epoch` goes up by 1, even when nothing above needed changing;
        - one audit row records the event only (no ids, no secrets).

        Returns the new epoch.
        """
        with self.transaction() as conn:
            conn.execute("UPDATE devices SET state = 'REVOKED' WHERE state != 'REVOKED'")
            conn.execute(
                "UPDATE token_families SET revoked_at = ? WHERE revoked_at IS NULL", (now,)
            )
            conn.execute("UPDATE offers SET state = 'expired' WHERE state = 'open'")
            conn.execute(
                "UPDATE pairings SET state = 'expired' WHERE state = ?", (PAIRING_PENDING_STATE,)
            )
            conn.execute(
                "UPDATE meta SET store_revocation_epoch = store_revocation_epoch + 1 WHERE id = 1"
            )
            conn.execute(
                "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, NULL, 'ok')",
                (now, "identity_change_revoke_all"),
            )
            row = conn.execute("SELECT store_revocation_epoch FROM meta WHERE id = 1").fetchone()
            return int(row["store_revocation_epoch"])

    # ------------------------------------------------------------------------------------------
    # offers / pairings (PR1-1, PR2-5 durable nonces, PR3-3, PR4-3 last_p4_ts)
    # ------------------------------------------------------------------------------------------

    def insert_offer(
        self,
        oid: str,
        secret_hash: bytes,
        expires_at: int,
        *,
        intended_user_id: str | None = None,
    ) -> None:
        if len(secret_hash) != 32:
            raise ValueError("secret_hash must be a 32-byte SHA-256 digest")
        self._require_conn().execute(
            "INSERT INTO offers (oid, secret_hash, expires_at, state, intended_user_id, failures) "
            "VALUES (?, ?, ?, 'open', ?, 0)",
            (oid, secret_hash, expires_at, intended_user_id),
        )

    def get_offer(self, oid: str) -> sqlite3.Row | None:
        return self._require_conn().execute("SELECT * FROM offers WHERE oid = ?", (oid,)).fetchone()

    def insert_pairing(
        self,
        pairing_id: str,
        oid: str,
        device_pub: bytes,
        device_name_sanitized: str,
        nd: bytes,
        ni: bytes,
        confirm_by: int,
        *,
        state: str = PAIRING_PENDING_STATE,
    ) -> None:
        """PR2-5: `nd`/`ni` are persisted here, with the pairing record, so a gateway restart
        between P2 and P4 does not lose them."""
        self._require_conn().execute(
            "INSERT INTO pairings (pairing_id, oid, device_pub, device_name_sanitized, nd, ni, "
            "confirm_by, state, sas_mismatches, last_p4_ts, first_issue_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)",
            (pairing_id, oid, device_pub, device_name_sanitized, nd, ni, confirm_by, state),
        )

    def get_pairing(self, pairing_id: str) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute("SELECT * FROM pairings WHERE pairing_id = ?", (pairing_id,))
            .fetchone()
        )

    def record_p4_ts(self, pairing_id: str, ts: int) -> None:
        """PR4-3: the last accepted `ts`, so the next one must be strictly greater."""
        self._require_conn().execute(
            "UPDATE pairings SET last_p4_ts = ? WHERE pairing_id = ?", (ts, pairing_id)
        )

    # ------------------------------------------------------------------------------------------
    # users / devices / token families
    # ------------------------------------------------------------------------------------------

    def insert_user(self, user_id: str, label: str, created_at: int) -> None:
        self._require_conn().execute(
            "INSERT INTO users (user_id, label, created_at) VALUES (?, ?, ?)",
            (user_id, label, created_at),
        )

    def insert_device(
        self,
        device_id: str,
        user_id: str,
        device_fp: str,
        device_pub: bytes,
        label: str,
        created_at: int,
        *,
        state: str = "PENDING",
    ) -> None:
        if state not in DEVICE_STATES:
            raise ValueError(f"unknown device state {state!r}")
        self._require_conn().execute(
            "INSERT INTO devices (device_id, user_id, device_fp, device_pub, label, state, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (device_id, user_id, device_fp, device_pub, label, state, created_at),
        )

    def get_device(self, device_id: str) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
            .fetchone()
        )

    def owner_controls_decision(self, device_id: str) -> bool | None:
        """Return the host's explicit decision, or None for a legacy device without one."""
        row = (
            self._require_conn()
            .execute("SELECT allowed FROM device_owner_controls WHERE device_id = ?", (device_id,))
            .fetchone()
        )
        return bool(row["allowed"]) if row is not None else None

    def readiness_owner_controls_value(self, device_id: str) -> int | None:
        """Strict readiness-only read; unlike the operational helper, never coerces bad data."""
        row = (
            self._require_conn()
            .execute("SELECT allowed FROM device_owner_controls WHERE device_id = ?", (device_id,))
            .fetchone()
        )
        if row is None:
            return None
        value = row["allowed"]
        if type(value) is not int or value not in (0, 1):
            raise ValueError("invalid controls decision")
        return value

    def set_owner_controls(self, device_id: str, *, allowed: bool, now: int) -> bool:
        """Set a per-device host decision. Refuse missing or revoked devices."""
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT state FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
            if row is None or row["state"] != "ACTIVE":
                return False
            conn.execute(
                "INSERT INTO device_owner_controls (device_id, allowed, decided_at) "
                "VALUES (?, ?, ?) ON CONFLICT(device_id) DO UPDATE SET "
                "allowed = excluded.allowed, decided_at = excluded.decided_at",
                (device_id, int(allowed), now),
            )
            return True

    def set_device_state(self, device_id: str, state: str) -> None:
        if state not in DEVICE_STATES:
            raise ValueError(f"unknown device state {state!r}")
        self._require_conn().execute(
            "UPDATE devices SET state = ? WHERE device_id = ?", (state, device_id)
        )

    def insert_token_family(self, family_id: str, device_id: str, created_at: int) -> None:
        self._require_conn().execute(
            "INSERT INTO token_families (family_id, device_id, created_at, revoked_at) "
            "VALUES (?, ?, ?, NULL)",
            (family_id, device_id, created_at),
        )

    def revoke_family(self, family_id: str, now: int) -> None:
        self._require_conn().execute(
            "UPDATE token_families SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
            (now, family_id),
        )

    def revoke_families_for_device(self, device_id: str, now: int) -> None:
        self._require_conn().execute(
            "UPDATE token_families SET revoked_at = ? WHERE device_id = ? AND revoked_at IS NULL",
            (now, device_id),
        )

    def get_token_family(self, family_id: str) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute("SELECT * FROM token_families WHERE family_id = ?", (family_id,))
            .fetchone()
        )

    # ------------------------------------------------------------------------------------------
    # refresh / access tokens (PR4-4, PR5-4..PR5-7; hashes only, never raw bytes)
    # ------------------------------------------------------------------------------------------

    def insert_refresh_token(self, token_hash: bytes, family_id: str, issued_at: int) -> None:
        if len(token_hash) != 32:
            raise ValueError("token_hash must be a 32-byte SHA-256 digest")
        self._require_conn().execute(
            "INSERT INTO refresh_tokens (hash, family_id, issued_at, last_used_at, used_at, "
            "successor_hash) VALUES (?, ?, ?, NULL, NULL, NULL)",
            (token_hash, family_id, issued_at),
        )

    def get_refresh_token(self, token_hash: bytes) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute("SELECT * FROM refresh_tokens WHERE hash = ?", (token_hash,))
            .fetchone()
        )

    def insert_access_token(
        self, token_hash: bytes, family_id: str, device_id: str, iid: str, expires_at: int
    ) -> None:
        if len(token_hash) != 32:
            raise ValueError("token_hash must be a 32-byte SHA-256 digest")
        self._require_conn().execute(
            "INSERT INTO access_tokens (hash, family_id, device_id, iid, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (token_hash, family_id, device_id, iid, expires_at),
        )

    def get_access_token(self, token_hash: bytes) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute("SELECT * FROM access_tokens WHERE hash = ?", (token_hash,))
            .fetchone()
        )

    def rotate_refresh_token(
        self,
        *,
        old_hash: bytes,
        family_id: str,
        new_hash: bytes,
        successor_hash: bytes,
        issued_at: int,
    ) -> None:
        """PR5-4: single-transaction rotation. Marks the presented token used, records the
        successor hash it produced (research R16; the raw successor is never stored), and
        inserts the new refresh token row."""
        with self.transaction() as conn:
            conn.execute(
                "UPDATE refresh_tokens SET used_at = ?, successor_hash = ? WHERE hash = ?",
                (issued_at, successor_hash, old_hash),
            )
            conn.execute(
                "INSERT INTO refresh_tokens (hash, family_id, issued_at, last_used_at, used_at, "
                "successor_hash) VALUES (?, ?, ?, NULL, NULL, NULL)",
                (new_hash, family_id, issued_at),
            )

    # ------------------------------------------------------------------------------------------
    # p5 nonces (LRU-bounded, TR-6; stored only after signature verification, PR5-3)
    # ------------------------------------------------------------------------------------------

    def nonce_seen(self, device_id: str, nonce: bytes) -> bool:
        row = (
            self._require_conn()
            .execute(
                "SELECT 1 FROM p5_nonces WHERE device_id = ? AND nonce = ?", (device_id, nonce)
            )
            .fetchone()
        )
        return row is not None

    def record_p5_nonce(
        self, device_id: str, nonce: bytes, seen_at: int, *, bound: int = LIMITER_TABLE_MAX
    ) -> None:
        """Inserted only after the caller has verified the request's signature (PR5-3). Enforces
        the LRU bound (TR-6): once the table exceeds `bound` rows, the oldest (by `seen_at`, then
        insertion order) are trimmed back down to it."""
        conn = self._require_conn()
        conn.execute(
            "INSERT OR IGNORE INTO p5_nonces (device_id, nonce, seen_at) VALUES (?, ?, ?)",
            (device_id, nonce, seen_at),
        )
        (count,) = conn.execute("SELECT COUNT(*) FROM p5_nonces").fetchone()
        if count > bound:
            conn.execute(
                "DELETE FROM p5_nonces WHERE rowid IN ("
                "  SELECT rowid FROM p5_nonces ORDER BY seen_at ASC, rowid ASC LIMIT ?"
                ")",
                (count - bound,),
            )

    def count_p5_nonces(self) -> int:
        (count,) = self._require_conn().execute("SELECT COUNT(*) FROM p5_nonces").fetchone()
        return int(count)

    # ------------------------------------------------------------------------------------------
    # chats / session baselines / roster (RO-6, RO-8, R11: never minted by a read)
    # ------------------------------------------------------------------------------------------

    def set_chat(self, user_id: str, profile: str, conversation_id: str, chat_id: str) -> None:
        self._require_conn().execute(
            "INSERT INTO chats (user_id, profile, conversation_id, chat_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (user_id, profile, conversation_id) "
            "DO UPDATE SET chat_id = excluded.chat_id",
            (user_id, profile, conversation_id, chat_id),
        )

    def get_chat(self, user_id: str, profile: str, conversation_id: str) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute(
                "SELECT * FROM chats WHERE user_id = ? AND profile = ? AND conversation_id = ?",
                (user_id, profile, conversation_id),
            )
            .fetchone()
        )

    def set_session_baseline(
        self,
        user_id: str,
        profile: str,
        session_id: str,
        lineage_tip: str,
        active_row_count: int,
        updated_at: int,
    ) -> None:
        self._require_conn().execute(
            "INSERT INTO session_baselines (user_id, profile, session_id, lineage_tip, "
            "active_row_count, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (user_id, profile) DO UPDATE SET "
            "session_id = excluded.session_id, lineage_tip = excluded.lineage_tip, "
            "active_row_count = excluded.active_row_count, updated_at = excluded.updated_at",
            (user_id, profile, session_id, lineage_tip, active_row_count, updated_at),
        )

    def get_session_baseline(self, user_id: str, profile: str) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute(
                "SELECT * FROM session_baselines WHERE user_id = ? AND profile = ?",
                (user_id, profile),
            )
            .fetchone()
        )

    # ------------------------------------------------------------------------------------------
    # Amendment A1 (session browsing, SES-1a, SES-2): session_refs, other_session_baselines
    # ------------------------------------------------------------------------------------------

    def mint_or_get_session_ref(
        self, user_id: str, profile: str, session_id: str, candidate_ref: str, now: int
    ) -> str:
        """Atomically mints `candidate_ref` for `(user_id, profile, session_id)` unless a ref was
        already minted for that same triple, in which case the existing ref is returned instead
        (SES-1a: "same session ⇒ same ref on every later listing"). `candidate_ref` is generated
        by the caller (a fresh random id) and is discarded, never reused for another session,
        when a race loses; ref generation is O(1) and unconditional generation is simpler than a
        SELECT-then-maybe-INSERT with retry."""
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO session_refs (ref, user_id, profile, session_id, first_seen_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, profile, session_id) DO NOTHING",
                (candidate_ref, user_id, profile, session_id, now),
            )
            row = conn.execute(
                "SELECT ref FROM session_refs WHERE user_id = ? AND profile = ? AND session_id = ?",
                (user_id, profile, session_id),
            ).fetchone()
        assert row is not None  # the INSERT above, or an earlier one, always leaves a row
        return str(row["ref"])

    def resolve_session_ref(self, user_id: str, profile: str, ref: str) -> str | None:
        """The Hermes session id for `ref`, scoped to `(user_id, profile)`. A ref minted for a
        different user or profile -- or an unknown ref -- is `None` (SES-1a scoped lookup)."""
        row = (
            self._require_conn()
            .execute(
                "SELECT session_id FROM session_refs WHERE ref = ? AND user_id = ? AND profile = ?",
                (ref, user_id, profile),
            )
            .fetchone()
        )
        return str(row["session_id"]) if row is not None else None

    def get_other_session_baseline(
        self, user_id: str, profile: str, session_id: str
    ) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute(
                "SELECT * FROM other_session_baselines "
                "WHERE user_id = ? AND profile = ? AND session_id = ?",
                (user_id, profile, session_id),
            )
            .fetchone()
        )

    def set_other_session_baseline(
        self,
        user_id: str,
        profile: str,
        session_id: str,
        lineage_tip: str,
        active_row_count: int,
        updated_at: int,
    ) -> None:
        self._require_conn().execute(
            "INSERT INTO other_session_baselines (user_id, profile, session_id, lineage_tip, "
            "active_row_count, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (user_id, profile, session_id) DO UPDATE SET "
            "lineage_tip = excluded.lineage_tip, active_row_count = excluded.active_row_count, "
            "updated_at = excluded.updated_at",
            (user_id, profile, session_id, lineage_tip, active_row_count, updated_at),
        )

    # ------------------------------------------------------------------------------------------
    # Amendment F2 (direct send, HMP_V1.md §7a DS-3): direct_send_idempotency
    # ------------------------------------------------------------------------------------------

    def reserve_cmid(
        self,
        iid: str,
        user_id: str,
        profile: str,
        cmid: str,
        payload_hash: bytes,
        now: int,
    ) -> tuple[sqlite3.Row, bool]:
        """Atomically reserve `cmid` in scope `(iid, user_id, profile)`, BEFORE any loopback call
        (DS-3: "reserved atomically before... not after"). Returns `(row, inserted)`: `row` is the
        resulting record whether it was just inserted or already existed; `inserted` is `True` only
        when THIS call is the one that created it (`cursor.rowcount` of the `INSERT ... ON CONFLICT
        DO NOTHING` statement itself -- 1 when it inserted, 0 when a conflict left it untouched).

        Review BLOCKER #1: the caller needs `inserted` to tell "a brand-new reservation" from "a
        retry that found an existing `pending` row" -- only the former may ever call the network;
        the latter must reuse whatever is already in flight (or already recorded) for that cmid,
        never call `api_server` a second time."""
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO direct_send_idempotency "
                "(iid, user_id, profile, cmid, payload_hash, status, result_json, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?) "
                "ON CONFLICT (iid, user_id, profile, cmid) DO NOTHING",
                (iid, user_id, profile, cmid, payload_hash, now, now),
            )
            inserted = cur.rowcount == 1
            row = conn.execute(
                "SELECT * FROM direct_send_idempotency "
                "WHERE iid = ? AND user_id = ? AND profile = ? AND cmid = ?",
                (iid, user_id, profile, cmid),
            ).fetchone()
        assert row is not None  # the INSERT above, or an earlier one, always leaves a row
        return row, inserted

    def get_cmid_record(
        self, iid: str, user_id: str, profile: str, cmid: str
    ) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute(
                "SELECT * FROM direct_send_idempotency "
                "WHERE iid = ? AND user_id = ? AND profile = ? AND cmid = ?",
                (iid, user_id, profile, cmid),
            )
            .fetchone()
        )

    def delete_cmid_reservation(self, iid: str, user_id: str, profile: str, cmid: str) -> None:
        """DS-4: releases a reservation HMP is CERTAIN never reached the loopback call (a pre-call
        guard failure -- `no_bot_chat`/`session_busy`). Unlike `finalize_cmid`, this is a real
        delete: the same cmid can then be reserved fresh by a plain retry, never blocked by a
        stale 'rejected' row for an attempt Hermes never even saw. NEVER used for a genuine
        post-call ambiguity (DS-3: those stay 'pending', reconciled read-only via DS-8)."""
        self._require_conn().execute(
            "DELETE FROM direct_send_idempotency "
            "WHERE iid = ? AND user_id = ? AND profile = ? AND cmid = ?",
            (iid, user_id, profile, cmid),
        )

    def finalize_cmid(
        self,
        iid: str,
        user_id: str,
        profile: str,
        cmid: str,
        *,
        status: str,
        result_json: str | None,
        updated_at: int,
    ) -> None:
        """Records an outcome (`status` in `'accepted'`/`'rejected'`/`'unknown'`). `'unknown'`
        is the round-3 terminal state for a task that ended before a definitive Hermes answer
        (cancel, or any exception) — never left `'pending'`. A still-running task stays
        `'pending'` until it concludes. Never auto-resent."""
        self._require_conn().execute(
            "UPDATE direct_send_idempotency SET status = ?, result_json = ?, updated_at = ? "
            "WHERE iid = ? AND user_id = ? AND profile = ? AND cmid = ?",
            (status, result_json, updated_at, iid, user_id, profile, cmid),
        )

    def reserve_phone_cmid(
        self,
        iid: str,
        user_id: str,
        profile: str,
        cmid: str,
        payload_hash: bytes,
        now: int,
    ) -> tuple[sqlite3.Row, bool]:
        """AP-6: reserve before `handle_message`. `(row, inserted)` matches `reserve_cmid`."""
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO phone_send_idempotency "
                "(iid, user_id, profile, cmid, payload_hash, status, result_json, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?) "
                "ON CONFLICT (iid, user_id, profile, cmid) DO NOTHING",
                (iid, user_id, profile, cmid, payload_hash, now, now),
            )
            inserted = cur.rowcount == 1
            row = conn.execute(
                "SELECT * FROM phone_send_idempotency "
                "WHERE iid = ? AND user_id = ? AND profile = ? AND cmid = ?",
                (iid, user_id, profile, cmid),
            ).fetchone()
        assert row is not None
        return row, inserted

    def finalize_phone_cmid(
        self,
        iid: str,
        user_id: str,
        profile: str,
        cmid: str,
        *,
        status: str,
        result_json: str | None,
        updated_at: int,
    ) -> None:
        self._require_conn().execute(
            "UPDATE phone_send_idempotency SET status = ?, result_json = ?, updated_at = ? "
            "WHERE iid = ? AND user_id = ? AND profile = ? AND cmid = ?",
            (status, result_json, updated_at, iid, user_id, profile, cmid),
        )

    def set_roster_state(self, user_id: str, served_set_hash: str, updated_at: int) -> None:
        self._require_conn().execute(
            "INSERT INTO roster_state (user_id, served_set_hash, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "served_set_hash = excluded.served_set_hash, updated_at = excluded.updated_at",
            (user_id, served_set_hash, updated_at),
        )

    def get_roster_state(self, user_id: str) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute("SELECT * FROM roster_state WHERE user_id = ?", (user_id,))
            .fetchone()
        )

    def get_authorize_cooldown(self, user_id: str, profile: str) -> sqlite3.Row | None:
        return (
            self._require_conn()
            .execute(
                "SELECT * FROM authorize_cooldowns WHERE user_id = ? AND profile = ?",
                (user_id, profile),
            )
            .fetchone()
        )

    def set_authorize_cooldown(self, user_id: str, profile: str, last_trigger_at: int) -> None:
        self._require_conn().execute(
            "INSERT INTO authorize_cooldowns (user_id, profile, last_trigger_at) "
            "VALUES (?, ?, ?) ON CONFLICT (user_id, profile) DO UPDATE SET "
            "last_trigger_at = excluded.last_trigger_at",
            (user_id, profile, last_trigger_at),
        )

    # ------------------------------------------------------------------------------------------
    # audit (SEC-4: event + 8-char id prefix + outcome code only; never a secret or message text)
    # ------------------------------------------------------------------------------------------

    def write_audit(
        self, ts: int, event: str, outcome: str, *, id_prefix8: str | None = None
    ) -> None:
        if id_prefix8 is not None and len(id_prefix8) != 8:
            raise ValueError("id_prefix8 must be exactly 8 characters")
        self._require_conn().execute(
            "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
            (ts, event, id_prefix8, outcome),
        )

    def audit_events(self) -> Sequence[sqlite3.Row]:
        return self._require_conn().execute("SELECT * FROM audit ORDER BY ts ASC").fetchall()

-- Historical schema 1, captured unchanged from public HMP commit 88ddee2.

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

INSERT INTO meta VALUES (1, 7, 4, 1);

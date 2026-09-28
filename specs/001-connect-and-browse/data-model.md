# HMP server data model

This public extract covers the server-owned schema and compatibility lists. App domain models and owner decisions remain in the app repository.

## Server (`server/hmp_plugin`, SQLite store)

New relative to the spike, or changed by contract: marked **(new)** / **(changed)**.

| Table | Key fields | Notes |
|---|---|---|
| `meta` | `instance_epoch`, `store_revocation_epoch`, `schema_version` | ID-2 |
| `offers` | `oid`, `secret_hash`, `expires_at`, `state` (`open`/`claimed`/`burned`/`expired`), `intended_user_id`?, `failures` | PR1-1, PR3-3 **(changed: intended user)** |
| `pairings` | `pairing_id`, `oid`, `device_pub`, `device_name_sanitized`, `nd`, `ni` **(new, PR2-5)**, `confirm_by`, `state`, `sas_mismatches`, `last_p4_ts` **(new, PR4-3)**, `first_issue_at` | |
| `users` | `user_id` (`hmpu_…`), `label`, `created_at` | Gateway users (OD-5) |
| `devices` | `device_id`, `user_id`, `device_fp`, `device_pub`, `label`, `state` (`PENDING`/`ACTIVE`/`REVOKED`), `created_at` | |
| `token_families` | `family_id`, `device_id`, `created_at`, `revoked_at` | |
| `refresh_tokens` | `hash`, `family_id`, `issued_at`, `last_used_at`, `used_at`, `successor_hash` **(new, PR5-5 durable grace)** | Single-transaction rotation (PR5-4). The successor is re-derived from the raw presented token under `k_grace`, never stored raw (research R16, CS-13). `k_grace` is a secret file (0600, outside every Hermes home), not a table column |
| `access_tokens` | `hash`, `family_id`, `device_id`, `iid`, `expires_at` | PR5-6 |
| `p5_nonces` | `device_id`, `nonce`, `seen_at` | Stored only after the signature verifies; LRU-bounded (PR5-3, TR-6) |
| `chats` | `user_id`, `profile`, `conversation_id` (= `default`), `chat_id` | Never minted by a read (R11) |
| `session_baselines` **(new)** | `user_id`, `profile`, `session_id`, `lineage_tip`, `head_row_id`, `active_row_count`, `updated_at` | RO-6, RO-8 |
| `session_refs` **(new, amendment A1)** | `ref`, `user_id`, `profile`, `session_id`, `first_seen_at` | SES-1a; `UNIQUE (user_id, profile, session_id)` so the same session always yields the same ref; scoped lookup by `(ref, user_id, profile)` |
| `other_session_baselines` **(new, amendment A1)** | `user_id`, `profile`, `session_id`, `lineage_tip`, `active_row_count`, `updated_at` | SES-2; generalizes `session_baselines` with an extra `session_id` key column, one row per foreign session browsed, not per `(user, profile)` |
| `direct_send_idempotency` **(new, amendment F2, DS-3)** | `iid`, `user_id`, `profile`, `cmid`, `payload_hash`, `status` (`pending`/`accepted`/`rejected`), `result_json`, `created_at`, `updated_at` | `PRIMARY KEY (iid, user_id, profile, cmid)`. Reserved atomically **before** the loopback call (DS-3); the record never holds message text, only the SHA-256 `payload_hash` (SEC-4) |
| `roster_state` | `user_id`, `served_set_hash`, `updated_at` | RO-2 baseline |
| `audit` | `ts`, `event`, `id_prefix8`, `outcome` | SEC-4: no secrets, no text |

No table holds message text, raw tokens, raw offer secrets or private keys. The instance key lives in
plugin data with a host binding (ID-2).

**Server identity-state transitions**: devices `PENDING → ACTIVE → REVOKED`, and `PENDING → REVOKED`
on deny, expiry or rotation. On `instance rotate-key`, every device is revoked, every open offer
expires and every pending pairing expires, in one transaction (PR7-2). The listener then follows the
PR7-6 sequence.

## Read-compatible builds list (`server/hmp_plugin/read_compat_builds.json`)

```json
{
  "format": 1,
  "bridge_files": ["gateway/run.py", "…"],
  "builds": [
    {"git_sha": "<40 hex>|null", "fingerprint": "<64 hex>",
     "source_sha": "<40 hex>  (provenance only for fingerprint-only entries; never used for matching)",
     "label": "stock base | experimental r0e-hmp | upstream tag",
     "qualified_by": "<test run id>", "qualified_at": "YYYY-MM-DD"}
  ]
}
```

Matching rule (CS-19): an install with git metadata matches only an entry whose `git_sha` equals its SHA and whose fingerprint matches; an install without git metadata matches only a fingerprint-only entry (`git_sha: null`). It starts empty (GU-2c). Entries are added only by the compat task after the full read suite passes.
The write-supported matrix (GU-2a) is a different file and stays empty.

## Direct-send qualification list (`server/hmp_plugin/direct_send_supported_builds.json`, amendment F2)

Same shape as `read_compat_builds.json`, plus the `bridge_files` union extended by
`hermes_cli/active_sessions.py` (DS-4(3)'s lease-registry snapshot) and `hermes_state_titles.py`
(DS-4(2)'s `SessionDB.get_session_by_title`, defined in Hermes's `SessionTitlesMixin` -- a
genuinely separate file from `hermes_state_sessions.py`, where `get_session`/`list_sessions_rich`
live; this corrects `specs/002-send-messages/DESIGN.md` v4's claim that only one file was new --
verified directly against the extracted `stock-base`/`experimental`/`upstream` trees while
implementing `bridge.py.resolve_bot_chat`). It is a **separate list from `write_supported_builds.json`** (OD-F3's full-guarantee
matrix, untouched, still empty) because `"open_guarded"` (GU-4a) is a different, weaker guarantee
than GU-2's full `"open"` state — silently reusing the same list for both would misrepresent which
guarantee a listed build actually earned. It also starts empty; a build enters it only by
independently passing the guarded-write fixture suite (`tools/compat/run_matrix.py`, extended).
`api_server`'s own route/body shape is not fingerprinted here (GAP-2, `HMP_V1.md`) — it is probed at
request time (DS-2(b)) and confirmed behaviorally at qualification time, recorded per-entry as
`"api_server_probe_ok": true|false`, not as part of the `bridge_files` fingerprint.

## Fixture manifest

Defined in `contracts/fixture-format.md`.

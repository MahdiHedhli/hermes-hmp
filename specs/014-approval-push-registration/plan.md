# Implementation plan: approval push registration, issuance, hint resolution and relay delivery


**Current contract review status (2026-10-02):** The clock mechanism, optional pin grammar and N3–N6 were accepted by the prior focused review. The independent D1/D2/D3 sentence review accepted the capacity/retention qualifications, per-`(app, env)` APNs connections and seal-expiry wording. Root resolved its remaining editorial status finding M1 by dating the pre-review statements below. This is contract-text acceptance only. Source, causal tests/vectors, interoperability, provider/device/deployment/release and owner choices O1–O6 remain pending. No task checkbox or security mechanism changed.

Status: design frozen by root on 2026-10-02 after independent review and C1–C3 closure.
Implementation still requires the separately accepted approval inputs (T003) and contract updates.
Account, credential, deployment and device actions retain their own gates. Values written `⟨Dn⟩`
use the frozen mapping in [`ROOT_DECISIONS.md`](ROOT_DECISIONS.md); owner budgets remain pending.

**Root interoperability amendment, 2026-10-02 (authoritative where it conflicts with an earlier line
of this plan).** Decisions B1 to B6 and P1 to P3 in `ROOT_DECISIONS.md` (section "Root
interoperability amendment") fix the relay signature transcript bytes (raw `R`, `K`, `C`), the JCS
seal plaintext, the `enc ‖ ct` seal framing and its 82 to 1,105 byte range, the `kid` and `aud`
grammars, the literal `hmp_approval_v1` FCM channel and collapse key, `DELETE` independence from
delivery availability, the result-code map, and the relay's atomic admission and nonce rules. §3,
§5.1, §6.1, §6.2, §6.5 and §8 below are synchronized to it. Contract text only: it authorizes
nothing, and is not implementation, vector or device evidence. A scoped independent review of an earlier
candidate accepted it with conditions; a later review of the clarified text accepted its other clauses and
required the clock and pin gates, now written (next paragraph) and pending focused review.

**Root review clarifications, 2026-10-02 (authoritative; F1 to F7).** Contract-text clarifications
(`ROOT_DECISIONS.md`, section "Root review clarifications") that preserve B1 to B6, P1 to P3 and every
authority and security requirement: F1 the relay's atomic nonce section reads one current instant (the effective instant of R-F1a below) and
re-checks both skew inequalities; F2 push-off never expires registrations on kid liveness, with the
`why` precedence and the `PUT` check order; F3 the removed relay-contract GAP-1 to GAP-6 labels are not
HMP v1's live `GAP-1` and `GAP-2`; F4 strict DER signature encoding; F5 APNs environment per allowed
`(app, env)` pair; F6 rolling 3,600-second post-seal counters; F7 status wording. §5.1, §6.1, §6.5, §8.1
and §8.2 are synchronized. They authorize nothing and are not vector, interoperability, provider or
device evidence.

**Root clock and pin delta, 2026-10-02 (authoritative; pre-review status recorded below).** A later independent review
accepted the other clauses and required two source gates. Pre-review history: this delta writes them; none is accepted, a
focused independent sentence review is pending, and there is no source, vector, device or provider
evidence. The clock-count repair of 2026-10-02 followed a focused review of that delta: the review accepted the mechanism, the pins and N3 to N6, and required text repairs for the 4,800-nonce and 240 s qualification under clock steps (its finding D1) and for one APNs connection granularity per allowed `(app, env)` pair (D2), with editorial wording (D3). At that checkpoint, the repaired capacity and connection sentences awaited a focused check of those sentences only. That check has now accepted D1/D2/D3 as contract text; implementation and verification remain pending. **R-F1a:** the relay computes one effective acceptance instant `max(raw wall now, last_now)`
inside the atomic nonce section and stores it in memory; skew re-check, purge, seen, capacity, reserve
and the step 14 seal expiry use it, step 6 may use the raw clock, and the rolling windows of steps 2 and
16 (including the per-source 600 per rolling 3,600 s) use monotonic elapsed time. A backward step cannot
reopen a purged nonce within one relay lifetime; a forward step can cause `401`/`422` availability
refusals until the wall clock catches up or the operator restarts, with no automatic restart or reserve
reset; no nonce persistence or restart immunity is claimed (§6.1, §6.5, §8.2). **R-PIN:** host setting
`push.relay_spki_pins`, omitted means no pin, configured means exactly 1 to 8 distinct canonical unpadded
base64url SHA-256 digests (43 characters, 32 bytes) of the leaf DER `SubjectPublicKeyInfo`, additional to
mandatory chain and host-name validation, a mismatch before any request byte under the bounded RES-C retry,
malformed (explicit `None`, empty, non-list, duplicate, bad entry) gives `relay_unconfigured`, no
environment fallback (§6.1, §8.1). **N3:** separation of APNs connections per allowed `(app, env)` pair;
credential and signing-key provisioning is pending owner choice O3. **N4** and **N5** sync the settings
list, the all-off purge reasons and D24 (not D25) counting for inert rows (§8.1). **N6** marks earlier
"six gaps resolved" and skew-replay wording as superseded history; the live `GAP-1`/`GAP-2` stay open.

## 1. Context

- **HMP base `4d6863e`.** Pairing (P1–P4), bearer auth (TR-5, PR5-6), token families and rotation
  (PR5-4/5), revoke paths (PR7-1/2/3/6), the SQLite store (schema 2), `RateLimiter`,
  `log_event`, and the instance key that already signs pairing transcripts. No approval lane and
  no outbound non-loopback socket. Facts confirmed in source for this amendment:
  - `identity.py` `_read_or_create_k_grace` re-creates `k_grace` when the file is missing,
    unreadable or the wrong length, with no identity change.
  - `pairing.py` revokes a device's earlier family on a P4 lost-response re-issue, outside
    `_revoke_in` and `_retry_or_reuse`.
  - `store.py` exposes `revoke_family`, `revoke_families_for_device` and `set_device_state`.
  - The store has no purge job. Only the `IDEMPOTENCY_RETENTION_S` comment in `contract.py`
    mentions an hourly purge; the only bounded deletes are the `p5_nonces` LRU trim and specific
    route deletes.
  - HMP sets no cap on the number of paired devices, and never deletes device rows.
  - `ErrorCode.RETRY_STATE_LOST` (503) and `ErrorCode.OTHER` (503/500) exist.
  - `contract.py` limits error extras to `{why, authz, head_message_id, definitive}` and `why` to
    the closed `OtherWhy` set; error messages are fixed text per code.
  - `LoadedIdentity.k_grace()` reads, and may write, the file on every call (`identity.py`).
  - `devices.state` is written only to `REVOKED` in production (`revoke.py`, the identity-change
    path in `store.py`); auth refuses REVOKED and non-ACTIVE devices; `Store.set_device_state` has
    no production caller and no terminal-state guard.
  - Reproduced by the delta review (in-memory Python `sqlite3`, the `store.py` connection mode):
    SQLite can roll back the whole transaction on some errors (`SQLITE_FULL`, `SQLITE_IOERR`,
    `SQLITE_NOMEM`, `SQLITE_BUSY`); `ROLLBACK TO` then finds no savepoint and the cause is lost. A
    nested savepoint therefore cannot isolate push from a cause, and no push statement runs inside
    a cause's transaction.
- **Approval lane (specs 034/015).** Base `150bd0f` has independent source review and two
  isolated native samples; deployment remains pending. Spec 015 `6a139ba` adds independently
  reviewed insertion, settlement-cause and immutable visibility inputs. T003 is source accepted.
  Section 10 records exact interfaces and I-3/I-4/I-5 lifecycle confirmation. This branch has not
  integrated them, and 014 still supplies dispatcher cancellation and hint/slot cleanup. Native
  evidence for the base does not attest 015. AP-3 uses the shared visibility seam; the frozen
  baseline oracle and final route tests verify source-level equivalence.
- **App spec 030 (private app repository).** The S1 foundation is source-implemented and its
  resolver port is root-accepted: hint parser `{v, route, hint}` with 22..64 character opaque
  strings, the begin/commit route table, `HintResolveRequest{iid, epoch, hintRef}` and the handoff
  machine. The HMP resolver body `{v, hint}` fits that port without reopening S1. Its open gates
  G-HMP and G-ISSUE are what this spec closes on the HMP side. G-PROV, G-OS, G-PERSIST,
  G-NATIVE-INPUT, G-DEV and G-UX stay app or owner work, and this plan names their concrete inputs.
- **Policies.** The minimum-version owner policy (spec 013) holds: push adds no Hermes dependency or
  manifest, and later or unknown builds attempt the actual APIs. The root approval-alert decisions
  (Time Sensitive and a high Android channel; user settings prevail; no Critical, full-screen or
  lock-screen actions; opaque payload; no roster-scan fallback) and the owner's existing
  authorization of the priority alert feature carry over. Provider infrastructure still needs owner
  choices O1–O6 (§9).

## 2. Architecture

```text
 phone (instance A pairing)                 Hermes host (self-hosted, tailnet)          relay (ours)          providers
 -------------------------                  ---------------------------------          ------------          ---------
 APNs/FCM address --seal(HPKE, kid, iid)--> PUT /push/registration ------------------>  (not contacted)
                    <------- R (route) ---- issuer: R = HMAC(k_grace, ..., G, salt), store hash
                                            approval row inserted (034 I-1), visible (I-6)
                                            dispatcher: recheck, recipients, K, C, ttl
                                              -- HTTPS POST, instance-key signature, aud --> verify sig, aud,
                                                                                              nonce, open S,
                                                                                              check bindings,
                                                                                              fixed template --> APNs alert p10 / FCM HIGH
 background: OS shows "Approval needed" <------------------------------------------------------------------ (no app code needed)
 foreground: app code shows the same text (no host fetch)
 tap -> 030 handoff (local R -> iid)
   -> POST /push/hints/resolve {v, hint}    resolver: bearer device's current R, exact K,
      (bearer, pinned tailnet)              owner, bot grant, gate, visible
                                            -> {located, profile} | not_pending | 404
   -> Approvals page: fresh AP-3 read -> human answers via AP-4
```

The flows are in three separate trust domains. Registration and resolution use only the existing
pinned, bearer-authenticated tailnet connection. Dispatch is outbound HTTPS from the host. Background
display is done by the OS from a fixed relay template; foreground display is app code showing the
same text. The phone needs the tailnet only at tap time.

### 2.1 Alternatives considered

| Option | Verdict | Why |
| --- | --- | --- |
| Local polling, sockets, background fetch | Rejected for background | Not delivered while suspended or killed; no OS guarantee. It remains the foreground path. |
| HMP sends to APNs/FCM directly | Rejected | Needs the app's provider credentials on every self-hosted host. The earlier root decision forbids the APNs key in the plugin or client. |
| Relay stores provider tokens; phone registers with the relay | Viable, not recommended | Needs a relay database, phone-to-relay authentication and relay-side revocation. The sealed address gives the same binding without a database. |
| **Sealed address, stateless relay** (recommended) | Proposed | HMP never sees the raw token. The relay has no token database. The binding to `iid` stops another host from using a sealed address. Revocation is HMP retiring the row; a seal the host still holds stays usable by that host until `not_after` (analysis A13). |
| FCM for both platforms | Rejected for iOS | Adds Google processing and an SDK to iOS. FCM's own APNs example uses `apns-priority: 5`, which is wrong for an alert. Direct APNs is smaller. |
| Third-party push service | Rejected | Another processor of tokens and metadata. Same authentication design still needed. |
| UnifiedPush/ntfy on Android | Future option | Not a substitute for FCM on Play devices. Out of scope. |
| Resolver body carrying `route` | Rejected (root B2) | The accepted 030 S1 port never carries the route; the server binds the bearer device's single current registration instead. |

## 3. Affected modules and contracts (future implementation; nothing changes now)

| Area | Planned change | Verification |
| --- | --- | --- |
| `docs/architecture/contracts/HMP_V1.md` | New §7f "Push registration and hint resolution" (PN-REG, PN-ISS, PN-RES, PN-BND), constants (§13), residuals (§14). No new error code. | Contract review |
| Constitution and PR-2 surface note | Record the one sanctioned outbound non-loopback client (`push_relay.py`), whose destination comes only from host config | `check_plugin_surface.py` rule extension and test |
| `store.py` | Schema 3: `push_registrations` and `push_device_generations`. A bounded push purge step (expiry of stale active rows, deletion of REVOKED devices' rows, retained caps, the D28 cap). A guard in `Store.set_device_state` that refuses to change a REVOKED device. No push statement runs inside any cause's transaction. | Migration tests from schema 1 and 2; idempotent migrate; a test that `set_device_state` cannot revive REVOKED; purge tests |
| `revoke.py`, `tokens.py`, `pairing.py` | After the cause's transaction commits (before `REVOKED` is raised in the refresh-reuse path), call one best-effort cleanup in its own `Store.transaction()`. The cause's outcome is unchanged on any cleanup error. | Causal negative tests; a real `SQLITE_FULL` (for example `max_page_count`) injected into the post-commit cleanup leaves each cause's committed outcome and rows unchanged |
| `identity.py` | A new read-only `k_grace` accessor for push only: never creates or rewrites; off-loop reads; an unreadable file means not re-derivable. No change to existing callers | Own source tests: absent, unreadable, wrong-length and transient-error reads never write or delete the file; existing refresh tests unchanged |
| new `push_issuer.py` | Extract the pure PN-ISS-1/2 route/collapse derivation and saved-route-hash check from registration orchestration. No I/O, salt creation, store mutation, route registration or authority decision | Independent derivation vectors; every bound-field mutation; unchanged V1 transcript domains; import without Hermes |
| new `push_registration.py` | Route handlers PN-REG-1..4, calling the pure issuer only after live authority checks; CAS, idempotency, capacity. `DELETE` does not consult push availability (B5) and never calls Hermes, the relay or a provider | Route-level tests with the real `Authenticator`, including `DELETE` with push disabled, relay unset, kid removed and approval members closed |
| new `push_resolve.py` | PN-RES, using approval-lane inputs I-2..I-4 and I-6 | Route-level tests; masking tests |
| new `push_dispatch.py` | Queue, recipients, coalescing, TTL, rate, hint map, breaker, bounds (I-1, I-5, I-6) | Fake clock and fake relay tests |
| new `push_relay.py` | Signed client, bounded response parser, retry policy | Fake HTTPS server tests: redirects, oversize, slow, malformed, connect failure vs post-write timeout |
| `server.py` | Register the four routes. Wire the dispatcher at listener open and close; creation failure leaves push off. | Route set test (beside the existing e10 set test) |
| `adapter.py` / `request_ctx.py` | Live `push.*` config readers; `ServerContext.push_*` fields default closed | Default-closed tests |
| `cli.py` | `hermes hmp push status` (read-only, store counts only) | CLI tests; no identifiers in output |
| `contract.py` | Tags `HMP1-PUSH-ROUTE`, `HMP1-PUSH-COLLAPSE`, `HMP1-PUSH-RELAY`; proposed constants; the four new closed `why` values (`push_disabled`, `relay_unconfigured`, `approvals_unavailable`, `push_capacity`), allowed only on `503 write_gate_closed` | Constant pin tests; prefix-freeness test over all tags; an error-envelope test that only allowed extras and closed `why` values appear |
| Relay (new service, separate repository; visibility is owner choice O5) | Verify, open, template, send, limits | Its own spec, tests and review |
| App (private repository) | 030 S2/S3 wiring, native registration, sealing, encrypted route persistence, permission and channel, foreground presentation, PN-APP-1/2 | App specs and device gates |

No `plugin.yaml` registration, hook, tool or dependency changes. `aiohttp` and `cryptography` are
already allowed. Existing send, jobs, model, AP-3 and AP-4 behavior is not modified (spec PN-NC);
AP-3 code changes only through the separate I-6 amendment (spec §10), as a behavior-preserving
refactor.

## 4. Data model (schema 3, additive)

```sql
CREATE TABLE IF NOT EXISTS push_device_generations (
    device_id TEXT PRIMARY KEY REFERENCES devices(device_id),
    generation INTEGER NOT NULL
        CHECK (generation >= 0 AND generation < 9007199254740992)
        -- never decremented while the device is not REVOKED; deleted only with a REVOKED device (D28)
);
CREATE TABLE IF NOT EXISTS push_registrations (
    route_hash BLOB PRIMARY KEY,            -- SHA-256(R); R itself never stored
    device_id TEXT NOT NULL REFERENCES devices(device_id),
    family_id TEXT NOT NULL REFERENCES token_families(family_id),
    iid TEXT NOT NULL,
    host_generation INTEGER NOT NULL,       -- meta.store_revocation_epoch at issue
    generation INTEGER NOT NULL,            -- G at issue
    salt BLOB NOT NULL,                     -- 32 B CSPRNG; not secret without k_grace
    platform TEXT NOT NULL CHECK (platform IN ('apns','fcm')),
    addr_kind TEXT NOT NULL CHECK (addr_kind IN ('apns_token','fcm_token','fcm_fid')),
    env TEXT CHECK (env IN ('production','sandbox')),
    relay_kid TEXT NOT NULL,
    sealed BLOB,                            -- relay ciphertext; secret; bounded; NULL once non-active
    request_hash BLOB,                      -- SHA-256(request_id raw); NULL once non-active
    body_hash BLOB,                         -- SHA-256(canonical PUT body); NULL once non-active
    state TEXT NOT NULL CHECK (state IN ('active','provider_gone','expired','retired')),
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,            -- := seal_expires_at
    state_changed_at INTEGER NOT NULL,
    CHECK (state <> 'active' OR (sealed IS NOT NULL AND request_hash IS NOT NULL
                                 AND body_hash IS NOT NULL)),
    CHECK ((platform = 'apns' AND addr_kind = 'apns_token' AND env IS NOT NULL)
        OR (platform = 'fcm' AND addr_kind IN ('fcm_token','fcm_fid') AND env IS NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS push_one_active_per_device
    ON push_registrations(device_id) WHERE state = 'active';
CREATE INDEX IF NOT EXISTS push_retained_age
    ON push_registrations(state, state_changed_at);
```

All writes go through `Store.transaction()` (`BEGIN IMMEDIATE`). There is no existing store purge
to join (§1). The push purge step (spec PN-BND) runs at listener open and hourly on the listener's
loop, as short transactions per pass. It expires stale active rows, deletes retained rows over
retention or caps, and deletes the generation and registration rows of REVOKED devices (re-reading
`devices.state` inside the transaction, and only once the `set_device_state` guard exists). A
generation row of a non-REVOKED device is never deleted. An active row implies its device's
generation row; the transaction that inserts a device's first active row creates it.

## 5. Flows

### 5.1 Registration (PUT), including lost acknowledgement and rotation

1. The app runs 030 `beginRegistration(iid)`, which captures the pairing generation and creates the
   intent. It draws `request_id` once for the intent, seals the provider address for the pinned
   `iid` and a kid from `GET` (`relay_kids`), and persists the exact body (PN-APP-2).
2. `PUT` with `expected_generation = G` from the last `GET` or `PUT`.
3. Server before the store transaction: authenticate → owner → bucket → shape (kid matches the grammar,
   `addr_kind`/`env` consistent, seal lifetime in range, `sealed` canonical b64u of 82 to 1,105 decoded
   bytes; all independent of availability) → available (`503` with the PN-AV precedence `why`) → the
   kid is in the live list (`400`; F2) → read `k_grace` off-loop. (`DELETE` skips the availability and
   `k_grace` steps: authenticate → owner → bucket → shape → the write transaction with its `ACTIVE`
   device and live-family re-check, then CAS.) In one
   `BEGIN IMMEDIATE` transaction, re-check device ACTIVE and bearer family live (`401 revoked` on
   failure), then replay check on the active row with the
   same `request_hash`: body mismatch `409 idempotency_conflict`; family mismatch or expired
   `409 stale`; re-derive `R` using the already-read key and compare its hash (a mismatch
   or an unreadable file is `503 retry_state_lost`, nothing changed); else `200` with the same `R`.
   With no matching active row: CAS on `G` (`409 stale`, no extra), capacity (`503 write_gate_closed
   push_capacity`: active-row cap D24 and generation-row cap D28), retire the old row, advance `G`
   by one, create the generation row if absent, draw the salt, insert, enforce retained caps,
   return. A `route_hash` UNIQUE violation, or `G` reaching 2^53, rolls everything back
   (`503 other`, `G` unchanged). A replay made after push became unavailable answers `503`, and one made
   after the kid was removed while push is available answers `400`, before the replay check; the app does
   `GET`, then a new intent.
4. The app commits the intent with `R`. If the acknowledgement is lost, the same bytes return the
   same `R` (030 FR-6). A provider token change, kid change, `expired`/`provider_gone` state or
   nearing expiry (`⟨D9 refresh⟩`) starts a new intent; 030 `begin` closes the old handle locally at
   once.

### 5.2 Dispatch

1. Approval row inserted → I-1 → thread-safe, bounded enqueue on the listener loop (never blocks).
2. Worker at dequeue: drop if TTL already passed; PN-DSP-3 recheck including I-6 visibility and the
   breaker. Select recipients (PN-DSP-4) with one store read; check the bot grant once per row
   (`user_id` scoped).
3. Per recipient: coalescing slot, hourly cap, re-derive `R` and check its hash, mint `K` and bind
   it, compute `C` and `ttl_s`, re-check visibility, sign with fresh `ts`/`nonce`, POST.
4. Handle the response (PN-DSP-8/9). Retry only a pre-write connection failure or relay
   `unavailable`. Log a fixed outcome.

### 5.3 Tap and resolve

The OS (background) or app code (foreground) shows the generic alert. A tap launches the app. The
native adapter converts the payload to the 030 map. 030 checks the route locally, asks for a switch
if needed, and the resolver adapter calls `POST /push/hints/resolve` with `{v: 1, hint}` through the
shared foreground wrapper bound to `(iid, epoch)`. A `located` result pushes the Approvals page. The
page does its own fresh AP-3 read. Answers go through AP-4 after a human choice.

### 5.4 Revocation and rotation

See spec PN-REV. Eligibility is validation-based, so any committed revocation closes it at once,
even if cleanup never runs. After the cause's transaction commits, one separate best-effort
transaction retires rows; push never executes inside the cause's transaction, and a cleanup failure
(including a real `SQLITE_FULL`) is logged and swallowed, leaving the cause's outcome and rows as
they were. The purge is the backstop. Async edges (queued dispatch, retries, relay feedback,
resolve) recheck exact generations, so ordering races fail closed.

## 6. Relay design (our infrastructure)

### 6.1 Function

A single stateless HTTPS service, run as **one replica** (`⟨D27⟩`), with four parts:

1. Request verifier: size and shape, the atomic pre-verification admission (per-source limit and
   global verify budget, charged together at once), the `iid` derived from the supplied SPKI, the
   signature over the transcript with raw `R`, `K`, `C` (strict DER, F4), audience, the early skew screen,
   the atomic nonce section that computes one effective acceptance instant `max(raw wall now, last_now)`
   (R-F1a, memory only), re-checks skew at it and then purges and reserves in a bounded replay cache (F1),
   kid, optional `iid` allowlist. Rolling windows are measured on a monotonic clock.
2. HPKE opener and binding checker: RFC 9180 §7.1.4 validation, open `enc ‖ ct`, restricted JCS
   plaintext check, then `iid`, the `(app, env)` allowlist pair (F5), `not_after`, platform, `addr_kind`.
3. Provider senders: an APNs HTTP/2 client with token authentication, using an ES256 JWT
   refreshed no more than every 20 minutes and no less than every 60. FCM HTTP v1 with OAuth 2.0
   short-lived access tokens derived from a service account or the platform's default credentials,
   targeting `token` or `fid` by `addr_kind`. The relay makes one provider attempt per request and
   never retries a provider call.
4. Limiter: per source, per `iid`, per destination HMAC, per `(destination, iid)`, global.

It has no database of tokens, users or instances. Its configuration is: its audience, the app
allowlist (`(bundle ID, environment)` pairs for APNs and packages for FCM, F5), kid keys, APNs team and key IDs, the FCM project,
the optional `iid` allowlist and limits.

### 6.2 Provider facts this design relies on (primary sources, fetched 2026-10-02; see analysis §6)

- APNs is best effort. It may reorder, stores one notification per bundle ID, and may coalesce.
  With `apns-expiration` it tries to deliver at least once until that date. Whether it can deliver
  after the date is not stated in the saved page (`EVIDENCE_GAP`); the design tolerates late taps.
  Priority 10 means immediate; alert pushes need `apns-push-type: alert`; payloads are limited to
  4 KB; `apns-collapse-id` is at most 64 bytes.
- An APNs `410 Unregistered` or `ExpiredToken` means stop sending to that token. Do not retry
  `BadDeviceToken`, `DeviceTokenNotForTopic`, `Forbidden`, `ExpiredToken`, `Unregistered` or
  `PayloadTooLarge`. 5xx may be retried after 15 minutes, which exceeds the alert TTL, so the relay
  answers `provider_unavailable` and nobody retries. The relay also answers `provider_unavailable`
  for every one of those refusals (decision B6); only `Unregistered`/`ExpiredToken` and FCM
  `UNREGISTERED` are `provider_gone`, and HMP retires no registration on a refusal. `TooManyRequests` may be retried with a delay;
  the relay does not retry it and answers `provider_unavailable`, never `429` (which means the
  provider was not attempted).
- Time Sensitive notifications break through Notification Summary and Focus, and the user can turn
  that off. `interruption-level: time-sensitive` is the payload key. The
  `UNAuthorizationOptions.timeSensitive` option's availability metadata reads iOS 15.0 to 15.0
  (introduced and deprecated in 15.0); the design does not use it.
- FCM HIGH priority attempts immediate delivery and may wake a dozing device. Messages that do not
  produce user-visible notifications risk deprioritization (7-day per-instance window), and when the
  user disabled notifications none are posted, so high-priority messages are deprioritized; the
  app must not keep a registration then (spec PN-APP-1). There are only seconds of processing in
  `onMessageReceived`, and no network calls should happen before display. Notification messages
  are displayed automatically only in the background; in the foreground the app's code decides.
  Payloads are limited to 4096 bytes; TTL is at most 4 weeks; at most 4 distinct `collapse_key`
  values at a time. `UNREGISTERED` (404) means remove the registration. `UNAVAILABLE` and
  `INTERNAL` may be retried with backoff and `Retry-After`; `QUOTA_EXCEEDED` needs at least a
  one-minute delay. The relay does not retry; it answers `provider_unavailable` for these, including
  `QUOTA_EXCEEDED`, and never `rate_limited` (PN-REL-4).
  The v1 `message.token` field is marked deprecated in favor of `fid`, which also accepts a Firebase
  Installation ID during the transition; both patterns are co-supported.
- Android 13+ needs `POST_NOTIFICATIONS`. Channel importance cannot be changed by the app after
  creation; the user controls it.

### 6.3 Deployment choices (owner decision; nothing provisioned)

| Choice | Fit | Tradeoffs |
| --- | --- | --- |
| **R2. Owner-operated relay on the owner's tailnet** (recommended first stage) | Same code and contract. Runs with an `iid` allowlist (`⟨D23⟩`). Hosts without internet egress can still reach it over the tailnet; the relay node needs internet egress. | Only the owner's hosts can use it; provider keys live on an owner machine (a separate OS user and process, never inside Hermes or HMP). |
| **R1. Project-operated public relay** at a project subdomain | Serves every tester's self-hosted host with outbound HTTPS only | Open enrollment is **not activated** until the owner accepts the concrete abuse residuals (analysis A1, A6, A13, the restated A14 sybil suppression, and A17 global and verify exhaustion). Ongoing operation, secret store, availability. Small compute; needs outbound HTTP/2 to APNs (the hosting platform must support it, `EVIDENCE_GAP` per platform). |
| R3. Third-party push service | Not recommended | Extra processor and privacy disclosures; no simplification of authentication. |

Staging R2 then R1 uses one relay codebase and one contract. Only `push.relay_url`,
`push.relay_audience`, `push.relay_spki_pins`, kids and the allowlist mode differ.

### 6.4 Custody and lifecycle

- **HPKE relay keys.** Per-kid private keys live in the relay secret store; public keys ship in the
  app. Generating them is an owner action whose custody is effectively irreversible once a
  distributed build ships the public key. Rotation: add a kid to new app builds and the host
  `relay_kids`; keep old private keys for `⟨D9 max⟩` plus margin; then retire. A compromised kid is
  removed from host lists, so new registrations refuse it and dispatch skips rows sealed to it.
- **APNs signing key.** An environment-specific team key, or a topic-specific key, created by the
  owner (O3). Kept in the relay secret store. If compromise is suspected, revoke and replace it, and
  reopen connections.
- **FCM credentials.** Least-privilege service account credentials, or workload identity, in the
  relay secret store. The exact IAM role is an `EVIDENCE_GAP` until owner setup.
- **Host key.** Proposed reuse of the instance key with a distinct transcript tag (`⟨D2⟩`, §7.3).
  Identity rotation then invalidates every sealed address automatically.

### 6.5 Relay bounds (single replica; every table has a cardinality and an overflow rule)

`B` is the owner-set global hourly budget (`⟨D17 global⟩`). Proposals: R2 `B = 600/h`, R1
`B = 6,000/h`.

| Object | Cardinality bound | Overflow rule |
| --- | --- | --- |
| Request body / response | 4 KiB / fixed small JSON | `400 bad_request` before any other work |
| Pre-verification signature checks | `⟨D17 verify⟩`: at most 20 in any rolling 1-second interval on a monotonic clock, global, no extra burst (a sliding log of at most 20 timestamps), checked atomically with the per-source limit and charged immediately only if both admit, even if a later check fails | `429 rate_limited`, provider not attempted, nothing charged. Exhausting it with unauthenticated traffic denies every R1 alert (A17) |
| Per-source table (pre-verification) | 4,096 entries, LRU; the limit is 600 per rolling 3,600 s on a monotonic clock | Eviction can only loosen one source's limit; the global verify budget still bounds CPU |
| Replay nonce cache | `⟨D18 cache⟩` = 16,384 entries, each kept over `[receipt, ts + CLOCK_SKEW_S)` (at most 240 s under normal clock progress) and purged when `expiry ≤ now`. Under normal clock progress at the verify budget (20 per rolling second) at most 4,800 are live; clock stalls or backward steps (`last_now` ahead of the raw clock) can prolong retention and exceed 4,800, and repeated steps can reach 16,384 (relay CLK-1) | Atomic check-and-reserve before decrypt or provider work; refuse `503 unavailable` when full (provider not attempted); never evict an unexpired nonce; never release a reservation early; a full cache under repeated steps refuses `503` with no eviction and no new replay acceptance; one effective instant `max(raw wall now, last_now)` inside the atomic section re-checks skew, drives purge, check and reserve (F1) and is reused by the step 14 seal expiry; a backward wall-clock step cannot reopen a purged nonce in one relay lifetime, and while `last_now` is ahead of the raw clock (a forward step or a backward correction) the relay can refuse requests until the clock catches up or the operator restarts (R-F1a, no automatic reset, no other progression or TTL). A full cache is a defensive path, not an expected one. Memory only: a restart empties it (HMP v1 §14 RES-26) |
| Per-`iid`, per-destination, per-`(destination, iid)` tables | `B` entries each, rolling 3,600-second windows (F6); an entry is created only when the request is admitted by every per-key cap and the global budget | Cannot overflow while global admission holds. If full anyway, refuse `429 rate_limited` (fail closed, no eviction of a live counter) |
| Admission (post-seal) | the four counters (per `iid`, per destination, per `(destination, iid)`, global `B`), each over a rolling 3,600-second window on a monotonic clock (F6; no new cap value), are checked together, atomically | A request is counted against any of them only if all admit it, so only admitted requests charge `B`. Separate from the pre-verification admission above. Sybil `iid`s and random addresses can still exhaust `B` in public mode (A17) |
| `iid` allowlist (R2 mode) | ≤ `⟨D23 allowlist⟩` = 8 entries, from relay config | Not in list: `401 unauthorized` |
| Negative cache of gone destinations (optional) | 4,096 HMACs, LRU, 30-day entry lifetime | Eviction only costs one more provider attempt |
| Provider connections | APNs: one HTTP/2 connection per allowed `(app, env)` pair (F5, N3; credential provisioning is pending O3); FCM: ≤ 8 concurrent requests | Queue inside the request's own timeout; on timeout answer `502 provider_unavailable` if the provider call began, else `503 unavailable` |

## 7. Security and compatibility review

### 7.1 Trust boundaries and threats

| Boundary | Threat | Control |
| --- | --- | --- |
| Push payload (relay, Apple, Google, device) | Payload as authority, data leak | Generic text only; `R`/`K` are opaque non-authority values; the resolver needs bearer and pin; fresh AP-3 read; human choice |
| Phone → HMP registration | Late or duplicated PUT, lost acknowledgement, forged handle, lost `k_grace` | CAS on `G`; idempotent replay by request hash with hash-checked re-derivation (`retry_state_lost` on mismatch); server-issued `R` with a per-row salt; exact-field validation; capacity cap |
| HMP → relay | Spoofed host, replay, cross-relay replay, URL redirection | Instance-key signature; audience; ts and nonce kept until `ts + skew`; host-config URL; no redirects; `trust_env=False`; bounded parse |
| Host-learned sealed blob reused elsewhere | Another host pushes to the phone | Seal binds `iid`; relay checks signature key against the bound `iid` |
| Leaked raw provider token | A stranger seals it under their own `iid` and spams generic alerts, or exhausts a shared destination budget to suppress real alerts (one `iid` cannot; `⌈ceiling / pair cap⌉` sybil `iid`s can) | Per-`(destination, iid)` cap below the destination ceiling; generic, non-authoritative payload; an unknown route gives an "unlinked" notice; R2 allowlist; R1 not activated until the owner accepts the restated residual (A14) |
| Public relay exhaustion | Unauthenticated floods, or sybil `iid`s sealing random addresses, exhaust the global verify or hourly budget; all R1 alerts are denied | Per-key caps before the global count; only admitted requests charge it; bounded tables; R2 allowlist; R1 not activated until the owner accepts the residual (A17) |
| Relay compromise | Token disclosure; arbitrary alert text | Relay holds provider keys; generic alerts still carry no authority; the app parser rejects extra keys; incident procedure rotates the APNs key, FCM key and kids |
| Revoked, re-paired, rotated device | Alerts or resolves continue | Validation-based eligibility (row family, device state, `H`, `G`); post-commit best-effort cleanup, never inside the cause's transaction; feedback CAS; `G` monotonic |
| Unpaired phone, host unreachable | The host still holds a usable seal | Bounded by seal `not_after` (`⟨D9 max⟩`); app shows "unlinked" on tap; Android full alert opt-out can rotate the FCM registration, iOS has no equivalent guarantee (A13) |
| Desktop-held prompt | Alert or `located` for a prompt the Approvals page hides | I-6 visibility at dequeue, before each send and at resolve; hidden is `404` |
| Non-owner, lost bot grant | Alerts reveal activity | Live owner and grant checks at dispatch and resolve; `404` masking |
| Resource exhaustion | Bursts, slow relay, many devices, many hints | PN-BND caps with defined overflow; breaker; bounded close |
| Gateway liveness | Producer or close stalls Hermes | Non-awaiting thread-safe enqueue; no lock across `await`; bounded close; breaker drops at once |
| Logs, audit, CLI | Secret leakage, stable pseudonyms | Fixed codes; never pass `R`/`K`/`C`/`S`/salt/`request_id` to `log_event`; relay logs no `iid` prefix |
| Local clock | TTL as authority | TTL is a provider hint; resolver authority comes from row state only |

`SECURITY_REVIEW_REQUIRED`: the sealed-address binding, instance-key reuse (§7.3), the relay open
enrollment model (R1 activation), the computational nonreuse argument (PN-ISS-2), the authoritative
settle-cause set (I-2) and the visibility seam (I-6).

### 7.2 Compatibility

- No floor, manifest, fingerprint or latch. Availability inherits the approval members (spec 034
  R1) plus host settings. Later and unknown Hermes builds attempt the actual APIs. Older phones
  ignore the new routes. Older HMP returns `404` on `GET /push/registration`, which the app reads
  as "push absent"; a resolver `404` always maps to `other` (unable to check), never to a separate
  unsupported state.
- Wire contract minor revision (v1.x) with additive routes; no change to existing routes.

### 7.3 Key separation (conditions for D2(a))

- TR-13 transcripts are `tag || Σ(u32 len || field)`. The tags `HMP1-PUSH-ROUTE`,
  `HMP1-PUSH-COLLAPSE` and `HMP1-PUSH-RELAY` must not be prefixes of any existing tag, or the
  reverse; a prefix-freeness test runs over the full tag set.
- `ROUTE` and `COLLAPSE` are HMAC-only tags kept out of `TRANSCRIPT_TAGS`, like `TAG_GRACE`. `RELAY`
  is signature-only and no phone verifier ever accepts it. `crypto.py` builds transcripts only for
  tags in `_TRANSCRIPT_TAGS_ALLOWED` (`TRANSCRIPT_TAGS` plus `TAG_GRACE`), so the three tags join
  that allowed set without joining `TRANSCRIPT_TAGS` or `HASH_DOMAIN_TAGS`.
- HMP serves TLS 1.3 only, so there is no TLS 1.2 signing oracle; TLS 1.3 CertificateVerify content
  starts with 64 bytes of 0x20 and cannot equal `HMP1-`. If TLS 1.2 is ever enabled, D2 is
  revisited.
- Optionally derive a push subkey from `k_grace` for `ROUTE` and `COLLAPSE`.

## 8. Verification strategy and operational test matrix

### 8.1 HMP (unit and route, no network)

Route-level negatives with the real `Authenticator`, store and a spy relay: non-owner `404`;
host-denied owner `404`; wrong instance `401`; revoked `401 revoked`; replay, conflict and stale
CAS; replay with a different bearer family (`409 stale`); replay after `k_grace` is deleted between
`PUT` and retry (`503 retry_state_lost`, row and `G` unchanged); replay after the retired row was
evicted (`409 stale`, never `200`); forced `route_hash` collision (`503 other`, `G` unchanged, old
row active); capacity full (`503 push_capacity`; replacement and `DELETE` of an existing registration still
succeed); generation-row cap (first `PUT` and no-generation `DELETE` refused, nothing written); kid not
configured at `PUT`; kid removed before dispatch while push is available (skipped, `GET` reads `expired`); `addr_kind`/`env`
mismatch; seal lifetime out of range; bounds; post-commit cleanup for each cause in PN-REV including the P4
re-issue; a real `SQLITE_FULL` injected into each post-commit cleanup leaves the committed revoke,
refresh, P4 and identity-change outcomes and their store rows unchanged (no savepoint is promised);
feedback CAS against a newer registration; resolve for unknown, foreign, rotated, re-paired, revoked, expired, closed-generation, rebound, purged or evicted rows; Desktop held
between enqueue and send (no request) and at resolve (`404`, never `not_pending`); bot grant lost
(`404`); gate closed (`503`); `not_pending` only for authoritative causes; log canaries for `R`,
`K`, `C`, `S`, salt and `request_id` never appearing; default-closed config; existing route suites
unchanged with push off; relay client against redirect, oversize, slow, malformed, unknown-code,
TLS-failure, pre-write connect failure (retried) and post-write timeout (not retried) fakes; R-PIN config reader and client (tests pending): `push.relay_spki_pins` omitted allowed (no pin), versus explicit `None`, an empty list, a non-list, a duplicate, a padded, wrong-length, non-canonical or non-base64url entry, a non-string entry and more than 8 entries, each `relay_unconfigured` (never ignored, never a trust fallback); exactly 1 and exactly 8 valid distinct entries accepted; no environment-variable fallback; a leaf pin match still requires a valid chain and host name; a self-signed certificate with a matching pin, a chain-certificate-only match and a leaf mismatch all fail before any request byte, the failure retried only under the bounded RES-C pre-write rule; breaker
opens and drops without waiting; listener close completes within its bound while the relay hangs.
Purge and invariants: stale active rows (past expiry, kid removed while push is available, hash mismatch) are expired, `G`
advances once and capacity frees; the read-only accessor writes no secret-file bytes, expires no row merely for an unreadable `k_grace`, and still lets
past-expiry, removed-kid, REVOKED and retained-row purge steps run; a negative test combines an
unreadable `k_grace` with an expired row and a removed-kid row (both expired, `G` advanced once,
capacity freed) and a valid unexpired live-kid row (stays active); F2: for each off reason
(`push_disabled`, `relay_unconfigured` including one malformed kid among valid ones, an empty kid list or malformed
configured `push.relay_spki_pins` (N4), and
`approvals_unavailable`) a removed-kid row stays active and inert after a purge and `GET`, still counting against the D24 active cap and not the D25 retained cap (N5), absolute
expiry, revocation, family, hash and retained-row purge still run, and kid-removal expiry resumes when
push is available again; `GET` omits `relay_kids` unless available; the `why` precedence (`push_disabled`,
then `relay_unconfigured`, then `approvals_unavailable`); `PUT` order: a lexically malformed kid `400` even
while off, a removed well-formed kid `503` while off and `400` while available, grammar and size failures
independent of availability; REVOKED
devices' rows are deleted only with the `set_device_state` guard in place, and a test shows that
function cannot revive REVOKED; `G` never decreases for a non-REVOKED device; an active row always
has a generation row; exactly one `G` increment per transaction; `G` at the 2^53 bound refuses
`503 other`; the error envelope uses only allowed extras and the closed `why` values; `GET` reports a
fenced row as not active and applies the latest-row rules; a replay after kid removal while push is available gets `400` (and `503` while it is off) and
the app path is `GET`; the consistent-restore replay outcome is documented (A19); counters keyed by
device survive re-registration; coalescing-slot eviction never exceeds the hourly cap; every
`k_grace` read is off the event loop; `DELETE` succeeds (`200`, same CAS and `G` rules) with push disabled,
relay unset, kid removed, approval members closed and direct send off, and still answers `404` for a non-owner,
`401 revoked` after a revoke between authentication and the write, `429` over the bucket and `409 stale` on a
CAS miss; `GET` stays readable (`available: false`) in the same states; `PUT` of `sealed` at 81, 82, 1,105
and 1,106 decoded bytes and with padded or non-canonical b64u; kid grammar bounds (64 and 128 characters, a
leading `.` or `-`, non-ASCII, whitespace, case difference). Mutation checks: removing each fence kills a
named test.

### 8.2 Relay

Signature, audience, skew and replay negatives (nonce kept until `ts + skew`; full cache refuses); F1 concurrent
and boundary tests (a request passing the early screen before `ts + 120` and reaching the atomic section after it
is `401` with no reservation and no provider call; no reliance on an instant captured before another worker's
purge); F4 strict DER and range cases (non-minimal, zero, negative, `n`, above `n`, trailing bytes `400`; valid
in-range non-verifying `401`; low-S and high-S valid; vectors from an independent generator, pending); F5
environment pairs (sandbox-only, production-only and both; pair not allowed or env mismatch `422`; no
fallback; separate connection per allowed `(app, env)` pair; `iid` allowlist miss `401`); F6 rolling-window boundary tests
(no double burst across a fixed hour, all-admit-or-none charge, no new cap value); R-F1a causal clock tests
and vectors (**pending; none exists**): a backward wall-clock step after a purge leaves the replayed request
`401` with no reservation and no provider call; a forward step across `ts + 120` refuses `401` at step 7
until the clock catches up, with no automatic restart or reserve reset; the step 14 expiry check reuses the
step 7 instant and never a later raw reading; the verify budget, the per-source limit and the four counters
neither double-count nor un-count across backward and forward steps because they use monotonic elapsed time;
a cold restart resets `last_now` and the cache together (documented residual, no persistence claim); causal retained-capacity tests under repeated backward steps (live count may exceed 4,800, no exact bound promised) and a full-cache test under repeated steps (`503`, nothing evicted, no replay accepted) (**pending**);
seal binding mismatch (iid, app, env, expiry, platform, `addr_kind`); unknown kid; allowlist mode;
payload template fixed (host text ignored); `token` vs `fid` targeting; provider response mapping
(`provider_unavailable` after any provider attempt, never `unavailable`); per-`(destination, iid)`
cap stops one `iid` from suppressing another host (not sybil `iid`s, see the two-`iid` test below); the signature
transcript with raw `R`, `K`, `C` and the derived `iid` (vectors from an independent generator, reviewed: implementation
follow-up); the result-code map (`400`, `401`, `422` and every provider refusal as `502`); two concurrent identical
requests never both reach a provider; the nonce interval boundary and `expiry ≤ now` purge; a rolling-second
verify budget with no burst; the JCS plaintext negatives and the `enc ‖ ct` length and `422` negatives; log canaries (no `iid` prefix, no provider body); limiter tables fail closed
when full; no persistence of addresses; per-key caps run before the global count and only admitted
requests charge it; a verify-budget exhaustion test returns `429` with no provider call; a
two-`iid` destination-ceiling test documents the A14 residual; under normal clock progress (clock-step tests excluded) the replay cache never exceeds 4,800
live nonces at the verify budget; FCM requests carry no `env`; provider throttling maps to
`502 provider_unavailable`.

### 8.3 Integration (isolated, no live home)

An isolated Hermes fixture with the approval lane and a local fake relay: approval → dispatch →
signed request; revoke between enqueue and send; Desktop held between enqueue and send; restart
drops queue and hints. Sample evidence, not a gate on future builds.

### 8.4 Physical delivery (owner-authorized signed builds, provider sandbox then production)

| Case | iPhone | Android |
| --- | --- | --- |
| Foreground (app code presents the generic text) | required | required |
| Background, suspended, locked (OS display) | required | required |
| After reboot, after first unlock | required | required |
| Before first unlock (also direct boot on Android) | measured, reported as observed | measured, reported as observed |
| Force-quit from the app switcher (iOS) / recents swipe (Android) | measured, reported as observed | measured, reported as observed |
| Force stop (Android Settings) | n/a | measured, reported as observed |
| Doze (`adb shell dumpsys deviceidle force-idle`), app standby buckets, battery restricted | n/a | required |
| Focus on with and without the app allowed; Time Sensitive off | required | n/a |
| Permission denied; channel importance lowered or blocked by the user (registration removed, PN-APP-1) | required | required |
| Phone off tailnet at alert, on tailnet at tap; Tailscale off at tap (unable to check) | required | required |
| Tap with another instance active; cold-start tap (route persistence) | required | required |
| Re-pair, revoke, P4 re-issue, `rotate-key`, reinstall/restore, provider token change: old handles never resolve, new handles differ | required | required |
| Burst coalescing, TTL expiry before delivery, duplicate delivery, relay down, host offline | required | required |
| Paired Apple Watch mirroring of the iPhone alert | measured, reported as observed | n/a |
| Play services proxied notification behavior (`⟨D16⟩`) | n/a | required |

Simulators and emulators are not evidence for these rows. Results are recorded privately, never in
this public repository.

## 9. Owner actions (choices; nothing provisioned yet; all pending)

These are owner or account actions: outward-facing, billed or hard to reverse. Root design choices
do not authorize any of them.

1. O1 Relay operator and stage: R2 then R1 (recommended), or R1 directly. R1 open enrollment
   additionally needs the owner's acceptance of the recorded abuse residuals (A1, A6, A13, the
   restated A14 and A17).
2. O2 Hosting platform, region and replica model for R1, a subdomain under the existing project
   domain, and later billing. The website stays unchanged until a separate decision.
3. O3 Apple: a push key (environment-specific team key or topic-specific key; key quota is scarce);
   Push Notifications and Time Sensitive Notifications capabilities on the App ID. Signed
   entitlements are checked only on later owner-requested, authorized builds.
4. O4 Google: a Firebase project for the Android package(s), with least-privilege send
   credentials. A project ID is permanent once created.
5. O5 Relay source visibility (public or private repository).
6. O6 Privacy answers (App Store privacy, Play Data safety, privacy policy text) before any
   external build that enables push, covering provider processing, the relay learning `iid`, and
   the `C` pseudonym. Beta tracks stay unchanged now.

Also owner actions, not O-items: generating HPKE kid keypairs; relay domain or DNS; the relay secret
custody and incident runbook.

## 10. Staged implementation (the end state is unchanged)

| Stage | Delivers | Exit evidence |
| --- | --- | --- |
| S-0 Approval-lane amendments | I-1, I-2, I-6 (and confirmation of I-3..I-5) on accepted 034 source `150bd0f`, with their own spec delta, independent review and root verification; I-6 includes AP-3 calling the same seam, with an equivalence test | Accepted lane commit carrying the inputs |
| S-A Contract freeze | Delta review of this amendment, root decisions, contract text | Independent delta review accepted; root freeze recorded |
| S-B HMP server | Store, routes, issuer, resolver, dispatcher (fake relay), post-commit cleanup, purge, CLI | Unit, route and mutation tests; scans |
| S-C Relay | Service and tests; sandbox credentials after owner action | Relay tests; sandbox sends to test devices |
| S-D App | 030 S2 wiring, native registration, sealing, encrypted routes, native input, foreground presentation, permission and channel UX, PN-APP-1/2 | App unit tests; device install |
| S-E Owner dogfood (R2, sandbox, then production) | End-to-end on owner devices | §8.4 matrix on physical devices |
| S-F Beta relay (R1) | Production relay; privacy declarations; owner acceptance of R1 residuals | Release-candidate security review; §8.4 on the release candidate |

A stage that passes its own exit does not complete the feature. Only S-F's evidence does. S-B does
not start before S-0 and S-A.

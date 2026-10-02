# Feature: Approval push registration, issuance, hint resolution and relay delivery

Status: **design frozen by root, 2026-10-02**, after independent design, amendment and focused
C1–C3 closure reviews. Not implemented or provider-verified. The accepted decisions and bounds
are in [`ROOT_DECISIONS.md`](ROOT_DECISIONS.md); `⟨Dn⟩` refers to that frozen mapping.
Owner/account choices, deployment budgets and public relay activation remain pending. This change set is
documentation only: no runtime, test, dependency, account, credential, provider or host change.
The C1–C8 text records design decisions; the tests it names are future work (tasks T020–T024, T030,
T040) and nothing here is source evidence.

Base: HMP `4d6863e` (minimum-version policy, spec 013; no approval lane). The approval lane this
feature consumes is spec 034. Root states that its source `150bd0f` (PR #73) is independently
accepted as source, with native fixtures and deployment still pending; this documentation pass did
not re-verify that. Root also states that the three inputs I-1, I-2 and I-6 (section 10) are absent
from it, and the delta review found the relevant files byte-identical to the earlier-reviewed
candidate, where `PromptStore.put` signals nothing. So I-1, I-2 and I-6 need separately reviewed
approval-lane amendments before any 014 implementation. Without those inputs the feature stays
unavailable. This spec depends on neither 034's native evidence nor its deployment.

## Summary

An owner whose phone is an approval owner for a Hermes instance gets a prompt, generic, system-level
"Approval needed" alert on that phone when the instance's HMP lane observes a new Hermes approval
that the Approvals page would show. With the app in the background, suspended or not running, the
OS displays the alert from the push payload without app code or any host contact. With the app in
the foreground, the app's own code presents the same generic text, also without host contact. The
phone does not need the tailnet to receive the alert. Outcomes after a user force-quits the app
(iOS app switcher) or force-stops it (Android settings) are unknown and are measured, not promised.

Tapping the alert opens the app. The app checks locally that the alert belongs to a paired, current
instance, asks HMP over the pinned, authenticated tailnet connection where the approval is, opens
that bot's live Approvals page, and fetches the prompt fresh. Only then can the human choose an
answer. The alert never carries the command, bot, profile, session, URL, path, credential or answer,
and it never authorizes anything.

Delivery to a suspended phone needs a provider push: APNs on iOS, FCM on Android. HMP runs on
self-hosted Hermes hosts that cannot hold the app's provider credentials. The design therefore adds
a small push relay that we operate. HMP reaches it with outbound HTTPS only. The phone hands HMP a
**sealed provider address** that only the relay can open, bound to that one instance. HMP never sees
the raw device token.

Local polling, sockets or in-app timers cannot promise background delivery and are not a substitute.
They remain the foreground path through the existing approval list (AP-3).

**Coverage.** 014 dispatches only for approval rows that the 034 lane inserts: Bot Chat streams that
HMP started, and HMP Phone chat. Approvals raised on other surfaces (Desktop, CLI, cron, other
platforms) are not covered. Whether Hermes offers a suitable cross-channel observer is open research
(`EVIDENCE_GAP`, section "Gaps by owner"), not an established Hermes API gap.

## End state (the full goal; staged delivery does not shrink it)

The feature is complete only when all of these are shown on **physical devices**:

1. A Hermes approval on an owner host that AP-3 would show produces a visible Time Sensitive alert
   on the owner's iPhone, and a high-importance channel alert on an Android phone, in these
   **required** states: backgrounded, suspended, locked, after a reboot once the device has been
   unlocked, and on Android in Doze (OS display from the payload); and foregrounded (app code
   presents the same generic text; G-OS). These are **measured and reported as observed, with no
   claim made in advance**: iOS app-switcher force-quit, Android recents swipe, Android settings
   force stop, and before the first unlock after a reboot. Mirroring of an iPhone alert to a paired
   Apple Watch is OS behavior; it is measured as observed and is not a 014 feature.
2. A tap reaches the correct instance's live Approvals page through the app 030 handoff. With
   another instance active, the user is asked to switch, and nothing switches automatically. The
   human answers only after a fresh read.
3. Revocation, re-pair, identity rotation, token-family change, reinstall and provider token change
   stop delivery to the old registration and never revive an old handle (nonreuse shown on device).
4. User settings prevail: permission denied, Time Sensitive off, Focus, a lowered channel
   importance, battery restriction. Nothing claims delivery the OS withheld. While notifications are
   denied or the approval channel is blocked, the app does not keep a registration (PN-APP-1).
5. Bounds hold under bursts: coalescing, TTL, rate, capacity and backpressure limits (PN-BND). Logs
   and the relay hold no raw secrets.

Interfaces, fakes, unit tests, simulators or a successful provider HTTP response alone do not
complete this feature (section 9).

## Terms and generations

| Term | Meaning | Source |
| --- | --- | --- |
| Instance `iid` | Fingerprint of the instance key; the pinned identity | `identity.py` |
| Host generation `H` | `meta.store_revocation_epoch`. It goes up on every identity change, which revokes all devices | `store.py` |
| Pairing generation | `device_id`. A fresh one on every pairing; never reused | `pairing.py`, `store.py` |
| Credential generation | `family_id` of the token family. Issued at P4; revoked on reuse detection, P4 lost-response re-issue or device revoke | `tokens.py`, `pairing.py` |
| `k_grace` | 32-byte host secret file. Created with a new identity, and also **silently re-created** by every existing caller whenever the file is missing, unreadable or the wrong length, with no identity change (`identity.py` `_read_or_create_k_grace`). Push uses a new read-only accessor that never creates or rewrites it (PN-ISS-5) | `identity.py` |
| Registration generation `G` | New. A per-device integer, persisted and never decremented while the device is not REVOKED. A device with no generation row has `G = 0`. Its row is deleted only together with a REVOKED device (D28) | this spec |
| Row salt | New. 32 bytes from the OS CSPRNG, drawn per registration row and stored on it | this spec |
| Prompt generation | The `PromptStore` object of one listener open (spec 034 R9) | approval lane |
| Visible now | The exact AP-3 predicate for a row, evaluated now: status open, not locally expired (the AP-3 `purge(now)` rule, `expires_at + EXPIRY_GRACE_S`), its surface member available, and, for `bot_chat` rows, Desktop not holding `(iid, user, profile)` (034 `list_visible`, `handle_prompts_list`); input I-6, which AP-3 itself also calls | approval lane |
| Route handle `R` | New. Opaque per-registration handle carried in the push and mapped locally by the app to `iid` | issued here |
| Hint ref `K` | New. Opaque per-dispatch handle naming one observed approval for one registration | issued here |
| Sealed address `S` | The phone's provider address and bindings, encrypted to the relay's public key | phone |
| Effective approval owner | Exact `owner_device_ids` entry AND no explicit host controls denial (`is_approval_owner_device`). A jobs/model controls grant alone never qualifies | approval lane |
| Bot grant | `bridge.authz_state(user_id, profile) is AUTHORIZED` (ERR-3) | `reads.py` |

## User stories and acceptance scenarios

1. **Owner alert, iPhone in pocket.** Given my phone is an effective approval owner for instance A,
   has a current push registration, and has notification permission, when a Bot Chat send from my
   phone leads Hermes to request approval after I locked the phone, then an "Approval needed" Time
   Sensitive alert appears with no bot, command or instance detail.
2. **Android in Doze.** Same as 1 on an Android device forced into Doze. The alert arrives on the
   approval channel at high priority.
3. **Tap, same instance.** When I tap and A is active, the app opens A's Approvals page for the
   located bot and reads prompts fresh before any answer control is enabled.
4. **Tap, other instance.** When B is active, the app asks me to switch or stay. Staying contacts
   nothing. Switching resolves under A's new context. No automatic switch.
5. **Not pending, hidden or unknown.** If Hermes settled the approval authoritatively and the row is
   not hidden now, the resolver says `not_pending`. If the prompt is hidden from the Approvals page
   now (for example Desktop holds that bot's live turn), or there is any other doubt, the app shows
   unable to check. None of these enables an answer. A currently hidden prompt is never reported as
   `not_pending`. A prompt that was hidden earlier, was settled by Hermes meanwhile and is visible
   again may report `not_pending`, which is true (I-6, analysis A20).
6. **Revoked phone.** After `hermes hmp devices revoke`, self-revoke, refresh-reuse revocation, a P4
   lost-response re-issue or `rotate-key`, no alert is dispatched to the old registration. An already
   displayed alert resolves to `404 not_found`, and the app shows "Couldn’t check this approval…". A
   late provider error for the old registration cannot affect a newer one.
7. **Re-pair.** After re-pairing the same phone, the old route handle and hint refs never resolve
   again, and the new registration's handle differs from every earlier one.
8. **Not an owner.** A device that is not an effective approval owner, or whose user lost the bot
   grant, receives no alert for that bot. Push routes answer it `404 not_found`. A host jobs/model
   controls denial also closes approval ownership (034), so it silences push for that device too.
9. **Settings prevail.** With Time Sensitive turned off, or Focus active without allowing the app,
   the alert follows the OS rules. The app never claims it was shown.
10. **Burst.** Ten approvals in ten seconds produce at most the bounded number of alerts per
    registration. The newest hint wins. The tapped bot's Approvals page lists that bot's pending
    prompts; prompts of other bots may have no alert of their own (best-effort provider storage)
    and are found through the app's normal navigation, not a roster-wide scan.
11. **Relay or host down.** If the relay answers that it did not attempt the provider, or HMP could
    not connect, HMP retries a bounded number of times within the TTL. Any ambiguous or
    provider-side failure is not retried. Repeated failures open a circuit breaker that drops new
    alerts with a fixed code. Approvals stay answerable in the foreground. No queue survives restart.
12. **Operator visibility.** `hermes hmp push status` shows whether push is enabled and configured,
    the configured kid count and the count of active registrations, with no identifiers. It does not
    report dispatch outcomes; those appear only as fixed-code log events.

## Requirements

### PN-AV Availability under the minimum-version policy

- **PN-AV-1** Push adds no Hermes API dependency, floor, manifest, fingerprint or process latch. It is
  available for an approval row's surface exactly when that surface's approval member is available
  (`approvals` for `bot_chat`, `phone_chat` for `phone_chat`; spec 034 R1), the direct-send flag is
  effective, the host push flag is on, and a relay is configured. Unknown, later and development
  Hermes versions attempt the actual APIs, per spec 013; no exact-build gate applies.
- **PN-AV-2** Host settings, read live per request and per dispatch: `push.enabled` (default
  `false`), `push.relay_url` (no default, `⟨D3⟩`), `push.relay_kids` (a closed list of relay key IDs
  the phone may seal to), `push.relay_audience` (the relay identifier bound into every signature,
  PN-REL-2). A missing, malformed or non-HTTPS value means push is off. No host setting comes from
  the wire.
- **PN-AV-3** A relay failure is a delivery outcome, not a Hermes compatibility finding. It never
  closes approvals and never produces a spec 013 issue draft.

### PN-REG Registration routes (bearer, own device, pinned instance)

All routes are under `/hmp/v1`, use TR-5 bearer auth with `HMP-Instance`, I-JSON bodies and the
existing error envelope (ERR-2). They add no new error code and no new error extra:
`retry_state_lost` (503) and `other` (503) are existing codes, the envelope carries only the allowed
extras (`why`, `authz`, `head_message_id`, `definitive`), and `409 stale` carries none, so the app
reads the current generation with `GET`. Error messages stay the fixed text of each code and are
generic for push; the app ignores message text and acts only on `code` and `why`. The one contract
addition is four values of the closed `why` set (`OtherWhy`): `push_disabled`, `relay_unconfigured`,
`approvals_unavailable` and `push_capacity`, each allowed only on `503 write_gate_closed` (T010).
Gate order on every route: bearer → effective approval owner (else
`404 not_found`, the AP-3 non-disclosure pattern) → per-device bucket (`429 rate_limited`) → body
shape and size (`400 bad_request`, `413 too_large`) → route logic. None of them uses
`/bots/{p}/authorize`, the owner-controls `GRANT` path, any access card or any privilege-grant path.
Registration is device-scoped, not per bot.

- **PN-REG-1 `GET /push/registration`** returns
  `{"available": bool, "why"?: code, "relay_kids"?: [kid], "generation": G, "registration": null |
  {"state": "active"|"provider_gone"|"expired", "platform": "apns"|"fcm", "expires_at": int}}`.
  `GET` writes nothing and creates no row; it reports `generation` 0 for a device with no generation
  row.
  - `why` is one of `push_disabled`, `relay_unconfigured`, `approvals_unavailable` and appears only
    when `available` is false (a field of this `200` body; the same codes are the `why` values of
    `503 write_gate_closed`). `approvals_unavailable` covers every closed approval prerequisite:
    both members closed, or the direct-send flag off. The route handle is never echoed.
    `relay_kids` lets the phone choose its seal key; the iid binding is the pinned `iid` the phone
    already holds.
  - **Which row.** The device's active row, when one exists and is not in the delete fence, is
    reported `active` if usable and `expired` (re-register needed) if not. Unusable means past
    `expires_at`, its `relay_kid` no longer in the live list, its `family_id` not the bearer's
    family, or its stored route hash not re-derivable (PN-ISS-4; this includes an unreadable
    `k_grace`, PN-ISS-5). A row in the delete fence is reported as `registration: null`. With no
    active row, the device's latest row is reported (state `provider_gone` or `expired`) only if it
    left `active` by relay feedback or by the purge's expiry (PN-BND) and no write has advanced `G`
    since, that is, the row's `generation + 1` equals the current `G`. Every other case, including
    a `retired` row, is `null`.
  - A `GET` answering `200` is the app's signal that the push feature is present on this host; a
    `404` on `GET` from an older HMP means absent. The app shows the notification permission opt-in
    only after some paired instance reports `available: true`.
- **PN-REG-2 `PUT /push/registration`** body (≤ `⟨D10⟩` bytes):
  `{"v": 1, "request_id": b64u, "expected_generation": int, "platform": "apns"|"fcm",
  "addr_kind": "apns_token"|"fcm_token"|"fcm_fid", "env"?: "production"|"sandbox",
  "relay_kid": kid, "sealed": b64u, "seal_expires_at": int}`.
  - `request_id`: 16 to 32 random bytes, canonical b64u, chosen once per app registration intent
    (030 FR-1) and reused, with the identical body bytes, on every retry of that intent (PN-APP-2).
  - `sealed`: canonical b64u, decoded length within `⟨D10⟩`. HMP cannot open it and never tries.
  - `relay_kid` must be in the live `push.relay_kids` list, else `400 bad_request`.
  - `addr_kind` must match `platform` (`apns_token` for `apns`; `fcm_token` or `fcm_fid` for `fcm`).
    `env` is required for `apns` and forbidden for `fcm`. Else `400 bad_request`. These declared
    values are signed into every relay request, and the relay rejects any mismatch with the sealed
    plaintext (PN-REL-3), so the host's checks and the seal agree.
  - `seal_expires_at` must lie in `(now + ⟨D9 min⟩, now + ⟨D9 max⟩]`, else `400 bad_request`. The
    row's `expires_at` is defined as exactly `seal_expires_at` (the purge acts on it, PN-BND).
  - Requires push available (PN-AV-1 for at least one member), else
    `503 write_gate_closed {why}` with the PN-REG-1 code.
  - **Idempotent replay first**, after the configuration checks above. A replay of a request whose
    `relay_kid` was removed since gets `400 bad_request`, and one made after push became unavailable
    gets `503 write_gate_closed {why}`; neither reaches the replay check. The app treats both like
    `409 stale`: `GET`, then a new intent. Otherwise, if the device's current active row has the same
    `request_hash`:
    - a different body hash is `409 idempotency_conflict`;
    - a row `family_id` different from the bearer's family, or a row past `expires_at`, is
      `409 stale`;
    - otherwise HMP re-derives `R` from the row's stored inputs (PN-ISS-1). If `SHA-256(R)` equals
      the stored `route_hash`, return `200` with that `R` and generation, whatever
      `expected_generation` says. If it differs, or `k_grace` cannot be read (PN-ISS-5), return
      `503 retry_state_lost`; the row and `G` stay unchanged. The app treats this like
      `409 stale`: `GET`, then a new intent.
  - **No history is not a replay.** A `request_id` that matches no active row goes to CAS. Every
    successful `PUT` advanced `G` past its own `expected_generation`, and `G` never decreases for a
    non-REVOKED device. So, **absent a consistent restore of the store and the binding** (PN-ISS-2),
    a replay of an already-applied request fails CAS with `409 stale`, even after its retired row
    was purged or evicted, and HMP never answers it with fresh handle bytes. After a consistent
    restore that rolled `G` back, a byte-identical retry of a `PUT` whose acknowledgement was lost
    can pass CAS and returns a fresh `R′`, never the lost `R`. That is harmless: the app never
    committed the lost handle and commits `R′` (analysis A19).
  - **Transactional liveness.** Before either replay or CAS, the write transaction re-reads the
    device as `ACTIVE` and its bearer family as live. A revoke committed after authentication
    answers `401 revoked`, with no registration or generation write.
  - **CAS.** Otherwise, succeed only if `expected_generation == G` (0 for a device with no
    generation row), else `409 stale` with no extra. Then the capacity checks, with nothing changed
    on refusal: if the device has no active row and the instance already holds `⟨D24⟩` active rows,
    or the device has no generation row and `⟨D28⟩` non-REVOKED devices already hold one, return
    `503 write_gate_closed {"why": "push_capacity"}`. Replacing the device's own active row never
    counts against capacity. On success, in one store transaction: retire the device's current row
    (if any), advance `G` by exactly one, create the generation row if absent, draw the row salt,
    insert the new active row, enforce the retained-row caps (PN-BND), and return
    `200 {"route": R, "generation": G, "expires_at": int, "state": "active"}`. A transaction that
    changes a device's registration state advances that device's `G` once, however many rows it
    touches. `G` stays below 2^53 (I-JSON): if `G + 1` would reach 2^53 the write is refused
    `503 other` with nothing changed. This is unreachable at the proposed rate buckets.
  - **Collision.** A UNIQUE violation on `route_hash` (whatever its cause, including an identical
    salt draw) aborts the whole transaction: no row is inserted, the previous row stays active, `G`
    does not advance, and the answer is `503 other`. A retry of the same intent draws a fresh salt.
  - The device's live token family, `iid` and `H` are recorded on the row.
- **PN-REG-3 `DELETE /push/registration`** body `{"v": 1, "expected_generation": int}`. CAS as
  above. It retires the current row (if any), advances `G` by one and returns
  `200 {"generation": G}`. Only a `200` confirms removal; every other outcome is "not confirmed"
  (§11, PN-APP-3). Deleting with no row is still a CAS and still advances `G`, so a late older `PUT`
  cannot land.
  - **Capacity.** `DELETE` of an existing registration is never refused for capacity and never
    inserts into a capped table: retiring is an in-place update, and the device already has its
    generation row. Only a `DELETE` from a device with no generation row would create one, so it is
    subject to the D28 cap: while `⟨D28⟩` non-REVOKED devices already hold one, it is refused
    `503 write_gate_closed {"why": "push_capacity"}` with no write. Under the invariant "an active
    registration implies a generation row", nothing is registered for that device. The answer is
    still not a `200`, so it confirms nothing, and the app keeps its pending delete intent
    (PN-APP-3).
  - **Documented race (no invariant waiver).** A `PUT` delayed in flight can land after capacity
    frees, after such a no-generation `DELETE` was refused. The app's pending delete intent then
    retries as an ordinary CAS `DELETE` against the now-existing generation row and removes it.
  - **Store write failure.** If the store write itself fails (for example the disk is full),
    eligibility still closes: the listener adds the device's current `route_hash` to an in-memory
    delete fence (PN-BND) that dispatch and resolve check, and `GET` stops reporting the row as
    active (PN-REG-1). The answer is `503 other` (not confirmed) and the app retries
    `GET`/`DELETE`. The fence entry is removed once a store write retires that row. The fence does
    not survive a restart; between a restart and a successful `DELETE`, a revocation or the seal's
    `not_after`, alerts may resume and resolve as unable to check (residual, analysis A12). That is
    why the app keeps the pending intent and never says alerts stopped before a `200`.
- **PN-REG-4 Limits.** At most one active registration per device per instance, at most `⟨D24⟩`
  active registrations per instance, and at most `⟨D28⟩` generation rows of non-REVOKED devices.
  Proposed buckets `⟨D11⟩`: registration writes and status reads per device per minute. A refused
  write changes nothing.
- **PN-REG-5 No cross-instance effect.** Every row carries the serving `iid`. A route, handle or
  sealed address registered on one instance has no meaning on another. HMP never forwards to,
  falls back to or names another instance.

### PN-ISS Issuer: fresh, nonreused handles validated against the exact registration

- **PN-ISS-1 Route handle.**
  `R = b64u(HMAC-SHA256(k_grace, transcript("HMP1-PUSH-ROUTE", iid, H, device_id, family_id, G,
  salt)))`, which is 43 characters and inside app 030's 22 to 64 character shape. The store keeps
  `SHA-256(R)` and the inputs, including the salt; it never keeps `R`. `R` can be re-derived only
  with the store **and** the `k_grace` file, the same custody as the refresh retry grace (R16,
  CS-13). The dispatcher re-derives `R` for the payload; a replay re-derives it for the response.
  Both compare the result with the stored hash first. The `request_id` is used only for idempotency
  (`request_hash`), not as a handle input.
- **PN-ISS-2 Nonreuse is a computational argument, not a proof.** Under the assumption that
  `k_grace` is secret and uniformly random, HMAC-SHA256 is treated as a PRF. Distinct transcripts
  then give outputs that collide only with negligible probability; distinct inputs alone do not make
  outputs mathematically distinct. The transcripts differ across devices (`device_id` is fresh per
  pairing), credential generations (`family_id`), host generations (`H`), registration generations
  (`G` persisted, only increasing) and rows (a fresh 32-byte CSPRNG salt). The salt keeps handles
  fresh where the other inputs can repeat:
  - `k_grace` can be re-created without an identity change (Terms). A new `k_grace` is a new PRF
    key; old handles then stop validating (PN-ISS-4) rather than becoming reusable.
  - A consistent backup restore of both the store and the binding directory rolls `G` back without
    `_classify` noticing (the epochs agree). The salt keeps the next handle fresh. The replay CAS
    guarantees of PN-REG-2 are stated absent such a restore; it is the one case in which a replay of
    an applied `PUT` can succeed, with fresh bytes (analysis A19).
  A UNIQUE index on `route_hash` over stored rows (active and retained) rejects an actual
  collision deterministically, but only while the row is stored. Beyond retention or cap eviction
  (PN-BND), nonreuse rests on the salts, `G` and the PRF assumption, and is stated that way, not as
  a test result.
- **PN-ISS-3 Hint ref.** `K` is 32 bytes from the OS CSPRNG, b64u (43 characters), minted per
  (approval row, registration) dispatch. It is held only in process memory with its binding
  `(SHA-256(R), G, prompt generation, row key)`. A collision with a live entry is redrawn. `K` lives
  while its row is open in its prompt generation, then for a margin of `⟨D14 margin⟩` after the row
  settles, and never longer than `⟨D14 hard max⟩`. It dies on listener close or restart, like the
  rows it names (spec 034 AP-2). Map overflow follows PN-BND.
- **PN-ISS-4 Validation is exact.** A registration is usable only when every bound field equals the
  current value: row `active`, row `device_id` equals the bearer's device, row `family_id` equals the
  bearer's family (resolver) or is a live family (dispatch, PN-DSP-4), row `iid` and `H` equal the
  serving ones, row generation equals the device's current `G`, not expired, `relay_kid` still in the
  live list (dispatch), the row's `route_hash` is not in the delete fence (PN-REG-3), and the
  re-derived `SHA-256(R)` equals the stored `route_hash`. A hint is
  accepted only when its binding names that exact row hash and generation, and the current,
  unclosed prompt generation. Existence alone never suffices.
- **PN-ISS-5 `k_grace` access for push (new read-only accessor).** Push never calls the existing
  `LoadedIdentity.k_grace()`, which re-creates and rewrites the file. It uses a new read-only
  accessor that reads the file, checks its length, and never creates, rewrites, deletes or changes
  the mode of it. It does not reuse `_read_private`'s mode-tightening side effect.
  Existing callers (the refresh grace and others) are unchanged, and no existing caller is edited.
  - Every file read runs off the event loop (`asyncio.to_thread` or the existing executor), once per
    request or per batch, never once per row and never inside a store transaction.
  - A missing, unreadable, wrong-length or transiently failing read means "not re-derivable" for
    that call only: `GET` reports `expired`, dispatch skips the row, a replay answers
    `503 retry_state_lost`, a first-issue `PUT` answers `503 other`, and that call writes nothing
    because of the read failure. A
    transient read error therefore never creates, rewrites or deletes the secret, and by itself
    never changes a row's state. The purge's expiry of a hash mismatch (PN-BND) changes state only
    after a successful read whose derived hash differs. Independent authoritative expiry (past
    `expires_at`, removed kid) and revocation still change row state in the purge, with the
    secret unreadable.
  - This needs its own source tests (T021, T024). No current source is edited by this spec.

### PN-RES Hint resolver (`POST /push/hints/resolve`)

- **PN-RES-1** Body `{"v": 1, "hint": K}` with `K` a 22 to 64 character canonical b64u string, else
  `400 bad_request`. There is no `route` field: this matches the accepted app 030 S1 resolver port
  (`HintResolveRequest{iid, epoch, hintRef}`), which never carries the route handle. Order: bearer →
  effective approval owner (`404`) → bucket (`429`) → body shape (`400`) → push flag on (`404`) → the
  **bearer device's** single current active registration, validated exactly (PN-ISS-4 with the
  bearer's family; `404`) → exact hint whose binding names that registration's route hash and `G`
  (`404`) → bot grant for the hint's profile (`404`, masking ERR-3 detail) → the approval gate for
  the row's surface (spec 034 `_require_approvals_gate`; `503 write_gate_closed`) → visibility
  (I-6; a hidden row is `404`, whatever its status) → row state.
- **PN-RES-2 Results.** `200 {"state": "located", "profile": p}` only when the row is open in the
  current prompt generation and visible now (I-6). `200 {"state": "not_pending"}` only when the row
  is not hidden now and was settled by an authoritative cause (section 10, I-2). Every other case is
  `404 not_found`. That covers unknown, foreign, revoked, rotated, expired, a closed or rebound
  generation, a hidden row (Desktop held, member closed), a locally expired row, a purged or
  evicted row or hint, and an unknown settle cause.
  - **Current visibility (root choice; no sticky bit).** Hiddenness is evaluated at resolve time and
    is not remembered. A row that was hidden at some earlier moment, was settled authoritatively by
    Hermes meanwhile, and is visible now may answer `not_pending`. That is a true statement about
    Hermes. 014 adds no sticky hidden bit and no extra history observer to the approval lane.
  - **Local expiry.** A row past `expires_at + EXPIRY_GRACE_S` is locally expired exactly as AP-3's
    `purge(now)` treats it: no longer open, so `404`. I-6 applies this rule, and AP-3 calls the same
    I-6 seam, with an equivalence test (section 10).
  - **Phone rows.** AP-3 reconciles Phone rows through `list_gateway_approvals` before listing; the
    resolver does not (PN-RES-4). `located` for a Phone row that Hermes has since withdrawn is the
    same accepted residual as "located but settled elsewhere" (analysis A20).
- **PN-RES-3** The response never carries a request ID, command, description, choices, run or
  session identifiers, expiry, instance name or any authority. The located profile is a navigation
  hint for the app's own fresh AP-3 read (030 FS-3, SR-4).
- **PN-RES-4** The resolver mutates nothing. A hint can be resolved again while it lives
  (PN-ISS-3). Proposed bucket `⟨D11⟩` per device per minute.

### PN-DSP Dispatch

- **PN-DSP-1 Trigger.** Only a newly inserted **approval** row (`kind == "approval"`, either
  surface) in an open prompt generation (I-1). Clarify prompts, settlements, cancellations, chat,
  jobs and model events never dispatch (030 RD-3). A row that was hidden at dispatch time is not
  dispatched later when it becomes visible; the app's catch-up (T047) covers it.
- **PN-DSP-2 Non-blocking producer.** The I-1 notification only hands
  `(row key, surface, prompt generation, expiry estimate)` to one bounded per-listener queue
  (`⟨D12⟩`) owned by the HMP listener's event loop: `put_nowait` when called on that loop,
  `loop.call_soon_threadsafe` otherwise. It never awaits, takes no store lock and does no I/O. A full
  queue drops the new event with the fixed log `push_dispatch outcome=queue_full`. It never blocks
  or fails a send, stream, answer or Hermes callback. Exceptions are swallowed with a fixed outcome.
  The queue and its worker are created at listener open and cancelled at close; failing to create
  them leaves push off for that listener and does not block listener open or any existing route.
- **PN-DSP-3 Re-check at dequeue and before each send.** The worker drops the event at dequeue if
  its TTL has already run out. At dequeue and again immediately before each relay request, it
  requires: generation current and unclosed; row still open and visible now (I-6); the surface's
  member available; direct send effective; push enabled; relay configured; breaker closed. Any
  failure drops the event (or that recipient) with a fixed outcome.
- **PN-DSP-4 Recipients.** Every device that has the row's `user_id`, state `ACTIVE`, effective
  approval ownership read live, and one active, unexpired registration with this `iid`, `H` and its
  current `G`, whose **row** `family_id` is a live, unrevoked family of that device within
  `REFRESH_ABSOLUTE_TTL_S` (some other live family is not enough), whose `relay_kid` is in the live
  list, and whose re-derived route hash matches. The row's `(user_id, profile)` must hold the bot
  grant at dispatch time. At most `⟨D13⟩` recipients per row, most recently registered first. No
  other user, instance or fallback target.
- **PN-DSP-5 Coalescing.** One coalescing slot per `(registration, collapse scope ⟨D5⟩)`. If the
  slot sent within `⟨D6 min interval⟩`, the new event replaces the slot's single pending event, and
  one trailing send fires at the window end after the PN-DSP-3 re-check. The newest hint wins. The
  collapse identifier is
  `C = b64u(HMAC-SHA256(k_grace, transcript("HMP1-PUSH-COLLAPSE", SHA-256(R), scope)))` truncated
  to `⟨D5⟩`, at most 64 bytes. It is opaque and reveals no profile, but it is a stable pseudonym per
  (registration, bot) for the registration's lifetime (analysis A6).
- **PN-DSP-6 TTL.** `ttl_s = clamp(expiry_estimate - now + EXPIRY_GRACE_S, ⟨D7 floor⟩, ⟨D7 cap⟩)`,
  or `⟨D7 default⟩` when no estimate exists. The estimate is HMP's config-derived display hint, not
  Hermes's authoritative deadline. A provider may still deliver after it. A late tap is safe
  (PN-RES-2).
- **PN-DSP-7 Rate.** Per registration at most `⟨D6⟩` sends per hour. Over the cap the event is
  dropped with `push_dispatch outcome=rate_capped`. The relay enforces its own caps (PN-REL-6).
- **PN-DSP-8 Retry only before a provider attempt.** Each attempt is a new signed request with a
  fresh `ts` and `nonce` and the same `K` and `C`. Automatic retry is allowed only when the provider
  was certainly not attempted: a connection that failed before the request was written (DNS, TCP or
  TLS), or relay `503 unavailable`. At most `⟨D8⟩` retries, with backoff and jitter, only while the
  TTL has not run out. Never retry: a timeout or connection loss after the request was written,
  relay `502 provider_unavailable`, `409 replayed`, `429 rate_limited`, `400`, `401`, `410`, `422`,
  or any malformed, oversized or unknown response. Those outcomes are ambiguous or definitive and
  are dropped with a fixed code. No queue or retry survives a listener close or restart.
- **PN-DSP-9 Feedback CAS.** `provider_gone` marks the registration `provider_gone`, and
  `sealed_invalid` marks it `expired`, only if `(SHA-256(R), G)` is still the device's current
  active registration. The same transaction advances `G` by exactly one (PN-REV rule). Late feedback never touches a
  newer registration.
- **PN-DSP-10 Lifecycle and isolation.** The worker never holds the prompt-store lock or a store
  transaction across an `await`. Store writes from the worker are single short transactions. A
  circuit breaker opens after `⟨D8 breaker⟩` consecutive retriable failures or post-write timeouts
  and stays open for its cool-down; while open, events are dropped at once with
  `outcome=breaker_open`, with no waiting. Listener close cancels the worker and every in-flight
  relay request, closes the HTTP client, and waits at most `⟨D8 close⟩` for that; it never waits on
  the relay. A cancelled request whose alert is still delivered later resolves `404`.

### PN-BND Resource bounds (every table and map has a cardinality and an overflow rule)

Active registrations are not bounded by the dispatch queue. HMP does not cap the number of paired
devices, so push sets its own caps. Values use the frozen D mapping; owner-set deployment budgets remain pending.

| Object | Scope | Cardinality bound | Overflow rule |
| --- | --- | --- | --- |
| Active registration rows | store, per instance | ≤ 1 per device and ≤ `⟨D24⟩` | A `PUT` from a device without an active row is refused `503 write_gate_closed {why: "push_capacity"}`, nothing changed. Replacement, `DELETE` of an existing registration and every retirement are never refused. A row that can never deliver again (past `expires_at`, kid no longer live, hash no longer re-derivable) is expired by the purge and stops counting: capacity frees no later than the seal maximum `⟨D9 max⟩` (14 d) plus the next purge interval (up to 1 h while the listener runs) for expiry, and within one purge interval for kid removal or a hash mismatch after a successful `k_grace` read. A stopped listener delivers nothing and purges nothing; the purge runs again at the next listener open. A row of a device that lost owner status stays active and inert until its `expires_at`, because owner status is live and reversible. |
| Retained rows (`retired`, `provider_gone`, `expired`) | store, per instance | ≤ `⟨D25 per device⟩` per device and ≤ `⟨D25 total⟩` in total, each for at most `⟨D9 retention⟩` from its state change | Enforced only inside a `PUT` transaction and the push purge step, by deleting the oldest retained rows first (per device, then globally). Retirement in `DELETE`, feedback CAS, purge expiry or post-commit cleanup (PN-REV) does not enforce caps, so the table may transiently exceed `⟨D25 total⟩` by at most `⟨D24⟩` rows until the next `PUT` or purge. |
| Device generation rows (`G`) | store | ≤ `⟨D28⟩` rows whose device is not REVOKED | A first `PUT`, or a `DELETE`, from a device without a generation row while `⟨D28⟩` such rows exist is refused `503 write_gate_closed {why: "push_capacity"}`, nothing changed and no write. The purge deletes the generation and registration rows of REVOKED devices (below), so they do not count. A generation row of a non-REVOKED device is never deleted or decreased. An active registration implies its device's generation row. After 256 distinct non-REVOKED devices have written, a new device remains capacity-blocked until the operator revokes some; registration expiry alone does not release a generation slot. |
| Dispatch queue | memory, per listener | `⟨D12 queue⟩` events | Drop the new event, `queue_full`. |
| Recipients per row | memory | `⟨D13⟩` | Most recently registered first; the rest skipped, `recipients_capped`. |
| In-flight relay requests | memory, per listener | `⟨D12 concurrency⟩` | The worker waits for a free slot; the dequeue TTL check still applies. |
| Hint map | memory, per listener | `⟨D14 entries⟩` | Evict, in order: entries whose row settled or whose generation closed; then the oldest by mint time. An evicted hint resolves `404`. |
| Coalescing slots | memory, per listener | `⟨D26⟩` | Evict the least recently used idle slot (no pending trailing event). If every slot holds a pending event, drop the new event, `coalesce_full`. Evicting an idle slot forgets its last send time, which loosens the `⟨D6⟩` minimum interval for that slot once; the per-device hourly cap still bounds the rate (analysis A22). |
| Hourly per-device counters | memory, per listener | keyed by `device_id`; ≤ `⟨D28⟩` (only a device with a generation row has one) | A device's counter survives a re-registration (retire plus new `PUT`) while the device is `ACTIVE` and has an active registration. It is removed when its hour window ends with no active registration, or when the device stops being `ACTIVE`. Never evict a live counter. If the table is full anyway, refuse the send, `rate_table_full` (fail closed, not a reset). A restart discards the table (analysis A22). |
| Delete fence (route hashes whose `DELETE` write failed) | memory, per listener | ≤ `⟨D24⟩` (one per active row; removed when the row leaves `active`) | Cannot exceed the active cap. If it would, every dispatch is refused, `fence_full` (fail closed). |
| Per-device request buckets (`⟨D11⟩`) | memory, shared `RateLimiter` | `LIMITER_TABLE_MAX` (4096, LRU) | The existing limiter's behavior: eviction or restart can only loosen a limit briefly. Keys are authenticated device IDs, not attacker-chosen. |

Rows of REVOKED devices wait at most one purge interval before deletion. Their number is bounded by
the operator-gated pairing and revocation rate over that interval, not by `⟨D28⟩`.

**REVOKED is terminal (D28 terminal-state guard).** The purge deletes the generation row and every
registration row of a REVOKED device inside a `BEGIN IMMEDIATE` transaction that re-reads
`devices.state` (never a cached value). That is safe only while no code path returns a REVOKED
device to another state. In production the only writes to `devices.state` are to REVOKED
(`revoke.py`; the identity-change path in `store.py`), and `Store.set_device_state` has no
production caller. The implementation (T020) adds an explicit guard in `Store.set_device_state` that
refuses to change a REVOKED device, and a test that tries to revive a REVOKED device through it and
fails. The REVOKED purge is not enabled without that guard and test. Device IDs are fresh per
pairing and never reused, and a REVOKED device cannot authenticate, so a purged row is never needed
again.

The push purge step runs at listener open and then hourly on the listener's loop. HMP base
`4d6863e` has no existing store purge job to join (only the `IDEMPOTENCY_RETENTION_S` comment);
014 adds its own bounded step. A pass reads `k_grace` once, off the loop (PN-ISS-5), then runs
short store transactions, each bounded by `⟨D24⟩`, `⟨D25⟩` or `⟨D28⟩` rows, that:
- delete retained rows past retention or over the caps, oldest first, and wipe the secret columns
  of any non-active row (PN-PER);
- delete the generation row and every registration row of each REVOKED device (above);
- retire active rows whose device is no longer `ACTIVE` or whose family is revoked (advancing `G`);
- **expire** (`state := expired`, advance that device's `G` once, wipe the secret columns) every
  active row that is past `expires_at`, whose `relay_kid` is no longer in the live list, or whose
  route hash no longer re-derives after a **successful** `k_grace` read. Only the hash-mismatch
  case needs a successful read. Past-`expires_at` and removed-kid expiry, the REVOKED and
  retired-row cleanup, and the retained-row purge do not read `k_grace` and proceed whether or not
  it is readable. An unreadable `k_grace` therefore never expires a row merely because it is
  unreadable, and never blocks the other steps.

A purge failure is logged with a fixed code and changes no revoke, token, P4, route or Hermes
outcome.

**Lost idempotency history.** Once a retained row is purged or evicted: a replay of its `PUT` gets
`409 stale` (CAS, PN-REG-2); its `R` and any surviving hint resolve `404` (unable to check); late
relay feedback for it is a no-op. Nonreuse past that point is the computational argument of
PN-ISS-2 (salts and `G`). Absent a consistent restore of the store and binding, HMP never answers a
replay with fresh handle bytes; after such a restore it can, harmlessly (PN-REG-2, analysis A19).

### PN-REL Relay contract (HMP to relay, relay to providers)

- **PN-REL-1 Endpoint.** `POST {push.relay_url}/v1/push`, HTTPS only, from host configuration only.
  Use `aiohttp.ClientSession(trust_env=False)`, no redirects, bounded response (at most 1 KiB),
  platform trust store, optional SPKI pins `⟨D3⟩`. No phone-supplied URL, host or kid can change the
  destination. A kid not in the host list is refused at registration and skipped at dispatch.
- **PN-REL-2 Request.**
  `{"v": 1, "kind": "approval", "aud": push.relay_audience, "iid_spki": b64u(SPKI DER), "ts": int,
  "nonce": b64u(16 B), "kid": kid, "platform": p, "addr_kind": a, "env"?: e, "sealed": S,
  "route": R, "hint": K, "collapse": C, "ttl_s": int}` (at most 4 KiB),
  plus header `HMP-Relay-Signature: b64u(ECDSA-P256(instance key,
  transcript("HMP1-PUSH-RELAY", aud, iid, ts, nonce, kid, platform, addr_kind, env, SHA-256(S), R,
  K, C, ttl_s, kind)))`, with an absent `env` encoded as the empty string. The instance key already
  signs pairing transcripts under distinct tags; reuse is decision `⟨D2⟩` under the conditions in
  plan §7.3. The audience stops a request signed for one relay (for example the owner relay) from
  being replayed to another that shares kids.
- **PN-REL-3 Relay verification order.** Size and shape; then the per-source pre-verification limit
  and the global verify budget (`⟨D17 verify⟩`); then signature with the supplied SPKI. Then `aud`
  equals the relay's own audience, `iid := base32(SHA-256(SPKI))` (52 characters, lowercase,
  unpadded, as `crypto.spki_fingerprint`), `ts` within the skew, nonce unseen, kid known, `iid`
  allowed when the relay runs an allowlist (`⟨D23⟩`). Each nonce is kept until `ts + CLOCK_SKEW_S`
  (not measured from receipt), so a nonce lives at most 240 s. At the verify budget of 20/s the
  cache therefore holds at most 4,800 nonces, below `⟨D18 cache⟩` (16,384): a full cache is a
  defensive path, not an expected one. A seen nonce is `409 replayed`. If the replay cache is full,
  the request is refused `503 unavailable` and no unexpired nonce is evicted. Then HPKE-open `S`
  and check its bindings: `iid` equals the computed iid, `app` is in the relay's app allowlist,
  `platform` and `addr_kind` match the signed values and each other, `not_after > now` and
  `not_after ≤ now + ⟨D9 max⟩`, and `env`. For `apns`, `env` matches both the relay's APNs mode
  and the signed `env`. For `fcm`, `env` is absent from the signed request and from the seal (a
  signed `env` on an `fcm` request is `400 bad_request`, a sealed one `422 sealed_invalid`), and the
  relay's environment mode does not apply. Then the per-key rate limits and the global hourly
  budget in the order of PN-REL-6. Only then is any provider called.
- **PN-REL-4 Responses** (closed set, JSON `{"result": ...}`): `202 accepted`;
  `410 provider_gone`; `422 sealed_invalid`; `409 replayed`; `429 rate_limited` (the relay's own limits only;
  provider not attempted; provider throttling is never `429`); `401 unauthorized`; `400 bad_request`;
  `502 provider_unavailable` (the provider was attempted and answered 5xx, throttled us (APNs `TooManyRequests`, FCM `QUOTA_EXCEEDED`), timed out or the outcome
  is otherwise ambiguous); `503 unavailable` (the provider was **not** attempted). The relay never
  returns `503 unavailable` after a provider attempt began, and never retries a provider call itself.
  HMP treats anything outside this set, malformed, oversized or timed out after the request was
  written as ambiguous (PN-DSP-8). HMP never logs or echoes relay text.
- **PN-REL-5 Payload templates are fixed by the relay.** The host contributes no visible text.
  - **APNs (direct, iOS):** `apns-push-type: alert`, `apns-priority: 10`,
    `apns-expiration: now + ttl_s` (nonzero), `apns-topic: <bundle ID from the allowlist>`,
    `apns-collapse-id: C`, random `apns-id`. Body:
    `{"aps": {"alert": {"title": "Approval needed"}, "sound": "default",
    "interruption-level": "time-sensitive"}, "hmp": {"v": 1, "route": R, "hint": K}}`.
    The visible text form, literal or `loc-key`, is `⟨D15⟩`.
  - **FCM HTTP v1 (Android):** the target field is chosen from the sealed `addr_kind`: `token` for
    `fcm_token` (marked deprecated in the v1 reference, which says to use `fid`), `fid` for
    `fcm_fid`. `android.priority: "HIGH"`, `android.ttl: "<ttl_s>s"`,
    `android.collapse_key: <one constant>` (FCM allows at most four distinct keys at a time),
    `android.restricted_package_name: <package from the allowlist>`,
    `android.notification: {"title": "Approval needed", "channel_id": <approval channel>,
    "tag": C}`, `android.data: {"hmp_v": "1", "hmp_route": R, "hmp_hint": K}`. A notification
    message lets the system show the generic alert **while the app is in the background** without
    app code or a host fetch. In the foreground, app code decides presentation (PN-PLAT). The Play
    services proxy setting is `⟨D16⟩`.
  - **iOS through FCM is not used.** FCM's own APNs example uses `apns-priority: 5`. Direct APNs
    alerts use priority 10 and an explicit expiration. Mixing the two is a defect.
- **PN-REL-6 Relay rate and abuse limits** `⟨D17⟩`, per relay replica: a global verify budget and a
  per-source-address limit (both before signature verification), then per host `iid`, per
  destination (`HMAC(relay secret, provider address)`), per `(destination, iid)` (at most the HMP
  per-device hourly rate), and a global hourly budget `B`. **Order:** every per-key cap is checked
  before the global budget, and a request is counted against any of them only if all of them admit
  it, so only admitted requests charge the global budget. The per-`(destination, iid)` cap stops
  **one** `iid` from exhausting the destination ceiling and suppressing another host's alerts to
  the same phone; the per-destination cap stays as a ceiling that bounds spam to one phone.
  Residuals, recorded and not closed (analysis A14, A17):
  - Under open enrollment an `iid` costs nothing, so `n ≥ ⌈ceiling / pair cap⌉` sybil `iid`s (2 at
    the proposed 60 and 30) holding a leaked address still exhaust the destination ceiling and
    suppress a real host's alerts to that phone. Keeping the ceiling keeps the spam bound at the
    price of this suppression; dropping it would remove the suppression but allow unbounded spam
    across many `iid`s. 014 keeps the ceiling.
  - In public (R1) mode, unauthenticated traffic from many source addresses can exhaust the global
    verify budget, and sybil `iid`s sealing random addresses can exhaust the global hourly budget
    `B`. Those requests pass the seal checks, because the relay checks `app`, `env` and bindings,
    not whether an address is real. Either exhaustion denies all R1 alerts. Floods of garbage
    addresses may also affect the relay's standing with a provider (`EVIDENCE_GAP`, not checked).

  Public R1 stays inactive and owner-pending (O1). Each limiter table and the replay cache has the
  cardinality and overflow rule in plan §6.5. The relay runs as a **single replica** (`⟨D27⟩`);
  more replicas need shared replay and rate state, and a new review.
- **PN-REL-7 Relay custody.** HPKE private keys (per kid), the APNs token signing key (`.p8`), and
  FCM credentials live only in the relay's secret store. They never reach HMP, the app, CI logs or
  any repository. The relay keeps no database of provider addresses. It holds bounded in-memory
  rate and replay state, and optionally a bounded negative cache of HMACs of addresses the provider
  reported gone.
- **PN-REL-8 Relay logging.** Only the kid, the result code, the provider status class and, at
  most, a relay-local keyed hash of the `iid` that rotates with the relay's log key. Never a raw
  `iid` or `iid` prefix, an address, a sealed blob, `R`, `K`, `C`, a signature or a provider
  response body.

### PN-SEAL Sealed provider address (phone to relay, opaque to HMP)

- **PN-SEAL-1** Plaintext, canonical JSON (at most `⟨D10⟩` bytes):
  `{"v": 1, "iid": iid, "platform": "apns"|"fcm",
  "addr_kind": "apns_token"|"fcm_token"|"fcm_fid", "env": "production"|"sandbox" (apns only),
  "app": bundle-or-package, "addr": provider address, "not_after": seal_expires_at,
  "n": b64u(16 B)}`. `addr_kind` must match `platform`; the relay rejects a mismatch as
  `sealed_invalid`. Make no assumption about the address size beyond the bound.
- **PN-SEAL-2** HPKE (RFC 9180) base mode to the relay public key named by `kid`, with
  `info = "HMP push seal v1"` and `aad = kid`. The suite is `⟨D1⟩`. Relay public keys ship in the
  app build as a closed `kid → key` list; there is no runtime key fetch.
- **PN-SEAL-3** The phone re-seals and re-registers when the provider address or its kind changes,
  the kid list changes, the registration reads `expired` or `provider_gone`, or fewer than
  `⟨D9 refresh⟩` remain before `not_after`. Apple says not to cache device tokens and to expect a
  new token after restore, new device or OS reinstall.

### PN-REV Revocation, post-commit cleanup and lifecycle

**Eligibility is validation-based.** Dispatch and resolve check device state, the row's own family,
`H`, `G`, expiry and kid live (PN-ISS-4, PN-DSP-4). A committed revocation therefore closes push
eligibility immediately, even if no cleanup statement ever runs or the cleanup fails. Cleanup is
defense in depth and capacity hygiene, not the mechanism of revocation.

**Rule: separate best-effort cleanup after commit.** Any statement that sets
`token_families.revoked_at`, sets a device to a non-`ACTIVE` state, or bumps `H` makes the matching
rows retire-able. Push cleanup never runs inside the cause's transaction: no push statement,
savepoint or push error handling is added to a revoke, refresh-reuse, P4 re-issue or
identity-change transaction, and 014 promises no savepoint isolation. The reason is that SQLite can
roll back the whole transaction on some errors (`SQLITE_FULL`, `SQLITE_IOERR`, `SQLITE_NOMEM`,
`SQLITE_BUSY`), which would discard the cause itself. The delta review reproduced this in memory
with Python `sqlite3` in the `store.py` connection mode (`isolation_level=None`): the cause row
was gone, `ROLLBACK TO` reported no such savepoint, and `COMMIT` reported no active transaction.

After the cause's transaction has committed (in the refresh-reuse path, before `REVOKED` is
raised), the code makes one best-effort call: a separate `Store.transaction()` that retires every
active row whose device is not `ACTIVE`, whose family is revoked or whose `H` is not current. It is
idempotent and derives its work from current store state, so it needs only the trigger from the
cause. Any error in it, including a real `SQLITE_FULL`, is caught, logged with a fixed code
(`push_purge outcome=cleanup_failed`) and swallowed. The cause's outcome and its store rows are
exactly what they would be without push. The purge step (listener open and hourly) retires
whatever a failed or skipped cleanup left. Every transition of a row out of `active` wipes the
row's secret columns and advances that device's `G` by exactly one per transaction.

Cleanup call sites are `revoke_device` and `self_revoke` after their outer `with` exits,
`_retry_or_reuse` after its outer `with` and before `raise HmpError(REVOKED)`, `_outcome` after its
outer `with`, and `_new_identity` after `revoke_all_for_identity_change` returns. Never call cleanup
from `_revoke_in`, `issue_family` or a helper receiving the open `conn`: `Store._write_lock` is not
reentrant, and nesting the transaction would hang the cause.

| Cause | Effect on registrations | Effect on hints and queued dispatch |
| --- | --- | --- |
| Operator revoke, self-revoke (`_revoke_in`) | the device's active row → `retired` (post-commit cleanup) | validation skips it at once; hints bound to it resolve `404` |
| Refresh reuse → family revoked (`tokens._retry_or_reuse`) | rows with that `family_id` → `retired` | as above |
| P4 lost-response re-issue (`pairing.py`, `outcome="reissued"`) revokes the device's earlier family | rows with a revoked `family_id` of that device → `retired` | as above; the app re-registers under the new family |
| `store.revoke_family`, `revoke_families_for_device`, `set_device_state` (no production caller found; hazards) | same rule if a caller is ever added; `set_device_state` gets a guard that it cannot change a REVOKED device (PN-BND, T020) | as above |
| Identity change, `rotate-key`, clone/restore (`revoke_all_for_identity_change`) | every row → `retired`, then the REVOKED purge deletes them; `H` and `iid` change | listener restarts; memory gone |
| New `PUT`/`DELETE` | the previous row → `retired`, `G` advances once | old `R`/`K` never resolve |
| Relay `provider_gone` / `sealed_invalid` | CAS to `provider_gone` / `expired`, `G` advances once (PN-DSP-9) | none |
| `expires_at` (= `seal_expires_at`) passed, kid removed from the host list, `k_grace` re-created | inert; reported `expired` by `GET`; the purge sets them `expired`, advances `G` and frees capacity (PN-BND). Only the `k_grace` re-created (hash mismatch) case needs a successful read | skipped |
| Owner removed from `owner_device_ids`, host denial | rows kept but inert: dispatch and resolve re-check live; the purge expires them at `expires_at` | skipped; resolve `404` |
| Bot grant revoked in Hermes | per-profile re-check | skipped for that bot; resolve `404` |
| `push.enabled` off, relay unset | rows kept, inert; expired at `expires_at` | nothing dispatched; resolve `404` |
| Listener close, gateway restart | rows kept | queue, coalescing slots, counters and hint map discarded |

Non-active rows keep only `route_hash`, the salt and the generation fields, and are purged under
PN-BND. Device rows are never deleted. A generation row of a non-REVOKED device is never deleted or
decreased, so its `G` never resets except through a consistent restore of the store and binding
(PN-ISS-2). The generation and registration rows of a REVOKED device are deleted by the purge
(D28); REVOKED is terminal, enforced by the guard on `set_device_state` (PN-BND).

### PN-PER Persistence (store schema version 3; additive)

- `push_registrations(route_hash BLOB PK, device_id TEXT NOT NULL REFERENCES devices,
  family_id TEXT NOT NULL REFERENCES token_families, iid TEXT NOT NULL,
  host_generation INTEGER NOT NULL, generation INTEGER NOT NULL, salt BLOB NOT NULL,
  platform TEXT NOT NULL CHECK IN ('apns','fcm'), addr_kind TEXT NOT NULL, env TEXT,
  relay_kid TEXT NOT NULL, sealed BLOB, request_hash BLOB, body_hash BLOB,
  state TEXT NOT NULL CHECK IN ('active','provider_gone','expired','retired'),
  created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, state_changed_at INTEGER NOT NULL)`,
  where `expires_at` is exactly the request's `seal_expires_at`, with
  `CHECK (state <> 'active' OR (sealed IS NOT NULL AND request_hash IS NOT NULL AND body_hash
  IS NOT NULL))` and a partial UNIQUE index on `device_id` where `state = 'active'`. Leaving
  `active` sets `sealed`, `request_hash` and `body_hash` to NULL.
- `push_device_generations(device_id TEXT PK REFERENCES devices, generation INTEGER NOT NULL
  CHECK (generation >= 0 AND generation < 9007199254740992))`. Invariant: a registration in state
  `active` implies a generation row for its device. The transaction that inserts a device's first
  active row creates the generation row, and the purge deletes a generation row only together with
  all registration rows of a REVOKED device. A test asserts the invariant after every writer
  (`PUT`, `DELETE`, feedback, cleanup, purge).
- No raw `R`, `K`, request ID, provider address or relay response is stored. `sealed` is
  ciphertext only the relay can open. It is still treated as secret: never logged, printed or
  exported. The salt is not secret without `k_grace`. Hints, coalescing, counters and queues are
  process memory only.
- The migration from schema 1 and 2 is additive and idempotent; no existing table or column changes.

### PN-LOG Logging and privacy

- Fixed events only: `push_registration`, `push_resolve`, `push_dispatch`, `push_relay`,
  `push_purge`, with fixed outcome codes (for example `push_purge outcome=cleanup_failed`) and at most an 8-character `device_id` prefix. `R`, `K`,
  `C`, `S`, the salt, `request_id`, signatures, profile names, commands and relay bodies are never
  passed to `log_event`, not even as ids: it logs `id_prefix()` of every id keyword, which would
  still leak 8 characters, which app 030 SR-5 forbids.
- The audit table gets `push_retire` rows with a `device_id` prefix only.

### PN-OPS Operator surface

- `hermes hmp push status` (read-only, host terminal, separate process): enabled, relay configured
  (yes or no, never the URL's secrets), configured kid count, active registration count and
  non-REVOKED generation-row count read
  from the store. It reports no dispatch outcomes: they live only in the gateway's memory and fixed
  log events, and no persistent status snapshot is added. It touches neither `devices list` (SD3
  pending) nor key-length handling (SD5 pending).
- No CLI sends a push, grants push, or edits owner lists or controls decisions.

### PN-NC No change outside push

- With push off (the default), every existing route, gate, response and test outcome is unchanged.
- Send, jobs, model, AP-3 and AP-4 routes, gates and authority are unchanged. Minimum-version
  behavior is unchanged: later or unknown Hermes builds attempt the actual API, with no exact-build
  runtime gate.
- Push cleanup runs only after the cause's transaction has committed, in its own best-effort
  transaction, so it cannot change revoke, refresh-reuse, P4 or identity-change outcomes or make
  them fail (PN-REV). The schema-3 migration is additive and idempotent.
- Spec 034 behavior changes only through its own reviewed amendments (section 10), never from 014.

### PN-PLAT Platform truthfulness

- **Background OS delivery.** With the app backgrounded, suspended or not running, the OS displays
  the alert from the payload (APNs alert; FCM notification message). No app code or host fetch.
- **Foreground presentation.** On both platforms the app's own code decides presentation (iOS
  `willPresent`; FCM foreground handling). The app presents the same generic text, with no host
  fetch (G-OS). This is app work, not a relay or host property.
- **Force-quit and force-stop.** Delivery after an iOS app-switcher force-quit, an Android recents
  swipe, an Android settings force stop, or before first unlock is not established by the evidence
  read (`EVIDENCE_GAP`/`PLATFORM_GAP`). It is measured on device and reported as observed.
- **Settings prevail.** Permission, Time Sensitive, Focus, channel importance and battery settings
  are the user's. The app keeps no registration while notifications are not allowed (PN-APP-1).
- **Watch.** iOS may mirror an iPhone alert to a paired Apple Watch as OS behavior: generic text,
  no 014 actions; measured as observed. A standalone (Family Setup) watch is **not supported**. Any
  future watch design needs its own pairing, device identity and registration, and must not assume
  the watch can reach the tailnet at tap (`EVIDENCE_GAP`).

### PN-APP App obligations (consumed by app spec 030 S2/S3; listed here so the contract is complete)

- **PN-APP-1** The app does not `PUT`, and `DELETE`s an existing registration, while notification
  permission is denied, the Android approval channel is blocked, or iOS authorization is denied. It
  re-checks on resume. FCM deprioritizes high-priority messages to apps whose notifications are
  disabled.
- **PN-APP-2** The app persists the exact `PUT` body bytes (including the randomized `sealed`) with
  the intent, so a lost-acknowledgement retry is byte-identical. A re-sealed body is a new intent.
  The persisted body is stored encrypted, like the route table (G-PERSIST), and is deleted when the
  intent commits or is abandoned.
- **PN-APP-3** Removal is a persisted, encrypted, pending delete intent. When the app must stop
  alerts (unpair, notifications turned off, PN-APP-1) it persists the intent and sends `DELETE`. It
  retries on resume (`GET`, then a new CAS after `409 stale`) until a `200`, until the pairing is
  revoked or removed (then moot), or until the intent is abandoned, and it deletes the intent on
  `200` or abandon. The UI never says alerts stopped, and never shows "alerts off" as established,
  before a `200`; until then it says removal is pending. Background display cannot be suppressed by
  app code on either platform, so alerts may continue until a retry succeeds, a revoke happens or
  the seal's `not_after` passes (analysis A12).

## Security requirements (SECURITY.md "Notifications", constitution I to VI)

- **PN-SEC-1 Hint, not authority.** No payload field selects an instance, profile, request, answer
  or pairing. Route lookup is local to the app (030 SR-2). The resolver returns a profile locator
  only. Answers still need a fresh AP-3 read and a human choice (spec 008 FR-8, 030 T106).
- **PN-SEC-2 Recipient authority and visibility.** Effective approval owner AND bot grant AND the
  row's own live family AND visible now (I-6), at dispatch and at resolve, read live. Jobs/model
  `GRANT`, shared `user_id` and pairing alone confer nothing. A prompt Desktop holds is neither
  alerted nor located.
- **PN-SEC-3 No redirect by wire content.** The relay URL, audience, pins and kid list come only
  from host configuration. Sealed contents cannot steer HMP; HMP cannot read them.
- **PN-SEC-4 Exact-generation fencing** on every async edge: dispatch re-check, feedback CAS,
  resolve. No cross-instance fallback, automatic switch or answer.
- **PN-SEC-5 Custody.** Provider credentials only in the relay. HMP holds no provider token. The
  phone's raw address leaves it only inside a seal. No secret in logs, the audit table, CLI output,
  issue drafts or test fixtures.
- **PN-SEC-6 Bounded everywhere.** Every queue, map, table, retry, body and response has an
  explicit cardinality or size bound and an overflow rule (PN-BND, plan §6.5).
- **PN-SEC-7 Fail closed.** Unknown, stale, expired, hidden, gated, rate-limited, unauthenticated or
  malformed means no dispatch, a `404` resolve, or unable-to-check in the app. It never means
  `not_pending` or `located`.

## Section 9. What counts as done

| Claim | Needs |
| --- | --- |
| HMP contract implemented | unit and negative tests at the real route; store migration tests; fake relay |
| Relay implemented | unit tests; signature, seal and replay negatives; provider sandbox runs after owner authorization |
| Delivery | physical iPhone and Android evidence for the end-state matrix (plan §8) on an owner-authorized signed build |
| Feature complete | all of the above plus independent security review at feature freeze |

## Section 10. Inputs required from the approval lane (spec 034 or its successor)

The dispatcher and resolver consume, and must not reimplement:

- **I-1** A non-throwing, non-blocking `approval_row_inserted(key, surface, prompt_generation,
  expires_at)` notification, fired once after `PromptStore.put` actually inserts an approval row,
  outside the store lock, never from a closed or Phone-closed generation. Its contract names the
  calling thread: the Bot Chat stream path on the listener loop, and the `AdapterHooks` path as
  awaited by the gateway. 014 hands off with `put_nowait` or `call_soon_threadsafe` (PN-DSP-2).
- **I-2** A `settle_cause` on settled rows. It is authoritative only for: answer applied (native
  `resolved > 0`); native `409 approval_not_pending`/`approval_not_active` or
  `404 run_not_found`; Phone listing omission by `list_gateway_approvals`. Purge or local expiry,
  generation close, the binding fence, `expire_run` and unknown are non-authoritative. Root decides
  whether run completion counts (`⟨D4⟩`).
- **I-3** Read access to a row by key in the current generation, and the generation's
  `closed`/`phone_closed` state.
- **I-4** The live predicates `is_approval_owner_device`, `approval_surface_available`,
  `direct_send_effective` and the surface gate, with their 034 semantics.
- **I-5** On generation close: cancel the dispatcher and discard hints and slots.
- **I-6** `row_visible_now(row, now)`: exactly AP-3's predicate, evaluated now: status open, not
  locally expired (the 034 `purge(now)` rule: a row past `expires_at + EXPIRY_GRACE_S` is no longer
  open), the surface member available, and `bot_chat` rows hidden while
  `desktop_held(iid, user, profile)`; plus a way to evaluate the hidden part (held or member closed)
  for a settled row, also evaluated now. Root chose current visibility: no sticky hidden bit and no
  extra history observer, so a row that was hidden earlier and is visible now is answered by its
  current state (PN-RES-2). **AP-3 itself must call this same seam**, so dispatch, resolve and the
  Approvals list cannot diverge. That is a behavior-preserving refactor of AP-3 inside the I-6
  amendment, proven by an equivalence test (the same visible set as the old code over held, closed,
  expired and Phone cases). "AP-3 unchanged" therefore holds for behavior, not for code. The seam
  does not reconcile Phone rows through `list_gateway_approvals` as AP-3's listing does
  (PN-RES-4); the withdrawn-Phone-row residual is recorded (analysis A20).

The historical base `150bd0f` lacked I-1, I-2 and I-6. Spec 015 now supplies those
inputs with independent focused security review and final root source acceptance at
[`6a139ba`](https://github.com/MahdiHedhli/hermes-hmp/commit/6a139bae6646eb6e7584336c94ef611609833fe3) (PR #76).
I-1 is `PromptStore.set_insertion_observer` and `ApprovalInserted`; I-2 is the closed cause
sets and guarded settlement writers; I-6 is `view_row`/`view_visible` plus
`ServerContext.approval_members_now`, used by AP-3 itself. Root passed 482 focused source cases
(three unconfigured native-probe skips) and 2,004 complete source cases (16 explained skips).
The final test-only repairs preserve the reviewed production hashes and frozen AP-3 oracle.

I-3 is confirmed in `PromptStore.get`, the new immutable `view_row`, and the generation's
`closed`/`phone_closed` flags. Consumers must use `open_now` and `visible_now`, not `status`
alone: a view can retain status `open` while already past the grace boundary. I-4 is confirmed
in the existing owner, surface, direct-send and availability predicates in `request_ctx.py`;
015 changes none of their authority. I-5's lifecycle boundary is confirmed in
`adapter._close_generation`, reached by listener close and disconnect. Its dispatcher
cancellation, hint and slot cleanup are still **014 implementation work**, not behavior
provided by 015. No dispatcher or production observer registration exists yet.

This closes T003's source prerequisite. It does not merge or wire 014, prove native behavior
of the amended candidate, or supply provider infrastructure. The base's two native samples
cover `150bd0f`, not 015. Implementation must integrate the accepted inputs and pass its own
review and runtime gates before dispatch becomes available.

## Section 11. Inputs this provides to app spec 030 (S2/S3)

- The `PairingGenerationSource` mapping is unchanged. The accepted 030 S1 resolver port is
  unchanged; S1 is not reopened.
- **Registrar wiring.** `beginRegistration` before `PUT`. One `request_id` and one persisted,
  encrypted body per intent (PN-APP-2). Commit with the returned `route`. A lost acknowledgement is
  retried with the same bytes, which returns the same `route` (030 FR-6). `409 stale` and
  `503 retry_state_lost` both mean read status, then begin a new intent. So does a `400` or
  `503 write_gate_closed` answer to a replay after the kid list or push availability changed:
  `GET`, then a new intent. `503 write_gate_closed` (including `push_capacity`) and `503 other`
  mean this attempt did not commit and registration is not confirmed. After an earlier lost
  acknowledgement they do not prove that an older row is absent: the app keeps its exact local
  begin and close of old handles, then recovers by `GET`, and gains no new authority.
  `409 idempotency_conflict` is a client defect.
- **`DELETE` mapping.** `200` means removed, and only a `200` is confirmation. `409 stale` means
  `GET`, then retry with the new generation. `503 other` (including a store write failure),
  `503 write_gate_closed` (including `push_capacity`) and `429` mean **not confirmed**: keep the
  pending delete intent and retry on resume (PN-APP-3). `404` means the device is not an effective
  approval owner now: no alert is dispatched while that holds, but removal is not confirmed. `401`
  means the pairing itself is gone and the intent is moot. The UI never says alerts stopped before
  a `200`.
- **Resolver adapter mapping.** The adapter receives `HintResolveRequest{iid, epoch, hintRef}` and
  sends `{"v": 1, "hint": hintRef}` over the connection bound to `(iid, epoch)`. `200 located` →
  `HintLocated(profile)`. `200 not_pending` → `HintNotPending`, which is a definitive authoritative
  negative (RD-19). `429` → `rateLimited`. `503 write_gate_closed` → `gateClosed`. Network or
  timeout → `network`. Every other status, including every `404`, → `other` (unable to check). A
  `404` is never `notPending`. Feature presence comes from `GET /push/registration` (PN-REG-1), not
  from resolver statuses.
- **Native input.** iOS `userInfo["hmp"]` and Android data `hmp_v`/`hmp_route`/`hmp_hint` become
  the 030 map `{v: 1, route, hint}`. `hmp_v` must be exactly `"1"`; anything else is not converted.
  Size and nesting are bounded before parsing (G-NATIVE-INPUT). The FP rules are unchanged. The
  route stays a local lookup key (R → iid) and is never sent to the resolver.
- **Persistence.** The route table, meaning `iid`, `R`, the intent's generation and `G`, must be
  encrypted and hydrated before a cold-start tap is handed off (G-PERSIST).
- **Permission state.** PN-APP-1.
- **Shapes.** `R` and `K` are 43 characters, inside 030's 22 to 64 bounds. 030 FP-4 is unchanged.

## Gaps by owner

| Gap | Kind | Owner |
| --- | --- | --- |
| 014 dispatches only for rows the 034 lane inserts (Bot Chat streams HMP started, HMP Phone chat). Approvals raised on Desktop, CLI, cron or other platforms are not covered. Whether Hermes offers or lacks a plugin-visible, profile-scoped multi-subscriber approval observer is unresearched for the target builds. Upgrade to `HERMES_API_GAP` only after a cited exact-commit source trace following the skill's refresh procedure. | `EVIDENCE_GAP` (research pending) | Project, then Nous if confirmed |
| No stream settlement or expiry event (034 G4). A located prompt may already be settled elsewhere and is discovered at answer (`409`). | `HERMES_API_GAP` (as recorded by 034) | Nous |
| No session-stream approval capability flag; `ExecApprovalPrompt` lacks a request ID (034 G1, G3) | `HERMES_API_GAP` (as recorded by 034) | Nous |
| I-1, I-2 and I-6 source accepted by 015 at `6a139ba`; integration and 014 runtime consumers remain unwired | Implementation and runtime verification | HMP (014 lane) |
| Instance-level pending-approval summary, so prompts of other bots without their own alert are discoverable without a roster scan | `UX_CONTRACT_GAP` / `HMP_CONTRACT_GAP` | App and HMP |
| Registration, issuer, resolver, dispatcher, post-commit cleanup, store, purge, CLI | `HMP_CONTRACT_GAP` (this spec) | HMP |
| Relay service, HPKE keys, rate limits, deployment | Our infrastructure | Project and owner |
| APNs key, Firebase project, App ID capabilities, store privacy answers | Provider and account | Owner |
| APNs registration, FCM SDK, channel, permission, Time Sensitive entitlement, foreground presentation, native input, encrypted route persistence, sealing, PN-APP-1/2 | App, native, OS (`PLATFORM_GAP`) | App |
| Physical delivery, Doze, Focus, force-quit and force-stop, rotation | `PLATFORM_GAP` | Owner devices |

## Out of scope

Clarification, chat, job, model or settlement notifications; lock-screen actions; Critical Alerts;
full-screen intents; Apple Watch features. OS mirroring of iPhone alerts to a paired watch is OS
behavior, measured only as observed. A standalone (Family Setup) watch is not supported; a future
watch design needs its own pairing, device identity and registration. Also out of scope: website,
store listing or beta-track changes; provisioning any account, key, domain or billing; changing
`owner_device_ids`, controls decisions, SD3 or SD5; any change to spec 034 except through its own
reviewed amendments; and any Hermes core change.

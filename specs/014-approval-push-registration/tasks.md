# Tasks: approval push registration, issuance, hint resolution and relay delivery


**Current contract review status (2026-10-02):** The clock mechanism, optional pin grammar and N3–N6 were accepted by the prior focused review. The independent D1/D2/D3 sentence review accepted the capacity/retention qualifications, per-`(app, env)` APNs connections and seal-expiry wording. Root resolved its remaining editorial status finding M1 by dating the pre-review statements below. This is contract-text acceptance only. Source, causal tests/vectors, interoperability, provider/device/deployment/release and owner choices O1–O6 remain pending. No task checkbox or security mechanism changed.

Root has frozen `ROOT_DECISIONS.md` after the focused closure review. Implementation remains
blocked on the subsequent contract tasks. The approval-lane source prerequisite T003 is now accepted; no runtime is wired. Tasks are dependency-ordered. Work in parallel only
after T001–T004 freeze the shared contract. Workers do not tick review boxes. The **root
interoperability amendment of 2026-10-02** (`ROOT_DECISIONS.md`, decisions B1–B6 and P1–P3) adds the
conformance obligations marked "(amendment)" below to T010, T012, T022, T025, T030, T031, T040 and T043.
It ticks no box, claims no acceptance, and leaves the contract text under independent review. The **root
review clarifications of 2026-10-02** (`ROOT_DECISIONS.md`, F1–F7) add the conformance obligations marked
"(clarification)" to T020, T022, T025, T030 and T031; a scoped independent review of an earlier candidate
accepted that candidate with conditions; a later independent review accepted the clarified text's other clauses and
required the relay clock and optional pin source gates. The **root clock and pin delta of 2026-10-02**
(`ROOT_DECISIONS.md`, R-F1a, R-PIN, N3–N6) writes those gates and adds the obligations marked "(clock/pin delta)"
to T020, T022, T025, T030 and T031. Before its focused review, it was new and **unreviewed**: the gates are written, not accepted, a focused
independent sentence review is pending, and it ticks no box and claims no source, vector, device or provider
evidence. The clock-count repair of 2026-10-02 followed a focused review of that delta: the review accepted the mechanism, the pins and N3 to N6, and required text repairs for the 4,800-nonce and 240 s qualification under clock steps (its finding D1) and for one APNs connection granularity per allowed `(app, env)` pair (D2), with editorial wording (D3). At that checkpoint, the repaired capacity and connection sentences awaited a focused check of those sentences only. That check has now accepted D1/D2/D3 as contract text; implementation and verification remain pending. Gap markers:
`HMP_CONTRACT_GAP`, `HERMES_API_GAP`, `PLATFORM_GAP`, `EVIDENCE_GAP`, `UX_CONTRACT_GAP`,
`SECURITY_REVIEW_REQUIRED`.

## Phase 0: freeze (root)

- [x] T001 Independent design review of spec, plan, analysis and root decisions (FRONTIER, not the
  author), then a focused independent delta review of the amendment. Both ran, and their findings
  (B1–B4, N1–N23, C1–C8) became bounded edits to these files. Root checks the final text against
  C1–C8, with a targeted independent check of C1–C3 only if an actual remaining risk is found.
  Root closes design review on 2026-10-02 after the focused C1–C3 acceptance and mechanical precision fixes.
- [x] T002 Root freezes D1–D28 (D21 unused) and records the frozen values in `ROOT_DECISIONS.md`.
- [x] T003 **Approval-lane source prerequisite.** Spec 015 `6a139ba` supplies I-1, I-2 and I-6
  with independent focused review and final root source verification. Section 10 records the
  exact interfaces, immutable visibility flags and source-test limits. I-3/I-4 and the I-5
  generation-close lifecycle boundary are confirmed. Dispatcher cancellation and hint/slot
  cleanup remain future 014 work. No native, push, device or deployment acceptance is implied.
- [ ] T004 Owner chooses O1–O6 (all pending). Nothing is provisioned by this task.
- [ ] T005 Cross-channel coverage research (`EVIDENCE_GAP`): run the Hermes Developer skill refresh
  procedure, then trace the approval notification path on the exact target commits (Desktop TUI
  RPC, CLI prompts, cron, gateway platforms). File a `HERMES_API_GAP` only from that cited trace.

## Phase 1: contract text (single worker, after T002 and T003)

- [ ] T010 Add HMP v1 §7f (PN-REG, PN-ISS, PN-RES, PN-BND) with schemas, gate order, status table and
  constants. Add the four `why` values (`push_disabled`, `relay_unconfigured`,
  `approvals_unavailable`, `push_capacity`) to the closed `OtherWhy` set, each allowed only on
  `503 write_gate_closed`; no new error extra (the `generation` extra is dropped) and no new error
  code; push uses the generic fixed messages and the app ignores message text. Add §14 residuals
  (leaked-token spam, sybil suppression A14, public global and verify exhaustion A17, unrevocable
  seals until `not_after`, best-effort delivery, located-but-settled-elsewhere including a withdrawn
  Phone row, lost idempotency history, replay after a consistent restore A19, `DELETE` write failure
  and the delayed-`PUT` race, idle-slot eviction A22). Docs only. (Amendment) The same section carries
  `DELETE` independent of delivery availability (B5), the `sealed` range 82–1,105 decoded bytes (B3),
  the `kid`/`aud` grammars (B4), raw-byte `R`, `K`, `C` in the relay signature (B1), and residuals
  RES-26 (relay restart replay window) and RES-27 (provider refusals retire nothing).
  (Clarification) The same section carries the F2 availability, `why` precedence, kid-liveness and `PUT`
  order text and qualifies the gap labels (F3). A scoped independent review of an earlier candidate
  accepted it with conditions; the clarified text is pending review. No box is ticked.
- [ ] T011 Amend the constitution and the closed-surface note: one sanctioned outbound
  non-loopback client whose destination comes only from host configuration.
- [ ] T012 Write the relay contract (PN-REL, PN-SEAL, plan §6.5 bounds) as a standalone document for
  the relay repository, including the audience, `addr_kind`, the closed result set with
  `unavailable` versus `provider_unavailable`, HPKE parameters (D1) and the pinned RFC 9180 vector
  reference. (Amendment) The relay document now also fixes the transcript bytes (B1), the JCS plaintext
  (B2), the `enc ‖ ct` framing (B3), the identifier grammars and the fixed `hmp_approval_v1` channel
  and collapse key (B4), the result-code map (B6), and the atomic admission and nonce order (P1, P2).
  HMP-specific vectors are not part of this task; they are implementation follow-up (T025, T030, T043).
  (Clarification) The relay document also carries F1 (atomic skew re-check), F4 (strict DER signature),
  F5 (APNs environment per allowed `(app, env)` pair) and F6 (rolling 3,600-second post-seal counters).
  A scoped independent review of an earlier candidate accepted it with conditions; a later review accepted the
  clarified text's other clauses and required the clock and pin gates, written at that time as the unreviewed clock/pin
  delta (R-F1a, R-PIN). No box is ticked.

## Phase 2: HMP server (after T010/T011; GENERAL tier; unit and route tests only)

- [ ] T020 Store schema 3 and migration from schema 1 and 2 (additive, idempotent). Post-commit
  cleanup (a separate best-effort `Store.transaction()` after the cause commits; never a push
  statement or savepoint inside `revoke_all_for_identity_change`, `_revoke_in`, the reuse-revoke
  transaction or the P4 re-issue transaction). Push purge step (listener open and hourly). A guard in
  `Store.set_device_state` that refuses to change a REVOKED device. Tests: migration idempotence;
  a real `SQLITE_FULL` (for example `max_page_count`) injected into the post-commit cleanup leaves
  each cause's committed outcome and store rows unchanged, regardless of the exception code or
  text. Cleanup runs only at PN-REV's named post-commit call sites; a bounded-timeout test detects a
  nested call inside `_revoke_in`. The purge later retires the
  leftovers; a test that `set_device_state` cannot revive REVOKED; the REVOKED purge deletes the
  generation and registration rows only with that guard; every exit from `active` advances `G` once
  per transaction and wipes secret columns; `G` never decreases for a non-REVOKED device and its
  generation row is never purged while the device is not REVOKED; an active row always has a generation row; the D28 cap; `G` at
  2^53 refuses `503 other`; `expires_at` equals `seal_expires_at`; the purge expires active rows that
  are past expiry, kid-removed (while push is available) or hash-mismatched (only the hash mismatch needs a successful
  `k_grace` read) and frees D24 capacity; with an unreadable `k_grace`, an expired row and a
  removed-kid row are still expired and free capacity while push is available, and a valid unexpired
  live-kid row stays active (that row is unchanged and no secret-file bytes are written);
  (clarification, F2; clock/pin delta, N4, N5) while push is off for each reason (`push_disabled`,
  `relay_unconfigured` including one malformed kid among valid ones, an empty kid list or a malformed configured
  `push.relay_spki_pins`, `approvals_unavailable`) the purge expires no row for kid liveness and keeps
  otherwise valid active rows inert (still counted against D24 as active rows, not against D25), while past-`expires_at`, revocation, family, hash and retained-row steps
  still run, and kid-removal expiry resumes when push is available again; one active row per device; UNIQUE `route_hash`; retained caps enforced only
  in `PUT` and purge; purge retires rows
  of non-active devices or revoked families.
- [ ] T021 Issuer: `R` derivation (`HMP1-PUSH-ROUTE` with salt), re-derivation with hash check, `C`
  derivation, and the new read-only `k_grace` accessor (PN-ISS-5). Tests: a distinct `R` for every
  change of `iid`, `H`, `device_id`, `family_id`, `G`, salt; re-derivation returns the identical
  `R`; a re-created `k_grace` makes the hash check fail; nothing in the store alone derives `R`;
  prefix-freeness over all tags; the accessor never creates, rewrites or deletes the file when it is
  missing, unreadable, wrong-length or fails transiently; it never changes file mode, including
  after a successful read; existing callers are unchanged.
- [ ] T022 `GET/PUT/DELETE /push/registration` with the PN-REG gate order. Negative tests at the
  real route: non-owner and host-denied owner `404` with no store read beyond auth; wrong instance;
  revoked, including a revoke between auth and the write transaction before replay or CAS
  (`401 revoked`, no registration/generation writes); bad shape and size; kid not configured (`400` while push is available); `addr_kind`/`env`/platform mismatch; seal
  expiry out of range (max 14 d); push unavailable `503` with the closed `why`; CAS stale;
  idempotent replay after a newer `G` (same response); same `request_id` with a different body
  (`409 idempotency_conflict`); replay with a different bearer family (`409 stale`); replay after
  `k_grace` deletion (`503 retry_state_lost`, row and `G` unchanged); replay after the retired row
  was evicted (`409 stale`, never `200`); forced `route_hash` collision (`503 other`, `G`
  unchanged); capacity full (`503 push_capacity`; replacement and `DELETE` succeed); an injected
  store write failure on `DELETE` (`503 other`; the delete fence stops dispatch and resolve at once;
  a later successful `DELETE` clears the fence entry); DELETE CAS
  blocks a late older PUT; `GET` reports `expired` for kid removal (while push is available), family mismatch, route state
  loss and an unreadable `k_grace`; `GET` reports a fenced row as not active and applies the
  latest-row rules; the error envelope uses only allowed extras and the closed `why` values (no
  `generation` extra on `409 stale`); first `PUT` and no-generation `DELETE` at the D28 cap refuse
  `503 push_capacity` with nothing written, while `DELETE` of an existing registration never does;
  a replay after push became unavailable gets `503`, and one after kid removal while push is available gets `400`, before the replay check;
  the consistent-restore replay outcome is documented (A19); the bucket refuses with no change.
  (Amendment) `DELETE` answers `200` with the same CAS and `G` rules while push is disabled, the relay
  is unset, the kid was removed, approval members are closed and direct send is off, makes no Hermes,
  relay, provider or `k_grace` call, and still answers `404` for a non-owner, `401 revoked` after a revoke
  between authentication and the write, `409 stale` on a CAS miss and `429` over the bucket; `GET` stays
  readable (`available: false`) in those states; `PUT` accepts `sealed` of 82 and 1,105 decoded bytes and
  refuses 81, 1,106, padded and non-canonical b64u (`400`); the kid and audience grammars at their length
  bounds and one over, a leading `.` or `-`, non-ASCII, whitespace and case differences.
  (Clarification, F2) The `why` precedence (`push_disabled`, then `relay_unconfigured`, then
  `approvals_unavailable`) for `GET` and `PUT`; one malformed kid among valid ones, an explicitly empty kid list,
  or a malformed configured `push.relay_spki_pins` is `relay_unconfigured`, never an
  empty live list. (Clock/pin delta, R-PIN) `push.relay_spki_pins` omitted is allowed (no optional pin); explicit
  `None`, an empty list, a non-list, a duplicate, a non-string, a padded, wrong-length, non-canonical or
  non-base64url entry and more than 8 entries are each `relay_unconfigured`, while exactly 1 and exactly 8
  distinct canonical 43-character digests (decoding to 32 bytes and re-encoding identically) are accepted; there
  is no environment-variable fallback and no setting is read from the wire (tests pending); `GET` omits `relay_kids` unless `available`; `GET` does not report `expired` for kid removal
  while push is off; `PUT` order: body grammar and size failures (including a lexically malformed kid) are `400`
  independent of availability, then availability `503`, then live-kid membership `400`, then replay and CAS, so a
  removed well-formed kid is `503` while off and `400` while available; `DELETE` stays independent (B5).
- [ ] T023 `POST /push/hints/resolve` (PN-RES) with body `{v, hint}`. Negative tests: a body with
  `route` or extra keys (`400`); no current registration for the bearer device; hint bound to a
  retired, foreign-device, foreign-family, other-instance, old-`H` or old-`G` registration; hint
  bound to an old prompt generation, a Phone-closed generation, an evicted entry; Desktop held at
  resolve (`404`, never `not_pending`, open or settled); bot grant lost (`404`, ERR-3 detail
  masked); gate closed (`503`); `not_pending` only for the D4 authoritative causes, `404` for each
  non-authoritative cause; a row hidden earlier, settled authoritatively and visible now follows the
  chosen current-visibility semantics (`not_pending` is allowed); a locally expired but unpurged row
  gives `404`; a fenced row gives `404`; the response carries nothing beyond `state` and `profile`; no mutation.
- [ ] T024 Dispatcher with a fake relay and fake clock (PN-DSP, PN-BND). Tests: clarify never
  dispatches; closed generation; Desktop held between enqueue and send (no request) and no later
  re-dispatch; expired TTL dropped at dequeue; recheck failure at send; recipients exactly owner AND
  grant AND the row's own live family within absolute TTL AND current registration AND kid live;
  cap D13; coalescing trailing send carries the newest `K`; slot table full; hourly cap; counters keyed
  by `device_id` survive re-registration and never evict a live counter; idle-slot eviction never
  exceeds the hourly cap; `k_grace` access is off the event loop; hint lifetime follows the row and the hard maximum; hint map
  eviction order; TTL clamp; retry only for pre-write connect failures and relay `unavailable`,
  only within TTL, with fresh `ts`/`nonce`; no retry after a post-write timeout or
  `provider_unavailable`; breaker opens and drops without waiting; feedback CAS against a newer
  registration; enqueue from another thread uses `call_soon_threadsafe`; queue full drops the new
  event without blocking the producer; producer exception isolation; dispatcher creation failure
  leaves listener open and existing routes unaffected; listener close cancels in-flight requests
  within the D8 bound while the relay hangs.
- [ ] T025 Relay client (`push_relay.py`). Tests against local fake HTTPS servers: redirects
  refused; proxy environment ignored; oversize, slow, malformed and unknown result treated as
  ambiguous; TLS failure; pre-write connect failure versus post-write timeout; (clock/pin delta, R-PIN) the
  standard trust-store chain and host-name validation are always required, a configured pin additionally
  constrains the **leaf** SPKI digest only and never replaces a trust anchor, a self-signed certificate with a
  matching pin, an issuing-certificate-only match and a leaf mismatch all fail before any request byte, and that
  failure is retried only under the bounded RES-C pre-write rule with no trust fallback (tests pending); signature transcript
  vectors including `aud`, `platform`, `addr_kind` and `env`; no relay text in logs. (Amendment) The
  transcript uses raw 32-byte `R` and `K`, raw 24-byte `C` and the `iid` derived from the supplied SPKI;
  signature vectors come from an independent generator and are independently reviewed; a result of
  `502`, `401`, `400`, `409`, `429` or `503` retires no registration; no provider text is logged.
  (Clarification, F4) The signature header is a strict minimal DER `SEQUENCE` of two positive `INTEGER`s in `1` to
  `n − 1`; the client's test vectors, from an independent generator and pending, cover that encoding and both
  low-S and high-S validity; no homemade signing or verification.
- [x] T026 `hermes hmp push status`, read-only, active registrations and non-REVOKED generation-row
  counts only. Tests: no identifiers, URL
  secrets or handles in output; no dispatch outcome field; no change to `devices list` (SD3) or key
  handling (SD5).
  Implementation checkpoint: configuration projection and schema-3 read-only counters are in
  the focused `feat/push-status-readonly` slice. Missing optional configuration APIs or unreadable
  store state report unavailable; no exact-build admission gate is added. Independent v3 source
  review accepted the bounded slice after fixing nonregular file reads. Local full regression:
  2,591 passed, 16 skipped, one existing warning; eight isolated native configuration cases match.
  Hosted CI, relay interoperability, registration and notification delivery remain separate gates.
- [ ] T027 Log and privacy canaries: `R`, `K`, `C`, `S`, salt, `request_id`, signatures and profile
  names never reach `log_event`, the audit table, CLI output or issue drafts. Run `scan_logs.py`,
  `scan_private.py`, `check_plugin_surface.py` (with the T011 rule) and Ruff. Existing route suites
  pass unchanged with push off (PN-NC).
- [ ] T028 Mutation pass: remove each fence (owner, grant, row family, `H`, `G`, generation,
  visibility/held, CAS, replay hash check, feedback CAS, kid check at `PUT` and at dispatch, TTL
  bound, capacity, D28 cap, cleanup never inside the cause transaction, REVOKED terminal-state guard,
  transactional ACTIVE/family re-check before replay/CAS, pre-provider-only retry) and record the named test that
  fails.
- [ ] T029 Isolated fixture (no live home): an approval lane plus a local fake relay on an isolated
  Hermes build. Approval → signed request; revoke between enqueue and send produces no request;
  Desktop held between enqueue and send produces no request; restart drops the queue and hints.
  Sample evidence, not a gate on future builds.
  Focused branch checkpoint: implement the bounded verified-TLS fake receiver and production-client
  seam first. Component tests do not complete this task. Native-origin and positively synchronized
  interleaves, independent review and sampled runtime receipts remain required.

## Phase 3: relay (separate repository; after T012)

- [ ] T030 Verifier, HPKE opener, binding checks, fixed templates, limiter, replay cache, optional
  `iid` allowlist. Unit tests with RFC 9180 vectors and negatives (signature, audience, skew,
  replay with nonce retention to `ts + skew`, full replay cache refuses, kid, iid mismatch, app,
  env, expiry beyond 14 d, platform, `addr_kind`, oversize). Every table follows plan §6.5.
  Per-key caps run before the global count and only admitted requests charge it; verify-budget
  exhaustion gives `429` with no provider call; a two-`iid` destination-ceiling test documents the
  A14 residual; under normal clock progress (clock-step tests excluded) the replay cache stays within 4,800 live nonces at the verify budget; FCM requests
  carry no `env`. Address-free logs with no `iid` prefix. (Amendment) The relay negatives and codes of
  `HMP_PUSH_RELAY_V1.md` §14: `400` before any provider work (malformed SPKI, signature encoding,
  identifier, `ttl_s` 59 and 901, `ts` negative or 2^53, `sealed` length 81 and 1,106), `401` for a
  wrong signature, audience, `ts` (including `now = ts + 120`), unknown kid and allowlist miss, `422`
  for a bad point, tag, plaintext, JCS form or binding; two concurrent identical requests never both
  dispatch; the nonce stays reserved after a later refusal and is purged at `expiry ≤ now`; at most 20
  verify checks in any rolling second with no burst; the pre-verification pair charges both or neither
  and keeps the charge when a later check fails; the four counters (rolling 3,600-second windows, F6) charge only when all admit;
  a relay restart empties the replay cache (documented residual RES-26). HMP-specific JCS and seal
  vectors come from an independent generator and review, not from this document.
  (Clarification) F1: the atomic section reads one current `now`, re-checks both skew inequalities and purges,
  checks and reserves with that instant; concurrent and boundary tests, including a request that passes the early
  screen before `ts + 120` and reaches the atomic section after it (`401`, no reservation, no provider call) and one
  whose nonce another worker purged. F4: strict DER and range cases (`400`), valid non-verifying (`401`), low-S
  and high-S verify, vectors pending. F5: environment pairs, no fallback, `iid` allowlist `401` versus seal
  binding `422`. F6: rolling 3,600-second post-seal counters with boundary tests, no new cap value.
  (Clock/pin delta, R-F1a) The atomic section computes one effective acceptance instant
  `max(raw wall now, last_now)`, stores it in memory only, and uses it for the re-check, purge, seen check,
  capacity and reserve and for the step 14 seal expiry (step 6 may use the raw clock); the rolling windows of
  steps 2 and 16, including the per-source 600 per rolling 3,600 s, use monotonic elapsed time. Causal tests
  and vectors (**pending; none exists**): a backward wall-clock step after a purge leaves the replayed request
  `401` with no reservation and no provider call; a forward step across `ts + 120` refuses `401` until the
  clock catches up, with no automatic restart or reserve reset; step 14 never uses a later raw reading; the
  counters neither double-count nor un-count across backward and forward steps; a cold restart resets `last_now`
  and the cache together; retained capacity under repeated backward steps (the 240 s retention and 4,800 live bound hold only
  under normal clock progress; the live count may exceed 4,800 and no exact bound is promised) and a full cache under
  repeated steps (`503`, nothing evicted, no early release, no replay accepted). While `last_now` is ahead of the raw clock
  the raw and effective screens may `401` until catch-up, with no automatic restart or reset. No nonce persistence or
  restart immunity is claimed.
- [ ] T031 APNs sender (HTTP/2, ES256 provider token refresh 20–60 min, priority 10, alert type,
  expiration, collapse ID, Time Sensitive key) and FCM v1 sender (`token` or `fid` by `addr_kind`,
  HIGH, TTL, constant collapse key, channel, tag, restricted package, data keys). One provider
  attempt per request, no provider retry. Response mapping to the PN-REL-4 set, with
  `provider_unavailable` after any attempt, including provider throttling (APNs `TooManyRequests`,
  FCM `QUOTA_EXCEEDED`), never `429`. Tests against provider stubs. (Amendment) Every other provider
  refusal (`BadDeviceToken`, `DeviceTokenNotForTopic`, `Forbidden`, `PayloadTooLarge`, FCM topic, payload
  and permission refusals) is `502 provider_unavailable`, never retried; only APNs `Unregistered` or
  `ExpiredToken` and FCM `UNREGISTERED` are `410 provider_gone`; the FCM `channel_id` and the only
  `collapse_key` are the literal `hmp_approval_v1`. (Clarification, F5; clock/pin delta, N3) One provider connection
  per allowed APNs `(app, env)` pair; the selected pair decides the connection; no environment fallback.
  Credential and signing-key provisioning is pending owner choice O3 and is not decided or implemented here.
- [ ] T032 Deployment descriptor for the chosen platform (O1/O2), single replica (D27). No secrets in
  the repository or CI. Runbook for key rotation and incidents.
- [ ] T033 **Owner-gated.** Sandbox credentials and sends to owner test devices only.

## Phase 4: app (private repository; consumes spec §11; separate app specs and reviews)

- [ ] T040 030 S2 registrar wiring (T101 there) using `PUT/DELETE` CAS and idempotent retry with the
  persisted, encrypted body, deleted on commit or abandon (PN-APP-2); `503 retry_state_lost`, and a
  `400`/`503` answer to a replay after a configuration change, handled like `409 stale` (`GET`, then
  a new intent). `DELETE` mapping per spec §11 and a persisted, encrypted pending delete intent
  retried on resume (PN-APP-3); no "alerts off" copy before a `200`. (Amendment) The pending delete
  intent is retried whether or not push is available on the host (`DELETE` is not refused for that
  reason), and a `503 write_gate_closed` answer to it can only be `push_capacity`.
- [ ] T041 030 production resolver adapter (T103 there) with the §11 mapping: sends `{v, hint}`;
  every `404` → `other`; never `notPending` from a `404`. The S1 port is unchanged.
- [ ] T042 Native APNs registration (iOS) and FCM registration (Android), with the address kind. No
  token caching across launches beyond the current registration.
- [ ] T043 Sealing with the D1 suite and shipped kid list; the RFC vectors pass in Dart. (Amendment)
  The sealer emits RFC 8785 JCS plaintext in the restricted domain (B2) and `b64u(enc ‖ ct)` of 82 to
  1,105 decoded bytes (B3), uses a fresh CSPRNG ephemeral key for every production seal and a vetted
  HPKE implementation, and rejects a `kid` outside the grammar (B4). HMP-specific seal vectors come
  from an independent generator and review.
- [ ] T044 Encrypted route-table persistence and hydration before cold-start handoff (G-PERSIST).
- [ ] T045 Native input adapter with size, nesting and encoding bounds (G-NATIVE-INPUT).
- [ ] T046 Permission opt-in only after `available: true`; Android approval channel at high
  importance; iOS Time Sensitive capability; foreground presentation of the same generic text with
  no host fetch; `DELETE` or no `PUT` while permission, channel or authorization is off, re-checked
  on resume (PN-APP-1); copy and settings explainer, including that a host controls denial also
  silences push (`UX_CONTRACT_GAP`, G-UX).
- [ ] T047 Catch-up: after any approval tap, the Approvals flow does a fresh read and never treats
  alerts as a complete inbox. Another bot's pending prompt is found through normal navigation; the
  instance-level summary is a recorded gap, not a roster scan.

## Phase 5: operational acceptance (owner devices; owner-authorized signed builds)

- [ ] T050 **Owner-gated.** R2 relay (allowlist mode) with sandbox APNs and Android internal build:
  the full plan §8.4 matrix on one iPhone and one Android phone. Measured-only rows are reported as
  observed. Evidence stays private.
- [ ] T051 Nonreuse on device: re-pair, revoke, P4 re-issue, `rotate-key`, reinstall/restore and
  provider token change. Old `R` and `K` never resolve; new handles differ.
- [ ] T052 Burst, TTL, duplicate, relay-down and host-offline cases.
- [ ] T053 **Owner-gated.** R1 production relay only after the owner accepts the R1 residuals (A1, A6,
  A13, the restated A14 and A17),
  privacy declarations (O6), then the §8.4 matrix on the release candidate.

## Phase 6: review and release

- [ ] T060 Independent security review at feature freeze across HMP, relay and app diffs, against
  `checklists/security.md`. The reviewer ticks boxes.
- [ ] T061 Findings become bounded defect subgraphs with delta reviews.
- [ ] T062 Root verification of T028 mutants and T050–T053 evidence. Then the release decision.

## Explicitly not tasks here

No Hermes core change; no change to spec 034 except through its own reviewed amendments (T003); no
change to existing send, jobs, model, AP-3 or AP-4 authority; no Watch features; no clarification,
chat or job alerts; no website, store or beta change; no grant, controls or owner-list edits; no
SD3/SD5 edits.

## Source prerequisite checkpoint — 2026-10-02

T003 is closed by accepted spec 015 `6a139ba` (PR #76). Root checked the current store,
owner/surface predicates and adapter close call sites. The production delta is documentation only;
it does not import or wire the input implementation. The synthetic issue-draft fixture repair
keeps its runtime values unchanged and passed all 46 tests without privacy suppressions. T010–T012 are the next source-contract
work. T004 and all provisioning choices remain pending and do not prevent documentation work.
The 015 no-await adjacency invariant is source-read evidence only, not a killed test mutant.

## Interoperability amendment checkpoint — 2026-10-02

Root's interoperability direction (`ROOT_DECISIONS.md`, B1–B6 and P1–P3) is transcribed into HMP v1
§7f, the relay contract, `spec.md`, `plan.md` and the obligations above. It addresses the six former
relay-contract items (labels GAP-1 to GAP-6, removed; distinct from HMP v1's live `GAP-1` and `GAP-2`) and the former
GAP-PN-1 item. No box is ticked. T010–T012 stay unticked until the independent contract
review of the amended text. HMP-specific vectors are implementation follow-up, not blocked by a
contract gap. T004, T005, provisioning, runtime, device, provider and release evidence remain pending.

## Review clarification checkpoint — 2026-10-02

Root's review clarifications (`ROOT_DECISIONS.md`, F1–F7) are transcribed into HMP v1 §7f, the relay
contract, `spec.md`, `plan.md` and the obligations above. A scoped independent review of an earlier
eight-document candidate accepted it with conditions; the clarified candidate is a new text and awaits
its own independent review, which its author cannot certify. No box is ticked: T010–T012 stay unticked.
The F1, F4, F5 and F6 vectors and boundary tests are implementation follow-up (T025, T030, T031) and
do not exist. Runtime, source, interoperability, device, provider and release evidence remain pending.

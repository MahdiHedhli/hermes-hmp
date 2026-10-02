# Tasks: approval push registration, issuance, hint resolution and relay delivery

Root has frozen `ROOT_DECISIONS.md` after the focused closure review. Implementation remains
blocked on the subsequent contract tasks. The approval-lane source prerequisite T003 is now accepted; no runtime is wired. Tasks are dependency-ordered. Work in parallel only
after T001–T004 freeze the shared contract. Workers do not tick review boxes. Gap markers:
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
  and the delayed-`PUT` race, idle-slot eviction A22). Docs only.
- [ ] T011 Amend the constitution and the closed-surface note: one sanctioned outbound
  non-loopback client whose destination comes only from host configuration.
- [ ] T012 Write the relay contract (PN-REL, PN-SEAL, plan §6.5 bounds) as a standalone document for
  the relay repository, including the audience, `addr_kind`, the closed result set with
  `unavailable` versus `provider_unavailable`, HPKE parameters and test vectors (D1).

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
  are past expiry, kid-removed or hash-mismatched (only the hash mismatch needs a successful
  `k_grace` read) and frees D24 capacity; with an unreadable `k_grace`, an expired row and a
  removed-kid row are still expired and free capacity, and a valid unexpired live-kid row stays
  active (that row is unchanged and no secret-file bytes are written); one active row per device; UNIQUE `route_hash`; retained caps enforced only
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
  (`401 revoked`, no registration/generation writes); bad shape and size; kid not configured; `addr_kind`/`env`/platform mismatch; seal
  expiry out of range (max 14 d); push unavailable `503` with the closed `why`; CAS stale;
  idempotent replay after a newer `G` (same response); same `request_id` with a different body
  (`409 idempotency_conflict`); replay with a different bearer family (`409 stale`); replay after
  `k_grace` deletion (`503 retry_state_lost`, row and `G` unchanged); replay after the retired row
  was evicted (`409 stale`, never `200`); forced `route_hash` collision (`503 other`, `G`
  unchanged); capacity full (`503 push_capacity`; replacement and `DELETE` succeed); an injected
  store write failure on `DELETE` (`503 other`; the delete fence stops dispatch and resolve at once;
  a later successful `DELETE` clears the fence entry); DELETE CAS
  blocks a late older PUT; `GET` reports `expired` for kid removal, family mismatch, route state
  loss and an unreadable `k_grace`; `GET` reports a fenced row as not active and applies the
  latest-row rules; the error envelope uses only allowed extras and the closed `why` values (no
  `generation` extra on `409 stale`); first `PUT` and no-generation `DELETE` at the D28 cap refuse
  `503 push_capacity` with nothing written, while `DELETE` of an existing registration never does;
  a replay after kid removal or push becoming unavailable gets `400`/`503` before the replay check;
  the consistent-restore replay outcome is documented (A19); the bucket refuses with no change.
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
  ambiguous; TLS failure; pre-write connect failure versus post-write timeout; signature transcript
  vectors including `aud`, `platform`, `addr_kind` and `env`; no relay text in logs.
- [ ] T026 `hermes hmp push status`, read-only, active registrations and non-REVOKED generation-row
  counts only. Tests: no identifiers, URL
  secrets or handles in output; no dispatch outcome field; no change to `devices list` (SD3) or key
  handling (SD5).
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

## Phase 3: relay (separate repository; after T012)

- [ ] T030 Verifier, HPKE opener, binding checks, fixed templates, limiter, replay cache, optional
  `iid` allowlist. Unit tests with RFC 9180 vectors and negatives (signature, audience, skew,
  replay with nonce retention to `ts + skew`, full replay cache refuses, kid, iid mismatch, app,
  env, expiry beyond 14 d, platform, `addr_kind`, oversize). Every table follows plan §6.5.
  Per-key caps run before the global count and only admitted requests charge it; verify-budget
  exhaustion gives `429` with no provider call; a two-`iid` destination-ceiling test documents the
  A14 residual; the replay cache stays within 4,800 live nonces at the verify budget; FCM requests
  carry no `env`. Address-free logs with no `iid` prefix.
- [ ] T031 APNs sender (HTTP/2, ES256 provider token refresh 20–60 min, priority 10, alert type,
  expiration, collapse ID, Time Sensitive key) and FCM v1 sender (`token` or `fid` by `addr_kind`,
  HIGH, TTL, constant collapse key, channel, tag, restricted package, data keys). One provider
  attempt per request, no provider retry. Response mapping to the PN-REL-4 set, with
  `provider_unavailable` after any attempt, including provider throttling (APNs `TooManyRequests`,
  FCM `QUOTA_EXCEEDED`), never `429`. Tests against provider stubs.
- [ ] T032 Deployment descriptor for the chosen platform (O1/O2), single replica (D27). No secrets in
  the repository or CI. Runbook for key rotation and incidents.
- [ ] T033 **Owner-gated.** Sandbox credentials and sends to owner test devices only.

## Phase 4: app (private repository; consumes spec §11; separate app specs and reviews)

- [ ] T040 030 S2 registrar wiring (T101 there) using `PUT/DELETE` CAS and idempotent retry with the
  persisted, encrypted body, deleted on commit or abandon (PN-APP-2); `503 retry_state_lost`, and a
  `400`/`503` answer to a replay after a configuration change, handled like `409 stale` (`GET`, then
  a new intent). `DELETE` mapping per spec §11 and a persisted, encrypted pending delete intent
  retried on resume (PN-APP-3); no "alerts off" copy before a `200`.
- [ ] T041 030 production resolver adapter (T103 there) with the §11 mapping: sends `{v, hint}`;
  every `404` → `other`; never `notPending` from a `404`. The S1 port is unchanged.
- [ ] T042 Native APNs registration (iOS) and FCM registration (Android), with the address kind. No
  token caching across launches beyond the current registration.
- [ ] T043 Sealing with the D1 suite and shipped kid list; the RFC vectors pass in Dart.
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

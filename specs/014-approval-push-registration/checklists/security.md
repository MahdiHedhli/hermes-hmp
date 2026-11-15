# Security checklist: spec 014

Reviewer-owned. The author ticks nothing; the amendment ticked nothing. Each item cites the
requirement it checks.

## Authority and scope
- [ ] No payload field can name an instance, profile, request, answer or pairing (PN-SEC-1, PN-REL-5).
- [ ] The resolver returns only `state` and, when located, `profile`. No request ID, command, choices, expiry or session/run identifiers (PN-RES-3).
- [ ] An answer still needs the app's fresh AP-3 read and a human choice. The resolver result enables nothing (spec §11, 030 SR-4, T047).
- [ ] Recipients are exactly effective approval owner AND bot grant AND the row's own live family within absolute TTL AND current registration AND kid live, read live at dispatch (PN-DSP-4).
- [ ] A jobs/model `GRANT`, a shared `user_id` or pairing alone never makes a recipient (PN-SEC-2).
- [ ] No route reuses `/bots/{p}/authorize`, owner-controls grant, access cards or any privilege-grant path (PN-REG).
- [ ] Non-owner and host-denied devices get `404` before any registration or hint read (PN-REG, PN-RES-1).
- [ ] Existing send, jobs, model, AP-3 and AP-4 authority, gates and outcomes are unchanged, and push defaults off (PN-NC).

## Visibility
- [ ] Dispatch re-checks AP-3 visibility (I-6), including Desktop held, at dequeue and before each send; a hidden row is not dispatched later (PN-DSP-1/3).
- [ ] The resolver answers `404` for a row hidden now, open or settled, and never `located` or `not_pending` for it; visibility is evaluated now, so a row hidden earlier and visible now follows its current state (PN-RES-1/2, analysis A20).
- [ ] A locally expired row (`expires_at + EXPIRY_GRACE_S`) is `404`; AP-3 calls the same I-6 seam, shown by an equivalence test; the withdrawn-Phone-row residual is recorded (§10, analysis A20).

## Issuance and nonreuse
- [ ] `R` derivation inputs include `iid`, `H`, `device_id`, `family_id`, `G` and a per-row CSPRNG salt under a domain-separated tag (PN-ISS-1).
- [ ] `R` is re-derivable only with the store and `k_grace`; every re-derivation is checked against the stored hash before use (PN-ISS-1/4).
- [ ] `G` is persisted, never decremented for a non-REVOKED device, advanced exactly once per transaction that changes a device's registration state (every successful PUT and DELETE and every exit from `active`), and stays below 2^53 with `503 other` at the bound (PN-REG-2/3, PN-REV). Its row is deleted only with a REVOKED device, behind an explicit `set_device_state` terminal-state guard and test (D28, PN-BND).
- [ ] Only `SHA-256(R)` is stored. A UNIQUE index covers stored rows; a violation leaves `G` and the old row unchanged (PN-ISS-2, PN-REG-2).
- [ ] `K` comes from the OS CSPRNG, lives only in memory, is bound to the exact registration and prompt generation, and is redrawn on a live collision (PN-ISS-3).
- [ ] Validation compares every bound field; existence alone never resolves (PN-ISS-4).
- [ ] The nonreuse statement is a computational PRF argument, not a proof or a claimed test result, and names the `k_grace` re-creation and consistent-restore cases (PN-ISS-2).
- [ ] Push reads `k_grace` only through a new read-only accessor that never creates or rewrites it; every read is off the event loop; a transient read error fails closed, never creates, rewrites or deletes the secret, and by itself never changes a row; only hash-mismatch expiry needs a successful read (PN-ISS-5, PN-BND).

## Concurrency, CAS and late events
- [ ] Idempotent replay returns the identical `R` and generation. A different body is `409 idempotency_conflict`; a different bearer family or an expired row is `409 stale`; a re-derived hash mismatch is `503 retry_state_lost` with nothing changed (PN-REG-2).
- [ ] Absent a consistent restore of the store and the binding, a replay whose history was purged or evicted fails CAS and never succeeds with fresh handle bytes; the restore case is stated as a residual (PN-REG-2, PN-ISS-2, PN-BND, analysis A19).
- [ ] A replay after the kid was removed or push became unavailable answers `400`/`503` before the replay check, and the app does `GET`, then a new intent (PN-REG-2, §11).
- [ ] A late older PUT after a newer PUT or DELETE fails CAS (PN-REG-3).
- [ ] Relay feedback changes only the exact `(route_hash, G)` that was dispatched (PN-DSP-9).
- [ ] Queued or retried dispatch re-checks every gate at send time (PN-DSP-3).
- [ ] Closed or Phone-closed prompt generations never dispatch or resolve `located` (I-1, I-3, I-5).

## Revocation
- [ ] Eligibility closes by validation on any committed revocation, without relying on a cascade (PN-REV).
- [ ] Each PN-REV cause, including the P4 lost-response re-issue, retires rows in a separate best-effort transaction **after** the cause commits; no push statement or savepoint runs inside a cause's transaction, and a push failure, including a real `SQLITE_FULL`, never changes or blocks the cause's outcome (PN-REV, PN-NC).
- [ ] After revoke, re-pair, family reuse revocation, P4 re-issue or `rotate-key`, no dispatch occurs and old `R`/`K` resolve `404`.
- [ ] Owner removal, host denial, bot grant loss and the push flag off are enforced by live re-checks at dispatch and resolve.
- [ ] `DELETE` of an existing registration is never refused for capacity and never inserts into a capped table; when its store write fails, the bounded in-memory delete fence still closes eligibility, `GET` reports the row as not active, and the restart residual is recorded (PN-REG-3, PN-BND, analysis A12).
- [ ] Only a `200` confirms removal; every other `DELETE` outcome is "not confirmed" and the app keeps a persisted, encrypted pending delete intent; no "alerts off" claim before a `200` (PN-REG-3, PN-APP-3, §11).
- [ ] Active rows that are past `expires_at` (= `seal_expires_at`), kid-removed or hash-mismatched are expired by the purge, so they cannot hold D24 capacity beyond the seal maximum plus the next purge interval while the listener runs (a stopped listener purges at next open); expiry and removed-kid expiry proceed with an unreadable `k_grace` (PN-BND).

## Relay and custody
- [ ] The relay URL, audience, pins and kids come only from host configuration. No redirects or environment proxies. The response is bounded and parsed into a closed set (PN-REL-1, PN-REL-4).
- [ ] The kid is checked against the live host list at `PUT` and at dispatch; seal lifetime, `env` and `addr_kind` are checked at `PUT` and again by the relay against the sealed plaintext (PN-REG-2, PN-DSP-4, PN-REL-3).
- [ ] Relay requests are signed over the full transcript including the audience, with skew checks and nonces kept until `ts + skew`; a full replay cache refuses rather than evicts (PN-REL-2/3).
- [ ] The seal binds `iid`, app, env, platform, `addr_kind` and `not_after`. The relay rejects any mismatch before contacting a provider (PN-REL-3, PN-SEAL-1).
- [ ] `unavailable` is returned only when no provider attempt began; HMP retries only that and pre-write connect failures; ambiguous and provider failures are never retried (PN-DSP-8, PN-REL-4).
- [ ] Provider keys and HPKE private keys exist only in the relay secret store. None reaches HMP, the app, the repository or CI logs (PN-REL-7).
- [ ] The relay stores no provider-address database. Logs carry no address, seal, `R`, `K`, `C`, signature or `iid` prefix (PN-REL-7/8).
- [ ] The relay ignores host-supplied text; templates are fixed (PN-REL-5).
- [ ] iOS uses direct APNs with priority 10, `alert` type and an explicit expiration. No FCM-for-iOS priority 5 path exists (PN-REL-5).
- [ ] The relay runs as a single replica, or a reviewed shared-state design exists (PN-REL-6, D27).
- [ ] R2 runs with an `iid` allowlist; R1 open enrollment is not activated before the owner accepts the recorded residuals (D23).
- [ ] The leaked-token spam, sybil cross-host suppression (at least `⌈ceiling / pair cap⌉` `iid`s), unrevocable-seal, `iid`/`C` correlation and public global and verify exhaustion residuals are recorded (analysis A1, A6, A13, A14, A17); public mode stays inactive and owner-pending.
- [ ] Per-key caps run before the global count and only admitted requests charge it; a full replay cache is a defensive path under the 4,800-nonce bound (PN-REL-3/6).
- [ ] FCM requests carry no `env`; the `iid` is the 52-character lowercase unpadded base32 SPKI fingerprint; provider throttling is `502`, never `429` (PN-REL-3/4).

## Bounds
- [ ] Every queue, map, slot, table, retry, timeout, body and response has the frozen bound and overflow rule from `ROOT_DECISIONS.md` (PN-SEC-6, PN-BND, plan §6.5).
- [ ] Active registrations are capped per instance independently of the queue; overflow refuses only a new device's `PUT` (PN-BND, D24).
- [ ] Generation rows of non-REVOKED devices are capped (D28); a first `PUT` and a no-generation `DELETE` at the cap refuse `503 push_capacity` with nothing written; an active registration implies a generation row; the delayed-`PUT` race is documented (PN-BND, PN-REG-3).
- [ ] Retained-row caps are enforced only in `PUT` and purge; the transient excess is bounded by D24 (PN-BND, D25).
- [ ] A full queue drops the new event without blocking or failing any Hermes path; enqueue is thread-safe and never awaits (PN-DSP-2).
- [ ] The breaker drops without waiting, and listener close is bounded and never waits on the relay (PN-DSP-10).
- [ ] Hourly caps and coalescing hold under a burst; the newest hint wins; a live rate counter, keyed by `device_id` and kept across re-registration, is never evicted; idle-slot eviction never exceeds the hourly cap (PN-DSP-5/7, PN-BND, analysis A22).

## Logging and privacy
- [ ] `R`, `K`, `C`, `S`, salt, `request_id`, signatures, profile names and relay text never reach `log_event`, audit, CLI output or issue drafts (PN-LOG).
- [ ] `push status` prints store counts and fixed codes only, reports no dispatch outcomes, and does not touch `devices list` (SD3) or key handling (SD5) (PN-OPS).
- [ ] The public repository receives no physical-device evidence or identifiers.

## Platform truthfulness
- [ ] No document claims delivery before Hermes's deadline, Critical Alert behavior, or delivery when the user turned off Time Sensitive, notifications or the channel.
- [ ] Documents distinguish background OS display, foreground app presentation, unknown force-quit/force-stop outcomes and OS watch mirroring from a future standalone watch (PN-PLAT).
- [ ] Simulator or emulator results are never cited for plan §8.4 rows.
- [ ] Signed Time Sensitive and push capabilities are verified only on owner-authorized builds.

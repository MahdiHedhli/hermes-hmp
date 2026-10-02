# Analysis: approval push registration (spec 014)

Consistency analysis of the proposal against the constitution, spec 013, spec 034 (accepted source
`150bd0f`, per root), app spec 030 and the app security requirements. The author checked these
artifacts; this is not independent review. It was amended on 2026-10-02 after an independent design
review (verdict `NEEDS_AMENDMENT`, blockers B1–B4, findings N1–N23), and again in one bounded pass
after the independent delta review (verdict `NEEDS_AMENDMENT`, findings C1–C8, root's decisions
recorded in `ROOT_DECISIONS.md`). Root checks the final text against C1–C8; nothing is frozen and no
checklist box is ticked.

## 1. Constitution

| Principle | Result |
| --- | --- |
| I. Hermes owns agent behavior | Pass. The alert and resolver are hints. Answers still go through AP-4 to Hermes after a fresh read. No approval decision, expiry authority or execution path is added. |
| I. Minimum-version policy | Pass. No floor, manifest, fingerprint or latch (PN-AV-1). Availability inherits the approval members; later and unknown builds attempt the actual APIs. |
| II. Device trust is explicit | Pass. A device-scoped registration on the pinned instance. Eligibility is the effective approval owner AND the bot grant AND the row's own live family AND AP-3 visibility, read live. Revocation closes eligibility by validation; cascades are cleanup. |
| III. Public by default | Pass for these files: no private addresses, identifiers or owner evidence. Physical results stay private. |
| IV. Contract before code | Pass. Wire additions are specified here and go to HMP v1 §7f (T010) before code. |
| V. Verify on Hermes | Planned: route-level tests, isolated fixture, surface, log and privacy scans (T022–T029). Samples are evidence, not gates. |
| VI. Security findings block | The open items in §4 are explicit. `SECURITY_REVIEW_REQUIRED` items are listed in plan §7.1. |
| Closed plugin surface (PR-2) | **Needs amendment (T011).** HMP currently opens sockets only to loopback literals. The relay client is a new outbound destination, sourced only from host config. There is no new registration surface, hook, tool or dependency. |

## 2. Cross-artifact consistency

| Source requirement | Where satisfied |
| --- | --- |
| 030 FR-11 / G-ISSUE: fresh nonreused handles across device, pairing, token and host-registration generations; validate against the exact active registration | PN-ISS-1/2/4. `R` inputs include `device_id`, `family_id`, `H`, `G` and a per-row salt; validation is exact-field and checks the re-derived hash. |
| 030 FS-4 / G-HMP: device-scoped registration, recipient eligibility, resolver route, revocation cascade, rate limits | PN-REG, PN-DSP-4, PN-RES, PN-REV, PN-REG-4, PN-RES-4, PN-DSP-7, PN-BND |
| 030 S1 resolver port `HintResolveRequest{iid, epoch, hintRef}` (root-accepted) | PN-RES-1 body `{v, hint}`; the server binds the bearer device's current registration. S1 is not reopened. |
| 030 FS-3: `located` leads to a page that can show the prompt | I-6 visibility at resolve; hidden is `404` |
| 030 FP-4 shape 22..64 b64url | `R`, `K` are 43 characters; `C` is 32 characters |
| 030 FS-2 / RD-19: `NotPending` only for a definitive authoritative negative | PN-RES-2 with I-2 and D4. Hidden rows and every `404` are never `notPending` (spec §11). |
| 030 FR-6 lost-ack retry returns the same registration | PN-REG-2 replay by request hash with hash-checked re-derivation; `503 retry_state_lost` when `k_grace` was re-created; PN-APP-2 byte-identical retry |
| 030 FR-5 stale intent and generation CAS | PN-REG-2/3 CAS on `G`; app intent identity stays local |
| 030 SR-2 iid only from local registration | The payload has no `iid`; resolver input is the hint only, under the bearer of the pinned instance |
| 030 SR-10: no command, bot or media identifiers on the lock screen | Fixed relay template (PN-REL-5) |
| App root decision: provider idempotency, delayed feedback compares the exact registration and generation | PN-REG-2 replay; PN-DSP-9 feedback CAS |
| App root decision: dispatch rechecks profile authorization, visibility and qualification | PN-DSP-3/4 with I-6 |
| App root decision: APNs keeps one notification and may reorder or deliver late; never a complete inbox | Plan §6.2; T047 catch-up; D5; story 10 wording |
| App root decision: an HMP deadline estimate is not a native deadline | PN-DSP-6 |
| App root decision: jobs/model `GRANT` and shared user IDs confer no recipient authority | PN-SEC-2 |
| App root decision 6: no roster-scan fallback | Story 10; the instance-level summary is a recorded gap |
| 034 R6 gate order and `404` non-disclosure for non-owners | PN-REG and PN-RES gate order |
| 034 R9 generation fence; R10 binding fence | I-1, I-3, I-5; closed or Phone-closed generations never dispatch or resolve `located` |
| 034 AP-3 visibility (`list_visible` hides `bot_chat` while `desktop_held`) | I-6; PN-DSP-3; PN-RES-1/2 |
| 034 D8 residual: allowlisted device without a controls decision also gets jobs/model | Unchanged. Push uses the narrower approval-owner predicate and adds no authority. |
| Spec 013 constraint: closed eligibility member set | No new member. Push is a host feature over existing members. |
| SECURITY.md Notifications | Hint only, minimal payload, rehydrate on open, authenticated, scoped, revocable and rate-limited enrollment and publishing |

## 3. Gap classification check

The resolver and issuer are HMP-owned contract work, not Nous API gaps (030 FS-4, plan §1).

1. **Coverage (`EVIDENCE_GAP`, research pending).** 014 dispatches only for rows the 034 lane
   inserts: Bot Chat streams HMP started, and HMP Phone chat. Approvals on Desktop, CLI, cron and
   other platforms are not covered. The independent review spot-checked one Hermes checkout
   (`81f481b2`, `tools/approval.py`): approval notification there is a single callback per
   `session_key`, and `list_gateway_approvals`, `register_gateway_settle`,
   `withdraw_gateway_approval` and `pending_gateway_approval_count()` are module functions, not
   documented plugin APIs. That is consistent with "no multi-subscriber observer at that commit",
   but it is not evidence about current main, the builds root targets, Desktop TUI RPC, CLI prompts
   or cron. The proposed notifier covers only 034 rows; broader cross-channel gap research is
   pending (T005). No Nous API gap is filed from this.
2. **Settlement (`HERMES_API_GAP`, as recorded by 034 G4).** No settlement or expiry event, so a
   located prompt may already be settled elsewhere. The answer path discovers that (`409`), and the
   app's fresh read shows the current list.
3. **Capability and request ID (`HERMES_API_GAP`, as recorded by 034 G1, G3).**
4. **Approval-lane amendments.** I-1, I-2 and I-6 were absent from base `150bd0f`. Spec 015
   `6a139ba` supplies the independently reviewed source inputs and closes T003; integration
   and runtime consumers remain 014 work, not Hermes gaps.

Everything else (relay, accounts, keys, native registration, persistence, device proof) is our own
work or the owner's choice.

## 4. Findings and risks (author's, for the reviewer)

| # | Finding | Severity | Disposition |
| --- | --- | --- | --- |
| A1 | Leaked raw provider token allows generic-alert spam through an open relay: anyone can seal to the public kid under their own `iid` | Medium (availability and annoyance; no authority) | Per-`(destination, iid)` and destination caps (D17); unknown routes show "unlinked"; R2 runs an `iid` allowlist; R1 open enrollment is not activated until the owner accepts this residual |
| A2 | Reusing the instance key for relay signatures (D2) is a cross-protocol use | Low under conditions | Plan §7.3 conditions (tag sets, prefix-freeness test, TLS 1.3 only); alternative D2(b) |
| A3 | Nonreuse beyond stored history rests on a computational PRF argument (salts, `G`), not on stored history or a proof. The replay CAS guarantees also assume no consistent restore of the store and binding (A19). Salts' nonreuse is computational. | Low | Stated as an argument (PN-ISS-2), not a test claim; UNIQUE index only while rows are stored |
| A4 | HMP rows live in process memory; a restart loses hints, so pending alerts resolve as unable to check | Low (availability) | Matches 034 AP-2; the app's fresh Approvals read still works if Hermes re-emits |
| A5 | Coverage: only 034 rows (§3 item 1). Users may expect alerts for Desktop or CLI approvals | High for user expectation | State the coverage in user-facing copy and FEATURES once shipped; research T005 before any upstream request |
| A6 | The relay learns which `iid`s a provider token is registered with; `C` is a stable per-(registration, bot) pseudonym visible to the relay, Apple and Google | Low (privacy) | Disclose in privacy answers (O6); relay logs carry no `iid` prefix (PN-REL-8); D2(b) would replace `iid` with a relay key fingerprint, but still links the registrations |
| A7 | Android force-stop, recents swipe, iOS force-quit, before-first-unlock and Play services proxying are not established from the evidence read | Unknown | `PLATFORM_GAP`/`EVIDENCE_GAP`; measured on device and reported as observed (plan §8.4); D16 |
| A8 | `interruption-level: time-sensitive` without the signed entitlement: system behavior not verified here | Unknown | `PLATFORM_GAP`; capability check on owner-authorized builds only |
| A9 | `UNAuthorizationOptions.timeSensitive`: availability metadata reads iOS 15.0 to 15.0 (introduced and deprecated in 15.0), consistent with the earlier app root record. The earlier "evidence conflict" note misread the page. | Resolved | The design does not use the option; it relies on the Time Sensitive entitlement, checked only on owner-authorized signed builds |
| A10 | The relay client is HMP's first non-loopback socket | Medium (surface) | T011 amendment, host-config-only destination, no redirects or proxies, bounded parser |
| A11 | Base `150bd0f` lacked I-1/I-2/I-6; spec 015 `6a139ba` now supplies source-accepted inputs, while 014 integration and runtime evidence remain pending | Source prerequisite resolved; runtime pending | T003 source gate closed; integrate accepted inputs and verify consumers before wiring |
| A12 | A `DELETE` whose store write fails (for example a full disk), and background display that app code cannot suppress | Low | Eligibility closes at once through the bounded in-memory delete fence (PN-REG-3, PN-BND); `GET` reports a fenced row as not active; `503 other` is "not confirmed". The app keeps a persisted, encrypted pending delete intent, retries on resume, and says alerts stopped only after a `200` (PN-APP-3, §11). Residual: the fence does not survive a restart, so alerts may resume until a retry succeeds, a revocation happens or the seal's `not_after` passes; a tap then shows unable to check |
| A13 | A phone that unpairs while its host is unreachable cannot withdraw the seal the host holds; the host's alerts keep being displayed by the OS until `not_after` | Medium (annoyance; no authority) | D9 max lowered to 14 d; app shows "unlinked" on tap; Android full alert opt-out can rotate the FCM registration; iOS has no equivalent guarantee |
| A14 | A shared per-destination cap lets one host suppress another's real alerts. The per-`(destination, iid)` cap stops **one** `iid` doing so (not all cross-host suppression), but under open enrollment `iid`s cost nothing, so `n ≥ ⌈destination ceiling / pair cap⌉` sybil `iid`s (2 at the proposed 60 and 30) holding a leaked address still suppress the real host's alerts to that phone | Medium (availability) | Root keeps the destination ceiling (the spam bound) and accepts the suppression; the alternative of dropping the ceiling would allow unbounded spam across many `iid`s. Recorded for R1 acceptance; public mode stays inactive and owner-pending (O1) |
| A15 | Author defect found during amendment: the proposal's `R` took `request_id_raw` as an input while storing only its hash, so the dispatcher could never re-derive `R` for the payload | Fixed in the proposal | `R` now derives from stored inputs plus a per-row salt; `request_id` is idempotency-only (PN-ISS-1). Needs delta review. |
| A16 | The plan assumed an existing hourly store purge; HMP base `4d6863e` has none (only the `IDEMPOTENCY_RETENTION_S` comment) | Fixed in the proposal | 014 specifies its own bounded purge step (PN-BND). The base comment itself is outside 014 scope. |
| A17 | Public (R1) global exhaustion: unauthenticated traffic from many source addresses can exhaust the global verify budget (20/s), and sybil `iid`s sealing random addresses can exhaust the global hourly budget `B`; those requests pass the seal checks because the relay checks `app`, `env` and bindings, not whether an address is real. Either denies all R1 alerts. Garbage addresses may also affect the relay's standing with a provider (`EVIDENCE_GAP`, not checked) | Medium (availability; no authority) | Per-key caps run before the global count and only admitted requests charge it (PN-REL-6); keyed tables are bounded by admitted requests (plan §6.5); R2 allowlist; R1 is not activated until the owner accepts A17 and the restated A14 (O1). R2 is not immune: the allowlist reduces reachability and stops non-allowlisted provider and hourly admission, but the global verify budget is consumed before signature and `iid` allowlist checks (PN-REL-3), so a reachable tailnet peer can still exhaust it. That residual is explicit; no limit is moved and no key is added |
| A18 | A cleanup after a revoke, refresh-reuse, P4 or identity change can fail (for example `SQLITE_FULL`) | Low | The cleanup is a separate best-effort transaction after the cause commits (PN-REV). Eligibility is validation-based, so a committed revocation closes push at once. Leftover rows are inert until the purge retires them. No savepoint isolation is promised, because SQLite can roll back the whole transaction on such errors |
| A19 | After a consistent restore of the store and the binding that rolls `G` back, a byte-identical retry of a `PUT` whose acknowledgement was lost can pass CAS and return a fresh `R′` | Low | Harmless: the app never committed the lost handle and commits `R′`; freshness of `R′` rests on salts (computational). The replay CAS guarantees are stated absent such a restore (PN-REG-2, PN-ISS-2) |
| A20 | Visibility is evaluated now (root choice). A row hidden earlier, settled by Hermes meanwhile and visible now may answer `not_pending`; the resolver does not reconcile Phone rows, so `located` can name a Phone row Hermes has withdrawn | Low | `not_pending` is a true statement about Hermes; `located` for a withdrawn Phone row is the same residual as "located but settled elsewhere" (the fresh AP-3 read shows the truth). Local expiry and the AP-3 seam are shared through I-6, with an equivalence test |
| A21 | Generation rows: a delayed `PUT` can land after capacity frees, after a no-generation `DELETE` was refused `push_capacity` | Low | Documented race, no invariant waiver (PN-REG-3). The app's pending delete intent retries as a normal CAS `DELETE`. After 256 distinct non-REVOKED devices have written, new devices remain blocked until the operator revokes some; expired registrations do not free generation slots. The read-only CLI reports both counts. REVOKED devices' rows are purged only with the terminal-state guard on `set_device_state` (PN-BND, T020) |
| A22 | Evicting an idle coalescing slot forgets its last send time and loosens the D6 minimum interval; counters are memory only and a restart resets them | Low | The per-device hourly counter (keyed by `device_id`, kept across re-registration while the device is eligible and active) still bounds the rate; the relay's per-`(destination, iid)` cap bounds it again. Self-only effect |

## 5. Coverage of the end state

Every end-state item in spec "End state" maps to physical rows in plan §8.4 and tasks T050–T053.
No phase before T050 can claim delivery. Measured-only rows are reported as observed, not as
satisfied promises.

## 6. Primary evidence (fetched read-only on 2026-10-02 UTC)

| Source | Fact used | Page date |
| --- | --- | --- |
| [Apple: Sending notification requests to APNs](https://developer.apple.com/documentation/usernotifications/sending-notification-requests-to-apns) | Best-effort reordering; one stored notification per bundle ID; with `apns-expiration` APNs tries to deliver at least once until that date (whether it may deliver after is not stated: `EVIDENCE_GAP`); priority 10 immediate, 5 power-aware; `alert` push type; topic is the bundle ID; collapse ID at most 64 bytes; 4 KB payload; do not assume token size | no date shown |
| [Apple: Setting up a remote notification server](https://developer.apple.com/documentation/usernotifications/setting-up-a-remote-notification-server) | The provider server holds the trust with APNs; APNs may coalesce for offline devices | no date shown |
| [Apple: UNNotificationInterruptionLevel.timeSensitive](https://developer.apple.com/documentation/usernotifications/unnotificationinterruptionlevel/timesensitive) | Breaks through Notification Summary and Focus; the user can turn it off | no date shown |
| [Apple: UNAuthorizationOptions.timeSensitive](https://developer.apple.com/documentation/usernotifications/unauthorizationoptions/timesensitive) | Availability metadata iOS 15.0 to 15.0 (deprecated in 15.0); not used | no date shown |
| [Apple: Establishing a token-based connection to APNs](https://developer.apple.com/documentation/usernotifications/establishing-a-token-based-connection-to-apns) | ES256 JWT; refresh no more than every 20 and no less than every 60 minutes; environment-specific team keys recommended (at most two per environment); topic-specific keys exist | no date shown |
| [Apple: Handling notification responses from APNs](https://developer.apple.com/documentation/usernotifications/handling-notification-responses-from-apns) | `410` Unregistered or ExpiredToken; the do-not-retry list; 5xx retry after 15 minutes; `TooManyRequests` | no date shown |
| [Apple: Generating a remote notification](https://developer.apple.com/documentation/usernotifications/generating-a-remote-notification) | `interruption-level` values; custom keys go beside `aps` | no date shown |
| [Apple: Registering your app with APNs](https://developer.apple.com/documentation/usernotifications/registering-your-app-with-apns) | Do not cache tokens; new token after restore, new device or OS reinstall | no date shown |
| [Firebase: Android message priority](https://firebase.google.com/docs/cloud-messaging/android-message-priority) | HIGH may wake from Doze; seconds of processing; no network before display; deprioritization over 7 days if not user-visible; with notifications disabled none are posted and high-priority messages are deprioritized; the example's `apns-priority: 5` | 2026-10-01 |
| [Firebase: Registration management](https://firebase.google.com/docs/cloud-messaging/manage-tokens) | Transition from tokens to Firebase Installation IDs, both co-supported; stale after one month; Android expiry after 270 days | 2026-10-01 |
| [Firebase: Message types](https://firebase.google.com/docs/cloud-messaging/customize-messages/set-message-type) | Notification messages are displayed by the SDK only in the background; in the foreground app code decides; 4096-byte payload | 2026-10-01 |
| [Firebase: HTTP v1 messages reference](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages) | `message.token` marked deprecated ("use fid instead"; accepts an FID during the transition); `AndroidConfig` priority, TTL (at most 4 weeks), `collapse_key` (at most 4 distinct), `restricted_package_name`; notification `channel_id`, `tag`, `proxy` (`PROXY_UNSPECIFIED` behaves as `IF_PRIORITY_LOWERED`) | 2026-09-08 |
| [Firebase: ErrorCode](https://firebase.google.com/docs/reference/fcm/rest/v1/ErrorCode) | `UNREGISTERED` 404; `QUOTA_EXCEEDED` 429 with at least a one-minute delay; `UNAVAILABLE` and `INTERNAL` retry with backoff and `Retry-After`; 4096-byte limit; TTL 0 to 2,419,200 s | 2026-02-03 |
| [Firebase: v1 send authorization](https://firebase.google.com/docs/cloud-messaging/send/v1-api#authorize-http-v1-send-requests) | OAuth 2.0 short-lived tokens from a service account or Application Default Credentials | 2026-10-01 |
| [Android: Notification runtime permission](https://developer.android.com/develop/ui/compose/notifications/notification-permission) | `POST_NOTIFICATIONS` on Android 13+; notifications off by default for new installs | 2026-10-01 |
| [Android: Notification channels](https://developer.android.com/develop/ui/compose/notifications/channels) | Importance cannot be changed by the app after creation | 2026-10-01 |
| [Android: Power management restrictions](https://developer.android.com/topic/performance/power/power-details) | In the device-state table, with the screen off and Doze active, high-priority FCM has no execution limits, while normal priority waits for a maintenance window. The user can restrict battery. | 2026-05-19 |

Anything not in this table, such as Apple behavior for force-quit apps or before first unlock,
Android force-stop or recents swipe, Play services proxy tap behavior, Watch mirroring, or a hosting
platform's HTTP/2 support, is an assumption or a gap and is marked as such.

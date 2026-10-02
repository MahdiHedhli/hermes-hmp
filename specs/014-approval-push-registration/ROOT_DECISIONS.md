# Root decisions (design frozen 2026-10-02; owner choices pending)

The direction tables and proposal columns below preserve the review history. The **Root freeze**
section is authoritative for accepted design choices and bounds. The owner items O1–O6 and global
deployment budgets remain pending. Numbers carry no latency, entropy or delivery guarantee.

Kinds: **R** = root design or protocol choice, reversible in source. **OA** = owner or account
action: outward-facing, billed or hard to reverse. Root design choices never authorize an OA item.

## Review history: root direction received 2026-10-02

| Item | Direction | Where applied |
| --- | --- | --- |
| B1 | Enforce exact AP-3 visibility, including Desktop held, at dispatch (dequeue and before each send) and at resolve. Hidden means unable to check, never `not_pending`. | spec PN-DSP-3, PN-RES-1/2, I-6 |
| B2 | Resolver body `{v: 1, hint: K}`; the server binds the bearer device's current registration. The accepted 030 resolver interface is retained; S1 is not reopened. | spec PN-RES-1, §11 |
| B3 | A replay whose re-derived route hash mismatches answers `503 retry_state_lost`; row and `G` unchanged; recovery is `GET` then a new intent. | spec PN-REG-2, PN-ISS-1 |
| B4 | State observed coverage (034 rows only); broader cross-channel research is a pending `EVIDENCE_GAP`; no unverified Nous API gap. | spec Summary, Gaps; analysis §3 |
| N4 | CSPRNG per-row salt; a computational PRF/collision argument, not a proof. | spec PN-ISS-1/2 |
| N1 | Retry only `unavailable` before a provider attempt; ambiguous or provider failure gets no automatic retry. | spec PN-DSP-8, PN-REL-4 |
| N15 | Drop dispatch outcome counts from the CLI; no persistent status snapshot. | spec PN-OPS |
| D9 | Maximum seal lifetime 14 d; refresh under 4 d. | below |
| D21 | Unused. | below |
| D23 | Allowlisted `iid` for the owner R2 stage; public R1 open enrollment is not activated until the owner accepts the concrete abuse residuals. | below; plan §6.3 |
| N20 | Resolver `404` maps to `other`/unable to check; `GET` availability signals feature presence. | spec PN-REG-1, §11 |
| I-1, I-2, I-6 | Separate reviewed approval-lane amendments before any 014 implementation. | spec §10; tasks T003 |
| Bounds | Every map, slot, registration, tombstone, replay and rate table gets an explicit cardinality and overflow rule; concrete host and single-replica relay caps are proposed. | spec PN-BND; plan §6.5; D24–D28 |
| All other N items | Apply as the review proposed. | see the amendment report |

## Review history: bounded final pass (delta review C1–C8)

| Item | Direction | Where applied |
|---|---|---|
| C1 | Push cleanup is a separate best-effort transaction after the cause commits, never executed inside a cause's transaction; no savepoint promise. A committed revocation closes push by live validation even if cleanup fails. A real `SQLITE_FULL` test leaves the cause committed. | spec PN-REV, PN-NC; plan §3, §5.4, §8.1; tasks T020, T028 |
| C2 | `expires_at` is `seal_expires_at`. The bounded purge expires stale, kid-removed and hash-mismatched active rows, freeing D24 capacity. | spec PN-BND, PN-PER, PN-REV; tasks T020 |
| D28 | Option (c): at most 256 generation rows for non-REVOKED devices, plus a purge of REVOKED devices' generation and registration rows only with an explicit terminal-state guard and test that `Store.set_device_state` cannot revive REVOKED. `G` never decreases for a non-REVOKED device; an active registration implies a generation row. A first `PUT` and a no-generation `DELETE` at the cap refuse `503 push_capacity` (truthful: not confirmed); `DELETE` of an existing registration is never refused for capacity. The delayed-`PUT`-after-capacity-frees race stays documented, with no new invariant waiver. | spec PN-REG-2/3/4, PN-BND, PN-PER; tasks T020, T022 |
| C7 | No false promise: a persisted, encrypted pending delete intent, retried on resume; only a `200` confirms removal. | spec PN-REG-3, PN-APP-3, §11; tasks T040 |
| C3 | Drop the `generation` error extra. Add the four `why` values to the closed set with the codes they may accompany. Fixed messages are ignored; `code` and `why` are used. | spec PN-REG intro, PN-REG-2; tasks T010, T022 |
| C4 | Record the sybil suppression (at least `⌈destination ceiling / pair cap⌉` `iid`s) and public global and verify exhaustion (A17). Keep the destination spam ceiling; public mode stays inactive and owner-pending. Per-key caps before the global count; only admitted requests charge it. The replay cache is bounded by 4,800 and a full cache is defensive. | spec PN-REL-3/6; plan §6.5; analysis A14, A17 |
| C5 | Qualify the replay CAS guarantees: they hold absent a consistent restore of the store and the binding. Salt nonreuse is computational. | spec PN-REG-2, PN-ISS-2; analysis A19 |
| C6 | Option (a), current visibility: a row hidden earlier, settled authoritatively and visible now may answer `not_pending`. No sticky hidden bit and no extra history observer. Exact local expiry matches AP-3; AP-3 calls the shared I-6 seam, with an equivalence test. The withdrawn-Phone-row residual is recorded. | spec PN-RES-2, §10 I-6; tasks T003, T023; analysis A20 |
| C8 | Hourly counters keyed by `device_id`, kept across re-registration while the device is eligible and active. The loosening from idle coalescing-slot eviction is documented. | spec PN-BND; analysis A22; D6, D26 |
| Low items | `iid` canonical format; FCM requests carry no `env`; provider throttling is `502`, never a pre-provider `429`; exactly one `G` increment per transaction; `G` below 2^53 with `503` on overflow; `GET` latest-row rules and a fenced row not active; a config-change replay answers before the replay check and the app does `GET` then a new intent; the persisted `PUT` body is encrypted and deleted on commit or abandon. | spec PN-REG, PN-REL-3/4, PN-APP-2 |
| `k_grace` | A new read-only accessor for push only, never read-or-create, no change to existing callers. Every file read is off the event loop. A transient read error fails closed and does not destroy the secret. It needs its own source tests later; no current source is edited. | spec PN-ISS-5; plan §3; tasks T021 |
| 034 status | Spec 034 source `150bd0f` (PR #73) is independently accepted (root statement); native fixtures and deployment are pending; I-1, I-2 and I-6 are absent, so separately reviewed amendments are required. | spec Base, §10; plan §1; tasks T003 |
| Review | No new broad review round. Root checks the final diff and report against C1–C8; a targeted independent check of C1–C3 only if an actual remaining risk is found. No freeze; O1–O6 pending. | this file |

## Protocol and security decisions

| ID | Kind | Decision | Options | Recommendation |
|---|---|---|---|---|
| D1 | R (sticky once builds ship) | Seal construction | (a) HPKE RFC 9180 base mode, DHKEM(P-256, HKDF-SHA256), HKDF-SHA256, AES-128-GCM; (b) the same with X25519 and ChaCha20-Poly1305; (c) custom ECIES | (a). Standard, with RFC 9180 test vectors for this suite on relay and app. The plaintext carries `addr_kind` (PN-SEAL-1). Whether the app's existing Dart crypto dependencies are enough without a new package is an `EVIDENCE_GAP` for the app plan. |
| D2 | R | Host key for relay requests | (a) reuse the instance key with the distinct transcript tag `HMP1-PUSH-RELAY`; (b) a dedicated relay key in the binding directory, regenerated on identity change | (a) under the conditions in plan §7.3 (tag sets, prefix-freeness test, TLS 1.3 only as the rationale). (b) remains valid if root wants relay unlinkability from the TLS identity; the phone would then bind a host relay-key fingerprint obtained over the pinned `GET`. |
| D3 | R | Relay configuration source | (a) host config only, no default; (b) a shipped default URL constant plus a host override | (a): `push.relay_url`, `push.relay_audience`, `push.relay_kids`, optional SPKI pins. Repository visibility is O5. |
| D4 | R | Authoritative settle causes (spec §10 I-2) | include or exclude run completion (`expire_run`) | Exclude at first. Only applied answers, native `409 approval_not_pending`/`approval_not_active`, native `404 run_not_found` and Phone listing omission count. I-2 is an approval-lane amendment. |
| D5 | R | Collapse scope and identifier | (a) per registration; (b) per (registration, profile) for display, one constant FCM `collapse_key` | (b). `C` is 32 characters and a stable pseudonym per (registration, bot), recorded beside A6. APNs still stores only one pending notification per bundle while offline. The app never treats alerts as a complete inbox. |
| D19 | R | Recipients for a row | (a) every eligible owner device of the row's user; (b) only the device whose send started the turn | (a), bounded by D13, with the row-family binding (PN-DSP-4) and visibility (I-6). |
| D20 | R | Surfaces | Bot Chat only; or Bot Chat and Phone chat approvals | Both approval surfaces. Clarifications are excluded. |
| D21 | n/a | Unused | | No decision carries this ID. |
| D22 | R | Registration precondition | require push available and at least one approval member; or allow advance registration | Require it. The app also removes its registration while notifications are not allowed (PN-APP-1). |
| D23 | R (security) | Relay enrollment | (a) open, protected by the sealed `iid` binding and limits; (b) allowlisted `iid`s | Root direction: (b) for the R2 owner stage. (a) for R1 stays a proposal and is **not activated** until the owner accepts the concrete residuals (analysis A1, A6, A13, the restated A14 and A17). Allowlist size proposal: 8. |
| D27 | R (relay deployment) | Relay replica model | (a) exactly one replica with in-memory replay and rate state; (b) several replicas with shared replay and rate state | (a). (b) needs a new design and review. Its hosting consequences belong to O2. |

## Proposed bounds (all `⟨Dn⟩` placeholders in spec and plan)

| ID | Kind | Bound | Proposal | Basis |
|---|---|---|---|---|
| D6 | R | Coalescing minimum interval per slot; hourly cap per device | 10 s; 30/h | Bursts collapse into one trailing alert; a user still sees each new burst. Counters are keyed by device (C8); evicting an idle slot loosens the interval once, and the hourly cap still bounds it |
| D7 | R | Provider TTL floor / cap / default | 60 s / 900 s / 330 s | Hermes `approvals.timeout` default 300 s plus HMP's 30 s grace; expired events are dropped at dequeue; a late delivery is safe |
| D8 | R | Relay client: retries (pre-provider only), backoff, connect/total timeout, response cap; breaker threshold and cool-down; listener close bound | 2 retries (1 s, 4 s, ±20% jitter), 5 s / 10 s, 1 KiB; breaker after 3 consecutive retriable failures or post-write timeouts, open 60 s, one half-open probe; close waits at most 1 s | Bounded within TTL; never blocks Hermes; `rate_limited` and every ambiguous or provider outcome are not retried |
| D9 | R | Seal lifetime min / max; refresh threshold; retained-row retention | 1 h / **14 d**; re-seal under **4 d**; up to 30 d from the state change, shortened by the D25 caps | Root direction for max and refresh. 14 d bounds the unrevocable-seal residual (A13). Lost history under the caps reads as stale or unable to check (PN-BND). `expires_at` is defined as `seal_expires_at`, and the purge expires stale active rows (C2) |
| D10 | R | PUT body; sealed (decoded); seal plaintext | 4 KiB; 2048 B; 1024 B | Apple warns not to assume token size; the FCM v1 reference marks `token` deprecated in favor of `fid`; plaintext plus 65 B `enc` and a 16 B tag fits |
| D11 | R | Per-device buckets per minute: registration writes / status reads / resolves | 6 / 30 / 30 | Existing 60-second `RateLimiter` windows |
| D12 | R | Dispatch queue; relay concurrency per listener | 64; 2 | Bounded memory; a full queue drops the new event; the queue does not bound registrations (D24 does) |
| D13 | R | Recipients per approval row | 4 | Bounded fan-out |
| D14 | R | Hint map entries; hint lifetime | 256 entries (= D12 × D13); lives while its row is open, plus a 60 s margin after settle; hard maximum 60 min | Amended per review N13: a long-timeout prompt keeps its hint while open |
| D15 | R/UX | Visible text | literal "Approval needed"; or an app-bundled `loc-key` | Literal for the first stage; localization later as a UX decision |
| D16 | R (measured) | FCM Play services notification proxy | default (`PROXY_UNSPECIFIED`, which the reference describes as `IF_PRIORITY_LOWERED`); or `proxy: DENY` | Default, measured on device (`PLATFORM_GAP` for the tap and data path). Switch to DENY if the tap or data path fails. |
| D17 | R (relay policy); global budget OA | Relay limits per hour: per `iid` / per destination HMAC / per `(destination, iid)` / per source address / global; verify budget | 120 / 60 / 30 / 600 / owner-set (proposal R2 600, R1 6,000); 20 signature checks per second | The per-`(destination, iid)` cap (≤ D6) stops one `iid` from suppressing another host's alerts; at least `⌈ceiling / pair cap⌉` sybil `iid`s still can (A14), and the destination ceiling stays as the spam bound. Per-key caps run before the global count; only admitted requests charge it. Freeze the R1 values only with A14 restated and A17 recorded |
| D18 | R | Relay replay window and cache | equal to HMP `CLOCK_SKEW_S` (120 s); each nonce kept until `ts + 120 s`; cache 16,384 entries; full cache refuses with `503 unavailable` | Existing skew policy; never evict an unexpired nonce. At the 20/s verify budget at most 4,800 nonces are live, so a full cache is a defensive path |
| D24 | R | Active registrations per instance | Options: 16, 32 or **64** (recommended) | One per device already; HMP does not cap paired devices, and the queue does not bound registrations. Overflow refuses a new device's `PUT` (`503 write_gate_closed push_capacity`); replacement and `DELETE` of an existing registration are never refused. Conditional on the purge expiring stale active rows (C2) |
| D25 | R | Retained (non-active) rows | Options: per device 4, **8** or 16; per instance 512, **1,024** or 4,096 (recommended bold) | Enforced only in `PUT` and the purge step, oldest first; cascades never wait on it, so the table may exceed the total by at most D24 until the next `PUT` or purge |
| D26 | R | Coalescing slots per listener | Options: 128, **256** or 512 | LRU idle eviction; if every slot is pending, drop the new event. Eviction loosens the D6 interval for that slot once; the hourly cap bounds it (C8) |
| D28 | R | Generation rows (`G`) bound | (a) residual only, no code; (b) purge REVOKED devices' rows; (c) (b) plus a hard cap on non-REVOKED generation rows: 128, **256** or 1,024 (at least 2 × D24) | (c) at **256**, per root. The purge deletes a REVOKED device's generation and registration rows only with a terminal-state guard in `Store.set_device_state` and a test that it cannot revive REVOKED. A first `PUT` and a no-generation `DELETE` at the cap are refused `503 push_capacity` (not confirmed); `DELETE` of an existing registration is never refused for capacity. `G` never decreases for a non-REVOKED device; an active registration implies a generation row. A delayed `PUT` can land after capacity frees; the app's pending delete intent removes it (PN-REG-3) |

## Owner choices (infrastructure; no provisioning, billing or public action yet; all pending)

| ID | Kind | Choice | Options | Recommendation and tradeoffs |
|---|---|---|---|---|
| O1 | OA | Relay stage | R2 owner tailnet relay, then R1 public relay; or R1 directly | R2 then R1. R2 proves physical delivery for the owner with the least exposure and needs an owner machine with internet egress and provider-key custody. R1 is needed for any external tester, and its open enrollment needs the owner's acceptance of the recorded residuals. |
| O2 | OA | R1 hosting | small VPS or container; managed serverless; owner hardware | A managed container platform with a secret store and outbound HTTP/2. Verify HTTP/2 to APNs on the chosen platform before committing. It must run the single-replica model (D27). |
| O3 | OA (scarce) | Apple push key type | environment-specific team key; topic-specific key | Separate sandbox and production keys. Apple allows at most two environment-specific team keys per environment; topic-specific keys allow more. Creating a key consumes quota. |
| O4 | OA (hard to reverse) | Firebase project scope | one project for both Android packages; separate projects | One project, both packages registered, with `restricted_package_name` per message. A project ID is permanent once created. |
| O5 | OA (outward) | Relay source visibility | public repository; private repository | Public is reasonable: its code has no secrets. Publishing is outward-facing. |
| O6 | OA (outward) | Privacy declarations | update before the first external push build | Required before any external build that enables push, covering provider processing, the relay learning `iid` (A6) and the `C` pseudonym. |

Also owner or account actions that are not O-items: generating the HPKE kid keypairs (custody is
effectively irreversible once a distributed build ships the public key), App ID Push and Time
Sensitive capabilities, any relay domain or DNS, and the owner-set relay global budget.

Signed APNs and Time Sensitive capabilities are verified only on later, owner-requested, authorized
builds. The website, store listings and beta tracks stay unchanged by this proposal. The owner's
existing authorization of the priority approval feature (Time Sensitive, high Android channel, user
settings prevail) is preserved. The provider infrastructure above still needs the owner's explicit
choice.

## Root freeze

Root freezes the amended design text after full root reading of the 1,335-line bounded amendment,
the 149-line precision delta, and the independent targeted C1–C3 **ACCEPT_FOR_ROOT_FREEZE**.
The direction tables above record review history; the following is the authoritative decision.

- D1 P-256/HKDF-SHA256/AES-128-GCM HPKE base mode; D2 instance-key reuse with the distinct
  transcript and prefix-freeness tests; D3 host configuration only; D4 exclude run completion;
  D5 per-registration/profile collapse with one FCM collapse key.
- D6 10 s and 30/h; D7 60/900/330 s; D8 2 pre-provider retries (1/4 s, ±20%), 5/10 s timeouts,
  1 KiB response, breaker 3 failures/60 s/one probe, close 1 s; D9 1 h/14 d seal, refresh under
  4 d, retained lifetime at most 30 d; D10 4 KiB/2048 B/1024 B; D11 6/30/30 per minute;
  D12 64 queue/2 concurrent; D13 4 recipients; D14 256 hints, 60 s settle margin, 60 min maximum;
  D15 literal generic text; D16 default FCM proxy subject to physical measurement.
- D17 per-iid/destination/pair/source limits 120/60/30/600 per hour and verification 20/s are
  frozen. The global budget is an owner deployment choice; 600 R2/6,000 R1 remain proposals.
  D18 120 s skew, nonce retention through ts+120 s, 16,384 cache with defensive-full refusal.
- D19 all eligible owner devices with exact row/family/visibility; D20 both approval surfaces;
  D21 unused; D22 require availability; D23 allowlisted owner R2 only, maximum 8 iids. Public R1
  open enrollment remains inactive until explicit owner acceptance of abuse residuals.
- D24 64 active; D25 8/device and 1,024 total retained; D26 256 slots; D27 exactly one relay
  replica; D28 option (c), 256 non-REVOKED generation rows with terminal guard and revoked purge.
- Precision M1–M7 from closure review are incorporated: named post-commit call sites, exception-
  agnostic cause preservation, key read before transaction, no key-file mode mutation, generation
  capacity visibility, retirement excess wording, and in-transaction device/family liveness.
- T003 approval inputs I-1/I-2/I-6 and T010/T011 contract changes remain prerequisite work.
  No operational approval, push delivery, crypto dependency or provider qualification is claimed.
- O1–O6, provider keys/capabilities, HPKE key custody, DNS and global deployment budgets remain
  pending. This freeze authorizes no provisioning, billing, store submission or public activation.

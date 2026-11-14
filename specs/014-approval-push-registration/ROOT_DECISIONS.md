# Root decisions (design frozen 2026-10-02; owner choices pending)


**Current contract review status (2026-10-02):** The clock mechanism, optional pin grammar and N3–N6 were accepted by the prior focused review. The independent D1/D2/D3 sentence review accepted the capacity/retention qualifications, per-`(app, env)` APNs connections and seal-expiry wording. Root resolved its remaining editorial status finding M1 by dating the pre-review statements below. This is contract-text acceptance only. Source, causal tests/vectors, interoperability, provider/device/deployment/release and owner choices O1–O6 remain pending. No task checkbox or security mechanism changed.

The direction tables and proposal columns below preserve the review history. The **Root freeze**
section is authoritative for accepted design choices and bounds. The owner items O1–O6 and global
deployment budgets remain pending. Numbers carry no latency, entropy or delivery guarantee. The
**Root interoperability amendment of 2026-10-02**, at the end of this file, is authoritative for the
byte-level and result-code choices it names and supersedes any earlier line that conflicts; the
review history and the freeze record above it stay as history. The **Root review clarifications of
2026-10-02**, after the amendment section, are likewise authoritative for F1 to F7 and supersede any
conflicting earlier line. The **Root clock and pin delta of 2026-10-02**, at the end of this file, is
authoritative for R-F1a, R-PIN and N3 to N6; before its review it was new and unreviewed. The clock-count repair of 2026-10-02 followed a focused review of that delta: the review accepted the mechanism, the pins and N3 to N6, and required text repairs for the 4,800-nonce and 240 s qualification under clock steps (its finding D1) and for one APNs connection granularity per allowed `(app, env)` pair (D2), with editorial wording (D3). At that checkpoint, the repaired capacity and connection sentences awaited a focused check of those sentences only. That check has now accepted D1/D2/D3 as contract text; implementation and verification remain pending.

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
| C4 | Record the sybil suppression (at least `⌈destination ceiling / pair cap⌉` `iid`s) and public global and verify exhaustion (A17). Keep the destination spam ceiling; public mode stays inactive and owner-pending. Per-key caps before the global count; only admitted requests charge it. The replay cache is bounded by 4,800 and a full cache is defensive. (Qualified by the 2026-10-02 clock-count repair: this bound and the 240 s retention hold only under normal clock progress; clock stalls or backward steps can exceed 4,800 and reach the 16,384 cap, `503` with no eviction. See relay CLK-1.) | spec PN-REL-3/6; plan §6.5; analysis A14, A17 |
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
| D3 | R | Relay configuration source | (a) host config only, no default; (b) a shipped default URL constant plus a host override | (a): `push.relay_url`, `push.relay_audience`, `push.relay_kids`, optional SPKI pins (the setting `push.relay_spki_pins` and its grammar are fixed by R-PIN at the end of this file). Repository visibility is O5. |
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
| D18 | R | Relay replay window and cache | equal to HMP `CLOCK_SKEW_S` (120 s); each nonce kept until `ts + 120 s`; cache 16,384 entries; full cache refuses with `503 unavailable` | Existing skew policy; never evict an unexpired nonce. At the 20/s verify budget at most 4,800 nonces are live, so a full cache is a defensive path. (Qualified by the 2026-10-02 clock-count repair: this bound and the 240 s retention hold only under normal clock progress; clock stalls or backward steps can exceed 4,800 and reach the 16,384 cap, `503` with no eviction. See relay CLK-1.) |
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
- T003 approval inputs I-1/I-2/I-6 are source accepted in spec 015 `6a139ba`; section 10 records
  I-3/I-4 and the I-5 lifecycle boundary. T010/T011 contract changes remain prerequisite work.
  No operational approval, push delivery, crypto dependency or provider qualification is claimed.
- O1–O6, provider keys/capabilities, HPKE key custody, DNS and global deployment budgets remain
  pending. This freeze authorizes no provisioning, billing, store submission or public activation.

## Contract section allocation — 2026-10-02

Local media already reserves HMP v1 section 7e in spec 011. Root allocates section 7f to
push registration and hint resolution; this changes numbering only, not the frozen protocol
or owner choices. T010 follows that allocation. The old branch's two synthetic hostile
fixture literals are now assembled exactly as in accepted `6a139ba`; runtime canaries and
assertions are unchanged, with no privacy suppression added.

## Root interoperability amendment — 2026-10-02 (authoritative)

Architecture direction for spec 014 **contract text only**: `HMP_V1.md` §7f,
`HMP_PUSH_RELAY_V1.md`, `spec.md`, `plan.md` and `tasks.md` conformance obligations. Independent
contract review remains required. No source, key, relay, deployment, provider action or owner choice
is authorized, and nothing here is implementation, vector, interoperability, provider or device
evidence. The labels **B1 to B6 and P1 to P3 belong to this amendment**; they are unrelated to the
earlier review items B1 to B4 in the history table above. B1 to B6 address the six former
relay-contract `HMP_CONTRACT_GAP` items (labels GAP-1 to GAP-6, since removed from the relay contract) and, through B5,
HMP's former `GAP-PN-1`; those removed labels are distinct from `HMP_V1.md`'s own live `GAP-1` and `GAP-2` rules, which
this amendment does not address. The
cryptographic and canonicalization primitives come from RFC 9180 (§§6.1, 7.1, 7.1.1, 7.1.4, 7.2, 7.3)
and RFC 8785 (§§3.1, 3.2.1 to 3.2.4); the protocol choices below are project architecture decisions.

| ID | Kind | Decision |
|---|---|---|
| **B1** (GAP-1) | R | `R` and `K` enter the relay signature transcript as raw decoded 32-byte values and `C` as raw decoded 24 bytes. Their wire forms stay canonical b64u of 43, 43 and 32 characters. `SHA-256(S)` and `SHA-256(R)` are over raw decoded bytes. `ROUTE` fields `iid`, `device_id`, `family_id` are UTF-8, `H` and `G` u64, `salt` raw 32. The `COLLAPSE` scope is the exact canonical profile locator as UTF-8, without normalization; `C` is the first 32 characters of `b64u(HMAC)`, which decode to 24 bytes. The base TR framing is unchanged. `iid` is derived from the parsed supplied SPKI **before** the signature transcript is built; a wire `iid` is never trusted, and the derivation is not deferred until after verification. |
| **B2** (GAP-2) | R | Seal plaintext is RFC 8785 JCS, UTF-8 without BOM, at most 1,024 bytes, with the existing exact member set, in a restricted domain: fixed ASCII member names; all values strings except `v` = 1 and `not_after`, which are nonnegative JSON integers below 2^53 (never boolean, float or exponent lexemes). Reject duplicate names, extra or missing fields, invalid Unicode and lone surrogates, and any bytes unequal to the JCS reserialization of the validated object. No Unicode normalization. Canonical order for APNs: `addr`, `addr_kind`, `app`, `env`, `iid`, `n`, `not_after`, `platform`, `v`; FCM the same without `env`. No unchecked test vector is invented; the implementation generates and independently reviews HMP vectors. |
| **B3** (GAP-3) | R | `sealed = b64u(enc ‖ ct)`; `enc` exactly 65 bytes (uncompressed SEC1 P-256 point); `ct` is the AES-128-GCM output including its 16-byte tag; no version, key or length prefix inside the blob. `kid` and the suite come from the existing outer fields and the closed configured key mapping, with no negotiation. A nonempty plaintext gives a decoded size of 82 to 1,105 bytes inclusive (65 + 16 + 1 to 1,024), inside the 2,048-byte ceiling of D10. HMP checks only canonical b64u and these bounds and never opens the seal. The relay performs RFC 9180 §7.1.4 input and output validation, authenticates and opens, then checks the exact schema and JCS form; failure is `422 sealed_invalid`. An invalid decoded length is `400 bad_request` at the relay's shape check; a malformed point, tag or plaintext is `422`. No homemade curve validation and no deterministic production ephemeral keys. |
| **B4** (GAP-4) | R | `kid`: ASCII full match of `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`. `aud`: the same with `{0,127}`. Case-sensitive exact comparison, no URL semantics, whitespace, Unicode normalization or trimming. Host configuration, HMP registration and status, and relay wire parsing agree. The grammar defines no real key, audience, endpoint or account. The Android `channel_id` and the one global FCM `collapse_key` are both the fixed literal `hmp_approval_v1`. The channel's user-visible name and localization are separate, and settings prevail. No per-bot FCM `collapse_key`. |
| **B5** (GAP-5, GAP-PN-1) | R | `DELETE /push/registration` does not require push enabled, a configured relay, a live kid, available approval members or an effective direct-send flag. It keeps the bearer, instance, effective-owner, bucket, body, CAS, transactional `ACTIVE`-device and live-family checks, terminal revocation and the capacity rules, and makes no Hermes, relay or provider call. It never resurrects a row, bypasses authentication or claims deletion before a `200`. A disabled delivery lane must not prevent removal of an existing registration. `GET` remains readable while unavailable. The resolver keeps its frozen, independent gate order. |
| **B6** (GAP-6) | R | A malformed request, shape, SPKI, signature encoding, identifier or `ttl_s` is `400 bad_request` before provider work. `ttl_s` is a JSON integer 60 to 900 inclusive; `ts` is a nonnegative JSON integer below 2^53. A well-formed but invalid signature, a mismatched audience, an out-of-skew timestamp, an unknown kid or an allowlist miss is `401 unauthorized`. An HPKE open, point, plaintext, JCS or binding failure is `422 sealed_invalid`. `409 replayed`, `429 rate_limited` and `503 unavailable` keep their mappings. After a provider attempt every result that is not accepted or a definitive gone is `502 provider_unavailable`, including `BadDeviceToken` and the forbidden, topic and payload refusals, with no automatic retry. A registration is not retired on those refusals. No new response code. |
| **P1** | R | No provider before step 17 of the relay order; step 16 only checks hourly limits. The nonce seen/full check and the reservation are atomic on the single replica, before decrypt or provider work; the reservation lasts until `ts + 120` and is not removed early when a later check refuses. The restart replay residual remains and no durable cache is added. Concurrent identical requests cannot both dispatch. |
| **P2** | R | Pre-verification per-source and global-verify admission is separate from post-seal hourly admission. The pre-verification pair is checked atomically and both are charged immediately, only if both admit, even when a later signature or seal check fails. The global verify budget allows at most 20 checks in any rolling 1-second interval with no additional burst, which makes the existing bound of at most 4,800 live nonces valid with retention `[receipt, ts + 120)` and purge when `expiry ≤ now`. (Qualified by the 2026-10-02 clock-count repair: this bound and the 240 s retention hold only under normal clock progress; clock stalls or backward steps can exceed 4,800 and reach the 16,384 cap, `503` with no eviction. See relay CLK-1.) The hourly `iid`, destination, pair and global counters are checked atomically and charged only if every one admits. CPU charging is never deferred to provider admission. |
| **P3** | R | `202` is provider acceptance and `410` is the only definitive provider result; `502` is never definitive. No provider body or text crosses HMP logs. All existing residuals and all owner choices stay pending. The six gaps are resolved without conflating independent review with implementation or device evidence. **(Superseded as history by N6: "six gaps resolved" is not a current claim; the removed relay-contract labels are distinct from the live `GAP-1` and `GAP-2` of HMP v1 §12, which stay open.)** |

**Consequences recorded by the authors of the text (for root to confirm).**

- The half-open past side of the relay skew window (`now < ts + 120`, with `ts ≤ now + 120`) is
  written as the consequence of P1/P2's nonce interval `[receipt, ts + 120)`: a request is never
  accepted for skew after its nonce was purged. It is not a separate choice. **(Superseded as history by
  F1 for the instant handling and by R-F1a for the clock condition: that sentence holds only with the
  effective, non-decreasing acceptance instant of the clock and pin delta below.)**
- The HMP `PUT` range for `sealed` is now 82 to 1,105 decoded bytes (B3), not "at most 2,048".
  2,048 stays the frozen ceiling of D10 and the earlier freeze text above is history.
- A `relay_kids` entry or audience that does not match B4 is treated as malformed, so push is off,
  extending the existing "missing, malformed or non-HTTPS value means push is off" rule.
- Two residuals are added to HMP v1 §14: RES-26 (relay restart replay window, P1) and RES-27
  (provider refusals do not retire a registration, B6).
- HMP-specific signature, JCS and seal known-answer vectors are **implementation follow-up** (T025,
  T030, T043) from an independent generator with independent review. They are not blocked by any
  open contract gap, and none is included or claimed here.

**Still pending and unchanged.** O1 to O6, provider keys and capabilities, HPKE key custody, DNS, the
global relay budget `B`, public R1 activation, physical-device and provider evidence (`PLATFORM_GAP`),
cross-channel coverage research (T005), and every residual of HMP v1 §14 (RES-13 to RES-27). No task
box is ticked by this amendment.

## Root review clarifications — 2026-10-02 (authoritative)

Contract-text clarifications after an independent scoped review of an earlier eight-document
candidate (`HMP_V1.md` §7f and its additions, `HMP_PUSH_RELAY_V1.md`, `spec.md`, `plan.md`, `tasks.md`,
this file, the constitution text and the closed-surface note), which accepted that candidate with
conditions. They preserve B1 to B6, P1 to P3 and every authority and security requirement above. They
authorize no source, key, relay, deployment, provider action or owner choice. The labels F1 to F7 belong
to this section. A later independent review accepted the other clauses of the clarified text and required two
source gates (the relay clock source and the optional pin grammar); they are written in the clock and pin delta at
the end of this file, which was new and unreviewed before its focused review. Nothing here is implementation, vector, interoperability,
provider or device evidence. No box is ticked.

| ID | Kind | Decision | Where applied |
|---|---|---|---|
| **F1** | R | Inside the relay's atomic nonce check/full/reserve section, obtain one current `now` and re-check both skew inequalities (`ts ≤ now + 120` and `now < ts + 120`); then purge, check and reserve with that same instant. A failed atomic re-check is `401`, with no new nonce and no provider work. External step 6 stays an early screen; nothing relies on an instant captured before another worker purged. Concurrent and boundary conformance is required, including a request that passes the early screen before expiry and reaches the atomic section after it. The restart replay residual (RES-26) stays. This supersedes the instant handling implied by the earlier consequence note on the half-open past side. | relay §5 steps 6 and 7, VER-1, §12, §14; spec PN-REL-3; plan §6.5, §8.2; tasks T030 |
| **F2** | R | Push-off never destructively expires registrations on kid liveness. A well-formed relay configuration is independent of availability, but `GET` and the purge apply removed-kid expiry only while push is available (PN-AV for at least one member). While push is off for any reason they keep otherwise valid active rows inert; absolute expiry, revocation, family, hash and retained-row purge operate unchanged. An invalid or missing kid or audience configuration is `relay_unconfigured`, never an empty live-key list, and one malformed configured kid closes the whole push configuration. `GET` omits `relay_kids` unless available. `why` precedence: `push.enabled` not exactly `true` is `push_disabled`; then a missing, malformed or non-HTTPS relay configuration is `relay_unconfigured`; then closed approvals or direct send is `approvals_unavailable`. `PUT` still validates body grammar and size independent of availability; after those checks it evaluates availability first (`503` with the mapped `why`), then live-kid membership (`400` if absent), then replay and CAS. A lexically malformed supplied kid stays `400` even while off; a removed but well-formed supplied kid is `503` while off and `400` while available. `DELETE` stays wholly independent (B5). | HMP v1 §7f PN-AV, PN-GO table, PN-REG-1, PN-REG-2, PN-ISS-5, PN-BND, ERR-2b; spec PN-AV-4, PN-REG-1, PN-REG-2, PN-ISS-5, PN-BND, PN-REV; plan §5.1, §8.1; tasks T020, T022 |
| **F3** | R | The removed relay-contract labels GAP-1 to GAP-6 are distinct from HMP v1's still-live `GAP-1` and `GAP-2` (§12). B1 to B6 are cited with that qualification, and no broad gap-resolution claim is made. | HMP v1 §7f header, relay header and §13.1, spec header, tasks, this file |
| **F4** | R | The relay signature is a strict minimal ASN.1 DER `SEQUENCE` of exactly two positive `INTEGER`s, each in `1` to `n − 1` (`n` the P-256 group order), with no trailing bytes. A non-minimal, zero, negative or out-of-range value is `400`; a syntactically valid, in-range, non-verifying pair is `401`. Low-S and high-S are both valid (TR-13). No homemade verifier. Vectors are pending. | relay SIG-1, §5 steps 1 and 3, §14; spec PN-REL-2; plan §8.2; tasks T025, T030 |
| **F5** | R | The APNs environment policy is per configured allowlist pair `(app, env)`, not one global mode. A relay may allow sandbox and production pairs, each with a separate provider connection. The signed and sealed `env` must equal each other and the selected allowed pair; there is no environment fallback. The first allowlist check (the `iid` allowlist, step 10) stays `401`, and the later seal bindings (app, `env`) stay `422`. No real account is configured. | relay CF-2, §5 step 15, ENV-1, §8.1, §9; spec PN-REL-3; plan §6.1, §6.5; tasks T030, T031 |
| **F6** | R | The relay's four post-seal counters (per `iid`, per destination, per `(destination, iid)`, global `B`) use rolling 3,600-second windows, charged atomically all-admit or none, so a fixed-window boundary allows no double burst. No new cap value and no deployment choice. HMP's per-device dispatch rate window (D6, PN-DSP-7) stays its own frozen policy and is not changed. Boundary conformance is pending. | relay §5 step 16, LIM-1, LIM-3, §9, §12, §14; spec PN-REL-3, PN-REL-6; plan §6.5; tasks T030 |
| **F7** | R | The stale `analysis.md` status header now states the contract-candidate and bounded-review status. The nonexistent "constitution VIII" citation in `server-modules.md` is removed; the reference-only and rewrite/review requirements remain unchanged. Status lines of the candidate documents said that the clarified text awaited independent review (superseded by the status in the clock and pin delta below) and make no source or interoperability claim. Unrelated history is not rewritten. | `analysis.md` header, `server-modules.md`, status lines |

**Consequences confirmed by root (2026-10-02; contract text only).**

- While push is off, a row whose kid was removed stays active and keeps counting against the D24
  active capacity (and is not a retained row, so D25 is unaffected; corrected by N5) until push is available again
  or `expires_at` (F2 as written); no new residual was added.
- An explicitly empty `relay_kids` list is `relay_unconfigured`, not an available relay with no live keys.
  Malformed configured optional SPKI pins also close configuration as `relay_unconfigured`; absent
  optional pins are allowed. Malformed pins are never ignored or replaced by a trust fallback. (The pin setting,
  grammar and trust semantics are now written by R-PIN below.)
- F6 covers only the four post-seal counters. (R-F1a below now also makes the per-source limit a rolling
  3,600-second window on a monotonic clock; no cap value changes.)
- The inapplicable constitution citation on the reference-only spike sentence is removed; the
  reference-only and rewrite/review requirements remain.
- The `iid` allowlist (step 10, `401`) and the `(app, env)` pair checks (steps 12 and 15, `422`) are read as the
  "first allowlist check" and "later seal binding" of F5.

**Still pending and unchanged.** Focused independent review of the clock and pin delta below; O1 to O6, provider keys and capabilities,
HPKE key custody, DNS, the global relay budget `B`, public R1 activation, HMP-specific signature, JCS, seal, DER and
boundary vectors, physical-device and provider evidence, cross-channel coverage research (T005) and every residual of
HMP v1 §14 (RES-13 to RES-27).

## Root clock and pin delta — 2026-10-02 (authoritative; pre-review status recorded below)

Bounded root decisions after the independent review of the clarified candidate (`HMP_V1.md` §7f,
`HMP_PUSH_RELAY_V1.md`, `spec.md`, `plan.md`, `tasks.md`, this file, `analysis.md`, `server-modules.md`, constitution
unchanged). That review accepted the other clauses of the clarified text and required two source gates; this section
writes them. Pre-review history: **Written is not accepted.** The text below is new and has not been independently reviewed; a focused
independent sentence review is pending. The clock-count repair of 2026-10-02 followed a focused review of that delta: the review accepted the mechanism, the pins and N3 to N6, and required text repairs for the 4,800-nonce and 240 s qualification under clock steps (its finding D1) and for one APNs connection granularity per allowed `(app, env)` pair (D2), with editorial wording (D3). At that checkpoint, the repaired capacity and connection sentences awaited a focused check of those sentences only. That check has now accepted D1/D2/D3 as contract text; implementation and verification remain pending. It authorizes no source, vector, key, relay, deployment, provider action,
device test or owner choice, and it ticks no box. Names, counts and the leaf-certificate choice are root's.

| ID | Kind | Decision | Where applied |
|---|---|---|---|
| **R-F1a** | R | Inside the one atomic nonce admission section the relay chooses the effective Unix acceptance time `now = max(raw_wall_now, last_now)` and updates the in-memory `last_now`. The re-check of both skew bounds, the purge, the seen check, the capacity check and the reserve use that instant. The early step 6 may use raw wall time (it only rejects). Step 14 seal expiry uses the same effective instant and never a later raw backward clock. The rolling windows of steps 2 and 16 use monotonic elapsed time, including the per-source 600 per rolling 3,600 s. A backward clock cannot reopen a purged nonce within one replica lifetime. While `last_now` is ahead of the raw wall clock (a forward step or a backward correction) the relay can refuse availability until wall time catches up or the operator restarts; there is no automatic restart or reserve reset. The 240 s retention and 4,800 live bound hold only under normal clock progress; clock stalls or backward steps can prolong retention, exceed 4,800, and with repeated steps reach 16,384, refusing `503` with no eviction, no early release and no new replay; no other progression, TTL or reset is stated. `last_now` is memory only; a cold restart or memory rollback stays the existing VER-1a and RES-26 residual, with its timestamp bound stated in relay-clock time. No nonce persistence and no restart immunity are claimed. The caps, the nonce hold rule, the framing and the no-authority payload are unchanged. Causal clock-rollback and forward-jump tests and vectors are pending; none exists | relay §5 steps 2, 6, 7, 14, 16, VER-1, VER-1a, CLK-1, LIM-1, LIM-3, §9, §12, §13.5, §14; HMP v1 §7f, RES-26; spec PN-REL-3, PN-REL-6; plan §6.1, §6.5, §8.2; tasks T030 |
| **R-PIN** | R | Host setting `push.relay_spki_pins`. Omitted means no optional pin. If configured, it is an exact nonempty list of 1 to 8 distinct canonical unpadded base64url SHA-256 digests of a DER `SubjectPublicKeyInfo`: 43 ASCII characters that decode to 32 bytes and re-encode identically. An explicit `None`, an empty list, a non-list, a duplicate or a bad entry is malformed and gives `relay_unconfigured`; omission and `None`/empty are distinct. Standard TLS trust-store chain validation and host-name validation are always required. Only the **leaf** certificate SPKI is pinned; a pin is an additional constraint and never a replacement trust anchor, self-signed bypass or chain match, and the leaf must match one configured digest. A mismatch occurs before any HTTP request or body write and is retried under the same bounded RES-C rule as any other pre-write TLS failure, with no trust fallback. The setting holds only public digests, no secrets. There is no environment-variable fallback | relay CF-1, CF-1a, REQ-2, §12, §13.5, §14; HMP v1 §7f PN-AV; spec PN-AV-2, PN-AV-4, PN-REL-1; plan §6.1, §8.1; tasks T022, T025 |
| **N3** | R | The relay's APNs connections are separate for each allowed `(app, env)` pair. Credential and signing-key provisioning belongs to the pending owner choice O3 and is not decided here. There is no environment fallback. This narrows the earlier "connection and credential" wording | relay §8.1, ENV-1, §13.5; plan §6.5; tasks T031 |
| **N4** | R | The settings list includes the optional pins (spec PN-AV-2), and the all-off purge reasons of task T020 include an empty kid list and malformed pins | HMP v1 §7f PN-AV, PN-BND; spec PN-AV-2, PN-BND; plan §8.1; tasks T020 |
| **N5** | R | An inert active row counts against the D24 active capacity, not the D25 retained capacity. No capacity invariant changes | HMP v1 §7f PN-BND; spec PN-BND; plan §8.1; tasks T020; this file |
| **N6** | R | The earlier "the six gaps are resolved" wording (P3 row) and the consequence note that a request "is never accepted for skew after its nonce was purged" are superseded history. Core `GAP-1` and `GAP-2` of HMP v1 §12 remain open and untouched | this file |

**Consequences recorded by the authors of the text (for root to confirm).**

- With R-F1a, `401` at step 7 while `last_now` is ahead of the raw clock (a forward step or a backward correction) and a `422`
  at step 14 for a seal whose `not_after` is at or before the effective instant (below `ts + 120` for a request that passed
  step 7) are availability refusals only. HMP already does not retry `401` or `422` (RES-C) and,
  under RES-E, marks a registration `expired` only on a `422`; the phone recovers by sealing afresh. No HMP route,
  code or retry rule changed.
- The restart residual RES-26 gains only the statement that its bound is in relay-clock time and that `last_now`
  resets with the cache. It is not closed.
- A mismatching pin is a pre-write TLS failure and is retried under RES-C with the other pre-write failures; the
  breaker and timeouts (D8) are unchanged.
- The leaf-only pin choice and the 1 to 8 count are root's and are taken verbatim.

**Still pending and unchanged.** Focused independent sentence review of this delta; O1 to O6 (including APNs
credential provisioning under O3), provider keys and capabilities, HPKE key custody, DNS, the global relay budget `B`,
public R1 activation, HMP-specific signature, JCS, seal, DER, clock and boundary vectors, physical-device and provider
evidence, cross-channel coverage research (T005) and every residual of HMP v1 §14 (RES-13 to RES-27).

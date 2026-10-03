# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

## Current development checkpoint (2026-10-02)

The table below preserves earlier release/source history. Current development
follows the owner's minimum-version policy; historical fingerprints are sampled
evidence, not runtime feature allowlists.

Host-local image descriptors ([draft #79](https://github.com/MahdiHedhli/hermes-hmp/pull/79))
and authenticated fetch ([draft #80](https://github.com/MahdiHedhli/hermes-hmp/pull/80),
source `c9a47b7`, status head `d924f28`) are independently source-reviewed. Fetch
clean locked CI passed 3613 cases with 16 native-dependent skips and one existing
warning; root focused tests passed 162, and the reviewer reproduced 162 plus 308
startup/layout cases. Nine causal guard-removal mutants failed targeted assertions.
The synthetic four-fetch sample passed provisional memory limits, including late
cancelled workers retaining permits. This does not establish native serving/T12,
Linux serving, phone decoding or device/release acceptance. No local-media live
flag, host installation or phone build changed. Public CDN rendering remains
physically confirmed; host-local MEDIA text on the installed phone is unchanged.

After three failed attempts, the independently reviewed probe repair completed
one isolated native phase/service sample. Both Bot Chat and Phone returned exact
8 MiB images and passed access, kind, changed-session and corruption refusals.
Four actual fetch workers passed active and cancelled-lease samples within the
unchanged memory ceilings. This advances native worker evidence; native HTTP,
full T12, Linux, phone loading and release acceptance remain open. See the
[native sample](docs/research/local-media-native-phase-service-2026-10-02.md) and
[probe diagnosis](NOUS_GATEWAY_OBSERVATIONS.md#native-fetch-probe-diagnosis-2026-10-02).

The mobile [spec 029 policy amendment](https://github.com/MahdiHedhli/HermesBotMobile/commit/57fb3394af8c61026074abf8ebe3387942d67a75)
is independently documentation-reviewed and published. It aligns client planning
with minimum-version/API admission while preserving authorization and image limits.
The combined app source baseline is independently accepted in
[mobile draft #68](https://github.com/MahdiHedhli/HermesBotMobile/pull/68).
Phone image deployment remains open. The [v2 Phone media contract](https://github.com/MahdiHedhli/HermesBotMobile/blob/4fa4764bbad7799850755ce4e7262b2fc38b0b28/specs/029-host-local-images/phone-media-contract.md)
has independent architecture acceptance. The controller/read ports and shared
card/viewer prerequisites now have bounded independent source acceptance in
[mobile draft #70](https://github.com/MahdiHedhli/HermesBotMobile/pull/70), `ba0f619`.
Independent media activity/applied-read proof preserve send fences; original
permits join actual refresh/fetch/decode work. Root passed 218 focused client,
seven dev-support, 12 logging and 112 card/viewer cases; independent component
reviews passed overlapping causal cases. Phone screen/owned-route wiring,
stable final budget and actual shared-flight/fresh-row retry integration now
have independent source-only acceptance at mobile `1a4641e`: root 276 focused
passes and independent 122 overlapping cases, exact eight source pins and clean
analysis. Hosted CI on accepted Phone head `11cbf29` now passes; physical delivery remains open. The following failed run is historical: hosted mobile run `37060192148` failed a
legacy immediate-permit-release test and the inherited late-TLS test. Root's
corrected legacy test and its full 42-case binding suite pass locally; that local check did not establish hosted success; the later green run is recorded below. Handoff SDK paths were sanitized at `19a5ba6`; hosted security hygiene passes
in run `37061780872`, closing the current-document privacy finding. Historical
Git bytes remain in public history.
No new upstream Hermes API is required.
The mobile MEDIA-C1/F1 source and exact
registry repair are independently accepted in [draft #69](https://github.com/MahdiHedhli/HermesBotMobile/pull/69):
219 focused passes and local serial CI pass (app 925 / 3 skips). This repairs the
demonstrated client accounting/API settlement mechanism; installed devices and
physical/native/global memory/release gates remain unchanged. See [current mobile lifetime evidence](NOUS_GATEWAY_OBSERVATIONS.md#mobile-public-image-lifetime-2026-10-02).

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Preview | Bot Chat sends | Explicit owner gate, per-bot authorization, freshness checks and retry-safe handling. Current development follows the minimum-version policy and attempts the required APIs on later or unknown builds; an untested fingerprint alone does not disable the feature. Actual API failures remain explicit. |
| Draft; not enabled live | Approvals and choices | Minimum-version candidate `150bd0f` is independently source-reviewed; two prepared native samples passed 13 cases each. Corrected exact-source package is prepared. Live activation and physical card/answer acceptance remain open; earlier setup failures are historical evidence below. |
| Source registration/resolver/dispatcher/HTTPS client reviewed; interoperability and delivery pending | Priority approval notifications | Issuer `9611b5d`, storage `d41f5e7` and live configuration/listener `22e92b1` and registration routes/writers `71385bb` plus hint resolver/map `ef11d01` and injected-port dispatcher `e6e20a6` are independently source-reviewed, with exact hosted CI passing. HTTPS client/factory `fcd10e0` is independently source-reviewed, with exact hosted CI passing. Remote relay/seal interoperability, relay/app integration, provisioning and physical delivery remain open. No notification is delivered by this source slice. |
| Owner dogfood; source follow-up reviewed | Linked chat images | Owner confirmed public-CDN rendering. Accepted public-image settlement repair `16c2095` and Phone media wiring `11cbf29` passed hosted CI; integrated Play source `8671061` also passed hosted CI. Native allocation, host-local HTTP serving and device/release evidence remain open. No new installed image capability is claimed. |
| Planning | Phone photo/file attachments | Root reproduced native adapter primitives in isolated discovery tests on an archive, not a Git attestation (73 checks, 30 focused tests, 315 fixture and CI-tool tests together; no full CI gate claimed); the complete upload, busy-handler, admission and read-back flow remains unqualified. Canonical Desktop-owned multimodal admission and reusable authorized media history remain upstream contract gaps. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).


## Approval push HTTPS client checkpoint (2026-10-03)

[Draft PR #88](https://github.com/MahdiHedhli/hermes-hmp/pull/88), source
`fcd10e0370be185a445f25a1f77ce1e6b7a1d62b`, adds the signed HTTPS client
and production adapter factory. Independent source review accepted the client
and its integrated independent synthetic vectors: all 52 frozen pins matched,
22 fixed-vector/DER reference cases passed, and a scratch raw-route framing
mutation failed. Root passed 277 focused and 2,562 full tests, with 16 existing
skips and one existing warning. Both exact-source hosted CI runs `37089728685` and `37089727146` passed.

The client requires standard certificate-chain and hostname validation; optional
leaf SPKI pins are additional constraints checked before HTTP request bytes. It
ignores proxy environment variables, refuses redirects, caps responses, signs
raw fields and distinguishes certain pre-write failure from post-write timeout
and ambiguous outcomes. Local HTTPS tests establish this source behavior. The
DER cases verify vetted primitive/reference classifications, not the separate
remote relay's verifier.

This supersedes the dispatcher checkpoint's pending-client source status only.
Remote relay/seal interoperability, app registration/taps, provider provisioning,
physical notification delivery and release remain unverified. No live host,
app, flag, grant, credential, provider or deployment changed. Push remains a
navigation hint and never authorizes an approval answer.

## Approval push dispatcher checkpoint (2026-10-03)

[Draft PR #87](https://github.com/MahdiHedhli/hermes-hmp/pull/87), source
`e6e20a61ddcaf44d76c73e0a1ff35688e8e27e96`, adds the bounded insertion
worker and listener lifecycle through an injected relay port. Independent v2
review accepted all 48 frozen source pins after resolving v1's recipient-order
defect: registration insertion order now remains correct when wall-clock
timestamps tie or move backwards. Focused verification passed 380 tests; the
full suite passed 2,486 tests with 16 existing skips and one existing warning.
Both exact-source hosted CI runs passed.

The worker bounds queued callbacks, recipients, concurrent requests, coalescing
slots and per-device counters; repeats current owner, grant, family, generation,
visibility and live-setting checks; restricts retry to certain pre-write failures
and relay `unavailable`; and applies feedback only to the matching active
registration. Listener close detaches the observer, cancels work and bounds client
shutdown. These tests use a fake relay port and establish source behavior only.

**Still open:** the T025 HTTPS/signing client and production adapter factory are
under development and independent review, with no accepted transport or delivery
claim yet. Relay/seal interoperability, app registration/taps, provider setup,
physical delivery, owner deployment choices and release gates remain incomplete.
No live host, app, credential, grant or provider was changed by this checkpoint.
The generation-ceiling disposition remains open. Push carries navigation hints
and never authorizes an approval answer.

## Approval push hint resolver checkpoint (2026-10-02)

HMP [draft #86](https://github.com/MahdiHedhli/hermes-hmp/pull/86), source
`ef11d01cdcda6194169fd16e4a64cfc4a0379e07`, adds the authenticated,
owner-gated `POST /push/hints/resolve` route and a 256-entry listener-local
hint map. Resolution is navigation only. It rechecks exact device/family,
registration H/G/hash, DELETE fence, prompt generation, bot grant and current
visibility after async boundaries; hidden or stale rows disclose nothing.
Only recorded authoritative settlement can return `not_pending`. Immutable
row snapshots now carry actual settlement time for the 60-second margin;
this additive input changes neither native answer authority nor AP3 wire data.

Root passed 463 focused and 2,389 full configured tests (16 existing/native
skips, one existing warning). Independent review passed 694 overlapping cases,
matched all 41 frozen hashes and detected four causal mutants: hidden visibility,
non-authoritative settlement, settlement margin and live hint collision. Counts
are not additive. Both hosted runs `37085947620` and `37085944710` passed on
the exact commit; configured lint and privacy/log/surface checks passed.

This accepts the bounded T023 source slice. Production insertion dispatch and
hint minting (T024), HTTPS/signing relay transport (T025), relay/seal and app
integration, owner provisioning, physical delivery and release remain open.
T022 is incomplete at feature scope. No host, phone, provider or release changed;
there was no operational push delivery at this resolver checkpoint. The later
dispatcher checkpoint above supersedes its source-consumer status; transport and
delivery remain incomplete. The separate dispatcher work was unreviewed
and is not credited by this checkpoint. Earlier checkpoints below preserve the
scope and unfinished work at their own dates.

## Approval push registration route checkpoint (2026-10-02)

HMP [draft #85](https://github.com/MahdiHedhli/hermes-hmp/pull/85), source
`71385bb5a7b9352cec62fbe44c7e20e8e90f90a4`, adds authenticated GET/PUT/DELETE
registration routes to the reviewed runtime. Effective approval ownership is
separate from controls grants. Reads expose no route; writers validate bounded
opaque seals, recheck liveness after awaits, enforce replay/CAS and advance G
once atomically. DELETE works independently of delivery gates; failed DELETE database writes
fence the route in listener memory. Future resolver and dispatcher consumers
must enforce that fence. The shared COMMIT-failure rollback defect is repaired
in this isolated source; no deployed store incident is claimed.

Root passed 247 focused and 2,285 full configured tests (16 existing/native skips,
one existing warning); independent review passed 326 overlapping cases and
verified all 33 frozen hashes before and after. Scratch mutations caught owner,
transactional liveness, CAS, replay-hash, COMMIT rollback and DELETE-fence
regressions. Both hosted CI runs `37084551333` and `37084527827` passed on the
exact source commit. Configured lint and privacy/log/surface checks passed.

T022 remains incomplete at full feature scope: resolver/dispatch, hint lifecycle,
relay and app/native integration are not supplied by these routes. The G-ceiling
contract tension and volatile-fence restart residual remain open. No live host,
phone, provider, provisioning or release changed; push delivery is not available.

## Approval push configuration and listener checkpoint (2026-10-02)

HMP [draft #84](https://github.com/MahdiHedhli/hermes-hmp/pull/84), source
`22e92b168ede7b8398a970fd58b5722ea27cc673`, composes reviewed approval inputs
with issuer/storage and adds strict live host-only push availability. Invalid keys,
audience, relay URL or configured pins close the lane; omitted pins remain distinct
from malformed pins. Existing approval authority and minimum-version behavior stay
intact. Maintenance runs before listener open and hourly, reads the non-repairing key
once off-loop, and yields only between committed bounded transactions. Stop cancels
and awaits maintenance. Missing keys skip only hash expiry; other cleanup continues.

Independent v1 review found empty URL query/fragment delimiters could misroute a
future appended endpoint. The repaired v2 rejects the literal delimiters; six scratch
mutant failures demonstrate regression coverage. Root and reviewer each passed the
same 149 focused cases. Root's complete locked suite passed 2,210 cases, with 16
existing/native-dependent skips and one existing warning; configured Ruff passed.
All 26 frozen hashes matched after tests. Counts overlap. Hosted CI remains a
separate exact-commit check.

At this earlier runtime checkpoint, registration routes/writers were unfinished;
the newer route checkpoint above records their source acceptance. Resolver,
observer/dispatch, relay/app integration, provider provisioning and physical
delivery remain unfinished. T020/T021/T022 stay
open at feature scope, including the documented G-ceiling disposition. This checkpoint
proves source and isolated listener/SQLite/key behavior only; it enables no delivery,
live host activation, new phone build or release.

## Approval push storage source checkpoint (2026-10-02)

HMP [draft #83](https://github.com/MahdiHedhli/hermes-hmp/pull/83), source
`d41f5e7b271338bd2af88f1674c3115d3d9c237b`, builds on the reviewed issuer.
It adds additive schema 3 migration, bounded generation/capacity and purge helpers,
a terminal REVOKED setter guard, and separate post-commit retirement at five existing
HMP cause sites. Retirement advances G, wipes the sealed/request/body fields and
records a device-prefix-only audit before a later purge deletes revoked rows.
Cause cleanup does not purge historical backlogs. An independent source review
accepted the third revision after two concrete recovery/bounding repairs; the earlier
rejected receipts remain preserved. Root and reviewer each passed the same 63 focused
cases, including 15 actual SQLite disk-full cases (five causes by three cleanup write
stages). Independent post-COMMIT reads prove recovery retirement is durable before
deletion; a scratch mutation that bypassed the active-state deletion guard was caught.
Root's full locked suite passed 1,450 cases, with 10 existing skips and one existing
warning. These counts overlap and prove only the tested source slice.

The integer-ceiling contract disposition remains open: at G = 2^53 - 1 an increment
fails closed with 503 and leaves the row/G unchanged, while unconditional capacity
reclamation and G-advance wording are in tension at that boundary. No overflow,
wrap, reset or invariant waiver was introduced. At this storage checkpoint, listener
scheduling and live configuration were unfinished; the newer checkpoint above reviews
those source changes. Registration routes/writers, resolver, dispatch, relay/app
interoperability, owner provisioning and device/release evidence remain unfinished. T020/T021/T022 are not marked complete. No new phone build, host
activation or operational push delivery follows from this checkpoint.

## Approval push issuer source checkpoint (2026-10-02)

[Draft #82](https://github.com/MahdiHedhli/hermes-hmp/pull/82), source
`9611b5d8761f77edfa34d4d306d8aff29e934919`, implements pure route/collapse
derivation and hash validation, plus async read-only push access to `k_grace`.
It creates, repairs and logs no key or handle. Existing V1 transcript domains and
identity/token callers remain unchanged. Independent source and narrow module-tree
reviews accepted it: root/reviewer each passed the same 224 focused cases, two
independent vectors match, and seven causal scratch mutants fail. Root's complete
locked suite passed 1,387 cases with 10 existing skips and one existing warning;
counts overlap. Registration storage/routes and caller lifecycle checks are not
implemented here. No observer, outbound client, dispatch, native/device, provider
or release capability is enabled. The task audit in [draft #74](https://github.com/MahdiHedhli/hermes-hmp/pull/74)
at `ef94560` closes research/text only; owner choices remain pending.

## Source checkpoint — 2026-10-02, approval notification contract

[HMP draft PR #74](https://github.com/MahdiHedhli/hermes-hmp/pull/74) now publishes the independently accepted relay contract text at `92a719f`. It uses one atomic effective acceptance instant, `max(raw_wall_now, last_now)`, for nonce admission and seal bounds; monotonic time for rolling rate budgets; explicitly qualified normal-clock retention/capacity bounds; and separate APNs connections for each allowed `(app, env)` pair. Clock stalls/steps may prolong retention and fill the hard cache cap, which fails closed without evicting live nonces. Optional leaf pins constrain an otherwise valid TLS chain/hostname. This paragraph records contract acceptance only; the separate issuer checkpoint records its bounded source evidence. Registration/resolver/dispatch source, relay signature/seal vectors and interoperability, provider/device/deployment/release and owner choices remain pending. No push capability is enabled.

The related mobile image branches passed hosted CI: public repair `16c2095` in [37064933078](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37064933078), and accepted Phone image wiring plus the fixture repair `11cbf29` in [37065452665](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37065452665). The actual successful-TLS late-delivery cancellation case passed. The former fixture collision is resolved; native serving/allocation, physical device and release gates remain. No new deployed media or approval capability is claimed.

## Mobile reporting and approval coverage checkpoint

Mobile production reporting composition `8671061` is independently source-reviewed
and [exact-source CI passed](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37071200537).
A fixed report sender is wired; the receiver has synthetic receipt/private retention
evidence and matching privacy is published. Signed Free Android code 2 is prepared
and installed in an isolated emulator, but the Mac lock prevented an app walkthrough
or report acknowledgement. It is not uploaded or submitted. Final Data safety and
reviewer access remain unresolved. This does not alter private HMP transport or grants.

The [cross-surface approval census](docs/research/approval-cross-channel-source-census-2026-10-02.md)
finds existing Hermes observer hooks for CLI/shared gateway approvals. HMP's current
adapter/local-store path has no global consumer. Actual CLI loading and safe lifecycle
mapping need evidence; cron uses unattended policy, and clarify is separate. No
missing generic Hermes hook is inferred, and no broader push capability is enabled.

## Historical approval and renderer evidence

The following records preserve earlier checkpoints; current source status is above.

Exact-request approval/question routes and mobile cards are implemented on focused branches. Historical archive and independent Git-install parent matrices passed; the later combined candidate's run 4 failed (24 of 27 integration cases passed, three errored in setup before gateway start, no receipt; cause unconfirmed) and it remains unqualified. Scoped fixture-diagnostic tooling `d8b8b08` is in [draft PR #60](https://github.com/MahdiHedhli/hermes-hmp/pull/60). A new unchanged complete seven-stage/27-case attempt on `d8b8b08` and independent Git `8afaab3703e336d72a72c812dd2dd249f04f166a` ended terminal (exit 1): identity, boundary and behavior passed; selected integration ran exactly 27 cases (24 passed, 3 setup errors, 0 failures, 0 skipped); later stages were not reached, the run is not complete and no receipt was written. The setup errors stopped in offline per-profile seeding at its 120-second limit before gateway start; the cause is unconfirmed and this attempt does not prove the earlier Run 4 cause. An earlier partial rerun of only the three T7 cases passed (3 of 3, provisional fixture-only) but does not qualify. Tool-only nonfatal diagnostics are accepted in draft [PR #61](https://github.com/MahdiHedhli/hermes-hmp/pull/61) at `f4730eb`, with final 15 diagnostic tests and 300 earlier fixture / 23 CI-tool passes separately. That earlier attempt is no longer a current running-status claim. The latest private package at `c1d3d0b` has 239 byte-exact files, 32 changed-input native checks passed, and a native scan with 121 caution findings and zero critical findings. It is not installed; live approval activation and device verification remain open. The controller send slice is accepted in draft [app PR #55](https://github.com/MahdiHedhli/HermesBotMobile/pull/55), and a plain-text Phone chat screen is accepted in draft [app PR #56](https://github.com/MahdiHedhli/HermesBotMobile/pull/56), both with synthetic evidence only. The production approval manifest stays empty. No approval capability is part of the released migration.

The mobile candidate renders public HTTPS assistant images after explicit tap with bounded, credential-free fetching. A CDN MIME-mismatch repair ([app PR #57](https://github.com/MahdiHedhli/HermesBotMobile/pull/57), `dba5c93`) passed 106 root tests and focused Opus review; the same production-loader CDN probe now decodes successfully. Signed local build `2026093003` is installed on one owner iPhone; the owner screenshot confirms public-CDN rendering, and public TestFlight is unchanged. Local image dogfood is separate from live gateway approval admission (the same local build also contains the existing approval screen, unusable while the live host gate is closed); generated local media handles, video/audio and uploads are not included.

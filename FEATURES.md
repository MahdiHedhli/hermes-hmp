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
| Source reviewed; Desktop native case failed; remote delivery pending | Priority approval notifications | Issuer `9611b5d`, storage `d41f5e7` and live configuration/listener `22e92b1` and registration routes/writers `71385bb` plus hint resolver/map `ef11d01` and injected-port dispatcher `e6e20a6` are independently source-reviewed, with exact hosted CI passing. HTTPS client/factory `fcd10e0` is independently source-reviewed, with exact hosted CI passing. Remote relay/seal interoperability, relay/app integration, provisioning and physical delivery remain open. Verified-TLS component `9e21614` and native fixture `871ebb0` are independently accepted within their scopes: three selected approval/revoke/restart cases passed on one development sample. The new genuine Desktop interleave failed shared visibility/capture and close-registry checks; T029 and remote relay/provider/app/device gates remain open. No notification is delivered by these source slices. |
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

## Read-only push status implementation checkpoint

The independently accepted T026 source slice at `25324c664d7f6147669498562ec7da4bb366ad11` ([HMP PR #89](https://github.com/MahdiHedhli/hermes-hmp/pull/89)) adds `hermes hmp push status`: configured opt-in, validated relay
configuration, configured kid count, active registration count, and non-revoked generation-row
count. It emits only fixed names/codes, booleans and counts; unreadable configuration/store data is
unavailable rather than zero. It loads no identity key, mutates no grant, migrates no store, sends no
push and reports no dispatch or delivery outcome. A disabled host may still have valid relay config;
stored active rows are not a claim of current dispatch eligibility.

Local source verification: **2,591 passed, 16 skipped**, one existing aiohttp warning; lint, closed
surface and privacy checks passed. Eight isolated cases against Hermes source `ac0cfa7db94cefa90cf3e35191f38b53888b9e17`
matched the native pure configuration primitives, including flat versus explicit `extra` precedence,
legacy state, environment references and managed leaf overrides. No diagnostic file/environment
change was observed. Native CLI bootstrap is accounted for separately; the bridge refuses to cause
Hermes configuration's first import because it can seed SOUL.md. Live WAL uses read-only/query-only
SQLite; missing SHM reports unavailable, and existing SHM may update ordinary reader bookkeeping.

Independent v3 source review accepted the frozen implementation, verifying pins and inspecting the exact test logs; the reviewer did not rerun pytest. Initial hosted CI stopped at import formatting because the local lint used the wrong configuration. The whitespace-only followup passed canonical repository lint locally and [hosted CI run 37092782098](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37092782098) succeeded on exact head `25324c664d7f6147669498562ec7da4bb366ad11`, including tests, surface, log hygiene and privacy gates. It changes no minimum-version
policy or app feature gate. Missing optional configuration primitives affect diagnostics only.
A supported read-only Hermes settings projection would remove HMP's private parser/expansion/merge
primitive dependencies. Provider/device delivery, relay/seal interoperability, app registration,
provisioning and remote release gates remain open.

The diagnostics reader now rejects opened nonregular targets before reading, uses nonblocking open to avoid FIFO waits, and preserves native symlinks to regular configuration files. Four isolated FIFO/symlink tests have subprocess timeouts; regular filesystem stalls remain outside a universal wall-clock guarantee. The accepted v3 fixes the blocking-read edge identified by the v2 rejection. No live installation or notification delivery is implied.

## Native approval relay fixture component checkpoint (2026-10-03 UTC)

The independently accepted receiver/client component at
`9e21614f44edf984072353a21d94ce78d9457365`
([HMP draft PR #90](https://github.com/MahdiHedhli/hermes-hmp/pull/90)) adds a disposable
loopback HTTPS receiver. The real production relay client sends requests through verified chain
and hostname checks plus the configured leaf pin; the receiver independently frames and verifies
the P-256 signature. Untrusted CA and wrong-pin cases fail before a request is captured.

The receiver has bounded headers, body, capture count and connection/close time, fixed responses,
no request logging, and synthetic private certificate files in fresh scratch directories.
Independent review found that deeply nested JSON could reach the standard traceback path;
the accepted repair returns fixed 400 with no capture or stderr. No request-body disclosure was
demonstrated. Independent focused tests passed 2/2; the full local CI-equivalent suite passed
2,610 cases, with 16 skips and one existing aiohttp warning. Exact-head hosted CI
[run 37094865602](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37094865602)
also completed successfully.

**At this component checkpoint, T029 remained incomplete.** These tests used a synthetic
signing identity rather than a native approval. The later native checkpoint below adds bounded
approval/revocation/restart evidence; the genuine Desktop-held interleave remains unverified. HPKE opening, relay admission/replay/provider behavior, app registration,
APNs/FCM delivery, runtime privacy canaries and release qualification remain separate work.
No production module, live home, deployment, provider or device was changed by this component.

## Native approval push origin, revocation and restart checkpoint (2026-10-03 UTC)

The isolated fixture at `871ebb0d322140e834e99b585844ebfa2b0ddf4a`
([HMP draft PR #91](https://github.com/MahdiHedhli/hermes-hmp/pull/91)) drives actual
Hermes approval callbacks, AP3/AP4 routes, the production dispatcher and the verified-TLS fake
receiver. Independent source/confinement review preceded the run; independent receipt review
accepted these three selected cases on Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`,
Python 3.14.7 and its locked messaging dependency set (3 passed, 0 skips, 9 unrelated parameters
deselected):

- A native approval produced a request whose signature the fake relay independently verified.
- After positively observing pending work and the real coalescing delay, native device revocation
  invalidated the bearer and prevented a second relay request.
- Graceful restart cancelled positively pending work; the test assertions verified cleared
  queue/slots/hints, old-hint 404 and no second relay request.

**Receipt limitation:** final teardown overwrote the old dispatcher's close journal with the new
listener's zero counters. The old current journal retains cancellation and the in-test close
assertion passed, but the final close file is not the old dispatcher's snapshot. This limit is
retained alongside the accepted receipt, not repaired retroactively.

Fresh sandbox preflight and native imports passed. Prepared/shared/protected tree digests stayed
unchanged and no child processes remained. An earlier preflight failed its offline package check
from a working directory denied by the sandbox; the successful check used the private fixture
directory. Both receipts and the causal diagnostic are retained. The sandbox was not weakened.
Dependency wheel-byte provenance remains a residual.

The observer exists only in disposable copied fixture code, follows the actual coalescing sleep
and records bounded counters/booleans. Independent review required a notifier-absent sample to
fail the positive prerequisite and FIFO reads to fail without blocking; the runner requires a
passed current-receipt preflight before native imports. Those repairs were independently
confirmed. Six focused helper tests, Ruff, privacy and closed surface checks passed locally.
Hosted unit/tool CI initially failed because the FIFO regression's child could not import the
observer from CI's working directory (2,614 passed, 17 skips, one failure). The independently
accepted test-only repair at `3e676ec10266ef958ca631b6f8384c6aa297745e` binds that child to
the imported observer directory, retaining its no-writer setup and three-second timeout. Six
helper tests passed independently. Exact-head hosted
[run 37098887364](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37098887364)
then completed successfully: 2,615 passed, 17 skips and one existing warning, with lint, closed
surface and privacy checks passing. The native test/observer/wiring code is unchanged by this
repair; the three native cases retain their original sealed receipt, not a new native rerun.

**T029 remains incomplete:** the genuine combined Desktop-held interleave is unverified. HPKE
opening, remote relay admission/replay, app registration, APNs/FCM delivery, physical devices and
release acceptance remain separate gates. The fake relay accepts opaque seal syntax; it does not
open a seal or contact a provider. This one development sample is not a runtime allowlist or a
qualification of future versions. No production module, live home, device, deployment or provider
configuration changed.

## Desktop ownership source trace (2026-10-03 UTC)

Historical source-only checkpoint; the actual experiment below supersedes its
runtime-pending status.

Independent source and fixture-plan review on Hermes
`8afaab3703e336d72a72c812dd2dd249f04f166a` and HMP
`3e676ec10266ef958ca631b6f8384c6aa297745e` distinguishes two native leases:
the API agent holds a durable SessionDB turn lease, while Desktop claims the
active-session registry lease at `prompt.submit`. The durable lease serializes
model turns. Desktop submit-time transcript persistence precedes its worker's
turn-lease admission. HMP's shared AP3 visibility currently uses a stream-derived
held marker, which does not observe a new Desktop registry claim during an
already-open API approval. This is a source hypothesis for stale visibility and
transcript ordering; no causal runtime defect or concurrent model execution is
claimed. The native snapshot read exists, so an upstream missing primitive has
not been established.

The independently accepted experiment warms the real Desktop backend before
arming one pending push barrier, uses actual `/api/ws` resume/submit, observes
registry ownership, transcript ordering, AP3 and relay capture, then denies the
original approval for cleanup. Implementation and fresh confinement/runtime
review remain required. The prior three-case native receipt is unchanged;
**T029 remains open**. No production module, deployed build or availability gate
changed, and this sample is not an exact-version allowlist.


## Desktop pending approval experiment (2026-10-03 UTC)

A fresh isolated four-case native run on Hermes
`8afaab3703e336d72a72c812dd2dd249f04f166a`, with HMP base
`3e676ec10266ef958ca631b6f8384c6aa297745e` and the independently accepted
Desktop fixture v4, ended **3 passed, 1 failed, 0 skipped**. The full 292-file
candidate was frozen before preparation; production modules were unchanged.
The original three-case receipt remains intact.

- The real Desktop `prompt.submit` returned streaming, persisted the exact new
  user row in shared Bot Chat history, and held the exact native registry claim
  through the completed dispatch observation.
- The original pending API approval remained visible in AP3 while that owner
  was active. Verified fake-relay captures increased from the warm-up baseline
  of one to two. The pending sentinel and later exact-ID denial support that
  this was the original nonterminal request, not an expired request.
- After the fixture closed Desktop, its raw registry claim remained; this was
  the first failing assertion. The same original approval was still visible
  and exact-ID denial applied, but this does not prove a hide-and-reappear
  transition. WebSocket close followed by process termination is not evidence
  of graceful native session/registry release. That lifecycle question remains
  separate from the observed live-owner visibility and capture failure.

Current-receipt preflight proved same-sandbox child signal delivery and denied
signaling of a disposable external test sentinel, which survived. Native imports
passed without owner/old source modules. The run reported no leftover child
processes and no prepared/shared/protected byte changes. Failed fixture state
and private causal artifacts are retained; broad process-information isolation
and independent dependency wheel-byte provenance are not claimed.

Independent database inspection later created SQLite WAL/SHM sidecars inside
the retained private fixture despite `mode=ro` and `query_only`. The primary
database, registry and original test artifacts stayed unchanged; the private
sidecars are preserved and the review footprint is explicitly corrected. Future
inspection uses immutable database access or an isolated copy. This was not a
live host/database action.

**T029 remains failing.** The next repair must cover shared approval visibility,
answer and push consumers, with independent review and a new bounded runtime
receipt. There is no concurrent model-execution claim, upstream missing-primitive
claim, live installation, device, provider or release qualification. The fake
relay verifies signatures and captures requests; it does not open HPKE seals or
contact APNs/FCM. The live visibility/capture failure is distinct from the
unqualified close/release transition.

### HPKE/JCS vector preparation

The separate test-only vector plan passed independent plan review. It uses the
frozen D1 suite and exact 16-byte `HMP push seal v1` info, an independent Node
generator and Python opener/checker, and the official RFC corpus. Source and
exact dependency preparation have started on an isolated branch. Dependency
execution, generated-vector acceptance, production app libraries, relay keys,
providers and interoperability remain unqualified. Owner provisioning choices
are not prerequisites for this test-only work.

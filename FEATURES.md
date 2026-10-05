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
| Implementation | Phone photo/file attachments | Pure codecs, scoped slot/owner and canonical asset layout source published; 64 focused layout/domain tests passed; the complete picker/Send flow, upload/readback and encrypted staging remain unimplemented. The inspected Phone dispatch has a separate atomic no-defer admission gap; canonical Desktop multimodal remains an upstream gap. Historical archive primitive tests do not qualify the complete flow. See the [admission checkpoint](#phone-attachment-admission-checkpoint-2026-10-03). |

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

### Phone attachment admission checkpoint (2026-10-03)

The revised Photos/Files contract is accepted as input for normative amendments
and pure interface work only. It preserves attachment-first composition, the
existing Phone pending-send slot, bounded device-upload custody and fresh native
own-CMID row authority. The exact encrypted staging envelope, portable host
validator, complete upload/admission/readback implementation and OS/device tests
remain pending. No operational attachment Send or product + entry is available.

On inspected Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`, a synchronous
adapter busy refusal cannot guarantee no deferred execution: [startup restore
queues before plugin hooks](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/run_inbound.py#L212-L217),
and [cold entry can encounter runner busy handling or orphan FIFO rescue](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/run_inbound.py#L1243-L1344).
That [event type](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/platforms/event.py#L36-L123)
has no reject-policy admission ticket. This is a separate
`PHONE_ATTACHMENT_ATOMIC_ADMISSION_GAP`: native settlement must cover all
retaining/effectful exits, preserve the original CMID and ordered media, and
compare/create an exact absent session for an attachment-first Send. A refusal
must leave no deferred instruction or user row; an unresolved outcome remains
unknown. HMP will not patch private runner queues or ship FIFO as an alternative.
Later builds use actual required APIs under the minimum-version policy; this
revision is source evidence, not an availability allowlist or a universal
absence claim. Desktop-owned canonical multimodal admission remains a separate
upstream gap.

### HPKE/JCS vector preparation

The test-only source in [draft PR #92](https://github.com/MahdiHedhli/hermes-hmp/pull/92)
contains 151 finite case definitions and six pure-test methods. The earlier repaired
protocol source and lint-only delta passed their separate independent reviews.
The current eight-file metadata-minimization delta also passed a separate
source/data review; none of these verdicts admits vector execution.
It uses the frozen D1 suite, exact 16-byte `HMP push seal v1` info, an independent
Node generator/Python opener, and the original official RFC corpus. Package
archives and member digests are pinned as data. CI exposed lint and public
publisher-contact hygiene failures; the repair minimizes the five registry
records to selected provenance fields while preserving original-response hashes
and the existing privacy scanner. Package/archive/license bytes are unchanged.

**All 151 crypto case definitions remain unexecuted.** The separate fixed
stdlib-only codec run passed six methods and 33 subtests, with zero boundary
refusals and all 226 pinned inputs unchanged. It extracted ten pure functions
and two classes from the exact PR #92 checker source without importing the
whole checker, crypto packages, preflight or main. This verifies only the tested
JSON/base64/request-shape/transcript rules. No generated known-answer corpus,
installed/imported crypto package, production consumer,
relay/provider delivery or native app interoperability is qualified. Independent
containment review requires a startup watchdog, specific allocation-failure
observations with small positive controls, and exact accepted-canary/profile
receipt bindings. Runtime startup, hard resource enforcement, immutable input
and mount lifetime, loader closure and other denial/reaping controls still need
verification. Native and crypto execution admission remains closed. Owner provisioning choices
are not prerequisites for this test-only work.

The startup-supervisor v2 ownership repair is independently accepted in source.
The caller retains the exact child handle before startup and through observation,
handoff and receipt failures. All 140 source-review input hashes matched. A
separately reviewed fixed recipe then ran all 46 isolated synthetic controls:
46 passed, zero boundary refusals, and all 206 execution-review inputs remained
unchanged. The prior failed v1 source review and both failed recipe attempts are
preserved. This verifies the ownership repair under mocked failure cases; it
does not qualify native startup or runtime cleanup, or execute any crypto vector.
Exceptional holding can remain indefinite. Actual resource collectors, trusted
receipt provenance and immutable runtime/mount lifetime remain open. Native
startup and crypto admission remain NONE.

A separate root-admitted trusted startup attempt was refused before fork. The
collector exited 125 with no bound child or child log files. A fresh stdlib
context check identified the inherited macOS file-descriptor hard limit above
the supervisor's supported ceiling; all 247 source/history inputs remained
unchanged. This is a launcher-context refusal, not a failed controlled-child
startup. The failed attempt is retained.

The replacement trusted launcher lowers only its own file-descriptor limit to
32/32 before the existing preexec-free process launch. The collector and child
inherit that limit; the configured child limits, including `NOFILE` 32, remain
unchanged. Its ordinary child actually forked and was reaped, but exited 125
during limit setup: `FORKED, SETUP_ERROR`, no payload or child log bytes, no
signals or identity loss. The collector correctly failed, and all 270 pinned
inputs remained unchanged. That attempt did not identify the failing resource
or error. No startup-stall or TERM/KILL case was attempted, and neither failed
ordinary attempt is a startup/resource/crypto pass.

A later diagnostic-only ordinary attempt identified the exact failing call on
this macOS test runtime: setting the unchanged 256 MiB address-space limit raised
`ValueError`, with no errno available. The child was actually reaped after
`FORKED, SETUP_ERROR`, exit 125, with no child log bytes, signals or identity loss.
All 296 pinned source/history inputs remained unchanged. This identifies the
resource call, not the operating-system cause or resource enforcement. The
limits remain unchanged; no later startup-stall or TERM/KILL case ran. Supported
fixed-limit runtime validation remains open, and all 151 crypto definitions
remain unexecuted.

### Shared Desktop ownership repair contract

Independent review accepted the revised contract only; backend/mobile integration
and a new bounded native receipt remain pending. Explicit `owned`, `unowned` and
`unknown` state stays distinct from a legacy absent field. Unknown Bot ownership
hides answerable Bot cards while preserving reserved/releasable and other pending
state. Phone approvals keep their existing independent path. AP4 must preserve
settled replay/conflict/expiry handling before checking open Bot ownership, and
must not apply an answer under owned/unknown state. A point-in-time ownership
check does not eliminate the check/use race.

The native snapshot API exists, so a missing upstream primitive is not established.
Its default lenient mode can prune unknown-liveness entries; strict mode aborts
on unknown and can prune proven-dead entries. HMP currently omits strict mode.
The snapshot lacks hard parsing, entry-count, lock, probe and deadline bounds;
two worker threads and a caller timeout alone do not resolve this. Bounded
observation, native cleanup/read-route semantics and worker termination require
separate review before integration. HMP must not parse or mutate the native
registry as a second authority. The failing T029 receipt above is unchanged.

### Retained access and availability repairs

[Draft PR #93](https://github.com/MahdiHedhli/hermes-hmp/pull/93), at
`7b8138e4e62bd7cff975909f1a1cc09b6cee73c5`, applies the existing stripped
16-character API-key floor to the default profile's scoped fallback. Ten new
regression cases cover invalid types, empty/whitespace, below-boundary and valid
boundary values while retaining inline precedence and named-profile isolation.
Independent source review accepted the repair. Both exact-head hosted CI runs
passed; [PR run 37110174546](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37110174546)
reports 2,625 passed and 17 skipped, with lint, closed-surface and privacy gates
passing. Native startup already checks key strength; this was a false-availability
prerequisite, not a demonstrated authentication bypass. No live deployment or
credential change is claimed.

[Draft PR #94](https://github.com/MahdiHedhli/hermes-hmp/pull/94), at
`69bd1d6f2d03d78ebe0ea8cfe36d1e5ac039dfc1`, adds the existing Hermes-session
presence guard to device listings before store opening. Operator listings still
work without a TTY; mutation ordering and other read paths are unchanged.
Independent source review accepted the three-file repair. Twenty new cases cover
18 session refusals and two populated operator controls. Exact-head hosted
[run 37112555432](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37112555432)
passed 2,635 cases with 17 skips and one existing warning, including lint,
closed-surface and privacy checks. This mitigates accidental metadata disclosure;
the same OS user remains the authority boundary. No live deployment is claimed.

[Draft PR #95](https://github.com/MahdiHedhli/hermes-hmp/pull/95), at
`c0d0945b64058e3f337c8ff7181ec3294387df9a`, repairs the large-inventory finding
in reviewed source. The local listener-file read/write/removal limit is 64 KiB;
legacy small-record parsing and the pinned network ready-read limit remain
16 KiB. Larger records require a closed schema, canonical identity, bounded
ASCII fields and complete unique profile/health coverage. All 128 supported
maximum-length profiles and derived names are preserved without truncation.
Bounded projection and incremental encoding retain atomic failure behavior.

Independent source review accepted the four-file repair. Author and independent
focused runs each passed 113 cases: 65 new and 48 existing controls. Exact-head
[run 37114626278](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37114626278)
passed 2,680 cases with 17 skips and one existing warning, including lint,
closed-surface and hygiene gates. Combined source/CI status is recorded below.
Old readers may reject large records; an out-of-domain (>128) failed refresh can
retain an older snapshot fresh for up to 45 seconds. Freshness does not prove
current live roster completeness. The same OS user remains the authority
boundary. Neither finding establishes an owner incident.

The three repairs are now composed in [draft PR #96](https://github.com/MahdiHedhli/hermes-hmp/pull/96),
at `df30e09309569550232af6fbec4596817a75f464`. Independent source review verified
exact CLI composition, eight unchanged carried files and 283 untouched common-parent
files. Exact combined-head [CI run 37116039263](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37116039263)
passed: 2,710 tests, 17 skips and one existing warning, with lint, closed-surface,
log hygiene and privacy checks. This accepts the combined source and configured
CI scope. Native, mobile/device integration, activation and deployment remain
pending; the residual limits above still apply. No new upstream API is required
for these three repairs.

## Ownership and attachment source progress (2026-10-03 UTC)

### Desktop ownership seam

[HMP draft #97](https://github.com/MahdiHedhli/hermes-hmp/pull/97) at
`b65f6aa` adds the reviewed tri-state Desktop ownership port: `owned`, `unowned`
and `unknown`. The production default cannot observe. Unknown ownership hides
Bot approval cards; independent Phone cards and settled replay/conflict/expiry
handling remain. Open Bot answers check the injected port under their row lock
and cannot call the resolver for owned or unknown state.

Root passed 225 focused fake-port cases and the full HMP unit suite
(2,394 passed, 15 skipped). Three deliberately removed guards each failed their
targeted assertion. Exact-head [hosted CI](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37126002690)
passed lint, unit/tool tests, plugin surface, log hygiene and privacy checks.
The earlier 220-pass/5-fail fixture run is retained; its test-only repairs and
a snapshot file-mode correction are documented in the private evidence.

This draft is a source foundation, not a deployable ownership provider. No
native registry observer is included, and the point-in-time check/use race
remains open. It does not verify genuine Desktop interleaving, urgent
notification delivery, native approval coverage or physical-device behavior.

### Attachment parser review

The Python/Dart attachment DTO, hash, pending-record codec and declarative ports
are authored in isolated branches. Independent review found that the Python
raw parser checks object/member and array bounds during or after generic JSON
decoding, while the accepted contract requires them before decoding. This
source defect must be repaired and reviewed before candidate test execution.
No upload route, picker, native admission, custody store, encrypted staging
adapter or operational attachment Send is enabled.

### Push diagnostic test repair

A separate test copy repaired the missing-resource diagnostic fixture by using
an explicit delegate rather than a Mock side effect for builtin `getattr`.
All 20 guarded synthetic collector cases then passed with zero boundary
refusals; all 358 source/history pins matched after execution. The original
19-pass/1-error result remains retained. This verifies the mocked diagnostic
contract only: the actual macOS fixed-AS setup failure is unchanged, later
startup controls and 151 crypto case definitions remain unexecuted, and no
native resource, relay, provider or notification-delivery readiness is claimed.

## Attachment codec verification progress (2026-10-03 UTC)

The independently reviewed pure attachment candidate now has actual focused results on the
exact cleanup revision:

- **Python: 56 attachment cases passed**, including structural bounds before generic JSON
  decoding, exact UTF-8/hash vectors, duplicate-key and fixed-error controls.
- **Python: 115 existing contract/module regression checks passed**, covering table fidelity
  and the declared module inventory/import surface.
- **Dart: 71 attachment cases passed**, including combined/legacy pending-record fidelity,
  phase/classifier controls, immutable values and all 64 reference suffixes.

The first Dart run recorded **69 passes and one failure**: a noncanonical reference suffix
exposed an input-bearing Base64 exception instead of the fixed domain error. That failure is
preserved. A separately reviewed two-file repair rejects noncanonical suffixes before decoding
and maps decoder failures to the fixed error. The subsequent 71-case run passed; this resolves
that defect in the unreleased candidate without claiming a deployed attachment capability.

These are focused pure-codec results, not full CI, native admission, file-content validation or
physical-device proof. The subsequent cleanup preserved behavior and assertions under independent
review, then passed all 56 + 115 Python and 71 Dart checks again. Root Ruff checks on four Python
paths and strict Dart analysis on all eight new source/test/port paths are clean. No rules were
waived; the original failure and earlier diagnostics remain preserved as historical evidence.

The mobile **+** picker, encrypted asset storage, shared message-ID/CAS adapter, validated
upload/send routes, native admission and authorized own-row readback still require implementation
and separate verification. Local host `MEDIA:` output remains blocked by its provenance/read
authority gap. No upload route, device/provider qualification or release availability is implied.

## Published attachment codec CI (2026-10-03 UTC)

The pure codec slice is now published in draft [HMP PR 98](https://github.com/MahdiHedhli/hermes-hmp/pull/98)
at `7cbdf8199e0b372911d02e15fc41cd1dc9babc59` and draft
[Mobile PR 72](https://github.com/MahdiHedhli/HermesBotMobile/pull/72)
at `b0107a70b22cabfa3e2f134da888714141f3aae6`.
[HMP source CI](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37130502909)
passed, including 2,767 unit/tool tests with 17 skips and one warning.
[Mobile source CI](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37130507541)
passed app/client analysis and tests, security hygiene, source gates, and 145
release-wrapper/scanner regression checks. The second same-commit
[Mobile CI run](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37130504615)
also passed. These are complete results for the named source workflows, with
no skip or warning recast as a pass and no release security gate waiver.

The next checkpoint below supersedes the earlier shared-slot implementation
status. The public feature remains incomplete: asset encryption, picker ownership,
custody/upload/send, native atomic admission, authorized readback and physical
device gates are still open. Source CI does not qualify those missing capabilities
or make the **+** media route available.


## Signed Android reporting validation (2026-10-03)

The exact signed Free Android code 2 (`8671061`, APK SHA-256
`04c247fff5e4e35ec2d6e4df2127aaf62d9bdd2443dd6a364d846c362d0a96df`)
passed a bounded, independently inspected emulator-5570 report walkthrough.
Initial excerpt-off, privacy/consent, editable opt-in synthetic preview, Cancel
and reopened reset were observed. One explicitly sent synthetic report with
excerpt off produced the Android success acknowledgement and one independently
correlated receiver record with a receipt and approximately 30-day expiry.
No private receipt token, KV key or test content is published here.

This supersedes earlier locked-emulator/report-pending checkpoints. Physical
Android, paired/live reviewer coverage and an opt-in excerpt submission were not
tested. No wire capture, extra Send/retry, host or receiver deployment, Play upload
or submission occurred. Provider-aware Data safety, full reviewer access,
exact-source automated release-security-review PASS and replacement upload/submission
remain open. No usable Android beta install link or release acceptance is claimed.


## Android provider and staged-build review (2026-10-03)

Historical initial review; the later supported-draft/publication checkpoint below
supersedes its prepared-only and unsent-support statements.

The provider inventory and exact-build reviewer matrix are complete with independent
factual acceptance; final Data safety answers and release certification remain open.
Fresh Console reads distinguish Free code 1 (`150dd06`) available to internal
testers from the closed Alpha release marked **not yet sent for review**. There
are 13 unsubmitted changes. Verified local replacement code 2 (`8671061`) is not
among uploaded bundles; no public Android enrollment/install link is verified.

The existing bounded emulator report acknowledgement and independent KV receipt
correlation remain valid; they do not certify physical, live-host or full reviewer
access. The saved no-restrictions answer is inaccurate for live pairing and host
approval. The owner-selected synthetic/BYO-host scope remains: no exposed reviewer
Hermes, local LLM or automatic removal of product features. A Google access
clarification is prepared, not sent; no full-access certification is made.

Data-flow review includes HMP host recipients, Cloudflare content versus network
metadata, consented Android recognizer fallback, TTS, public/host-local image
requests and relevant-version aggregation. **PLAY-QR-METADATA-1** records ML Kit
diagnostics/usage metrics separately from on-device QR input processing. Code 2
APK barcode metadata versions 17.3.0 and 18.3.1 match current primary guidance;
that is not a telemetry/network capture. Recipient/controller purposes, sharing
basis, category/retention mapping and the older inactive upload's relevance remain
explicit gaps. **PLAY-VOICE-1** remains open. No new report Send/retry, host or
receiver deployment, permission/provider connection, Play upload or submission
occurred during this review.

## Supported Android provider drafts and published privacy — 2026-10-03 UTC

This supersedes the earlier prepared-only scanner/privacy and unsent-support
status. Independent provider review accepted source/policy-supported mappings;
Console draft-save confirmations were observed. Messages are required collected
content; other user-generated content/actions and voice remain optional. ML Kit
Diagnostics and Device IDs are conservatively collected/shared, required and
non-ephemeral, with analytics and security purposes; collected identifiers also
serve app functionality. Code 2's optional report route includes conservative
Cloudflare IP-derived approximate-location handling. No GPS/QR-frame upload,
advertising ID, Firebase Analytics or shipped phone photo/video upload is claimed.

The [privacy policy](https://hermes-bot.app/privacy.html) now includes the reviewed
ML Kit and Cloudflare network-metadata disclosures. Site
[PR #10](https://github.com/MahdiHedhli/Hermes-Bot-Site/pull/10) retains the October 2
effective date and adds an October 3 revision date; exact live bytes were verified.
The single authorized Google Play Support BYO-host clarification was sent and
confirmed. No reply or policy exception is established by the ticket.

This is a saved draft, not a final Data safety declaration or full-feature reviewer
certification. Actual OEM speech processing/retention, provider metadata retention
and native transport remain qualified; the report-record 30-day TTL is not global.
The saved no-restrictions access answer remains inaccurate. Last inspected code 1
is internal available/closed unsubmitted; older code 2026092917 has a Draft track
with zero releases and unpinned source, while code 2 remains local/unuploaded.
Truthful reviewer access, exact-source automated security review, independent
signed-artifact acceptance and required physical/native gates remain open. No
support resend, report Send, device/provider/permission change, host exposure,
Play upload/submission or feature deployment occurred in this documentation update.

## Published Phone pending-slot adapter (2026-10-03 UTC)

The scoped shared-slot persistence adapter is published in draft
[Mobile PR 73](https://github.com/MahdiHedhli/HermesBotMobile/pull/73), exact source
`416dbe5b5a1e351ad446232a4c2aea4d7f71fa22`, stacked on the reviewed attachment
contract branch. Its fourteen committed files match the frozen V5 source.
Independent reviews accepted the bounded persistence/source changes. Root cached
focused app suites passed **110 cases with zero failures**; unchanged client
source retains **19 passing cases**. Earlier compile and V3/V4 failures remain
historical evidence. Transparent real type-query delegation in the tests does
not establish the original SDK failure cause or qualify native OS cryptography.

The adapter reads one sealed pending slot for legacy text or attachments, uses
registered read revisions and lifecycle-scoped compare-and-write, and preserves
malformed/unavailable distinctions. This is source implementation, not a working
mobile picker or attachment Send feature. Hosted source CI failed at this exact
commit: the network guard rejected two local `File.open` calls, and the app
analyzer reported two warnings. A focused reviewed repair is needed; no CI pass,
physical durability or release qualification is claimed.

The next-contract status below is historical; the implemented owner checkpoint follows.
That independently accepted contract covers private pending-slot inspection,
conservative restart normalization from `messageMayTransmit` to `unknown`, actual
operation accounting through invalidation/close, and explicit clear refusal.
Source authoring has begun on the exact published adapter base; no source tests
or production Phone route are accepted yet. A lifecycle-admitted conservative
normalization may finish after page/session loss; stale work must issue no
current capture. Successful clear needs a separate publication-currency decision
and actual native/owned-cleanup proofs. Full D4-S, encrypted assets, native atomic
admission/upload/readback and the **+** media route remain open. No upstream
Hermes change, live host change, deployment or release is implied.

## Phone pending owner and repaired source CI (2026-10-03 UTC)

The scoped slot parent is now `a3fa1febb95127762ae936edec70663a9b98edfd`, in
[draft PR #73](https://github.com/MahdiHedhli/HermesBotMobile/pull/73).
Actual hosted App CI [37147527021](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37147527021)
passed on that exact head. Earlier failures remain historical evidence: local File.open calls
needed a reviewed exact-blob lexical allowance; test lint and a shallow-checkout historical-object
assertion also needed correction. The allowance exempts only `open` for unchanged reviewed local
file bytes. All network/import/type/acceptance guards remain enforced, with matched negative
controls and actual depth-one regression checks.

The internal pending owner is published at `d31fafa520a5f1c505f35ec8d591d8104a29b9e6`, in
[draft PR #74](https://github.com/MahdiHedhli/HermesBotMobile/pull/74), stacked on that parent.
Independent review accepted the exact two source/test paths and their disjoint composition.
Root's cached pure Dart owner/lower-slot/send suites passed 83 aggregate checks, with zero failures;
those executed source bytes are unchanged in the published composition. Cached client analysis
exited zero with three infos, including one new initializing-formal suggestion; the existing public
named environment parameter is retained. Current combined-source network and privacy scans passed;
new-head hosted CI was pending at the initial checkpoint. Subsequently, exact-head App CI
[37148001498](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37148001498) and
[37147969675](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37147969675) passed.
These CI results do not establish full D4-S, native/device behaviour or release qualification. The adapter's earlier 110 app and
19 client focused results remain separate evidence, not extra owner tests.

This owner permits current scoped inspection and only conservative restart normalization of
attachment `messageMayTransmit` to `unknown`. Private captures compare instance/profile, all
foreground/lifecycle/slot/page/session generations and exact identities. Its single actual pipeline
stays reserved through reads, admitted CAS, fresh typed post-read, invalidation and close. It joins
already admitted normalization after UI currency loss and returns stale without claiming the write
was prevented. Every clear request still refuses with no I/O.

Production Phone environment/route/session derivation, successful clear with native and joined
cleanup proof, encrypted owned assets/quotas/orphans, picker/tray, upload, atomic native admission,
actual own-row readback and physical/device/provider/release gates remain open. Full D4-S and the
complete attachment flow are not complete. The next independent local prerequisite is the D4-A/F
encrypted-asset/file-custody contract; no real native crypto or file-attacker custody is established
by synthetic storage tests. No attachment UI or release is enabled by these source publications.

## Pure phone asset layout source (2026-10-03 UTC)

[Draft PR #75](https://github.com/MahdiHedhli/HermesBotMobile/pull/75), source
`c998ef9edb880798864f40650d050aaa301a5fef`, adds the internal canonical context/header,
chunk AAD and completion encoders on the reviewed pending-owner branch. Interface and exact
three-path source received independent review. The seven byte-layout fixtures are synthetic
encoding data; their declared hashes do not establish authenticated ciphertext or key entropy.

Root ran 64 focused cached synthetic tests: 17 new layout tests and 47 existing attachment-domain
tests, with no failures. Controls cover all six MIME discriminants, 128 chunk ordinals, exact
integer timestamp endpoints, malformed Unicode/IDs/hex, field bounds, buffer mutation and fixed
error privacy. Focused analysis exited zero with one nonblocking test-local const style info.
The network guard and source private-value scan passed. The unchanged captured-log scanner passed
against four historical logs and its existing reviewed baseline; this creates no new runtime-log
or device evidence. Hosted exact-source CI was in progress at publication; it is separate from
these focused results.

The new class only encodes bounded declared data. It does not encrypt, verify digests or tags,
create a file/key/source capability, publish a tray, upload or enable attachment Send. Full D4-A/F
remains open: native purpose and ABI, cryptographic controls, catalog/current generation, clocks,
quotas/orphans, descriptor custody, normalization/picker integration, atomic native admission,
actual own-row readback, complete device flow and release verification are still required.
Native AES preparation can follow the existing iOS Keychain construction and an Android path
that verifies StrongBox/TEE protection and refuses unverified/software outcomes. No optional
software fallback or new native operation is adopted by this encoder checkpoint; existing
release residuals remain open.


## Approval mode and operator test planning — October 4, 2026

**AM1 is officially planned:** mobile read/change of native `manual`, `smart`, and
`off` approval mode. Native mode is persistent and profile-wide; a future HMP
capability and explicit gateway-admin write contract must expose that scope,
confirm weakening, preserve hard-deny safeguards, and provide authoritative
saved/effective readback. Approval-answer ownership or jobs/model control grants
do not confer mode-write authority. This is backlog/specification work; no mode
selector or live setting change is implemented.

**AT1 remains separate:** an operator-invoked, explicitly device/profile/session
scoped synthetic approval card for a harmless no-op. Its in-process producer
contract has independent acceptance and bounded source authoring is active.
The proposed `hermes hmp approvals test --device <paired-device-id> --profile
<bot-profile> --session <existing-test-session-id>` command is not implemented
or runnable. Native `hermes approvals test` is verdict-only and does not prompt.
Local operator IPC, current grants and target-device projection, exact native
lifecycle integration, and phone qualification remain pending; no tool, model,
message send or persistent permission rule may be produced by the test.


## Asset cipher runtime and approval-test source checkpoint (2026-10-04 UTC)

The current isolated asset-cipher candidate compiled on the host-JVM and
unhosted macOS XCTest routes. Actual named results match the complete selected
classes: all 24 Swift tests passed; Kotlin executed 22 tests with 20 passes and
two failures, with zero skips or assumptions. The failing Kotlin tests are
`officialNistSevenPrimitiveKnownAnswersOnly` and
`corruptionHasNoReceiptAndDoesNotRetryOpen`. Their exception locations remain
unknown in the captured name-only reporter; a bounded diagnostic is being
prepared. This checkpoint supersedes earlier statements that no selected native
tests had executed, within this isolated host scope.

The candidate remains incomplete. The two Kotlin failures require diagnosis and
repair; Android keystore, iOS device key storage, production asset custody,
current-owner integration, picker/upload and full media-send qualification
remain open. These host results provide selected synthetic coverage only.

AT1's in-process synthetic approval producer has a frozen source candidate and
eleven unexecuted fake-test definitions. Independent review requires explicit
loop-applied completion fences before terminal reconciliation, distinct local
pre-invocation cancellation provenance, and the remaining causal
lifecycle/schema/identity/privacy controls. Source repair is active. The
operator command, authenticated target binding, bridge factory and phone-card
projection still require implementation and verification. AM1 approval-mode
control remains an official planning feature.


## Planned device permission readiness (2026-10-04)

**AR1 is an official planning feature**, with nine unchecked tasks in the
[mobile permission-readiness plan](https://github.com/MahdiHedhli/HermesBotMobile/blob/056a48120460542dcd097479d687ac3850b004bb/docs/planning/MOBILE_PERMISSION_READINESS_2026-10-04.md).
Pairing and subsequent refresh should distinguish authenticated per-device
capability, current entitlement, and host/API availability. Missing rights
should have safe, actionable explanations within already authorized scope;
unauthorized resource existence must remain private. A jobs404 alone cannot
distinguish a controls refusal from a native endpoint404.

Request access creates a request. Fix access requires an explicit authorized
administrator decision, current device/profile checks, and authoritative
stored/effective readback. There must be no silent grants or broader defaults.
The plan covers revocation, stale state, concurrency, denied requests and lost
acknowledgements, with negative tests and separate physical/release acceptance.
Current jobs/default-model controls remain separate from approval-answer
ownership and approval-mode/gateway administration. AM1 mode planning and AT1
synthetic approval testing remain separate. AR1 is not implemented or deployed.


## Asset cipher repair and approval-test verification (2026-10-04 UTC)

A bounded diagnostic localized the two earlier Kotlin failures. Independently
reviewed repairs changed the complete-record matcher for the pinned NIST fixture
and declared the private fake-backend checked exception contract. A fresh
focused host-JVM run compiled and executed the same 22 named methods: all passed,
with zero failures, skips or assumptions. The previous failed runs remain
historical evidence. The unchanged Swift candidate retains its earlier 24
passing unhosted macOS tests; it was not rerun for these Android-only changes.

These are selected synthetic host tests. Production owner/catalog and encrypted
file custody, Android hardware keystore and iOS device key behavior, picker,
upload, attachment Send and full D4/release qualification remain open.

AT1's repaired in-process synthetic approval producer has independent source
acceptance and 31 passing isolated fake tests. The operator command is still
not implemented or runnable: local-operator authentication and paired-phone
projection/answer contracts require separate integration. No native approval
card, tool execution, permission grant or phone delivery was exercised by those
fake tests. AM1 and AR1 remain official planning features.


## Planned Desktop bot identity on Mobile (2026-10-04 UTC)

BI1 is an owner-authorized official planning feature with nine unchecked tasks
in the Mobile roadmap. It covers host-backed display names, recognizable
shape/color/eye characters and static custom images across roster, chat header
and bot details. The inspected Desktop has presentation metadata and separate
avatar assets; the inspected HMP roster and Mobile model lack that projection.
Desktop-local customization may be unsynced, so fallback provenance stays explicit.

The plan binds presentation to authenticated instance/canonical profile and
current credential generation, without changing routing or privileges. It allows
only a small negotiated presentation DTO, never private prompts, SOUL/personality,
chat or general settings. Older hosts retain a usable safe fallback.

The inspected native get_asset helper reads the whole file before responding.
Future exposure requires a fixed-avatar authenticated primitive bounded before
host reads, plus transport/decode limits; an after-read cap is insufficient.
Arbitrary paths, URLs, redirects and active content are excluded. Separate image
and metadata revisions, cache invalidation, stale-read fencing, revoke/unpair,
accessibility and reduced motion are part of the acceptance plan. Implementation,
wire-contract approval, physical parity and release qualification remain pending.
AM1, AT1 and AR1 remain separate.


## Physical jobs access and current feature integration (2026-10-04 UTC)

An owner supplied a populated Bot Jobs screenshot after an explicit per-device
controls grant. This confirms the Jobs read view on that iOS phone. It does not
confirm job creation, edits, deletion, scheduler execution or delivery, and no
authenticated HTTP trace was captured. The third, controls-denied device was
unchanged. A second physical phone remains unverified because its supported
public pairing-metadata read reports the device locked; no identity was inferred
from enrollment timing and no grant was made to an unidentified pairing.

Default-model controls are already allowed on the verified phone, but the host
model-management flag is absent and fresh per-profile health reports disabled.
The inspected host runs native `ca705dbf` / `0.21.5` with exact installed HMP
`4d6863e` bytes, meeting the model floor. Required model-reader/writer definitions
are present in that native source; no provider catalogue or current model was
read and no model was changed. This is a separate host setting, rather than a
minimum-version allowlist refusal.

The exact native CLI canonicalizes the nested gateway spelling to
`platforms.hmp.extra.model_management.enabled`. The HMP gate reads the live
adapter config object, not a fresh disk file; the inspected supported reload
signal performs a graceful drain/relaunch. Proposed enablement therefore needs
the one Boolean leaf and a supported graceful host restart, with explicit owner
approval, unchanged phone grants and post-restart readback. It enables the host
surface for controls-approved devices and their separately authorized bot
profiles; it must not grant a denied device, alter an approval mode or select a
model/provider. That change is pending and has not been performed. AR1 remains
the official permission-readiness/remediation plan, not deployed automation.

The inert native asset-cipher slice is published in Mobile draft
[PR76](https://github.com/MahdiHedhli/HermesBotMobile/pull/76), exact head
`b675b96b4593d4893c9ccb0557218fc097b44436`. Both recorded exact-head hosted CI
runs succeeded. Selected synthetic prerequisites remain Kotlin 22 passes and
the unchanged earlier Swift 24 passes; neither is physical key-store evidence.
Production composition stays unavailable. The iOS protected-catalog codec and
transaction contract is now a frozen proposal pending independent review.
Android protected-head custody, genuine pairing/draft ownership, key/file
handoffs, native clocks, descriptor custody, picker/upload/Send and complete
media/device/release qualification remain open.

AT1's unwired no-op approval producer is published in HMP draft
[PR99](https://github.com/MahdiHedhli/hermes-hmp/pull/99). Finite lint repair
`d33f4c34cd390c3f1ac2210e72194587598728e1` received independent review and a
fresh isolated run of the same 31 fake cases passed with three collection
warnings. Its hosted CI passed lint, then reported 2,671 passes, 17 skips and one
failure: the producer filename was missing from the explicit module inventory.
Later security-check steps were skipped, so this checkpoint does not claim
that CI passed. A finite inventory/documentation correction is under review;
the equality/import checks and all security scanners remain intact.

The CLI/paired-phone bridge remains unimplemented. Its independent contract
review requires precise direct-await ordering, a distinction between framing
half-close and operator abandonment, and fixed phone refusal responses. The
proposed `hermes hmp approval-test begin` syntax is not runnable. Fake tests do
not demonstrate a real native approval card, paired-phone delivery, grant, tool
execution or deployment. AM1 approval-mode control and BI1 Desktop identity
remain official planning features with separate implementation gates.


### AT1 source-check follow-up (2026-10-04 04:50 UTC)

The five-line inventory/documentation repair is published at HMP
`736662caafb26ecb58c7906530e4ebd561c26d04`. Its two existing targeted inventory
and import checks passed; exact-head hosted CI run `37178015906` then passed
lint, 2,673 unit/tool cases (17 skips, four warnings), closed plugin surface,
log hygiene and privacy checks. This supersedes the preceding pending-inventory
checkpoint. Caller bridge contract v4 received independent contract-only
acceptance; source integration and phone/native/card/release verification remain
open. No operator command is runnable and no host setting was changed.


## Cross-platform candidate and readiness checkpoint (2026-10-04 UTC)

The cross-platform test candidate retains Mobile source
`8671061b85c8019e31172ed497cbf27dc327c6dd` and its pinned HMP dependency.
Production source is unchanged; newer feature branches have not been silently
mixed into this candidate and existing features have not been removed.

| Item | Observed result and remaining qualification |
| --- | --- |
| Android beta 1.0.0 / code 2 | Existing exact signed APK/AAB retained and independently rehashed. Prior emulator report consent/cancel and one synthetic acknowledgement remain bounded evidence; physical Android qualification is pending. This candidate has not been uploaded or submitted. |
| iOS local dogfood 1.0.0 / 2026100401 | Guarded release-mode build and independent signed-artifact inspection passed. Installed on one owner physical phone; fresh app metadata confirms the build and public pairing registry bytes remained identical across upgrade. UI, sealed draft readability and hardware qualification remain pending. |
| Native qualification harnesses | Separate iOS example and Android self-instrumented test package built and signing/isolation inspected. Neither has been installed or executed. Generic PASS, hardware-unavailable branches and API skips cannot establish positive physical hardware evidence. These artifacts do not replace shipping-app qualification. |
| Release gates | Physical Android/iOS acceptance, exact-source release security review, truthful whole-package declarations and reviewer access remain open. The iOS owner artifact is development signed, not an App Store/TestFlight distribution export. No release submission occurred. |

Public HTTPS image handling remains distinct from host-local output. The
candidate has host-image seams without production composition; an emitted
MEDIA path is not authority to read an arbitrary host file. Existing model
confirmation concurrency and report failure/ordinary-chat acknowledgement UX
are retained as finite qualification/repair findings, rather than falsely
reported as observed device failures or fixed by removing functionality. No
additional report submission was made.

### Host model readiness follow-up

This supersedes the preceding pending-enablement checkpoint for one owner
deployment. At 05:02 UTC, an explicitly approved single Boolean
`platforms.hmp.extra.model_management.enabled=true` and supported graceful
gateway restart completed. Sanitized before/after evidence verified unchanged
other settings, model/provider selections, device grants and profile membership.
Three profiles reported send/jobs/model readiness; one pre-existing unavailable
profile remained unavailable. This is point-in-time host readiness, not proof of
phone current/options rendering, an actual model change or later host state.

### AR1 source progress remains separate

Mobile readiness warnings and local remediation guidance are published in draft
[PR77](https://github.com/MahdiHedhli/HermesBotMobile/pull/77), exact source
`3c5e5b9edd84fb93d1351b3b97120449bb0ee369`. Recorded exact-head hosted CI runs
`37185279303` and `37185274691` succeeded after the reviewed large-text repair.
This source/fake verification does not establish a deployed HMP readiness
endpoint, physical pairing/permissions, a mutating Fix action or release
acceptance. It is not part of the 8671061 installed candidate. AM1, AT1, BI1 and
complete media composition retain their separate implementation and integration
gates. No automatic grant, flag change, restart, model selection or job execution
is introduced by this documentation checkpoint.


### AR1 reviewed local source checkpoint (2026-10-04 UTC)

The separate HMP read-only readiness slice is now locally committed at
`982bc034a7e87346e6959ca5477a0b3bc5e33bab`. Independent review accepted the
exact source checkpoint in the recorded synthetic environment. The focused
readiness/actor checks passed. The full unit run had 2,433 passes, 16 skips and
one offline packaging-cache setup failure; the unchanged packaging case passed
in a separate offline follow-up using the existing cache. This is composite
source evidence, not a new all-suite pass or supported-version matrix.

The slice provides authenticated fixed capability and authorized bot-scoped
readiness diagnostics. It keeps host flags, device controls, endpoint
configuration and unprobed API reachability distinct. It adds no live probe,
automatic grant, actual request send, administrator Fix, model selection or job
execution. Mobile warnings/local guidance remain the separate PR77 source.
The HMP checkpoint remains local; neither slice has been composed into the
installed 8671061 candidate or deployed as part of it. Runtime, native version,
physical phone, security and release gates remain open.

The latest verified owner iOS candidate is **2026100401** on iPhone15, superseding
the earlier 2026100204 installation checkpoint above. Android remains the exact
signed beta code2 candidate; the attached physical Android is USB-debugging
unauthorized and has not been installed or qualified.


## Reviewed UI repairs and next test candidate (2026-10-04 UTC)

A separate local test candidate has been built from the retained `8671061`
baseline and reviewed finite corrections. Current functionality, declared
dependencies, native permissions and connection routes are preserved. The
original candidate and its artifacts remain available; new feature branches
have not been silently mixed in.

| Item | Current evidence and limits |
| --- | --- |
| Report delivery feedback | Reviewed app repair `ba148c4` passed 109 focused fake tests and changed-file analysis. Uncertain delivery remains explicit; ordinary chat gives local feedback for confirmed report acknowledgement. No extra report was submitted, and physical acceptance remains open. |
| Model confirmation | Reviewed app repair `47cbd97` passed 22 focused app tests, five fake client tests and changed-file analysis. One confirmation remains reserved through settlement and retires when its owning view changes. No actual host model or permission was changed; native persistence and phone checks remain open. |
| Android local beta 1.0.0 / code 3 | APK and AAB built through the unchanged guarded wrapper; scans and expected upload-signature checks passed. Earlier cache-related guard refusals were retained and regenerated outputs rechecked. A bundle reader warning remains under assessment. Neither artifact is installed, uploaded, submitted or physically qualified. |
| iOS local dogfood 1.0.0 / 2026100402 | Guarded build and strict signature check passed. This is an owner development artifact, not a distribution export. It has not been installed; the last verified owner installation remains `2026100401`. UI, preserved saved content and native hardware checks remain pending. |

Independent source-composition review accepted the exact finite changes. Binary
review, physical Android/iOS journeys, hardware outcomes, exact-source security
review, whole-package declarations and reviewer access remain separate release
gates. Source/fake results cannot establish installed functionality. The last
scoped USB Android inventory was unauthorized; no device installation or UI
test followed from that inventory. Public-image handling and uncomposed
host-local media remain distinct; the latest candidate does not enable complete
media upload or host-local image rendering.

### AT1 prerequisite documentation reconciled

The no-op producer remains an unwired source prerequisite in draft
[PR99](https://github.com/MahdiHedhli/hermes-hmp/pull/99). Its separate pure host
request/frame DATA codec is now documented in draft
[PR100](https://github.com/MahdiHedhli/hermes-hmp/pull/100), exact source
`ffb2d9b2bb24d8f35488427a6c234024d3fba196`. The codec passed 135 focused
synthetic/inventory checks; exact-head hosted CI `37179997382` succeeded with
2,807 passes, 17 skips and four warnings. Counts overlap. These are not genuine
operator authentication, native card, socket or paired-phone delivery checks.

The proposed command is `hermes hmp approval-test begin`; it is not runnable.
Caller contract v4 permits bounded source authoring, while CLI/IPC admission,
current target-device/session authority, normal approval-lifecycle binding and
phone projection remain unfinished. AR1, AM1, BI1 and full media integration
retain their separate scope and qualification gates. No grant, provider, model,
job, live host or release changed through this documentation update.


## Approval-test transport and installed-device checkpoint (October 4, 2026)

AT1 now has a separately reviewed private local operator transport in
[draft PR101](https://github.com/MahdiHedhli/hermes-hmp/pull/101), exact source
`41daef17ab2e2fcd69f7d54c67469c8418cfd7e4`, stacked on codec PR100. Root passed
227 focused transport, codec and module-inventory tests after independent
source review. Counts overlap earlier codec results. The original 225-pass,
two-failure run is preserved; the independently reviewed fixture-only repair
restricts failed-write injection to the intended accepted response, without
weakening assertions or changing the accepted production source.

This covers isolated macOS Unix sockets and kernel peer UID, Linux credential
mocks, bounded framing and fake-handler lifecycle. Exceptional response or
notification errors retain the operation until its owned cleanup joins;
unknown finalization retires the generation. It is not a Linux kernel run,
a genuine different-UID adversarial test, native producer settlement or a
phone-card check. No current CLI, adapter or server registers the endpoint,
and no production handler exists. Current device/profile/session admission,
normal lifecycle binding, typed phone projection/answer/cancel and physical
qualification remain unfinished. The proposed `hermes hmp approval-test begin`
command is still unavailable; AT1-T003 remains open.

The finite cross-platform candidate's artifact identity review is accepted
only for local dogfood. iOS build `2026100402` was subsequently installed on
the owner iPhone 15 Pro Max through a data-preserving update. Fresh native app
metadata confirms that build. The source-declared non-secret public pairing
registry was byte-identical before and after, with two saved instances. There
was no uninstall, launch, UI/hardware test, keychain or sealed-content read;
this does not verify all saved chat content. The iPhone 12 Pro remains pending
its last lock/access blocker. Android code 3 artifacts remain uninstalled and
unqualified; the connected USB Android still reports unauthorized debugging.

The AAB streaming-reader warning, exact-source security review, whole-package
provider/declaration and reviewer-access gates, and physical Android/iOS
journeys remain open. Public HTTPS image rendering has earlier owner evidence;
host-local `MEDIA:` rendering and complete photo/file upload remain unfinished.
No host grant, actual model, job, provider or release changed in this checkpoint.


## LB1 priority and pure-source checkpoint — October 4, 2026

The owner selected device-local bot sections and bundled static icons next,
then host-local chat images. Essential release checks continue in parallel.
AT1 remains at its separate reviewed transport checkpoint; no runnable approval
test command or complete phone card flow is inferred from it.

LB1 planning is in `specs/044-local-bot-sections-icons`. Root locally committed
`5e6458c`: a bounded immutable section/preference model, eight closed static
icon IDs, typed edits, and a canonical depth-limited codec. Independent source
and execution-evidence reviews accepted that pure slice for local commit. The
exact focused run passed 16 tests; strict analysis found no issues. The prior
failed analysis is preserved as a failed gate, followed by the reviewed correction.
No dependency, SDK, native permission or host capability was changed.

This is source progress, not a phone feature or release pass. The dedicated
sealed storage/CAS/controller seam is still a proposal for independent review;
section management, icon picker, roster/header/details integration, encrypted
persistence and actual Android/iOS UI/accessibility checks remain outstanding.
Custom sections are the stated working assumption, not an invented owner answer.
Pending request-access rows and saved-content disclosure must stay intact.
Host-local `MEDIA:` text remains unrendered until authenticated producer and
bounded serving authority are composed; a path string alone grants no file read.

The separate release lane freshly observed only Android version code 1 Active
and 2026092917 Inactive in Play's complete two-bundle inventory; local code 2/code 3
were absent. Publishing showed 13 changes not submitted. Saved Sign in details
No does not certify the QR/paired-host flow is freely reviewable. Exact consumer
validation still needs a verified resolved dependency closure; physical device,
provider/Data safety, reviewer-access and security-release gates remain open.
No upload, submission, provider/permission change, live host operation or report
Send occurred in these source/release-read checkpoints.

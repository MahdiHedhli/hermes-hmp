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
analysis. Combined hosted CI and physical delivery remain open. Hosted mobile run `37060192148` failed a
legacy immediate-permit-release test and the inherited late-TLS test. Root's
corrected legacy test and its full 42-case binding suite pass locally; exact
hosted verification remains open. Handoff SDK paths were sanitized at `19a5ba6`; hosted security hygiene passes
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
| Draft; not enabled live | Approvals and choices | Exact-request approval/question routes and mobile cards are implemented on focused branches. Historical archive and independent Git-install parent matrices passed; the later combined candidate's run 4 failed (24 of 27 integration cases passed, three errored in setup before gateway start, no receipt; cause unconfirmed) and it remains unqualified. Scoped fixture-diagnostic tooling `d8b8b08` is in [draft PR #60](https://github.com/MahdiHedhli/hermes-hmp/pull/60). A new unchanged complete seven-stage/27-case attempt on `d8b8b08` and independent Git `8afaab3703e336d72a72c812dd2dd249f04f166a` ended terminal (exit 1): identity, boundary and behavior passed; selected integration ran exactly 27 cases (24 passed, 3 setup errors, 0 failures, 0 skipped); later stages were not reached, the run is not complete and no receipt was written. The setup errors stopped in offline per-profile seeding at its 120-second limit before gateway start; the cause is unconfirmed and this attempt does not prove the earlier Run 4 cause. An earlier partial rerun of only the three T7 cases passed (3 of 3, provisional fixture-only) but does not qualify. Tool-only nonfatal diagnostics are accepted in draft [PR #61](https://github.com/MahdiHedhli/hermes-hmp/pull/61) at `f4730eb`, with final 15 diagnostic tests and 300 earlier fixture / 23 CI-tool passes separately. That earlier attempt is no longer a current running-status claim. The latest private package at `c1d3d0b` has 239 byte-exact files, 32 changed-input native checks passed, and a native scan with 121 caution findings and zero critical findings. It is not installed; live approval activation and device verification remain open. The controller send slice is accepted in draft [app PR #55](https://github.com/MahdiHedhli/HermesBotMobile/pull/55), and a plain-text Phone chat screen is accepted in draft [app PR #56](https://github.com/MahdiHedhli/HermesBotMobile/pull/56), both with synthetic evidence only. The production approval manifest stays empty. No approval capability is part of the released migration. |
| Draft mobile renderer | Linked chat images | The mobile candidate renders public HTTPS assistant images after explicit tap with bounded, credential-free fetching. A CDN MIME-mismatch repair ([app PR #57](https://github.com/MahdiHedhli/HermesBotMobile/pull/57), `dba5c93`) passed 106 root tests and focused Opus review; the same production-loader CDN probe now decodes successfully. Signed local build `2026093003` is installed on one owner iPhone; the owner screenshot confirms public-CDN rendering, and public TestFlight is unchanged. Local image dogfood is separate from live gateway approval admission (the same local build also contains the existing approval screen, unusable while the live host gate is closed); generated local media handles, video/audio and uploads are not included. |
| Planning | Phone photo/file attachments | Root reproduced native adapter primitives in isolated discovery tests on an archive, not a Git attestation (73 checks, 30 focused tests, 315 fixture and CI-tool tests together; no full CI gate claimed); the complete upload, busy-handler, admission and read-back flow remains unqualified. Canonical Desktop-owned multimodal admission and reusable authorized media history remain upstream contract gaps. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).


## Source checkpoint — 2026-10-02, approval notification contract

[HMP draft PR #74](https://github.com/MahdiHedhli/hermes-hmp/pull/74) now publishes the independently accepted relay contract text at `92a719f`. It uses one atomic effective acceptance instant, `max(raw_wall_now, last_now)`, for nonce admission and seal bounds; monotonic time for rolling rate budgets; explicitly qualified normal-clock retention/capacity bounds; and separate APNs connections for each allowed `(app, env)` pair. Clock stalls/steps may prolong retention and fill the hard cache cap, which fails closed without evicting live nonces. Optional leaf pins constrain an otherwise valid TLS chain/hostname. This is contract acceptance only: source, causal tests/vectors, interoperability, provider/device/deployment/release and owner choices remain pending. No push capability is enabled.

The related mobile image branches passed hosted CI: public repair `16c2095` in [37064933078](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37064933078), and accepted Phone image wiring plus the fixture repair `11cbf29` in [37065452665](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37065452665). The actual successful-TLS late-delivery cancellation case passed. The former fixture collision is resolved; native serving/allocation, physical device and release gates remain. No new deployed media or approval capability is claimed.

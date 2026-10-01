# Gateway observations for Nous Research

HMP is a mobile gateway plugin for Hermes. These are proposals for upstream discussion, not claims that Hermes currently provides every requested API. Findings were checked against Hermes `main` at `81f481b2` and the qualified older `8afaab37` build on 2026-09-28. Search, bot lifecycle, and plugin installation were rechecked against `main` at `39faafb6` on 2026-09-29; the approval session stream was rechecked at `ac0cfa7` on 2026-09-29. The Bot Mode baseline tag `v2026.8.31` was also inspected on 2026-09-29; later releases may differ. Chat media and attachment handling was checked against exact Hermes `ca705dbf7ef86425b381b542712aff310f1ee52c` on 2026-09-30, together with an owner-observed display result in HMP's own mobile app.

The [unified gateway research](https://github.com/MahdiHedhli/hermes-hmp/blob/main/HermesUnifiedGatewayResearch.md) and Nous's [one-gateway PR](https://github.com/NousResearch/hermes-agent/pull/106742) support one profile-scoped execution authority. The companion [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) puts a future mobile client behind an authenticated gateway API but treats remote entry as follow-on work. The requests below concern that remaining remote contract; they do not ask Nous to create another session owner.

| Area | Current constraint | Requested upstream contract |
| --- | --- | --- |
| Bot tabs | Desktop stores its bot tab list locally. A remote client cannot identify or create the same tabs. | Server-side tab metadata and list/create operations shared by Desktop and other clients. |
| Safe sends | The canonical Bot Chat has a live-owner mailbox, but other session chat routes do not use the same active-session lease. Session chat also lacks an idempotency key. | Apply the active-session lease to session chat and support retry-safe idempotency. |
| Forward compatibility | HMP's read bridge calls undocumented Hermes internals. Bot Chat reads still require a reviewed bridge fingerprint and exact Git SHA, so a newer but unreviewed build can be refused. An HMP-owned pairing path is in draft that warns but does not grant bot access on such a build. At the Bot Mode baseline tag `v2026.8.31`, 8 of the current bridge's 16 fingerprinted Hermes source paths do not exist, including the split gateway and session modules; merely accepting that version cannot make the present bridge work. An isolated exact-tag adapter fixture exercises the old platform registry, HMP's pinned-TLS listener, and HMP-owned pairing/token/revoke while Bot Chat and controls return the compatibility refusal. In a repeatable disposable two-profile gateway fixture, the full old gateway connected HMP, served both profiles, completed pairing with a certificate-pinned synthetic client, and still returned `/bots` 503 (`hermes_build_unsupported`). Its base Python environment lacked `aiohttp`, which Hermes treats as an optional messaging dependency and does not install from the plugin manifest; the isolated run installed the declared requirement before boot. The exact-tag source also contains a profile-home resolver that falls back to the root home for a missing or invalid explicit profile, so HMP must not substitute it for a fail-closed profile lookup. An isolated two-profile ingress probe found that the old adapter stamps a profile only when an explicit route matches; a matching `scope_id` alone does not stamp one. Its authorization check can use a transport-profile secret scope that differs from the routed runtime scope, and a routed allow-all scope would admit a never-enrolled user if evaluated without the transport stamp. These are scratch findings, not evidence of a qualified Bot Chat bridge or physical-device pairing. The release-watch fixture suite can qualify a build, but it is not part of the runtime-only plugin. A version number or import-signature probe alone cannot establish profile isolation and authorization behavior. | Expose versioned, authenticated, profile-scoped roster, canonical Bot Chat, authorization, and history contracts with declared capability guarantees. A missing, invalid, unserved, or unrouted explicit profile should be rejected rather than served from another home. Include the effective ingress authorization scope in that contract. HMP could then warn on an unvalidated newer release, exercise those supported contracts, and reserve fail-closed behavior for missing or failed capabilities rather than every new Git SHA. |
| Bot lifecycle | Profile creation is available to Desktop's TUI gateway and dashboard, while deletion uses the profile CLI or Desktop host. The gateway platform API server has no profile lifecycle routes. A profile by itself is not a Bot Mode bot with a canonical chat. | Authenticated, owner-scoped profile create/delete routes with explicit identity, partial-delete results, and a canonical Bot Chat outcome. |
| First Bot Chat | The API server can look up a hidden chat by exact title and create a titled session, but creation, hidden state, and profile-following behavior are not one atomic create-or-get operation. Desktop coordinates this through its own TUI RPC and adopts a concurrent winner. | A supported, idempotent create-or-get API for a bot's hidden canonical chat that preserves the profile's current runtime settings. |
| Turn state | A client can read history but cannot reliably tell when a session is waiting for approval or clarification. | A session-scoped turn-state read or event stream. |
| Bot Chat approvals | The two older fixture builds (`04fa849e` and `7e8c8f07`) have no Bot Chat session-stream approval notifier. Untagged `ac0cfa7` registers one and emits an answerable `approval.request`, and an isolated fixture passed on it. HMP has no released, approval-qualified build entry; Desktop-owned cross-client answers remain an upstream gap. The `/v1/runs` route has a different lifecycle and is not an equivalent replacement for a guarded Bot Chat send. | Preserve the session-chat notifier with stable request IDs and offered choices, and provide a supported, authenticated exact-ID answer contract with Hermes-owned expiry and termination semantics across execution owners. |
| Pairing access | A platform plugin currently synthesizes an inert inbound message to create a standard pairing request. | A documented plugin API to request access for a platform user. |
| Gateway setup status | On `8afaab37`, the resolved config default can say multiplexing is on while the gateway's boot preflight keeps it standalone. Explicitly setting `true` can skip that preflight and change profile API ingress and secret scoping. HMP needs this state to guide setup safely. | Expose the effective served-profile topology and migration blocker through a machine-readable, read-only operator interface. Keep topology changes in Hermes's own migration workflow. |
| Plugin install footprint | A bare `owner/repo` install stages the repository root, and the plugin guard scans its tests, tools, and docs along with runtime code. HMP keeps those files public for review, so its full-tree install prompts on numerous heuristic findings. | Let a root plugin manifest declare a bounded install file set. Verify the selected paths and source revision, reject escaping symlinks or imports outside the selected tree, and scan exactly the tree that will be activated. Keep dangerous findings blocking. |
| Message origin | Session rows do not identify the client surface that submitted a turn. | An optional, non-model-visible client/surface field stored with user rows. |
| Updates | A mobile client discovers new rows by polling. | A session change feed or bounded long poll. |
| Scheduled-job parity | On qualified `8afaab37`, the profile API's `POST /api/jobs` passes delivery and repeat settings but ignores `context_from`; the PATCH allowlist excludes it. Desktop's scheduler writer supports previous-run continuity. HMP uses that exact-build, profile-scoped writer for its owner-gated preview, so it cannot assume this path is stable across Hermes updates. | Accept and validate `context_from` in the authenticated profile-scoped jobs create/update API, with the same lifecycle checks and scheduler notification as Desktop, and return the persisted job. This removes HMP's private writer dependency. |
| Private session search | `SessionDB.search_messages` logs up to 200 characters of the query at INFO when a search crosses its slow threshold (`hermes_state_search.py` in the checked build). Hermes-wide search could put private conversation terms in host logs. HMP can separately page its authorized canonical Bot Chats and match on the phone without sending a query. | Log timing, path, and row count without query text, and cover the slow path with a regression test before any remote feature invokes native Hermes search. |
| Session management | The profile-scoped API server already lists sessions, reads messages, changes title/pin/archive/hidden state, and deletes sessions. Its `/fork` ends the source session, so it cannot implement a non-destructive branch. Project moves, export, and opening a session in a terminal are not API server operations. | Preserve the existing safe metadata routes; add a non-destructive branch operation and explicit project/export capabilities where appropriate. A canonical Bot Chat must not be accidentally archived or deleted by a remote client. |
| Scoped session read | HMP's draft session-ref repair checks whether a ref still selects an allowed Bot Chat before reading its messages, but Hermes exposes those as separate database reads. An archive, retitle, or replacement between them can leave one page based on the earlier eligibility decision. Per-bot authorization still applies; [HMP's extra session routes](https://github.com/MahdiHedhli/hermes-hmp/pull/51) now require an explicit boolean-true host opt-in, and the phone's picker remains hidden. | Provide an authenticated, profile-scoped read that selects an allowed session and returns its eligibility, canonical lineage, and message page from one consistent snapshot. Unknown and no-longer-eligible refs should have the same refusal. |
| Chat media and attachments | Displaying a linked image was an HMP renderer gap, not a Hermes API gap; a bounded renderer is now in an unreleased mobile draft. Sending attachments into a Desktop-owned canonical Bot Chat, and reading generated local media back later, have no equivalent canonical contract on the inspected source. | Attachment-aware canonical single-owner admission and stable, authorized, reusable generated-media reads with capability flags. See [Chat media and attachment parity](#chat-media-and-attachment-parity). |
| Canonical remote attachment | Current HMP reaches a qualified legacy Bot Chat path; the unified runtime PR is a local/gateway cutover, while remote Desktop/web/mobile entry is staged separately. | Expose authenticated, profile-scoped remote attach/submit/event/control operations with explicit capability negotiation, target-session authorization, durable request identity, and replay-or-snapshot recovery. Keep one execution owner. |

## Bot Mode baseline verification

The exact `v2026.8.31` source has two session-key modes: a standalone named
profile uses the legacy `agent:main` namespace, while multiplexing uses the
routed profile namespace. HMP's scratch fixture now verifies both through the
old `SessionStore._generate_session_key`, cross-checks an explicit HMP route
with Hermes's matcher, and reads synthetic compression lineage from two
profile databases opened read-only. Database and sidecar hashes are unchanged
by those reads. This remains unwired: the paired full-gateway fixture still
refuses Bot Chat, and authorization plus canonical history must be proven
through that gateway before support for this tag can be listed. A supported
versioned read contract would eliminate these private per-build adapters.
The pinned old runtime uses Hermes's safe DELETE journal fallback for its
SQLite 3.50.4, and a writer-open read interleave passes in that mode. HMP has
not overridden Hermes's WAL guard; a patched-runtime WAL test remains open.

HMP is also drafting an [opt-in exact-commit compatibility matrix](https://github.com/MahdiHedhli/hermes-hmp/pull/46)
and a [consent-gated advisory report](https://github.com/MahdiHedhli/hermes-hmp/pull/47)
for unlisted builds. Neither qualifies a build or relaxes Bot Chat authorization.
The matrix executes candidate code, so an unreviewed commit needs a separate
disposable environment without live credentials. Its receipt is unsigned and
can be forged by code running as the same user. Community reports therefore
cannot replace a versioned, authenticated Hermes remote contract.

## Canonical Bot Chat through compression

At the qualified `8afaab37` source and the `f97608f` snapshot, Hermes's
`publish_compression_child` inserts a continuation row without copying the
parent's `hidden` column. The hidden canonical Bot Chat root can therefore have
a visible child; the exact `Bot Chat` title may also move onto that child when
Hermes transfers a title along the compression lineage. A bridge that requires
the *titled child* to be hidden can lose the existing chat after compaction.
[HMP's draft scope repair](https://github.com/MahdiHedhli/hermes-hmp/pull/49)
checks the hidden lineage root and refuses inconsistent lineage answers; its
isolated read fixture passed on two qualified build labels. A supported
profile-scoped API that returns canonical Bot Chat identity, lineage, and
visibility together would remove this per-build inference.

That identity check and the later message read currently use separate Hermes
database snapshots. [The draft HMP scope repair](https://github.com/MahdiHedhli/hermes-hmp/pull/49)
records the remaining race: an archive or retitle after eligibility is checked
may leave one message page readable under the prior state. This is a
read-consistency limit, not a bypass of HMP's per-bot authorization. A
profile-scoped canonical read that binds selection and rows to one snapshot
would close it without HMP copying Hermes's private database logic.

## Approval and clarify events

Desktop-owned Bot Chat turns still surface prompts through Desktop's process-local channel; a remote client cannot answer those same prompts through session chat. The two older Hermes builds used for HMP's draft approval matrix lacked a Bot Chat session-stream notifier. The inspected untagged Hermes `main` revision at [`ac0cfa7`](https://github.com/NousResearch/hermes-agent/commit/ac0cfa7db94cefa90cf3e35191f38b53888b9e17) registers one on the session-chat stream and emits `approval.request` for the existing run-approval route. An [HMP socket-free handler probe and isolated gateway/PTY matrix](https://github.com/MahdiHedhli/hermes-hmp/pull/44) passed on this exact archive: 32 focused checks and 17/17 integration cases, including T7 Bot Chat, T8 Phone chat, a same-device cross-profile exact-ID refusal, and fail-closed gates. The fixture used a fake model and synthetic credentials; no runtime compatibility entry was added. The tag inspected in that earlier check (`v2026.9.24`) predated the session-stream change; this file makes no claim about current release status. Each exact installed candidate, whether tagged or source, needs its own qualification; HMP does not require a future tag. Live multiplex profiles, physical devices, and Desktop-owned cross-client prompts also still need qualification or an upstream contract. This is not yet a released mobile approval capability.

Current HMP status (draft, not released): an independent approval manifest gates prompt reads, exact-ID answers and Phone sends (AP-3, AP-4 and AP-6). The production manifest is empty, so no production approval is admitted, live approval is not enabled, and there is no execution-owner fallback. Loaded memory is not attested. Ordinary guarded sends remain independent. [Draft route-qualification PR #53](https://github.com/MahdiHedhli/hermes-hmp/pull/53) captures one source baseline at the first supported factory call, prevents listener reconnects from redefining it, and caches successful dependency probes while rechecking the manifest and source on every call. Ambiguous normalized clarification labels are refused rather than guessed.

- **Current HMP candidate (draft).** [HMP PR #56](https://github.com/MahdiHedhli/hermes-hmp/pull/56) at `86f2a23760369749018c2e97d895696ffb0c9970` fixes an HMP bug: a stock queued `_gateway_accepted=False` was treated as a definitive refusal. Stock Hermes admission is known only for strict `True`; `False`, missing or non-boolean values are unknown. Where an AdmissionTicket is available, only a reported, enumerated known refusal proves no admission; `refused_other`, missing, unfamiliar or timed-out outcomes remain unknown. An unknown send is stored under the same id as unknown, is not observed, and is never retried automatically. This is not an upstream requirement. The root full suite passed 1493 tests with 13 skips and one existing warning.
- **Historical archive (Run 10).** The root-checked archive matrix reports all seven stages passed with exact 27/27 integration JUnit cases, on exact Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a` with HMP runtime `86f2a23`. It is a disposable, fixture-only run (fake model, synthetic credentials) with an unsigned receipt. It **cannot qualify a git-install**. The independent-clone Git-install matrix (Run 2) has also passed all seven stages and the exact 27 required integration cases without failures, errors or skips. Its receipt binds the independent clone's full SHA; it does not admit a live installation or the later build-identity fix. It is not live or release qualification.
- **Combined candidate history.** Identity fix `3e66e6b` and independent Git-install tooling were combined in `6a83cec`. Run 3 selected all 27 cases: 25 passed and two errored during native-listener setup at the unchanged 45-second deadline. Reviewed tooling `853aa2d` records process-aware startup outcomes without extending that limit. Run 4 on combined candidate `847696d` passed identity, boundary and behavior; 24 of 27 integration cases passed and three T7 cases errored before gateway startup. Offline per-profile seeding stopped with build-process exit 1. These are different from Run 3's readiness errors. Neither run issued a final receipt; the discarded child output leaves Run 4's cause unconfirmed.
- **Accepted diagnostic tooling.** `d8b8b08` ([draft PR #60](https://github.com/MahdiHedhli/hermes-hmp/pull/60)) limits the offline builder's environment and retains failed-build output in a new private 0600 file under a descriptor-validated private directory. Exceptions carry closed phase/status metadata. Root independently passed 312 fixture/CI-tool tests, configured Ruff, private-content and plugin-surface scans.
- **Historical `d8b8b08` attempt: terminal failure (superseded as latest by the `f4730eb` pass below).** An unchanged complete seven-stage/27-case attempt on `d8b8b08` and independent Git `8afaab3703e336d72a72c812dd2dd249f04f166a` ended terminal with exit 1.
  - Identity, boundary and behavior passed.
  - Selected integration ran exactly 27 cases: 24 passed, 3 setup errors, 0 failures, 0 skipped. Later stages were not reached; the run is not complete and no receipt was written.
  - In every final private log root inspected, the offline per-profile seed step timed out at its 120-second limit before the gateway started. The exception metadata is public and closed. The three final logs are preserved privately and are not published.
  - The cause is not confirmed. This newly captured run does not prove the original Run 4 cause.
- **Bounded diagnostic reproduction.** Three real offline builds in a scratch environment passed in 15.7-16.6 s with seeding at 2.11-2.15 s, and the timer was never reached. Database file and row metadata alone does not locate a stuck frame or measure time from kill to exit. No native bug or cause is claimed. Tool-only nonfatal 90-second faulthandler diagnostics are root-accepted in draft at `f4730eb` ([HMP PR #61](https://github.com/MahdiHedhli/hermes-hmp/pull/61)); final root checks passed 15 focused diagnostic tests, with 300 earlier fixture and 23 CI-tool passes recorded separately. A later unchanged complete attempt on `f4730eb` is recorded below; the 120-second deadline is unchanged, with no SIGABRT or core dump, relaxed deadline, retry or gate change.
- **Partial rerun, not qualification.** The three formerly setup-failing T7 cases passed earlier against the same independent Git commit (3 passed, zero failures, errors or skips, snapshot unchanged, provisional fixture-only receipts, allowlisted parent environment). That recorded result does not qualify: it is not all 27 cases or seven stages, writes no final receipt, enables nothing and does not identify any failure cause. The partial run alone was not qualification; the later full fixture pass below supersedes it for fixture status, while live and release gates remain pending.
- **Historical: full matrix passed on `f4730eb`.** An unchanged complete seven-stage attempt on tooling `f4730eb` ([draft PR #61](https://github.com/MahdiHedhli/hermes-hmp/pull/61)) against the independent Git `8afaab3703e336d72a72c812dd2dd249f04f166a` exited 0: all seven stages passed, exactly 27 selected integration cases ran with 27 passed and no errors, failures or skips, and a final fixture receipt was written and independently validated against current fingerprints and case identities. Limits: the receipt is unsigned fixture-only evidence (fake model, synthetic credentials), not a live, process, release or device attestation, and the public approval manifest remains empty. The original seed-timeout cause was not found; the nonfatal diagnostics did not hit a stall. PR #61 is tooling only. This does not erase the earlier failed runs above.
- **Current integrated candidate (2026-10-01).** [HMP draft PR #65](https://github.com/MahdiHedhli/hermes-hmp/pull/65) combines the approval bridge with the mobile app's HMP features and root-only new-profile route preparation. Root verified a fresh full Git-install matrix at `f584b91c5b5b157444b3875528ec034c6b83c4f9` against independent Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`/Python 3.14.7: all seven stages and exactly 27 required gateway cases passed, without failures, errors or skips. The actual JUnit selection and current-source receipt were independently checked. An earlier run of this candidate failed because its generic fixture pairing explicitly declined host controls; only approval fixtures now opt into primary-device owner enrollment, with production permissions unchanged. Approval ownership still requires the configured owner list and no explicit host denial; a controls grant alone does not open it. Both production write manifests remain empty. The unsigned fixture result is not package, live host, device, memory or release admission; separate owner-local packaging and device acceptance remain next. Earlier failures and receipts retain their exact-revision limits.
- **Private package tooling (2026-10-01).** [HMP draft PR #68](https://github.com/MahdiHedhli/hermes-hmp/pull/68) derives a private candidate with only the two qualification `builds` arrays changed. Root and Opus reverified the full receipt against the clean integrated source, the strict package delta and the package's own exact-Git parser match. The source receipt is stale for the separate package digest and is not relabelled. Root pinned the candidate's tree/plugin/manifest hashes; `verify` alone reports hashes and does not pin a prior package. The public source manifests remain empty. This is candidate evidence only, with live flags/grants, drain/restart, native crypto/artifact evidence and real phone acceptance still required.
- **Remaining limits.** Other fixture helpers still inherit their caller environment; the parent was manually contained for this rerun. Captured streams remain unbounded in memory, and `--showlocals` can expose test internals. Earlier historical results do not qualify other candidates; the historical `f4730eb` fixture pass and current integrated candidate are validated separately above; it is fixture-only and not final live admission, and all privacy, memory and environment limits above still apply. The public approval manifest remains empty; no fixture receipt is promoted into a live installation.

- Earlier Run 8 (source `ac0cfa7`, runtime draft `8934993`) is historical. It predates these diffs and cannot qualify them.
- Source checks do not attest already-loaded module bytes: a full gateway process restart is required after source/plugin changes. The final combined runtime candidate, live profiles, physical devices and release review remain.
- **Mobile.** [PR #50](https://github.com/MahdiHedhli/HermesBotMobile/pull/50) (draft) holds the combined S2/S3 store API at `a1f9515`; the root full run passed 967 client (1 skip) and 587 app (3 skips) tests. The separate Phone chat read controller is reviewed in [app PR #52](https://github.com/MahdiHedhli/HermesBotMobile/pull/52) at `7429b3f`: root passed the full client (1,013 / 1 existing skip), app (692 / 3 existing skips) and dev-support (8) suites before a small reconnect repair, then all 48 controller tests on the final candidate. Opus independently cleared the bounded read/concurrency surface. Reads preserve the sealed Bot Chat and Phone pending records; a stored Phone `sending` is displayed as unknown without a POST or store rewrite. The controller send slice is accepted in [draft app PR #55](https://github.com/MahdiHedhli/HermesBotMobile/pull/55) at `91f8cd0`: root's final client run passed 1,147 tests with one existing skip, and the sealed store passed 8. Its evidence uses a synthetic server and crypto; no real-device crypto, Keychain, process-restart, live-gateway proof or live approval admission is claimed. The Phone chat screen is accepted and pushed in [draft app PR #56](https://github.com/MahdiHedhli/HermesBotMobile/pull/56) at `56177bf`, based on PR #55's `91f8cd0`: root passed 60 widget tests and clean analysis; Opus cleared the preceding cover, dialog and cleanup candidate, then root independently reviewed the final departure fence. The screen shows plain-text Phone rows only; images remain the existing Bot Chat dogfood (`acc9543`, build 2026093002) on two owner iPhones after explicit tap, and the live approval gate stays closed. S6 reconciliation is assigned and in progress. The new Phone composer is not deployed; its physical-device and release gates remain open.

The [earlier ac0 fixture evidence](https://github.com/MahdiHedhli/hermes-hmp/pull/44) cannot qualify the current candidate.

**Future priority notification (not existing).** A future urgent-approval notification would carry only a minimal payload hint to fetch fresh state over APNs or FCM. The hint is not authority, carries no sensitive fields, and is not part of any current build, which is foreground-only. It needs a push provider and credential-custody design plus physical-device testing. No ETA.

**Watch exploration (not implemented).** A standalone Family Setup watch without its own iPhone is future exploration only. An optional parent companion phone does not prove an always-on relay. No ETA.

This is the next major HermesBot Mobile feature after beta release work. We
request a supported, authenticated, session-scoped contract that carries exact
request IDs, offered choices, session/profile ownership, and authoritative
expiry and settlement across Desktop and remote clients. The current-main
session-stream candidate passed an isolated fixture matrix; each exact installed
candidate still needs wrong-ID, cross-profile, timeout, disconnect, restart, and live-owner
handoff qualification. HMP must not infer approvals from tool text or create
another execution owner.

## Chat media and attachment parity

Checked against exact Hermes `ca705dbf7ef86425b381b542712aff310f1ee52c` on 2026-09-30. The source census and owner observation are supplemented by isolated native primitive tests on an archive with matching `ca705dbf` provenance; that archive is not a re-attested Git install. No live gateway upload was exercised.

**Display was the mobile app's gap.** The owner observed that an assistant's HTTPS Markdown image string reaches the HMP mobile app intact but was shown as literal text, because the app rendered plain text and fenced code only. That needed a mobile renderer change, not a new Hermes API. It is now addressed in draft, not released: [mobile PR #51](https://github.com/MahdiHedhli/HermesBotMobile/pull/51) at `acc9543` (root full run: app 690 passed / 3 skipped, client 967 passed / 1 skipped; clean app analysis; an independent review cleared the bounded renderer and its policy exception).

- **Scope.** It renders public HTTPS images from canonical assistant Markdown, only after an explicit tap. It uses a separate public-PKI transport without Hermes credentials or Hermes instance pins; per-hop public-only DNS with single resolution; TLS server-hostname checks; at most 3 redirects; 8 MiB and 15 s limits; PNG, JPEG and static WebP only; 20 MP, 8192-pixel edge and 2048 decode bounds; at most 2 fetch-and-decode operations; lifecycle fences and cache clearing.
- **Not included.** No automatic or background fetch of public URLs, no browser, video, audio, native upload or localhost media.
- **Evidence.** A signed local dogfood build was installed on one connected owner iPhone, and the app's metadata was confirmed. No new external TestFlight build with these approval or media changes has been submitted. The same installed build also contains the existing approval screen, which is unusable while the live host gate is closed. The owner reported a public-CDN card failing to load. Root reproduced a 200 response with an allowed PNG header but JPEG image bytes; the current equality check returns `unsupportedType`. The focused fix is root-accepted at `dba5c93` ([app PR #57](https://github.com/MahdiHedhli/HermesBotMobile/pull/57)): allowed raster MIME and signatures are checked independently, preserving all other bounds. Root passed 106 focused cases; Opus cleared the exact code/test hashes. The production CDN probe now downloads and decodes the image successfully. Signed and scanned local build `2026093003` is installed and launched on one owner iPhone. The owner screenshot confirms the public CDN image renders on the phone; the separate local `MEDIA:` output remains text-only. This is not a TestFlight update. Authorized local host media, NAT64 and app-switch snapshot proof remain open.
- **Limits that remain.** The existing native hooks and the Desktop-owned canonical handoff's string-only constraint and session API's rejection of file parts are unchanged. Linked video and audio look feasible, but codecs, URL authorization and expiry, and device behavior are unverified.

**Priority:** approvals first, then media/file/photo attachment support (planning only: spec 028), then full desktop-composer parity. Phone-side Photos, Files and pasted-image selection is possible app work, but upload and native adapter media-fixture qualification are not complete. HMP does not plan a second execution owner beside a Desktop-owned canonical chat, or browser-control artifact reuse.

**Composer inventory.** Desktop's composer plus menu offers Files, Folder, Images, Paste image, URL and Prompt snippets, and `@` inline file references. HMP plans to cover all of these and does not claim any as complete. Phone-local file, photo and clipboard selection and draft snippets need app work. Host-folder references need grant-scoped handles. Canonical uploads are separately gated on the upstream contract below.

**Existing building blocks.** Hermes's `gateway/platforms/event.py` `MessageEvent` has `media_urls`, `media_types` and `media_text_inlined` plus photo, video, audio and document types. `gateway/platforms/base.py` has `cache_document_from_bytes`, `cache_image_from_bytes` and `cache_media_bytes` (`cache_media_from_bytes` is not present in that source), and native image, video, document and audio send methods. A different `cache_media_bytes` (different signature and return type) lives in `gateway/platforms/media_cache.py`, so a plugin must name the module. These are plugin building blocks. HMP's current Phone-chat inbound event is text-only and it overrides no native outbound media hook; its bridge's `_text_of` drops non-text structured parts, and `_rows` carries no media handles. A bounded native adapter delivery path, with profile-, conversation- and device-authorized opaque handles for generated local files, is needed. The current native platform extension can be investigated without a core change, but it does not by itself provide canonical Desktop media or history.

**Native primitive evidence, not upload qualification.** Root reviewed and reproduced an isolated
fixture on the `ca705dbf` archive: 73 checks across real cache helpers, `MessageEvent`, inbound
preparation, the runner's queue-policy method and durable-row flush helpers. All 12 exercised
source files were byte-identical before/after. Root passed 30 focused fixture tests and 315
fixture/CI-tool tests together; this is not the full CI-equivalent suite. The private scratch home
was removed, no Python-level IP attempt occurred and no model or full gateway was started.
Python socket instrumentation is not an OS sandbox and does not cover DNS, C extensions or
subprocesses. An earlier wider worker run reported four failures that did not reproduce; the cause
is unconfirmed and no full CI gate is claimed. The archive provenance is not a Git attestation.
Evidence is on the unmerged discovery branch at `9d91ca1`:
[fixture and limitations](https://github.com/MahdiHedhli/hermes-hmp/blob/test/phone-attachment-native-primitives/docs/research/phone-attachment-native-primitives-2026-09-30.md).

- *Validation and private storage.* The document helper kept hostile names inside the profile
  cache but accepted a document above the configured image cap. Under umask 022, the tested
  file was 0644 and its cache directory 0755; native did not enforce private modes. Newlines
  survived in a name and reached the document note. The image helper rejected cap+1 and invalid
  magic, but accepted a magic prefix with an undecodable body. HMP must enforce bounds, MIME/
  content checks, decode/pixel/metadata policy, generated names and private storage before
  delivery. Only paths HMP created may become event media paths; inbound preparation trusted
  an outside-cache path in this isolated test. No live exploit or universal build claim is made.
- *Inline contract.* Absent or None text-inline flags made the same claim as True without
  actually inlining content. False changed the note; binary notes ignored the flag. An adapter
  that does not inline text must explicitly set `media_text_inlined=[False]`.
- *Busy sessions.* The real base fallback merged media; the runner's tested queue method merged
  matching-scope PHOTO/TEXT while documents used FIFO. Different scope or gateway-control flags
  prevented merge. The merged event kept only the first client identifier. A later client send
  therefore cannot be reconciled merely by that merged event's id. Full busy authorization, ack,
  steering and durable admission were not exercised, and `defer_policy` was absent on this build.
- *Persisted identity.* Actual flush helpers wrote/read real SessionDB rows with controlled agent
  shapes. Documents stored the prepared host-path note; an image-part list plus a string override
  projected to caption plus `[screenshot]`, without a path or attachment identity. Client ids
  round-tripped as `platform_message_id`. This was not a real agent turn or an HMP read-back;
  model-dependent enrichment, profile re-homing, cache sweep and audio/video remain unproven.

Separately, a source census and persistence fixture ran on independent Git Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`. [HMP draft PR #62](https://github.com/MahdiHedhli/hermes-hmp/pull/62) (commit `5a688c7`) records five synthetic scenarios through real native Desktop and Phone turns, including failed writes and Desktop deferred tools. The model and image provider were synthetic; Phone used a stand-in adapter, not `HmpAdapter`. Root accepted this research, not a media feature. Observed:

- On normal turns the assistant call row and the tool row are linked by call id, the tool row carries the executing tool name `image_generate`, and the tool-row flush precedes the Desktop completion frame and the Phone reply and media sends. With default deferred tools the Desktop assistant call is named `tool_call` (the single-entry bridge) while the tool row is `image_generate`, so linkage cannot require the assistant call name. A follow-up ([HMP draft PR #63](https://github.com/MahdiHedhli/hermes-hmp/pull/63), commit `97316ad`; four new native Desktop/Phone cases; root 37 non-native plus the 1 native aggregate of those four cases passed, with the older five-case aggregate deselected) saw the modern one-entry `calls` bridge execute and record an `image_generate` row linked to the outer call id, while a two-local-entry batch was rejected before any provider call and left an error row, which must not become a candidate. A matching id alone is not execution proof. On Phone, a bridged image was generated and persisted but native auto-append media sends were 0 (the reason it keys on the outer assistant call name is source inference, not an isolated causal native experiment); that differs from the direct-send shape and does not contradict it. This does not require upstream delivery for an HMP history-based route, which remains unimplemented and unqualified. Still unseen: other providers, flush failure for these shapes, connector batches, `HmpAdapter`.
- The full tool result parsed as one JSON object with `image` near the start, while its first 4000 characters did not parse: any parse has to see the uncapped result.
- A failed tool-row flush left the cache file and the assistant call row but no tool row, and the Phone path still sent media. A cache file or a native delivery is therefore not evidence of a stored row.

A later accepted G2 storage characterization ([HMP draft PR #64](https://github.com/MahdiHedhli/hermes-hmp/pull/64), commit `b437888`; synthetic seed, native `SessionDB` methods only) found that an active call/result pair can be retired or re-cloned, and that a closed compression parent keeps active rows, so "active" is meaningful only at the current tip. An imported session with a parent edge can change the Hermes resume tip, and foreign image values are stored verbatim, so stored values are not serving authority. A same-inode restore rolled back row ids, conversation generation and rewind count while the examined file identity fields stayed unchanged, so no monotonic epoch is assumed or invented, and sampled sequential reads give no atomic snapshot claim. This is not generation, HMP adapter, authorization or service qualification, and it needs no new producer hook; current local `MEDIA:` text remains unsupported. Branch handlers, a different-file or swapped-inode restore, and concurrency remain open.

Accepted G3 research now addresses selected file/raster hazards: [HMP draft PR #66](https://github.com/MahdiHedhli/hermes-hmp/pull/66), `6470379`, pins flat selected-profile cache descriptors and bounds regular single-link reads; [draft PR #67](https://github.com/MahdiHedhli/hermes-hmp/pull/67), `8a74190`, checks a static PNG/JPEG/WebP structural subset with 8 MiB, 8192 edge, 20 MP declared dimensions, 10000 units and 64 JPEG scans. Late file mutation and an empty-SOS bounds error were repaired causally and independently reviewed. These are research prototypes, not a host decoder, authority or integrity proof against a trusted same-account writer. A many-scan availability case motivated the conservative cap; no phone freeze was observed. Public CDN bytes bypass host validation, so a separate phone preflight is reviewed in [app draft PR #62](https://github.com/MahdiHedhli/HermesBotMobile/pull/62), still uninstalled.

Limits: no native media network, grant or wire qualification. G4 active-history linkage/rechecks are the next native-storage research slice; fresh device/profile/conversation authorization and complete worker/buffer transport lifetimes remain unimplemented. The earlier `ca705dbf` fixture is not evidence for `8afaab37`. We do not claim that an upstream change is required for a possible HMP-owned route; a generic reusable upstream media contract remains the request below. The only end-to-end evidence so far is public-CDN image display in the mobile app, which is a separate path from local `MEDIA:` text.

These observations constrain our adapter design. They do not qualify a release, freeze the
upload wire or make an attachment send available on the phone. Canonical owner handoff and
reusable authorized media history still need the contract below.

**Source constraint on this build.** `api_server.py` `_session_chat_user_message` normalizes text and `image_url`/`input_image` lists and rejects `file`/`input_file`. `_admit_to_live_bot_chat` returns `None` for non-string content, and `tools/bot_live_delivery.py` `deliver_to_live_owner` requires a string. On this source, multimodal input therefore does not take the Desktop-owned canonical Bot Chat handoff. No live attachment submit or adversarial test was performed during this investigation; this describes a source constraint, not an exercised bypass. HMP must not use this path to create a second execution owner beside Desktop.

**Generic upstream request.** Attachment-aware canonical single-owner admission; per-profile and per-conversation media handles; and stable, reusable, authorized generated-media reads with retention, recovery and capability flags. The existing primitives do not substitute for that contract:

- `_resolve_media_to_data_urls` validates bounded `MEDIA` image tags in the API server's own completions. It does not cover all persisted history or Desktop-mailbox outputs, and does not cover video or documents.
- `/v1/artifacts` upload and download require browser-control to be enabled, an API bearer, and a principal/family match; receipts are one-shot, TTL-bound and held in memory. It is not a durable ordinary-chat media API, and HMP will not enable browser control to implement attachments.

Source references (exact commit): [`api_server.py` L493-L586](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L493-L586), [L663-L672](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L663-L672), [L890-L931](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L890-L931), [L2859](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L2859), [L3463-L3489](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L3463-L3489); [`event.py`](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/event.py); [`base.py`](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/base.py). Hermes's [deliverable-mode](https://hermes-agent.nousresearch.com/docs/user-guide/features/deliverable-mode) and [adding platform adapters](https://hermes-agent.nousresearch.com/docs/developer-guide/adding-platform-adapters) docs are contextual reading, not exact proof of HMP's behavior.

## Already usable without a new Hermes contract

### Newly created profiles

On the inspected `ca705dbf` build, the gateway can discover and serve a newly created profile
without adding its exact HMP route to the root configuration. Serving, routing and phone access
are separate states. HMP's [draft host-only routing command](https://github.com/MahdiHedhli/hermes-hmp/pull/52)
prepares that route without granting phone access or enabling multiplexing for the whole gateway.
The command is an unmerged draft. The correction at `4e270f0` removes every profile-config write:
it adds only an exact root route and preserves the profile's history settings. Root passed the
repository CI-equivalent suite (1,322 tests / 10 existing skips) and all 138 final route tests;
Opus cleared the bounded code review. The command itself was not verified live.
The profile flag must stay unchanged because it selects the session-history namespace.

History for a profile whose own multiplex flag is absent or false, on the same `ca705dbf` build
(an archive, so no Git SHA is attestable; bound by read-bridge fingerprint `d45f9a13…f11f627` and a
source-tree digest), was checked with a real-Hermes fixture in an isolated home: the native gateway
runner, `SessionStore` and `SessionDB`, the real HMP read bridge and the route helper, with synthetic
messages and no model turn, credential or Phone transport. Its Python socket instrumentation
recorded no attempted IP connections; it is not an OS network sandbox. Authorization was not tested.
Root independently reproduced 7 of 7 passing
with no skips. The result is split by where the history came from, and is identical for the flag
absent and false:

- **A, created by the root for a routed source.** The canonical conversation resolves (4 of 4 rows)
  and the conversation is visible in the Phone list. The profile's own flag is not needed.
- **B, created earlier by a standalone gateway of that profile.** Its rows are intact and readable by
  session id, but they sit under the legacy `agent:main` key. The canonical read is empty, not an
  error, and the Phone list does not show them. A first routed conversation then starts a new session
  and leaves the earlier one unlinked.

The route helper left the profile tree byte-, mtime-, inode- and mode-identical and wrote no flag or
history. Route-only preparation therefore does not make existing standalone history readable, and is
not a migration. One origin per case, one user and chat, and this one build were covered; the real
gateway loop, authorization and a physical device were not. Evidence:
[`C6-EVIDENCE.md`](https://github.com/MahdiHedhli/hermes-hmp/blob/test/flagless-profile-history/specs/005-new-profile-routing/C6-EVIDENCE.md)
on the unmerged `test/flagless-profile-history` branch. Disposable-host qualification of the full
gateway loop stays open.

**Generic upstream request.** A stable, versioned, profile-scoped read contract for legacy history:
for an authorized profile, resolve its canonical conversation and lineage whichever session-key
namespace created the rows, or report explicitly that legacy history exists and is not addressable.
It should need no change to the profile's multiplex flag and no history rewrite. Until then HMP treats
legacy history as unqualified rather than repairing it from the mobile side. This is an observation
from one build, not a new upstream submission.

On one selected host, a manual operator-scoped
root-route repair and distinct per-profile send keys were verified for passive reads and cross-key isolation,
and a native, explicitly requested access approval matched its request. A real owner send remains unverified.
This is an HMP setup/workflow finding, not evidence that Hermes must grant access automatically.

Automatic preparation and the bot-access permission card are an unimplemented proposal; nothing is
released. The plan has one host opt-in, per-bot keys and a running route activation. Gaps:

- **Route activation.** Root routes are read at startup. Profile rescan and plugin reload do not refresh them, and SIGUSR1 is a drain and relaunch. Activation needs a qualified route-refresh primitive or a separately evaluated, consented drain policy.
- **Access card.** The primary destination is the exact authorized bot chat, with central Requests as the aggregated fallback. It is a device-targeted ephemeral event for a separate host-selected approver role, not stored in the transcript, group chat or model context. It needs a host-only contract amendment.
- **Grant scope.** Native grants are user-scoped and can cover multiple paired devices. The card must say so.
- **Reject.** Native pairing has no per-request deny. `clear-pending` clears all requests and is not a substitute. A local dismissal is not a rejection. This is a generic upstream gap.
- **Settlement.** `PairingStore` locks only within a process, and the CLI approval makes two non-atomic JSON writes. An unknown outcome is never automatically resent. A cross-writer settlement API is needed.
- **Key writes.** Native `.env` writing lacks compare-and-swap and owner-0600 enforcement, so automatic key provisioning requires a qualified writer. Durable profile identity and safe same-name replacement are a separate gap.

### Scheduled jobs

The profile-scoped API server has list, create, edit, pause, resume, and delete
routes for scheduled jobs. HMP's mobile cron preview uses those existing
read/pause/resume/delete routes with an owner-device gate, a closed-by-default
host flag, and exact-build qualification. New jobs start paused. On qualified
builds, a narrow profile-scoped Hermes writer also saves Bot Chat delivery,
finite repeats, and previous-run continuity for create/edit. The feature works
without an upstream change on those builds, but a complete public API contract
for continuity would remove that version-specific writer. Delivery of mobile
push notifications remains a separate API gap. On the owner's qualified host,
two runs of a phone-created job completed with Bot Chat delivery receipts and
persisted replies. The second run's input contained the first answer,
establishing previous-run continuity in this preview. This does not make the
private writer a supported public API.

Bot default-model reads and writes are also possible on a qualified build using
Hermes's profile-scoped validation. HMP keeps this preview off by default and
does not send model credentials to the phone.

Named profiles need their own API server keys under the existing multiplexed
gateway contract. HMP now reports Bot Chat send availability per authorized bot
and requires its owner send switch on every build. This is an HMP/client fix;
it does not request a new Hermes API. A failed loopback connection after a
roster read remains a send-time failure.

## Additional API parity requests

- Make model overrides apply to live Desktop-owned turns as well as API-owned turns.
- Expose safe checkpoint rewind and non-destructive branch operations.
- Expose profile lifecycle, voice routes, and view-only bot-screen access through the API server with their existing safeguards.

Please discuss proposals in [repository issues](https://github.com/MahdiHedhli/hermes-hmp/issues). This file is the reviewable source for any companion public Gist.

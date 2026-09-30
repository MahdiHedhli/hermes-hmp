# Gateway observations for Nous Research

HMP is a mobile gateway plugin for Hermes. These are proposals for upstream discussion, not claims that Hermes currently provides every requested API. Findings were checked against Hermes `main` at `81f481b2` and the qualified older `8afaab37` build on 2026-09-28. Search, bot lifecycle, and plugin installation were rechecked against `main` at `39faafb6` on 2026-09-29; the approval session stream was rechecked at `ac0cfa7` on 2026-09-29. The Bot Mode baseline tag `v2026.8.31` was also inspected on 2026-09-29; later releases may differ.

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

Desktop-owned Bot Chat turns still surface prompts through Desktop's process-local channel; a remote client cannot answer those same prompts through session chat. The two older Hermes builds used for HMP's draft approval matrix lacked a Bot Chat session-stream notifier. Current untagged Hermes `main` at [`ac0cfa7`](https://github.com/NousResearch/hermes-agent/commit/ac0cfa7db94cefa90cf3e35191f38b53888b9e17) registers one on the session-chat stream and emits `approval.request` for the existing run-approval route. An [HMP socket-free handler probe and isolated gateway/PTY matrix](https://github.com/MahdiHedhli/hermes-hmp/pull/44) passed on this exact archive: 32 focused checks and 17/17 integration cases, including T7 Bot Chat, T8 Phone chat, a same-device cross-profile exact-ID refusal, and fail-closed gates. The fixture used a fake model and synthetic credentials; no runtime compatibility entry was added. The latest published tag, `v2026.9.24`, predates the session-stream change. A released build, live multiplex profiles, physical devices, and Desktop-owned cross-client prompts still need qualification or an upstream contract. This is not yet a released mobile approval capability.

Current HMP status (draft, not released): an independent approval manifest, currently empty, gates prompt reads, exact-ID answers and Phone sends (AP-3, AP-4 and AP-6). Ordinary guarded sends remain independent. [Draft route-qualification PR #53](https://github.com/MahdiHedhli/hermes-hmp/pull/53) captures one source baseline at the first supported factory call, prevents listener reconnects from redefining it, and caches successful dependency probes while rechecking the manifest and source on every call. Its current local suite passed 1,364 tests with 12 skips; focused independent review cleared the process-binding fixes as closed groundwork. Ambiguous normalized clarification labels are refused rather than guessed. This does not attest already-loaded module bytes: a full gateway process restart is required after source/plugin changes. Current real gateway behavioral/restart evidence, device checks and release review remain. The [earlier ac0 fixture evidence](https://github.com/MahdiHedhli/hermes-hmp/pull/44) predates this diff and cannot qualify it. Mobile integration of both approvals and questions is in progress; no build is admitted and no live approvals are enabled.

This is the next major HermesBot Mobile feature after beta release work. We
request a supported, authenticated, session-scoped contract that carries exact
request IDs, offered choices, session/profile ownership, and authoritative
expiry and settlement across Desktop and remote clients. The current-main
session-stream candidate passed an isolated fixture matrix; released builds
still need wrong-ID, cross-profile, timeout, disconnect, restart, and live-owner
handoff qualification. HMP must not infer approvals from tool text or create
another execution owner.

## Already usable without a new Hermes contract

### Newly created profiles

On the inspected `ca705dbf` build, the gateway can discover and serve a newly created profile
without adding its exact HMP route to the root configuration. Serving, routing and phone access
are separate states. HMP's [draft host-only routing command](https://github.com/MahdiHedhli/hermes-hmp/pull/52)
prepares that route without granting phone access or enabling multiplexing for the whole gateway.
The selected host's route repair and separately requested profile-scoped access approval were
verified; a client conversation and the draft command's isolated installation remain unverified.
This is an HMP setup/workflow finding, not evidence that Hermes must grant access automatically.

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

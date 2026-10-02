# Gateway observations for Nous Research

HMP is a mobile gateway plugin for Hermes. These requests come from implementing a client that reads and sends to the canonical Bot Chat. They are proposals for upstream discussion, not claims that Hermes currently provides these APIs. Legacy-path findings were checked against Hermes `main` at `81f481b2` and the qualified older `8afaab37` build on 2026-09-28; the approval finding was also reproduced on extracted stock-base `04fa849e` and experimental `7e8c8f07` builds. Search, bot lifecycle, and plugin installation were rechecked against `main` at `39faafb6` on 2026-09-29; later releases may differ.

The [unified gateway research](https://github.com/MahdiHedhli/hermes-hmp/blob/main/HermesUnifiedGatewayResearch.md) and Nous's [one-gateway PR](https://github.com/NousResearch/hermes-agent/pull/106742) support one profile-scoped execution authority. The companion [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) puts a future mobile client behind an authenticated gateway API but treats remote entry as follow-on work. The requests below concern that remaining remote contract; they do not ask Nous to create another session owner.

| Area | Current constraint | Requested upstream contract |
| --- | --- | --- |
| Bot tabs | Desktop stores its bot tab list locally. A remote client cannot identify or create the same tabs. | Server-side tab metadata and list/create operations shared by Desktop and other clients. |
| Safe sends | The canonical Bot Chat has a live-owner mailbox, but other session chat routes do not use the same active-session lease. Session chat also lacks an idempotency key. | Apply the active-session lease to session chat and support retry-safe idempotency. |
| Bot lifecycle | Profile creation is available to Desktop's TUI gateway and dashboard, while deletion uses the profile CLI or Desktop host. The gateway platform API server has no profile lifecycle routes. A profile by itself is not a Bot Mode bot with a canonical chat. | Authenticated, owner-scoped profile create/delete routes with explicit identity, partial-delete results, and a canonical Bot Chat outcome. |
| First Bot Chat | The API server can look up a hidden chat by exact title and create a titled session, but creation, hidden state, and profile-following behavior are not one atomic create-or-get operation. Desktop coordinates this through its own TUI RPC and adopts a concurrent winner. | A supported, idempotent create-or-get API for a bot's hidden canonical chat that preserves the profile's current runtime settings. |
| Turn state | A client can read history but cannot reliably tell when a session is waiting for approval or clarification. | A session-scoped turn-state read or event stream. |
| Bot Chat approvals | The inspected session-chat route does not register an approval notifier or emit an answerable pending approval event. The `/v1/runs` route has a different lifecycle and is not an equivalent replacement for a guarded Bot Chat send. | Register a per-run notifier on session chat, emit stable request IDs and offered choices, and provide an authenticated exact-ID answer route with Hermes-owned expiry and termination semantics. |
| Pairing access | A platform plugin currently synthesizes an inert inbound message to create a standard pairing request. | A documented plugin API to request access for a platform user. |
| Gateway setup status | On `8afaab37`, the resolved config default can say multiplexing is on while the gateway's boot preflight keeps it standalone. Explicitly setting `true` can skip that preflight and change profile API ingress and secret scoping. HMP needs this state to guide setup safely. | Expose the effective served-profile topology and migration blocker through a machine-readable, read-only operator interface. Keep topology changes in Hermes's own migration workflow. |
| Plugin install footprint | A bare `owner/repo` install stages the repository root, and the plugin guard scans its tests, tools, and docs along with runtime code. HMP keeps those files public for review, so its full-tree install prompts on numerous heuristic findings. | Let a root plugin manifest declare a bounded install file set. Verify the selected paths and source revision, reject escaping symlinks or imports outside the selected tree, and scan exactly the tree that will be activated. Keep dangerous findings blocking. |
| Message origin | Session rows do not identify the client surface that submitted a turn. | An optional, non-model-visible client/surface field stored with user rows. |
| Updates | A mobile client discovers new rows by polling. | A session change feed or bounded long poll. |
| Scheduled-job parity | On qualified `8afaab37`, the profile API's `POST /api/jobs` passes delivery and repeat settings but ignores `context_from`; the PATCH allowlist excludes it. Desktop's scheduler writer supports previous-run continuity. HMP uses that exact-build, profile-scoped writer for its owner-gated preview, so it cannot assume this path is stable across Hermes updates. | Accept and validate `context_from` in the authenticated profile-scoped jobs create/update API, with the same lifecycle checks and scheduler notification as Desktop, and return the persisted job. This removes HMP's private writer dependency. |
| Private session search | `SessionDB.search_messages` logs up to 200 characters of the query at INFO when a search crosses its slow threshold (`hermes_state_search.py` in the checked build). Hermes-wide search could put private conversation terms in host logs. HMP can separately page its authorized canonical Bot Chats and match on the phone without sending a query. | Log timing, path, and row count without query text, and cover the slow path with a regression test before any remote feature invokes native Hermes search. |
| Session management | The profile-scoped API server already lists sessions, reads messages, changes title/pin/archive/hidden state, and deletes sessions. Its `/fork` ends the source session, so it cannot implement a non-destructive branch. Project moves, export, and opening a session in a terminal are not API server operations. | Preserve the existing safe metadata routes; add a non-destructive branch operation and explicit project/export capabilities where appropriate. A canonical Bot Chat must not be accidentally archived or deleted by a remote client. |
| Canonical remote attachment | Current HMP reaches a qualified legacy Bot Chat path; the unified runtime PR is a local/gateway cutover, while remote Desktop/web/mobile entry is staged separately. | Expose authenticated, profile-scoped remote attach/submit/event/control operations with explicit capability negotiation, target-session authorization, durable request identity, and replay-or-snapshot recovery. Keep one execution owner. |

## Approval and clarify events

Desktop-owned Bot Chat turns can surface prompts only through Desktop's process-local channel. A remote client cannot answer those same prompts through session chat. The inspected session-chat route also lacks the notifier and approval events needed for API-owned Bot Chat turns. We propose durable, session-scoped pending prompt identifiers, event delivery for approval and clarify requests, and authenticated response routes that enforce the same authorization and expiry rules as Hermes itself. HMP's proposed Phone chat path is under security review and is not released; draft HMP security fixes do not resolve the missing Bot Chat notifier, so the interim server path remains disabled pending real-route qualification.

## Already usable without a new Hermes contract

The profile-scoped API server has list, create, edit, pause, resume, and delete
routes for scheduled jobs. HMP's mobile cron preview uses those existing
read/pause/resume/delete routes with an owner-device gate, a closed-by-default
host flag, and exact-build qualification. New jobs start paused. On qualified
builds, a narrow profile-scoped Hermes writer also saves Bot Chat delivery,
finite repeats, and previous-run continuity for create/edit. The feature works
without an upstream change on those builds, but a complete public API contract
for continuity would remove that version-specific writer. Delivery of mobile
push notifications remains a separate API gap.

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

# Gateway observations for Nous Research

HMP is a mobile gateway plugin for Hermes. These requests come from implementing a client that reads and sends to the canonical Bot Chat. They are proposals for upstream discussion, not claims that Hermes currently provides these APIs. Findings were checked against Hermes `main` at `8afaab37`; behavior may change in later releases.

| Area | Current constraint | Requested upstream contract |
| --- | --- | --- |
| Bot tabs | Desktop stores its bot tab list locally. A remote client cannot identify or create the same tabs. | Server-side tab metadata and list/create operations shared by Desktop and other clients. |
| Safe sends | The canonical Bot Chat has a live-owner mailbox, but other session chat routes do not use the same active-session lease. Session chat also lacks an idempotency key. | Apply the active-session lease to session chat and support retry-safe idempotency. |
| First Bot Chat | Desktop creates the hidden canonical Bot Chat through its own RPC. | A supported create-or-get API for a bot's canonical chat. |
| Turn state | A client can read history but cannot reliably tell when a session is waiting for approval or clarification. | A session-scoped turn-state read or event stream. |
| Pairing access | A platform plugin currently synthesizes an inert inbound message to create a standard pairing request. | A documented plugin API to request access for a platform user. |
| Message origin | Session rows do not identify the client surface that submitted a turn. | An optional, non-model-visible client/surface field stored with user rows. |
| Updates | A mobile client discovers new rows by polling. | A session change feed or bounded long poll. |
| Private session search | `SessionDB.search_messages` logs up to 200 characters of the query at INFO when a search crosses its slow threshold (`hermes_state_search.py` in the checked build). A phone search could put private conversation terms in host logs. | Log timing, path, and row count without query text, and cover the slow path with a regression test. HMP will add authorized, bounded search only after a qualified build includes this fix. |

## Approval and clarify events

Desktop-owned Bot Chat turns can surface prompts only through Desktop's process-local channel. A remote client cannot answer those same prompts through session chat. We propose durable, session-scoped pending prompt identifiers, event delivery for approval and clarify requests, and authenticated response routes that enforce the same authorization and expiry rules as Hermes itself. This is an upstream design request. HMP's proposed interim implementation is under security review and is not included in the initial public migration.

## Already usable without a new Hermes contract

The profile-scoped API server has list, create, edit, pause, resume, and delete
routes for scheduled jobs. HMP's mobile cron preview uses those existing routes
with an owner-device gate, a closed-by-default host flag, and exact-build
qualification. New jobs start paused. This feature does not require an upstream
change; delivery of mobile push notifications remains a separate API gap.

## Additional API parity requests

- Make model overrides apply to live Desktop-owned turns as well as API-owned turns.
- Expose safe checkpoint rewind and branch operations without ending the parent session.
- Expose profile management, voice routes, and view-only bot-screen access through the API server with their existing safeguards.

Please discuss proposals in [repository issues](https://github.com/MahdiHedhli/hermes-hmp/issues). This file is the reviewable source for any companion public Gist.

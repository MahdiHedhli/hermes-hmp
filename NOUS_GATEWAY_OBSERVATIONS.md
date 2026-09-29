# Gateway observations for Nous Research

HMP is a mobile gateway plugin for Hermes. These requests come from implementing a client that reads and sends to the canonical Bot Chat. They are proposals for upstream discussion, not claims that Hermes currently provides these APIs. The legacy-path findings were checked against Hermes `8afaab37` on 2026-09-28; behavior may change in later releases.

The [unified gateway research](HermesUnifiedGatewayResearch.md) and Nous's [one-gateway PR](https://github.com/NousResearch/hermes-agent/pull/106742) support one profile-scoped execution authority. The companion [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) explicitly places a future mobile client behind an authenticated gateway API, but treats remote entry-point migration as follow-on work. The requests below concern the remaining remote contract; they do not ask Nous to create a second session owner or duplicate work already in that PR.

| Area | Current constraint | Requested upstream contract |
| --- | --- | --- |
| Bot tabs | Desktop stores its bot tab list locally. A remote client cannot identify or create the same tabs. | Server-side tab metadata and list/create operations shared by Desktop and other clients. |
| Safe sends | The canonical Bot Chat has a live-owner mailbox, but other session chat routes do not use the same active-session lease. Session chat also lacks an idempotency key. | Apply the active-session lease to session chat and support retry-safe idempotency. |
| First Bot Chat | Desktop creates the hidden canonical Bot Chat through its own RPC. | A supported create-or-get API for a bot's canonical chat. |
| Turn state | A client can read history but cannot reliably tell when a session is waiting for approval or clarification. | A session-scoped turn-state read or event stream. |
| Pairing access | A platform plugin currently synthesizes an inert inbound message to create a standard pairing request. | A documented plugin API to request access for a platform user. |
| Message origin | Session rows do not identify the client surface that submitted a turn. | An optional, non-model-visible client/surface field stored with user rows. |
| Updates | A mobile client discovers new rows by polling. | A session change feed or bounded long poll. |
| Canonical remote attachment | Current HMP reaches a qualified legacy Bot Chat path; the unified runtime PR is a local/gateway cutover, while remote Desktop/web/mobile entry is staged separately. | Expose authenticated, profile-scoped remote attach/submit/event/control operations with explicit capability negotiation, target-session authorization, durable request identity, and replay-or-snapshot recovery. Keep one execution owner. |

## Approval and clarify events

Desktop-owned Bot Chat turns can surface prompts only through Desktop's process-local channel. A remote client cannot answer those same prompts through session chat. We propose durable, session-scoped pending prompt identifiers, event delivery for approval and clarify requests, and authenticated response routes that enforce the same authorization and expiry rules as Hermes itself. This is an upstream design request. HMP's proposed interim implementation is under security review and is not included in the initial public migration.

## Additional API parity requests

- Make model overrides apply to live Desktop-owned turns as well as API-owned turns.
- Expose safe checkpoint rewind and branch operations without ending the parent session.
- Expose profile management, voice routes, and view-only bot-screen access through the API server with their existing safeguards.

Please discuss proposals in [repository issues](https://github.com/MahdiHedhli/hermes-hmp/issues). This file is the reviewable source for any companion public Gist.

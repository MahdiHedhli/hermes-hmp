# Roadmap

HMP follows the [feature list](FEATURES.md), [unified gateway research](HermesUnifiedGatewayResearch.md), and [requests for Nous](NOUS_GATEWAY_OBSERVATIONS.md). The research describes a target architecture, not a remote API available to HMP today. At the September 28 checkpoint, Nous [PR #106742](https://github.com/NousResearch/hermes-agent/pull/106742) remained open; its companion [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) still placed remote clients in a later cutover. Recheck both before planning against a new Hermes build.

| Investment | Work | Boundary |
| --- | --- | --- |
| Continue now | Pairing, Bot Chat reads and guarded sends, exact-build compatibility, draft scheduled-jobs and default-model previews, install/setup, and release hardening. | Keep owner and per-bot gates; requalify each Hermes build. Do not expand the legacy send route to arbitrary sessions. |
| Continue when safe | Authorized, bounded search and read-only session browsing. | Search waits for the raw-query log fix. Existing session reads can remain, but avoid new metadata writes while canonical revision semantics are moving. |
| Small, adaptable groundwork | Capability discovery, installation → profile → session identity, and fixtures for lost acknowledgements, replay gaps, snapshots, and stale controls. | Reuse the existing persisted `client_message_id`, unconfirmed-send state, and snapshot/reset path. Do not invent authority admission IDs, event watermarks, or remote wire fields before Hermes exposes them. |
| Hold for supported upstream contracts | Any-tab sends, shared Desktop/mobile approvals and clarifications, durable FIFO UI, authoritative replay and generation controls, session metadata writes, non-destructive branching/rewind, remote attachments, and full bot lifecycle. | Session features need authenticated canonical remote entry and one execution owner. Bot lifecycle separately needs an atomic, authorized profile and canonical-chat contract. |

The draft approval bridge still has known security blockers. Its reusable phone UI can remain in development; do not enable the server preview or broaden its temporary gateway-control path. If the preview is retained, fix its authorization, expiry, bounds, and logging findings before any release. The upstream shared-control contract may replace much of that server path.

## Adoption gate for a new Hermes release

1. Confirm the canonical runtime and remote entry-point work have actually landed in the target release. A merged local authority alone does not prove that a phone can attach remotely.
2. Identify the authenticated installation, profile, and session; negotiate supported operations. A missing canonical capability fails explicitly and never falls back to an independent session host.
3. Requalify HMP read and guarded-write fingerprints, plus cron/model bridges, against the exact build. Keep the installed plugin and live Hermes unchanged during isolated testing.
4. Prove the [research acceptance cases](HermesUnifiedGatewayResearch.md#20-hmp-acceptance-tests-derived-from-upstream): Desktop/mobile share one session, lost acknowledgements do not duplicate execution, reconnect uses replay or snapshot, unknown work is not retried blindly, and stale controls cannot affect a newer generation. Include profile authorization and restart tests.
5. Only then add a versioned canonical-gateway adapter behind HMP's client boundary and plan a live switch with rollback. Keep legacy HMP behavior for qualified older builds without presenting its mailbox queue as canonical FIFO.

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

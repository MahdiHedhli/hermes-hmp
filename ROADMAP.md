# Roadmap

HMP follows the [feature list](FEATURES.md), [unified gateway research](HermesUnifiedGatewayResearch.md), and [requests for Nous](NOUS_GATEWAY_OBSERVATIONS.md). The research describes a target architecture, not a remote API available to HMP today. As of September 29, Nous [PR #106742](https://github.com/NousResearch/hermes-agent/pull/106742) is open with conflicts; its [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) places authenticated remote clients in a later cutover.

| Investment | Work | Boundary |
| --- | --- | --- |
| Current qualified Hermes | Pairing, Bot Chat reads and guarded sends, read-only setup and bot health checks, and owner-gated scheduled jobs and default-model previews. | Requalify each Hermes build and bridge fingerprint. Keep the owner and per-bot gates; do not widen the legacy send route to arbitrary sessions. |
| Release hardening | Integrate the draft features, run isolated gateway fixtures, then review the exact release candidate and device artifacts. | No live-host switch or external beta based solely on source tests. |
| Plugin updates | Add a read-only release-aware HMP update and compatibility check, then an explicit pinned update with rollback ([issue #18](https://github.com/MahdiHedhli/hermes-hmp/issues/18)). | `hermes update` does not advance the pinned plugin. Never silently update HMP across an unqualified Hermes boundary. |
| Installer footprint | Keep the current full-tree security scan and explain its caution findings to operators. | A quieter bare install needs Hermes to support a verified install file set; do not suppress scans or hide executable tests. |
| Search | The distinct authorized start page is in draft; the companion app draft matches locally across available Bot Chats or within one. | Keep older-HMP, compaction-reset, incomplete-scan, and request bounds visible. Hermes-wide search still needs the upstream raw-query log fix. |
| Approvals and choices | Converted to the minimum-version policy in source: `approvals` and `phone_chat` availability members, owner-only streaming, native-answer classification and generation and binding fences. Next: independent focused review, sampled evidence on locally present pinned builds, then an owner-local dogfood decision. | Security clearance; upstream capability flag and release containing the session-stream approval notifier; phone Phone-chat composer UI; no exact-build qualification is required |
| Bot lifecycle and session writes | Request complete remote bot create/delete and stable canonical session metadata operations. | A profile alone is not a Bot Mode bot; destructive or uncertain results need exact recovery. |
| Canonical gateway | Prepare capability discovery and fixtures for durable admission, replay or snapshot, and Desktop/mobile ownership. | Wait for an authenticated remote entry with one execution authority; do not invent admission IDs or event watermarks in HMP. |

## Adoption gate for a new Hermes release

1. Confirm canonical runtime and authenticated remote entry have landed in the target release.
2. Identify and authorize the exact installation, profile, and session; negotiate supported operations. Missing capabilities fail explicitly.
3. Re-run the HMP read/send, Cron, and model fixtures in an isolated Hermes home as tested-sample evidence.
4. Prove the [research acceptance cases](HermesUnifiedGatewayResearch.md#20-hmp-acceptance-tests-derived-from-upstream): shared Desktop/mobile session, no duplicate turn after a lost acknowledgement, replay or authoritative snapshot after reconnect, stale-control refusal, profile isolation, and restart recovery.
5. Add a versioned canonical-gateway adapter only after those checks pass, with a rollback for qualified older builds.

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

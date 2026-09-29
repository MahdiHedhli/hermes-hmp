# Roadmap

HMP follows the [feature list](FEATURES.md), [unified gateway research](HermesUnifiedGatewayResearch.md), and [requests for Nous](NOUS_GATEWAY_OBSERVATIONS.md). The research describes a target architecture, not a remote API available to HMP today. As of September 29, Nous [PR #106742](https://github.com/NousResearch/hermes-agent/pull/106742) is open with conflicts; its [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) places authenticated remote clients in a later cutover.

| Investment | Work | Boundary |
| --- | --- | --- |
| Current qualified Hermes | Pairing, Bot Chat reads and guarded sends, read-only setup checks, and owner-gated scheduled jobs and default-model previews. | Requalify each Hermes build and bridge fingerprint. Keep the owner and per-bot gates; do not widen the legacy send route to arbitrary sessions. |
| Release hardening | Integrate the draft features, run isolated gateway fixtures, then review the exact release candidate and device artifacts. | No live-host switch or external beta based solely on source tests. |
| Installer footprint | Keep the current full-tree security scan and explain its caution findings to operators. | A quieter bare install needs Hermes to support a verified install file set; do not suppress scans or hide executable tests. |
| Search | Add the distinct authorized start page for canonical Bot Chats, then match on the phone across those chats or within one. | Detect older HMP releases, compaction resets, incomplete scans, and bounds. Hermes-wide search still needs the upstream raw-query log fix. |
| Approvals and choices | Keep the reusable UI and security fixes in draft; require a passing real-route qualification. | Bot Chat still lacks a session-scoped prompt notifier. Do not enable an alternate execution owner or gateway-control shortcut. |
| Bot lifecycle and session writes | Request complete remote bot create/delete and stable canonical session metadata operations. | A profile alone is not a Bot Mode bot; destructive or uncertain results need exact recovery. |
| Canonical gateway | Prepare capability discovery and fixtures for durable admission, replay or snapshot, and Desktop/mobile ownership. | Wait for an authenticated remote entry with one execution authority; do not invent admission IDs or event watermarks in HMP. |

## Adoption gate for a new Hermes release

1. Confirm canonical runtime and authenticated remote entry have landed in the target release.
2. Identify and authorize the exact installation, profile, and session; negotiate supported operations. Missing capabilities fail explicitly.
3. Requalify HMP read/send, Cron, and model fingerprints in an isolated Hermes home.
4. Prove the [research acceptance cases](HermesUnifiedGatewayResearch.md#20-hmp-acceptance-tests-derived-from-upstream): shared Desktop/mobile session, no duplicate turn after a lost acknowledgement, replay or authoritative snapshot after reconnect, stale-control refusal, profile isolation, and restart recovery.
5. Add a versioned canonical-gateway adapter only after those checks pass, with a rollback for qualified older builds.

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

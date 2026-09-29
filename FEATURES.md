# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This page describes the plugin; the mobile UI is tracked in the private app repository.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Local QR offer, operator code comparison, and one key per device. |
| Available | Private transport | TLS instance-key pinning over a private network such as Tailscale. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the Hermes gateway. |
| Draft | Host setup check | Read-only build, identity, and pinned-listener diagnostic; profile routing remains an operator check. See [install](docs/INSTALL.md). |
| Preview | Bot Chat sends | Explicit owner gate on every build, profile-specific send status, freshness check, and retry-safe handling. A bot without a usable profile key reports read-only. Unsupported builds fail closed. |
| Preview, off by default | Scheduled jobs | Owner-gated list, create-paused, edit, pause, resume, and delete on an exact qualified Hermes build. |
| Preview, off by default | Bot default model | Owner-gated catalog and validated change within the selected bot's profile. New sessions use the choice. |
| Security blocked | Approvals and choices | Separate draft work needs a passing real-route qualification; Bot Chat lacks a Hermes session-stream prompt event. |
| Draft read support | Phone Bot Chat search | A distinct start-of-history page for authorized sessions lets the phone match locally without passing query text to Hermes. The companion app draft handles compaction, incomplete scans, and bounded paging; this is not Hermes-wide search. |
| Upstream gap | Hermes-wide search | Hermes logs raw query text on a slow search path; HMP cannot safely expose that full-corpus search yet. |
| Upstream gap | Create and delete bots | The profile-scoped API server lacks a complete profile lifecycle and canonical Bot Chat create-or-get contract. |
| Partly available | Session management | Read-only browsing exists. Metadata writes and non-destructive branching need a stable canonical remote contract. |

See the [roadmap](ROADMAP.md), [unified gateway research](HermesUnifiedGatewayResearch.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

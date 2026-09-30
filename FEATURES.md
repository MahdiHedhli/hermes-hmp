# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This page describes the plugin; the mobile UI is tracked in the private app repository.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Local QR offer, operator code comparison, one key per device, and a separate host decision for jobs and model controls. |
| Draft | Pairing before read qualification | A running HMP listener can complete cryptographic device pairing on an unqualified Hermes build. The host warns and records an owner-control denial; bot grants, Bot Chat, sends, jobs, and model controls remain unavailable until their Hermes adapter is qualified. The exact `v2026.8.31` gateway serves two profiles and completes pairing with a pinned synthetic client in a disposable home while refusing `/bots`; physical-device pairing and security review remain open. Its base environment needs HMP's declared runtime packages installed separately. The [older read-adapter investigation](docs/compat/29112bef.md) includes unwired strict profile and route checks, both old session-key modes, isolated ingress authorization, and two-profile read-only compressed history; it does not qualify Bot Chat. |
| Available | Private transport | TLS instance-key pinning over a private network such as Tailscale. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the Hermes gateway. |
| Qualification required | Newer Hermes builds | HMP can be installed, and the draft pairing lane does not depend on read qualification, but Bot Chat reads and controls require a reviewed bridge build. The release watch tests new tags; an unvalidated Git SHA is not admitted solely because its version is newer. A stable upstream profile-scoped API is needed for warning-only Bot Chat compatibility. |
| Draft | Host setup check | Read-only build, identity, and pinned-listener diagnostic; profile routing remains an operator check. See [install](docs/INSTALL.md). |
| Draft | Bot channel health check | Read-only per-bot send, jobs, and model prerequisites from the running gateway; enabled failures exit nonzero. See [install](docs/INSTALL.md). |
| Draft | HMP release check | Read-only `hermes hmp update check` compares the installed pin with the latest published stable release and its exact Hermes compatibility manifests. No release is published yet; it never installs automatically. |
| Preview | Bot Chat sends | Explicit owner gate on every build, profile-specific send status, freshness check, and retry-safe handling. A bot without a usable profile key reports read-only. Unsupported builds fail closed. |
| Preview, off by default | Scheduled jobs | Owner-gated list, create-paused, edit, pause, resume, and delete on an exact qualified Hermes build. New mobile jobs can deliver to Bot Chat or stay in run history, use a finite run count, and carry previous-run continuity. On the owner's qualified host, two scheduled runs completed with delivered Bot Chat replies; the second run consumed the first answer. Other builds still need qualification. |
| Preview, off by default | Bot default model | Owner-gated catalog and validated change within the selected bot's profile. New sessions use the choice. The owner confirmed saves in two bots on the qualified host. |
| Security blocked | Approvals and choices | The two older Hermes builds lack the Bot Chat prompt event. Untagged `main` at `ac0cfa7` passed the isolated HMP gateway/PTY matrix (17/17, including a same-device cross-profile refusal) in [draft PR #44](https://github.com/MahdiHedhli/hermes-hmp/pull/44). No released or live build is qualified; F3 remains disabled. |
| Owner preview | Phone Bot Chat search | A distinct start-of-history page for authorized sessions lets the phone match locally without passing query text to Hermes. The owner confirmed results on an iPhone. The companion app handles compaction, incomplete scans, and bounded paging; this is not Hermes-wide search. |
| Upstream gap | Hermes-wide search | Hermes logs raw query text on a slow search path; HMP cannot safely expose that full-corpus search yet. |
| Upstream gap | Create and delete bots | The profile-scoped API server lacks a complete profile lifecycle and canonical Bot Chat create-or-get contract. |
| Partly available | Session management | Read-only browsing exists. Metadata writes and non-destructive branching need a stable canonical remote contract. |

See the [roadmap](ROADMAP.md), [unified gateway research](HermesUnifiedGatewayResearch.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

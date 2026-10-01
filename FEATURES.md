# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This page describes the plugin; the mobile UI is tracked in the private app repository.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Local QR offer, operator code comparison, one key per device, and a separate host decision for jobs and model controls. |
| Available | Private transport | TLS instance-key pinning over a private network such as Tailscale. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the Hermes gateway. |
| Draft | Host setup check | Read-only build, identity, and pinned-listener diagnostic; profile routing remains an operator check. See [install](docs/INSTALL.md). |
| Draft | Bot channel health check | Read-only per-bot send, jobs, and model prerequisites from the running gateway; enabled failures exit nonzero. See [install](docs/INSTALL.md). |
| Preview | Bot Chat sends | Explicit owner gate on every build, profile-specific send status, freshness check, and retry-safe handling. A bot without a usable profile key reports read-only. Unsupported builds fail closed. |
| Preview, off by default | Scheduled jobs | Owner-gated list, create-paused, edit, pause, resume, and delete on an exact qualified Hermes build. New mobile jobs can send results to Bot Chat or keep them in run history, use a finite run count, and carry Hermes's previous-run continuity. |
| Preview, off by default | Bot default model | Owner-gated catalog and validated change within the selected bot's profile. New sessions use the choice. |
| Draft | Phone chat approvals and choices | Server implementation is under security review; it is not released or enabled. The dedicated mobile approval/clarification integration is written in draft app PR #48; physical-device and end-to-end release qualification remain pending. A separate approval qualification gate ships with an empty build list, so `hermes hmp compat` reports every build as unqualified for approvals. Prompt listing, answers, and Phone sends are wired to that gate and stay closed; no approvals are live. |
| Draft | Bot Chat approvals | Draft only and closed: the approval build list is empty, so HMP keeps Bot Chat approvals closed for every build. An earlier fixture pass on the untagged Hermes `ac0cfa7db94cefa90cf3e35191f38b53888b9e17` predates the current approval gate and qualifies nothing. Draft test tooling (`specs/005-approval-process-matrix`) defines an independent approval process matrix with a gateway restart lifecycle; the pre-safety baseline passed 27 real gateway cases. A later wire assertion failed because the fixture used UUIDv4 instead of the required UUIDv7; the corrected current candidate is awaiting a fresh full matrix. An exact Hermes build and HMP release candidate still need their own full qualification, device gate and security review. |
| Draft read support | Phone Bot Chat search | A distinct start-of-history page for authorized sessions lets the phone match locally without passing query text to Hermes. The companion app draft handles compaction, incomplete scans, and bounded paging; this is not Hermes-wide search. |
| Upstream gap | Hermes-wide search | Hermes logs raw query text on a slow search path; HMP cannot safely expose that full-corpus search yet. |
| Upstream gap | Create and delete bots | The profile-scoped API server lacks a complete profile lifecycle and canonical Bot Chat create-or-get contract. |
| Partly available | Session management | Read-only browsing exists. Metadata writes and non-destructive branching need a stable canonical remote contract. |

See the [roadmap](ROADMAP.md), [unified gateway research](HermesUnifiedGatewayResearch.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

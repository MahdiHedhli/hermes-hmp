# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Preview | Bot Chat sends | Explicit owner gate, supported-build fingerprint, freshness check, and retry-safe handling. Unsupported builds fail closed. |
| Preview, off by default | Scheduled jobs | An owner device can list, create paused, edit, pause, resume, and delete a bot's prompt jobs on a qualified Hermes build. |
| Preview, off by default | Bot default model | An owner device can inspect and change a bot's default model using Hermes's scoped validation on a qualified build. New sessions use the choice. |
| Planned | Approvals and choices | Design and security review are in progress. No approvals implementation is part of the released migration. |
| Upstream gap | Create and delete bots | The API server has no profile lifecycle route; a complete Bot Mode create also needs a safe canonical Bot Chat create-or-get operation. |
| Partly available | Session management | Hermes already exposes session metadata and delete routes. Non-destructive branching, project moves, and export need further upstream support and design. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

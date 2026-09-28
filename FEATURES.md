# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Preview | Bot Chat sends | Explicit owner gate, supported-build fingerprint, freshness check, and retry-safe handling. Unsupported builds fail closed. |
| Draft | Phone chat approvals and choices | Server implementation is under security review; it is not released or enabled. The app screens and end-to-end qualification are still pending. |
| Blocked upstream | Bot Chat approvals | The inspected Hermes session-chat route does not emit approval requests or provide an answerable pending prompt. HMP fails closed until that route is supported and qualified. |
| Requested upstream | Session management | Remote pin, rename, export, branch, project move, archive, and delete need a supported Hermes API contract. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

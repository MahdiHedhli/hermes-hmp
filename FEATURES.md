# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Preview | Bot Chat sends | Explicit owner gate, supported-build fingerprint, freshness check, and retry-safe handling. Unsupported builds fail closed. |
| Draft | Phone chat approvals and choices | Server implementation is under security review; it is not released or enabled. The app screens come from the legacy F9 source; current app integration and end-to-end qualification remain pending. A separate approval qualification gate ships with an empty build list, so `hermes hmp compat` reports every build as unqualified for approvals. Prompt listing, answers, and Phone sends are wired to that gate and stay closed; no approvals are live. |
| Draft | Bot Chat approvals | The exact untagged Hermes `ac0cfa7db94cefa90cf3e35191f38b53888b9e17` passes 17 selected real gateway fixtures, including Bot Chat approval. It is not a qualified or released build: the approval build list is empty, so HMP keeps Bot Chat approvals closed. A released build still needs its own full matrix, device gate and security review. |
| Requested upstream | Session management | Remote pin, rename, export, branch, project move, archive, and delete need a supported Hermes API contract. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

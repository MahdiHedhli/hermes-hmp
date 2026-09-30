# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Preview | Bot Chat sends | Explicit owner gate, supported-build fingerprint, freshness check, and retry-safe handling. Unsupported builds fail closed. |
| Draft | Phone chat approvals and choices | Server implementation is under security review; it is not released or enabled. The dedicated mobile approval/clarification integration is written in draft app PR #48; physical-device and end-to-end release qualification remain pending. A separate approval qualification gate ships with an empty build list, so `hermes hmp compat` reports every build as unqualified for approvals. Prompt listing, answers, and Phone sends are wired to that gate and stay closed; no approvals are live. |
| Draft | Bot Chat approvals | Draft only and closed: the approval build list is empty, so HMP keeps Bot Chat approvals closed for every build. An earlier fixture pass on the untagged Hermes `ac0cfa7db94cefa90cf3e35191f38b53888b9e17` predates the current approval gate and qualifies nothing. Draft test tooling (`specs/005-approval-process-matrix`) defines an independent approval process matrix with a gateway restart lifecycle; the pre-safety baseline passed 27 real gateway cases. A later wire assertion failed because the fixture used UUIDv4 instead of the required UUIDv7; the corrected current candidate is awaiting a fresh full matrix. An exact Hermes build and HMP release candidate still need their own full qualification, device gate and security review. |
| Requested upstream | Session management | Remote pin, rename, export, branch, project move, archive, and delete need a supported Hermes API contract. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Preview | Bot Chat sends | Explicit owner gate, supported-build fingerprint, freshness check, and retry-safe handling. Unsupported builds fail closed. |
| Draft; not enabled live | Approvals and choices | Exact-request approval/question routes and mobile cards are implemented on focused branches. Historical archive and independent Git-install parent matrices passed; the later combined candidate is still being qualified. The production approval manifest stays empty. No approval capability is part of the released migration. |
| Draft mobile renderer | Linked chat images | The mobile candidate renders public HTTPS assistant images after explicit tap with bounded, credential-free fetching. Local image dogfood is separate from live gateway approval admission; generated local media handles, video/audio and uploads are not included. |
| Planning | Phone photo/file attachments | Root reproduced native adapter primitives in isolated discovery tests (73 checks, 30 focused tests); the complete upload/admission/read-back flow remains unqualified. Canonical Desktop-owned multimodal admission and reusable authorized media history remain upstream contract gaps. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

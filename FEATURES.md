# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Preview | Bot Chat sends | Explicit owner gate, supported-build fingerprint, freshness check, and retry-safe handling. Unsupported builds fail closed. |
| Draft; not enabled live | Approvals and choices | Exact-request approval/question routes and mobile cards are implemented on focused branches. Historical archive and independent Git-install parent matrices passed; the later combined candidate's run 4 failed (24 of 27 integration cases passed, three errored in setup before gateway start, no receipt; cause unconfirmed) and it remains unqualified. Scoped fixture-diagnostic tooling `d8b8b08` is in [draft PR #60](https://github.com/MahdiHedhli/hermes-hmp/pull/60); a rerun of only the three formerly failing cases passed (3 of 3, provisional fixture-only), which is not a full 27-case or seven-stage result, writes no receipt and does not identify the old cause. A separate complete run is pending qualification. The controller send slice is accepted in draft [app PR #55](https://github.com/MahdiHedhli/HermesBotMobile/pull/55) with synthetic evidence only. The production approval manifest stays empty. No approval capability is part of the released migration. |
| Draft mobile renderer | Linked chat images | The mobile candidate renders public HTTPS assistant images after explicit tap with bounded, credential-free fetching. Local image dogfood is separate from live gateway approval admission (the same local build also contains the existing approval screen, unusable while the live host gate is closed); generated local media handles, video/audio and uploads are not included. |
| Planning | Phone photo/file attachments | Root reproduced native adapter primitives in isolated discovery tests on an archive, not a Git attestation (73 checks, 30 focused tests, 315 fixture and CI-tool tests together; no full CI gate claimed); the complete upload, busy-handler, admission and read-back flow remains unqualified. Canonical Desktop-owned multimodal admission and reusable authorized media history remain upstream contract gaps. |

See the [roadmap](ROADMAP.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

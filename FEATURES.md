# HMP features

HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This list describes the plugin in this repository. Mobile UI work is tracked separately.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Operator starts a local QR offer and confirms a short authentication string. Each paired device has its own key. |
| Available | Private transport | TLS with instance key pinning over a Tailscale connection. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the root Hermes gateway. |
| Draft | Host setup check | Read-only build, identity, and pinned-listener diagnostic; profile routing remains an operator check. |
| Preview | Bot Chat sends | Explicit owner gate, supported-build fingerprint, freshness check, and retry-safe handling. Unsupported builds fail closed. |
| Draft, unavailable on `main` | Scheduled jobs | [PR #3](https://github.com/MahdiHedhli/hermes-hmp/pull/3) adds owner-gated, exact-build-qualified job management; new jobs start paused. |
| Draft, unavailable on `main` | Bot default model | [PR #4](https://github.com/MahdiHedhli/hermes-hmp/pull/4) adds a scoped model catalog and validated write, off by default. |
| Security blocked | Approvals and choices | The draft server path has unresolved authorization, expiry, and resource bounds. Preserve reusable UI; shared cross-client controls need a supported canonical remote contract. |
| Waiting on Hermes | Search and full bot lifecycle | Search can log raw slow-query text; remote bot creation/deletion lacks a complete profile and canonical-chat contract. |

See the [roadmap](ROADMAP.md), [unified gateway research](HermesUnifiedGatewayResearch.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).

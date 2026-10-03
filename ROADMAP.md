# Roadmap

HMP follows the [feature list](FEATURES.md) and the [upstream requests](NOUS_GATEWAY_OBSERVATIONS.md). Ordering can change as Hermes exposes new gateway contracts.

| Area | Next step | Dependency |
| --- | --- | --- |
| Compatibility | Attempt implemented features on versions at or above the supported minimum; diagnose actual feature failures. | Required native APIs, authorization and security checks; exact-build receipts are sampled evidence, never availability allowlists |
| Approvals and choices | Complete owner-local activation and physical card/answer acceptance for the independently reviewed minimum-version candidate. | Genuine runtime/device evidence; remaining shared-session gaps are recorded in the upstream requests |
| Priority approval notifications | Implement the accepted shared-ownership contract through a bounded native observer, resolve the close/registry evidence gap, then complete remote relay/HPKE, app and provider work. | [Desktop experiment](FEATURES.md#desktop-pending-approval-experiment-2026-10-03-utc); strict cleanup/resource review, new runtime evidence, explicit provisioning and device/release gates |
| Push cryptography | Repair containment gates and execute independent Node/Python known-answer checks before actual consumer integration. | [151 unexecuted definitions](FEATURES.md#hpkejcs-vector-preparation); no crypto/runtime admission yet |
| Access and discovery hygiene | Integrate the reviewed default scoped-key floor after candidate acceptance; repair session-bound device-list metadata and full bounded profile inventories. | [Access checkpoint](FEATURES.md#retained-access-and-availability-repairs); focused independent review/CI, no live deployment assumed |
| Host-local generated images | Complete native HTTP/T12/Linux and signed phone loading/codec acceptance after reviewed serving and renderer slices. | Bounded authorized output delivery; documented native materialization/history gaps |
| Phone photo/file attachments | Freeze and implement the upload/admission route, preserving bot/profile/instance authority. | Native primitives are researched; canonical Desktop-owned multimodal admission remains an upstream gap |
| Bot tabs | Show and create the same tabs Desktop sees. | Shared server-side tab registry |
| Updates | Replace polling with a session change feed when available. | Hermes gateway event or long-poll API |
| Voice and screen | Add client features when authenticated API server routes are available. | Upstream routes and access controls |

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

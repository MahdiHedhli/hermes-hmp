# Roadmap

HMP follows the [feature list](FEATURES.md) and the [upstream requests](NOUS_GATEWAY_OBSERVATIONS.md). Ordering can change as Hermes exposes new gateway contracts.

| Area | Next step | Dependency |
| --- | --- | --- |
| Compatibility | Attempt implemented features on versions at or above the supported minimum; diagnose actual feature failures. | Required native APIs, authorization and security checks; exact-build receipts are sampled evidence, never availability allowlists |
| Approvals and choices | Complete owner-local activation and physical card/answer acceptance for the independently reviewed minimum-version candidate. | Genuine runtime/device evidence; remaining shared-session gaps are recorded in the upstream requests |
| Priority approval notifications | Complete the genuine Desktop-held interleave after the three passing native fixture cases, then remote relay/HPKE, app and provider work. | [Bounded native checkpoint](FEATURES.md#native-approval-push-origin-revocation-and-restart-checkpoint-2026-10-03-utc); explicit provisioning and device/release gates |
| Host-local generated images | Complete native HTTP/T12/Linux and signed phone loading/codec acceptance after reviewed serving and renderer slices. | Bounded authorized output delivery; documented native materialization/history gaps |
| Phone photo/file attachments | Freeze and implement the upload/admission route, preserving bot/profile/instance authority. | Native primitives are researched; canonical Desktop-owned multimodal admission remains an upstream gap |
| Bot tabs | Show and create the same tabs Desktop sees. | Shared server-side tab registry |
| Updates | Replace polling with a session change feed when available. | Hermes gateway event or long-poll API |
| Voice and screen | Add client features when authenticated API server routes are available. | Upstream routes and access controls |

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

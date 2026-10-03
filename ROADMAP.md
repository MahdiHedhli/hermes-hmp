# Roadmap

HMP follows the [feature list](FEATURES.md) and the [upstream requests](NOUS_GATEWAY_OBSERVATIONS.md). Ordering can change as Hermes exposes new gateway contracts.

| Area | Next step | Dependency |
| --- | --- | --- |
| Compatibility | Attempt implemented features on versions at or above the supported minimum; diagnose actual feature failures. | Required native APIs, authorization and security checks; exact-build receipts are sampled evidence, never availability allowlists |
| Approvals and choices | Complete owner-local activation and physical card/answer acceptance for the independently reviewed minimum-version candidate. | Genuine runtime/device evidence; remaining shared-session gaps are recorded in the upstream requests |
| Priority approval notifications | Implement the accepted shared-ownership contract through a bounded native observer, resolve the close/registry evidence gap, then complete remote relay/HPKE, app and provider work. | [Desktop experiment](FEATURES.md#desktop-pending-approval-experiment-2026-10-03-utc); strict cleanup/resource review, new runtime evidence, explicit provisioning and device/release gates |
| Push cryptography | Complete native containment gates and independent Node/Python known-answer checks before consumer integration. | [151 unexecuted definitions](FEATURES.md#hpkejcs-vector-preparation); supervisor ownership repair accepted in source and 46 isolated synthetic controls passed; six pure codec methods / 33 subtests passed; actual trusted startup attempts retained: v1 pre-fork descriptor refusal, v2 child setup failure with exact reap; bounded error attribution next; all crypto vectors remain unexecuted; no native startup or crypto qualification |
| Access and discovery hygiene | Complete native/device integration of the accepted combined scoped-key, device-list and full bounded inventory candidate. | [Access checkpoint](FEATURES.md#retained-access-and-availability-repairs); combined draft PR #96 passed exact-head CI (2,710 passed / 17 skipped); native/device integration and deployment remain pending |
| Host-local generated images | Complete native HTTP/T12/Linux and signed phone loading/codec acceptance after reviewed serving and renderer slices. | Bounded authorized output delivery; documented native materialization/history gaps |
| Phone photo/file attachments | Amend normative custody contracts and freeze pure interfaces/encrypted staging before implementation, preserving bot/profile/instance authority. | [Inspected Phone atomic admission gap](FEATURES.md#phone-attachment-admission-checkpoint-2026-10-03); native no-defer and attachment-first settlement, portable validator and complete-flow evidence pending; Desktop multimodal gap separate |
| Bot tabs | Show and create the same tabs Desktop sees. | Shared server-side tab registry |
| Updates | Replace polling with a session change feed when available. | Hermes gateway event or long-poll API |
| Voice and screen | Add client features when authenticated API server routes are available. | Upstream routes and access controls |

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

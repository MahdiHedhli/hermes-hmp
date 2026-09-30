# Roadmap

HMP follows the [feature list](FEATURES.md) and the [upstream requests](NOUS_GATEWAY_OBSERVATIONS.md). Ordering can change as Hermes exposes new gateway contracts.

| Area | Next step | Dependency |
| --- | --- | --- |
| Compatibility | Requalify guarded sends on each new Hermes build. | Exact build and bridge fingerprint review |
| Session browsing | Review the current-scope repair in [PR #49](https://github.com/MahdiHedhli/hermes-hmp/pull/49) and keep browsing opt-in (default off) and the phone picker dormant. Residual gap: the scope re-check and message read are not one atomic snapshot, so revocation is not immediate. | Upstream profile-scoped read transaction or atomic selector-plus-messages method; per-bot authorization and exact canonical Bot Chat qualification |
| Approvals and choices | Finish authorization, expiry, resource-bound, and log-leak security review before any release. | Security clearance; upstream session events for full parity |
| Bot tabs | Show and create the same tabs Desktop sees. | Shared server-side tab registry |
| Updates | Replace polling with a session change feed when available. | Hermes gateway event or long-poll API |
| Voice and screen | Add client features when authenticated API server routes are available. | Upstream routes and access controls |

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

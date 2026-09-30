# Roadmap

HMP follows the [feature list](FEATURES.md) and the [upstream requests](NOUS_GATEWAY_OBSERVATIONS.md). Ordering can change as Hermes exposes new gateway contracts.

| Area | Next step | Dependency |
| --- | --- | --- |
| Compatibility | Requalify guarded sends on each new Hermes build. | Exact build and bridge fingerprint review |
| Approvals and choices | Draft groundwork: a fail-closed, empty approval qualification list. Next, finish authorization, expiry, resource-bound, and log-leak security review and add behavioral qualification evidence before any release. | Security clearance; a qualified released Hermes build (the untagged `ac0cfa7` fixture pass is not one); upstream session events for full parity |
| Bot tabs | Show and create the same tabs Desktop sees. | Shared server-side tab registry |
| Updates | Replace polling with a session change feed when available. | Hermes gateway event or long-poll API |
| Voice and screen | Add client features when authenticated API server routes are available. | Upstream routes and access controls |

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

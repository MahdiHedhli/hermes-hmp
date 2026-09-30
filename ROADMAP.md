# Roadmap

HMP follows the [feature list](FEATURES.md) and the [upstream requests](NOUS_GATEWAY_OBSERVATIONS.md). **Hermes-native approvals and choices are the next major feature.** Compatibility and release checks continue alongside that work. Ordering can change as Hermes exposes new gateway contracts.

| Area | Next step | Dependency |
| --- | --- | --- |
| Compatibility | Requalify guarded sends on each new Hermes build. | Exact build and bridge fingerprint review |
| Approvals and choices | Complete the Hermes Bot Chat prompt lifecycle, then qualify and integrate the draft HMP routes. | Session-scoped request IDs and offered choices from Hermes; exact-ID answers and expiry; full real-route qualification and independent security review |
| Bot tabs | Show and create the same tabs Desktop sees. | Shared server-side tab registry |
| Updates | Replace polling with a session change feed when available. | Hermes gateway event or long-poll API |
| Voice and screen | Add client features when authenticated API server routes are available. | Upstream routes and access controls |

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

## Next major feature: approvals and choices

1. **Hermes contract:** Bot Chat's session stream must emit an answerable, session-scoped approval or clarification request with a stable ID and offered choices. Hermes must own authorization, expiry, settlement, and cleanup. The two builds previously tested by HMP lack the approval notifier; untagged Hermes `main` at [`ac0cfa7`](https://github.com/NousResearch/hermes-agent/commit/ac0cfa7db94cefa90cf3e35191f38b53888b9e17) now has a session-stream candidate that passes a [focused HMP handler probe](https://github.com/MahdiHedhli/hermes-hmp/pull/44), but it has no full real-route qualification. HMP cannot reconstruct prompts from tool text or switch execution to another route. See the [upstream request](NOUS_GATEWAY_OBSERVATIONS.md#approval-and-clarify-events).
2. **HMP qualification:** Keep the [draft security fixes in PR #8](https://github.com/MahdiHedhli/hermes-hmp/pull/8) disabled until the exact Hermes build passes the real gateway and PTY approval matrix, including cross-profile, stale-ID, denial, timeout, disconnect, and resource-bound cases. A provisional test receipt is not a runtime qualification.
3. **Mobile integration:** Expose only Hermes-native pending requests and offered choices through the existing draft phone UI. A response is bound to the active instance, conversation, and request ID; the phone shows success only after Hermes confirms settlement. See the [draft app UI in PR #9](https://github.com/MahdiHedhli/HermesBotMobile/pull/9).

Until those gates pass, the first beta does not advertise shared approval control. When a pending request is visible but unanswerable on mobile, the phone directs the user to another Hermes surface.

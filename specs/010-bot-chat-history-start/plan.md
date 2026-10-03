# Plan

1. Register a distinct GET route under the existing session-browsing kill switch. Route absence is capability detection for older clients.
2. Parse and bound `limit`; reject an `after` argument on this start route. Call `session_history` with `after=0` only after the bearer and normal per-device limiter.
3. Document the new response shape as SES-2a in HMP v1 and add a client-facing feature note.
4. Verify first/next page, authorization, foreign refs, kill switch, reset, and query bounds. Run unit, Ruff, plugin-surface, log, and zero-baseline privacy gates.

The phone will perform matching locally in a separate app branch. This PR adds no HMP search endpoint and changes no send path.

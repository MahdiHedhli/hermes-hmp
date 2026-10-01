# Plan

1. Add bounded, status-only per-profile health to the existing mode-0600
   listener record. Keep older records parseable, but never report them healthy.
2. Compute status in the running adapter on connect, served-profile changes,
   and its 15-second refresh. Reuse the route's flags, qualification checks,
   and profile-scoped endpoint. Do not probe or mutate Hermes configuration.
3. Add `hermes hmp health check` to the existing CLI. Reuse setup check's
   compatibility, current-identity, record-safety, and TLS-pinned liveness
   checks. Require a fresh complete snapshot and print bounded status codes.
4. Add isolated missing-key, disabled-channel, stale-record, malformed-record,
   and refresh tests. Run the full unit suite, Ruff, plugin-surface, log, and
   zero-baseline privacy checks, plus an exact-build fixture check.

No HMP wire route or send fingerprint changes. The phone already receives a
per-authorized-bot `send_gate` from the runtime; this operator check covers
every served bot without revealing device authorization state.

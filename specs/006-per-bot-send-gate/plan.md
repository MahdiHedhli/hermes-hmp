# Plan: per-bot send availability

The installed HMP reports `open_guarded` from the instance-wide owner flag while `POST /bots/{p}/chat/messages` also requires the target profile's key. A named profile without a key therefore looks sendable and returns `503 write_gate_closed`. The private app's F14 branch retains rejected text, but the misleading gate remains.

Add optional `send_gate` to each authorized roster bot under HMP V-3. Resolve the same profile-scoped endpoint and qualification used by the send route in the roster's worker thread. Do not resolve or advertise key availability for unauthorized bots. Keep the old top-level roster gate closed if any authorized bot is closed. `/ready` stays an instance-level diagnostic. The app uses a bot's `send_gate` when present and falls back to the old roster gate when absent; malformed present values fail closed. No secret is serialized.

Make the `direct_send` host switch mandatory before the full-guarantee branch in the send route. The route has no independent native submission path and always needs its loopback endpoint. Keep idempotency reservation and the guard after this gate. Preserve send-time checks because roster state can become stale.

Security checklist: authorization before profile lookup; default-off owner switch; no secret serialization or logging; no off-flag endpoint lookup; A→B→A scoping; no queued retry; deterministic closed-gate outcome. Verify against the pinned HMP unit and fixture suites, the private client's parser/context tests, Ruff, and zero-baseline privacy and log scans before publication. Independent security review remains a feature-freeze gate.

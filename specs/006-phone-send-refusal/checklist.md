# Checklist: phone send definitive refusal

- [x] Only exact `False` yields `applied:false` on AP-6 delivery refusal.
- [x] `None`, non-bool, exception, session-key and probe-list uncertainty never carry `applied`.
- [x] Exact `True` still `202 submitted`.
- [x] Replay equals the stored body with zero redelivery.
- [x] `409 stale` gates unchanged; fresh gate replies leave earlier unknown attempts unknown.
- [x] No new error code, no `HERMES_API_GAP`, `approval_supported_builds.json` still empty.

Root checked the focused diff and full CI-equivalent suite (1,388 passed, 12 skipped); pinned
Ruff, surface/privacy scans and whitespace checks passed. These checks do not qualify the
changed runtime against a real Hermes gateway or complete device/release acceptance.

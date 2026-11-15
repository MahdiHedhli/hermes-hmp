# Tasks: permission readiness diagnostics

This checklist tracks the AR1 first slice and its separate future gates.
Contract v3 was independently accepted on 2026-10-04; source, Mobile, and
runtime acceptance remain open. A checked source task would not mean installed
runtime, phone, host activation, or release qualification.

## Spec Kit / contract gate

- [ ] **AR1-T001 / AR1-035-T001** Independently review `spec.md`,
  `clarifications.md`, and `contracts/readiness-v1.md`; resolve whether
  unprobed API reachability is acceptable or requires a separate safe-probe
  contract.
- [ ] **AR1-T002 / AR1-035-T002** Amend HMP v1 and Mobile contract only after
  the owner freezes the capability/readiness schemas, compatibility exception,
  auth order, error table, bounds, and legacy fallback.
- [ ] **AR1-T006 / AR1-035-T003** Complete an independent security review of
  the authorized source diff, mobile projection, privacy/log behavior, and
  causal tests before implementation acceptance.

## Read-only host source slice

- [ ] **AR1-T007 / AR1-035-T004** Add the authenticated capability route; keep
  `/ready` unchanged and exempt only that fixed path from compatibility
  middleware. Authenticate before returning compatibility states.
- [ ] **AR1-035-T005** Add the bot-scoped read-only route with bot
  authorization before own-device controls disclosure; reauthenticate and
  recheck family, device, bot access, flag, controls, endpoint config, and
  listener generation around every blocking await. Use a diagnostic-only
  exception-preserving projection; do not infer missing/disabled from lossy
  `False`/`None` helpers.
- [ ] **AR1-035-T006** Project the strict allowlisted DTO with fixed enums,
  safe-integer timestamp bounds, exact sorted reasons and per-feature action
  precedence; preserve errors as fixed unavailable and never return tested labels, dependency names, profile
  labels, settings, endpoint/key data, jobs, model data, or raw errors.
- [ ] **AR1-035-T007** Add non-queueing four-slot worker bound, fixed deadline,
  response cap, per-device rate bucket, timeout/cancellation ownership, fixed
  refusal behavior, and no retry or partial response.
- [ ] **AR1-T008 / AR1-035-T008** Add causal fake tests from the security
  checklist; run the focused suite, Ruff, closed-surface checks, privacy and
  log scans. Keep test results distinct from host/device acceptance.

## Mobile user experience

- [ ] **AR1-035-T009** Negotiate capability for each authenticated instance;
  on old or unknown HMP, display the conservative fallback and never infer
  missing controls. A valid protocol response permits the per-bot diagnostic
  even if only one feature is compatible; the independent capability values
  do not gate ordinary user-invoked operations.
- [ ] **AR1-035-T010** Show capability, shared device controls, per-feature
  host setting, profile endpoint configuration, and unprobed reachability as
  separate status lines. Add no green-ready claim.
- [ ] **AR1-035-T011** Provide local Request access guidance and a fixed
  host-remediation plan. Neither button sends a request or writes settings.
- [ ] **AR1-035-T012** Keep no durable readiness cache; clear on sign-out,
  reported revocation, instance switch, listener generation change, and app
  resume. Since TokenManager has no successful-rotation observer, record no
  immediate invalidation claim; force fresh same-scope negotiation/read before
  local guidance or a feature action without gating the normal operation.
- [ ] **AR1-035-T013** Test legacy fallback, unauthorized generic refusal,
  strict DTO decoding, 404/405 negotiation fallback versus per-bot generic
  not-found, no action/send/write side effects, the existing single P5
  unauthenticated-GET refresh, and stale snapshots.

## Explicitly separate future gates

- [ ] **AR1-T003** Specify and review an actual device request, administrator
  notification, allow/deny/cancel, expiry, and exact-grant contract.
- [ ] **AR1-T004** Specify and test concurrent administrator changes, revocation,
  stale/duplicate/expired requests, and scope refresh.
- [ ] **AR1-T005** Specify authoritative grant readback, conflict/idempotency,
  and lost acknowledgement with no automatic replay.
- [ ] **AR1-035-T014** Independently source-review and causally test existing
  jobs/model operation authorization after awaits. The diagnostic source task
  does not close this current gap.
- [ ] **AR1-T009 / AR1-035-T015** Separately qualify exact installed host and
  physical device behavior, supported Hermes versions, and release artifacts.
  No source result marks this complete.

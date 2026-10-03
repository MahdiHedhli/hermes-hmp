# Requirements checklist: spec 014

Reviewer-owned. The author ticks nothing; the amendment ticked nothing.

## Policy
- [ ] No Hermes floor, manifest, fingerprint, commit check or process latch gates push; later and unknown builds attempt the actual APIs (PN-AV-1).
- [ ] No new eligibility member. Availability follows the approval members, the direct-send flag and host push settings.
- [ ] A relay failure is never a Hermes compatibility finding or issue draft (PN-AV-3).
- [ ] Host settings default closed. A malformed or non-HTTPS relay setting means push is off (PN-AV-2).
- [ ] Existing send, jobs, model, AP-3 and AP-4 behavior is unchanged (PN-NC).

## Wire
- [ ] Four routes only: `GET`, `PUT`, `DELETE /push/registration` and `POST /push/hints/resolve`. No new error code and no new error extra (no `generation` extra on `409 stale`); the four new `why` values are in the closed set and allowed only on `503 write_gate_closed`; additive minor revision.
- [ ] The resolver body is `{v, hint}` and fits the accepted 030 S1 port without reopening it (PN-RES-1).
- [ ] Schemas, gate order, status codes and bounds match spec PN-REG, PN-RES and PN-BND exactly, including `expires_at` = `seal_expires_at`, one `G` increment per transaction and the D28 cap.
- [ ] The `DELETE` outcome mapping and the pending delete intent are mirrored in app spec 030 S2 tasks (spec §11, PN-APP-3).
- [ ] `R` and `K` are 43-character canonical b64u, inside app 030's 22..64 shape.
- [ ] The resolver's `not_pending` uses only the frozen authoritative causes (D4), and never for a row that is hidden now.
- [ ] A resolver `404` maps to `other`; feature presence comes from `GET` (spec §11).

## Integration inputs
- [ ] Spec 034 source `150bd0f` (PR #73) is recorded as independently accepted with native fixtures and deployment pending; I-1, I-2 and I-6 exist in the accepted approval lane only through their own separately reviewed amendments; I-3..I-5 are confirmed or amended in that review (T003).
- [ ] I-6 means current visibility with local expiry, and AP-3 calls the same seam with an equivalence test (§10).
- [ ] The spec §11 mapping, PN-APP-1 and PN-APP-2 are mirrored in app spec 030 S2 tasks (registrar, resolver, native input, persistence, permission state).

## Coverage
- [ ] Coverage is stated as 034 rows only; cross-channel research is an open `EVIDENCE_GAP` until a cited exact-commit trace (T005).

## End state
- [ ] Every required end-state item has physical-device evidence (plan §8.4) on owner-authorized builds.
- [ ] Measured-only rows (force-quit, recents swipe, force stop, before first unlock, watch mirroring) are reported as observed, with no advance claim.
- [ ] Nonreuse is shown on device across re-pair, revoke, P4 re-issue, `rotate-key`, reinstall and token change.
- [ ] Android Doze, standby and battery restriction rows are measured and reported as observed.
- [ ] iOS Focus and Time Sensitive off rows are measured and reported as observed.

## Owner and infrastructure
- [ ] O1–O6 chosen explicitly by the owner before any provisioning; root design choices are not treated as owner authorization.
- [ ] R1 open enrollment is activated only after the owner accepts the recorded residuals (A1, A6, A13, the restated A14 and A17).
- [ ] Privacy declarations updated before any external build enables push.
- [ ] Website, store listings and beta tracks unchanged until a separate decision.
- [ ] A standalone watch remains unsupported; any future watch design has its own pairing and registration.

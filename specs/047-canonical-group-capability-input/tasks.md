# Tasks

## Current task GC-input (not full GR1)

- [x] Record issue152 and native owning-source/candidate boundary.
- [x] Specify/clarify/plan/checklist/analyze the pure internal input boundary.
- [x] Independent contract/security review: accepted with exact-String key
      validation before lookup; contract updated before code.
- [x] Implement bounded frozen native observation parser with no runtime caller.
- [x] Test current/future/malformed/oversized/hostile inputs, metadata dropping,
      immutability and advertised-but-not-authorized semantics.
- [x] Show causal failures when exact boolean typing or metadata vocabulary
      restriction is removed; restore exact code and rerun positive suite.
- [x] Focused independent code/security review and deterministic checks.
- [x] Publish exact source/docs/evidence and update mobile feature list/Nous gist
      (HMP PR153, mobile docs f1699295, selected status readback verified).

## Complete feature remains open

- [ ] GR1-AUTH02 native client/ticket lifecycle + device/room/bot authority,
      grant boundary, revocation/generation/isolation/publication contracts.
- [ ] GR1-CONTRACT03 complete mobile creation/membership/discovery/history/send/
      member control/approval/reconnect UX and wire Spec Kit convergence.
- [ ] GR1-IMPLEMENT04 bridge, authenticated HMP routes and shared mobile UI using
      native execution/IDs/receipts; no shadow runtime or automatic uncertain replay.
- [ ] GR1-VERIFY05 native fault/causal tests, Android/iOS native storage, physical
      operation, privacy/provider/security and release qualification.

## Separate existing release prerequisite

- [ ] CI-LINT-PARENT: resolve the1,241 reproduced findings in79 unchanged parent
      paths through an independently reviewed repair; preserve semantics/security
      and do not suppress the gate. Hosted unit tests did not run on7f8df1fe.

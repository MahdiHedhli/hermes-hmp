# Consistency analysis (implementation worker's, not self-certification)

## Coverage

| Requirement | Plan | Tasks | Checklist |
|---|---|---|---|
| R1-R5 availability | eligibility rows, resolution table | T2-T4 | N13, N14, N23-N25, N30, N33 |
| R6-R8 authority and fresh reads | gates and wiring | T5 | N1-N12, N31, N32 |
| R9-R10 fences | generation/binding | T8 | N20-N22 |
| R11 transport | direct_send row | T6 | N26, N27 |
| R12-R13 bounds and logs | unchanged reviewed code | T10 | N16, N17, N28, N29 |
| R14-R16 failure classification and reporting | direct_send, issue_draft rows | T6, T7, T9 | N18, N19 |

## Conflicts to resolve on freeze

- Spec 013 constraint (closed feature set without approvals) is amended by R1.
- HMP v1 §7b "Independent approval qualification" and the flag paragraph naming
  `direct_send_supported_builds.json` contradict R5 and must be replaced (T1).
- §7b AP-1 makes the stream route mandatory for every guarded send; D2b limits it to
  approval-owner sends. The no-fallback-after-failure rule is kept.
- `specs/003-approvals/DESIGN.md` and `REVIEW_STATUS.md` describe the superseded gate as current;
  mark them historical.
- The reviewed fixture receipt covers `8afaab37` with runtime `f584b91`, not the converted runtime.

## Open evidence gaps

- No local release tag contains Hermes commit `583d5b407b` (session-stream notifier); the latest
  local tag is `v2026.9.24`. No released minimum for Bot Chat cards is claimed.
- `v2026.9.24` has not run HMP's stream or approval fixtures; T14 adds that sample.
- Physical-device approval behavior is unverified.

## Root source review — 2026-10-02

Independent Opus review accepted the converted source and merge/exclusion boundary. Root then
accepted L1's setup/runbook wording correction and L2's three focused guard regressions after
reading their exact diff, running 222 tests and defeating each new guard independently.
The existing optional missing-helper diagnostic-log nit remains recorded; no helper is granted
or made available by this review. Native T14 and packaging T15 are separate, unfinished gates.
The earlier fixture receipt is not evidence for this converted candidate. Prepared foreign
dependencies and an out-of-range floor interpreter are setup findings, not compatibility failures.

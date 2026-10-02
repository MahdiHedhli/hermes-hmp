# Tasks: approvals under the minimum-version policy

Root froze D1-D8 on 2026-10-01. T1-T12 are authorized for the implementation worker; T13-T15 are
root-operated gates. Root records T13, the two prepared T14 samples and the exact T15 source export below. Each item is one reviewable change.

- [x] T1 Amend HMP v1 §7b (availability replaces qualification; AP-1 transport; AP-5 status table),
      GU-2d, the error table, spec 013 (closed-set constraint) and `specs/003-approvals` status.
- [x] T2 Merge `1bcb586` per the plan's resolution table; approvals closed; both suites pass.
- [x] T3 Exclusion commit: routes lane (D5), owner package tool, exact manifests' runtime readers,
      latch and receipt-binding tests.
- [x] T4 Eligibility: two members, phone helper table, field spec, floors, diagnostic marker.
- [x] T5 Gates and wiring: adapter, request context (fail-closed defaults), server route order.
- [x] T6 Transport selection (D2b) and the native answer status classification (R14).
- [x] T7 Use-time capability failures (R15) and fixed log outcomes.
- [x] T8 Generation fence (R9) and binding fence (R10, D6).
- [x] T9 CLI and issue draft: members, diagnostic line, operator-reported codes, `setup check`
      notice for allowlisted devices without a controls decision (D8).
- [x] T10 Unit and negative tests N1-N34 from the security checklist.
- [x] T11 Fixture cases: capability mutants, listener reconnect, process restart, non-owner
      synchronous send, notifier-absent release.
- [x] T12 Ruff, unit suite, plugin surface, log and zero-baseline privacy scans.
- [x] T13 Independent focused security review of the merge (`--remerge-diff`) and conversion.
- [x] T14 Sampled candidate evidence on `8afaab37` and `v2026.9.24`. An additional `ca705dbf` candidate run remains unperformed.
- [x] T15 Owner-local dogfood package from the reviewed candidate commit (separate authorization).

Worker status at original handoff: T1-T12 meant "source written", not "verified".
Root accepted the independent Opus source review and the bounded L1/L2 wording/test correction
on 2026-10-02. Root verified 222 focused tests and three causal failures for the added guards.
T14's corrected isolated runs passed 13 selected cases on each prepared sample, with zero skips
or failures and no protected-source changes. The release-floor notifier-dependent cases are
negative capability checks, not proof of operational Bot Chat cards. See the
[native sample evidence](../../docs/research/approval-minimum-native-samples-2026-10-02.md).
Mismatched dependencies or a Python version outside a sample's declared range are not admitted
as that sample's runtime evidence.
The T15 private source export has zero changed files relative to reviewed `150bd0f`, with
239 tracked files (32 runtime files), private custody modes and an independent Git archive
comparison. Plugin-surface and source privacy checks passed. This is an unsigned exact source
copy; it adds no build allowlist entries. Installation, fresh running-process verification and
physical card/answer acceptance remain open. See the
[packaging record](../../docs/research/approval-minimum-owner-package-2026-10-02.md).
Reviewer-owned checklists are not
blanket-certified. See the [source review record](../../docs/research/approval-minimum-policy-source-review-2026-10-02.md).

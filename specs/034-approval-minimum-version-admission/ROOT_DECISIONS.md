# Root decisions (frozen 2026-10-01; see the Root freeze section below)

Each item is a real choice with a recommendation. Nothing here is accepted until root freezes it.

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Integration mechanics | (a) merge `1bcb586` into a branch from `4d6863e`, then separate exclusion and conversion commits; (b) port runtime files onto `4d6863e` without ancestry | (a). Review the merge with `git show --remerge-diff`. Never install an intermediate commit. |
| D2 | Bot Chat transport | (a) stream for every guarded send (reviewed package AP-1); (b) stream only when the sending device is an effective approval owner | (b). On sampled builds a notifier makes an unanswered dangerous command wait for `approvals.timeout`, while the synchronous route returns Hermes's non-blocking pending result; (a) changes that for every non-owner send. |
| D3 | Eligibility granularity | one `approvals` member; or `approvals` (Bot Chat) plus `phone_chat` | Two members. Bot Chat answers use the native HTTP route, not the in-process helpers, so a missing Phone helper must not close Bot Chat approvals. |
| D4 | Floor | `0.21.5`/`2026.9.24`; `0.21.4`/`2026.9.21` | `0.21.5`, equal to send, which both members require. All called helpers exist in `v2026.9.24` source. No floor is claimed for the Bot Chat notifier. |
| D5 | New-bot routing (`routes.py`, PyYAML plugin dependency) | carry with approvals; keep in its own lane | Own lane. It is absent from `4d6863e`, adds a host config writer and a declared dependency that triggers install consent. |
| D6 | Binding fence | object-identity check (R10); rely on restart plus native `409` | Include the identity check; it is small and has no file I/O. Without it a rebinding degrades to stale answers, not mis-resolution. |
| D7 | Failure reporting now | operator-reported drafts plus fixed log outcomes; runtime ledger now | Operator-reported now; ledger stays spec 013 F1. Additive phone `why` copy is an app slice. |
| D8 | `owner_device_ids` also grants legacy controls when no host decision exists | runbook plus CLI notice; separate approval key | Runbook: record an explicit controls decision before listing an approval owner. Add a read-only notice. No authority change. |


## Root freeze — 2026-10-01

Root fully read the terminal Opus architecture report and all seven draft spec artifacts.
READY_WITH_DECISIONS is adopted with D1(a), D2(b), D3(two members), D4(0.21.5 /
2026.9.24), D5(own lane), D6(identity fence), D7(operator-reviewed reporting now,
ledger stays separate) and D8(runbook plus read-only setup notice). No authority is
added by this freeze. SD3 and SD5 remain pending human permission and untouched.

Authorize a Sonnet implementation of T1–T12 on an isolated branch from 4d6863e.
Record the merge ancestry of 1bcb586 and preserve all source/diff evidence. Intermediate
merge/exclusion commits may remain local, but never publish or install them. Review
--remerge-diff and every named H1–H6 resolution. No source certification follows.
Amend contracts/specs before conversion. If a phased interim suite is incompatible with
the intentionally removed legacy gate, retain its failure as interim evidence and repair
only the obsolete assertion; do not fabricate a passing intermediate or add a stub.
Final converted source must pass the actual affected tests and independent review.

Additional binding clarifications:
- R14 stale requires a bounded parsed native JSON error code: 409 approval_not_active or
  approval_not_pending; 404 run_not_found. Unknown 409, non-JSON/malformed 404, all other
  errors and malformed 200 (including missing/noninteger/nonpositive resolved) are
  unavailable with the observation left open. Only a non-bool integer resolved > 0
  proves application. Do not echo or log response text. No transport retry or fallback.
- R10 changed-helper closure invalidates the local Phone-chat generation; it does not
  establish that Hermes's pending request expired. Do not report authoritative native
  expiry/notPending from rebinding alone. Bind the actual called helpers, compare
  identity off any disk/manifest path, close until reopen and keep Bot Chat eligibility
  independent. A stale source-bound stream cannot reinsert rows into the new generation.
- D8 changes no controls decision or owner allowlist automatically. Existing host denial
  still prevents approval ownership. No separation-of-privilege runtime redesign is
  smuggled into the compatibility conversion; record the coupling clearly as a residual.
- No new-bot route/config writer, PyYAML dependency, owner_package manifest editor or
  per-build approval admission reader survives in this lane. Preserve 4d6863e send/read/
  session/jobs/model/wizard behavior, dependency tables and sampled evidence bytes.
- Sampled fixture evidence is not a runtime allowlist or a required future-build test.
  Test locally present pinned notifier and no-notifier builds after review; no installed
  Hermes home is a fixture. Missing callbacks cannot generate fabricated cards.

T13 independent review, T14 sampled candidate fixture execution, and T15 owner-local
packaging remain root-operated gates. The implementation worker may update isolated
fixture source but may not start native fixtures, install dependencies, deploy, change
live grants/config, build a phone, publish source, merge main or submit upstream.

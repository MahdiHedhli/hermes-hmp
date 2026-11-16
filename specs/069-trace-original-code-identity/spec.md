# Match synthetic trace observations to their original code identity

## Bounded test-helper repair

The shared synthetic trace helper used dictionary lookup on frame.f_code for every
event, including unrelated large native functions. Code equality can also route
an unregistered structurally equal clone. The helper now scans registered route
keys by original code identity, avoiding repeated code hashing while preserving
the existing dictionary/direct-registration interface and exact source-line timing.

This is not a fully identity-keyed registry: dictionary registration still uses
code equality/hash, so simultaneous equal-code registrations are not independent.
No production code, protected method, guard, deadline, count/assertion, host or
phone behavior changes. No test is removed or marked skipped.

## Evidence and acceptance

A child regression exercises original callbacks, equal-code unregistered clone
rejection, later direct registration and unchanged original code. Replacing only
the helper with its exact prior bytes causes the intended clone-observation
assertion to fail. Inert compile-only timing of5000 dictionary misses on one large
code object measured roughly0.083seconds versus0.00043 for integer identity; this
is a helper-cost sample, not a native runtime benchmark or timeout explanation.

The separate operator-native readlink observer prototype still times out at its
unchanged60second deadline, even after this helper repair. It is not imported by
this branch or qualified by this work. Its native raw-return observation is a
different timing boundary from the old completed-carrier wrapper. Do not publish
or report that broader prototype as accepted based on this helper.

- [x] Reproduce equal-code misobservation and preserve the exact old helper control.
- [x] Add actual child regression and retain direct-registration interface.
- [ ] Complete representative unchanged legacy readlink/fault trace coverage.
- [ ] Independent terminal coverage review and bounded test-only publication.

The full native43940129806 and broad original regression processes remain on their
unchanged source and handles. No full-suite/native/private/physical/release pass.

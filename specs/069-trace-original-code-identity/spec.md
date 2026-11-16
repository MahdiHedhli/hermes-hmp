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
- [x] Complete all26 unchanged legacy readlink/fault cases plus the new child regression:27 pass, zero failures/errors/skips,137.333seconds on exact8dab0ffb.
- [x] Independent terminal coverage review accepted within the helper-only scope.
- [x] Publish bounded test-only source in Draft PR183.

The full native43940129806 and broad original regression processes remain on their
unchanged source and handles. No full-suite/native/private/physical/release pass.

Actual additional child samples pass on installed CPython3.11.15,3.13.13 and3.14.4;
no3.12 or Linux claim. Complete production subtree Git IDs match published f1b0e6b6.
Scoped Ruff0.16.9 and source privacy/plugin-surface checks pass. No changes to the
active native experiment payload or physical candidate are implied.

Published at https://github.com/MahdiHedhli/hermes-hmp/pull/183. Source8dab0ffb and its independent review remain the executable binding; later documentation does not widen that result.

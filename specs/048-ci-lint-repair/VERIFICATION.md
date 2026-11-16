# Formatting stage verification — full gate incomplete

Base: `070f2199fb7bd066b6c8d230ce27b916be7ae516`.
Pinned Ruff: 0.16.9. Original diagnostics: 1,241; current diagnostics: 530.
No lint configuration, rule, exclusion, deadline or runtime admission change.

The initial 74 formatted Python pairs had equal ASTs excluding positions. Final
source has one explicit test-only AST difference in `test_presentation_link_layout`:
the separately reviewed AST-based trace locator. The other 73 retain equal ASTs.
Original literal scripts and production operation trees remain represented, but
this does not establish identical execution, tracing, allocation or startup costs.

## Existing six-file comparison

Unchanged base: 194 collected, 191 passed, three failed, two passing subtests;
717.16 seconds. Final candidate: 194 collected, 191 passed, the same three failed,
two passing subtests; 713.45 seconds. XML contains 196 testcase elements, including
two subtest elements; keyed comparison has 194 unique case keys and zero outcome
deltas. All 665 frozen server/tools input hashes remained unchanged during the run.
Both processes exited 1. These are not green suites or whole-runtime qualification.

Remaining failures:

- `test_actual_link_scope_last_origin_return_seals_publication[normal]`: original
  60-second child timeout; cause unresolved.
- `test_actual_link_scope_unobserved_normal`: original 60-second child timeout;
  cause unresolved.
- `test_parent_refuses_self_consistent_foreign_sys_root`: expected tuple-return
  observation absent. A separately instrumented disposable single-case pytest run
  records no capture entry before parent refusal. This diagnoses that invocation,
  not every possible collection context; it does not justify deleting the assertion.

Initial formatting introduced four additional locator-premise failures; the final
observer repair resolves them. The repaired file passes 19 cases. Its four affected
cases pass with unchanged base and formatted source. A disposable source mutation
omitting only the original value-identity guard produces exactly one intended failure,
no errors/skips. Production guards and all original assertions remain unchanged.

## Compiled-source limits

Recursive compile-only diagnostics cover CPython 3.11.15 and 3.14.6. Source locations
change for every observed code object. Normalized operation projections differ in
nine paths on 3.11 and 37 paths on 3.14; generated `__firstlineno__` and compiler
fusion differences are observed. Classification is incomplete. No compiled parity,
trace equivalence, full heap funding or prior exact-source proof reuse is claimed.

## Remaining work

Independent final review accepted this bounded stage: no production semantic or
security-guard weakening found; all 665 frozen hashes and same-failure comparison
verified. Publication remains pending.
Resolve the remaining 530 lint findings and three baseline failures, then run all
configured CI checks. Meaningful ownership references, intentional adversarial tests
and copy semantics require intent review; do not apply unsafe automatic fixes.
Device qualification, private deployed composition and release checks remain separate.

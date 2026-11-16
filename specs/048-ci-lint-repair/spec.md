# CI-LINT-PARENT — preserve behavior while restoring the full CI gate

Tracking: [issue154](https://github.com/MahdiHedhli/hermes-hmp/issues/154).
The complete target is the existing configured lint, unit/tool, plugin-surface,
privacy and log gates running successfully on reviewed exact source. Repairing
only layout is a first task, not a redefinition or completion of that target.

## Requirements

- CL1: Resolve the1,241 reproduced inherited findings without dropping checks,
  adding a broad baseline/ignore, changing admission budgets or deleting features.
- CL2: Keep feature authority, denial behavior, native execution/custody gates,
  claims and uncertainty semantics intact. Do not activate an unqualified producer,
  deployment, permission, provider, mode, model or job operation.
- CL3: First stage is the74 exact Ruff0.16.9 formatted copies whose ASTs equal
  their originals when locations are excluded. Every expression/statement/import
  order, binding, literal/embedded script and assertion stays represented in that
  tree. No `ruff --fix`, import removal/sorting or production semantic rule rewrite here.
  One separately reviewed test-only AST delta repairs a line-fragment observer
  invalidated by formatting; it preserves the four mutations and original
  security assertions and is qualified against both layouts and a causal mutant.
- CL4: Source positions, tracing and compiled metadata may change despite AST
  equality. Existing location-sensitive/custody tests and a recursive compiled
  operation comparison must inform acceptance. Old exact-source/startup/resource
  qualification cannot be reused as evidence for the changed files.
- CL5: Preserve the unchanged lint configuration, rules and exclusions. Independently
  review each later semantic repair and meaningful counterexample; no blind
  deletion of unused-looking owned references or substitution of weaker tests.
- CL6: Keep the full gate incomplete until actual configured results prove it.
  Local source passes, AST equivalence and independent review do not establish
  physical/native/heap/startup or release acceptance.

## Acceptance

The layout task requires all74 input/output hashes and ASTs, original literal
content, compiled operation projections, unchanged configuration, fresh appropriate
existing-test results, explicit source-tracing limits and independent review.
The complete repair additionally requires every remaining diagnostic addressed
without a broad waiver and fresh full configured CI, with platform/fixture skips
and all native/device/release limits reported honestly.

CPython3.14 additionally emits executable class `__firstlineno__` metadata; its
value changes with layout. AST equality is not equality of that generated value
or all compiled constants. The3.14 preview records these differences rather
than treating the source as byte-identical.

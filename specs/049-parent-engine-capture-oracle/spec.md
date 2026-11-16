# CI-LINT-PARENT: exercise the actual parent engine-root refusal

Parent issue: #154. Base: f4dac58480e27a0b21be31096cc043719857e12b.

## Observed problem and scope

The existing foreign-system test calls `link_factory_origin.capture()` directly.
Its import of cache/entry dependencies eventually imports `gateway_entry`, whose
module initialization calls capture again. The once-only guard refuses this
reentry before the test injects its fake system. A disposable trace identified
both caller frames and the earlier refusal. This is a test setup failure, not
permission to remove the production once-only guard or weaken root identity.

## Contract and plan

Repair only the existing test. Start a fresh isolated Python child, declare the
synthetic hmp_plugin namespace explicitly to avoid plugin bootstrap, and import
normal gateway_entry. Never reset capture state. At the exact engine capture code
object, inject a fake system with a copied module registry, observe the original
returned tuple containing both fake identities, and restore link.sys/tracing.
Require one capture entry, exact parent system-identity refusal and started state.
Bind the expected parent refusal line to its actual AST identity guard, not a
hardcoded line or any later exception. No service, operator file, provider or key
is loaded. The child has a 15-second deadline and runs in a temporary directory
with a bounded locale-only environment. No production source changes.

The former top-level ModuleType import served only this moved fixture. Remove it;
the child imports its own ModuleType explicitly. Preserve the remaining parent
module import order; its inherited lint finding remains visible.

## Acceptance and causal control

- Existing engine-capture tests and isolated approval import-order tests pass.
- The exact new test passes unchanged on the current source.
- In a disposable full package copy, disabling only the three immediate parent
  engine-root identity comparisons must fail this test. Preserve comparator ASTs
  so the test reaches runtime rather than failing its locator premise. A later
  retained engine refusal cannot count as the expected parent boundary.
- Independent exact-source/evidence review; plugin/private/whitespace checks.
- Keep the two baseline child timeouts, 530 lint findings and all native metadata,
  custody, allocation, device and release gates separate and open.

## Analysis

Normal entry import resolves the circular setup without changing runtime guards.
Fresh-process isolation prevents ordering-dependent module state or resets from
standing in for an actual initial capture. AST binding avoids formatter-specific
line fragments. The synthetic namespace is deliberately narrower than a complete
plugin startup; these observations cannot certify full plugin or host execution.

## Tasks

- [x] Reproduce original failure and identify actual earlier caller/refusal.
- [x] Independently review normal-entry child contract before implementation.
- [x] Implement test-only change preserving original refusal and root assertions.
- [x] Verify final source and causal omission; independently review exact evidence.
- [ ] Publish bounded source/docs checkpoint; retain broader CI/feature tasks.

## Verified result

Final focused run:38 passed, zero failures/errors/skips,3.85 seconds. The exact
causal control disables all three immediate parent identity comparisons; its one
case fails at the exact-boundary assertion because a later ArtifactObservationError
is observed instead. Independent source/evidence review accepted this test repair.
Plugin surface, private-data scan and whitespace checks pass. The changed file
retains its one inherited import-order lint finding, without adding suppressions.
The full six-file suite has not been rerun on this test revision; do not compose
this focused result into a fresh full-suite pass or claim either timeout resolved.

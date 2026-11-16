# Keep the no-filesystem media probe reportable

## Specify and plan

The original no-filesystem candidate test on 88a75bdf exits 1 without JUnit even
when run alone: global filesystem/path/open traps remain installed until fixture
teardown, while pytest's report path itself needs those APIs. This masks the
actual candidate-call result and prevents completion of broader qualification.

Keep the exact trap list and original three candidate assertions. Scope the
traps to those calls with the fixture's local context so all globals restore on
normal return and exceptions before pytest reports the result. Do not suppress
assertions, disable APIs or relax the production no-I/O predicate. Add causal
filesystem-call injections that must still fail the same guard and demonstrate
restoration/reportability after failure.

This is a test-harness change only: no production field/import/parser/authority,
image read, native SDK, provider, network, permission or host/device change.
The listed API traps are not a universal syscall sandbox or proof about unrelated
threads, native execution, physical rendering or release.

## Tasks and verification

- [x] Reproduce original standalone failure and missing JUnit in a fresh test home.
- [x] Scope the unchanged guard and preserve all assertions.
- [x] Prove injected filesystem calls fail and restore globals before reporting.
- [x] Run the complete candidate test file and appropriate related parser/scanner tests.
- [ ] Independent review and focused source publication; preserve broad-suite gates.

## Observed results and remaining qualification

Executable source: `8efd6c1f2739adda576342a5b2de2024b3548376`.
The complete candidate/result/active-scan/active-batch/file-safety selection
produced normal JUnit: 418 cases, 417 passes, one failure, no errors or skips,
on Darwin with Python 3.14.4. The remaining frozen-registry SHA expectation
in active-batch is unchanged and remains an unresolved pre-existing failure;
this is not a clean related-suite pass.

The original guard retains all 16 OS/pathlib traps, the builtins.open trap,
and all three candidate assertions (normalized function AST checked).
Three negative controls exercise stat, abspath and open; they assert the
failure and restoration of the actual patched function identities. In a separate
synthetic source checkout, deliberately inserting os.getcwd into the production
candidate function makes the original guard fail with ordinary JUnit output.
Restoring exact source gives four passes (original plus three controls).
This demonstrates the selected guard rather than universal filesystem isolation.

Focused Ruff 0.16.9 and source privacy/plugin-surface checks pass. No captured
runtime-log corpus was supplied to the log scanner. Independent source/causal
review accepted this test-only scope; no production source changed.

A broader unit/tool selection is running against a separate immutable checkout
of the exact executable source above. Its retained process session and private
receipts remain authoritative; partial progress is not a terminal result or a
whole-suite pass. Linux CI, actual native integration, device startup/rendering,
private integration, and release qualification are not established by this test
repair. Existing production and security gates remain in force.

# Keep the no-filesystem media probe reportable

## Specify and plan

The original no-filesystem candidate test on88a75bdf exits1 without JUnit even
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
- [ ] Scope the unchanged guard and preserve all assertions.
- [ ] Prove injected filesystem calls fail and restore globals before reporting.
- [ ] Run the complete candidate test file and appropriate related parser/scanner tests.
- [ ] Independent review and focused source publication; preserve broad-suite gates.

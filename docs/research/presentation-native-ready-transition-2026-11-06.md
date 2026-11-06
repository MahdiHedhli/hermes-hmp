# Original-work native READY transition — November 6, 2026

This source-only transition consumes the completed original signed READY read,
revalidates it on the original work allocation, performs fresh native PRE_GO,
and calls the existing native READY transition once. Post-transition checks use
fixed READY material scope, actual STARTING/READY native ledger state, current
keys, original socket/clock/deadline and successful native return. They do not
borrow the old BEGIN-only guard or mint GO/worker/resource permission.

Partial owners are retained before callbacks. Refusal, revocation, drift or
uncertainty is terminal, including after actual native mutation: no rollback or
retry is performed. Generic credential gates and production dispatch remain
closed. No host, device, settings, providers or installed mobile build changed.

Independent read-only source review caught a foreign equality callback hazard
in phase membership. Identity-only checks now reject it without callbacks; the
new tripwire covers that boundary. Reviewer found no remaining defect in this
bounded transition review; this is not whole-lifecycle or release qualification.

Focused final checks: 60 tests and configured lint passed. A prior broader run
passed 1,437 tests with one skip before the identity tripwire was added. Earlier
selected regression had 836 passes and one cancellation fixture failure: an
unfinished notification Future was read after FIRST_COMPLETED. Its underlying
control-task refusal/timing cause remains unproven. The fixture now surfaces the
completed control task result instead of masking it with InvalidStateError;
later success does not erase the original failure. Final exact-source regression
is recorded below when terminal.

Remaining delivery work: production original-task integration, later signed
phases, resource admission/worker GO relay, startup, native publication and STATUS,
plus physical/release qualification. Character delivery remains unavailable.

Final exact-source affected regression: **1,438 passed, one skipped**, 63.41 seconds.
Configured repository-wide lint and diff whitespace checks passed.

## Original-task exchange composition

`NativePhaseWorkOwner.exchange_ready` composes the reviewed signed BEGIN writer,
signed READY receiver and fresh PRE_GO/native READY transition on the same
original retained work allocation. Exact allocation/task admission precedes native
authorization; a foreign actor does not consume the attempt. The exchange latches
once before IO and retains each partial owner through existing fields; failure
is sticky, with no fallback, rollback or retry. It returns only the native READY
receipt. Production caller/startup selection and GO remain closed.

Three focused cases pass: complete signed exchange, invalid broker signature,
and foreign actor rejected before the valid original task proceeds. The first
wrong-actor fixture expected FrameError but initially encountered native
AuthorityRefusalError and waited indefinitely for its peer start Event. That run
was intentionally interrupted after two passes; it is not qualification. Pure
actor admission now precedes native checks, and a two-second fixture rendezvous
bound exposes such setup failures without changing any protocol deadline.
Independent read-only review accepted the composition and final entry fence.
Selected affected regression: **841 passed**, 37.97 seconds; configured lint passed.
This selected scope is narrower than the prior transition regression.

# Original-service signed READY write — November 6, 2026

This source helper sends the fixed signed READY record and its empty HBR1 frame
from the retained `CredentialReadyProducer`. There is no production caller. It
starts no resources and relays no worker GO. Fixtures independently start actual
disposable resources in new synthetic homes, stage actual input, and separately
qualify this original-service send. Production resource admission, later signed
IO, startup, native publication, STATUS and device/release qualification remain
closed.

`CredentialReadyWriter.retain(producer)` derives its actor, original native input,
resources, child, pipe-write observation, grammar, role keys and socket from the
retained producer. It accepts no caller frame, digest, phase, timeout, Future or
permission flag. A partial owner is retained in both producer and channel before
callbacks. Its original exact native Future allocation is retained before Future
initialization in an immutable tuple within original writer references. Current
aliases cannot replace that allocation. Future methods and scheduler dispatch
are fenced before waits/notifications; substituted metadata is type-checked
before getters/comparison.

`write_ready()` consumes one attempt, captures a fixed write intent, independently
rechecks the signed transcript/input-derived context and complete committed frame,
and writes only the original READY bytes through captured native socket send.
Original resource/input/key/current-material checks surround each syscall and each
await. Final concrete socket identity, nonblocking mode and timeout checks follow
peer/clock callbacks. Actual positive syscall progress is retained immediately
from the held pre-syscall offset, before current-material callbacks. Zero is a
known terminal refusal, never a retry. An invalid/uncertain return, exception or
progress/intent drift preserves unknown debt and forbids another send attempt.

Only an exact native would-block result with EAGAIN/EWOULDBLOCK and unchanged
held cursor permits waiting on an owned write registration. The original absolute
work end is used without renewal. Registration is retained before initialization;
unknown registration/retirement keeps the channel write claim. The concurrent
control reader is preserved. Known settled local IO may later be closed even
when signature/current-material success was withheld; uncertain IO cannot.

READY grammar is observed only after all original bytes were written and current
facts revalidated. Only this exact retained writer intent can match the producer's
post-READY grammar state. The writer publishes its original completion Future
only after grammar/current checks; cleanup finishes synchronously before the
controller can resume. `CredentialGoPhase` joins this exact writer when present,
under the original deadline and original controller scope, then revalidates the
original signed GO completion before minting a native GO-read receipt. This is a
read fact, not worker GO execution or an execution acknowledgement. Existing
modeled-READY fixtures without a producer remain unit scaffolding, not production
admission. Generic credential work/GO transports remain closed.

Local retirement checks are distinct from send authority: `_released` checks
original metadata, no active/inflight/unknown IO and positive owned wait retirement.
It does not require live role keys or the ended creator task merely to read a
historical local completion. This is not aggregate channel closure: an interrupted
unfinished control cursor still conservatively retains its separate read claim,
even after its selector wait retired. Additional closure assertions initially
failed in three such fixtures (wouldblock, wrong-task yield, kernel backpressure).
They now explicitly verify that the completed writer is locally retired while the
independent unknown read prevents socket/clock closure. Successful completed
GO/CANCEL consumption separately proves known channel closure. The interrupted
read-cancellation/native settlement gap remains open; it is not fixed by READY. Sending still requires the original service creator;
joining GO still requires the original reader. No unknown subscription is removed
by this historical check.

Independent read-only source/test review found and accepted repairs for native
Future method fencing, observation type fencing and original Future allocation
binding. Root executes all tests; the reviewer executes none. Causals exercise
actual READY bytes received over the private socket, actual kernel backpressure
(with a known synthetic preload drained only by the fixture), partial native
writes, exact EAGAIN, known zero, uncertain syscall outcome, post-send key
retirement, paired offset/Future substitution, foreign-method/observation
tripwires, deadline refusal, uncertain registration, original READY/GO/CANCEL
consumption and a malicious early GO waiting for the original incomplete write.

During test development, initial GO-chain fixtures waited for a parked controller
to terminate without the normal creator cancellation consumption/abort. The park
correctly expired; fixtures now consume the actual cancel notification and invoke
the existing owned abort under unchanged deadlines. An unknown-registration case
initially expected a generic OSError from a matching suffix; it now expects the
actual readiness FrameError. These were fixture errors, not source passes or
reasons to weaken deadlines. Prior broader cancellation-consumer failure remains
recorded in the write-readiness evidence; no causal fix is claimed here.

Final affected regression: **1,375 passed, one skipped**, 56.86 seconds, including
all 17 new sender cases. Configured repository-wide Ruff passed. Exact source/CI
binding is recorded in the current feature checkpoint and private integration
receipt; new-source CI is pending. Prior write-readiness source f210093 passed
CI742 plugin and Python 3.12/3.13/3.14 Unicode jobs. No live host/device/settings,
permissions, providers, role-key installation or installed app changed. Full
bot-character delivery remains unavailable.


## Subsequent source checkpoint

The later [known cancelled-read slice](presentation-cancelled-control-read-2026-11-06.md)
settles only actual original-task cancellation during a positively retired owned
wait. The preceding observations remain evidence of b066cac; unknown native IO and
generic failures still retain debt. Exact b066cac passed CI744 plugin and Python
3.12/3.13/3.14 Unicode jobs; this does not qualify later source or full delivery.

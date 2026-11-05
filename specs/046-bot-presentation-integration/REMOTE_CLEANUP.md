# Retained remote cleanup owner

## Implemented source contract (not runtime qualification)

This joins the selected-v2 remote BEGIN/READY handoff to retained work/cleanup
ownership. It is part of complete desktop character delivery, not a substitute
feature. Version1 behavior stays unchanged. The coupled source adds only selected-v2
BEGIN/READY/CANCEL dispatch. GO, RESULT, STATUS/ACK, started terminal release
and credential/native DRAIN remain closed.

Allocate and retain one exact owner on RemoteOperationOwner before initializing
it. It captures the original remote/record, channel, qualified clock/domain,
CancellationBudget, operation, deadline, event loop and process/thread. No new
admission ledger or cleanup budget. The supported initial runtime is the native
CPython asyncio SelectorEventLoop, default task factory, exact native Task/Future
objects; unfamiliar/eager/custom factories refuse before any work is opened.
This is an API/runtime gate, not a Hermes version allowlist.

Retain barrier Future allocations, task allocations and their exact coroutines
before initializer attempts. A cleanup task and a work task both wait behind owned futures. Neither can start
an exchange before both allocations are retained, successful initialization and
original reciprocal references are checked. Partial construction retains debt;
never retry construction, reopen the barrier or guess that a task did not start.
Separate immutable NamedTuple allocation seals retain original task/coroutine and
barrier identities independently of mutable partial-initialization records. Slot
substitution cannot manufacture a join or redirect cancellation. The work task
runs only the fixed RemoteOperationOwner BEGIN/READY method, never an arbitrary
callback/coroutine. The public await shields that task, so request
cancellation is first observed and frozen before cancelling the owned work task.

A cause observed before the cleanup task first runs skips the work clock entirely;
only original cleanup sampling is permitted after retirement. A single cleanup
task waits for the first explicit cancellation/failure or the original work
deadline. READY does not dispose it or release its reservation.
The first cause latches cleanup intent and revokes native/output work through
the original custody snapshot before any native clock boundary. It freezes the
same original budget using the original native cleanup-only clock before task
cancellation or transport cleanup. Duplicate causes only shorten the same window; expired/failed clocks never gain a fresh allowance.
Clock/owner/context drift retains UNKNOWN and cannot requalify the operation.

Cleanup cancellation never propagates from a cancelled public await. Work
cancellation is requested at most once; cleanup observes actual completion under
the frozen original budget. A still-running task/native claim remains debt. No
new native observation, work clock, GO, result or publication is allowed after
retirement. No socket close occurs while retained work I/O may still run.

Cleanup may send exactly one CANCEL only after actual work-task join and no live
read/write flags. A channel-owned immutable intent and completion fact bind the
concrete BEGIN write to the original remote/channel/socket/scope/packet/deadline;
a mutable remote completion flag alone is insufficient. Partial or uncertain
BEGIN never receives an appended frame. The dedicated send accepts only the
original retained cleanup owner on its own exact task. It freezes write intent
before encoding and uses the existing cleanup cutoff as its absolute timeout,
checking original clock/budget and data identity before and after native I/O.
Partial write, cancellation or timeout is UNKNOWN and never retried.

After the write (or where no completed BEGIN exists), observe only concrete local
socket close and distinct clock-FD close under the remaining original budget.
Expired or ambiguous cleanup retains debt; local write/close does not mean broker,
child, registry, policy/native DRAIN or credential closure. An observed cleanup-task
completion or its local-close boolean is not release authority or certification
that the last synchronous primitive finished on time.

Runtime shutdown, blocking syscall latency/external watchdog, trusted installed
code/exclusive native ownership and real Linux/device qualification remain
separate. Synthetic tests cannot certify a production hard wall-clock bound.

## Causal acceptance

- Actual local Unix selected-v2 BEGIN/READY with the original input/budget/clock.
- First-cause capture precedes owned task cancellation; repeated caller cancel
  cannot cancel cleanup, renew the deadline, reopen work or duplicate sends.
- Cancellation before work start, during native PRE_GO, during BEGIN, awaiting
  READY and after READY; EOF/deadline and late READY never restore work.
- Joined versus cancellation-swallowing work; no close during live work I/O;
  ambiguous BEGIN never gets a following CANCEL and no state releases credit.
- Default runtime success and refusal before effects for foreign loop/factory,
  partial first/second task initialization, stale owner/domain/budget/context.
- Immutable completed-BEGIN fact versus mutable flag substitution; one CANCEL
  under the same cutoff, partial-write ambiguity and no retry.
- Separate socket/clock closure facts, expiry/refusal and cleanup-task cancellation;
  native claims/headers stay retained. No private host or user content fixtures.

Python references: [3.11 task cancellation and shielding](https://docs.python.org/3.11/library/asyncio-task.html#shielding-from-cancellation)
and [3.14 tasks and eager execution](https://docs.python.org/3.14/library/asyncio-task.html#eager-task-factory).
These explain API semantics, not qualification of this runtime or source.

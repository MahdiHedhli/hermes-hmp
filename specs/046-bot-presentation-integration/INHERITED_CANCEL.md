# Original-window cancellation transport

## Required final transport

Retain existing native/remote and broker resource budgets; wire values never
attest a clock or authorize GO, result publication or release. Both ends bind
exact selected version 2, original operation/channel and qualified clock/domain.
CANCEL is sequence 1 before GO, or sequence 2 after a completed GO1 write;
it carries exactly 16 body bytes (original start/end), never a timer
request. Semantic adoption can only shorten the earlier retained end and is
capped at original work end plus 250 ms. Future starts, overflow, uncertain clock
or malformed framing refuse and retain debt. Version1 remains the default.

Gateway cleanup may send only after its exact owned work task and I/O have
joined, BEGIN completion is known and the same original cleanup window remains.
Record one write intent before transmission, never retry ambiguity. A partial or
uncertain BEGIN gets transport closure, not an appended CANCEL. The dedicated
cleanup-only send path must accept only the exact retained RemoteCleanupOwner;
ordinary work send cannot be reused after retirement. No status/release follows
from local send/EOF facts.

The broker retains a cancellation receiver on its enrolled channel after exact
BEGIN decode/reservation, before receiver task effects or reader launch. Capture
the registry ticket/record/budget, grammar, channel, qualified clock/domain and
original deadline. Default native selector/Task runtime only; retain partial Task
allocation/coroutine and independent immutable origin before initialization.
Failed/ambiguous construction cannot be retried or certify no work.

The continuous receiver reads optional GO1 followed by CANCEL2, or CANCEL1
before GO, for that exact binding. Bound
prefix/header/body before allocation and reject queued/duplicate/wrong-sequence GO, status, downgrade and wrong scope.
Keep partial bytes under one original absolute ceiling. Before the original work
end, native work time bounds each wait at that work end. On the first local work
expiry or already-caused budget, invalidate work/grammar before the cleanup
clock boundary, freeze the same budget and use only original cleanup time. Read
may continue through the remaining original cleanup interval without renewal;
expiry leaves uncertainty. An owned timeout is a clock checkpoint, not a new
window. EOF, partial data and cancelled receiver similarly retire the original
work before cleanup sampling.

A fully validated CANCEL header retires work and freezes its local cause before
waiting for the body. It does not certify semantic adoption or authorize a resource
abort. On complete valid CANCEL, invalidate grammar/work before native cleanup sampling
and adopt the received minimum on the registry's exact existing budget BEFORE
any resource abort, signal or closure. That same object is already retained by
managed resources, so launch/work freshness refuses and later local abort/polls
cannot renew it. Repeated/invalid CANCEL cannot reopen work. Header/framing or
pure grammar alone is not receipt/adoption authority.

Service work must shield the receiver task: caller cancellation first freezes
local cause, then cancels the original task once. Actual receiver join and frozen
budget precede local socket/clock closure; stalled/partial tasks stay reachable.
Version2 STATUS/ACK, RESULT and started terminal release remain closed until
their own lifecycle and proof integration. Native DRAIN/credentials are separate.

## Receiver source and coupled transport

BrokerCancellationOwner now retains one exclusive native task/coroutine before
initialization with a separate immutable allocation seal and successful-init
proof. Its exact registry record, budget, channel and native clock/domain remain
joined. Constructor refusal retires the original grammar/budget even on partial
initialization; it cannot leave launch enabled. Exact metadata types precede
comparisons, including grammar role/mode/snapshots/counters and boolean state.

The fixed cursor retains bounded prefix/header/body bytes across work expiry.
Native nonblocking/timeout facts are checked before read continuations. Known
expiry switches to original cleanup time; generic clock faults poison the budget.
CANCEL1 semantic adoption changes the exact existing budget before any resource
abort. Local and remote causes only shorten; already-expired windows get no time.

The prior receiver-only focused review passed 94 cases on Python 3.13. The
coupled source now joins its exact gateway sender and service retirement. Service
version2 admits only BEGIN/READY/CANCEL. Queue and READY boundaries recheck
retirement; a pending header revokes launch before body adoption. The receiver
is shielded from service cancellation until the same original cause is frozen;
partial initialization or unjoined work retains the original channel. Actual
join precedes resource abort/poll and separate local socket/clock closure under
the original cutoff. Registry/native debt is never released by these facts.

Local Unix tests explicitly mock peer identity and Darwin clock facts. Synthetic
owned-reader causals are not production manager/runtime or device qualification.
General SocketChannel GO/CANCEL and result/status/release remain closed. Dedicated
GO source is joined by the [async contract](ASYNC_GO.md); it adds no release authority.

## Source sequencing, not a reduced final feature

1. Selected grammar and exact retained broker receiver/adoption are implemented
   with local Unix causals. General channel CANCEL remains closed.
2. The coupled source adds the exact gateway cleanup send path and service
   receiver, original-budget abort/poll and partial-task retirement. Independent
   implementation review and runtime-specific evidence remain distinct.
3. Keep production runtime/manager/latency and signed physical image qualification
   distinct; finish native GO/result/terminal proof, routes and full rendering.

Causals: no renewed allowance after local-first or remote-first cause; delayed
already-expired interval; future/overflow/short/long/mixed-version/wrong-operation
refusal; partial header/body across work expiry; actual receiver/task ownership,
partial init and exact native Task substitution; one cancellation attempt and
actual join; resource launch/abort shares the original budget; no unintended GO, result/
release or post-ambiguity appended frame. No live host, messages or deployments.

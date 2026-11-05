# Original selected-v2 pre-result cursor

Selected-v2 SocketChannel.receive retains one original-task BEGIN/READY cursor
before initialization. Its immutable scope binds the original channel/socket,
expected binding, original end, optional remote owner, Task/loop/context and
original bounded bytearray. Cumulative received/target offsets and decoded header
metadata remain after the cursor copy is wiped. Only one attempt is allowed per
v2 channel; this creates no replacement reader or replay path. Selected-v1
receive/exact behavior remains unchanged.

Concrete nonblocking receive comes first. Exact EAGAIN/EWOULDBLOCK alone permits
owned readiness notification, under the same original end. Before registration
or receive, current channel/peer/native-clock checks and the remote BEGIN_INTENT
checks remain mandatory. Validate the outer header before body reads: broker
BEGIN or gateway READY, selected version/scope/sequence and declared input bound;
READY is bodyless. Exact wanted counts cannot consume the next GO/CANCEL/RESULT.

A second channel clock sample follows the ordinary remote check. Immediately
after it, a callback-free local fence revalidates original remote custody,
owner/job/lease/fence/epoch/phase, policy transfer/closed-state, cleanup actor and
unretired original budget. It does not repeat authorization, sample another clock
or create a new allowance. Causals revoke ownership, budget, fence, policy,
epoch or emit state at that last sample and forbid receive/readiness creation.

Capture pending bytes and received offsets synchronously after recv. Arithmetic
uses held exact primitives and extension uses the original bytearray. Unknown
registration, recv or commit retains the original read claim after Task failure.
Known EOF is a settled zero-byte receive. Validate exact readiness initialization,
attempt/retirement and unknown flags immediately after its await, before later
clock/current checks; foreign truthiness or a combined work refusal cannot erase
lost registration proof. This same metadata ordering applies to normal RESULT
and broker control callers.

Frame construction precedes wiping the cursor copy. The returned immutable
BrokerFrame/body remains intact private data, not wiped data or authority. On
refusal, transient part/prefix/header/body/frame aliases are dropped from retained
exception frames, and only the scope-captured original bytearray is wiped;
replaced buffers or channel metadata are never followed for cleanup. Task/clock/
socket closure, producer qualification, emission and release are separate facts.

This is normal pre-result framing, not cleanup-mode resumption. Extending the
same original reader through first cause, active timeout shortening, CANCEL/ACK,
qualified terminal acceptance and native PRE_EMIT/DRAIN/credential retirement
remains the joined lifecycle. No image route, host deployment or permission opens.

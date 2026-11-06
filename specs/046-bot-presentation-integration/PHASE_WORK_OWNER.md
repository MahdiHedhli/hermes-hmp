# Original work-task phase producer contract

Status: independently reviewed bounded contract/source seam. The no-IO BEGIN
reservation, fixed original-work BEGIN signer and source-only signed BEGIN writer
are implemented. Complete phase transport and production wiring remain open. See the [source/test evidence](../../docs/research/presentation-credential-work-signer-2026-11-06.md). No live runtime, credential, service or capability is admitted here.

## Actual task ownership

The original public caller creates `RemoteCleanupOwner` in `begin_ready`.
Cleanup init retains its fixed `_cleanup` allocation at index 0 and `_work` at
index 1. Both remain behind the original start barrier until `run` opens it.
The handshake belongs to the original caller task. Do not relax its guard to
admit arbitrary tasks, use a callback signer, or treat task names as ownership.

The separate `NativePhaseWorkOwner` is retained in the original
caller after successful cleanup initialization and before the start barrier opens.
That caller must be both the handshake's original task and cleanup's original
caller. Capture exact native allocation/coroutine/slot, loop, clock, budget and
native-input join references before effects. Initialization failure must use the
existing cleanup-owner barrier/debt handling; it must not leak unlocked work.
Work-phase methods admit only the original index-1 task, never the caller,
cleanup task, a copied allocation or a matching coroutine/name. Native/key/source
retirement, parent/work cancellation and original deadline remain mandatory.

## Implemented no-IO BEGIN seam

`SocketChannel._reserve_credential_begin(remote)` runs only after the existing
fresh native PRE_GO and BEGIN_INTENT transition on the original work allocation.
It derives the frame from the exact original packet/binding; no caller frame,
digest, profile or arbitrary bytes are accepted. Existing native
`_authorize_channel` executes once. Typed native-policy/lease fences and original
socket/value/identity/deadline references are rechecked after native callbacks.
It retains the existing `_BeginWriteIntent` but does not set `_writing`, sign,
write, start a worker or mint `_BeginWriteFact`.

The original request's earlier conserved deadline remains exact; no request,
phase or task may renew it. Caller cancellation is checked before reservation.
The same reserved intent remains after uncertainty or duplicate refusal. Future
signed transport MUST consume it; re-entering old `send`/`_authorize_channel`
would double-claim the original send and create a second intent. Merely removing
`_credential_work_ready` refusal is neither integration nor qualification.

## Implemented BEGIN producer; remaining transport

The fixed `prepare_begin` operation takes no caller statement/digest. Its
signer must verify current role material and exact original work/native intent,
latch first signing attempt before callback-bearing checks/crypto, derive the
closed commitment itself, and reseal native/key/task/time context after crypto
before publishing signed data. A presend signature is not a completed write.
Actual complete-write evidence must come only from the original full write.

READY, GO and RESULT retain their own original native/child/input facts. Cleanup
CANCEL/TERMINAL/ACK require separate exact cleanup-actor and frozen earliest
budget/cause contracts; the work-task guard cannot authorize them or replace
qualified cleanup-clock observations. Broker controller/cancellation/result
writers perform direct IO and must join the same typed auth transport. STATUS
remains a separately bounded unfinished contract. No generic signer or boolean
upgrade of synthetic/no-GO objects is permitted.

## Evidence and qualification limits

Independent source/test review accepted the reservation seam and bounded fixed
BEGIN signer; root's final affected regression passed 940 tests, one skipped. Task/caller/duplicate
assertions execute through the real policy-thread/shared-slot/socket model with
synthetic native authorization and modeled peer/clock facts. They preserve zero
application bytes and no write-completion/GO/child fact. No reviewer tests ran.
Production startup, remaining phase signing, complete streaming/native publication,
installation and physical/release qualification remain unfinished.


## November 6 — actual source-only signed BEGIN write

`NativeBeginWriter` derives only the original producer, signed record, exact input3
packet and the previously reserved native intent. Callback-free actor/metadata
admission precedes retained owner/attempt latches and native guards. The full
signed record plus HBR1 frame, offsets and one completion authorization remain
bound to the same intent. No second reservation/authorize-send is allowed. Input3
permits INPUT_LIMIT+4, with total bounded by 2048+8+1024+INPUT_LIMIT+4.

An original native `_BeginWriteFact` follows only full native bytes, existing
completion authorization and final current authority/material checks. Native fact
does not open old unsigned READY/GO/CANCEL/result transports. Historical local
retirement additionally requires the original work task joined; no write-quiescence,
resource, remote/native release or production startup follows. See
[write evidence and limits](../../docs/research/presentation-signed-begin-write-2026-11-06.md).


## November 6 — original-work signed READY cursor

`NativeReadyReceiver` joins only the original completed signed BEGIN writer and
consumes one existing native receive claim on that same live work allocation.
It validates bounded broker READY context/signature/empty-frame hash under the
original clock/deadline. Current read data is NOT native READY admission: a fresh
PRE_GO/native phase transition remains separate. Production caller/generic channel
gates remain unchanged. See [read evidence and limits](../../docs/research/presentation-signed-ready-read-2026-11-06.md).

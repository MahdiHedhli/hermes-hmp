# Retained asynchronous GO and continuous control ownership

## Purpose and current boundary

Complete the native-authorized remote character-image path, not an alternative
snapshot feature. Current source `f38b435` couples selected-v2 BEGIN/READY/CANCEL
only. Coupled GO source now implements the control path below; independent
implementation review and regression evidence are tracked separately in FEATURES.md.
Production activation still requires its retained runtime/source qualification. No new installed service, gateway,
permission, provider, image route or device qualification follows from this plan.

The local `ParentAuthorityAdapter.go_inline` deliberately rejects remote jobs and
coroutine callbacks. Keep that boundary. Do not wrap an async socket write in its
synchronous callback, fabricate a local child or treat READY as GO authority.
Use the existing native record, JobOwner reservation/RemoteSlot, input3 packet,
qualified channel clock and CancellationBudget; no second ledger or deadline.

## Gateway work and native admission

Retain one exact operation work task for the complete BEGIN -> READY -> optional
GO -> result-read lifecycle. Do not launch GO in a caller task after the old
BEGIN/READY task has finished: cleanup currently joins that task before touching
the socket, and an untracked second task would race cancellation/closure.

The existing cleanup owner must retain ready-notification and one-use GO-request
Future allocations with immutable origins before initializing or opening work.
Use the already required exact native selector/default Task/Future runtime.
Partial Future/Task initialization remains retained and cannot reopen admission.
The public BEGIN/READY await shields a notification future, not the work task;
READY notification is not work completion. A public cancellation freezes the
original cause before cancelling the exact work task once. The fixed work
coroutine waits for its owned GO-request barrier after READY while cleanup keeps
the original deadline watcher. No arbitrary callback/coroutine is queued.

An explicit one-use `RemoteOperationOwner.go()` request is permitted only from
the same original public caller task retained by BEGIN/READY (and same loop),
within the original authorized operation. Task identity is an isolation check,
not phone/native authority. A later route must preserve this original request
lifecycle, not turn a UI callback or arbitrary task into an authority source.
The request uses that same owner and operation and opens only the
original GO barrier. Duplicate requests, another task/loop, stale READY, cancelled
caller, expired/caused budget or any owner/scope drift refuse and retire the
original operation. Public GO awaits a retained notification under shielding;
notification is local write outcome only, never execution or release proof.
Keep the original work task alive/parked after this notification until the
implemented result phase or cleanup; do not return and bolt on another reader.

The original work task freshly calls the concrete native PRE_GO observation
using the original record. Recheck original native record/RemoteSlot, exact
policy packet/challenge/profile/epoch/source proof, listener/store/device/fence
and qualified clock/domain before and after that await. Require native claim
closure, original policy-thread join/postcheck and unexpired uncaused budget.
The earlier PRE_GO checks for BEGIN/READY cannot be reused as this admission.

Consume a one-use, immutable, locally minted GO intent bound to the original
remote/native/job/channel/packet/challenge/deadline and exact work task. Capture
intent and advance the shared remote state before any encoding/write await.
JobOwner records remote GO intent separately from local child GO; state must
never pass through a fabricated child or local custody path. After a possible
write begins, outcome is UNKNOWN until concrete write completion; even completed
write proves neither broker receipt nor child execution. Post-await native/scope
checks cannot roll back intent or authorize retry. Cancellation revokes output.

## Wire ordering and cancellation

Exactly one exclusive broker control owner must retain the original cursor and
native task for the whole operation. Extend the existing receiver instead of
creating a competing `channel.receive` task or replacing its owner after GO.
Bound header/body allocation before effects. Selected-v2 grammar is:

- client BEGIN0, broker READY0;
- client CANCEL1 before GO, or client GO1 followed by optional CANCEL2;
- GO has an empty body; CANCEL has the original sixteen-byte frozen window;
- GO is forbidden while queued/before READY, after cancellation/expiry, twice,
  or under different protocol/binding/operation/boot;
- no RESULT, STATUS/ACK or started release until their separate integration.

A complete validated GO header is the complete empty GO frame. Grammar admission
sets a retained one-use GO notification for the service; the same reader task
continues waiting for CANCEL2. Never use the notification as authentication or
resource custody evidence. A GO notification cannot be cleared/replaced to
produce a second effect. If CANCEL2 is already delivered, its validated header
retires the original shared budget before resource relay; service rechecks after
notification and immediately before concrete resource effects. A received GO
alone does not renew the original work deadline or cleanup cutoff.

Gateway cleanup must select the next sequence from a concrete channel-owned
write ledger, not mutable completion booleans. Known BEGIN completion and no GO
intent permits CANCEL1. Known GO completion permits CANCEL2. Partial/uncertain
GO forbids any appended CANCEL because its bytes may be torn; preserve unknown
debt and attempt only supported local retirement after actual I/O join. No
reconnect, replay, new channel, implicit second cancellation or fresh timeout.

The sender and continuous receiver share each original CancellationBudget and
qualified domain. A valid CANCEL header is a revocation hint, not semantic
adoption. Complete window validation adopts the earlier cutoff before resource
abort/poll. Local EOF/error/deadline first freezes the same budget. Partial
bytes, delivery ambiguity, expiry or faulty clocks never create another allowance.

## Service relay and retained debt

The service reserves once and launches/stages the existing controlled reader as
before. Only after READY plus the retained GO notification, current source/peer/
listener generation, exact record/resource/input bindings and uncaused original
budget may it call the concrete registry resource GO relay once. Record relay
intent before native resource effects. Service relay intent and concrete local
control-write completion are distinct from gateway GO intent/write completion;
none is a child execution acknowledgement. Recheck after any boundary; cancellation
wins over further work. No child read or result publication follows simply from
GO delivery in this step. No second control reader is created during relay.

Service cancellation freezes its original cause before cancelling the exact
continuous reader task. Actual reader/work join, original-budget resource
cleanup and separate local socket/clock closure remain required. Partial native
initializers/unjoined tasks retain channel and record debt. Started registry
entries remain PENDING/UNKNOWN until typed boot-bound terminal proof, original
parent policy/native DRAIN and credential retirement are integrated. No CANCEL,
GO notification/write, EOF, local task completion or local close releases credit.

## Acceptance and implementation order

1. READY/GO notification and request barriers plus shared remote GO intent states
   are implemented on the same retained work task. Partial initialization retains
   unknown debt; actual joins and public requester isolation remain mandatory.
2. Fresh native GO admission and one-use exact-task intent are implemented.
   Callback-free cleanup allocation validation follows the JobOwner clock before
   indexing; foreign metadata tripwires pass. Local go_inline stays unchanged.
3. Concrete GO write facts, CANCEL1/2 selection, continuous broker receiver
   and service relay are coupled in source. Neither receipt/write/relay alone
   attests execution, result validity or release.
4. Add synthetic real Unix/process causals: READY is not task join; native gate
   refusal; queued GO; GO/CANCEL delivery races; CANCEL before relay; duplicate/
   partial/late GO; lost write acknowledgement; cancellation at every await;
   factory/partial initialization; wrong instance/profile/device/operation/boot/
   packet/challenge/domain; stale generation and revoked authority; no retry or
   renewed budget; no local custody/credit release or unrelated writes.
5. Independently review exact source, serial floor/current regression matrices,
   lint/surface/privacy checks, source publication and accurate feature docs.
   Runtime/Linux/manager/latency and signed physical checks remain distinct.

After this control path, complete bounded independently validated result2 and
fresh PRE_EMIT, typed started-terminal proof and policy/native/credential
retirement, production admission, authenticated metadata/image routes and full
classic/blobatar/custom/header/details parity. Host-local images follow.

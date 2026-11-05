# BR3 operation sequencing and replay admission — independently accepted source model

This is the private broker control-state contract, not a native authorization or
remote custody receipt. Original bearer/bot/native authority stays in the gateway.
Kernel peer, endpoint, runtime and actual terminal process/pipe observations remain
mandatory before the future backend can consume any frame as trusted work.

## Replay identity

The operation field is now structured within its existing64 lowercase hex chars:
first16 are a nonzero unsigned serial1..2^63-1, remaining48 are fresh random192-bit
correlation entropy. This is separate from the input3 challenge, which remains
unchanged. The gateway allocates serials monotonically per listener generation at
BEGIN issuance, never reuses/wraps one, and never retries an ambiguous BEGIN.
These are correlation/replay controls, not a capability or grant.

Broker holds one bounded64-serial sliding replay window per registered exact
instance/listener/broker-boot scope. A new higher serial shifts its bitmap; an
unseen out-of-order serial within64 may be consumed once; consumed or older than
the window always refuses, even with a changed random suffix/channel. No terminal
ACK can make a consumed serial reusable. Counter exhaustion requires a fresh
qualified listener generation, not wrapping. A delayed serial aged out is refused,
never rerun automatically. Scope mismatch cannot advance the window. This covers
execution replay after bounded terminal tombstones are acknowledged/evicted.

Scope enrollment/replacement is not offered by this state model: active-generation
identity, old-resource drain and bounded registration are future service-manager/
endpoint/backend gates. Instantiating a new model must not silently reset a running
broker's replay history. Reserve actual bounded operation ownership and consume
admission before any spawn; capacity refusal still burns that issued serial.

## Per-direction sequence and roles

One operation connection starts with client BEGIN sequence0. Client subsequent
frames are consecutive1..3; broker frames are consecutive0..1. The codec's generic
0..3 bound is now interpreted per direction, never as a global counter.

- Broker may send READY0 after admission/input is retained, then exactly one
  RESULT1 or CLOSED1. Or it may send CLOSED0 without READY after actual known
  unlaunched/terminal closure. EOF/error is not that observation.
- Client GO is its next frame, only after READY, never twice. It requires fresh
  gateway native authorization outside this model before writing, then the broker
  relays the retained challenge once. A local intent is recorded before any
  awaited/possibly partial send; failures never roll it back for a retry.
- Client CANCEL is its next frame, once, before or after READY/GO. It can race with
  READY or a terminal broker frame. Local stale/deadline/cancellation first marks
  publication invalid even before CANCEL can be written. Late native checks
  cannot re-enable GO.
- Broker RESULT requires READY+GO and actual successful terminal custody outside
  this model. A stale/cancelled broker must not send RESULT. Gateway can receive a
  racing RESULT after local cancellation and consume it only as a discarded
  terminal message; no candidate publication survives. Closure still requires a
  separately validated authenticated remote owner, not this sequencing flag.
- CLOSED can carry only independently known terminal closure, with no body.
  Gateway ACK is its next frame, once and only after RESULT/CLOSED. ACK requests atomic acknowledgement of the globally retained exact terminal
  tombstone; it never proves child exit or authorizes reads. Original-connection
  and STATUS ACKs converge on that one idempotent broker registry operation.
  Connection-local flags cannot release a slot twice or establish closure.

Examples: BEGIN0/READY0/GO1/RESULT1/ACK2;
BEGIN0/CANCEL1/CLOSED0/ACK2;
BEGIN0/READY0/GO1/CANCEL2/CLOSED1/ACK3;
BEGIN0/READY0/CLOSED1/ACK1. READY arriving after client CANCEL remains allowable
for cleanup but never enables GO. Receiving RESULT before GO, GO before READY,
duplicate/skip/direction-inappropriate frame or any post-ACK frame fails closed.
A broker which already sent its terminal frame still accepts one valid in-flight
CANCEL at the next client sequence before ACK as cleanup-only; it sends no second
terminal. A client may similarly record its late cancellation before ACK. This
must not erase the already observed terminal message or revive publication.

Local invalidation is sticky through every await and terminal race. It cannot be
cleared in-place or by another frame. Invalidating after receiving RESULT but
before emission discards the candidate; a cleanup-only ACK may still proceed.
The model never emits HTTP, forwards GO, launches a process, calls a provider,
reads a file or issues a native decision.

## STATUS connection and unknown outcomes

STATUS is a distinct observation-only connection: client STATUS0, broker CLOSED0
(known terminal), PENDING0 (existing active/cleanup/debt), or UNKNOWN0 (no verifiable
exact retained observation). Client ACK1 is allowed only after CLOSED. No BEGIN,
READY, GO, CANCEL, RESULT, result-body replay or fresh work on a status connection.
PENDING/UNKNOWN are not closure and cannot release the gateway's reservation.
No status result can authorize publication or resume the original operation.

The codec adds uppercase bodyless PENDING and UNKNOWN for these responses. They
are not added to ordinary operation connections. Broker must authenticate exact
existing scope before lookup; an unknown/restarted boot remains unknown, never
fallback to another broker or generation. These helpers do not implement lookup.

## Tombstones, deadlines and actual custody gates

Future registry enforces active<=6, metadata<=4/avatar<=2, one per profile,
waiting<=16 and terminal journal<=64; it retains partial owners and unknown debt.
If a bounded terminal journal cannot retain required history, refuse new work.
No ACK/EOF/error/timeout converts unknown resource ownership into known closure.
Statuses are emitted only from retained exact operations/tombstones; body bytes
are never replayed on reconnect. A crashed broker/new boot cannot assert closure
for old work; gateway debt stays retained until separately qualified handling.

Both sides use the original input3 absolute monotonic deadline. No hop issues a
fresh work interval; cleanup has one frozen total250ms across every plane. This
model has no clock and must never be used to infer freshness. The future owner
must invalidate before timeout/cancellation handoff, recheck current authority
before GO and pre-emit, validate output2/work/source proof, and join actual topology-specific
child/pipes/control/native/thread custody before retirement. The shared-group
[child contract](BROKER_CHILD_CUSTODY.md) does not own the broker group and cannot
reuse exclusive-reader group_absent proof. Socket EOF or peer UID/PID
is not such proof.

## Plan / checklist

- [x] Review this sequencing/replay contract independently, including terminal/CANCEL races and global idempotent ACK boundary.
- [x] Implement source-only role/state validator and bounded replay window with
  exact types/correlation and nonreentrant mutation; no authority/closure methods.
- [x] Causal tests: one GO/cancel/ACK, cancel/READY and cancel/RESULT races, sticky
  local invalidation, late/duplicate/skipped/wrong-role/post-ACK frames, STATUS
  isolation; serial replay after simulated ACK, suffix change, out-of-order window,
  age-out, cross-scope, exhaustion, no window reset/rollback by packet.
- [x] Scanner/lint and Python3.11/3.14 fixtures; independent convergence review.
- [ ] Future BR5/BR6 actual registry, custody service, qualified peer/endpoint and
  typed remote closure authority integration. No service activation by this slice.

## Convergence and deliberately unproven boundaries

Independent lifecycle/codec132 tests pass. Root lifecycle/codec/peer/source-tree
union419 tests pass on Python3.11 and3.14.9 on this Mac, including the existing
Darwin separate-process identity fixture. Counts overlap and are not summed.
Ruff and mandatory closed-import scanner pass. No kernel/process work is done
by the new grammar or replay window.

The grammar captures binding identity/values, role and mode. Observed retargeting
permanently refuses it, including candidate inspection after a value is restored;
replay-scope replacement similarly poisons that retained window. These guards do
not attest arbitrary Python memory/code integrity or secure new-object enrollment.
Nonreentrant control mutation prevents a second intent; a poisoned grammar still
needs independent resource cleanup and cannot issue closure/release evidence.

`ACK_REQUEST` deliberately means neither acknowledged global tombstone nor slot
release. Atomic idempotent original/STATUS ACK convergence, actual registry limits,
qualified endpoint/direction, deadlines, native pre-GO/pre-emit, body proof and
process/thread/pipe closure are still required. The later enrolled no-GO service spine imports these helpers with fixed startup
scope. Its local tests mock peer identity; production qualification remains open.

Before custody implementation/activation, qualify service-manager crash/orphan
containment: the current direct reader starts a new session, so broker exit or
broker process-group termination cannot simply be assumed to close its readers.
Do not erase unknown debt or claim an OS hard bound from this source model.


Hosted CI41947357398 is terminal success on b4a97e5465c36c738d7698e86b1ed262cd50a1f1:
Ubuntu plugin job and Python3.12/3.13/3.14 Unicode jobs all pass. This broadens
source regression evidence without certifying service-manager containment,
qualified endpoints, installed listener code or physical parity.

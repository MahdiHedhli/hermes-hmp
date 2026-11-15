# BR5b retained resource API amendment — independently accepted implementation contract

This freezes concrete APIs for the accepted BROKER_RESOURCE_DRAIN.md scope. It
preserves full metadata/custom-image processing, not cleanup-only delivery.
No service or authority/route activation is introduced by these source methods.

## One retained resource set

BrokerReaderResources binds one exact already retained BrokerChildOwner and opaque
registry operation, a copied closed BrokerBinding, profile, METADATA/AVATAR kind
and immutable original deadline. It captures current PID/group and fixed recipe.
It owns one control owner, result/diagnostic pipe owner and each partial owner.
No request-selected factory, stream, executable, clock or permission callback.

Registry adds one managed start entry. It stores the resource object before any
constructor/start side effect, marks intent/capacity before launch, and delegates
to that same child owner. Constructor failure retains its partial object and child
record. The old unmanaged start path remains source-fixture-only; a managed record
cannot call unmanaged wait/signal/start, and vice versa. Resource acquisition holds
all raw stream references before constructing wrappers and catches exact failed
control/pipe owner exceptions. No input/READY until acquisition and fresh binding
checks complete. Original deadline guards remain before/after all launch phases.

Resource state is NEW, RUNNING, CLEANUP or LOCAL_DRAINED; normal-work invalidation
is sticky. Reentry invalidates publication before the in-flight method can return
success and freezes the same cleanup end. It never resets an owner or retries an
uncertain syscall. Metadata/reference/context drift prevents normal effects and
retains debt. Cleanup after ordinary work refusal can proceed only through still
known exact resource owners; unknown resource facts cannot mint observations.

## Source-owned work API

- stage_input(packet): exact bytes bounded by input3; once. Decode/copy scalar
  context and parent counts, require exact captured iid/profile/kind/deadline,
  enforce METADATA no expected digest / AVATAR expected digest. Transfer through
  the retained OwnedControlPipe once under the original deadline. No filesystem
  read is authorized by staging alone. Retain only the minimal bounded context.
- relay_go(): once, after complete input staging, only under current local scope
  and original deadline. This private source API is NOT a permission mechanism:
  the future qualified broker service may invoke it only after authenticated
  BEGIN/READY/GO grammar and fresh original gateway native pre-GO. There is no
  authorized=True parameter, token-only privilege claim or generic current callback
  offered to callers. It relays only the captured challenge via OwnedControlPipe.
- poll_result(): bounded original-deadline result/diagnostic polling plus exact
  child wait. No competing raw Popen wait and no group signal. Normal completion
  requires successful exact wait, real control/read/selector close, output2 decode
  with captured challenge/epoch, expected avatar digest where applicable, OK outcome
  and preserved parent work totals. Full chain/native pre-emit remains in gateway.
- take_candidate(): once, only while uncancelled/fresh and normal completion has
  a revalidated local drain observation. Returns bounded encoded result2 bytes as
  a CANDIDATE, never HTTP permission or a remote closure receipt. Mark intent before
  copy/return and wipe this resource set's byte buffer. Transport must retain its
  exact scope and cancellation and gateway must revalidate original authority.

Move the exact bounded result buffer from pipe owner to resource set after real
EOF, rather than retaining another long-lived full-body copy. Temporary decoder/
return copies remain bounded by OUTPUT_LIMIT; retain no result body in registry
STATUS or tombstone. Cancellation wipes owned buffers/context before any later
normal action. A caller-owned already handed-off bytes object cannot be revoked
in-place; it is still subject to service/gateway current-scope/native checks.

These APIs have no public HTTP/IPC registration. A test caller can exercise the
source with new synthetic roots; it cannot qualify a live service by calling them.
Future service must not expose relay_go or input staging before its peer/runtime/
phone-native gates. A local boolean/nonce/class instance is never that authority.

## Exact aggregate LOCAL observation

BrokerLocalDrainObservation is minted only by its retained resource set, frozen
and validated by exact identity plus captured closed scope/exit values. It joins
that child's owner-minted terminal wait, its native owning control-close fact,
its exact read ends and selector native closure and permanently retired child
signaling. Validate real closed facts even for normal/legacy pipe-read completion;
no discard is required to validate successful normal output. Thus normal result
publication is not resurrected after calling a refusal-only discard method.

The pipe owner exposes a read-only local-closed validation entry sharing its
existing exact child/control/native identity checks, while poll_local_discard
keeps its permanent refusal/wipe semantics. The resource set checks every owner,
reference and scope again when minting/revalidating its aggregate observation.
No caller-reconstructed observation, bool or header cleanup flag is accepted.

LOCAL_DRAINED and this observation mean only these local resources. They do not
prove no descendants/FD transfer or service/native/remote closure. The registry
STAYS ACTIVE/PENDING even after normal success or cancelled local drain. There is
no new started terminal/ACK path until real typed startup/runtime/no-spawn and
native/service binding is implemented and independently qualified.

## Cancellation and cleanup

abort() invalidates output immediately, wipes owned candidate/context/buffers and
freezes cleanup_end_ns = now+250ms exactly once before any cleanup action. No later
poll/reconnect/reentry extends it. A late normal syscall result is refused even
if its resources may later drain. One cleanup poll may close known control,
request one exact child-only termination if needed, perform exact wait and use
the separate local-FD-only bounded discard after wait/control close. Repeated
polls are observation/cleanup under that same end, never input/GO or respawn.

Unknown launch/child/identity/close keeps debt. Keep every partial object even
when other safe planes can still be closed. Time expiry does not assert resource
closure, and signal success alone is not wait. Full normal output decoding is
not required after cancellation; actual local EOF/close remains necessary. An
aggregate local observation may record cancelled drain without reviving work.
No mutation of the old group-based JobManager/authority semantics is permitted.

## Acceptance

- [x] Independent concrete API/authority/buffer/registry ownership review.
- [ ] Managed registry retention/exclusive ownership, actual fixed metadata and
  custom-image fixture processing with original input3/GO/output2 and native FD
  closure; no live user profile, prompt, media path or provider.
- [ ] Preinput/staged-input/post-GO/large-output/cancel-result races; cleanup end
  never extends, another owned child/controller unaffected, no registry ACK release.
- [ ] Partial control/pipe acquisition retention, stale/boundary deadline, context/
  generation/owner/fact drift, reentry, malformed/duplicate input/GO/take, failed
  close/wait/native primitive and no full-resource-copy retention/STATUS replay.
- [ ] Focused independent convergence and existing direct regressions on floor/
  current Python. Source/runtime/service/physical qualification remain distinct.

Review clarifications: poll_cleanup returns whether exact local drain is observed;
local_observation and validates_local are explicit read-only revalidation entries.
abort invalidates/wipes/freezes synchronously without I/O. poll_result is idempotent
after LOCAL_DRAINED and never repeats a wait. take_candidate still requires fresh
uncancelled scope and original deadline after completion. The source pipe buffer
moves once; temporary decoded avatar/header copies are dropped across calls.
Registry managed intent latches before __new__/__init__/start, and partial objects
stay retained. Unmanaged operations are refused for managed tickets.

# BR5b topology-specific reader resource binder — independently frozen contract

## Full feature and current proof boundary

The registry now retains exact readers before start and refuses started-resource
release. This binder is the next step toward live desktop presentation and image
parity. It must compose real input/control, result/diagnostic and child lifecycle;
it must not substitute fake group absence or a manual presentation snapshot.

No service/route/capability activation is part of this source step. Original phone
rights, native pre-GO/pre-emit checks, parent policy/work ledger and HTTP output
remain in the gateway. Broker ownership facts are not native authority. Runtime/
service/peer/endpoint qualification is mandatory before live RESULT/CLOSED.

## Retained resource set and acquisition

Registry stores a BrokerReaderResources instance strongly in the exact operation
record BEFORE calling its start routine. It binds the already retained fixed BrokerChildOwner
with that record identity, startup recipe and immutable original deadline. It
never creates a second owner for the same queued/started child. The
resource set retains the returned child owner even on failed launch. No external
callback or request-supplied child/stream/factory may be substituted.

The broker production path must use this resource set rather than returning raw
streams to the transport. After launch, retain all three exact stream references
before constructing result/diagnostic OwnedPresentationPipes and OwnedControlPipe.
Retain each returned or failed acquisition owner before a later operation. The
existing PipeAcquisitionError carries its failed owner. OwnedControlPipe currently
raises only FrameError on acquisition: add an equivalent partial-owner exception
or another reviewed exact capture before construction; never lose uncertain
close/identity state. Existing direct callers must preserve their behavior.

No input transfer or READY until exact child, pipes and control owners are held
and current. No await/thread/callback may discard partial owners. A constructor
or syscall failure retains the record and its reservations; no automatic owner
replacement, re-open, spawn retry, guessed raw-FD close or Popen compatibility wait.

## Work path and one-use input/GO

Decode bounded input3 once and bind its exact instance/profile/challenge/epoch,
operation kind, original deadline and parent work/chain identity to the retained
operation. Transport/header correlation cannot override those values. Fixed home/
policy input is supplied only by the gateway after original native authorization,
never derived from an assistant string, caller path or another profile's cache.

The resource binder has no generic permission callback. Its eventual GO entry is
reachable only from the qualified broker service after authenticated current
BEGIN/READY/GO grammar, retained operation and original gateway native pre-GO.
Record one-use GO intent before possibly partial writes. Relay only the captured
input challenge once. EOF, STATUS, timeout, CANCEL or recreated same-text request
cannot authorize GO. Cancellation invalidates candidate publication before any
cleanup. Recheck exact record/resource identity and original deadline before and
after every awaited or externally implemented step. No refreshed work interval.

Result reads stay bounded by the existing output2 decoder/work/source proof and
original deadline. A successful wait/pipe result is not an HTTP emission permit.
Gateway still compares its retained parent context and freshly reauthenticates
original rights/native generation before rendering. A late/cancelled result is
wiped/discarded; no result bytes are replayed by STATUS or journaled for retry.

## Exact local drain observations

Mint only an owner-validated BrokerLocalDrainObservation from the exact retained
resource set after observing: exact child terminal wait; result and diagnostic
EOF plus known closes and selector close; known input/control close; permanently
retired child signaling; and no uncertain resource ownership/close plane. Exact classes, captured
reference identities and closed primitive values must be checked before getters,
comparisons or syscalls. A caller-reconstructed tuple/boolean, child PID, output
cleanup JSON, elapsed timeout or socket EOF is insufficient.

This observation describes these owned local resources only. It is not group
absence, all-descendant absence, service containment, native thread drain or
publication authority. Full shared-group closure additionally requires qualified
fixed no-spawn/no-FD-transfer worker/runtime provenance bound to the SAME broker
boot/recipe/resource set. No generic qualified=True flag or source test double
may satisfy that live premise. Broker crash/restart/EOF leaves gateway UNKNOWN.
The group contains the broker and other readers; no killpg/group probe is added.

A separate typed registry terminal binder must validate this exact local drain
observation AND the startup/runtime premise before moving started records to
known terminal state. Gateway native/work cleanup remains a separate plane in
the future remote backend. Until those bindings are implemented/qualified, local
drain observations cannot release registry or native reservations or send CLOSED.

Ordinary work refusal/cancellation is distinct from unknown resource close or
identity. Existing helper uncertainty flags combine those categories. Before binder
implementation, add explicit monotonic work-refused versus FD/close-uncertain
observations without clearing the existing uncertain flag or changing direct
callers. A failed close never becomes known. Preserve the direct path's existing stronger checks; a new local
drain observation cannot revive result/GO authority. Only actual known resource
facts may retire cleanup after a work refusal.

## Cancellation and fixed cleanup budget

Begin cleanup by invalidating publication and freezing one absolute cleanup
end = current monotonic sample +250ms ONCE across all resource planes. Later
calls/attempts/reconnect do not extend it. Terminate only the retained unreaped
child once under BrokerChildOwner rules; signal outcome alone is not exit.
Continue exact wait and owned cleanup after cancellation without restoring GO,
publication or accepting a newer generation as the old operation.

Existing OwnedPresentationPipes.poll_discard explicitly requires child/group exit
before cleanup. Shared-group child wait is NOT its old group-absence precondition.
Do not silently weaken that rule or call it with a fake GROUP_GONE event. The
chosen source path is a separately reviewed LOCAL-FD-ONLY discard entry after an
exact child wait, tied to that child's retained pipe identities and known control
close. It may read/discard only those already-owned descriptors under unchanged
byte/FD/selector limits and the one frozen250ms cleanup end. It cannot open files,
renew normal output reads, return result candidates or assert descendant closure.

A surviving other writer can keep the pipe open or fill its bounded read allowance;
actual EOF/close is recorded, while timeout/limit/close uncertainty retains debt.
Even a successful local drain is only a local resource observation. The final
started terminal binder STILL requires a real typed no-spawn/no-transfer startup
qualification for that exact boot/recipe/resource set. No test qualified=True and
no unimplemented qualification may be assumed available. This breaks the source-
only dependency cycle without lowering full service closure requirements.

The existing direct poll_discard entry/group precondition and direct authority
checks remain untouched. If common bounded discard I/O is factored internally,
the two public/adapter contracts remain distinct; local FD observations cannot
supply GROUP_GONE to the old manager. Existing direct group tests must still pass.

No read/close retry after an ambiguous close, no FD/PID scan, process-name lookup,
new request, host restart or timeout-based 'cleanup succeeded'. Failed/busy/partial
plane stays retained debt. Cleanup cannot extend normal read authority or turn a
cancelled result into success. Wipe buffered payloads before a candidate retires.

## Sequenced acceptance

- [x] Independently review this full resource/authority contract, including the
  old poll_discard precondition and exact partial control-owner retention.
- [ ] Implement retained acquisition, one-use lifecycle and typed LOCAL drain
  observation; no started terminal release until full startup premise binding.
- [ ] Actual fixed reader empty input and synthetic input3/GO cases under new
  temporary synthetic homes only; real pipes/wait/close and full result decode.
- [ ] Actual cancellation before input, during input/GO, result before/after cancel,
  large output and post-GO kill; another owned reader/controller stay unaffected.
- [ ] Missing/foreign/rebound/uncertain child/pipe/control facts, failed acquisition,
  stolen reap, close ambiguity, descriptor reuse, stale operation/boot/generation,
  deadline delays and nonrenewable shared cleanup budget all retain correct debt.
- [ ] Independent source/security review, existing direct regression suite,
  floor/current Python and actual bounded kernel fixtures. Source tests are not
  physical/service/runtime qualification and cannot substitute for those gates.

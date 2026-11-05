# BR5a shared-group reader custody — accepted source contract

## Requirement and boundary

The broker must own the fixed presentation reader without inheriting the gateway's
native waitpid(-1) reaper. The BR8a fixture established a communication difference:
a new-session reader socket stayed open after broker death; shared-group EOF was
observed. This is not a process/group closure certificate. Preserve full desktop
name, classic/blobatar and custom image scope; do not replace it with a snapshot.

Add a separate source-only BrokerChildOwner. Do not change/subclass the direct
PresentationProcessOwner or pass it to the current ReaderSupervisor/authority.
No broker service, IPC endpoint, route, deployment, capability, native/file read
or phone permission is activated by this slice.

## Fixed topology and ownership

Capture the existing fixed child_launch recipe at owner construction, retaining
its exact immutable argv/environment/parser selection. Launch only that recipe,
with stdin/stdout/stderr pipes, bufsize0, close_fds=True, pass_fds=(), and
start_new_session=False. No shell, request-selected executable, preexec_fn,
process_group override, forkserver or import of Hermes/gateway/provider code.
Capture broker PID and process group; refuse use after fork or group change.
After retaining the exact Popen handle, verify child PID is positive/distinct and
its observed group equals the captured broker group. Layout failure retains the
partial owner as unknown, with no guessed signal or launch retry.

Broker bootstrap/runtime qualification must establish a single exclusive child
reaper. No SIGCHLD auto-reap, waitpid(-1), Popen.poll/wait/destructor race or other
consumer may reap this child. The worker/runtime closure must be audited not to
fork/spawn, change session/group, open unrelated descriptors or transfer them.
These are explicit activation gates, not facts this class can self-certify.
The caller must retain this owner strongly, including every failed/uncertain
owner, until qualified retirement; eventual broker registry admission must retain
it before launch. A launch exception carries the exact owner. This class cannot
make dropping the last owner reference safe; registry retention is an activation
gate. It never invents a returncode to suppress an unknown wait.
The child handle stays private. Expose only the three owned pipe streams to the
future pipe/control owners; never expose a Popen wait/signal interface.

Owner binds permanently to one non-null operation object by identity. Reentry,
observed binding/recipe/child identity drift, malformed wait, ECHILD or ambiguous
syscall causes sticky uncertainty and signal retirement. Restoring a binding does
not revive a previously invalidated owner. Retain raw known terminal facts for
cleanup diagnostics, but uncertainty cannot mint a known closure or success.

## Child-only termination and exact wait

A non-reentrant owner lock serializes exact wait and termination. One attempted
termination may issue SIGKILL only to its retained, not-yet-reaped exact child PID.
The exclusive-reaper premise and unreaped child prevent PID reuse; a numeric PID
or getpgid alone never establishes custody. Mark the attempt before the syscall.
No killpg, group probe, signal0, PID scan, process-name lookup or post-reap signal.
A successful signal is not a terminal observation. Unknown signal outcome retires
signals permanently; no retry. Termination is cleanup, never GO or work approval.

poll_wait uses waitpid(exact_pid, WNOHANG). Pending is exactly (0,0). A terminal
observation requires the exact PID and WIFEXITED/WIFSIGNALED status. Other tuples,
stopped/continued status, bools, exceptions and ECHILD are unknown. On exact reap,
record the raw terminal status and retire signals before conversion/callback;
set the retained Popen returncode to prevent its eventual destructor reaping an
unrelated PID. No Popen compatibility fallback or invented exit0.

Expose an owner-minted immutable terminal child-wait observation with exact
operation binding and revalidation of its identity/values, not a closure receipt.
Repeated observation may return that same terminal fact; duplicate wait is refused.
It proves only exact child wait under the qualified exclusive-reaper premise.
It cannot stand in for existing group_absent, pipe EOF/close, control close, native
thread drain, service containment or authorization. No generic closed=True API.
A never-started owner may be explicitly sealed once; an attempted/ambiguous launch
can never be reclassified as unlaunched. No later start follows a seal.

## Later composition and crash behavior

A future topology-specific broker closure binder must join exact child wait,
owned result/diagnostic EOF and close, input/control close, no-spawn/no-FD-transfer
runtime premise, original native/work authority and retained operation identity.
This slice provides no binder, registry slot release or remote RESULT/CLOSED.
The shared process group contains the broker and possibly other readers: it must
never be treated as one reader's exclusively owned group. No group_absent field.

Broker EOF/crash/restart leaves gateway UNKNOWN/debt. The fixture's shared-group
EOF is not recovery authority. Service-manager descendant closure, endpoint/code/
stdlib/parser/bytecode provenance, original deadline, frozen250ms cleanup phase,
aggregate capacity and typed authenticated remote closure remain separate gates.
No timeout extension, automatic respawn/replay or fresh BEGIN to resolve ambiguity.

## Plan, acceptance and independent checks

- [x] Independently review this topology/child-only contract before implementation.
- [x] Implement separate source owner, fixed launch and stream-only exposure.
- [x] Actual fixed reader with empty input: inherited group, real pipe EOF, exact
  terminal wait; no profile input, GO, file access or native authority.
- [x] Actual own child blocked on input: terminate only retained PID, exact reap;
  prove controller remains running and another retained synthetic child unaffected.
- [x] Causal refusals: recipe/binding/handle/PID/returncode drift, reentry, fork/group
  context change, duplicate start/signal/wait, malformed/pending/nonterminal wait,
  stolen reap/ECHILD, launch ambiguity, signal ambiguity, seal/launch races.
- [x] Assert no group signal/probe and no public group_absent/closure/Popen handle;
  pipe EOF alone and exact reap alone cannot release any operation/native resource.
- [x] Lint, closed-import inventory, floor/current Python tests and independent
  implementation/security convergence. Update feature inventories and upstream Gist.
- [ ] Later BR5b+ explicit topology closure binder/service/runtime qualification;
  do not claim this source slice completes BR5 or the broader feature.

## Source convergence

Independent53 child-owner cases pass. Root child/direct-process/probe/codec/peer/
lifecycle/source-inventory union513 cases pass on Python3.11 and3.14.9 on this Mac,
plus lint and closed-import scanner. Existing direct owner/supervisor remain
unchanged. The actual empty-input worker was reaped and pipes drained; the actual
child-only termination left the controller and separately owned reader running,
then that second reader was closed and reaped. No GO/profile content was sent.
Pending wait is not a readiness handshake.

Focused review found and resolved noncoercive drift checks: exact PID types and
captured identity precede syscalls; fixed recipe fields use captured references,
not foreign equality/path conversion; stream bundle exact type/identity precedes
getters. Regression tripwires verify no foreign callback, signal or launch. The
owner-minted terminal fact retains exact identity/values and cannot be replaced
by equal reconstructed data. Raw terminal status survives conversion failure;
unknown owners keep their private handle and cannot mint terminal observations.

This does not complete BR5. The future registry must strongly retain every owner
before launch, including failed/uncertain owners. Broker-only pipe/control/native
closure composition, bounded transport/service, endpoint/runtime provenance and
physical character delivery remain open. Nothing imports this owner at runtime.

## Original-deadline registry amendment

The admission registry now always constructs each child owner with its captured
original exact deadline_ns. The owner freezes that reference, rejects malformed
or rebound values and checks the same monotonic deadline immediately before
Popen. Registry additionally checks after ownership validation and after spawn.
A late return retains unknown ownership; it does not refresh the deadline, release
capacity or authorize GO. Standalone source fixtures may omit this deadline;
the registry path cannot. Its readonly startup_recipe exposes only already fixed
configuration for comparison, never a Popen or code-attestation claim.

The amended owner has59 focused cases; independent registry/child union87 passes.
Full root source union548 passes on Python3.11/3.14.9, plus lint/import scanner.
All existing activation limits remain. Broker resource closure is still unbound.

## Partial native constructor custody — November 5, 2026

The independently reviewed amendment separates native Popen allocation from
initialization. The fixed native class/new/initializer are captured from the
selected trusted runtime, with private seams used by isolated unit models.
The owner retains the allocated handle and its original snapshot before type
validation or initializer effects. An exact constructor-return flag distinguishes
opaque partial state from a successfully returned constructor; it is not wait,
stream-close, process-layout or terminal authority.

Before allocation and immediately before initialization, the standard-library
`_active` value must be the same exact empty list. No list item is inspected,
polled, removed or cleared. A foreign container, nonempty/replaced list or foreign
allocated handle refuses before initialization. Fixed recipe/context/class bindings
and the unchanged original deadline are checked after allocation. No new deadline
is issued. Reentry and malformed state remain sticky refusals.

This list observation is necessary, not atomic concurrency exclusion. A fresh
standalone namespace, no foreign constructors/reapers and strong retention of all
owners/handles remain qualification premises. Nothing monkeypatches native
reapers, SIGCHLD policy, `_active` cleanup or standard-library behavior in production.

If allocation or initialization raises, the exact owner and any allocated native
object remain retained, signals/work retire and replay/sealing refuse. Partial
PID/stream/returncode attributes are not consulted to mint facts. The native
constructor may itself close pipes or reap a failed child (inspected CPython
3.14.9 `subprocess.py` constructor/error paths). Those effects are opaque UNKNOWN;
retention prevents destructor enrollment but does not suppress constructor-internal
cleanup or recover its result as this owner's terminal observation.

The causal suite covers constructor failure before child creation, foreign handle
and `_active` state without getters/length callbacks, list replacement during
allocation, original-deadline crossing and reentry, plus attempted replay refusal.
An actual native initializer-success-then-injected-error fixture forces GC and
starts a second unrelated no-input reader without invoking the first handle's
internal poll. Fixture cleanup uses its independently retained exact own native
children and actual wait statuses. It never restores the failed production owner
from UNKNOWN or fabricates returncode/closure. No input, GO or real profile is used.

Root and independent child/registry/local-discard/partial-constructor union each
pass 120 cases on Python 3.13. Broader floor/current checks and exact published
source CI are recorded in FEATURES.md. This is a source custody improvement;
service crash/orphan containment, runtime/peer/boot qualification, native
original authorization and started terminal release remain open.

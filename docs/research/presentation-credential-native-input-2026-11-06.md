# Presentation credential to original native input handoff

Independent source review accepted the bounded correlation join, including the
finite earliest-deadline correction, on November 6, 2026. Root's final affected
regression run passed **640 tests, one skipped**, in 25.67 seconds. Review read
source/tests without executing them. The run includes credential/handshake,
input3/HBR1, original broker/channel/clock, remote/cleanup, selected protocol,
result transport, broker cancellation and terminal-claim tests.

The completed handshake derives a channel binding from its retained signed
records. It does not accept a caller's returned transcript as authority. During
existing RemoteOperationOwner construction, one attempted handoff joins the
original ParentAuthorityAdapter record/shared job slot, INITIAL completion,
actual joined/postchecked NativePolicyWork and its exact packet object. An equal
copy is refused. Input3 scope is independently decoded and hashed; its profile,
kind, challenge, epoch and exact original deadline remain bound to native state.

The typed local fence follows callback-bearing native-current and clock checks
before property access or fact mint. It checks original policy/thread references,
boolean join/uncertainty/invalid/closure state, closed original directory records,
live listener fence, original lease values and job state. The private fact is a
correlation join, not a native permission, worker-start or completed-transfer fact.
A refused attempt cannot reset the latch or replace the original failed slot.

A root positive test exposed an overstrict equality introduced in the new fence:
the existing adapter freezes the earlier of its original request ceiling and the
later JobOwner ceiling. The corrected predicate preserves
`record.deadline <= job.deadline`; input3 and the handshake stay equal to the exact
earlier record deadline. No timer is rewritten or extended. Early expectation-only
test failures also established that existing cleanup may surface authority refusal
and a half-close after the unsigned-phase gate; the corrected assertions require
retained UNKNOWN debt and zero application bytes, rather than one exception type
or an always-open peer.

Nine new composed tests use real policy-thread/directory input, native job ledger,
private keys and Unix sockets with synthetic native authorization and modeled
peer/clock qualification. Positive binding, copied packet/wrong channel rejection,
key/listener retirement, and final-current thread truthiness, policy invalidation,
listener retirement and paired owner/lease epoch changes are covered. The injected
final-boundary cases assert they reached the intended second native-current
boundary, invoked no foreign truthiness, minted no join and started no child.

Credential-attached channels explicitly refuse unsigned BEGIN/GO/CANCEL while
phase transport is unfinished. This is not a reduced replacement feature or a
production switch. Future integration must authenticate the original streaming
cursors and all direct broker controller/cancellation/result-writer IO too;
removing a refusal or toggling a boolean would not qualify that path. Existing
native/job/cleanup checks remain independent and mandatory.

Still incomplete: operator-selected paired runtime/source/credential factories,
authentication capacity and retirement, signed phase streaming, actual GO and all
name/classic/blobatar/custom-static variants, RESULT/TERMINAL/ACK/journal/native
publication joins, STATUS, installation and physical/release qualification. No
live host credentials, settings, permissions, jobs, models or providers changed.

## Configured lint follow-up

The configured repository-wide Ruff check passed after cleanup without rule
exclusions. Independent read-only comparison found all eight production modules
equal to source `c4f6f38` under only import/alias order, constant string-split to
literal-list and keyword-only builtin-dict to literal-dict normalizations.
Imported-name multisets remained identical. Test cleanup includes an Event
observing retained prefix bytes before cancellation, with the original unknown
debt/no-release assertions preserved. The final affected regression on this
cleanup passed 640 tests, one skipped, in 25.88 seconds. These are root execution
results; independent review inspected source/ASTs/tests without project execution.

## Original work-task reservation follow-up

A reviewed no-IO BEGIN seam now follows actual native PRE_GO/BEGIN_INTENT on
the existing work allocation, calls original send admission once and retains
the same `_BeginWriteIntent`. It checks original caller reciprocity/cancellation
and post-native socket/value/identity/deadline state. No signature, native write,
completed-write fact, worker or GO is produced. Root's expanded affected
regression passed 928 tests, one skipped, in 27.37 seconds. See the
[work-task producer contract](../../specs/046-bot-presentation-integration/PHASE_WORK_OWNER.md).

Separately, exact baseline source `9788b68` passed [CI run 42246085048](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/42246085048):
8,247 tests, 33 skips, 18 warnings and 190 subtests; configured lint, closed
plugin surface and privacy passed, with Unicode checks on Python 3.12/3.13/3.14.
Log hygiene had no captured logs to scan. That baseline full CI does not
qualify this later source edit or any production/device/runtime behavior.
The earlier `cc8a70f` CI failure remains historical: its two test portability/
explicit-census failures were corrected without weakening exact-set checks.

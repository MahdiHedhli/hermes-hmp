# Cancellation-safe readiness before retained cursor integration

## Observed prerequisite

A bounded synthetic socketpair probe on Python3.11 proved that the default
selector sock_recv callback can consume bytes into its internal Future and then
Task.cancel can win before the original task resumes. In that observation 22
synthetic bytes left the kernel, while the original task received zero. Saving a
cursor only after await cannot recover that offset. The current result/control
paths still use sock_recv; no cleanup-reader resumption is enabled there. They
must retain UNKNOWN rather than guess a frame boundary after ambiguity.

## Owned readiness primitive

SelectorReadiness waits only for readability. Its callback can publish only
None into a retained native Future; it never recv/accepts, copies payloads,
creates a Task or grants authority. After readiness, the original protocol task
must validate its actual mode, original clock/budget and FD, then perform concrete
nonblocking recv and commit progress synchronously before another await. EAGAIN
starts another readiness observation under the same original absolute end, not
another frame/work attempt or budget. Ambiguous interruption after actual recv
and before progress commit retains UNKNOWN and forbids resumption.

Caller retains the owner before initialization. Future allocation and exact
callback/token arguments precede native effects. Initialization uncertainty is
retained and does not permit Future methods or retry. One read-registration
attempt binds the original task/thread/process, borrowed socket and FD identity,
actual default selector/kernel backend and backend FD identity. Device/inode and
stable file type are checked rather than changing permission bits, so ordinary
Darwin peer EOF remains readable. Mutable loop/selector instance dispatch is
fenced before Future initialization and native effects. Future notification and
cancellation also fence the loop scheduler, including refusal cleanup; substituted
Futures are never notified or cancelled. Captured private loop
primitives perform registration/removal. Selector-key fields are closed before
mask/file-object dispatch, and actual callback/argument identity remains bound. No preexisting
read slot can be replaced. Capture exact native Handle/callback/arguments and
remove only that owned slot. Positively observed partial installation may retire;
absence after an exception cannot certify no installation. Replaced/foreign
handles, argument drift, FD/selector/backend replacement and unknown removal
refuse. Foreign actors cannot install/remove interest or cancel the original
notification Future.

Unrelated write interest may legitimately change during the wait. Capture its
current identity immediately before concrete removal and prove it is preserved
afterward; do not freeze it across the whole wait or restore stale interest.
Local selector retirement on timeout/cancellation grants no new IO allowance and
is not whole-operation or timely native closure. If retirement is unknown, future
integration must retain its read claim/UNKNOWN and cannot close the borrowed
channel on a fabricated no-reader fact. The primitive never closes the socket.

## Remaining whole receive/cursor integration

This standalone native primitive is not yet called by the HMP receive paths.
Bind it to the exact retained channel/work task/cursor/budget/clock before use.
Preserve outer prefix/header and body-consumption offsets, pending bounded chunks
and original credited accumulator identity across every await. Actual recv and
progress capture must precede native callbacks or later awaits; revoked result
bytes become bounded discard, never a new candidate. Hold an explicit ambiguous
recv/commit intent if either side is uncertain. Do not recover by scanning bytes
for magic or starting a replacement reader.

Integrate active timeout shortening and original-work write quiescence with the
cleanup-only original reader as one reviewed lifecycle. Continue the broker's
same CANCEL/ACK controller. Qualified producer/receiver acceptance, min stamp
adoption before subsequent cleanup IO, native PRE_EMIT/DRAIN and credential
retirement remain mandatory before terminal dispatch, release or public images.
No helper hint, registration flag or codec is a qualification capability. Trusted
installed Python/default-loop ownership is a premise, not a memory sandbox.

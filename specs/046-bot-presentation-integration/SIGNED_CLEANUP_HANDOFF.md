# Signed original-reader cleanup handoff

This is the next integration contract, not an enabled path or qualification pass.
The reviewed envelope/body stop receipts and discard data parser are prerequisites.
Existing signed `CleanupReadGate.request` remains False. Existing CANCEL signing
still requires actual whole-work join. No runtime flag or legacy-owner cast may
substitute for the new contract.

## Two facts and their ordering

1. A synchronous request reservation is considered after the actual pre-poison
   signed capture, output withdrawal and first minimum cleanup-budget freeze,
   but before completing the original cause or cancelling the original work task.
   It requires exact original live registered wait/capture/native handle ownership,
   uncompleted original cause, no pending recv/feed/commit/send and actual existing
   write-quiescence. Unknown registration, missing quiescence, stale scope or no
   remaining budget refuses reservation and preserves ordinary Task cancellation.
   Reservation alone suppresses cancellation; it grants no read or CANCEL authority.
2. After that exact cause completes and the original wait actually retires, the
   original uncancelled work task correlates its distinct native wake receipt to
   reservation/capture/scope/Future/handle/counts and frozen budget. Only then may
   it mint one separately allocated signed read-ready notice for its original
   cleanup task. Original actor/capture/cursor seals repeat after native callbacks.
   No new task, read interest, deadline or result candidate is introduced.

Do not put either fact in legacy `gate._fact_origin`, construct `_Request(mode=...)`
for a signed reader, set `_work_joined` while work lives, or use a caller-selected
actor/phase boolean. Retain partial allocation/notice ownership before effects;
ambiguous notification consumes its attempt and preserves unknown debt.

## Fixed actor and budget contracts

The original work task alone continues the same cursor in cleanup-only mode. The
original cleanup task alone writes one signed CANCEL and later one separately
qualified ACK. A fixed signed-read cleanup-material seam must prove actual
read-ready admission, reciprocal original allocations/channel, current retained
role keys, existing write-quiescence, no concurrent writer, correct sequence and
the SAME earliest frozen budget before and after native boundaries. It does not
borrow ordinary work authority or revive retired listener/policy/publication.
Existing whole-work-joined signing branches stay unchanged for other paths.

Cleanup waits on the exact signed read-ready notice or original work termination
under remaining original cleanup time before deciding the signed CANCEL route.
Waiting for whole-work join before this CANCEL would deadlock a reader waiting
for terminal. Conversely, reservation without read-ready must never send CANCEL.
If work exits, observe its actual result and use only already-qualified historical
retirement/closure contracts; there is no replacement reader.

## Exact framing continuation

Bind the data-only `SignedResultDiscard` to the actual retained envelope prefix or
body's ORIGINAL digest/hash allocation and received/committed counters. Supplying
a matching digest object is not ownership proof. Preserve the original captured
counts and credit every subsequent native byte before mutable alias checks.
Read only the exact `needed` bounded count; no overread, lookahead body cache,
terminal scan, authentication restart or replay. After cause, bytes are discard,
never native buffer feed/candidate/adoption/publication. Clear original image
aliases and temporary chunks on all refusal paths.

At an exact known record boundary, the retained protocol grammar may permit a
direct signed ABORTED TERMINAL when no RESULT has begun (including pre-READY).
Do not require a fabricated RESULT before that legitimate abort. Authenticate the
actual phase/header against the closed allowed next transitions; an unverified
phase string is DATA, not permission. A partial authentication prefix stays on
that SAME current record until its signed phase is known; never retry it under a
different parser after refusal. `SignedResultDiscard` implements only the RESULT
branch and does not decide this boundary dispatch. Once RESULT is established,
consume its exact full remainder/hash before the next TERMINAL; no scanning,
skipping, truncating or restarting to find a terminal. Midframe disconnect or
truncation remains unknown. Normal OK requires actual completed RESULT.

Consume the legitimate next signed TERMINAL on the same cursor. Verify pinned role,
transcript, operation, boot/generation, sequence and bounded envelope/body. Apply
only a qualified inherited earlier cleanup end before later I/O. Decoded terminal
DATA, signed frame consistency, accepted terminal claim, ACK completion, original
controller/work joins, local FD/clock closure and native release remain separate.
No helper parse or EOF proves any other ownership plane.

## Required causal qualification

Use actual private signed peers and original tasks/selector registrations; do not
manufacture successful captures, wake/notice/CANCEL/terminal/ACK facts. Cover:

- failed reservation still cancels; cause/ready/read races and duplicate requests;
- partial auth/header/body at each boundary, original hash identity and no replay;
- CANCEL before terminal and no notice/no CANCEL, no terminal/no ACK;
- wrong task/scope/instance/boot/generation and revoked keys/current-role refusal;
- earlier/expired budgets and native callback drift without deadline renewal;
- partial/unknown sends/reads, notice ambiguity and no automatic retry;
- output withdrawal, no competing consumer/writer and no payload error aliases;
- actual known local retirement separately from remote/native/release acceptance.

Production composition and physical/device/release qualification remain separate.

### Disabled signed reservation preflight — November 6, 2026

The original registered envelope/partial-body wait can now yield a one-attempt
preflight record tied to frozen capture/cause, actual write-quiescence, current
retained role and original cleanup budget. Post-callback structural/counter/native
custody seals refuse drift. It is retained DATA only: signed gate.request STILL
RETURNS FALSE and external Task cancellation remains. No read-ready notice,
read/CANCEL/ACK authority, release or publication follows. Separate original-work
admission/notice and full same-task continuation remain prerequisites.

The current disabled preflight component covers only captured GO_SENT with an
active envelope or unvalidated partial-body registered wait. Normal post-result/
adopted-image terminal waits require their own exact cursor/allocation proof and
are not admitted by this component; pre-READY and already-retired waits retain
their existing paths. Full integration must cover those legitimate lifecycle
positions rather than silently excluding them from the feature's final scope.

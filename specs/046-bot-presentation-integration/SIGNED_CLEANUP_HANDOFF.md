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

### Signed original-work stop notice — November 6, 2026

A distinct one-shot notice now retains actual native Future/fact allocations and
correlates original envelope/body wake retirement under original work actor,
current retained role and earliest cleanup budget. Partial initialization, paired
alias substitution, final-clock revocation and ambiguous notification retain
unknown debt/no retry. It has no consumer or signer: signed gate.request remains
False and normal external Task cancellation remains. Original-cleanup current
notice validation, concurrent-CANCEL authority and same-reader drain/terminal/ACK
still require separate qualification. Future DATA is no I/O or release permission.

### Actual parked-receipt expiry check — November 6, 2026

The controlled real-peer case now observes original controller timeout expiry
after actual CANCEL adoption: authenticated receipt remains retained, late service
consumption refuses, frozen end does not renew and no job credit/release follows.
This is expected negative qualification, not proof of the earlier intermittent
failures' causes or a new cleanup/terminal/native permission. Production guards
are unchanged; current consumption and original deadline remain independent gates.

### Fixed cleanup-side current stop DATA — November 6, 2026

The original cleanup actor can now validate an actually delivered signed stop
notice against the original live uncancelled reader, allocation, role and earliest
budget. Root bounds a wait on the actual retained notice/work pair, with dispatch
checks AFTER clock callbacks and held-identity rechecks after await. Wrong sender/
completed-work queries refuse; currentness drift retains unknown debt. This is
stop DATA only: signed request remains False, read-admission/concurrent-CANCEL
authority is absent, and original work-join/signing gates stay unchanged.

## Authenticated cleanup boundary commitment data — November 7, 2026

Added a closed-context check for one signed broker RESULT/1 or TERMINAL/2
commitment. The untrusted discriminator selects only a fixed signed expectation;
other phases, wrong sequences/context/peers and damaged signatures refuse without
parser fallback. No body is consumed and no cursor or transition is authorized.
A direct terminal still needs a separately qualified ABORTED claim; completed
RESULT remains required for OK. Partial-frame continuation and production dispatch
remain unfinished; signed gate.request remains False.

Independent read-only review found no issues. Focused phase/stream regression:
61 passed in 0.28s. Initial new negative fixtures used invalid frame bodies and
failed before reaching the helper (4 failed, 34 passed); their framing was fixed,
with no production guard relaxation. No device, deployment or settings changed.
Previous intermittent broker causes and sender-destination risk remain unresolved.

## Bounded cleanup authentication-prefix reader — November 7, 2026

`SignedCleanupAuthPrefix` preserves a partial HBA1 record and exposes only the
exact remaining authentication-byte count. It accepts no following outer header
or body, never scans/restarts, and permanently refuses overshoot, truncation,
invalid signature or substituted state while clearing its original framing
buffer. Its completed value is authenticated RESULT/1 or TERMINAL/2 commitment
DATA only. It does not select a legal lifecycle transition, validate an ABORTED
claim, bind a native cursor or enable signed cleanup.

Independent read-only review accepted the component. Focused phase/stream checks:
80 passed in 0.34s; expanded credential/cleanup/terminal/layout regression:
1,112 passed in 144.50s. Checks include partial prefix boundaries for both fixed phases,
exact record separation, sticky refusal and foreign arithmetic rejection. Native
reader admission, same-reader drain/terminal/ACK, production character images and
physical/release qualification remain open; signed gate.request stays False.
The current helper covers only RESULT/1 and TERMINAL/2 authentication data.
Earlier direct-terminal sequence positions need their own retained transition
expectations before production composition; they are not implicitly admitted.

## Original reader post-notification currentness — November 7, 2026

The original uncancelled reader can now revalidate the actual delivered stop
Future/fact and exact stopped envelope/body cursor after selector/FD and original
cleanup-clock callbacks. It repeats retained role, stopped counts, Future/fact
allocation and fixed reader-actor seals. Wrong/premature actors refuse without
consuming the original state; admitted currentness drift retains unknown debt.

Independent read-only review accepted the source. The initial focused run found
four test synchronization timeouts: a new foreign-actor await after publication
let original cleanup enter its work join before the fixture probe was installed.
The foreign-actor probe now runs before publication; no protocol state is restored
and no guard relaxed. Focused rerun: 20 passed, 42 deselected in 6.48s. Actual
13-byte partial-body currentness is also covered. Final exact-source expanded
credential/cleanup/terminal/layout regression: 1,114 passed in 139.66s. Full
server/tools lint and whitespace checks pass.

This is a required pre-admission currentness check, NOT running-reader admission,
receive/registration permission, concurrent CANCEL or terminal/ACK/native release.
The future reader owner still must bind its exact parser/digest allocation and
account for every native byte; signed gate.request remains False. No deployment,
build, install or settings changed. Prior broker causes and sender risk stay open.

## Original stopped parser/digest binding — November 7, 2026

Added one-attempt `SignedStoppedCursor` acquisition on the original reader after
actual delivered-stop currentness. The actual parser is independently retained
BEFORE construction, with a separate original state allocation. An envelope
keeps its exact partial authentication record plus any frozen outer-header
remainder; a partial body reuses the SAME original committed-frame digest and
received/committed count, without copying or restoring image data. Currentness
reseals those originals after notice/native/clock callbacks. Partial parser
construction failure remains attributable and cannot retry.

Review found that paired parser/state aliases alone could accept a coherent
replacement. Independent allocation anchors fix that finding; the actual final-
clock exact-type replacement causal now refuses and preserves the original
allocation. Independent read-only re-review accepted. Focused envelope causals:
23 passed; actual original13-byte body digest binding: one passed in1.71s.
The body parser and stream additionally retain the ORIGINAL envelope intent's
binding identity, rather than selecting the expected binding from mutable digest
aliases. A final-clock equal-but-distinct binding substitution across both parser
and stream refuses; focused causal: one passed in1.75s. No protocol state was
restored. The pre-refinement expanded run passed1,138 cases in133.90s; it is not
claimed as final-source coverage. Final exact-source expanded regression:
1,138 passed in138.08s; full server/tools lint and whitespace checks pass.

Cleanup authentication now requires the retained expected broker sequence, not
a sequence chosen from the wire: RESULT only1; TERMINAL exact0,1,2 as appropriate
to the retained sequence. This closes the earlier fixed-TERMINAL/2 data-helper
limitation. It does not itself establish a lifecycle transition or validate an
ABORTED claim. No production early-abort qualification is claimed.

The bound cursor exposes NO feed/recv/registration/signing method. Native read
admission, exact next-byte accounting, concurrent CANCEL, terminal/ACK/native
release and production character-image delivery remain unfinished; signed
request stays False. No deployment/build/install/settings/device changed. Earlier
broker causes and native sender-destination risk remain unresolved.

## One-shot original reader IDLE admission — November 7, 2026

`SignedCleanupReader` now retains one actual partial owner on the bound original
cursor BEFORE native currentness checks. Its scope, cursor and admission fact
have independent allocation cells. Current IDLE admission repeats fixed original
actor/cursor/native/role checks, the exact next bounded count and the original
minimum budget ceiling; no parser/digest advances and no deadline renews.
Wrong/duplicate actors cannot borrow or recreate the owner. Coherent owner/scope/
fact substitution, early/post-fact key revocation and foreign reservation/end
metadata refuse without foreign getters/ordering or a retry.

Independent review required retaining the partial owner before native checks and
exact nested reservation/end type fences; these are fixed and causally covered.
The corruption test additionally prompted failure paths to poison the HELD
original notice/cleanup reservation, never rediscover authority through drifted
cursor fields. Independent final read-only review accepted. Thirty focused
envelope cases passed in8.80s; original13-byte body case passed in2.00s. Final
exact-source expanded credential/cleanup/terminal/layout regression: 1,145
passed in142.06s. Full server/tools lint and whitespace checks pass. One
fixture assertion initially conflated idle-admission refusal with historical
original stop retirement: that independent local stop correctly remains valid.
The assertion was corrected; no production guard or unknown state was relaxed.

This is IDLE admission only. It exposes no receive/registration/signing operation
and enables no cooperative gate. Native progress handoff, exact per-byte accounting,
concurrent CANCEL, terminal/ACK/native release and production character-image
delivery remain open. Existing stopped-body validators must not be weakened to
accept an advanced digest; future native continuation needs a distinct qualified
handoff. No build/install/deployment/device/settings changed. Prior broker causes
and native sender-destination risk remain unresolved.

## One bounded original-task native read — November 7, 2026

`presentation_credential_cleanup_read.py` now owns one nonblocking receive on the
SAME original authenticated socket/task after IDLE admission. Its exact request
count comes from the bound parser, with no caller count/address/flags or new
reader/interest. Fixed C socket/backend identity, nonblocking/timeout/inheritable
probes run AFTER the final clock callback; full typed metadata, original role/
actor/budget/parser/count and I/O claims repeat before receive. Fixed native
MSG_DONTWAIT is used. An independent payload-free count allocation is retained
BEFORE post-read callbacks, separately from privately owned pending bytes.

Root observes pending counts on its fixed cleanup actor, without a signing grant.
Old unadvanced stop/cursor/IDLE APIs refuse reuse after the read attempt. The
actual original work's finally path finds its native owner through independent
allocation cells on the originally held gate and drops unconsumed pending aliases.
Observed native counts survive UNKNOWN; a chunk receipt is never frame credit.
There is no parser/hash/accumulator advancement or result candidate restoration.

Independent review required the post-clock descriptor/mode fence and final full
metadata/I/O-claim seal; both are implemented. Eighteen focused header cases pass,
including real private-socket timeout/blocking/dup2 with ZERO receives, final-probe
foreign-counter/claim drift, post-read role/descriptor/pending/count/scope/receipt
substitution, EOF, actual EAGAIN and ambiguous receive acknowledgement. Source
failure paths retain counts, not payload/error aliases, and never retry. The
original13-byte body plus an injected3-byte tail also passes pending-read checks;
its original digest remains at13 and accumulator stays empty. That fixture tail
is NOT broker-writer/currentness or whole-frame qualification.

Earlier test-only failures are retained: a broad ambiguous-notice selector matched
the new receive case (renamed narrowly); strict plain-int checking initially
rejected stdlib MsgFlag (fixed by exact stdlib-type C conversion); existing close-
debt teardown needed the precise new allocated NativeCleanupRead unknown reason.
No production close guard or role/currentness rule was relaxed.

This is ONE PENDING READ only. Parser consumption/active digest handoff, native
readiness continuation, full drain, concurrent CANCEL, terminal/ACK/native release
and production character delivery remain unfinished. Signed gate.request stays
False; production still parks after GO. No build/install/deployment/host/device
change was performed; tests used only owned private synthetic Unix sockets.
A further real-task case invalidates only the synthetic root initialization flag
AFTER a successful8-byte read and actual cleanup observation: held-original memory
retirement still drops pending aliases and preserves counts/UNKNOWN, without
restoring the flag. Retirement now runs independently of that initialization
flag; write-quiescence publication remains guarded as before. Nineteen focused
native header cases pass in6.19s. The prior expanded run is retained as a FAILURE:
1 failed,1,926 passed,1 skipped in174.24s. Its existing go_relay broker-control
reader refused and broker closure stayed false. Failure-only primitive cursor/
timeout/notice state capture was extended; no new native clock sample or success
recovery is added. The cause is unresolved, regardless of any later green run.
The second broad run also remains a FAILURE: 1 failed,1,927 passed,1 skipped in
181.56s, now at the existing body_adopt_capture_phase broker cancellation-adoption
refusal. No production control/close guard was changed. Failure-only primitive
capture was extended to that exact case; its failure branch has not thereby been
qualified. New native-read cases passed; broad broker lifecycle/release remains
unqualified. The isolated go_relay/body selection passed3 cases in2.83s, which
shows an available path but does NOT resolve either broad failure. The latest
body_adopt_capture_phase isolated rerun passed1 case in1.88s; its new diagnostic
failure branch was not exercised, and the broad failure remains unresolved.
This checkpoint is source-only and NOT a green whole-transport qualification.

Prior intermittent broker causes and native sender-destination risk remain open.

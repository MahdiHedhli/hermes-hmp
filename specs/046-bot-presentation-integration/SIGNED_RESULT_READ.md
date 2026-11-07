## Same-reader authenticated TERMINAL/2 frame — November 7, 2026

The original read owner now starts a separate TERMINAL/2 frame only from its actual
completed successor-auth allocation and receipt. The first RESULT frame and its
parser/counters remain retained. Both the full-frame and original partial-body
RESULT paths reach bounded terminal bytes and the exact signed frame digest on
the same socket/task under the original role and earliest cleanup end.

RESULT and terminal frames share the fixed exact-needed read/finish algorithm.
Two private dispatch identities select only already-owned frame slots and their
fixed currentness validators; they cannot provide a caller-selected parser,
phase, socket, receipt or authority. Held scopes survive constructor/feed/hash
boundaries; independently retained active-step cells preserve actual counts and
pending ownership after paired slot drift. Final dispatch reseals canonical
header/binding/hash metadata and both live I/O claims after the last callbacks.
An uncertain or competing read/write claim is never overwritten or cleared.

New synthetic cases cover both RESULT predecessor paths, bad terminal hash,
constructor acknowledgement loss, auth-scope clock drift, post-feed scope/receipt
replacement, paired step drift, changed finish data/ledger, final dispatch scope
substitution and final read/write claim changes on frame and auth reads. Actual
terminal bytes remain opaque bounded DATA; the fixture's b"abcd" is deliberately
not a qualified terminal claim. Independent read-only review accepted the source.
Exact-source checks:41 focused cases passed in14.05s; expanded affected regression
2,038 passed,1 skipped in192.34s. Full lint, plugin surface and whitespace pass;
execution source hashes match. Focused cases overlap the expanded run.

A pre-terminal-frame auth acquisition refusal in an earlier focused run remains
unexplained; its isolated constructor case later passed. Later green runs do not
establish that cause. Earlier broker failures and the sender-destination incident
also remain unresolved. Terminal domain-claim/cleanup-budget acceptance, earlier
terminal lifecycle positions, EAGAIN waiting, CANCEL/ACK/native release, production
routing and physical character-image delivery remain open. No app build/install,
live host/device/grant/provider or deployment change occurred.

## Same-reader RESULT/1 to TERMINAL/2 authentication — November 7, 2026

The original native reader now admits a distinct next authentication record only
after its actual completed RESULT/1 frame or original partial-body completion.
It retains those predecessor allocations and counts, derives sequence2 from the
closed original context, and keeps the same task/socket/current role and original
cleanup end. No predecessor parser, receipt, sequence or read flag is reset.
Exact-needed nonblocking receives record actual byte counts before callbacks;
independent active-step ownership survives paired slot drift, and pending bytes
must remain the actual returned chunk. Completed predecessor step self-cells are
retired only after a committed successor, keeping short-read history bounded.

The next original pinned signature verifies TERMINAL/2 authentication DATA.
Currentness rechecks the held stage/scope after predecessor native callbacks;
final pre-receive seals are typed and callback-free. Parser allocation, finished
state and canonical commitment fields are joined before an auth receipt. Prefix
buffers now have an independent owned allocation cell and fixed owned-buffer wipe.
No TERMINAL frame/body, domain cleanup claim, ACK or release is accepted here.

Thirteen new private-socket cases cover both RESULT completion paths, damaged
signature and wrong signed transcript context, constructor acknowledgement loss,
final-FD foreign metadata/flag, paired post-receive step drift with retained read
claim, GC-disabled short-read retirement, predecessor scope/counter drift and
coherent post-feed scope replacements with foreign pins/context rows. Constructor
and feed boundaries preserve the actual held scope before comparisons.
Independent read-only review accepted the repaired source. Exact-source checks:
27 focused cases passed in9.49s; expanded affected regression2,023 passed,1 skipped
in182.17s. Full lint, plugin surface and whitespace pass; execution hashes match.
The focused cases overlap the expanded run.

Terminal frame/body continuation and acceptance, earlier/direct-terminal lifecycle
positions, EAGAIN waiting, CANCEL/ACK/native release, production routing and physical
character-image delivery remain open. Earlier broker failures and sender-destination
incident remain unresolved. No app build/install, live host/device/grant/provider
or deployment change occurred.

## Original partial-body digest completion — November 7, 2026

`NativeCleanupRead.finish_body()` now finishes the SAME `SignedResultDiscard` and
original full-frame hash after exact-needed native continuation reaches its end.
The native image-only hash is a separate allocation and is not mistaken for the
full-frame digest. Original progress allocation/type checks precede nested access;
an independently retained one-shot finish attempt precedes parser/hash/currentness
boundaries. Actual finish results and frozen post-cause byte counts are retained
before callbacks. Finished validation reseals original parser/stream/hash/buffer,
result allocation, primitive counters and digest values after hashing, without
calling unfinished-parser guards or constructing a replacement digest.

Ten private-socket synthetic cases cover actual original partial-body completion,
initial fence refusal, lost finish acknowledgement, corrupted wire data, foreign
ledger, instance finish override, changed returned length, foreign progress seal,
and final-hash foreign result-cell/counter substitutions. Refusals do not call
foreign getters/index/equality or retry. The old body committed offset remains13,
the original stream advances to its full body length, and no image accumulator or
candidate is restored. Original cleanup observes consistency DATA only; work exit
still preserves UNKNOWN. Independent read-only review accepted the repaired slice.
Exact expanded regression:
2,009 passed, 1 skipped in 184.50s; full lint, plugin surface and whitespace checks
pass. Execution source hashes remain unchanged.

EAGAIN waiting, explicit next-record grammar, terminal acceptance, CANCEL/ACK/native
release, production routing and physical image delivery remain unfinished. Earlier
broker failure causes and the native sender-destination incident remain unresolved.
No app build/install, live host/device/grant/provider or deployment change occurred.

## Captured authentication and retained outer-header continuation — November 7, 2026

A fully captured original authentication record can now be verified once without
fabricating a post-cause receive or consume. Native read-attempt, returned/count,
consume and progress cells remain absent/false, and the auth receipt explicitly
records zero new bytes. Original parser/state allocation joins and exact primitive
checks precede comparisons, followed by current role, original actor/budget and
socket fences. The original cleanup observer recognizes this distinct path; frozen
notice/read APIs cannot revive it, and work exit preserves UNKNOWN and retires
owned pending storage.

The same original reader then consumes retained outer-header bytes exactly once
and reads only the remaining frame. A zero initial frame ledger does not recount
captured authentication or header bytes. Six focused synthetic tests pass: actual
captured authentication plus four header bytes and completed RESULT data, initial
FD-fence refusal, verification followed by lost acknowledgement or role retirement,
foreign post-verification count, and final-clock exact-scope/foreign-value
substitution. Refusals perform no retry or foreign comparison/length operation.
Independent read-only review accepted this bounded slice. Exact expanded regression:
1,998 passed, 1 skipped in 177.99s; full lint, surface and whitespace checks pass.
Execution source hashes remain unchanged.

Original partial-body completion using its SAME digest, EAGAIN waiting, subsequent
grammar transitions, terminal acceptance, CANCEL/ACK/native release, production
routing and physical image delivery remain open. Earlier broker failures and the
native sender-destination incident remain unresolved. No app build/install, live
host/device/grant/provider or deployment change occurred in this source work.

## Original-reader committed frame stage — November 7, 2026

The retained native reader now advances from actual newly completed authentication
into one exact-needed RESULT/1 or TERMINAL/1 frame on its original socket and work
Task. The captured pre-cancellation phase selects grammar only; live work remains
UNKNOWN. Independently retained frame/parser/step allocations and cumulative byte
counts survive callback failures. Fixed class dispatch rejects instance overrides.
Completed header, stream, hash, digest and returned-fact identities are rejoined
before returning consistency DATA; no terminal claim or release is granted.

Eight focused synthetic cases pass: RESULT and TERMINAL data, corrupt body hash,
foreign auth scope, feed/finish overrides, post-finish ledger substitution and a
copied header allocation. Independent read-only review found no remaining blocker
in this slice. Exact expanded regression: 1,992 passed, 1 skipped in 177.42s; full lint,
plugin surface and whitespace checks pass. Execution source hashes are unchanged.

Scope remains incomplete: captured-complete authentication with a retained outer
header needs a zero-new-byte transition, and an already partial body must finish
its SAME original digest. EAGAIN waiting, next-record grammar, terminal acceptance,
CANCEL/ACK/native release, production routing and physical character-image delivery
remain open. Earlier broker failures and the native sender-destination incident
remain unresolved. No app build/install, live host, grant/provider or deployment
change was made by this source work.

# Original gateway signed RESULT cursor

Status: the fixed GO_SENT custody tail, signed envelope cursor and same-original-
work body/private-candidate owner, private native adoption and original-caller
notification are qualified source components. Signed body digest and independent
native result2/parent/revision checks remain distinct from terminal authority.
Cooperative cleanup continuation and production dispatch/publication remain open.
Preserve the complete requested character image without a snapshot or unsigned
compatibility fallback. The broker producer/writer are separate
qualified components; local full write is not gateway receipt or native release.

## Retained owner and actual call path

Continue the original gateway work Task after its actual completed signed GO,
using the original retained channel, cleanup/work allocation, input3 packet,
job/buffer/parent context, operation, clock and original work deadline. The current
credential work Task parks for first cause after GO; the new continuation must
replace that internal park only when its exact retained signed-result owner is
qualified. Do not create another receive Task, use a public generic channel read,
accept a caller-supplied completed record or open a boolean work bypass.

Retain the partial receiver before native initialization/read effects. Wrong-task
or premature admission must not poison the original owner; admitted refusal is
sticky and never retries from a new owner. Keep the existing selected result2
independent native buffer/custody validation rather than trusting broker metadata.
The existing generic credential work gates must stay closed.

## Fixed current custody prerequisite

`RemoteOperationOwner._result_intent_local` is pinned to actual native GO_SENT,
original work actor/credential material, policy/lease/listener/admission/context and
uncased original budget. It samples no time and grants no I/O. Use it after
separate current native checks and the final descriptor callbacks; never reuse
GO_INTENT checks by changing a phase field or passing a caller-selected phase.
See [tail evidence](../../docs/research/presentation-gateway-result-custody-tail-2026-11-06.md).

## Current source integration decisions

The current original work allocation is retained by `RemoteCleanupOwner._work`.
After actual GO_SENT/write-quiescence it intentionally parks on its original cause
Future for credential channels. A receiver component may be qualified directly
on that original actor before production continuation is opened; no new Task or
caller-provided callback can stand in for it.

At admission, use the actual completed `NativeGoWriter.current_sent` proof while
the channel is idle. That method's current guard requires `_reading is False`;
do not reuse it during an active read by temporarily clearing the read flag.
Historical complete GO metadata plus the fixed current result-custody tail and
native current checks must cover subsequent read boundaries. The completed
`NativeReadyReceiver._metadata` also currently binds channel reading to its own
inactive flag. Add only a fixed reciprocal READY-to-RESULT ownership description,
analogous to the reviewed writer handoff, rather than weakening that invariant.

`RemoteResultOwner` and its `_ResultCursor` are the selected unsigned result
owners. Their general credential gate stays closed. The native outer-header
cursor is capped at 1,032 bytes; signed HBA1 metadata needs its separately bounded
authentication cursor. Do not increase the native header limit to fit auth bytes
or silently publish a different owner in closed `RemoteResultOwner`-typed slots.
Reuse the original native `BoundedResultBufferV2`, bytearray custody and parent
context through an explicitly reviewed typed bridge. The complete path still
needs original candidate ownership, cleanup withdrawal and result notification.

`CleanupReadGate` currently captures selected unsigned/pre-result cursors, not a
signed RESULT cursor. Full integration requires a fixed typed continuation for
its actual auth/header/body/digest progress. Unknown/partial signed reads cannot
be relabeled as its legacy cursor or handed to a replacement socket reader.
Before that continuation is qualified, fail closed with retained debt; never infer
remote terminal settlement from local task/FD retirement. Keep the original
first-cause hook ahead of native clock sampling so any new private candidate cell
is withdrawn together with native output custody.

## Envelope component checkpoint

`NativeResultEnvelopeReceiver` now retains a one-shot original-work cursor for
bounded HBA1 and committed RESULT outer header only. Actual counts, current final
GO_SENT custody and exact known local selector-cancellation retirement are checked.
The historical READY read slot recognizes only the reciprocal fixed result owner.
No body digest or native result follows from its private envelope fact. See
[envelope evidence](../../docs/research/presentation-signed-result-envelope-2026-11-06.md).

## Signed record and original frame

Read one bounded HBA1 RESULT record from the original socket/cursor, under the
original work budget. Require pinned original broker role/public key, own gateway
pin, immutable original transcript/input/scope/domain/generation, operation/channel,
phase RESULT, broker-to-gateway direction and sequence1. Enforce record length
before allocation; no algorithm, public-key or identity fallback.

Read bounded canonical broker header next and bind its selected-v2 RESULT seq1,
original operation/channel and body length to the checked commitment before any
body allocation. Hash the exact actual header plus actual body chunks while
feeding the existing bounded result2 buffer. Do not concatenate an additional
full image frame, reconstruct a different canonical wire as if received, or
allow a digest claim to substitute for actual byte acquisition. Complete signed
commitment validation and native result2/parent/expected-revision checks are
independent requirements. Retain only the original private candidate until native
terminal/custody/publication gates are satisfied.

## First cause and reader continuity

Before and after every native read/readiness/hash/feed/finalization boundary,
check original scope, role material, actor, clock/budget, descriptor and buffer
identity. End native descriptor callbacks with a fixed callback-free current
role/custody/cause tail; no callback can retire keys then permit another read/feed.
Credit actual native bytes before mutable-alias validation and retain framing
progress on refusal. Partial headers/bodies, unknown I/O and lost acknowledgement
never justify a replacement reader or replay.

Original first cause must withdraw candidate references and retire the original
work Task/selector. Preserve the same cursor's exact framing/count/digest progress
for bounded cleanup discard and later signed TERMINAL/ACK continuation; do not
start a second reader on the socket after cancellation. Frozen earliest cleanup
budget cannot grow. Known local selector retirement is not remote settlement.

## Required causal verification

Use private synthetic peers/disposable native source only. Test actual full signed
wire and result2 validation, arbitrary fragmentation, EAGAIN and partial native
counts; bad signature/transcript/role/key/scope/revision/size/digest; wrong actor,
revocation and cancellation at final native boundaries; original partial read to
cleanup handoff without competing reader; no payload in refusal tracebacks/facts;
short/unknown/torn writes, duplicate RESULT and no retries. Keep metadata-only
receipt distinct from private candidate, terminal OK/ABORTED, ACK, native release,
registry retirement and HTTP publication. Physical/runtime startup/release tests
remain required separately.

## Body continuation after the envelope component

Extend the retained original envelope owner/cursor; do not allocate a second
socket consumer after `current_envelope`. Its actual `raw`/canonical outer-header
bytes and original expected pins/context are the starting commitment. Feed those
actual header bytes to `CommittedFrameDigest`, then native body chunks directly
to both that digest and the original `BoundedResultBufferV2`. No full concatenated
outer frame or new body-sized staging array. Take declared length from the checked
header and require exact consumed/committed totals and final signed frame digest.

Retain the original output buffer, independent bytearray custody, parent result
context, challenge/epoch, native operation and expected avatar revision before
body read effects; never follow a substituted job buffer during feed or withdrawal.
Existing native finish/parent snapshot/outcome/cleanup/revision checks remain
independent of envelope authentication. Recheck authority after hash/feed/finish
boundaries and before private candidate adoption. The original first-cause path
must clear any new candidate references before native cleanup clock sampling.

`RemoteResultOwner`, `_CandidateFact` and the native job's remote candidate slots
currently have closed selected-owner contracts. Add an explicitly reviewed fixed
typed bridge for the new signed owner rather than fabricating one of those facts,
assigning its type-incompatible slots, changing native remote phase early or
inferring terminal/publication authority. Preserve one clearable candidate cell
and separately retained original native wipe custody. Partial body/hash progress
must be available to the same cleanup cursor under its earliest frozen budget;
all remote/native release and terminal/ACK/publication gates remain separate.

## Body component checkpoint

`NativeResultBodyOwner` now implements same-original-task body streaming in the
original native buffer, signed full-frame/body hashes, independent native result2/
parent/revision validation and one private candidate. Original stream/hash
allocation is independently retained; exact first-cause discard precedes cleanup
sampling. Held wait/progress/custody checks repeat after native callbacks, and
historical cancellation release requires original Task done+cancelled. See
[body evidence](../../docs/research/presentation-signed-result-body-2026-11-06.md).

Native result adoption/token/RESULT_VALIDATED and result notification are still
closed. The new job hook is discard-only; no existing selected-owner candidate
fact or terminal receipt is fabricated. Body validation does not authorize image
emission or prove native DRAIN/PRE_EMIT/resource/terminal release. Cooperative
signed cleanup-cursor and production continuation remain separate work.

## Private native adoption component

The signed body owner retains a dedicated original remote slot before native
initialization; it never occupies the legacy `RemoteResultOwner` slots. A one-shot
original-task `adopt` transition rechecks the validated candidate and independent
adoption allocation immediately before installing the original job result/token
and `RESULT_VALIDATED`. No callback follows that installation. A duplicate or
wrong-task call cannot consume another transition.

`current_adopted` uses its separate fixed native `RESULT_VALIDATED` tail, current
role material, original socket identity and cause-free budget. It never temporarily
resets phase or accepts a phase selector. It uses the held immutable candidate
fact after cryptographic callbacks, then repeats original candidate/token/custody
joins after the final native descriptor boundary. Admitted failure withdraws both
the private candidate and original job result/token with payload-free refusal;
first-cause withdrawal remains ahead of cleanup clock sampling.

This is private adoption only. The public readiness method still recognizes only
the selected legacy owner; signed notification needs an explicitly reviewed caller
contract. The original signed work task still parks in production after GO. No
terminal, ACK, native release or HTTP/image delivery follows from adoption.

## Original-caller notification component

The signed body owner now has one original-work publisher for the actual native
result Future and a separate fixed original-caller currentness path. Retained
body/candidate/adoption metadata grants no authority by itself. Original-work
gates remain original-work-only; the native result_ready signed branch requires
original caller/current role, fixed RESULT_VALIDATED custody, actual notice
allocation and adopted result. Legacy selected owners remain separate.

Future/scheduler dispatch is rechecked after final native callbacks and before
publishing only readiness. Partial native scheduling failure may leave the Future
done; withdrawn notice/token/candidate still force caller refusal, with consumed
attempt and no automatic replay. First cause withdraws the cleanup result token
as well as native/private output. See [notification evidence](../../docs/research/presentation-signed-result-notification-2026-11-06.md).

Production reader composition and cooperative signed cleanup/terminal/ACK remain
open. No image bytes or release authority follow from a readiness Boolean.

## First-cause signed progress capture prerequisite

The read gate now records the actual signed framing/body/hash allocation and
original wait scope/Future/registration metadata before native poisoning. The
frozen inspector is data-only: it proves no live wait retirement, quiescence,
transfer, clock allowance or remote credit. The signed request branch deliberately
returns False, preserving original Task cancellation until current typed
cooperative continuation is qualified. Bad signed metadata cannot select a legacy
unsigned reader. Bounded envelope metadata may be retained; image body bytes are
not copied and original native output is still withdrawn before cleanup sampling.
See [capture evidence](../../docs/research/presentation-signed-cleanup-capture-2026-11-06.md).

The next transition must correlate actual native cause wake/registration retirement
with this held original progress, not consume the snapshot as an IO grant. Same
Task/socket/framing/hash offsets and the earliest existing cleanup ceiling must
survive. No new reader, phase reset, timer renewal or fabricated retirement fact.

## Actual registered-wake retirement prerequisite

The native wait now supplies a retained typed receipt after its own registered
interest actually retires in response to its original wake. Pre-await identities
and original uncancelled actor are resealed after final metadata guards. An early
no-registration wake remains generic/no receipt; Task cancellation is separate.
The receipt proves historical local stop only and cannot authorize current FD/
role/budget/IO or cleanup transfer. Correlate it with this original signed cursor's
held wait progress and actual native cause, then independently qualify current
custody/write quiescence/minimum budget. Signed request stays disabled until that
transition is qualified. See [wake evidence](../../docs/research/presentation-wake-retirement-2026-11-06.md).

## Signed body original native-cause correlation

The body wait now holds and listens to its actual original cleanup cause Future.
Actual registered wake retirement is matched to the held body/wait scope/Future/
binding/handle/counters/hash allocation and actual original signed capture after
first-cause withdrawal. Current and historical checks are separate: original
uncancelled actor before storing, actual original task done/not-cancelled before
local retirement. Generic/copied/subclassed signals or waiter/counter drift cannot
provide known stop. Genuine external task cancellation remains distinct and binds
this same held cause. See [body cause evidence](../../docs/research/presentation-body-cause-wake-2026-11-06.md).

This is local stop only. Signed request remains disabled and CANCEL still requires
whole work join/current authority; no concurrent read/transfer/terminal permission
follows. Envelope cause wiring and current same-cursor minimum-budget continuation
remain open. Production composition is unchanged.

### Envelope pre-await cancellation binding — November 6, 2026

A payload-free original wait hold now binds envelope scope, waiter, native scope,
Future, deadline and counters through cancellation and historical release. Paired
Future-alias/receipt substitution after immediate wait checks is refused. This
prepares, but does not enable, envelope native-cause wake or signed cooperative
cleanup. Existing Task cancellation and whole-work-join requirements remain.

### Envelope native-cause local stop — November 6, 2026

Original envelope waits now bind the actual cleanup cause and exact native wake
retirement to the frozen signed capture and original pre-await cursor. A distinct
no-image-body envelope stop receipt separates original uncancelled Task currentness
from historical completed-task revalidation. Generic/copied/subclassed wake and
metadata drift retain unknown debt; historical refusal is sticky unknown. External
Task cancellation stays separate. Signed cooperative transfer remains disabled;
CANCEL still requires its existing whole-work join and current role/budget checks.
No terminal/ACK/publication/native release follows from local stop.

### Signed discard data continuation — November 6, 2026

`SignedResultDiscard` continues exact partial signed RESULT framing and bounded
body hashing without retaining image bytes. A supplied partial digest is reused
by identity, never copied/replayed; runtime owner/allocation proof remains separate.
It validates pinned commitment/header/full hash, refuses overread/scanning/restart
and clears input aliases on stable refusal. This grants no socket/actor/budget,
read transfer, terminal/ACK/native release or publication authority. Integrate only
through distinct signed reservation and original-work read-ready admission.

### Disabled signed reservation preflight — November 6, 2026

The original registered envelope/partial-body wait can now yield a one-attempt
preflight record tied to frozen capture/cause, actual write-quiescence, current
retained role and original cleanup budget. Post-callback structural/counter/native
custody seals refuse drift. It is retained DATA only: signed gate.request STILL
RETURNS FALSE and external Task cancellation remains. No read-ready notice,
read/CANCEL/ACK authority, release or publication follows. Separate original-work
admission/notice and full same-task continuation remain prerequisites.

### Signed original-work stop notice — November 6, 2026

A distinct one-shot notice now retains actual native Future/fact allocations and
correlates original envelope/body wake retirement under original work actor,
current retained role and earliest cleanup budget. Partial initialization, paired
alias substitution, final-clock revocation and ambiguous notification retain
unknown debt/no retry. It has no consumer or signer: signed gate.request remains
False and normal external Task cancellation remains. Original-cleanup current
notice validation, concurrent-CANCEL authority and same-reader drain/terminal/ACK
still require separate qualification. Future DATA is no I/O or release permission.

### Fixed cleanup-side current stop DATA — November 6, 2026

The original cleanup actor can now validate an actually delivered signed stop
notice against the original live uncancelled reader, allocation, role and earliest
budget. Root bounds a wait on the actual retained notice/work pair, with dispatch
checks AFTER clock callbacks and held-identity rechecks after await. Wrong sender/
completed-work queries refuse; currentness drift retains unknown debt. This is
stop DATA only: signed request remains False, read-admission/concurrent-CANCEL
authority is absent, and original work-join/signing gates stay unchanged.

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

## One-shot original-parser consumption — November 7, 2026

`NativeCleanupRead.consume_pending()` now feeds one actual pending allocation
on its original work actor into the SAME authentication parser or original body
digest. A distinct attempt allocation is retained before the first currentness
boundary; failure consumes the attempt even if no feed occurred. An independent
parser/count origin cell precedes feed/hash effects. Body expected progress uses
a pinned native hash copy without replacing the actual original stream/hash.
The actual after-state is retained before native callbacks and joined to fixed
role/actor/original budget/socket checks. Only then are pending aliases withdrawn.
The fixed cleanup observer recognizes that same progress. Old stopped/IDLE/pending
APIs do not revive. Work exit still records UNKNOWN because full drain is unfinished.

Actual private fixtures cover received8-byte auth-prefix consumption and the
SAME original digest13->16 for a3-byte body tail, with no image accumulator or
candidate restoration. Wrong actor/duplicate, initial boundary failure with
method restoration, partial feed, role retirement, coherent parser buffer copy,
foreign count, post-clock progress receipt copy/socket mode, and actual post-hash
lost acknowledgement refuse without replay; observed counts remain retained.
Independent read-only review found and required the pre-boundary attempt latch;
that repair and causal were accepted. No reader task/interest, new budget,
signing, frame/terminal/ACK/native release or production gate is granted.

Repeated native reads, record-boundary dispatch/auth completion, full drain,
concurrent CANCEL, terminal/ACK and phone character-image delivery remain open.
Exact affected transport regression:1,940 passed,1 skipped in168.05s. Full lint,
plugin surface and whitespace checks pass. Eight focused header consumption cases
and two body cases overlap this run. An isolated private basetemp avoids unrelated
pytest garbage cleanup; no existing temporary evidence was manually deleted.
The initial header fixture misclassified the new successful consumed state; that
expectation was corrected. Review required the early attempt-latch repair and its
first-boundary failure/restoration causal. No authority guard was relaxed.
Earlier broad broker failures and the sender-destination incident remain unresolved;
this green run does not establish their causes or certify full transport release.
No build, install, live host/device, grant/provider or deployment change occurred.

## Monotonic original-reader continuation — November 7, 2026

`NativeCleanupRead.read_and_consume_next()` now performs another exact-needed
nonblocking receive and same-parser feed on the original socket/task. Original
one-shot flags are never reset. One retained step plus cumulative received/parsed
counts replaces only a sealed committed predecessor; no linked receipt journal,
new reader, selector interest or cleanup budget exists. Actual return/count/pending
custody precedes postchecks; parser/hash progress precedes final currentness.
Only a sealed commit permits another ordinal. Needed0 stops at a record boundary.
EAGAIN, EOF, lost acknowledgement or post-native drift stays UNKNOWN with no retry.

Private causal fixtures reach the end of a real signed auth record without reading
the following outer header, perform two short reads with increasing ordinals and
reclaim the prior step without waiting for cyclic GC, reject foreign progress
before getters, and retain actual counts on foreign post-recv allocation without
calling its indexing hook. Original body continuation advances the SAME digest
13->16->19 while old body committed13 and the wiped image accumulator stay fixed.
Independent read-only review required two earlier type fences; both are repaired.
Predecessor private self-cells retire only AFTER the successor commit is sealed.

Exact expanded regression:1,947 passed,1 skipped in171.15s; full lint, plugin surface
and whitespace pass. Six header causals and one body causal overlap this result.
Earlier fixture faults (wrong observer scheduling, insufficient queued auth bytes,
shared suffix classification and stale historical release expectation) are retained;
production guards were not relaxed. EAGAIN waiting/registration, authentication
verification and phase dispatch, full drain, concurrent CANCEL, terminal/ACK/native
release and production/physical character-image delivery remain open. Earlier broad
broker failure causes and the native sender-destination incident remain unresolved.
No app build/install, live host/device, grant/provider or deployment change occurred.

## Original-reader authentication completion — November 7, 2026

`NativeCleanupRead.finish_authentication()` now verifies the completed original
bounded authentication record exactly once. Pure completed-parser admission and
an independently retained attempt precede native/currentness/signature boundaries.
The actual returned commitment is retained before callbacks and joined to the
actual raw record, original parser/pins/context, retained sequence and canonical
frame values. Finished-parser state is admitted only through that returned attempt,
never from a finished flag alone. Role, actor, original budget, socket and actual
allocation aliases reseal before an authentication receipt; the fixed cleanup
observer recognizes the same state. Cumulative post-cause counts are captured
before crypto and retained unchanged; captured prefix bytes are not counted again.

Ten private causal cases cover one positive RESULT record, invalid signature,
actual verification followed by lost acknowledgement or role retirement, post-clock
checked-result copy, initial native failure/restoration, final verifier foreign
ledger/count/scope substitutions, and inconsistent returned commitment values.
All refuse without replay or foreign getter/equality access. Review required the
post-crypto count/ledger fence; held primitive counts/local immutable scope and
new fault tests repair it. Failure wipes only the captured original auth buffer.

Independent read-only review accepted source/repairs. Exact affected regression:
1,957 passed,1 skipped in169.79s; full lint, surface and whitespace pass. The ten
focused cases passed in3.19s and overlap that run. Functional source hashes remain
unchanged through execution. Authentication phase is DATA, not permission to read
or accept a frame. Header/phase transition, direct ABORTED eligibility, full frame
digest, waiting after EAGAIN, concurrent CANCEL, terminal/ACK/native release and
production/physical image delivery remain open. Earlier broker failure causes and
sender-destination incident remain unresolved. No app build/install, live host,
device, grant/provider or deployment change occurred.

## Bounded committed-frame discard parser — November 7, 2026

`presentation_credential_frame_discard.py` now parses one bounded outer-header
prefix/header and its exact committed body without replaying authentication bytes.
`CommittedFrameDiscard` is consistency DATA only: constructing a commitment is not
signature provenance or an I/O permit. The actual header and digest allocation
are anchored before digest initialization; the original hash remains joined to
that header/binding. RESULT body bytes are hashed/discarded without an image
accumulator. Only TERMINAL metadata, at most4096 bytes, is retained privately; its
captured bytes are independently rehashed with the header and joined to the final
stream digest before transfer to a bounded data fact. No ABORTED claim is accepted.

Exact-needed chunks prevent overread/terminal scanning. Hash mismatch, copied
digest, partial initialization, lost hash acknowledgement, foreign header/hash
allocation, changed return values and metadata changed after hashing fail closed,
wipe only owned buffers and do not retry. DiscardedFrame is not lifecycle, native
acceptance, ACK or release proof. Native integration must hold the actual original
AuthReceipt, establish the allowed grammar transition and bind the actual parser
allocation to the same reader/task/socket before any I/O. That wiring remains open.

Independent read-only review accepted source and hardening. Exact expanded affected
regression:1,983 passed,1 skipped in173.26s; full lint, plugin surface and whitespace
pass. Twenty-five focused data cases passed in0.15s and overlap the expanded run;
RESULT chunking and TERMINAL0/1/2 include maximum terminal metadata. Current
functional source hashes match execution. Original partial-body digest integration,
header/phase native read ownership, EAGAIN waiting, terminal acceptance, CANCEL/ACK/
native release and production/physical image delivery remain unfinished. Earlier
broker failure causes and sender-destination incident remain unresolved. No build,
install, live host/device, grant/provider or deployment change occurred.

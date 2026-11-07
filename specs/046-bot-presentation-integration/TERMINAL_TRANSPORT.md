# Joined terminal transport: remaining lifecycle contract

This is the implementation contract for full character delivery, not a reduced
feature or a qualification receipt. The envelope codec/transcript alone enable
no terminal dispatch, ACK permission, image emission or registry/native release.

## Current concrete prerequisites

The gateway's reviewed post-GO cleanup retains its original reader while sending
one CANCEL. Its [pre-READY extension](PRE_READY_CLEANUP.md) has bounded source
review, local regression and exact-source CI; it is integrated through PR113.
The broker now publishes a typed cancellation-adoption notice and retains the
same controller/cumulative cursor in a bounded park after CANCEL. Service cleanup
waits for that notice rather than Task completion; local FD/clock retirement still
requires stopping and joining the original Task. This is the
[controller continuation prerequisite](BROKER_CONTINUATION.md), not ACK parsing.
Neither side may simply append a new reader for aborted TERMINAL/ACK. Do not lose partial framing,
create a competing reader or treat full-task join as proof of a different fact.
The independently qualified producer/receiver factory is also not implemented;
StartupEnrollment generation, clock qualification, same UID and decoded fields
cannot replace it. Native read service/PRE_EMIT and all ownership planes remain
required before public character routes.

The current startup direction is [local role credentials](CREDENTIAL_ADMISSION.md).
The [runtime issuer proposal](RUNTIME_ISSUER.md) is historical Mach research,
not an alternative admission route. Signed BEGIN/READY/GO and pre/post-READY CANCEL
have bounded source integration; production installation/startup remains open.
The [original pre-READY read-retirement and BEGIN-derived cancellation contract](SIGNED_PRE_READY_CLEANUP.md)
has source components/route/correlation and known-no-IO refusal local cleanup.
None confers remote terminal/ACK or publication authority. The fixed signed
worker relay and signing/result-writer components below remain separate from
production composition and terminal qualification.

The [local handoff freeze](LOCAL_HANDOFF_FREEZE.md) is integrated as source
797dbbc through PR114 with exact-source green CI42129488493. It supplies immutable
DATA only; qualified runtime custody and IO permission remain separate gates.

## Signed worker relay prerequisite

The current credential controller records GO; the original-service current GO
validator and fixed native relay component are implemented/reviewed separately.
Production dispatch is not enabled. Integrate the reviewed
[fixed native relay contract](SIGNED_GO_RELAY.md) with actual signed RESULT
transport before claiming normal OK TERMINAL. Keep terminal-write/ACK and
production startup qualification separate; never replace the native control
pipe's final current/FD/time checks with a signature-only allowance.

## Signed RESULT writer checkpoint

The original-service immutable RESULT producer and counted signed writer now have
bounded source components. The writer uses a fixed historical READY write-slot
handoff, final callback-free current authority checks, actual native send counts,
one frozen-budget controller cancellation and payload withdrawal. Full local write
is not remote receipt or terminal/native release. See
[writer evidence](../../docs/research/presentation-signed-result-writer-2026-11-06.md).
Production dispatch, original gateway signed RESULT cursor, terminal/ACK and
installed-runtime/native publication remain open; no unsigned fallback is enabled.

## Envelope and earliest first cause

Freeze canonical STARTED_READER_HANDOFF bytes with a closed historical claim and
nullable sender cleanup stamp. ABORTED and any already-caused sender require the
actual original minimum stamp, including a historical OK captured before a later
cause. Actual sender must derive it from the same retained CancellationBudget,
not caller arithmetic. Original binding/challenge/epoch/input/source/domain/
installation/deadline must match qualified original custody at both ends.

The bounded envelope receive uses only the original known local ceiling; the
sender stamp is not known until those bounded bytes are decoded. Validate common
clock/domain and current receiver time before inheritance. Adopt and recheck only
min(existing end, sender end) before any SUBSEQUENT cleanup/resource/ACK IO. An
already-expired sender end yields UNKNOWN; receiving it cannot retroactively prove
timely cleanup/closure. Future-dated stamps cannot renew time. Null normal data is not a cleanup allowance; a local
cause still freezes the original budget and later events can only shorten it.
ACK correlation hashes exact frozen envelope bytes, including the sender stamp.
No retransmission, modified envelope or appended frame after a torn write.

## Gateway: retain the original reader into cleanup-only mode

The [write-quiescence prerequisite](WRITE_QUIESCENCE.md) now composes with the
reviewed [post-GO cleanup reader](CLEANUP_READER.md) for one CANCEL while the
original RESULT task drains. The [pre-READY source candidate](PRE_READY_CLEANUP.md)
extends that coupling before GO and passes exact-source CI42124526459. ACK and
terminal acceptance remain unimplemented, and this contract is not deployment proof.
Keep the original retained work Task as the sole stream reader; existing cleanup
Task is the sole planned CANCEL/ACK writer (only CANCEL is implemented).
Replacing whole-task-join before sending requires the exact one-use
write-quiescence barrier owned by the original work allocation/channel/budget. It must establish completed BEGIN, no pending
client write, and either no GO attempt or the original completed GO-write fact.
An IO flag alone is not quiescence. Allocate/retain partial Future/Task/barrier
ownership before effects, with existing initializer failure and cancellation rules.

On first cause, retire publication and ordinary work immediately. No work clock,
GO, fresh result candidate or reauthentication success can revive the operation.
Original work transitions cooperatively to cleanup-only reading only after exact
write quiescence. The cleanup writer may then send CANCEL while that same Task
continues the one retained read cursor. A torn/uncertain BEGIN/GO never receives
an appended CANCEL or an invented quiescence fact; retain UNKNOWN debt instead.
Foreign scope/task/channel/generation or lost barrier acknowledgement cannot
transfer the cursor or permission to another operation.

The selected-v2 pre-result and normal RESULT readers now retain framing progress
through their reviewed readiness/cursor integrations; RESULT also retains its
original digest. The post-GO RESULT cursor now continues as bounded discard
under its original cleanup scope. The integrated pre-READY extension retains
its exact original cursor; it never resets offsets or starts a replacement reader.
Partial RESULT uses the existing credited accumulator; after revocation it is
bounded discard, never a new candidate. TERMINAL has the bounded envelope ceiling.
All active IO timeouts must shorten to the same earliest cleanup end before later
IO, using retained original timeout ownership and a reviewed wake/reschedule
boundary. A pending original work timeout cannot leave a read running past the
cleanup end. If quiescence/rescheduling/IO join is uncertain, keep UNKNOWN rather
than opening another reader or creating a new timer/allowance.

## Broker: continue the same control cursor after CANCEL

Retain a separate cancellation-notification Future before task effects. After
header-first retirement and complete exact CANCEL-window adoption, notify the
service through that original fact, clear only the consumed cursor bytes and
continue the SAME controller Task toward ACK. No replacement ACK reader/task.
The service's original Task owns local reader cleanup and one-use terminal send.
It may send only actual retained producer facts after known non-torn prior writes,
under remaining original work time or the earliest cleanup interval.

The cancellation-notice/park portion above is implemented; no park wake currently
grants further I/O. ACK parsing remains unimplemented and must be bounded and tied to the exact terminal-write completion fact,
original authenticated gateway/boot/channel and separately qualified receiver
permission. A syntactically matching digest is not permission. Lost/partial early
ACK, timeout, drift and uncertainty retain journal debt. Journal retirement never
drops native headers/job credits/policy ownership. After ACK/control completion,
join original Tasks and observe distinct local socket/clock closure; EOF alone
closes no other ownership plane.

## Required qualification and causal checks

Review whole coupling before enabling dispatch: normal/abort preREADY, postREADY,
partial RESULT and postRESULT; CANCEL during read/write and after frozen terminal;
torn/lost terminal/ACK; expired/earlier/future stamps and duplicate causes; partial
initialization, write-quiescence/timeout/cursor drift; no concurrent readers;
wrong instance/profile/device/boot/generation and revocation. Prove no callbacks
or cleanup effects reach another operation. Keep original payloads bounded and
wipe all owned aliases without touching replacements. Qualify actual producer
runtime/reaper/manager and native authority separately from synthetic fixtures.

Only joined accepted remote closure may feed a distinct native completion path.
Fresh PRE_EMIT, parent/native DRAIN and credential retirement remain mandatory.
V2 STATUS needs a separate boot-bound journal-only lookup/ACK contract and must
never renew expired work, replay a result or grant image access.

## Signed image/private candidate checkpoint — November 6, 2026

The original-task envelope/body components now verify actual signed image bytes
and independent native result2/parent/revision data in the original native buffer,
with a private candidate and first-cause withdrawal hook. Private native adoption
and original-caller readiness are now qualified source components. Production
reader composition and signed terminal/ACK remain closed; no terminal or release
credit follows from readiness. See
[body evidence](../../docs/research/presentation-signed-result-body-2026-11-06.md).
The cancelled-read retirement fact is local and payload-free, not a cooperative
terminal cursor, native resource release or ACK. Integrate the same original work
cursor's discard/terminal continuation before normal OK/ABORTED terminal claims;
never revive a cancelled Task or attach a replacement reader to complete cleanup.

Original-caller readiness now has separate fixed authority from original-work
publishing; it does not substitute for terminal claim/ACK. Ambiguous native Future
scheduling consumes its attempt and withdraws output even if the Future became
done. See [notification evidence](../../docs/research/presentation-signed-result-notification-2026-11-06.md).

The signed cleanup progress capture is now a frozen-data source prerequisite, not
a cleanup read transfer. It preserves original framing/hash/wait identities before
poisoning without copying an image body; output withdrawal remains ahead of clock
sampling. Signed request stays disabled until the same-task wake/retirement/current
custody/minimum-budget continuation is qualified. Terminal/ACK remain separate.
See [capture evidence](../../docs/research/presentation-signed-cleanup-capture-2026-11-06.md).

The actual registered-wake retirement receipt is now a source prerequisite. It
records only original local interest retirement; no current cleanup/terminal/ACK
permission follows. Correlation to the actual signed cursor/native cause and
current minimum-budget transfer remains open. See [wake evidence](../../docs/research/presentation-wake-retirement-2026-11-06.md).

Signed body cause wiring now correlates actual registered wake retirement to the
original signed progress and native cause, with original uncancelled actor and
separate historical completion checks. This supplies known local stop only.
Signed transfer remains disabled and CANCEL still needs whole-work join/current
authority. Envelope cause/cooperative reading/terminal/ACK remain open. See
[body cause evidence](../../docs/research/presentation-body-cause-wake-2026-11-06.md).

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

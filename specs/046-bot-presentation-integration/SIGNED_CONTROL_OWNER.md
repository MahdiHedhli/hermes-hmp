# Signed GO/CANCEL handoff before credential resource startup

Status: partial source integration; full signed control/resource lifecycle is NOT implemented. Legacy raw
control and result paths must refuse a credential-attached channel. Resource/READY
startup remains closed until the concrete signed control receiver is retained.
This changes no minimum-version policy and disables no legacy unsigned channel.

## Fixed original entry and task ownership

The planned source entry is `BrokerCancellationOwner.retain_credential(queued_owner)`.
It takes only the exact original `CredentialQueuedOwner`, never a caller channel,
registry, packet, key, phase, digest or enable flag. On its original service task,
join the original connection/shared registry/ticket/receipt/budget/grammar/channel
and completed BEGIN reader; require successful adoption and the current queued
native phase. Retain the control owner before initialization effects. Preserve
any partial owner/task and the consumed original attempt on failure.

Keep `retain` and direct legacy `__init__` closed to credential channels. A signed
entry must use an exact separate retained credential context, not bypass their
refusal by temporarily clearing handshake fields or setting a boolean. Its
context retains the original startup role material, installed generation, native
clock, signed input/scope/transcript and work end from the original owners.

Use the existing single `_TaskSlot`/`_TaskAllocation` and fixed reader coroutine.
Bind credential context to that actual initialized Task/coroutine/slot before
`_initialized` is published. Default native loop/no eager/custom factory remains
required. Partial initialization leaves `_failed` and no read eligibility. Do not
relax the handshake task guard. Distinguish the original service caller's current
checks, the actual controller reader allocation and local owned cleanup; no
other task/name/copied allocation may borrow either role.

## One cursor and exact signed phase

The same original controller cursor reads a bounded HBA1 record before each HBR1
control. Do not add a second reader/parser Task. Before body reads, verify pinned
gateway/broker key identities, current role generation and all original context:
iid/listener/channel/boots/transcript/operation, input/scope hashes, exact original
signed work end, phase/direction and the existing grammar sequence. No independent
renewable auth counter: GO uses client sequence 1; CANCEL uses the actual remaining
client sequence before or after GO, at most one GO and one CANCEL.

Check the bounded HBR1-v2 header against that retained commitment before its body,
then hash/compare the entire actual header/body on the original cursor. GO has no
body; CANCEL has the existing exact 16-byte CancellationWindow. Stage signed
metadata only; constructing a consistency object cannot mint a GO/CANCEL receipt.
Mint the existing native receipt/future only after original complete-read,
authentication/scope/clock/budget/grammar checks all succeed. Typed signature/read
context must remain joined to those actual receipt objects at later service use.
No unsigned, v1, copied-frame or caller-data fallback is allowed.

The original controller bound becomes at most two signed records (2*2048 bytes)
plus its existing two HBR1 control frames (2*(8+1024+16)): 6,192 wire bytes. This
must remain within the existing whole-channel 2,050,288 and cleanup-subset 13,384
limits. Counters are lifetime counts, not memory/latency guarantees. Keep original
consumed offsets, pending read intent and uncertain readiness registration debt.
On terminal refusal clear transient payload aliases/context and wipe only the
captured original private buffer; never follow a substituted buffer for cleanup.

## Cancellation is not a new budget

An unauthenticated HBA1 prefix or unverified signed claim cannot be treated as a
remote CANCEL cause or adopt a remote window. Work expiry/local Task cancellation
may still independently freeze qualified local cleanup on the original budget.
Only authenticated original-scope control and a completely validated native
window may use the existing remote receive/adoption operation. Preserve the
first cause and earliest end, including work expiry or an earlier local cause;
never add a handshake timeout, restart a cleanup interval or retry ambiguous IO.
An authenticated CANCEL intent may conservatively stop work before complete body
validation, but cannot adopt a body-supplied window or mint a completed receipt.

Current key/config/source generation retirement stops remote authentication and
phase effects, including cleanup messages. It must not prevent solely local
cleanup of already owned resources under the original frozen budget. Keep those
checks separate; `reader=False` cleanup is not permission for network writes.

## Resource/READY and later work stay gated

Before any credential `start_resources`, retain this actual signed controller,
its original Task and current context. A legacy controller object or future is
insufficient. Preserve queue capacity checks and original one-attempt resource
intent. READY must be a fixed broker signature produced from the actual original
resource/input-staged facts, not from queue admission alone. Actual native GO
requires both the authenticated complete GO receipt and existing fresh phase/
resource/native checks. RESULT/TERMINAL/ACK/direct writers and native publication
must independently join their own original facts. No generic sign API or premature
opening of `_credential_work_ready` follows from this contract.

## Required causal acceptance

Cover successful GO, CANCEL-before-GO and CANCEL-after-GO on the actual original
allocation/cursor; original service/registry/input/budget/grammar joins; wrong task,
instance/profile/operation/transcript/sequence and revoked generation; signature,
header/body/hash/window failures; unauthenticated CANCEL-prefix no adoption;
partial auth/header/body and ambiguous readiness/cancellation; first-cause/earliest
budget conservation, work-end expiry and key retirement during work/cleanup;
foreign getter/index/comparison/buffer tripwires; no task/owner claim or budget/
grammar mutation on known legacy-mode refusal; no duplicate receipt, retry or
resource/GO effect after refusal. Keep synthetic/native/device/release evidence
and local descriptor cleanup distinct from actual registry/native debt release.

## Implemented preparation checkpoint

`prepare_credential(queued_owner)` now retains the original key/context and actual
controller allocation before publication. It is a no-IO preparation entry, not
the planned working `retain_credential` reader. Its actual Task stops explicitly
and every reader/work guard stays hard-closed. Original constructor/refusal and
local cleanup boundaries remain separate. Root affected regression: 1,120 passed,
one skipped; independent source/test review accepted only this preparation slice.
See [evidence and limits](../../docs/research/presentation-prepared-control-binding-2026-11-06.md).

## Reader-material checkpoint

The actual prepared controller Task now checks original role material/current
service/socket/registry references without borrowing creator-only guards. It is
material-only; signed phase/deadline/read-cursor checks remain unimplemented, and
the Task still hard-stops before IO/receipts. Root affected regression: 1,123
passed, one skipped; independent read-only review accepted this limited slice.
See [evidence and limits](../../docs/research/presentation-control-reader-material-2026-11-06.md).

## First-frame cursor checkpoint

`stage_credential_control(queued_owner)` now reads and authenticates one bounded
first-control GO/CANCEL sequence1 on the original controller Task/socket cursor.
It checks exact signed context and complete HBR1 frame, validates CANCEL encoding
without adopting it, and explicitly stops before native receipts/grammar/budget
mutation. `prepare_credential` alone remains no-IO; the working `retain_credential`
entry, after-GO CANCEL and cleanup/resource/READY lifecycle are still unimplemented.
See [first-frame evidence and limits](../../docs/research/presentation-signed-control-first-frame-2026-11-06.md).

## Native pre-GO CANCEL checkpoint

`retain_credential_cancel(queued_owner)` now joins the actual original completed
signed CANCELseq1 to native grammar/budget/receipt and the existing original Task
park/local stop. It seals original phase/end across callbacks before effects.
The original notification Future is not sufficient on later owner failure, and
ordinary `cancel_receipt`/service `_v2_control` remain closed. Dedicated service
receipt validation, signed GO, after-GO/cleanup-time reads and resource/READY
startup remain open. See [bounded evidence](../../docs/research/presentation-signed-pre-go-cancel-2026-11-06.md).

## Dedicated service cancellation consumer checkpoint

The credential branch in service `_v2_control` now uses the exact original creator
and `CredentialCancelAdoption.wait_notice`, with one attempt latched before native
checks, original Task/Future/receipt seals across await, complete signed-frame
revalidation, actual native park verification and original cleanup time. Generic
work guards and ordinary `cancel_receipt` remain closed. Wrong caller/spine cannot
consume the original attempt; late authority failure cannot retry after restoration.
See [evidence and limits](../../docs/research/presentation-signed-cancel-service-consumer-2026-11-06.md).

## GO/read and next-CANCEL checkpoint

`stage_credential_go_control` retains a typed original GO proof, requires existing
READY grammar before native read/grammar receipt, and continues the SAME actual
Task/cursor for CANCELseq2. Native cancellation/service validation also retains
the original GO proof. Total control lifetime bytes remain bounded by6,192.
Reads remain under original work time; cleanup-time control, signed READY write,
resource/worker relay and production admission are unimplemented. Unit READY is
an explicit modeled grammar fact, not resource or signed transport evidence.
See [evidence and limits](../../docs/research/presentation-signed-go-control-chain-2026-11-06.md).

## Cleanup-time control checkpoint

The original signed cursor now crosses a known work deadline into the SAME native
earlier cleanup budget. It continues only after exact original readiness retirement
or known no-registration expiry plus qualified clock confirmation. Initialization
and guard errors cannot masquerade as wait expiry; unknown debt never retries.
Only authenticated CANCEL may continue, original offsets/targets/buffers remain
unchanged, and remote inheritance cannot extend the first cause. Source receiver
acceptance remains separate from signed READY/resources/worker relay and runtime
startup. See [evidence and limits](../../docs/research/presentation-signed-control-cleanup-time-2026-11-06.md).

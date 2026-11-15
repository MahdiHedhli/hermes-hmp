# Prepared original controller task/key-context handoff

Independent read-only review accepted this bounded preparation slice. The new
source-only `BrokerCancellationOwner.prepare_credential(queued)` derives its
channel/registry/ticket/grammar from the exact original queued owner; it takes
no caller frame, key, phase or enable flag. It retains the control/binding on the
original channel and connection before initialization, then binds the actual
existing `_TaskSlot`/`_TaskAllocation`, original coroutine, loop and creator.
Legacy construction keeps its credential refusal and one-initialization guard.

The shared initializer conserves original native failure custody and partial
Task/Future retention. The binding's creator checks use the original queued
service/native input/key context and reseal original control/queued/task/loop
references after callbacks, before attributes are followed. Allocation checks
independently validate exact control type/reciprocity and the actual native
Task/coroutine/slot/loop; they do not borrow prior constructor checks.

This is explicitly NOT a signed control reader. Its prepared Task raises
`BI1_SIGNED_CONTROL_READER_NOT_IMPLEMENTED` before any bytes, marks the controller
failed, and produces no GO/CANCEL receipt or budget/grammar mutation. All reader
and work guards hard-refuse even before the Task gets CPU. Constructor validation
uses only local cleanup/metadata checks, never work admission. No flag enables the
old unsigned reader. Known partial objects remain retained; no retry, resource/GO
permit or production dispatcher integration is introduced.

Root's affected regression passed **1,120 tests, one skipped**, in 29.73 seconds;
configured repository-wide Ruff passed. The focused adoption/control module
selection passed 64 cases in 5.62 seconds. New actual-task tests prove distinct
creator/reader allocations, exact original key/input context, duplicate refusal,
zero IO/receipts, unchanged grammar/budget, and refusal by service work guards
before scheduling. Creator-final-clock control substitution and reader allocation
substitution trigger no foreign getters. Tests use actual disposable service/
socket/registry ownership with synthetic keys/policy and modeled peer/clock facts.
No reviewer tests/live actions occurred.

Earlier fallback-refusal source `98d6c3b` passed CI720 plugin job128042748864:
8,309 tests, 190 subtests, 33 skips, 18 warnings, 330.33 seconds. Plugin checks
and all Python 3.12–3.14 Unicode jobs passed. That does not qualify this newer
preparation source. Actual `retain_credential` signed GO/CANCEL parsing/receipt
production, credential resource/READY, remaining signed/direct IO, production
startup, native publication, STATUS and physical/release qualification remain
open. No live host/device/permission change or key installation occurred. The
separate earlier destination-custody incident remains unresolved.

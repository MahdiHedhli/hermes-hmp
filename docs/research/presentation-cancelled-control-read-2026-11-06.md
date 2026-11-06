# Known local cancellation of the original control read — November 6, 2026

This slice settles only local socket/readiness ownership after cancellation of
the actual original controller task during its exact positively retired wait.
It grants no authenticated read completion, GO/CANCEL receipt, resource admission,
worker execution, native reservation release, response publication or production
startup. Unknown syscall/readiness ownership and generic failures remain refused.

The readiness wait captures original scope, native Future, wake binding, handle,
handle-argument tuple and absolute cutoff before awaiting. On actual task
cancellation it first retires its exact owned registration. Only positive known
retirement with all held aliases unchanged and native Task.cancelling > 0 produces
a private cancellation subclass carrying a payload-free local retirement fact.
A Future that merely raises CancelledError without actual task cancellation does
not produce that fact. Timeouts and ordinary metadata wakes keep their existing
semantics. Existing callers accept cancellation by subclass; no exact-type caller
assumption was found in the inspected presentation source/tests.

The original control cursor captures a per-frame read-run allocation before IO:
original controller task/coroutine, process/thread/loop, control/binding/connection,
socket, buffer identity and frame index. Its receive loop retains original count,
target and bytes before waiting. It accepts cancellation evidence only from this
exact await's held waiter/scope/Future/cutoff. A correctly typed reconstruction
from an earlier genuinely retired wait on the same task/socket is insufficient.

Cancellation retirement requires no native read intent, no pending bytes, exact
held count/target/buffer correspondence, exact original allocation/context and
positive original readiness retirement. It intentionally does not call a work or
live-key material guard: those guards correctly reject cancelling tasks/retired
keys and remain unchanged. Cleanup checks only original local ownership, never
current permission or a new operation. The original buffer is wiped; immutable
partial bytes and the internal exception/traceback are not retained in the final
fact. Original consumed counts and targets remain. The cursor is failed, not
complete; authenticated completion/phase/receipt fields remain absent. Outward
propagation is ordinary CancelledError. A one-attempt entry guard rejects retries
before failure cleanup can overwrite an earlier retirement or unknown debt.

Historical channel closure additionally requires the exact original native task
is done AND cancelled, retained run/readiness aliases remain joined, original
buffer is empty and read intent/pending bytes are absent. The service checks this
fact before close. Keys may have retired; another task in the same original
process/thread/loop may read historical retirement without acquiring read/work
permission. Separate writer/clock/resource/registry debt is not released by the
fact. Unknown state still prevents aggregate closure, including native read intent,
pending/foreign buffer or count drift, unknown retirement and waiter/Future/wake
substitution. This does not cover arbitrary failure settlement or unstarted tasks.

Root tests include actual nonblocking private sockets and native Task cancellation
at no-byte, partial authentication, signed-authentication, partial-header and
partial-body waits; second-frame cancellation after a modeled READY/GO-read; key
retirement; unknown registration retirement; foreign buffer/count/intent/pending
state; changed wait/wake/Future aliases; a stale earlier retired wait; and fake
Future cancellation with no native task cancellation. Known cases verify actual
socket AND native-clock closure. Unknown cases verify refusal and no auth/native
receipt or resource start. The after-GO fixture models prior READY grammar only;
it is not independently a signed-READY/resource qualification.

Independent source/test review accepted the final narrow slice read-only. The
reviewer ran no tests or native actions. Root's initial baseline readiness/adoption
run passed 186 checks. New fixtures initially missed the creator/control readiness
handoff; explicit original-allocation coordination fixed those fixture errors.
Partial cases then exposed a real retry-state bug: a rejected second run entered
failure cleanup and overwrote known retirement. The one-attempt admission repair
preserves the original outcome. Final targeted read-stop cases: 17 passed. A prior
focused readiness/adoption run passed 205 before the final stale-origin gate/case;
final affected regression: **1,395 passed, one skipped**, 57.38 seconds. Configured
repository-wide Ruff passed. Exact new-source CI remains pending; prior signed
READY source b066cac passed CI744 plugin and Python 3.12/3.13/3.14 Unicode jobs.
The first expanded run had 1,394 passes, one skip and one failure: the new idle
check directly accessed a missing cancel-owner field in an isolated BEGIN-only
channel fixture. It now follows the existing optional-owner pattern: both absent
aliases mean no owner, mismatches refuse, and present owners keep all typed checks.
This adds no work permission. Prior failure is retained as such.

No protocol deadline is extended, no key/material/auth/grant guard is relaxed and
no retry is enabled. Native clock and peer policy remain synthetic qualification
models; sockets, scheduler registrations, tasks and descriptor closure are actual
local test observations. No live host/device/settings, role-key installation,
provider/permission change or mobile build. Full character delivery still needs
production resource admission, actual signed BEGIN/later phase transport, worker
GO relay, startup, native publication, STATUS and physical/release qualification.
The earlier native-destination incident remains unresolved and separate.


## Subsequent CI observation

Exact cancelled-read source 36de774 passed CI746 plugin and Python 3.12/3.13/3.14
Unicode jobs. This qualifies only that source/check scope; later BEGIN transport
and production/device qualification remain separate.

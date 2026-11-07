# Original service consumes signed pre-GO cancellation — November 6, 2026

This source component connects the existing service `_v2_control` to a dedicated
current signed pre-GO cancellation validator. It does not relax generic work,
ordinary `cancel_receipt()`, unsigned fallback or resource/GO admission. No
production dispatcher calls the credential startup path yet.

`CredentialCancelAdoption.wait_notice(spine)` admits only the exact original
service creator Task, loop, spine and retained cancellation owner. Callback-free
scope checks reject wrong-task/wrong-spine calls without consuming the original
attempt. A correctly scoped call latches its one attempt before native/material
checks or awaits. Failure remains sticky; restoring fixture authority cannot
retry the original attempt.

The validator waits on the original native controller Task and notification
Future. Original role material, generation, service/socket/registry/input scope,
Task/Future allocations/methods and the exact minted receipt are resealed after
callbacks and after the wait. It revalidates the original complete signed frame
on the service creator, compares the native CANCEL body against the authenticated
wire frame, and requires the actual native Task to be parked on the original
park Future. It checks remaining time on the original nonrenewing cleanup budget
before returning the exact native cancellation frame. A completed notification
on a failed/stale owner is not usable authority.

Reader and creator checks remain separate fixed wrappers over the same original
scope. Service validation cannot borrow reader IO authority; actual reader IO
still enforces its original controller Task. No second parser Task, copied
receipt/caller permit, renewable auth timer or boolean work-gate bypass is added.

Independent source/test review accepted this bounded slice without execution.
Root focused module: **62 passed**, 5.51 seconds. Affected regression: **1,159 passed, one skipped**, 33.29 seconds;
configured repository-wide lint passed.
Success runs through actual service `_v2_control` and owned local stop. Causals
cover wrong task/spine, late key retirement, foreign Future replacement after
await and at the final native boundary (zero foreign getters), initial authority
drift followed by explicit white-box restoration with no second native wait,
duplicate consumption refusal and reader/creator role isolation. Fixtures use
synthetic key/peer/clock policy with real disposable sockets/native tasks/registry.
No physical-device or production runtime qualification is inferred.

Remaining: signed GO/READY/resources and their actual native receipts, after-GO
and cleanup-time control reads, later fixed signed producers/result/terminal/ACK
IO, production runtime/source/key startup, native publication, STATUS and separate
physical/release qualification. Full character delivery is unavailable. The
separately frozen image candidate/deployment approval and unresolved earlier
native-destination incident remain unchanged. No live host, device, mobile build,
permission, provider or installed key changed.

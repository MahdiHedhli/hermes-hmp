# Owned socket-write readiness — November 6, 2026

`SelectorWriteReadiness` is the notification prerequisite for the fixed signed
READY sender. It does not send bytes, create a worker task, advance READY grammar,
start resources, relay GO, authenticate a new peer or activate production startup.
The existing signed READY producer remains signing-only.

Direction is selected by exact concrete class and retained in immutable original
scope. The write owner uses the actual native writer slot; the original read
owner continues to use the read slot. Neither accepts an arbitrary subclass or a
caller direction flag. Class/scope drift refuses before selector effects. Native
writer dispatch is fenced before registration/removal; the read owner does not
acquire authority over an unrelated writer method.

Both directions retain original socket/FD identity, concrete selector/backend,
process/thread, task, Future, callback/token/handle and absolute wait deadline.
Registration intent precedes the native add. A known owned slot may be retired;
unknown acquisition or retirement remains debt. Retirement must preserve the
opposite subscription, including a legitimately replaced opposite owner while
waiting. A foreign same-direction registration is never replaced or removed.
Notification is only Future(None), with no IO or application data. Wake, expiry,
external task cancellation and unknown state remain distinct; no deadline renewal
or ambiguous retry follows from this helper.

Independent read-only review found a shared initializer reset flaw during this
change. Reinitializing a retained owner could erase original registration/Future
debt. Initialization now rejects any existing instance state before resetting
fields or allocating another Future, including partially initialized owners.
Read/write causals cover same-task reentry during native registration and verify
all original fields, registration and opposite slot survive. The reviewer accepted
the repair without executing tests or native actions.

Focused readiness tests: **73 passed**, 0.36 seconds. Configured repository-wide
Ruff passed. Broader joined checks: **815 passed**, 45.00 seconds. An earlier run
before the initializer repair produced **722 passes and one failure** in
`test_original_service_consumes_only_current_signed_cancel` for
`signed_control_native_service_wrong_spine-2`: the post-wait creator validator
refused because its final control-state predicate was false. That run is retained
as a failure; no root cause or causal fix is claimed for it, and the later pass
does not erase it. Protocol deadlines were not extended and the fixture was not
changed in this slice. Final expanded affected regression: **1,358 passed, one skipped**, 53.57 seconds.
Exact-source CI remains separate and pending.

Remaining sender work must retain the producer's original resource/input/key
facts, one fixed write/grammar intent and native syscall offsets. An uncertain
send must never be retried as a new send. The controller must join the original
write completion under the original deadline before using READY to authorize GO;
peer readability alone cannot substitute for that local completion. Production
resource admission, later signed IO, startup, native publication, STATUS and
physical/release qualification remain incomplete. No live host/device/settings,
permissions, providers, role keys or installed app changed.

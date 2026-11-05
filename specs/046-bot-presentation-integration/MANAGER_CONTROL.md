# Instrumented manager control

Candidate `tools/compat/presentation_manager_control_fixture.py` reuses BR8a's
fixed private reader/broker literals and the separately reviewed retained Darwin
exit observer. It is distinct from the actual-reader experiment. Independent
source/negative-test review must precede any invocation.

One explicit non-root Darwin invocation creates at most two random new GUI-user
labels, first new-session then shared-group. Each case independently verifies
exact-label absence, private installation hashes, immutable launch policy,
kernel UID/PID/nonce, retained broker-child relationship and group geometry. The
controller registers both kernel observers before the authenticated connection
stimulus. No existing job, native profile, real input, GO or numeric PID signal.
All known local sockets are retained before hello validation. Original absolute
startup, observation and cleanup deadlines cannot be renewed by partial progress.

The instrumented reader never reads stdin. It owns a socket directly connected to
the controller, and waits for one controller byte or its independent twelve-second
socket timeout. Broker close_fds means it holds neither end of that connection.
The controller keeps its endpoint open, sends no reader byte during the two-second
window, and requires at least nine seconds of independent lifetime before stimulus.
Window completion must precede the reported timeout by at least one second.
A separate trusted same-UID/root administrator remains outside the threat model.

Broker self-SIGKILL is acknowledged on its verified connection. The controller
polls retained broker and reader kernel registrations under the original window.
Expected contrast: shared-group reader exit observed; new-session reader exit not
observed during that same window. An absence of read events is not eternal process
liveness or a proof of no queued boundary event. Freeze observed outcome before
sending the explicit voluntary reader-stop byte or closing its connection.

After the window, reader-stop, exact owned-label removal, both kernel exits and
all monitor closes are recorded independently. Each cleanup plane is attempted
where still authorized despite another plane's error. Unknown observations,
registration, acknowledgement, deadline or cleanup preserve the lock/debt and
stop the second case; no automatic replay or reconstruction. Independent timeout
bounds the escaped instrumented reader even if controller communication is lost.

The paired contrast can support a bounded causal assessment of the inspected
Darwin launchd process-group policy under these premises. It supplies no exit
status, reap, arbitrary descendant absence, Linux/systemd qualification, restart
policy, production service/code/boot admission, authorization or phone parity.
Controller/observer code origin remains an explicit trusted-execution premise,
not a loaded process-image attestation.

## Observed candidate result — November 5, 2026

One explicit paired invocation on `dfa2858` passed. Independent review matched
all six generated artifact hashes and the literal broker/reader source, and
confirmed private file modes. New-session reader exit was not observed during
2.002s; its exit was read during cleanup after the explicit stop. Shared-group
reader exit was read at 2.11ms after crash request. Both observation windows ended
about 9.99s before the reported independent reader timeout. Exact own-job removal,
both kernel exits and all local monitor closes were recorded known in both cases.
No rerun or production activation occurred. These observed-at values are not
kernel exit timestamps or parent reap/exit-status observations.

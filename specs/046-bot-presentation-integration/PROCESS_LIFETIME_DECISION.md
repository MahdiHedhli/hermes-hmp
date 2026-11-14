# Actual child lifetime binding — source implementation decision

Use a private process record created before the fixed Popen attempt, retaining
that record in typed failures if launch outcome is ambiguous. It owns the exact
Popen object and exclusive direct-child wait responsibility. No public polling,
context-manager wait, unrelated reaper or PID-selected request may share it.
Parent records keep this owner through handler cancellation and failed startup.

## Actual observations

Use os.waitpid(exact_child_pid, WNOHANG) for a successful reap, checking returned
PID and status. Do not substitute Popen.poll()/wait() for this proof: their
ECHILD compatibility behavior can report success after another reaper acted.
ECHILD/unknown wait is retained debt. Synchronize the retained Popen returncode
only after the exact waitpid success, preventing its destructor from reaping
again. A zero WNOHANG result is not completion.

The fixed child starts a new session. Before any termination signal, retain the
unreaped direct-child identity and verify its process group equals that PID.
Signal only that held group, never a request-selected or already-reaped PID.
No signals after successful wait or ambiguous ownership. The exclusive owner
must serialize signal/wait actions; no await/callback/reentry between check and
effect. Timeout/cancellation invalidates output before termination. This is
termination of a disposable owned reader, not a gateway restart or host kill.

After successful reap, probe group existence with signal zero. ESRCH is observed
absence; any existing/reused group or other error retains debt and receives no
further signal. Never claim absence merely because wait or EOF completed. This
probe is not an atomic permanent absence guarantee; final authority/current-job
checks remain necessary before publication. The trusted processing closure
must remain non-forking, and source/runtime/dependency attestation is required.

Result/diagnostic EOF and stream close come only from OwnedPresentationPipes.
Control/GO stream close is separately one-use and must retain unknown-close debt.
Termination, wait, group absence, IPC and signal-capability retirement are each
recorded once in JobOwner order. No reservation is released until every actual
required record is settled; uncertain launch or cleanup stays UNKNOWN.

## Required independent decision and causal tests

Review the exclusive wait/signal contract on supported Linux/macOS POSIX targets,
including PID reuse after reap, ECHILD, signal/wait failure, callback reentry,
late launch/cancellation, descendant/group persistence and exact ownership loss.
Real synthetic processes must prove exit0/nonzero, WNOHANG pending, timeout and
signal/wait/group observation. No real host process, credentials or profile is
used by these tests. Full source/runtime attestation, bounded parent policy
acquisition/accounting, native GO/PRE_EMIT and listener drain still block routes.

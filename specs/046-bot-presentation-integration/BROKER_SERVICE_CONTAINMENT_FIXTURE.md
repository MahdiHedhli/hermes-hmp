# Next bounded service-containment fixture — November 5, 2026

Status: independently reviewed sequence; the fixture-only Darwin observer is
implemented under its [exact contract](DARWIN_PROCESS_EXIT_OBSERVER.md). The
authenticated fixture control and one actual-reader crash experiment are now
implemented and independently reviewed (`d86d9d4`). Instrumented manager-causality
and production service qualification remain open. No job/service is installed or
activated by this document.
Preserve full desktop presentation scope; this is qualification work, not a manual
snapshot replacement or a production closure certificate.

## Darwin-first actual-reader integration

Reuse BR8a's private receipt/lock, random new GUI-user job label, exact-label absence
check, one bootstrap attempt and verified program/nonce/peer identity. Operate only
on that owned temporary installation and label. No existing daemon, Hermes profile,
provider, device grant, model setting, network message, input3 or GO is used.

Run the actual verified namespace bootstrap, retained registry and fixed reader.
A private, inventoried broker oracle pauses immediately after start_resources;
it reports only its retained child identity and fixed recipe metadata. The
controller registers a retained exact kernel process-exit observer while that
verified broker still retains the child unreaped. Require job/peer identity,
expected group geometry, successful registration and no already-pending exit
before stimulus. PID values alone never grant signal or closure authority.

Stimulus is an authenticated fixture-control connection causing broker self-SIGKILL.
No controller numeric PID signal, process-name lookup or PID scan. Record broker
exit, reader kernel exit, pipe EOF, timestamps and manager job state separately.
Observer failure, ambiguous registration/bootstrap, stale identity, timeout or
lost crash acknowledgement remains UNKNOWN. There is no automatic rerun, release,
fresh BEGIN or reconstruction of a terminal child-wait observation.

## Critical causality distinction

The unmodified no-input/no-GO reader can exit voluntarily when broker death closes
its stdin writer. Even kernel-confirmed reader exit after broker crash does not
prove launchd killed it. Label that observation actual-reader integration only.

A stronger manager-causality experiment needs a separately reviewed, private reader
oracle that cannot exit from stdin EOF during the observation window, but has an
independent bounded self-exit afterward. Label this instrumented rather than
unmodified-reader evidence. Never turn either result into descendant absence,
remote closure, native-resource drain or authorization.

## Observer/platform boundaries

Darwin uses a retained kqueue EVFILT_PROC/NOTE_EXIT registration established before
the stimulus. Its exact flags, receipt/error handling and ownership semantics are
documented in the observer contract; service identity/control integration remains open. An observed event concerns that
registration; it is not an owned reap or proof of every descendant's exit.

Linux requires its own reviewed transient user-unit containment/restart policy
and retained pidfd_open/readiness observation acquired while the broker holds the
child unreaped. Unsupported APIs refuse. Do not substitute procfs disappearance,
numeric PID checks or require non-parent waitid. Exit status may remain unknown.
Darwin evidence never qualifies systemd or a Linux production service.

## Acceptance and cleanup

- [x] Freeze fixture observer and authenticated control contracts; see [crash control](BROKER_CRASH_CONTROL.md).
- [x] Actual fixed-reader broker-crash integration: both kernel exits and broker-control
  EOF observed; reader-output EOF explicitly unobserved. One own-label run passed
  cleanup on `d86d9d4`, with independent artifact/receipt review.
- [ ] Separate instrumented manager-causality control, bounded independent self-exit.
- [ ] Causal refusals: wrong job/peer, preexisting exit, observer-registration failure,
  ambiguous bootstrap, deadline-confounded observation and lost crash acknowledgement.
- [ ] Unrelated process isolation and exact owned-label cleanup.
- [x] Actual-reader fixture requires both kernel exits and local monitor closure,
  plus exact owned-job absence, for cleanup; unknown/refusal preserves lock/debt.
- [x] Independent actual-reader source/receipt/artifact review and private evidence.
  Oracle/plugin/parser source hashes verified. Controller/observer process-image
  attestation is not claimed; executing-tool association uses coordinator provenance.

Service production admission, complete runtime/native-library qualification,
peer/boot binding, original phone/native authorization, started terminal release,
authenticated routes and signed physical parity remain separate gates.

# Actual-reader broker crash fixture control

Implementation candidates: `tools/compat/presentation_broker_crash_fixture.py`
and `presentation_broker_crash_oracle.py`. Fixture only, never plugin admission or
a production service entry. Do not activate until independent review accepts the
exact source. No existing Hermes instance, profile, credential or device is used.

## One owned experiment

The explicit non-root Darwin controller creates an exclusive private lock and a
new private temporary installation. A collision is a refusal, never permission
to delete a prior lock. It copies only current plugin/parser Python source,
inventories the installation with the separately trusted inventory tool and
records the expected manifest and bootstrap source digests. The interpreter,
verifier origin and OS-loader trust policy remain explicit premises, not claims
of loaded-library measurement. This is a generated synthetic installation.

The new random GUI-user launchd label uses one immutable program/argument policy,
KeepAlive false and AbandonProcessGroup false. The controller verifies exact-label
absence before exactly one bootstrap attempt. Intent is recorded durably first.
Raw manager output is never retained. Only exact owned job queries/bootout are
allowed; no domain-wide command, PID scan or controller PID/group signal exists.

## Mutual scope and crash command

The controller binds a static Unix socket inside its 0700 directory, mode0600.
The oracle connects but creates no reader until it verifies controller kernel UID
and PID and receives the exact `ARM <32-hex-nonce>\n` frame. Before sending ARM,
the controller verifies broker kernel UID/PID against the exact current job's
program/arguments. The root inputs are rechecked. A nonce is experiment scope,
not host authorization; a PID alone never authorizes a signal or job action.

The oracle verifies the fixed bootstrap source, complete synthetic installation
and generation; creates the real retained registry; reserves one metadata slot;
and calls actual `start_resources` under its original work deadline. It sends no
input, GO, profile path or native request. It then pauses with the actual reader
retained unreaped and reports exact PID/group/no-input/no-GO state. Private field
inspection here is labeled instrumentation, not a public production API.

The controller checks the report/group layout and registers retained kernel exit
observers for both broker and reader while the broker retains the child. Both
must have empty pre-stimulus drains. Observation and cleanup have original fixed
four/twelve-second deadlines; these do not extend reader work rights. It sends
exactly one `CRASH <nonce>\n` frame. Only that synthetic broker may self-SIGKILL,
after sending `CRASH_ACK\n`. Wrong, lost or ambiguous acknowledgement never causes
retry and never becomes a valid experiment outcome. Both endpoints freeze absolute
protocol deadlines before their respective startup phase; each send/receive uses
only remaining time and checks expiration afterward. Per-byte progress never
renews a command or observation budget.

## Independent observations and cleanup

Record acknowledgement, broker-control EOF, both kernel exit observed-at times
and exact manager job state separately. Reader stdout/stderr read ends belong to
the broker and are not transferred: their EOF is unobserved. An unmodified reader
may exit voluntarily when broker death closes stdin. Therefore even timely kernel
exit does not prove launchd kill causality. A separate instrumented reader control
is still required for that stronger question. No reap/status, descendant absence,
production closure, started release or phone authorization is inferred.

Cleanup uses only the exact known owned label and original observers. Exact job
absence alone is insufficient: both kernel exits and each local monitor close
must be observed. Partial acquisition retains the failed monitor. A missing
observer, stale identity, unknown job ownership, timeout or ambiguous local close
leaves cleanup unknown. Socket, manager, diagnostic and monitor failures cannot
skip other still-authorized independent cleanup planes. Oracle diagnostic failure
cannot escape the retained-owner supervision loop. Refusal preserves the durable lock even if subsequent
local cleanup succeeds; no automatic fresh BEGIN/rerun or terminal release.
Record precise failure and obtain a separate reviewed recovery if needed.

This fixture does not qualify Linux, multi-operation services, native libraries,
production boot/peer admission, native original authorization, transport/routes,
manager causality or signed physical character parity.

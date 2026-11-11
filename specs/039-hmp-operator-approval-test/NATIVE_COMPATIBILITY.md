## Registered command terminal integration — November 11, 2026 UTC

Actual descriptor setup/dispatch and real PTY/pipe guards now pass against native
ed1/HMP6796, with the full stock launcher deliberately excluded. See
[coverage and exact bindings](REGISTERED_CLI_PTY_QUALIFICATION.md). No native API,
mode, grant, deployment or physical acceptance is inferred from this test.

## Coupled macOS integration — November 10, 2026

The native helper sample is now complemented by real local IPC/CLI-observer and
authenticated TLS HTTP card/control on an isolated synthetic instance. All four
outcomes pass with joined cleanup. See [qualification](NATIVE_IPC_QUALIFICATION.md)
and its exact source/report hashes. Physical mobile UI, parser/TTY, Linux,
real pairing, fault and release qualification remain separate.

# AT1 native callback compatibility — November 4, 2026

The current exported native source ed1afb adds its captured `timeout_s` to the
approval notification. The previous six-key HMP callback decoder refused that
notification, so the harmless test card could not be published even though the
native helper signatures remained compatible. Repair 4ad1344 accepts only the
original keys or those same keys plus an exact integer `timeout_s` in
0..2^31-1. Unknown fields, booleans, floats, strings, negative/out-of-range values
and changed request/marker/command/pattern data still refuse.

This field is descriptive only. It does not become phone data, grant authority,
extend the original monotonic operator deadline or change a native timeout/mode.
Expiry tests with native windows up to 2^31-1 still withdraw at the HMP deadline,
without calling a resolver. No tool, shell, model or user message runs.

## Qualification

The AT1 union passed 470 tests on isolated Python 3.14.9, with 17 existing pytest
collection warnings. Two further probe-admission cases passed separately. The
producer-only subset passed 55 cases, independently reproduced. Ruff passes.

The durable `tools/compat/approval_test_native_probe.py` samples the actual
exported native approval helpers with synthetic in-memory publication. It must
run under -I -B -S with assertions enabled, an explicit dependency directory
(no .pth activation), and a new empty private HERMES_HOME. OS-account home is
checked independently of Path.home; redirected home cannot authorize installed
source. The fixture must belong to the effective UID. The caller must impose an
external process timeout.

The probe refuses instrumented Python network/process entry points and asserts
zero attempts through those APIs. This is not an OS sandbox or a proof that
every possible external effect is blocked. It checks origins of the three native
helper modules; the exported Git/file hashes are separate evidence in
[NATIVE_SAMPLE_20261104.json](NATIVE_SAMPLE_20261104.json).

A root run and independent rerun observed once_acknowledged, denied, cancelled
and expired, each with actual worker/control cleanup joined, empty test/native
queues and released slot; stderr was empty. The same admission checks and
four-outcome sample passed after the tool's live-home guard repair. This is
producer/helper compatibility only. It does not prove live operator IPC,
paired-device grants, phone display/answer, push delivery or installed runtime.

## Operator interface and remaining gates

The current source registers:

```
hermes hmp approval-test begin --device <existing-paired-device-id> --profile <canonical-profile> --session <canonical-session-tip> --timeout-ms 30000
hermes hmp approval-test status <operation-id>
hermes hmp approval-test cancel <operation-id>
```

The scoped host service still requires the existing current device/approval-owner/
bot/session checks, current generation and existing feature gates. This repair
creates no grant, owner, pairing, service exposure or setting. Live deployment
and physical card/answer checks are not implied. An uncertain begin is not
resubmitted. Native `hermes approvals test` remains a different verdict-only
helper; the in-process source probe is not a paired-phone test command.

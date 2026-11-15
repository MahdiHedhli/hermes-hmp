# Original controller first signed control frame — November 6, 2026

This is source-only first-frame staging, not working character delivery or the
complete signed GO/CANCEL lifecycle. `stage_credential_control(queued_owner)`
retains the original `PreparedControlBinding` and a `CredentialControlCursor`
before the existing controller Task runs. It creates no second parser Task.
`prepare_credential` alone remains no-IO. Production dispatch and native work
remain closed.

The actual original socket cursor reads at most 3,096 bytes (one bounded HBA1
record plus one HBR1-v2 control frame). It derives exact original scope/key/boot/
transcript/work-end expectations from the adopted, reverified BEGIN. It accepts
only first-control GO or CANCEL sequence 1, verifies authentication before body
reads, checks header/body bounds and the full-frame digest, and checks CANCEL's
native window encoding without adopting it. The original signed work deadline
is the read cap; this stage does not implement cleanup-time reads or renewal.

Original service/registry/input/budget/task/material checks bracket reads and
native callbacks. Constructor callbacks must rejoin the captured original refs
before following fields. Concrete nonblocking and exact zero-timeout checks run
after callback-bearing peer/material checks and before synchronous recv.
Captured counter identities are checked before commit; actual read counts remain
recorded on refusal. Post-read fences rejoin the original buffer, target and
pending bytes. Failure clears only the buffer captured by the original run,
retains uncertainty/readiness evidence and never retries.

A successful read retains its exact authenticated bytes, then the controller
explicitly raises `BI1_SIGNED_CONTROL_RECEIPT_INTEGRATION_REQUIRED`. It does not
observe native grammar, mint `_GoReceipt`/`_CancelReceipt`, adopt a cancellation
window, change the budget, start resources, authorize GO, or publish output.
Native work/receipt getters still refuse. The planned `retain_credential` working
entry remains unimplemented.

Independent review was source/test read-only. Root focused tests passed 46 cases
in 3.66 seconds, including fragmented reads, wrong task, expiry, retirement before
and after recv, signature/scope/boot/sequence/full-body digest/window failures,
constructor Foreign refs with zero callbacks, paired counter drift, original vs
substituted buffer cleanup, and forbidden recv on final kernel-blocking or Python
timeout drift. Broader affected regression passed 1,143 cases with one skipped in 32.48 seconds;
configured repository-wide lint passed.
These use synthetic keys/peer/clock policy with real local sockets/native tasks;
they do not qualify production startup, physical devices or release.

Remaining work includes native receipt/lifecycle integration, CANCEL after GO,
first-cause cleanup-time semantics, resource/READY startup, fixed signed producers
and remaining result/terminal/ACK IO, native publication, STATUS, and separately
authorized runtime/device qualification. Frozen image source/deployment approval
is separate. No installed host, mobile build, keys, permissions or provider changed.
The earlier unverified native-destination incident remains unresolved and is not
remedied or reclassified by this work.

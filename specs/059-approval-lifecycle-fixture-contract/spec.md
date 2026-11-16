# Approval lifecycle fixture contract repair

## Problem and scope

A fresh broad local HMP component run on74843ffc reports approval shutdown and
listener fixture failures. Original isolated reproductions fail four existing
cases: two minimal listener doubles omit the current presentation/dependency
shutdown fields, and the synthetic listener start reports a bound address without
owning the runner required by startup's current guard. A later test's reduced
AT1 context omits readiness_reads before the real server stop path; waiting on a
producer-entry event then cannot report the early stop failure.

Repair test ports only, not production. Keep every original cancellation,
record/store lifetime, generation closure, nonce and cleanup-order assertion.
Use a real aiohttp AppRunner setup/cleanup without opening a listener socket in
the synthetic start. Model zero presentation debt and known initial dependency
state on existing listener doubles. Give the reduced AT1 context its absent
readiness service explicitly. Bound only the test observation of the producer
entry event; timeout does not terminate, refund or certify the actual producer.
The original finally still requests real synthetic service shutdown and join.

No production getattr fallback, gate suppression, grant/provider/model/message/
job/device/host action, live approval or source/runtime qualification transfer.
These are controlled fake-port tests, not an original native producer receipt.
The unchanged older broad process remains owned; no restart/cancel/cleanup pass
is inferred from stalled output. The four-scenario native experiment is separate
run43902423239 on its unchanged source.

## Tasks and acceptance

- [x] Isolate four original failing cases without a host or native operation.
- [x] Inspect actual startup/shutdown fields and preserve strict production reads.
- [x] Update only the two affected test files; retain original assertions.
- [ ] Run all tests in both files plus related adapter/authority-service coverage.
- [ ] Omit the reduced-context fix on a separate controlled source copy and prove
  the bounded observation reports failure instead of waiting indefinitely.
- [ ] Independently review source and results, then publish the finite test repair.

The actual local interpreter is Python3.14.4/Darwin; no Linux CI3.11, native SDK,
physical or release pass follows. Generic lint debt remains separate. The local
branch differs in eight production paths from the image experiment's separately
materialized HMPa4a source; results cannot be transferred between them.

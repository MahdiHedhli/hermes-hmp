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
The older broad supervisor received one graceful interrupt and exited130 after
its reproduced failures. Child/all-descendant terminal closure is not attested;
the original private root stays quarantined and is not reused. No full-suite or
cleanup pass is inferred. The four-scenario native experiment is separate
run43902423239 on its unchanged source.

## Tasks and acceptance

- [x] Isolate four original failing cases without a host or native operation.
- [x] Inspect actual startup/shutdown fields and preserve strict production reads.
- [x] Update only the two affected test files; retain original assertions.
- [x] Run all tests in both files plus related adapter/authority-service coverage.
- [x] Omit the reduced-context fix on a separate controlled source copy and prove
  the bounded observation reports failure instead of waiting indefinitely.
- [x] Independently review source and results, then publish the finite test repair.

The actual local interpreter is Python3.14.4/Darwin; no Linux CI3.11, native SDK,
physical or release pass follows. Generic lint debt remains separate. The local
branch differs in eight production paths from the image experiment's separately
materialized HMPa4a source; results cannot be transferred between them.


## Observed verification

Original-source isolated repros fail four existing cases. The first changed
attempt passes108 of111, retaining three failures from an incorrect runner
attribute and another incomplete listener double. Corrected exact source5284eb15
passes113 cases across both affected files, the adapter file and the complete
AT1 authority-service file, with no failures/errors/skips. The original deferred
debt case is retained as operator/presentation/readiness cases, each keeping the
store live until its selected synthetic drain completes. Production files are
unchanged.

In an exclusive separate source checkout, omitting only the reduced context's
readiness_reads field makes the original joined-producer test fail with that
AttributeError in5.758seconds instead of waiting indefinitely. Exact source
restoration is byte-verified, followed by a fresh one-case pass. Independent
review accepts this bounded source/evidence result, not native producer authority.

A new full local unit/tool selection on5284eb15 subsequently stops with exit1
before complete JUnit: further test failures and a global filesystem monkeypatch
trap remain to investigate. This does not undo the isolated113-case result or
establish an overall pass. Its supervisor retains and waits for its original
Popen; older interrupted descendants are not relabelled. CI lint remains open.

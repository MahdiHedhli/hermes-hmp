# Bounded supervisor witness-wait result — November16, 2026

Executable0bdc4ef660fb0da4ec97f42809080736b1d9ab66; basef74543be779d95c735feff6ba1b527a21acc97ed. This changes tests only. Both server/hmp_plugin and server/hmp_startup Git subtrees are byte-identical to base.

The complete original supervisor file and new ownership file pass23 cases in5.162seconds:17 original cases, six new. No failures/errors/skips. An earlier seven-case subset also passes; it is included in23 and is not added as separate coverage. The actual PRE_GO-1-False case passes in isolation.

Reversing only four await-call replacements and removing the new helper restores the complete original test-file AST. Every existing assertion, parameter case, native observation and deadline remains. The original file is byte-identical between the parent and frozen broad8efd6c1f source. This is not compiled/tracing equivalence of the changed tests.

Six new cases cover a returned owner with absent/present witness, original exception identity, original cancellation, successful witness with owner still pending, and caller cancellation that settles only the witness. Exclusive scratch omission of owner monitoring yields the intended TimeoutError for an already-finished owner. A separate scratch control that cancels the original yields the intended ownership assertion failure. Each has one failure, no errors/skips. The0.25s test bound applies only to an already-terminal synthetic future; no native cleanup/admission deadline is increased.

Changed/new test Ruff checks are clean; the original file's parent check is also clean. Changed-source private-value scan passes. Independent source and terminal review accepts the bounded test-only result. No product/native source, authority, permission, host configuration, process budget or device state changes.

## Remaining limits

Both-pending owner/witness still wait; no generic timeout was introduced. The original broad run remains live at its existing handle90824 with its immutable source and last recorded PRE_GO-1-False wait. The original operation's current in-process state was not observed, so this does not prove the cause or resolution of that run. No original broad run was killed/restarted, and no whole-suite pass is claimed.

The selected native presentation service is separate from the preserved legacy startup/broker path. Public f1/nativef8 Linux acceptance retains its original source binding; private composition/runtime, actual Mac scanner, phone startup/characters/images, full attachments/groups and release qualification remain separate. Docker currently returns HTTP503/“Docker Desktop is unable to start”; this harness change does not repair Docker.

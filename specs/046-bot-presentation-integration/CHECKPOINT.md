# Desktop presentation integration checkpoint

Composed parent: `2bd4303`, combining reviewed deployed HMP `dbdcdba` and
existing presentation foundation `cc51a4e`. Neither foundation merge nor this
backend enables presentation routes.

The explicit POSIX backend forwards only the existing FileOps operations. The
fixed reader continues to own flags, budgets, inode/mode checks and close custody.
Real temporary-file tests prove symlink leaf/directory refusal and held-descriptor
identity across name replacement. No live profile files or images were read.

Focused checks: 28 tests plus 31 subtests passed (backend and fake transaction);
earlier composition checks: 331 tests plus 23 subtests passed (pure projection,
parent authority and skeleton). Counts overlap and are not aggregate coverage.
The selected Python environment lacks ruff; lint is not claimed.

Remaining integration: native reauthentication service and worker process/custody
binding, shutdown drain, negotiated route, optional roster projection, mobile DTO
and rendering, cache isolation, independent contract review and physical parity.
An unbound NativeReadOnlyService must continue to refuse. No future route may
construct a lease or GO marker and treat it as native authorization.

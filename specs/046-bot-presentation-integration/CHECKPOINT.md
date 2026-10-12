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

## Native observation implementation

An explicit, currently unregistered native service now binds one listener/store/
bridge/identity/native owner and owning event loop. It authenticates original
headers before and after an owned native bot-authority/home lookup; wrong owner,
listener, retired generation or late/deadline response cannot return an observation.
Cancellation leaves the real worker under a retained task; per-operation drain or
close-and-join waits for actual thread termination before releasing it. No config,
avatar or chat bytes are read in this phase.

Five focused synthetic tests exercise valid bindings, post-read identity mismatch,
wrong listener/native owner and cancelled observer with a real blocked worker.
Authenticator behavior is mocked in these five tests; they do not prove native
credential integration or deployed functionality. Live route and worker-child
binding remain closed pending focused independent review and real integration.

## Independent review findings and repair

Review of `4af2f70` found native grant recheck missing after home resolution and
task-done incorrectly treated as actual worker drain. Both findings concern inert
source, not an observed live incident. The repair checks native bot authority and
routing again inside the worker, retains an explicit thread ledger independently
of task cancellation, and refuses closure after any ambiguous start exception.
Eight service tests now include native revocation during lookup, cancellation of
the owned task itself and ambiguous start. The combined service/parent/layout run
passed 258 tests plus 23 subtests. Independent re-review remains pending.

## Actual YAML parser integration

A worker-only PyYAML SafeLoader event adapter now feeds the existing closed reducer
without loading a profile object graph. Only the five allowlisted presentation
fields can leave the reducer. Explicit tags/directives, aliases/anchors, ambiguous
keys, multiple documents, selected-field type confusion, malformed UTF-8 and
expired shared deadlines refuse. Fifteen real-parser cases passed using synthetic
documents. No live metadata was read. Supervisor-enforced process deadline and
independent parser review remain prerequisites before route activation.

## Real fixed-reader transaction evidence

Three real-kernel synthetic cases passed: complete fixed metadata transaction
feeding the actual YAML reducer, symlink metadata refusal with all owned FDs
closed, and name replacement during read refusal with all owned FDs closed.
The synthetic test parent was explicitly selected under a safe ancestor chain;
no live Hermes directory or profile file was opened. Other test environments
with unsafe ancestors skip these fixtures rather than weaken production policy.
These cases qualify transaction/backend composition, not request authentication,
worker process isolation, live routing or physical parity.

## Worker processing pipeline

The fixed-reader result now feeds the actual YAML reducer, bounded raster
structural inspector and closed presentation DTO. Metadata carries canonical
instance/profile and separate metadata/image revisions; expected avatar revision
mismatch or clear refuses. The original clock/deadline is required on the raster
budget. Raw profile bytes cannot appear in the projection. Six real-file tests
passed, including actual metadata-only and tiny synthetic PNG result composition.
Raster structure admission is not a decode proof; the phone codec remains the
decoder. Shared total job ledger and child supervisor integration remain open.

Independent review accepted exact native repair `0eef794` with its three findings
closed by four separate inert checks. Receipt SHA256
`0514c3c5a2e02b7652166a8344303fa1a14142c22b702eada9bfde59e00746e2`.
This verdict does not cover the later parser, real-file or pipeline additions and
does not authorize live activation or certify atomic authority over file I/O.

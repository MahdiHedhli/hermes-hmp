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

## Deadline and lint checkpoint

The pipeline now checks the deadline after metadata revision/projection as well
as before it, and rejects a raster budget with an extended/different clock scope.
Causal tests cover both boundaries. All eight new source/test modules pass the
CI-pinned Ruff 0.16.9 checks; 34 focused backend/native/parser/pipeline cases pass.
Formatting and literal-dictionary cleanup do not alter the accepted native
ownership algorithm. The lint environment is available through the pinned tool
runner; the earlier missing-module limitation is superseded. No activation occurred.

## PYAML-01 review repair

Exact `d15c938` review found that PyYAML discards unknown directives before
document events, contradicting the all-directives rejection claim. The adapter
now scans bounded source tokens under the same deadline and refuses every actual
DirectiveToken, including unknown names, before parsing events. Token count is
bounded at 2048; block/quoted scalar text is not treated as a directive. The actual
unknown-directive and block-scalar regression cases pass. Combined parser/pipeline
run: 25 passed. Review of this repair remains pending; no route was activated.

## Nonresetting work ledger foundation

One immutable-limit ledger now retains file/read/hash/open/metadata/path/YAML/token/
raster counts across phases. Duplicate phase entry or exhaustion poisons it; an
expired/malformed clock cannot recover by moving back. Snapshot callers receive
a copy. Six counter tests and layout checks pass; pinned strict lint passes.
The file/YAML callback bindings and actual child supervisor remain incomplete,
so the shared-budget task is still open and no route was enabled.

## Shared ledger phase bindings

The fixed reader now debits shared bytes/open/metadata/path credits before I/O,
retaining the exact ledger in its processing result. Actual YAML scanner tokens
and reducer nodes debit the same ledger; raster processing must use that identical
clock/deadline/ledger. The worker processing entry creates the single ledger itself
and rejects mismatched profile before any file-open attempt. Real-file cases cover
metadata/avatar cumulative charges, replacement-ledger refusal and whole worker
entry. Twelve real-file cases pass and selected strict lint passes. Legacy pure
phase fixtures retain optional unbound counters; the worker entry does not use them.
This qualifies the processing budget binding, not a spawned process, child frame
proof, parent authorization, shutdown drain or live route. Independent review of
this new binding is pending. The shared-budget task awaits that review; supervisor
and transport remain open.

## Bounded private worker result frame

Completed processing now retains only numeric source proofs/hash/chain rows,
closed metadata and optional avatar bytes; no raw profile bytes/path enter IPC.
The existing frozen frame codec bounds header/body and binds challenge/epoch.
Real-file tests check raw-private-field/path exclusion and wrong challenge refusal;
default-profile blobatar survives frame-to-parent projection unchanged. Fourteen
real-file cases and selected lint pass. These frames are processing evidence,
never permission, and do not establish actual child wait/group/IPC/FD custody.

The shared-budget binding at `d1521fd` received bounded independent acceptance
with21 separate checks, receipt SHA256
`2fc1c83c70a0fc10dde8bec5979894d3171fe3f56c9668a16976d1bbee5f456f`.
Combined presentation/Unicode suites on that exact processing source passed256
tests plus190 subtests. Later framing changes require their own focused review.

## FRAME-NONE repair

Review of `98e7ca2` found null-character metadata for the default profile was
reconstructed as an implicit purple squircle because the normalized frame omitted
custom. The frame now explicitly suppresses that implicit default for every
normalized result, preserving a null character and its metadata revision. Raw
customization provenance is not claimed by these projection inputs. Two actual
file-to-codec-to-projection negative cases cover custom-only and invalid-color
characters;16 real-file cases and selected lint pass. Independent closure pending.
No host activation or updated phone install occurred.

## Parser runtime declaration / CI correction

CI38196929251 rejected the undeclared yaml import (11 scanner-suite failures;
source processing tests were not proof of install packaging). Runtime PyYAML>=6,<7
is now declared in plugin.yaml/project/lock; the already locked version did not
change. A narrow lazy module-import exception is confined to the worker adapter.
Other modules, module-level worker imports, from-imports and submodules remain
rejected by negative cases.64 scanner tests and selected lint pass in an isolated
fixture. The earlier successful61-case run had81 old temporary-artifact cleanup
warnings; those unrelated artifacts were not modified. Independent review of the
closed-surface amendment remains required. No live dependency installation occurred.

## Child control codec / lazy-import review repair

A bounded child control decoder now accepts only the existing closed input frame,
its exact64-byte GO challenge/newline and EOF before profile I/O. Missing/mismatched
GO, trailing data and oversized prefixes refuse. Seven stream cases pass; actual
stream reads can block and the parent hard-deadline/child custody remains open.
This is a local IPC binding, never native authority.

Independent dependency review found eager class bodies bypassed lazy-import rules.
Actual function-depth checks now reject module/nested eager classes and preserve
function-local class imports, including the analogous bridge late-binding rule.
Seventy scanner cases and238 control/layout cases passed; independent
review of the new lazy-scope repair remains required. No activation.

## Parent GO handoff

A synchronous one-use handoff binds the exact job handle/child and an observed
nonblocking pipe identity. Blocking/non-pipe or replaced descriptors refuse;
retired/wrong-child scopes perform no write. The65-byte GO uses one syscall, and
partial/invalid results or exceptions after actual writes cannot be retried.
Ten focused cases pass, including a real pipe and actual write-then-lost-ack.
An initial five failures were synthetic tests lacking the newly required explicit
pipe-info port; fixture correction preserved the production checks. Selected lint
and the preceding241 GO/layout tests pass. This module creates no process and
does not own/close its borrowed descriptor; the supervisor must supply exclusive
FD custody and native reauthorization. Independent handoff review remains open.

The lazy-import dependency repair `80c1406` received independent source acceptance
with37 separate scanner cases (receipt SHA256
`4fea051371c8a08f4cd05c65171b2ed5da8dc2658b25df2c56f096b1525a6789`).
This does not include the separate child control decoder or GO handoff.

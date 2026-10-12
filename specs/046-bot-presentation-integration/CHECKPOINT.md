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

## GO-01 one-use reentry repair

Review of88f103 reproduced two writes when current/pipe-info callbacks reentered
the handoff. Entry ownership is now consumed before callbacks; any reentry poisons
it even if the callback catches the refusal. Two new counterexamples perform zero
writes after caught reentry;12 GO cases and selected lint pass. Independent
closure review remains pending. No real worker launch or live route occurred.

## Worker launch policy

The fixed launch recipe selects the current absolute interpreter, isolated/no-
bytecode flags, one fixed future worker script, a new process session, close_fds
and no inherited descriptors. The environment contains only LANG/LC_ALL, never
a copy of provider/bearer/PYTHONPATH/loader variables or a changed HOME. Three
finite tests pass, including a real isolated interpreter with synthetic secrets
absent and an explicitly inheritable parent pipe not inherited. The recipe is
not source attestation: the worker script does not yet exist, and its verification,
actual launcher/ownership/drain and child code remain required. No live plugin
process or profile read was started by these tests.

GO-01 repair at54d0df received independent source acceptance with17 separate
checks, receipt SHA256
`4a72ac1380265a0e0493ac0fe870a05976129f724fddc47674bc743d87e26c6c`.
Actual exclusive FD custody/native binding/child supervision remain outside it.

## Controlled worker stream composition

Child-only processing now joins bounded input/GO, exact root/home/profile/UID/GID/
deadline/challenge/source-manifest scope checks, the one-ledger processing entry
and bounded result encoding. Output advances only known written prefixes; write
exceptions are not retried and expiry is checked after flush. A real-file stream
case passes and wrong GO reaches neither the scope factory nor filesystem opens;
17 real-file cases pass. Selected lint passes. The scope factory remains a trusted
parent-policy dependency, not request authority. No child entry script, process
launcher/reap/group/IPC ownership or live route is supplied by this module.

## Local-media rendering source check

Checked the existing deployed scanner's one-entry tool_call declaration linkage
and the mobile transcript's image-card placement. The scanner accepts the native
resolved image_generate tool result paired to a single image_generate declaration
inside tool_call; the card is above the collapsible tool header. Therefore no new
wrapper-name exception or expansion of assistant MEDIA-path authority is justified
by the screenshot alone. The historical named JPG is absent; fresh physical image
confirmation remains open. This is source evidence, not live rendering proof.

## WORKER-01 original-input preservation

Independent review of5b1961 found the scope factory could mutate the decoded row
used to validate its own deadline/hash/epoch. The factory now receives a deep copy
of the bounded primitive input; the original comparison/processing/emission source
never leaves the flow. Actual file cases reject deadline/hash substitution before
opens and preserve epoch1 despite a private-copy epoch/list mutation. Twenty
real-file/actual-pipe cases and selected lint pass. Independent closure pending.

The parent GO writer and child decoder also passed a real-pipe composition case.
No actual presentation child process, native permission or cleanup ownership is
qualified by that pipe-only test. Live routing remains absent.

## Current combined source verification

Exact3e85a38 passes286 presentation/Unicode tests plus190 subtests and complete
server/tools strict lint. WORKER-01 received independent closure with9 separate
causals, receipt SHA256
`d68814fcf2871937debfd4c1a6c4604019bb02026eb8efa152157330498f4b6b`.
This does not establish process custody, native route binding or installed support.
The draft branch was pushed for a fresh exact-head public CI run; prior failed CI
evidence stays intact. No live host/app or grants were updated.

## Scope preparation expiry fence

Worker flow checks the retained original deadline immediately before and after
scope preparation. A late factory cannot proceed into profile I/O or output even
with otherwise matching scope data. The new causal reports zero opens/output;
20 real-file cases and selected lint pass. The factory itself is not forcibly
bounded by these checks; actual child hard-deadline supervision remains required.

## October 12: strict child schema 2 transfer

Added the closed parent-qualified directory policy and bounded projection context codec, plus a schema-2-only GO reader. Canonical fallback must already match the existing normalized presentation name. Legacy schema 1 is rejected by the new path. No child entry, supervisor, native route, deployment or physical character result is claimed. Focused codec/control/layout verification: 260 passed; targeted Ruff imports repaired. Initial verification mistakenly referenced a nonexistent test file and ran no tests; the corrected invocation above completed. Independent source review remains pending.

## October 12: schema 2 processing binding

Added fixed schema2 processing and lexical policy reconstruction with exact effective UID/GID checks, singleton directory modes, and explicit default-profile mapping. It reuses the original retained-input/deadline/output fences; no child filesystem policy discovery occurs. Real synthetic profile processing preserves name/hexagon projection and closes descriptors. Focused real-file/codec/control tests: 48 passed. Independent schema2 codec review reported no actionable finding in f12a360 (61 independent cases); processing binding still awaits its own review. Actual standalone entry/provenance, parent policy acquisition, process custody, routes, deployment and physical rendering remain open.

## October 12: actual isolated child entry

Implemented fixed own-file private namespace bootstrap and schema2 processing entry with effective identity checks, no sys.path/environment/config/provider lookup, closed diagnostics and original input deadline adoption. The parent must bound startup/imports/blocked IPC with the original hard deadline; sys.float_info.max is only a pre-decode ceiling, not a renewed work deadline. A real -I -B process using a synthetic secure profile returned Synthetic/hexagon metadata; 258 real-file/layout tests passed. Namespace collision refusal added. This is not code/dependency attestation or an OS sandbox; parent source verification/policy acquisition, supervisor custody and route binding remain required before deployment. Independent entry review pending.

## October 12: CI dependency reconciliation

CI 38200379495 is terminal failure at 08b2c08: three tests retained the old qrcode-only dependency assumption. Local correction additionally exposed an actual root-install manifest omission: PyYAML was declared only in the package manifest. Root manifest now matches the reviewed bounded worker dependency. Routing/config writer absence and global third-party import restriction are retained; QR version checks select QR explicitly. 119 CLI/merge regression cases pass with a dedicated temporary directory. Worker 03f0d2c and entry 873bf02 independent source reviews reported no actionable defect. Runtime provenance must cover bytecode reads (Python -B only prevents writes), interpreter/system-site hooks and dependency origins; activation remains open.

## October 12: full-suite child import correction

Exact broader suite at 8af2c6d: 13 failed, 5613 passed, 38 skipped, 190 subtests; all failures came from the new child absolute private-namespace imports violating the surface scanner. Fixed bootstrap now assigns its explicit private __package__ and uses static relative processing imports, as the reviewed design intended. Scanner/global import policy is unchanged. Mobile header name+character sharing implemented at dbe4111; three widget cases and changed-source analysis passed, independent review pending. No deployed/physical claim.

## October 12: bounded actual pipe collection

Added OwnedPresentationPipes with pre-effect descriptor identity checks, finite selector waits under the original deadline, stdout/diagnostic limits before retention, diagnostic-content discard and actual EOF/one-use close records. Timeout/overflow never manufacture closure or release a reservation; errors retain uncertain ownership. An initial causal test found closed FDs disappearing silently from selectors; polling now verifies all held stream identities before select. Four real-pipe cases plus layout: 241 passed after correction. This is the receive/close part of supervision, not process launch/wait/group/signal or source attestation; independent review pending.

## October 12: actual child/pipe composition

Added a second real isolated-child execution path using OwnedPresentationPipes rather than subprocess capture. It verifies bounded result collection, diagnostic count, actual EOF/stream closure and successful wait while preserving Synthetic/hexagon projection. 23 real-file cases pass. Cleanup in this test targets only its exact synthetic Popen process; no production signal/group custody is inferred. The full suite started at e9c9a23 remains separately observed and must not be claimed to cover this later test delta.

## October 12: PIPES-01 ownership repair

Independent review held e9c9a23 because acquisition plus selector-close failure lost the exact selector owner. PipeAcquisitionError now retains the failed owner plus original/cleanup exceptions under a closed diagnostic. Selector construction is inside the owned failure path; close is marked attempted before effects and cannot be retried after uncertainty. Causal creation/double-failure/no-retry tests plus real child/pipes: 29 passed. Review closure remains pending; no activation. The e9c9a23 broad suite is a separate prior-source run, not evidence for this repair.

## October 12: exact broad-suite result

The exact e9c9a23 source run (session9372) completed exit0: 5631 passed, 38 skipped, 18 warnings, 190 subtests in179.52s. It includes the relative-import repair and original pipe reader, but predates ef58812 composition-test and6c600de PIPES-01 repair. Those later deltas have their separately scoped focused results; full-suite success does not close the held acquisition issue or physical gates. Log: /private/tmp/hermes-character-full-suite-e9c9a23-20261012.log.

## October 12: process wait/signal decision

PIPES-01 independent closure accepted6c600de,11cases, receipt SHA739bdb986fc8ce23cd315bca63310ffdb6223cb843ee21480a162ae91ee2376f. Added precise exclusive process lifetime proposal: direct waitpid proof rather than Popen ECHILD compatibility, held unreaped-group signals only, post-reap group absence probe with no further signals, typed failed owner retention and separate pipe/control cleanup. Contract review is required before binding; no new launch/deployment performed. Corrected stale shared-ledger contract prose to reflect implemented source while retaining parent-accounting gate.

## October 12: actual launch/terminal-wait ownership

Implemented retained fixed Popen launch owner, typed uncertain launch failure, nonblocking serialized/sticky reentry checks, stable child PID binding, exact terminal os.waitpid evidence and one post-reap signal-zero group probe. No Popen poll/wait/signal helpers are used. Actual isolated reader with empty input returned its expected refusal/exit1, bounded pipes drained and group absence was observed. 248 initial process/layout cases passed; later bound-PID focused cases pass. Destructive signalling, auto-reap/competing-reaper runtime exclusion, hard termination schedule and JobOwner binding remain unimplemented; no activation. Independent source review pending.

## October 12: owned control input/GO/EOF

Implemented exclusive nonblocking control pipe with fixed schema2 byte packet, original deadline, descriptor identity/blocking checks, one-use input and existing GoHandoff, exact close attempt and retained unknown outcome. Caught callback reentry prevents writes; changed blocking flags refuse before effects. Native PRE_GO must still call this through ParentAuthorityAdapter; no credentials/authority are conveyed. 243 control/layout cases passed. Real reader composition with this control path added separately; process hard deadline/termination, reaper/source qualification and full binder remain open. Independent review pending.

## October 12: CONTROL-01 prewrite/terminal repair

Independent review held c64f89e: control-owner poison or expiry during pipe callback could still send GO, and caught reentry in final writes could report normal completion. Added owner-aware actual GO write wrapper after pipe callbacks, rechecking current scope, poison and original deadline; final input-ready and post-GO/post-close success fences retain uncertainty. One-use GO/write/close debt is preserved without replay. Five new causal real-pipe cases cover callback poison/expiry/scope loss and final input/GO reentry; 33 real reader/control cases pass. Original HOLD receipt SHA595c656056d0a3a0a215fdc814da87d13b3aed7391d52e5b704edbb81b2bb12c retained. Review closure pending; no live activation/incident.

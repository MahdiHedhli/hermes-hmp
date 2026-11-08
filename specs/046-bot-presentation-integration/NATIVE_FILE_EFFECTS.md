# Held native file effects — proposed integration contract

Status: independently reviewed source contract; implementation and qualification
remain open. This
continues the full presentation startup requirement; it does not replace runtime,
loader, native/key, transport or physical qualification with a smaller feature.
Baseline: HMP1a49174; native reference ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df.

## Integration and ownership

Extend the existing original startup IO lifecycle rather than create a second
arbitrary-file API. Cover all six captured operations: open/read/close/stat/fstat/
readlink. Bind the actual interpreter native_io allocation to the original scope,
activation, descriptor records, aggregate counters and source/cache/link context.
Obtain it through the original entry/source binding, never a later namespace
lookup, caller path/hash/error or qualified Boolean. Keep legacy configuration
reads distinct; they must not mint entry/native outcome or fallback authority.
No request, profile or HTTP client may select an operation or IO root.

Each admitted operation holds its original actor, current authority, fixed native
function, arguments and original result slot before the native call. Arguments
use exact primitive types and existing canonical relative-path/descriptor rules;
no foreign PathLike, coercion, equality or callback is admitted at this boundary.
Open flags and stat-result types come from the held native origin. Consume the
attempt before calling; no guard/refusal callback may erase or replace it.

Capture an actual returned result or raised boundary outcome before callbacks or
postcondition refusal. Preserve the held result when owner/slot/counter/authority
changes afterward. Bind native open returns to the original descriptor allocation;
retain exact read/readlink lengths and aggregate progress including EOF and
refusal overread. No copied result tuple, synthetic fault object or final payload
hash substitutes for the original effect history. Rejoin the original scope,
ledger and allocation after callbacks and before publication/current use.

## Refusal, cleanup and resource limits

A native-boundary exception is not proof of kernel entry: audit hooks and builtin
argument handling can raise before a syscall. Neither class/errno nor synthetic
fault injection proves kernel ENOENT/EACCES. Initially all failed or ambiguous
operations remain refusals. Do not add operational source fallback in this slice.

Cleanup retains the original fd/allocation and original context even after work
refusal; it may not revive work authority. Attempt close once, capture its actual
boundary return, and retain unknown debt after a lost acknowledgement. Numeric fd
reuse is not a second close of the same descriptor record. Do not retry unknown
open/read/close effects or clear foreign replacement state. Preserve actual known
byte progress separately from unknown additional kernel consumption.

Before implementation, specify aggregate attempt/result storage limits, returned
buffer ownership and exception/traceback lifetime. Do not retain unbounded read
payload copies or exception tracebacks. Existing128MiB/read-count/file/count/byte
limits cannot reset at the new owner boundary. Resource bounds are source
constraints, not operational CPU/RSS/deadline qualification.

## Required acceptance

Exercise actual temporary no-follow file/directory operations for all six calls,
primitive/type rejection with zero foreign calls, native substitution, wrong
thread/process and stale/revoked context before attempt consumption, original
slot/ledger/counter drift, real returns followed by lost acknowledgement, partial
read progress, EOF, descriptor-number reuse, close exactly once and retained
unknown debt. Distinguish synthetic pre-call faults from actual boundary returns
and from unproven kernel outcomes. No error grants fallback or code execution.

Cover original configuration/package/entry/runtime/cache/link callers separately;
source-only current/floor and complete affected regression are required, followed
by independent contract/security review. Do not alter live hosts, grants,
providers, devices or release state. The ongoing fixture/broad verification roots
remain frozen. Actual presentation-service admission and physical bot-image
rendering remain separate unfinished requirements.

## Concrete resource and outcome proposal for second review

Use one original entry-bound lineage across package/artifact/runtime-source/cache
read/probe/link scopes; fresh SourceDigestContext objects do not reset it. Bind it
in the original invocation/entry allocation before its first admitted operation,
then carry the same lineage in typed original IO scope cells. Legacy configuration,
operator approval and recipe acquisition remain explicit separate phases: no
retrospective native-effect credit is invented for their earlier operations.

Proposed hard cap:1,048,576 total operation attempts including all six operations,
ancestors, probes, EOF, failures and cleanup. This is an upper source bound, not
an operational memory or latency qualification. Before each open, reserve capacity
for that open plus exactly one possible close of its original descriptor record.
Other work consumes only unreserved capacity. A known returned descriptor keeps
its reserved close even if later result allocation or work authority fails.
Open-unknown debt cannot be converted into permission to close a guessed fd.
No budget renewal or next-phase reset is allowed. Implementation must use bounded
O(1) append/custody with a bounded final traversal, not quadratic prefix copies.

Preallocate the attempt record, raw return slot and result-allocation slot BEFORE
native entry. Write actual native fd/bytes/stat_result/None into the held raw slot
immediately on return, before tuple/count/receipt allocation. Keep a known fd
closeable through its original reserved record even if any later allocation fails.
Retain raw bytes/stat results only until the same original fixed consumer has
acknowledged the exact returned allocation. Then clear raw references and retain
bounded category/actual length/count/result-claim identity, never payload history.
The fixed consumer must own any metadata/payload needed by its existing receipts;
retirement cannot manufacture a new success or erase unknown debt.

For exceptions, store no exception, traceback, message, repr, filename or errno.
Record only that the actual held native boundary raised, plus a closed category
based on exact originally captured exception-type identity when available. A
foreign subclass has only the generic raised category and receives no attribute
access. Clear exception/data aliases and raise a fresh refusal outside its handler.
All raised categories, including exact FileNotFoundError, remain non-fallback.

Cleanup checks original process/UID/thread, descriptor/allocation, held native
close builtin, reserved capacity and original cleanup custody. It does not call
live work guards or require current os aliases after work retirement. Close has
one attempted transition and an actual returned slot before later checks; loss
of acknowledgement retains unknown debt without automatic replay or closure credit.

Second review must accept or amend these exact storage, cap, retirement, exception
and cleanup choices before code is described as implementing the frozen contract.

## Accepted ownership and state-machine clarifications

Independent read-only review accepted the source cap and lifetime/reservation
proposal with the following mandatory clarifications, now part of this contract:

- Preallocate the original attempt AND result-claim object/slot in the original
  immutable scope/descriptor lineage. Hold those exact locals across callbacks.
  Acknowledgment joins the exact attempt, claim, raw returned allocation, fixed
  consumer owner/scope and original progress. A reconstructed equal claim or
  mutable current slot cannot acknowledge a result. Failed ACK retains debt and
  original cleanup custody; it cannot discard the result as though consumed.
- Establish original actor/context eligibility before consuming an attempt. Use
  explicit in-flight/reentrance exclusion: an audit callback cannot start another
  work effect or close a descriptor while the native boundary is in flight.
  Admitted failure is sticky. Cleanup begins only after the original call has
  returned or raised, never while its result/resource ownership is uncertain.
- Attach reserved close capacity to the original descriptor attempt BEFORE open.
  Transfer it only to the actual known returned fd. Post-return allocation or
  guard failure cannot cancel that reservation. Unknown-open debt never guesses
  an fd or returns the reservation as reusable work credit. An exhausted work
  allowance cannot block a close that already owns reserved capacity.

This is bounded contract acceptance, with no reviewer tests or writes. It is not
implementation acceptance, operational RSS/latency qualification, kernel outcome
proof, source fallback, deployed startup or physical character-image completion.

## Exact source integration map

At1a49174, the following sites must all participate; migrating only ordinary
artifact helpers would omit real operations:

- `gateway_entry.GatewayEntryOwner.start` and its actual original invocation/
  retained binding provide the entry anchor. Retain one typed lineage before its
  first admitted entry-bound IO operation. No completed historical binding or new
  digest context creates another allowance. Creation itself performs no file IO.
- `presentation_startup_artifacts._Scope` carries the original typed lineage as
  an additional explicit field. A legacy scope has no lineage and stays on its
  existing path; absence cannot be inferred as native qualification.
- `presentation_source_digest.retain/current` binds the actual original entry
  and shared lineage for package/artifact source phases. The manually constructed
  SourceDigestContext in `runtime_reader.RuntimeSourceReadOwner.retain` must reuse
  that lineage rather than reset it.
- `cache_probe.RuntimeCacheProbeOwner.retain` creates a scope with no source
  digest; `cache_reader.DeclaredCacheReadOwner.retain` does too. Both must receive
  the same actual entry-derived lineage through their original continuation,
  independently of source hashing. No late caller-supplied entry reconstruction.
- `StartupArtifactOwner._open/_close/_read/_stat/_fstat/_readlink` are shared
  native boundaries. Migrate typed entry-bound calls through the fixed dispatcher
  and preserve legacy dispatch distinctly. Descriptor allocation must hold close
  reservation and raw-return storage before open; cleanup uses those originals.
- `DeclaredCacheReadOwner._read` performs its own direct os.read rather than using
  the ordinary `_read`; it needs the same dispatcher and exact original pending
  read-claim acknowledgement. Its existing effect/result history and4096-call
  cap remain required alongside the shared aggregate operation cap.
- `RuntimeCacheProbeOwner._stat_known` catches current stat outcomes. A raised
  dispatcher category cannot silently become absence/permission or source fallback.
  Existing diagnostic provenance needs explicit migration; kernel proof stays open.

The implementation must document which original scope/claim holds every raw
native return until its fixed consumer acknowledgement, including allocation
failure and work-guard retirement. Generic private callbacks or a consumer-supplied
success flag do not satisfy this map. No implementation or test pass is implied
by this source inventory.

## First implementation checkpoint — unqualified

Corrected source0ebe76e adds only the original immutable entry allocation and explicit
lineage propagation through every listed scope, including probe/cache scopes
without a digest context. Digest currentness rejects copied/foreign lineage and
requires the scope to hold the actual original allocation. Ten refusal/normal and retained-constructor substitution cases, receipt-layout
regression and stronger existing phase-inheritance assertions are present.
The ten new cases passed on actual Python3.14.9 and3.11.15, zero failures/errors/
skips and unchanged source. Existing modified phase-inheritance assertions still
need their broader affected run. Syntax/full Ruff and bounded independent source
review accepted the allocation-only increment after the repairs below.

No operation budget/dispatcher, native result claim, cleanup reservation or
fallback is implemented by this part. The full contract and all remaining
implementation/verification requirements remain open; this is not a narrower
replacement for the required runtime or image-delivery end state.

The initial untestedf17bf42 placed the field on a receipt rather than the scope,
breaking constructors and shifting positional source timestamps. Review caught
this before execution/deployment. Corrected0ebe76e restores the exact original
receipt field order, adds only a trailing scope field, and explicitly joins probe/
cache/source scope lineage through the original entry getter. Static AST layout
comparison and the10+10 selected actual constructor/receipt causals passed;
broader constructor/phase regression remains required.
No earlier lint or syntax check is represented as a runtime qualification.

## Accepted native outcome distinction — November 8, 2026

Status: bounded read-only contract refinement accepted. The unwired sanitizer
implements only closed diagnostic classification; the operation owner and typed
consumer integration remain absent.

An operation's raised outcome is terminal and single-use. It never becomes a
success, kernel-absence fact or source-fallback permit. This differs from lineage
integrity/resource failure, which terminates collection except known cleanup.

Class-only sanitization would weaken existing cache missing-path checks and is
not sufficient. Only the fixed STAT exception handler may compute a closed
reported_missing_for_original_stat_argument category, after checking all of:
exact originally captured FileNotFoundError class; exact int errno equal to the
existing ENOENT requirement; exact str filename equal to the held original stat
argument. Type fences precede equality; foreign subclasses/attributes are never
inspected. Retain no exception, traceback, errno, filename, message or repr. The
closed category records what the native boundary reported, not kernel provenance.

Diagnostic acknowledgment requires an original typed plan/consumer claim made
before the call: original owner/scope, cache source, pass, path index, observation
ordinal, exact native stat arguments and original result allocation. The fixed
consumer may acknowledge only that exact category/claim. Its next same-path stat
is a distinct predeclared observation ordinal, never a retry or renewed allowance.
Preserve actual parent descriptors, ancestor rechecks, currentness and known
cleanup before publishing diagnostic DATA. No callback/Boolean chooses continuation.

Permission/structure/wrong-errno/wrong-name/foreign-subclass stat outcomes,
fstat/open/read/readlink errors, unknown open/close resource debt, and actor/
ownership/result drift terminate collection. Only known original cleanup remains.
Unknown debt is neither released nor converted into work credit. The accepted
diagnostic acknowledgment does not erase the operation refusal or poison the
entire shared lineage; the same aggregate quota and all prior facts remain.

Existing legacy missing-path checks remain unchanged until the typed consumer
route is integrated. Never reconstruct or rethrow an exception from sanitized
metadata. Runtime admission and fallback still require separate reviewed policy.

Review: existing character_custody_review, source-only; no tests, writes, native
calls, device actions or deployment performed by reviewer.

## Stat sanitizer implementation checkpoint

Source2cad9e5 adds an unwired exact-type diagnostic classifier plus15 synthetic
negative/normal cases. Full Ruff passes; tests have not run while the earlier
1290-case source regression occupies the serialized test lane. Independent
read-only review found no blocker within this narrow diagnostic-only scope.
The captured exception descriptors are trusted import-time metadata, not a
validated original interpreter dependency. Before native-owner integration, bind
their exact descriptor identity/class and ENOENT type to the held original error
origin. No exception or traceback is retained by the result. Calling the helper
with a constructed exception proves no actual operation or kernel condition.
No production route imports it and no authority, fallback or image delivery is
implemented by this checkpoint.

The next source increment rejects foreign captured descriptors and non-integer
ENOENT before invoking any descriptor. Exact MemberDescriptorType, OSError
owner and fixed slot names are required. Three synthetic dependency-substitution
cases bring the selected test set to18; none have executed yet. This validates
local capture shape only. Joining those captures to the original interpreter
origin remains required at native-owner integration, with actual claim custody.

## Shared ledger storage allocation — unqualified

The next separate source increment preallocates ledger storage before bootstrap:
an empty attempt list, used/reserved count cell, in-flight cell and failure cell.
Both the immutable original invocation and original lineage retain the same
ledger, entry/native/context allocation. Retained-binding checks join those
identities. Existing lineage causals now assert the original initial storage.
No dispatcher, scope registry, step/consumer claim, counter transitions, close
reservation or native call is implemented yet. Storage allocation is not an
operation budget enforcement or image capability. Tests have not run on this
increment; earlier exact-source qualifications do not apply to it.

The retained data getter now checks mutable storage shape before returning it:
exact lists/lengths, exact integer counters within the shared cap and reservation
headroom, inactive in-flight state and exact boolean failure state. Six added
original-cell mutations cover opaque/bool/negative counts, over-reservation and
foreign in-flight/failure values without foreign callbacks. This is structural
DATA validation only: attempt node/consumer custody and real counter transitions
remain unimplemented, and no native call is permitted merely by passing it.
Tests on this16-case lineage set are pending the existing serialized test lane.

## Original scope registry — unqualified source increment

A new separate increment allocates an original scope registry in the shared
ledger and records fixed package/artifact/runtime-source/cache-read/cache-probe
retention paths. Legacy scopes remain distinct and record nothing. Each redacted
registration joins original lineage, owner/scope/cell/root/context and its exact
registry index. Actor and existing owner guards run before registration. The
data currentness check refuses copied/foreign owner records and copied registry
records without foreign callbacks. Eight new causal cases exercise actual probe/
reader retention in the existing isolated entry fixture; tests are not run yet.

This is scope provenance DATA, not a predeclared path/component/descriptor step or
fixed consumer claim. Native operation dispatch, budget transitions, raw-result
custody, reserved close enforcement and result ACK remain absent. Passing the
registry check grants no IO or runtime admission. Other retention paths and the
full affected regression still need qualification. No live host/device changed.

Review found callback-order defects in the initial scope registry before any
execution/deployment: registration could overwrite a foreign slot or adopt roots
changed during actor/guard callbacks; currentness could adopt a paired replacement
read after its guard. The repair takes original scope/cell/root from each fixed
initializer, holds registry/index/vacancy across callbacks, and rejoins those
originals before append/assignment and again in the caller. Currentness requires
the held original record as an explicit argument before callback-bearing guards;
paired owner/registry replacements cannot become the selected record. Six added
callback-window causals bring scope registry coverage to14 pending cases. Source
review/tests of this repair remain required; earlier lint is not a runtime pass.

## Original registration slot and callback-free capture — unqualified

The next source increment adds a trailing defaultNone registration slot to the
original immutable IO scope. Only entry-bound constructors allocate exact[None];
legacy scope constructors keepNone. Registration holds the slot across callbacks
and fills it once with its actual registration alongside registry/owner mirrors,
without overwriting a foreign value. Currentness requires the same held slot and
actual record after callbacks. A callback-free metadata capture accepts the
initializer-held scope/cell/root and returns that slot's original record; actor/
authority currentness is still a separate required operation. Twenty source
causals are present, including substituted slot values, no guard call during
capture and slot changes during registration callbacks. Tests are not run yet.

Explicit registration threading through all file/tree/cache/link walkers and
typed per-step/consumer claims remain required. Cleanup must use held original
registration/resource custody without reviving callback-bearing work guards.
Package/entry scandir, iterator advancement and iterator close are separate
filesystem effects: the six captured operations do not cover those effects,
whose origin/effect/cleanup qualification remains open. No native operation or
image capability is granted merely by capture or registry presence.

## Held registration threading — partial, unqualified source

The next separate source increment threads the actual registration returned by
package initialization through both tree passes, recursive walks, enumeration
work guards and file hashing. Artifact complete captures from its original scope
slot before actor callbacks and passes the same record to every file. Runtime
source/cache readers capture before admission and pass that original to_file.
File work guards validate the held record; legacyNone remains separate. Existing
file fault wrappers forward the new argument so intended mutations are not
replaced by accidental signature errors. Eight new actual isolated source/cache
walker cases cover normal forwarding, copied/missing arguments and paired slot/
owner/registry substitution. They assert zero new file descriptors/bytes on
refusal; these cases are present but have not run.

This is not complete registration threading: entry-file metadata/tree walks,
cache before/after/ancestor probes, link/hop observations and per-operation
arguments/consumers remain to integrate. The six native boundaries/direct cache
read/stat, separate enumeration effect origin, quota and independent reserved
cleanup remain unfinished. Existing cleanup is not made dependent on a new work
guard. No source fallback, live host/device change or runtime/image acceptance
is implied by the partial source map.

Review of the first threading increment found two final callback gaps before
execution/deployment. The repair reseals the held source fact after the file's
last work guard and checks original result/root/count, followed by a pure held
registration rejoin. Package verification rejoins the held registration/registry
after final origin callbacks and again before fact publication; no new actor/
freshness callback cycle is started. Three added causal cases mutate the source
effect or registration at those precise tails. The new walker set is11 cases,
not yet executed; source review of this repair remains required.

The first21-case threading run on27135dc failed21/21 during setup: the new final
join incorrectly reused the three-part entry-root capture for legacy operator
approval's four-part root. The failure is preserved; no deeper mutation case is
claimed as exercised. The repair keeps the existing held legacy3/4 root identity
and unchanged owner guards, requires both native fieldsNone in the legacy branch,
and applies strict original-slot capture only to entry-bound registrations. This
is compatibility repair, not a relaxation of operator approval or native scope
authority. Exact repaired runs and independent review remain required.

## Cache and link registration forwarding — unqualified source checkpoint

A separate increment forwards the complete method's captured registration through
cache before/after passes, individual probes, missing-path and ancestor checks,
and link snapshots/path/readlink observations. Recheck-link captures from the
original scope before callbacks. Work guards consume that same held registration;
final metadata publication uses pure held registration joins and existing link
seals. Cleanup keeps the original descriptor/root path and does not acquire a
new live work guard. The reviewed legacy import-isolation repair fromfffa1b3 is
carried here with the explicit no-entry-import legacy assertion.

No new test run qualifies these changes yet. Focused forwarding/refusal causals
and independent source review are required. Separate fresh cache-probe owner and
entry metadata/tree walkers are not yet migrated. Per-step/consumer claims, raw
six-operation dispatch, diagnostic-plan ordinals, quota/reserved cleanup, separate
enumeration effect custody and runtime/device image delivery remain unfinished.
Existing exact missing-path checks are preserved; no fallback is added.

Bounded independent read-only review found no new forwarding/tail/cleanup-gate
defect in58e3478. Eleven added isolated source-active cases assert actual held
registration forwarding, copied/missing argument refusal, paired replacement at
cache-pass/link-path final callbacks, and metadata recheck fact/registration
replacement with unchanged byte/read counts. Both child injection scripts parse;
these cases have not executed. Existing wrong-ENOENT/name/permission behavior and
exact source selection remain required in affected regression. This is not a
claim of complete registration threading or native effect admission.

## Fresh cache-probe registration — unqualified source increment

The standalone metadata-probe owner captures its actual scope registration and
root/cell/count before actor admission, threads them through the owned observation
and exact-stat helper, and validates the held registration at work checkpoints.
Status-query publication also captures before callbacks and ends with a pure
held registration join. Original resource cleanup remains independent of new
work guards; exact missing errno/name/type rules remain unchanged.

Nine new isolated cases cover normal/copy/missing arguments, actor replacement,
stat registration substitution, final publication replacement, and current-query
registration/fact replacement with no new bytes or resources. Both child scripts
parse; tests have not run. Independent review and affected probe regression remain
required. No new native operation/path authority, diagnostic fallback, quota/
cleanup enforcement or runtime/image admission is implemented by this step.
Entry metadata/tree threading and all per-step/consumer/native-effect work remain
open; earlier cache/link results do not qualify this new source.

## Entry metadata/tree registration — unqualified source increment

The entry snapshot captures the retained IO owner's actual scope registration
before metadata work and threads it through IO-current checks, before/after
trees, recursive directory walks, enumerations and loose-file metadata. Final
entry publication rejoins held IO registration/roots after origin callbacks.
Metadata/tree/name results are returned only after known cleanup and a final
work check plus pure original registration join. Iterator cleanup uses the held
original context and remains independent of a new work guard.

Sixteen new isolated cases cover normal/copied/missing forwarding into four
walkers and paired replacement at post-cleanup or final entry-origin callbacks.
The child scripts parse; tests have not run. This draft includes the exact
present-leaf probe repair from9a4ed59. Independent review and affected regression
remain required. No step/consumer/native operation authority, quota/reserved
cleanup, complete enumeration origin or runtime/key/image admission is implied.

Review found a nested-access callback gap in the initial entry draft: IO-current
checks dereferenced a potentially replaced origin before rejoining its held
scope. The repair validates original scope/activation types before the callback,
then checks exact scope/cell/root identity before nested access. Final entry
fact publication also repeats original lifecycle/attempt/fact/count invariants
after allocation. Seven added callback cases cover foreign-origin zero-getter
refusal, coherent scope replacement and lifecycle/attempt/IO fact/count drift at
publication. Entry coverage is now23 prepared cases; no test pass is claimed.
Independent repair review and exact qualification remain required.

## Original declared-file identity — unqualified source increment

Entry-bound_file now requires the exact ExpectedArtifact object from its retained
original declaration tuple (or the validated package manifest's files), checks
existing primitive path/size/hash constraints, then rejoins its held registration
before any file acquisition. Equal copied declarations and unlisted paths cannot
be substituted. Legacy operator/configuration reads preserve their prior guards
and do not acquire this entry authority.

Eight prepared package/artifact cases exercise normal, copied, unlisted and
foreign expectations. Invalid cases assert unchanged original count/descriptors
and zero foreign hooks outside catch boundaries, so early unrelated refusal
cannot masquerade as a causal pass. Child scripts parse; tests have not run.
Independent review and exact current/floor qualification remain required. This
check is a prerequisite for fixed per-step claims, not a replacement for them,
raw-operation custody, resource accounting or runtime/image authority.

## Native primitive argument boundary — unqualified source candidate

Entry-bound open/stat require exact string relative components and an exact
nonnegative integer parent; only fixed root slash accepts no parent. Open's
directory selector must be an exact Boolean. Read/fstat require exact nonnegative
integer descriptors. Legacy paths retain their previous behavior. Existing
readlink and close already enforce exact bytes/integer arguments. These checks
reject foreign path/index/Boolean behavior before native calls; they do not prove
original descriptor membership, per-step authority or typed native outcomes.
Fourteen normal/foreign actual composed-file cases are prepared; tests pending.
Full operation custody, reservations and service/physical qualification remain open.

## Original declared walk allocation — unqualified source candidate

Native scope registration preallocates a bounded immutable tuple of file-walk
records from its exact declaration table. Each record retains original owner,
scope/cell/root, expected row, ordinal and path components. Legacy registrations
return before this allocation. The original registration retains the tuple and
progress cell; the actual fixed file path holds its selected record/state locally
from before descriptor acquisition until after final known cleanup and receipt
joins. Start requires the next exact row and unstarted state; successful completion
advances once. Failed work leaves started intent for the owning refusal path.

These are file-walk intent records, not individual syscall/consumer claims,
descriptor membership or authorization derived from a mutable progress value.
The fixed trusted callers still supply declaration order. Per-operation planning,
original parent/resource custody, aggregate quota, reservations and native outcome
ACK remain required before this becomes native effect authority. Cache probes may
retain an unused declaration record; no payload read is inferred from that DATA.
Five composed package cases are prepared: normal original allocation and
completion, replay, out-of-order row, Boolean progress and already-started refusal.
Tests have not run. Source-only review and affected regression remain required.

## Combined regression failure — exact local import scanner repair

The frozen9e6f02a combined startup run has recorded failures and remains active;
no terminal result or full cause is claimed. A separate static comparison confirms
two S1 violations: startup artifact registration lazily imports GatewayEntryOwner,
_NativeFileLineage and _NativeFileLedger, but the scanner had no exact allowance
for that HMP-owned sibling module. This made otherwise positive scanner fixtures
fail from the baseline package. The separate repair permits only these three type
names lazily in presentation_startup_artifacts.py. Eager imports, module imports,
wildcards, helper functions and other plugin modules remain closed. Nine additional
positive/negative scanner cases are prepared. Static scanner and Ruff pass; pytest
qualification is pending the existing serial lane. Other combined failures must
still be assessed from the actual terminal JUnit/tracebacks. No production guard,
upstream Hermes import or runtime permission was relaxed.

## Original registration at native open boundary — unqualified candidate

All eleven production StartupArtifactOwner._open call sites now forward their
already-held registration: package trees, artifact/runtime link and file walks,
entry metadata/trees, cache absence walks and fresh cache probes. Native opens
refuse missing/copied registration before descriptor allocation, and rejoin the
same held registration before native entry and after the returned fd is stored.
A pure final join follows callback-bearing currentness before publishing the row.
Legacy None registrations retain their existing path. Failure cleanup still uses
the original known descriptor/root/context rather than a new work guard.

Eight package/artifact normal/copied/missing/post-return-copy cases are prepared;
post-return mutation must leave the actual known row close-attempted/closed while
retaining unknown debt. These tests are unrun. Static scanner, Ruff and diff checks
pass. This does not capture the original native open function, grant per-operation
or descriptor authority, reserve cleanup capacity, enforce the aggregate quota or
complete the other five native operations. Original raw-return/claim custody and
all runtime/service/physical requirements remain open.

## Original registration at native metadata boundaries — unqualified candidate

All39 fixed stat/fstat sites forward their caller-held registration through
package/file/link/cache/probe and entry metadata/tree paths. Both boundaries
validate that same registration before the native call, retain original scope/
root/cell/registry, capture actual returned stat_result locally and repeat the
held registration join after callback-bearing currentness. Final joins are pure;
legacy None registrations retain the previous supported path. Existing metadata
exception handling and original known-descriptor cleanup remain unchanged.

Sixteen composed package/artifact cases cover each operation with normal, copied,
missing and post-return coherently replaced registration. A synthetic C-call
observer counts actual unchanged native functions at the fixed method's frame;
pre-refusal must observe zero calls, late refusal exactly one call plus actual
stat_result and original known descriptor closure. No native function is mocked.
Child script parses and Ruff/static scanner/diff checks pass; tests remain unrun.
Line-wrap edits preserve the parsed AST. This is registration forwarding only:
original native callable/typed argument-resource/step/result claims, bounded raw
slots, quota/reserved cleanup, remaining operations and actual runtime/service/
physical delivery are still unfinished. Native absence/fallback is not inferred.

## Original registration at native byte reads — unqualified candidate

The fixed artifact/source reader and distinct declared-cache reader now consume
the same caller-held registration at admission, immediately before native read,
and after return/currentness before data publication. All four payload/EOF file
call sites forward it. Actual returned byte accounting and prior result/effect
allocation behavior stay intact; late registration refusal does not erase those
facts. Cleanup still follows the prior original known-resource path. Legacy None
callers retain their existing behavior; this creates no alternate cache fallback.

Twelve composed cases are prepared: package/artifact and declared-cache readers,
normal/copied/missing/late-coherent-copy. Actual unchanged native read calls are
counted at the fixed reader frame. Pre-admission refusal must have zero reads;
late refusal observes actual positive byte return, retained progress and unknown
debt. Declared-cache late refusal requires its original 65,536-byte result and
attempt record. No returned payload is retained by diagnostic lists, only lengths.
Static scanner/Ruff/diff and both child-script parses pass; tests remain unrun.

This is registration custody only. Raw returns are not yet preallocated original
native-result claims, and the original native callable, resource/step/consumer
binding, quota/reserved close, cleanup after root retirement and actual native
runtime/service/physical feature qualification remain unfinished.

Read review found two synthetic fixed-signature wrappers: source-digest split
reads and runtime-reader buffer substitution. Both now forward the optional
registration unchanged; the 257-byte split and post-actual-read buffer mutation
remain intact. These causals must execute rather than fail from call arity.
Declared-cache finally may retire the active routing pointer when its original
root/ledger/claim still match; actual attempt/result/effect and byte progress
remain retained, unknown is latched, and no replay or fallback is authorized.
This preserves existing cleanup semantics rather than treating pointer retirement
as a successful acknowledgment of the refused native result.

## Held native work callees — unqualified executable candidate

Five fixed work operations now select their literal-index original native
function locally before callback-bearing work guards: open/read/stat/fstat/
readlink, including the distinct declared-cache read and fresh-probe stat paths.
Open retains original flags; metadata paths retain original result type and the
probe's exact missing-error class. A typed capture and pure original namespace
join check actual os/posix function identities, flags, result/error classes and
original registration lineage. Each fixed boundary rejoins its local callee
immediately before direct dispatch and the origin after post-return callbacks.
No generic operation-selection or caller-supplied callable interface was added.
Supported legacy None paths retain alias selection and avoid entry-only imports.

Fifty composed fixed-operation cases are prepared: positive actual calls,
origin copies, os substitution before admission, and os/posix/flag/result-type
and os/posix error-base substitution after the final work guard. Negative cases require zero actual
selected native calls and zero foreign hooks; original known resources must still
close. Capture checks only the already-loaded entry module dictionary, requiring no new
entry import or scanner allowance. Five missing-type module cases require zero
missing-attribute hooks. Synthetic
pre-call fault selectors now name the actual shared dispatch lines, preserving
fault timing instead of silently selecting the unused legacy branch. Existing
actual-return/progress/debt cases remain required. Tests have not run.

This is executable callee custody only, not completed native IO authority. Actual
per-operation actor/step/resource/result claims, preallocated raw returns, shared
attempt budget and independently reserved original close remain unfinished. The
current close path still uses a later os.close lookup: namespace drift can cause
foreign cleanup dispatch or leak. That source limitation is not a deployed
incident finding; no operational/factory/service/device or release readiness is
claimed, and this source must not be deployed as fully owned native IO.

Held-callee review found the fresh probe's private stat boundary lacked the
shared native-only exact name/parent fence. The repair applies that same fence
after admission and before stat, with four normal/foreign name/parent composed
cases requiring zero foreign coercion hooks and zero native calls on refusal.
The pure origin join also explicitly checks both os/posix error-base aliases
against the original OSError class; ten added substitution cases cover those
previously unjoined captured facts. This does not change missing-error/fallback
authority or the unqualified close/resource/actor/runtime limits above.

Capture refinement: remove dynamic entry imports before work guards; inspect the
already-loaded exact module dictionary and type identities instead. A foreign
module with missing definitions is rejected without invoking its __getattr__.
The draft NativeIOOrigin import allowance and four associated cases were removed;
the existing scanner boundary remains unchanged. This does not by itself anchor
all module/code/runtime dependencies, which remain separate admission gates.

Origin-capture review rejected using current entry-module type exports as the
source of accepted types: a replacement exact module could nominate a foreign
lineage class and trigger its getter before scope validation. The repair retains
original lineage/ledger/native type identities, ledger/native allocations and
entry-module identity in the original registration at qualified construction.
Constructor publication rejoins those exact allocations. Capture first joins the
original scope/cell/root/slot, active activation root, owner cells and original
registry; pinned types precede nested lineage/ledger/native access. Current module
state is only identity revalidation, never a type authority or import source.
Five added normal/copied/foreign and paired-replacement cases include a matching
foreign-type module plus getter traps and require zero getters/native calls.
These repairs and tests are unqualified until independent review and execution.

## Captured actor functions — close prerequisite, unqualified source

Entry now retains exact original POSIX getpid/geteuid and _thread.get_ident,
including their original native/Python namespace modules. Interpreter-current
comparison checks the same allocations; native work-origin joins verify aliases
without calling substituted functions. Each fixed work dispatch then checks its
actual actor with the captured functions before file IO. The separate actor
context helper intentionally does not depend on current namespace aliases, so a
future independently retained close claim can use it after work retirement.
This helper establishes context equality only; it grants no cleanup authority.

Six added origin-substitution cases and nine actual-context cases are prepared,
including wrong identity/thread and valid context despite retired alias fields.
Synthetic alias hooks are retired before thread/interpreter shutdown. Static
scanner/Ruff/diff and child-script parsing pass; tests remain unrun. Close still
uses its old path until immutable original open/close claims, reserved capacity,
raw slots and all coupled descriptor-status validators land together. No quota,
resource, factory/runtime/service/device or feature completion is claimed.

## Actor-return repair checkpoint — November 8

The actor-functions candidate now repeats original owner/argument, registration,
native origin and selected callee joins after sampling the three captured actor
functions at all seven fixed work dispatches. Open additionally preserves the
original descriptor-list allocation, length and each original row identity.
Read and readlink preserve their original count/effect/read-claim state. These
checks are bounded source repairs, not reserved-close or whole-runtime authority.
The actor helper accepts structurally fenced internal tuples; only the joined
registration supplies provenance. Shape or context equality alone grants nothing.

Ten new synthetic child cases mutate native aliases or the registration at the
actual final get_ident C-return; three malformed actor tuple cases must refuse
without foreign getters. They are prepared, not executed or accepted. Ruff, diff
checks and the plugin-surface scanner pass. Independent review is pending; the
serialized prior regression remains running. Native close reservation, runtime
binding, bot character delivery, local image delivery and physical qualification
remain incomplete. No deployment or installed-feature claim follows.

## Coupled reserved-close candidate — November 8

This source candidate implements original open/close storage and one reserved
cleanup per admitted open, actual raw returns before result-wrapper allocation,
immutable opened descriptors and native closure proof in all inventoried startup
consumers. Continuation resources retain their original file scope; directory
iterator resources keep their separate contract. Legacy configuration/approval
reads retain the legacy descriptor path.

Entry-preallocated preparation storage excludes reentrancy before actor sampling
and allocation. Only the actor helper's explicit actual-context mismatch remains
non-consuming; every later exception, including the same exception class, retains
original failure/debt and blocks further work. Actual known-FD cleanup uses its
held original reservation even after work/root/namespace refusal. Unknown close
never retries. Partial interrupted debit is retained, not reset as fresh capacity.

Thirty-four causal tests are prepared but unrun. Bounded source review does not
qualify them, the coupled consumer regressions, the Python floor or runtime/device
behavior. The wrappers/helpers are internal DATA with independently held scope and
original ledger requirements; an arbitrary self-consistent wrapper grants no
external authority. Open/close metering does not complete the six-operation budget.
Scandir/next/iterator-close, full loader/factory/key/transport binding and physical
character/local-media delivery remain unfinished. No deployment occurred.

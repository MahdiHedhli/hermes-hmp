## November 8 — reviewed host updates deployed; character integration remains open

Declared bytecode-cache reader work has advanced separately: frozen producer
`9d5e549` adds exact-type preflight and original-cohort cleanup, with three
malformed-field cases passing on both interpreters (3 each, no skips, unchanged
source and verified log/XML bindings). Descendant `6f84dee` integrates
a fixed buffer/hash/header and actual-EOF consumer plus caller ACK closure;
The 18-case cache-reader run on `6f84dee` finished 17 passing and one failing:
activation-owner drift was refused but its read claim had already been cleared.
The failed source/log/XML evidence is retained. Repair `8afe009` adds activation
owner/cell joins before publication; independent finite review found no new
blocker. Normal plus owner-drift cases passed on each Python version (2 each,
unchanged source, verified log/XML). Its 34-case suite, including partial-ACK
interruptions and prefix-wrapper retirement checks, passed on Python 3.14.9:
zero failures/errors/skips, unchanged source, source/receipt/log/XML rehashed.
The same 34-case suite also passed on Python 3.11.15, with zero failures/errors/
skips and unchanged source; source/receipt/log/XML bindings were independently
rehashed. Both runs qualify this cache-reader slice only. The separate floor
linear-read timeout remains open; no complete startup, six-operation, runtime/
service or physical qualification is claimed.

Separate unqualified metadata preparation `b63aed9` inventories all39 stat/fstat
sites and both missing-stat diagnostics, captures primitive stat DATA, allocates
lazy original declared-file site plans and retains the actual plan in its walk
handoff. Review corrected the plan to match final ancestor checks. Eleven focused
plan/caller cases passed on each supported Python version (11 each). Resource
`e593cde` passed five composed cases on each version, and operation preparation
`0884893` passed eight on each; all sources/receipt/log/XML bindings were rehashed.
These qualify preparation slices only. Directory-consumer preparation `bbf877d`
retains original scope/material/lifetime bindings and one-use result ownership;
nine focused cases passed on each interpreter. Subsequent causal constructor
mutation tests reproduced a missing final material-closure check on the control;
repair `cefd515` passed all12 cases on each interpreter. Each injected mutation
was refused before publication. Fixed directory-policy DATA source `d537500`
passed20 cases on each interpreter. Exact source/log/XML hashes were rechecked.
Latched-cohort preparation `a19560a` separates structural joins from unclaimed
admission; all14 dedicated cases passed on Python3.14.9 with unchanged source
and rehashed source/log/XML evidence. All14 also passed on Python3.11.15,
with source/log/XML hashes rechecked. Fixed ACTIVE-state guard `a131932` passed
all20 cases on Python3.14.9 with unchanged source and rehashed evidence; its
same20 cases also passed on Python3.11.15 with unchanged source and rehashed
source/log/XML evidence. Finite review found no new concrete defect after the
explicit phase/failure-slot checks. These remain guard-only passes.

Separate uninstalled directory producer `f47a1be` passed29 original intent/
admission/pending-return cases on each supported interpreter. Candidate
`8f12da7`, with production bytes unchanged from ACK source `520b08d`, then passed
all45 selected synthetic native/policy/ACK cases on each interpreter, including
10 source-store interruptions. Source/receipt/log/XML hashes were rechecked.
These component passes are not complete caller, runtime or device acceptance.

A new negative control on unchanged production `4072412` reproduced lost producer
return on both interpreters: the actual return-event fault fired, the caller
received no value, raw/envelope remained pending and the ledger was still healthy;
the one-unit charge remained. Each original test failed once as expected, with
exact private stage evidence rehashed. Those failures remain failures. Producer
finally alone does not establish caller receipt; current stored rows cannot be
adopted as returned receipts. The uninstalled candidate remains unqualified.

Directory custody migration `b6b8322` moved retained result/consumer raw-bearing
cells behind one detachable payload link. Its 58-case current-version regression
finished55 passing/3 failing, with no errors/skips and unchanged source. All
three failures reached the original60-second child deadline; no cause is yet
established. The failed source/receipt/log/XML evidence was rehashed and retained;
that candidate is not qualified and its floor lane did not start.

Successor `963b0a6` fixes reviewed state/equality and captured-cell ordering gaps,
captures actual cells before C, stores the raw return immediately, and rejoins
original lifecycle/material/native/budget state after custody callbacks. Its11
memory checks passed on each supported interpreter, including actual marker-
return cell replacement and GC-disabled synthetic reclamation. Its four fixed
producer cases also passed on each version, including revocation after custody
capture with zero observed callee c_call events and normal-case calibration.
These events are not kernel-entry receipts. Source/receipt/log/XML bindings were
rehashed. The full62-case selection then passed on Python3.14.9 with zero
failures/errors/skips, unchanged source and rehashed source/receipt/log/XML.
The same62 cases passed on Python3.11.15 too, with zero failures/errors/skips,
unchanged source and rehashed bindings. These qualify that selected source,
not the later caller or a complete runtime/feature.

Test-only `6d3a8cd`, with production identical to `b6b8322`, ran one original
timeout case with a private45-second stack sampler and unchanged60-second
deadline. It passed at26.093 seconds before sampling, leaving an empty stack
file. This supplies no timeout cause and does not erase the original failures.
A fresh static recheck of installed native source `ed1afb0` finds the public
`hermes-gateway-v1` session-authority contract (typed submissions/request IDs,
receipts, snapshots and mutation). This is a potential integration route, not
qualified HMP phone access: native transport ticket/actor authorization must be
mapped explicitly, and session attachment changes subscription/lifecycle state
rather than acting as a passive health read. Legacy peer sends generate a fresh
delivery key; contract presence alone does not resolve external message identity
or the duplicate-history bug. No live requests, grants or session operations
were performed. Independent read-only review confirms that the public runner
reference is not itself a device-authority issuer. No qualified per-device native
read/submit delegation route was identified in the inspected paths; this is not
proof the entire SDK lacks one or that upstream code changes are required.
Native authorize can also restore/mount cold sessions, so passive readiness must
not invoke it. See the current native session-authority source note.

Fixed-site DATA preparation `e285873` adds original row variants allocated with
the plan before descriptor acquisition. Structural role/op/component checks,
current resource and latched-consumer variant joins are source-reviewed, with
no new concrete DATA preparation blocker;19 plan tests now pass on each
supported interpreter, with unchanged source and source/log/XML hashes rechecked.
The tail is not full canonical-order or original-plan proof. Future fixed
callers must carry actual plan/variant returns across callbacks and bind all
predecessors/resources/actor/budget phases. No dispatcher, effect site or walker
finish-guard change is introduced; this code remains separate and uninstalled.

The next source draft `872e0fb` adds original-actor eligibility before caller
custody allocation/latching while retaining the later ACTIVE sample. Independent
source review found no new blocker. An unchanged-production cross-thread control
then failed on each interpreter: actual rejection and zero native calls still
changed preparation and metadata-progress state. Those failures remain failures.
The early-actor repair passed the same case on each interpreter with all nine
observed shared-state fields unchanged; it did not add effect authority. Uninstalled leaf-policy
preparation `d85d5d2` preserves declared regular-file type/owner/link/size/mode
checks in primitive DATA;23 tests pass on each supported interpreter, with
unchanged source and rehashed evidence. This proves selected policy checks,
not native-result/declaration provenance or admission. It
excludes anchor/configuration policies; actual leaf/ancestor consumers, original
mtime/hash/EOF checks, complete plan ACK progress and device/runtime integration
remain required. The refreshed39-site inventory matches all prior semantic
entries with current five-file hashes and diagnostic function locations checked.

The same source `e597dfe` subsequently passed the full71-case selected metadata,
memory and caller regression on each interpreter (71 each, no failures/errors/
skips, unchanged source and rehashed evidence). A separate test-only single-
interruption control `9808a93` then found pre-detach payload retention on both
interpreters; post-detach controls reclaimed it. Each control suite remains one
failure and one pass, not qualification. Corrected diagnostics reached actual
producer/native/arm/injection checkpoints exactly once, with GC disabled and
original debit/failed phase preserved; earlier missing-diagnostic refusals remain
inconclusive. Isolated repair `779312e` rechecks original actor and pre-effect
custody before a final conditional memory-only detach. Both before/after cases
now pass on each interpreter (2 each), with payload reclaimed and no invented
retirement/ACK marker. Lint and plugin-surface checks pass. The broader73-case
repair regression now passes on Python3.14.9 (zero failures/errors/skips,
unchanged source and every source/log/XML hash rechecked). The same73 cases
also passed on Python3.11.15 with zero failures/errors/skips, unchanged source
and all source/log/XML hashes rechecked. Independent repair review found no new blocker for the
single interruption. Four selected combined actual-caller cases on `cc9603e`
now pass on each interpreter: normal, wrong actor and before/after-detach
interruption, with unchanged source and rehashed evidence. The broader121-case
selected regression of that exact source now passes on Python3.14.9, with zero
failures/errors/skips, unchanged source and every source/log/XML hash rechecked.
The same121 cases also passed on Python3.11.15, with unchanged source and
source/log/XML bindings rehashed. Separate constructor controls on both versions
then reproduced accepted snapshot identity/mtime drift after an actual native
return. Those negative controls are retained as failures, not qualification.
Isolated repair `b2deb97` rejoins primitive returned fields to held native-derived
inputs before publication; independent finite review found no new blocker.
Separate identity-only and timestamp-only regressions plus normal/interrupted
caller cases now pass on both Python3.14.9 and3.11.15 (5 each, zero failures,
errors or skips, unchanged source and rehashed receipt/log/XML). All four causal
constructor checkpoints prove post-native refusal, no producer publication/ACK,
reclaimed payload with GC disabled and preserved original debit/failed state.
The121-case baseline did not cover this later constructor defect; its negative
controls remain retained and the repair has only the stated focused scope. Other isolation/
repeated-interruption cases, actual-site integration and physical/runtime
qualification remain open. The older73-case baseline does not cover the later
cross-thread preparation defect; the separate repair/control evidence above
must not be replaced by that passing baseline. This is not a completed image-delivery feature.

Separate caller source `e597dfe` has now passed13 memory cases and seven actual
synthetic native caller cases on each supported interpreter (20 each), with
zero failures/errors/skips, unchanged source and rehashed source/receipt/log/XML.
The caller holds actual factory custody before effects and actual producer/
policy/ACK returns. With cyclic GC disabled, tests verify owned capsule
reclamation for normal operation, actual lost producer return, revocation,
foreign public slot and copied inner marker. Late marker drift and a finalizer
revoking activation during disposal preserve the real ACK/cursor/debit while
failing the original operation; no native replay, refund or FD close is used.
The call counter observes callee c_call events, not kernel-entry receipts.

This handles the original lost-return counterexample in the isolated new caller;
the original failing control remains preserved. It does not prove interruption
at every store, wrong-actor cleanup, arbitrary foreign alias erasure, complete
retained-root graphs or real directory/site integration. The original timeout
cause remains unknown; no deadline was raised. These local implementation and
runtime/device gates stay open; no prototype is installed. An ordinary ledger-
field replacement finding was withdrawn after source verification showed the
fields are immutable named tuples; unneeded defensive code was reverted. No
runtime vulnerability or incident was established for that invalid example.
The [caller and repair contract](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/046-bot-presentation-integration/NATIVE_METADATA_RESULT_CUSTODY.md)
and dated39-site inventory document the local work. Caller integration, all
metadata/tree/link/missing-stat sites, six operations plus enumeration, original
aggregate budgets/reserved cleanup, complete factory/service/key/runtime, the
open minimum-version timeout and physical character delivery remain unfinished.
No character-prototype activation, device/feature/release pass or observed
user-data exposure is claimed. This startup bytecode/character custody work is separate from the
reviewed host-local chat-image deployment, which the owner has now authorized
and which is installed separately as recorded below. Physical acceptance remains
open. No character prototype is represented as installed.

Source-specific leaf-before policy `4c6f33c` now preserves the actual snapshot's
`st_mtime` conversion: exact numeric types, strict64-bit bounds and integer
truncation toward zero, including pre-epoch fractions; nanoseconds are not used
as a replacement. Forty focused leaf/timestamp DATA cases pass on each supported
interpreter, unchanged source and receipt/log/XML rehashed. Independent policy
review found no new blocker; its source-only scope is explicit, so cache or
non-source reads do not gain a new timestamp requirement. This remains a
prerequisite for the shared fixed-site consumer, not native admission or a
completed walker. Fresh static inspection of installed Hermes0.23.0/0f0e96fc
still finds the unbounded native avatar getter; no qualified safe shortcut was
established, no getter was called and no upstream change was made.

Open-registration source `1aa605d` passed all 1,434 configured startup cases on
Python 3.14.9 with zero failures, errors or skips; its eight focused cases passed
on both Python 3.14.9 and 3.11.15. Exact source/receipt/log/XML bindings were
verified. Earlier `77ae4dc` retains its separate 1,426-case pass and 183 focused
passes on each interpreter. The original `9e6f02a` failed run remains preserved.

Later coupled open/close source `5439fee` finished its 412-case focused run:
400 passed and 12 failed, with no errors/skips and unchanged source. Source,
receipt, log and XML bindings were rechecked. Eleven positive cases hit the
existing 60-second child deadline; one failed a close-ACK assertion. Diagnosis
continues without extending the deadline or relabeling failures as passing.
Unrun intermediate queues were consolidated into this descendant only after
ancestry and selected-case coverage checks; no active test was interrupted and
no unrun candidate is claimed passing. Its floor and full regression runs depend
on resolving the focused failures. No complete native IO/cleanup/quota/runtime
or device qualification is claimed.

Separate uninstalled source `9dc2875` finished its 68-case reader selection:
38 passed and 30 failed. Its first normal-case refusal was traced using only
synthetic guard function/line metadata: the caller passed an entire five-part
walk receipt instead of its original plan. Successor `2312e0b` corrects that join
and the optimistic close-status mirror without weakening the original-ledger
validator. The first 14 focused cases passed on Python 3.14.9. The repaired source then
passed all 130 selected read/close cases on that interpreter with zero failures,
errors or skips and unchanged source. Actual source, receipt, log and XML hashes
were rechecked. Python 3.11.15 then finished 129 passing and one failure: the
synthetic source-digest `linear_reads` child exceeded its existing 60-second
deadline. Source was unchanged; receipt/log/XML bindings were verified. This
floor suite is not qualified. Test-only `daf6350` prepares a 45-second bounded
stack diagnostic without changing the deadline. It reproduced the timeout,
but the parent did not persist child output. Test-only `ca2ea03` repairs private
raw-output persistence and adds two failure-preservation checks; all three
isolated cases passed, with the linear case at58.038 seconds. A further test-only
`01b586c` saved a private45-second stack even on success and passed at59.128s.
The sample shows repeated parent-package descriptor-history validation during
entry-file completion, not proof of an exclusive cause. Review found no safe
direct audit deletion across callback/import boundaries. The original timeouts
remain preserved; no deadline extension, weakened test or full floor pass is
claimed.
The original failures remain preserved, not relabeled passing; no complete
startup, six-operation, runtime/service or device/image qualification is claimed.

Corrected isolated EOF source `708beff` passed29 cases on each Python3.14.9 and
3.11.15 with zero failures/errors/skips and unchanged source; all bindings were
rechecked. Its original `7a4d42f`26-pass/3-failure fixture run remains preserved.
Cleanup diagnostic `b3115ee` passed its two mock evidence tests but still failed
the normal60-second timeout and close-status check. The latter now passes on
2312e0b; the profiling timeout cause is still unresolved. No deadline was raised.
The unstarted repeat on test-only3102341 was deferred before any child ran,
allowing source diagnosis first; no active test was interrupted.

Host-local media and desktop characters have separate source paths. Reviewed
local-media package `5e247a6` plus client source `56d517c` do not depend on the
unfinished character-source admission stack. After explicit owner approval,
ColPanicM2 received the exact reviewed109-file HMP package and a single native
graceful restart. Its new gateway retains native0.22.7/ed1afb0 and three profiles;
TLS identity and send/jobs/model readiness checks pass. LLY520 completed its
native0.23.0/0f0e96fc update, then received the same reviewed HMP package and a
supported graceful restart. Five profiles remain served; Belac/default/School Bot
channels are ready, while Lucas/Serenity retain their prior unavailable status.
LLY520 configuration and paired-device/control fingerprints are unchanged across
the HMP install/restart. Compatibility checks report local-media availability;
no actual phone image-display pass or per-device/API execution is claimed.
Existing paired-device legacy controls-decision warnings are retained for a
separate access review; no grants were changed. Character factory/runtime admission, remaining cache/metadata/link/
diagnostic integration and enumeration are still unfinished. Separate source
486bf04 prepares original cache journal joins and transient head handling; its
new helper is unused DATA validation. The actual cache producer, fixed consumer,
header/EOF acknowledgment and causal tests remain to implement.

Device-local sections/static icons and selected-bot readiness are implemented in
app source, with physical qualification pending. Desktop character parity and
host-local image delivery remain unfinished. No upstream prerequisite has been
established for the remaining HMP integration. Public integrated code remains
`34b862e` for the unfinished character work; the separate R3 image package
deployment above does not qualify that stack. The connected iPad
still refused automated launch as locked; no launch/crash acceptance is claimed.
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

## Verified isolated source results — November 8, 2026

Original-lineage5883690 passed the exact35-module1,290-case startup regression
on actual3.14.9 in2,508.53 seconds, unchanged source and zero failures/errors/
skips. The prior10 actual3.11.15 selected lineage cases retain their exact scope.
Unwired sanitizer66f7897 passed18 current and18 actual3.11.15 cases, zero
failures/errors/skips and unchanged source. Source/config/receipt/log/XML bindings
were verified. These results supersede the pending statements at earlier dated
checkpoints for those exact sources. No operational dispatcher, cleanup
reservation, service/runtime or device-image pass is implied.

## November 8 — selected registration checks passed; device features unchanged

The separate source candidates passed on actual Python3.14.9 and3.11.15:
ledger1b47c95 (16 cases each), scope registry731e7ac (14 each), original scope
slot874d6bf (20 each), and repaired partial file-walker threadingfffa1b3
(22 each). Exact source/config/receipt/log/XML bindings were verified. Initial
walker failures (21 setup failures, then19 passes/2 legacy failures) remain
preserved; root-shape and legacy import fixes did not weaken native checks.

Cache/link forwarding11ff67b passed55 current-version cases; its actual3.11.15
run remains pending. Fresh-probe0d74d65 has9 new plus16 existing cases queued
sequentially behind it. These remain unpublished source candidates, separate
from this review branch's34b862e code. No selected result is whole-plugin, native
runtime, device or release qualification. No host/device/deployment changed.

Bot characters and host-local images remain unfinished. Remaining work includes
entry metadata/tree registration forwarding, original per-step/consumer plans,
six fixed native-operation and separate enumeration effects, shared quota and
reserved cleanup, production native/key/service wiring and physical delivery.
No upstream prerequisite was established for the remaining HMP integration.
Earlier pending checkpoints below are historical and superseded only for the
exact source/results named above.

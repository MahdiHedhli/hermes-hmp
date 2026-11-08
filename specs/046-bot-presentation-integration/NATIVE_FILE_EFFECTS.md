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

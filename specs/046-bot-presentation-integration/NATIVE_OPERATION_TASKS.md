# Native read/metadata/link operation claims

Status: dirty experimental implementation from `5439fee`; no tests or deployment.
The runtime-source file loop now uses typed read results, fixed consumption and
EOF ACK. This path is awaiting independent wiring review and causal tests; it is
not runtime/image qualification. Other native sites remain unfinished. Earlier
checkpoints below describe intermediate states. NATIVE_FILE_EFFECTS governs.

- [ ] NO1: reserve shared unreserved capacity for read/stat/fstat/readlink at all
  six remaining work sites: four shared StartupArtifactOwner methods, distinct
  DeclaredCacheReadOwner._read and
  RuntimeCacheProbeOwner._stat_known. Open stays on its reserved-close path;
  keep legacy reads distinct.
- [ ] NO2: preallocate exact attempt/result/consumer claims and raw slot, bind the
  actual original scope, descriptor/parent, arguments, code/step, count/effect and
  consumer allocation. Retain actual bytes/stat result before any result allocation.
- [ ] NO3: distinguish active native call from awaiting original consumer ACK.
  No work or close during active native entry. After return, only the held typed
  result claim permits read-only currentness checks for that original fixed
  consumer. It cannot open another work step or acknowledge another claim.
  Never implement this as an allow-late Boolean or arbitrary private callback.
- [ ] NO4: exact consumer ACK joins original attempt/result/raw object, current
  owner/scope/code/step and original actual progress. Retire raw bytes/stat refs
  only after that ACK; retain bounded category/length/debit/claim history. Failed
  ACK preserves unknown debt and known descriptor cleanup, not fresh work.
- [ ] NO5: migrate both cache diagnostic consumers with original typed plans:
  presentation_startup_cache missing-path observations (pass/path/ordinal) and
  RuntimeCacheProbeOwner._stat_known. Fixed stat-only sanitization may record
  reported_missing_for_original_stat_argument only under exact original exception
  type, primitive errno/name and held argument checks. No raw exception/traceback/
  message/path metadata retained. This is diagnostic DATA, not kernel proof or
  operational fallback. Each predeclared next stat has its own ordinal/cost.
- [ ] NO6: all other raised/ambiguous outcomes terminate collection; preserve
  actual known byte progress and reserved cleanup. No retry, reset or new allowance.
- [ ] NO7: causal all-site tests: wrong actor/primitive/foreign callback0effects,
  counter/admission/ACK drift, raw return before allocation failure, copied claim,
  wrong consumer/step, EOF, partial read, diagnostics wrong-name/errno/subclass,
  phase/ordinal replay, reentrant work/close, retained buffers and exact cleanup.
  Run current/floor and affected complete consumer regressions serially.

Independent contract review must settle the exact typed post-return currentness
API before operational wiring. A returned-value holder alone does not establish
result custody, quota, factory/runtime admission, or physical image delivery.
Directory iteration is a separate remaining boundary. Open/close source and tests
remain frozen in the prior candidate while this descendant is developed.

## Reviewed state and API contract

Independent read-only contract review accepted the following next implementation
route; it did not accept an implemented dispatcher or tests.

1. Keep `_native_scope_current` normal-work checks IDLE-only. Split original
   callback-free scope/material joins from each fixed work guard. The entry ledger
   shape may represent IDLE, ACTIVE, PENDING_ACK and FAILED; shape does not grant
   any phase. Use original preallocated phase/pending cells and closed identities.
2. A distinct `_native_result_current(owner, actual_operation, actual_result,
   actual_consumer)` permits only the exact original pending claim's fixed
   consumer. No arbitrary callback, success Boolean or caller-nominated code can
   authorize currentness or ACK. During ACTIVE, this helper also refuses.
3. Consumer identity must include original scope registration, step kind and
   identity, accumulator/metadata cell, before progress, expected ordinal and actual
   result backlink. The initial generic consumer tuple is insufficient and must
   become closed internal consumer types before operational integration.
4. Native read returns a private result holder; legacy read still returns bytes.
   `_file` threads that exact holder through digest/accumulator/source effects. ACK
   follows actual bytes being consumed into the original progress allocations.
   ACK actual EOF/count/cursor BEFORE later fstat/stat; separate EOF consumption
   from source-hash finish where needed. No next read while pending.
5. Metadata ACK follows capture of actual identity/mtime/size or transfer into the
   bounded original metadata owner. Readlink ACK follows target/count/record joins;
   bound retained link metadata to at most twice hop count times 4096 bytes.
6. Cache diagnostics lazily mint component claims from the original ProbeEffect
   or fresh-probe selected row/observation. First reported-missing ACK may activate
   only its distinct confirmation ordinal under the same quota. No eager all-path
   table. Both consumers handle a typed report, never reconstructed exceptions.
7. ACK verifies original attempt/result/raw object, native arguments and parent,
   consumer before-to-after actual progress. Retain the actual ACK allocation
   before callbacks; final pure joins precede retirement of raw references and IDLE.
8. Refusal retains failed result/lineage evidence. An explicit typed abandonment
   step is allowed only after the native call ended; preserve category/length/count
   and original claims while releasing owned payload references. It grants neither
   ACK nor fallback. Reserved close runs only after that failed/no-active handoff,
   never during ACTIVE or unresolved PENDING_ACK.

Implementation order: one complete fixed read+EOF+ACK path, then metadata, link
and both diagnostic consumers on the same shared ledger. Qualification must cover
all six sites; finishing one path cannot certify the whole operation boundary.

## Current first-path source checkpoint

RuntimeSourceReadOwner and DeclaredCacheReadOwner now have separate material-only
checks preserving the previous guard's original lineage/currentness joins while
omitting its explicit actor sample. Existing guards remain unchanged. The new
helpers are unused until reviewed and wired through typed pending-result checks.
Their transitive purity is under review; method naming is not proof.

The first complete read path targets runtime-source and declared-cache reads.
Shared package/artifact work still needs its own full material split, because
activation/selection helpers currently include additional currentness calls.
This ordering does not remove those callers or reduce the six-site requirement.

## Phase representation and material-callback checkpoint

The original entry now preallocates opaque IDLE/ACTIVE/PENDING_ACK/FAILED identity
markers plus current/result cells. Ledger shape represents metadata only; the
normal native-work gate requires the original IDLE marker and no pending result.
Scope registration retains the actual original phase allocation/type rather than
adopting a later module export. No result phase transition or ACK is wired yet.

Review found that the extracted material methods still reach lazy imports. Even
a cached import can invoke an import hook. They remain callback-bearing: pending
currentness must hold exact original operation/result/consumer across that work,
then finish with a separate import-free identity/material tail before ACK. The
existing import allowlist was not broadened for the phase representation.

## Pending-read currentness prototype

The unused pending-result tail now joins exact operation/result/consumer backlinks,
original attempt membership and pending phase, actual raw bytes/length/count,
original declared walk and its read-file cursor, and actual open descriptor. The
read-file cursor retains original digest/buffer/source/observation identities and
ordinal/remaining/before-count/pending-consumer cells. These are not caller success
flags. A held material callable/code/module/owner type is checked before invocation
and the import-free original-claim tail runs again afterward.

This prototype does not consume a read, update phases, ACK or retire raw results.
It requires independent review and real all-path/fault tests before use. The close
reservation now retains its original phase and refuses active or unresolved pending
results; explicit failed-result abandonment must clear pending ownership before
reserved cleanup. Existing open/close intermediate in-flight states intentionally
remain unreadable through ordinary entry metadata guards.

## Actual-return and constructor custody amendment

Review found coherent mutable-slot replacement could pass the first prototype.
The private return envelope now carries actual returned bytes, actual after-count,
original file step and exact result/ACK/progress/cursor cells. Pending checks take
that original envelope, not fresh values recaptured from slots after callbacks.
The producer must retain the raw return first, allocate/publish the envelope once
before callbacks and carry it through consumer ACK/abandonment; this is not wired.

Runtime/cache reader retention now captures material function/code/globals and
shared-file function/code in the original immutable scope. Fixed step construction
accepts only these two reader types and their retained pins. Material globals must
be the held module namespace. Per-file cursors/EOF state and next-consumer creation
are prepared DATA helpers, not operation admission or ACK. Their reference/type
ordering and construction custody are under independent review before use.

## Admission preparation checkpoint

Fixed step and consumer constructors now rejoin the exact original registered
walk/ordinal/declaration/cell/root and started state before and after callbacks.
The unused read admission helper validates original effect/cursor/descriptor,
latches original entry preparation and ACTIVE state before actor/result allocation,
and debits one unreserved attempt while preserving close reservations. Partial
preparation failure is retained and blocks work. Wrong-actor refusal is
non-consuming only while all original admission references/counts remain unchanged.

This helper performs no file read and is not called by current read paths. Its
original-operation return custody and failure boundaries remain under review
before integration. Raw-return capture, fixed append/hash/EOF ACK and explicit
abandonment remain incomplete; no full read path or operation quota is qualified.

## Admission leaf/lifetime closure amendment

Review required more than same-scope descriptor membership. The step now binds the
actual leaf-open result and validates the bounded original parent chain against
every declared path component, with directory ancestors and a non-directory leaf.
The fixed consumer must retain that same leaf. No ancestor or other file in the
same scope can substitute for it.

The original activation/continuation references are retained in the file step.
Import-free lifecycle joins reject owner failure/release/readiness drift and
activation/continuation retirement/root changes after actor callbacks before the
admission debit. Pending-result checks repeat those joins. These amendments are
under review; actual native read/ACK integration remains unwired.

## Caller-held operation amendment

Operation/result preparation is now separate from admission: the unused prepare
helper allocates original operation/result and immutable budget DATA without debit.
The caller must hold that exact operation locally before passing it to admission,
so an interrupted admission return cannot erase the producer's reference. A final
ready tail checks the same admitted operation, budget, phase, callee and arguments
immediately before the future fixed native call. The return envelope also pins
the consumer's original operation cell.

Wrong-actor nonpoisoning now requires import-free input, registration, original
walk/descriptor/cursor and lifecycle closure as well as unchanged ledger heads
and counters. Retirement or original-record drift follows sticky refusal. Actual
read dispatch/return/consumption/EOF ACK/abandonment remain unwired and untested.

## Optional fixed-read producer prototype

The shared read boundary has an optional typed-consumer path. Existing callers
still use its unchanged default route; `_file` does not construct or pass typed
consumers yet. The prototype holds the prepared operation locally before debit,
rejoins operation/callee immediately before literal native read, records raw bytes
before allocation and builds the original effect/count envelope before PENDING_ACK.
It returns the private envelope, never a bytes-compatible proxy.

Review found two failure issues: clean unadmitted actor mismatch must not poison
the shared ledger through abandonment, and raw-bearing envelope locals must not
survive in propagated tracebacks. Both were amended: clean unadmitted refusal
remains nonconsuming, producer/abandonment clear raw-bearing aliases, and typed
producer refusal is raised fresh outside the handler. These changes still require
review/tests. Fixed consumer/EOF ACK and complete abandonment qualification are
incomplete. No actual application route, deployment or read feature is certified.

## Unadmitted refusal scope correction

A verified exact actor mismatch before admission leaves the shared ledger and
read budget unchanged, but retires the current reader with a known failure. Its
original read/digest/cursor preparations remain retained as unconsumed evidence;
they are not rolled back or reusable. This path does not set unknown-read flags.
All other typed producer failures retain unknown outcome handling. This is a
source correction awaiting causal tests, not a resumable-reader guarantee.

## EOF accounting split (unqualified source)

Source-digest accounting now exposes a one-use `consume_eof` step bound to the
original empty-read record/count. Legacy `finish` invokes it when needed; future
typed consumers can invoke it before metadata work and finalize later with the
same count. Duplicate EOF consumption and copied final counts refuse. Five
causal fixture cases cover early consumption, duplicate refusal, copied-count
refusal, append after EOF, and EOF drift at the actual hash return boundary. They have been authored but not executed while the frozen native suite
is active. This does not wire native consumer ACK or certify the full read path.

Bounded review required EOF monotonicity across hash callbacks. Append now
refuses an established EOF, and hash publication rejoins the original EOF count,
consumed cursor, read-list allocation and latest observation/result. Review and
causal execution of this amendment remain pending; static checks passed.

## Single latched actor sample for the typed producer

Typed read admission now carries the original shallow owner/argument snapshot
across its actor sample after the preparation latch. The producer's earlier
legacy actor sample runs only for the unchanged legacy route. A mismatch is
nonpoisoning for the shared ledger only after the original owner snapshot and
typed input closure both rejoin; buffer or other owner-alias drift is sticky
refusal before native read. The affected typed path remains unwired and untested.

## Original accumulators before read admission

The typed file cursor now retains the original native SHA kind/update descriptor.
Its input tail rejoins the exact scope-owned buffer, current byte length and owner
aliases plus the same native digest kind/update before admission and after actors.
This closes between-step alias drift before IO; it is not a digest-content or
consumer-ACK proof. Source review and behavioral execution remain pending.

## Original source-read result custody

The optional producer envelope now carries the actual source-read allocation and
actual `observed_read` result captured at native return. Pending checks join that
original record/effect/index/before/after/length and latest original source-read
list entry. A later consumer must use those held values, not recapture a mutable
latest source slot after append/hash callbacks. The path remains unwired; this
adds no ACK or runtime authority. Static checks passed; review/tests pending.

## Fixed runtime-source consumer prototype (unwired)

The new fixed consumer accepts only a caller-held original runtime-source result
envelope. It feeds the exact returned bytes to the original source/buffer/SHA
accumulators, publishes a raw-free consumer progress allocation, rejoins pending
result/count/observation/progress, then acknowledges once and retires owned raw
result/envelope slots before returning IDLE. Actual empty EOF is consumed before
ACK, metadata work and source-hash finalization. Interrupted consumption/ACK fails
permanently, records bounded cleanup uncertainty and erases captured buffers; no
retry or extra allowance is introduced.

This prototype has no application caller and has not passed causal tests or
independent complete review. Declared-cache's distinct attempt/result globals and
all remaining operation sites still need their own integration. It is not a
completed reader or runtime/image capability.

Consumer review found and repaired three prerequisite gaps: original pending
result/buffer capture now precedes callback-bearing imports; actor eligibility
precedes the destructive consumption boundary; an original one-use consumer
slot is latched before imports/material checks/feeds, and duplicate or wrong-actor
refusal does not abandon another pending consumer. The owning attempt remains
responsible for cleanup even if callbacks corrupt its slot. Final ACK joins its
held token. Raw-bearing actor argument/snapshot locals are cleared on failure.
These changes remain unqualified pending review and causal tests.

## Runtime-source caller wiring (experimental and unqualified)

The runtime-source file loop now holds original step/envelope/commit values,
feeds each actual chunk once, checks the returned ACK/cursor/debit closure, and
consumes/ACKs actual EOF before metadata and source-hash finalization. Its own
failure handler abandons its actual returned envelope even when the consumer
refused before taking a consumption slot. Known returned byte count/category is
preserved when an ACK is interrupted after raw retirement. Legacy callers and
DeclaredCacheReadOwner's distinct attempt/result route are unchanged.

Existing runtime causal fixtures now forward the optional consumer argument and
mutate the real bytearray.extend C-return boundary for same-length corruption,
rather than relying on a bypassed legacy append helper. No fixture execution is
claimed; independent review and focused/all-path tests remain required.

## Causal coverage queued for the experimental runtime path

Twenty-four consumer cases are authored: eight normal/refusal/lost-result cases
and sixteen exact-line interruptions at eight representative post-ACK update
points, each for data and EOF. They check actual hit/kind, original ACK history,
raw/envelope retirement, cleanup and no post-failure EOF metadata work. This is
not every bytecode/store interruption and no execution pass is claimed. The
existing runtime-source fixtures and complete source-digest suite are selected
for qualification alongside them. The separate frozen cleanup suite completed
400 passed/12 failed; those failures remain unresolved and separate.

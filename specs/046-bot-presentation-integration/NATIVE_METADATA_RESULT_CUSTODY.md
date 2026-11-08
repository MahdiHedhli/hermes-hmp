# Fixed metadata custody and caller integration

This describes isolated, uninstalled source candidates on November 8, 2026.
The server/scanner implementation on this documentation branch remains
`34b862e`; these designs are not integrated or deployed. Current selected test
results appear in [FEATURES](../../FEATURES.md). Source tests do not establish
runtime, device, feature or release acceptance.

## Verified preparation and current unresolved defect

- Original metadata plans/resources/intents and constructor closure have scoped
  current/floor passes, preserved in FEATURES.
- `a19560a`:14 structural cohort cases pass on each supported interpreter.
- `a131932`:20 synthetic ACTIVE-state cases pass on each interpreter; these are
  guard tests, not actual native admission.
- `f47a1be`:29 original directory intent/admission/pending-return cases pass on
  each interpreter with source/log/XML evidence rehashed.
- `8f12da7`:45 selected synthetic native-directory/policy/ACK cases pass on each
  interpreter, including10 source-store interruptions. Production is unchanged
  from ACK candidate `520b08d`; source/evidence hashes were rechecked.
- Separate negative control `4072412`, with unchanged production, reproduces a
  lost producer return on both interpreters. Each original suite fails exactly
  one assertion as expected; private evidence proves actual injection, no caller
  receipt, pending raw/envelope retained, healthy ledger and preserved debit.
  These failures are retained as failures, never qualification passes.
- New ended-preparation/known-return cleanup source `b643f02` has finite review
  but its50-case descendant remains unrun. It does not solve lost producer
  returns, revoked lifetimes or partial-ACK discovery.

The candidate is not qualified for complete caller integration or deployment.
The positive matrix does not close the counterexample or remaining gates.

## Lost-return failure and repair requirement

A return-event exception can occur after the producer finally cleared its local
aliases but before the caller received its value. Pure timing probes and the
actual synthetic-descriptor control establish this on Python3.14.9/3.11.15.
The current result remains pending without a caller-held receipt. Merely looking
up a current stored envelope is not proof of the actual producer return, and
retrying the native operation is not a repair.

The repair must give the fixed caller independently held retirement custody
before effects, separate from normal result/ACK authority. A conditionally
reviewed proposal uses an original raw-free preparation marker, an original
owner-link allocation and a weak identity anchor to a pre-C raw-bearing capsule.
All owned raw/envelope/consumption paths must pass through the one detachable
link. Current marker lookup is not independent provenance. Capsule custody must
never authorize result consumption, ACK, renewed permission or native close.

Implementation has started in isolated candidate `b6b8322`. Its retained
`_MetadataResult` now keeps the raw/category/snapshot/envelope cells behind the
payload link, and `_DirectoryConsumer.consumption` resolves through that same
payload rather than retaining a separate raw-bearing list. The preparation
factory exposes the actual operation/marker/payload before native effects.
Compatibility accessors are DATA only: following their current links cannot
establish a producer receipt or independent caller custody. The legacy preparation
wrapper does not retain those original factory returns across native work.

The memory-only component has eight focused checks passing on each interpreter,
including an injected interruption after detachment, callback-bearing weakref
refusal and GC-disabled reclamation of a synthetic owned graph. These checks do
not establish reclamation in the actual metadata pipeline. The 58-case migrated
metadata/component regression is running with immutable source/log/XML binding;
no result is claimed yet. The fixed caller and its ended-call failure cleanup
are still missing, so the original lost-return defect remains open.

This repair is not accepted as complete. Required evidence includes the entire retained-root reference graph, coherent copy/foreign-link
refusal, original-actor and revoked-lifetime retirement, interrupted detach,
return-event loss, sanitized exceptions and GC-disabled ownership/reclamation.
Caller alias disposal can run callbacks and needs final original closure before
further work. No erasure guarantee covers independently retained foreign aliases.
This is local HMP work and an explicit release/integration gate; no deployed
host, real user message or data exposure was observed in these tests.

## Fixed producer, policy and ACK contract

1. Hold the actual original owner/scope/registration, declared walk/site/ordinal,
   descriptor allocation and fixed consumer before admission. A string, copied
   tuple, matching FD or reconstructed receipt supplies no authority.
2. Use captured native functions and exact result/error classes. Each fixed
   actor-check stage samples its captured PID/UID/thread once with original
   input closure before/after; no resampling repairs an observed mismatch.
3. Reserve original preparation before actor sampling; debit one aggregate work
   unit while retaining all close reservations. Publish ACTIVE before the fixed
   native call. Retain its actual raw return before callbacks or allocation.
4. Rejoin the actual return around snapshot/envelope construction. PENDING owns
   the original result while its ended native call has no in-flight pointer.
   No new work or descriptor close is admitted by a result merely existing.
5. Latch the actual pending producer return once, apply the fixed policy to its
   original snapshot/UID and retain the actual policy commit. Directory policy
   preserves type, ownership, set-ID and write/sticky rules. No fake stat_result
   or data-only identity tuple substitutes for that consumer.
6. ACK keeps actual return/commit through final closure, retires raw/snapshot/
   envelope and the raw-bearing consumption backlink, advances only the exact
   original cursor and then restores IDLE. Caller verifies the complete closed
   commit and drops its producer-envelope alias before further work.
7. An ACK marker alone is partial history. Failure preserves debit, attempts,
   markers and any cursor stores already made; no rewind, refund or replay.
   Only original held data/pointers are retired; foreign replacements survive.
   Outward errors are bounded, owner-attributed and do not forward original
   raw-bearing exceptions. Clean wrong-actor refusal must preserve rightful
   ownership and is distinct from drift or an unknown native outcome.

## Caller evidence and exact local prerequisites

The inspected `_file` directory loop still invokes `_fstat`, computes directory
identity and checks mode/UID from the returned stat object. The shared path also
uses `info.st_uid/st_mode` for configuration-specific parent checks. The current
consumer admits only original RuntimeSourceReadOwner/DeclaredCacheReadOwner
scopes. Configuration, tree and link policies require their own fixed consumers;
class-name similarity or a generic dispatcher is not a substitute.

`_finish_native_declared_walk` currently requires metadata cursor0, explicitly
asserting that the new plan remains unwired. The plan already declares initial
directory, leaf and final ancestor observations. Do not relax this check or
pretend a partially consumed plan completed. A migrated finish must require
all declared sites to have actual completed original ACKs and no pending result.
Do not skip old metadata calls by shrinking the plan or jump its cursor to the
end after file hashing.

The fixed caller must retain its actual prepared operation/consumer before
calling the producer and carry the actual returned envelope and commit through
policy/ACK. Its abort/lost-return path remains to be implemented and causally
qualified: it must preserve original debt and partial ACK history, retire only
independently held original data and never adopt a current replacement as a
returned receipt. Clean wrong-actor admission ends an uncharged intent; safely
releasing its owned preparation without rearming that intent also needs an
explicit reviewed path. These are local implementation requirements, not a new
upstream API blocker or a request to broaden permissions.

## Next fixed-caller implementation and acceptance

The next caller must obtain the actual operation/marker/payload factory return
before preparing/latching the consumer or entering the native producer. Its
original references stay in caller locals across producer return and exception
unwinding. Neither `result.custody_slot[0]` nor a stored envelope can nominate
replacement custody after the call. Temporary payload-cell tuples must not enter
operation, consumer, commit, ledger, failure or metadata-progress history.

Separate the two exit paths:

- Normal: hold the actual producer return through policy and ACK, prove the
  original closed commit, dispose of caller envelope/cell aliases, detach only
  the original payload, and rejoin current live authority before further work.
- Failure: prove the actual fixed synchronous call has unwound and that cleanup
  runs under its originally captured actor. This memory retirement cannot depend
  on a permission remaining live, cannot clear foreign links or rewind partial
  ACK stores, and cannot authorize native close, retry, consumption or new work.
  A mutable ended flag or matching actor tuple alone is insufficient proof.

Acceptance must inject the original producer return-event loss against this
actual caller, not merely invoke the memory helper with synthetic values. It
must also cover return loss after policy/ACK, early failure before admission,
revocation during the call, a wrong actor, replaced links/cells, partial detach,
retained failure/ledger roots, GC-disabled reclamation and bounded outward
exceptions. Native debit, cursor and ACK histories must remain independently
observable and unchanged except for stores that actually occurred. A detached
payload is never an ACK. The original failing control stays preserved.

## Full scope remains open

The [dated inventory](NATIVE_METADATA_SITES.json) records39 stat/fstat syntax
sites and source hashes against `8afe009`. It is review data, never runtime
permission. Revalidate it against any migrated source. Both distinct missing-
stat diagnostics must preserve exact native exception/errno/name handling;
EACCES/ENOTDIR and ordinary fstat failure never become missing/fallback authority.

Remaining work includes per-store/drift/foreign-slot/lost-return evidence, fixed
caller and every metadata/tree/link/diagnostic migration, all six operation
boundaries plus separate enumeration, original aggregate quotas/reserved cleanup,
complete startup/factory/service/key/runtime, CPU/RSS/deadline and physical
character delivery. The existing minimum-version60-second timeout remains open;
no deadline extension or narrower fixture closes it. Host-local chat images are
separate from this startup/character path and retain their own deployment and
physical acceptance gates.

# RGA-01e: registered Scope dispatch integration

Source inspected: HMP44b6d0442bee1b88739970dc02a9685040714b24, November11,2026.
Design and coverage analysis; no reduced path is enabled by this document.
This is the next coherent implementation unit, not new feature scope.

## Actual junction and prohibited recursion

The duplicated owner audit is visible at presentation_startup_artifacts.
_native_scope_current's _owner_guard(owner) call. That observation does NOT make
its generic callers eligible for a reduced branch. Keep _native_scope_current and
_native_walk_scope unchanged: registration shape alone is not caller custody.
Do not call presentation_native_metadata._closed_link_engine_origin from that
junction to bootstrap a replacement: the selector begins with registration
validation and risks recursion. Nine DATA projections alone cannot replace a guard.

The intended new route is a distinct fixed private link-execution Scope checker
at actual closed driver/resource/lifetime sites. Its inputs are the actual held
_LinkExecution and actual operation-owned resource, never a bool or owner marker.
Retain this literal function/code/defaults in the original engine dependency rows
and required-function roles before Scope construction; Scope.audit_record must
join that same early engine. Initial execution construction remains generic.
Only after the literal execution constructor return and its post-constructor seal
may resource/lifetime/driver sites use the new route. Extending generic open/read
internals later requires a separate fixed link-only route carrying the same actual
execution/operation; generic registration lookup must not silently become reduced.

| Existing call site in artifacts | Actual custody observed | Routing decision |
| --- | --- | --- |
| _register_native_scope:3385 | Literal newly constructed Python registration and held s/cell/root through publication; no link execution yet | Generic |
| _native_walk_scope:3415 | Forwards supplied registration; wrapper itself establishes no actual execution custody | Generic |
| _begin_native_declared_walk:3709 | Walk/progress read from mutable registration slots; general declared-file path | Generic |
| _new_native_read_file_step:4477,4519 | Runtime/cache owner families; later local step return does not make them link owners | Generic |
| _new_native_read_consumer:4551,4563 | Runtime/cache step and mutable walk slot; later literal consumer remains excluded family | Generic |

No listed registration is a C return: these are Python record constructors.
The new private route must authenticate execution class/constructor/row provenance,
then join literal execution.registration, blueprint Scope/source/runtime/Entry
and operation/resource to the same preheld objects. Pending/ACK/actual-return
custody is phase-specific; a proposed copied execution is not sufficient DATA.

## Root custody before any selectable checker

The original native driver/consumer must already hold the literal execution and
its registration from actual Python creation/return. A record freshly nominated from current mutable
owner/global state does not qualify. The dispatcher is private to that actual
held-call route, never a standalone shape-based entitlement or public fast flag.

Hold actual record.scope and scope.source_digest.binding first, using authenticated
native tuple storage. The binding supplies invocation/cell/started; started[5]
supplies the actual EntryOrigin. These are expected roots, not values nominated
from gateway_entry exports. Hold scope.parent, scope.runtime, runtime.inputs and
runtime.cell, snapshot owner/dictionary, original package and recipe binding
members, actual runtime plan/link and cache slot before callbacks.

Compare current EntryOrigin/OWNER/CELL/STARTED/owner invocation against these held
objects. Join actual record.lineage to both Scope.native_files and invocation's
native lineage; require ledger.scopes[index], Scope registration slot and owner
registration to retain the very same record. Join package/recipe/selection and
approval/activation nodes to the actual input members, rather than independent
coherent tuples. Current mutually matching exports/ledgers alone confer no root
custody. A fully caller-supplied coherent graph is DATA, not original authority.

Select only a literal function retained by the original early helper/engine
record. Check function/code/globals/builtins/default/keyword/closure state before
and after invocation. Do not add a supplied callback, boolean bypass, self-stored
success marker or permissive fallback. Call-site qualification is required before
wiring: register publication, generic walk, declared walk and reader constructors
must not acquire a reduced path merely because they pass a registration value.

## Complete live requirements

| Node | Existing component | Additional obligations before replacing the full guard |
| --- | --- | --- |
| Artifact owner | Scope/file and loaded-owner projections | Original Scope/cell/root/activation, failed/unknown/reading, held attempt/fact/count plus activation mirrors; actual pid/euid/thread equals context |
| Runtime source | Current source metadata and cache/snapshot projections | _runtime_seal count owner/Scope/bytes_read, io_slot owner, before/after/reads containers, guard/code/entry class, actual input plan/link, completion_attempt and _completing |
| Loaded shared owners | _loaded_owner_graph_mirrors | Exact input package/recipe/selection to the same approval/activation roots, original caller and function authority |
| Approval | _approval_graph_mirrors | Actual native descriptor/read closure and fresh original API module/function/code/spec-state rejoin equivalent to gateway_approval._api_state; do not add an API invocation |
| Cache | _cache_context_graph_mirrors | Preserve retain-time immutable row correspondence; fresh root/fact/cwd/rows identity and _seal checks, actual cwd/getter observation when required, existing owned-cache and sealed-fact branches |
| Entry | _entry_graph_mirrors | Actual retained EntryOrigin, invocation, STARTED/CELL, actor and callee authority; interpreter/native API projections do not replace live observations |
| Activation | _activation_graph_mirrors | Settled state only; capture-active bootstrap remains generic |
| Interpreter/native APIs | _interpreter_graph_mirrors and _native_io_graph_mirrors | Original early functions/primitives, required exports and only current actual observations already required by the generic path |
| File/read effects | _closed_file_graph_mirrors and _scope_file_graph_mirrors | Original ledger/allocation and current lifecycle/counters/unknown/failure/cleanup; representation-valid failed DATA grants no work |

Perform existing required external/native actor/getter observations and fresh API metadata rejoins before the final complete
pure mutable reseal. Any callback/GC boundary can invalidate earlier mutable
facts; do not cache verdicts. Preserve sticky failure, pending claims, descriptor
custody, work and reserved-close accounting, and cleanup on lost return/refusal.
Retain all existing generated metadata/closure primitive checks. Annotation
execution has its separately recorded actual-journey boundary; static absence
and class bootstrap are not whole-startup absence proof.

## Exact runtime-plan and cache obligations

A November11 reinspection distinguishes actual generic behavior from a proposed
extra requirement. runtime_files.plan_current checks the original entry/recipe/
plugin binding pointers, dependency/interpreter byte pointers, interpreter identity
and recipe/link schema joins. RuntimeFilePlan.pending is an immutable tuple
constructed by the original plan builder, not a mutable progress list. Retain
those exact values under original execution custody; do not invent a pending-list
state machine. Nested referenced owners, native namespaces and callable metadata
remain mutable and still require their existing fresh checks.

cache_context._rows computes immutable CacheInputData/PlannedCachePath records at
retain time. CacheContextOwner.current_binding does not recompute _rows. It checks
current actor context, performs _seal, calls the original current getter and
_location only when requires_cwd is true, rejoins the original cwd value, performs
_seal again and returns the same held fact. The replacement must preserve _seal's
actual mutable snapshot/input/root/module/ready/failed/retired/fact/cwd/rows joins,
getter metadata and plan_current obligations. It must not add per-call cache-path
recomputation or new native/API observations just because the retained records
contain those concepts. Immutable correspondence reuse does not reuse a mutable
success verdict or relax any existing consumer's actual cache validation.

### Scope-guard phase, not every cache API

The actual replaced StartupArtifactOwner._guard runtime branch calls
EntryFileSnapshotOwner._pure_current/_pure_lineage and CacheContextOwner.
retained_binding/_seal. Its owned cache source checks also use retained_binding.
Those routes do not call CacheContextOwner.current_binding, _context or getcwd.
The new Scope body must not introduce those calls. Preserve native actor checks
already required by the actual owner/activation/Entry path, and fresh getter
metadata checks, without adding an unused getter invocation.

There are two distinct cache objects. _cache_context_graph_mirrors handles the
pre-IO CacheContextOwner. Scope.cache, when present, is the different mutable
startup_cache._CacheSource; it can coexist with a link RuntimeSource through
retain_from_cache_entry. Do not assume it is absent from the real linked path.
The complete body must preserve source_current/owned_current's actual source,
entry/inputs/cell/plan/context-fact joins; paths tuple; before/after list1; effects
list bounded by2*paths; each _ProbeEffect source, phase/index, attempted/returned
booleans, unknownFalse and count tuple3; and optional _Missing path/index/
ancestor tuple2/native identity tuple5 shapes. Owned source must equal Scope.cache,
its input io_slot must hold the same owner and Scope.expected must be plan.pending.

Retain the runtime _runtime_seal count owner/Scope/bytes_read and io_slot joins,
source guard/class/code identity, before/after/count list1 and reads list. Snapshot
completion requires the original completion_attempt tuple4; _completingFalse
requires no attempt on snapshot/activation, while True requires the same original
attempt on both. Recheck actual Entry/recipe/package/activation identity joins.

The post-fact path is not optional: runtime fact tuple5 and _LinkTargetObservation
must retain original owner/Scope/source/before/after/count, reads must have2*hops,
and both historical _link_reads_current predicates remain required. A cache fact
also retains seal_cache_observation/_cache_seal_mirrors obligations for original
before/after passes, phase/counts/effect order/results/descriptors and native finish
histories, plus final owner._cache_fact. Authenticate any historical helper from
its original Scope-owned startup-probe origin and actual held call metadata.
First-prefix factNone evidence does not qualify a later post-fact recheck.

## Required causal acceptance

1. Reach actual original success and actual new dispatch, not an earlier generic
   refusal. Witness the literal caller roots and retained callee at dispatch.
2. Reject coherent registration/Scope/source/input/binding and current Entry-root
   grafts against the original caller-held roots before invoking the reduced graph.
3. Cover owner/runtime/cache/API/interpreter/activation/descriptor drift, revoked
   roots, callback/GC-time mutations, changed checker code/defaults and lost return.
4. After failure prove no later native work, registration, read or ACK; independently
   verify private sticky state, custody, accounting and descriptor cleanup.
5. Compare generic and new paths under the same real fixtures on minimum/current
   Python. Preserve complete generic/non-native behavior and all existing checks.
6. Run the unchanged original native60s test alone on the exact candidate. Passing
   prefixes, monitoring overhead and timeouts are not complete acceptance.
7. Desktop character delivery, signed physical images, platform/provider and
   release qualification remain separate. No installation is authorized by tests.

## Independent design review

Read-only character_custody_review accepted this route/coverage contract, with the
API precision above corrected against gateway_approval._api_state. That function
checks hermes_constants module/function/code/file/spec/origin/loader state; it does
not call get_default_hermes_root. The optimization must not introduce that call or
new runtime API capture. This is design acceptance only; implementation and actual
call-path qualification remain unchecked.

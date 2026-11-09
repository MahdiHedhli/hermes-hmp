# Original link-policy factory capture

November 9, 2026. LP2 design following the separately frozen LP1 source
`0d5d86210dd1f2a163ace57effe5882c3a47e507`. This does not claim implementation
of the entry-origin extension or native link operations.

## Anchor and admission limits

Use the actual `_ENTRY_ORIGIN = _capture_origin()` allocation at the bottom of
`hmp_startup/gateway_entry.py`. It occurs before `GatewayEntryOwner.start`, its
owner constructor, interpreter observation and native bootstrap callbacks. The
existing actual `started[5]` binding independently retains and rejoins this
original entry object. A policy factory imported later at `_retain` cannot
establish its own provenance by matching the current module export.

Extend that early entry-origin return with the actual immutable link factory
origin. Thread precisely the same object into the original `_NativeFileLineage`
created by `start`, then through `SourceDigestContext.native_files`. Both the
entry origin and lineage getters must rejoin against the independently retained
object, not equal/copied tuples. Missing origins cannot admit link work.
Non-link callers must preserve their existing constructor compatibility and
must not trigger a later cold import that nominates a new origin.

The inspected import graph has no unavoidable eager cycle:
`gateway_entry -> activation`; policy imports `startup_artifacts -> activation`;
`runtime_files -> gateway_package -> recipe/selection -> startup_artifacts`.
However, imports execute module, class and standard-library initialization and
may perform import-system I/O. Do not describe early capture as effect-free.
This widens the pre-bootstrap trusted graph. Its complete fixed module inventory
and source binding must remain covered by later package/runtime/factory admission;
early capture grants no native bootstrap, listener, key, image or tool permission.

## Original capture and return sequence

1. Before policy/type imports, hold the original entry module/dictionary,
   `GatewayEntryOwner.start` classmethod/function/code/globals, `_require` and
   error class. Rejoin those originals after imports before allocating the
   extended `_EntryOrigin`.
2. Before any policy helper or constructor, hold the actual policy ModuleType,
   dictionary, canonical module-registry entry and fixed factory/dependency
   functions: `_new_policy`, `_need`, `_parts`, `_policy_tail`, `_directory`,
   `_leaf`, `_cursor_tail`, `_sites`, `_start`, `_action`, `_advance`, `_outcome`.
   Retain function/code/globals and any relevant default/closure dependencies.
   Calling a current exported helper to validate itself is not provenance.
3. Retain the original policy/cursor/blueprint/site/plan and native
   `RuntimeFilePlan`, `ExecutableLinkPlan`, `LinkHop`, `ExpectedArtifact` types,
   exact module/export bindings, fields/member descriptors, constructor/code/
   globals/`_tuple_new`, bases and read/write dispatch. The present native plans
   are plain NamedTuple DATA; no independently retained native type-module
   origin was found that would justify adopting those exports later.
4. Bind actual owner, runtime source/entry inputs/cell, literal link plan/hops,
   original paths/targets/destinations and target expectation, uid/mode/text-byte
   budget, exact context/bound and actual native lineage. Retain owner/activation
   dictionaries and vacant slots before any callback. A matching DATA blueprint
   cannot substitute for any of these actual returns.
5. Invoke the held factory for each fixed original hop and final target. Rejoin
   namespace/code/type/dispatch bindings by dictionary/tuple primitives after
   **each** helper or constructor return, before another helper or getter. The
   factory's local dependency capture must precede its first `_need`/`_parts`
   call; capture after path decoding could adopt a callback replacement.
6. Require exact actual constructor-return fields bound to the held original
   inputs, then use held validators and reseal owner/activation vacancies. Hold
   the literal origin return locally across the outer Scope constructor. Verify
   the actual Scope fields and origin object, then rejoin original blueprint/
   namespaces/vacancies again before publishing owner/activation fields or
   registering native scope.

This does not replace full mutable-parent and original actor/argument audits
before each actual native effect. It adds no operation, debit, result, ACK or
admission token. Keep one bounded blueprint per original declared link plan and
allocate only the active path's native sites; do not retain quadratic path-prefix
inventories or share a reusable permission witness.

## Causal evidence required

LP1 follow-up source now captures local dependencies before path decoding,
rejoins after the first helper and constructor, and seals after the held final
validator. Four new controls mutate need/tail/parts/constructor at the actual
first path-helper return and require zero foreign calls. These are controlled
DATA-return observations, not independent native-origin qualification.

LP2 still requires original export/helper substitution **before** capture;
same-function code and native module/member/dispatch substitution; later policy
constructor changes; copied plan/hop/target and owner/activation slots; lost or
copied blueprint return; Scope origin substitution/coherent registry copy;
foreign-slot preservation; and no descriptor/native/debit/scope publication.
Cover one and eight hops plus target, before/after/recheck, and supported no-link
callers without inventing a zero-hop executable-link plan (the current native
contract requires one to eight). Run meaningful existing constructor/entry/
native lifecycle regressions on current and minimum Python after integration.

Full link native result custody, consumption/ACK, literal finish and cleanup,
remaining enumeration/other owners, service/runtime/device/release qualification
are separate open tasks. No live deployment or settings change is authorized by
this source document.

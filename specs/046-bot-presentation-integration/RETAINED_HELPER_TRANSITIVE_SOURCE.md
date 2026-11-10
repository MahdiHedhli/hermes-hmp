# RBH-03: retained-only source dependency review

Status: source inventory, selection helpers and activation static projection
are implemented. Complete transitive custody and audit consolidation remain open.
These changes add runtime integrity checks, not availability gates. The actual
record now covers four modules, thirteen classes and fifteen functions; same159
selected cases pass on both runtimes, including24actual publication faults.
Source review found no blocker in the bounded extension. Later approval/import,
mutable approval/entry state and remaining descriptor/dispatch/primitive closure are not
qualified by that result. No audit has been removed or new target module imported.

Reproduce without importing HMP or reading host configuration:

```sh
python tools/compat/retained_helper_source_census.py
python tools/compat/test_retained_helper_source_census.py
```

## Retainer refusal boundary correction

Before adding the shared artifact helper closure, actual final-publication tests
reproduced changed `ArtifactObservationError.__init__` dispatch while refusing that
very drift. Both cases failed on the preceding source. The initial native-refusal
correction then passed 174/175 selected cases; the remaining first-publication
owner-subclass case exposed `vars(owner)` before exact owner-kind refusal.

`StartupArtifactOwner._retain` now preallocates one private actual typed error per
attempt with held native `BaseException` allocation/init/dictionary operations.
Its message is fixed and `failed_owner` joins the actual original owner through
the held native dictionary. Every local explicit or require/need guard raises
that same private refusal without invoking a mutable subclass constructor. The
original owner's native dictionary descriptor is held before callbacks; sticky
failure is written only after actual dictionary identity rejoins. All final owner
dictionary reads fence the original class first and use the held native getter.
Native traceback/context/cause descriptors clear earlier rejection state before
the final raise outside the handler. No error is cached on a long-lived owner.

Thirty-eight one-positional-argument, discarded-value `_require`/`need` statements
are exact-True inline guards. Conditions evaluate once in the same order. Static
independent AST comparison found 36 unchanged and exactly two intentional
exact-class/native-dictionary strengthenings. Original helper alias/code checks
remain. No parent or retained recipe/package audit was omitted.

Same205 selected tests pass on both Python versions with unchanged matching
source maps/case sets:134local,40actual publication faults,1early-entry and30legacy
artifact/constructor cases. The40 faults retain zero foreign calls, new work,
reservation change, later registration or successful retainer return. Sixteen
artifact error/owner constructor/code/getter/setter/property/subclass controls
also witness the native error type, actual owner, fixed args, cleared context/cause
and native failed flag. Dictionary-property controls use a real compatible owner
subclass; direct reassignment of a class's protected `__dict__` is not claimed.

This repairs the reproduced retainer failures only. Nested helpers outside
`_retain` still have ordinary error construction. No complete artifact/helper
closure, normal/native timeout resolution, service/phone image or release
qualification is inferred. No host or device was changed or deployed.

The inventory pins seven source files and enumerates 22 explicitly selected
functions, their lexical global reads (including comprehensions), call
expressions, local imports and attribute/subscript stores. It refuses missing or
ambiguous definitions. It does not infer a complete call graph, resolve dynamic
dispatch, prove purity or establish original runtime provenance. Calls appearing
in an untaken branch are included. Absence of direct stores does not exclude
mutations through a called function, descriptor, constructor or error path.

Four offline causal tests pass on Python 3.14.9 and 3.11.15: inspected top-level
and function exceptions are never executed; comprehension globals remain distinct
from locals/imported locals; both conditional branches and nonlocal stores remain
visible; missing/duplicate definitions refuse. Both runtimes produce identical
inventory JSON for the current source bytes. These four checks qualify only the
inventory tool, not startup, transitive custody, images or release.

## Source-confirmed retained path

| Caller | Success-path dependency requiring original provenance |
| --- | --- |
| Package retained binding | Local require; activation retained scope; selection retained binding; descriptor closed helper; shared recipe comparator and nested recipe retained binding for recipe-derived manifests |
| Recipe retained binding | Local require; activation retained scope; selection retained binding; approved recipe; descriptor closed helper; expected-artifact validation |
| Selection retained binding / approved recipe | Local require; activation retained scope; descriptor closed helper; approval binding when an original approval parent exists |
| Approval binding | Function-local import of approval owner; retained binding by default; current-binding branch exists but is outside this retained-only path |
| Approval retained binding / closed custody | Original seal; descriptor closed helper; local require; original receipt/read-effect types and live fact |
| Approval seal | Activation retained scope; root API metadata check; entry retained binding; entry comparator; local require |
| Entry retained binding | Activation retained scope; native ledger shape; local require; original invocation/entry/native types and live cells |

`_api_state` compares the retained native root API function/code/module/spec/loader;
it does not call that function. Approval `load`, selection `_guard`, activation
`current`, entry `start` and all IO/model/provider operations remain outside this
retained-only path. Exception construction is a separate dispatch boundary and
must be accounted for when claiming refusal-path provenance.

The artifacts engine already captures selected imported classes/functions, but
that is not proof that every external function's globals or late imported module
values are original. An existing pin may be reused only after demonstrating its
literal early-root binding and coverage of the exact function/code/global alias.

## Mutable state prevents whole-namespace freezing

Approval's `_OWNER`, `_CELL`, `_ROOT`, `_FACT`, activation's `_ENTRY_OWNER` and
`_ENTRY_CELL`, and entry's `_OWNER`, `_CELL`, `_STARTED` legitimately change as
owners allocate. Entry `_ENTRY_ORIGIN` is assigned after the early capture call
returns. Freezing their early values or namespace cardinality would reject normal
startup; simply ignoring their semantics would weaken the original live joins.

Activation now implements the fixed static-export projection for exactly its two
live values. Their keys and full namespace cardinality remain checked; every other
value stays pinned. Original `_retained_scope` and refusal-constructor code/defaults/
closures, class/member/base snapshots and defining aliases are held. It does not
freeze live allocation values or treat DATA currentness as an owner verdict. Actual
normal-entry and operator/publication paths pass; a unit causal accepts changed
DATA yet freshly refuses a mismatched cell through the original validator.

The remaining candidate contract for approval/entry is a fixed static projection:
hold exact original module/registry/namespace identity, function metadata,
referenced static aliases/constants and class/member/base dispatch provenance.
Keep the existing original retained bodies responsible for fresh mutable-cell
joins. Every omitted mutable or late key needs an explicit classification and
live validating caller; arbitrary namespace exclusions are not acceptable.
Primitive, local-import resolution, nested dispatch and exception paths must be
covered before calling this a transitive execution proof.

Do not add a second unbound inspection packet and treat it as authority. Extend
the actual early-parent binding and all three final inline DATA seals together,
or establish an equivalently original existing chain. Verify import ordering:
entry's owner class exists before its bottom-level early capture, but approval's
import back to entry must not introduce an initialization callback or native IO.

## Required implementation and acceptance

1. Review an explicit function/class/static-export list and mutable/late-key table
   against the exact pinned source. Resolve artifact descriptor subcalls separately;
   the 22-function inventory is a review boundary, not an exhaustive closure.
   Artifact's native closed path specifically continues through
   `_native_descriptor_closed` → `_native_descriptor_opened` →
   `_native_file_allocation_original`; the last two are absent from that inventory.
   Refusal-path constructor dispatch must remain safe even when the constructor
   itself is the changed object detected by a final seal.
2. Bind that projection to the actual early original root, before callbacks. Rejoin
   literal identity after callbacks and inline at final publication. No cached
   currentness verdict, per-call result or tuple shape grants an omitted audit.
3. Test code-only and export drift at each late helper/import, mutable-cell changes
   that must refuse versus legitimate allocation that must succeed, copied packets,
   changed descriptors/classes/builtins, callback windows and original cleanup.
4. Only then implement RBH-04's same-call recipe consolidation. Preserve direct
   validation on unmatched/legacy paths and the full original binding comparison.
5. Qualify complete normal/native traversal under the unchanged deadline on both
   runtimes. The existing full native timeout remains unresolved.

# RBH-03: retained-only source dependency review

Status: source inventory implemented; original transitive custody and audit
consolidation are not implemented. No runtime validator or availability gate
changes in this increment.

Reproduce without importing HMP or reading host configuration:

```sh
python tools/compat/retained_helper_source_census.py
python tools/compat/test_retained_helper_source_census.py
```

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

The candidate contract is a fixed static-export projection for these modules:
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

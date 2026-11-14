# Annotation execution boundary for RGA-01d

Decision: November 11, 2026. Source base07be1ad with the pending collections
primitive checks. Read-only independent review agrees with the distinction below.
This document neither removes a predicate nor activates a reduced audit.

## Actual dependency

The nine fixed graph components in presentation_startup_artifacts inspect native
shapes, fields, module/function/default/closure metadata and current dictionary
contents. A direct AST call inventory finds no project-name calls in those nine
bodies. Attribute calls still need their exact native type/descriptor guards;
the inventory alone is not a transitive call proof or execution result.

The inspected startup/presentation source bodies contain no direct calls to
annotation functions, evaluated __annotations__, get_type_hints/get_annotations
or inspect.signature. Transitive behavior still requires the journey proof below.
The only annotation-function references in this candidate retain/check raw
metadata. Calling an already-defined record constructor does not itself evaluate its
annotations. Class definition/typing bootstrap is a separate phase and may invoke
annotation machinery; no whole-startup absence claim is made.
This statement is confined to the inspected fixed path, not the whole host process.

On the pinned Python3.14.9 source, typing._make_eager_annotate eagerly constructs
checked_types. Its returned function gives that same dictionary to VALUE and
FORWARDREF callers. STRING invokes lazy annotationlib.annotations_to_string(types).
The previously recorded generic 'legitimate cache evolution' concern is not a
shown required behavior here. Do not invent an allowance for changed captured
dictionary contents; retain all current exact-key/cardinality/value predicates.

## Required proof before final dispatch qualification

1. Preserve existing generated metadata, native primitive, raw member, code,
   default, closure and shallow dictionary-content checks at all consumers.
2. Complete a fixed-call inventory including actual selected actors and their
   transitive/dynamic call sites, not merely an absence-of-name search.
3. Observe original annotation function code and the original lazy STRING
   evaluator entry during the actual final-graph/native journey. Use observer
   traps/counters, never replace the evaluator with a passing stub. Prove zero
   calls in that journey; an early stop or timeout proves only its reached prefix.
4. Introduce no dynamic annotation/callable/getattr nomination in the new graph.
   If a path does execute an evaluator, leave that path blocked for a specific
   dependency-closure review rather than claiming its execution is qualified.
5. Treat deep annotation execution as conditional on actual dependency, not a
   new prerequisite for implementing the otherwise complete coherent DAG unit.
   Do not label annotation execution closure complete on this decision alone.

## Next coherent implementation boundary

Establish original Scope.parent, runtime.inputs and actual entry/STARTED/CELL /
lineage/callee roots before selecting a held fixed graph. Complete all live owner,
approval, activation, entry, cache, interpreter, descriptor and actor predicates.
Perform external/native actor/getter observations first, then a final pure complete
mutable reseal after callbacks. Preserve sticky failure, custody, accounting and
cleanup; generic APIs remain full and there is no permissive fallback.

Qualify actual generic-versus-DAG dispatch with coherent whole-root/Scope/source/
registration grafts, stale/revoked roots, late callbacks/GC/function/default changes
and zero later native effects after failure. Then run the unchanged native60s
acceptance alone. The last dated native run fails; no replacement pass is claimed.
Character delivery, physical device and release qualification remain open.

Evidence inventory is retained privately at
/private/tmp/hermes-rga-fixed-call-inventory-current-20261111.json, with source hash
and exact function line ranges. It is static evidence only; actual journey proof
is an unchecked task.

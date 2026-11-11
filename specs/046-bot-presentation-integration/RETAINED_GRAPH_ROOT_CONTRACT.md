# Rooted retained-graph audit contract

Source inspection: November 10, 2026, executable source
`4409364051f629afab9ea890922d5632a7e89e5b`. Design checkpoint only;
no fast path is implemented or qualified by this document.

## Existing anchor and excluded shortcut

`presentation_link_path_policy._LinkScopeBlueprint` retains eight fields:
owner, runtime, context, lineage, origin, plan, link and rows. It does not
itself retain a package binding. A blueprint shape match, scope registration
ledger membership or mutually consistent mutable owner fields cannot establish
that a proposed retained graph is the original graph.

There IS an existing package anchor to investigate before adding a carrier:
`hmp_startup.entry_files._Inputs` is the original sixteen-field entry-input
record. Positions 4 and 5 retain the package owner and package binding;
positions 2 and 3 retain recipe owner and recipe binding. Artifact `_retain`
already joins the actual runtime-input pointer to the runtime entry dictionary,
its root cell, original runtime plan and source owner. This currently happens
AFTER a complete `_source_current` and a runtime-guard call. It is not permission
to omit either check, or proof that a late copied input record is authentic.

`SourceDigestContext` instead retains entry, entry binding, interpreter,
activation, effects and native lineage. It does not independently retain the
package binding. Its entry/startup/lineage joins remain necessary but cannot
substitute for the entry-input package and recipe joins.

## Next implementation task: RGA-01

At the actual original input/publication boundary, bind the exact original input
record and package/recipe binding pointers to the existing early-owned roots.
First determine whether the current original runtime-entry/root joins provide
this custody across EVERY intended consumer; do not add a new record solely
because a blueprint lacks a field. Reject coherent replacement of input, source,
Scope, registration and mutable owner mirrors before any reduced parser.

The selected audit may reuse only immutable schema/document correspondence that
was validated at that original boundary. It must freshly inspect all live owner,
activation, root, scope, retirement, failure, unknown, ready, reading, buffer,
context, counter, descriptor, read effect, receipt, namespace, spec, function,
default and closure state. Retain native exact-type/key fences before field or
mapping access. Derive the actual fixed callee and primitive provenance from the
early-held record, never from a supplied callback or a current export alone.

Audit before AND after the package guard and every other actual callback that
can intervene. A prior success, equal copy, self-stored marker or cached mutable
verdict cannot satisfy a later seal. Standalone generic package/source/recipe/
selection/approval APIs remain complete. Pre-publication and non-native paths
retain their complete validation; malformed or missing native roots refuse,
without falling back to a permissive path.

## Acceptance and limits

- Causal controls must reach the actual reduced-parser dispatch, not merely an
  earlier generic refusal. Include original success, copied inputs/bindings,
  coherent owner/Scope/registration graft, field/getter drift, revoked or stale
  roots, callback-time mutation, changed counters/read effects and lost return.
- Native work, descriptor effects and registration must not advance after a
  custody failure. Check cleanup and private refusal state independently.
- Run matching focused regressions on actual Python 3.14.9 and 3.11.15, then the
  UNCHANGED original native traversal deadline of 60 seconds, alone. Diagnostic
  monitoring and inclusive timings are not acceptance or an additive cost model.
- The latest original native receipt `/private/tmp/hq-n3qun25h/receipt.json`
  failed with TimeoutExpired at 60 seconds. The later approval profiling receipt
  `/private/tmp/hprof-9e_liiqi/receipt.json` is diagnostic only. Desktop character,
  full startup, integration, physical-device and release qualification remain open.
- No installed host, image service, grant, provider, device build or release is
  changed by this plan. This rejects a proposed shortcut; it does not establish
  an exploitable deployed incident.

## RGA-01a: explicit input-member fence

The native artifact retainer now compares the actual retained entry input's
package-binding members against the source package-binding members, including
all four nested selection members, before policy capture. Exact tuple widths
precede indexed reads. Fresh binding tuple containers are accepted when they
retain the same original members; tuple container identity is not authority.

The 12-case actual retainer-prefix control checks original and copied valid
bindings reach the next boundary, while foreign/short bindings and each of the
eight replaced original members refuse first. It deliberately stops both valid
controls at that boundary; neither is a complete successful retainer test.
All cases verify failed-owner cleanup, no Scope publication, no new native
work/attempts/registrations and no foreign binding hooks. This is an explicit
custody prerequisite, not the reduced graph audit or end-to-end performance fix.
The full generic source/runtime checks remain. Remaining root provenance,
post-callback joins and reduced-dispatch causals are still required by RGA-01.

## RGA-01b: hold source identity across callbacks

The retainer now holds the literal original package-source pointer after the
RGA-01a member fence. Each `link_rejoin` joins it to the actual runtime inputs and
held package-binding containers before and after the parent origin checker.
Both final raw publication windows also require Scope.parent to be that source.
Original-source identity is checked before indexed source access, so a foreign
replacement cannot nominate a getter. No late helper is added to these joins.

Twelve additional controls replace the source with an equal source copy, a source
with a copied binding container, or a foreign object at four actual caller sites:
the first line after blueprint factory return, the first caller line after parent
checker return, and each final raw publication window. The test asserts actual
frame writeback, exact outer error/failed owner, sticky failure, no foreign hooks,
no later registration or successful return and unchanged native ledger. These
are negative prefix controls, not arbitrary asynchronous mutation/atomicity,
successful native traversal or permission admission evidence.

The first failed run overmatched AST conditions before exercising these controls;
the second reached all controls but failed a witness that assumed a not-yet-set
registration attribute existed. Both failed receipts remain private. The fixed
24-case current-Python run passes. Broad final regression is recorded separately.
Independent read-only source review found no concrete blocker and confirmed the
caller-line scope; it did not execute tests or independently rehash the receipts.

RGA-01b does not close RGA-01. The actual original-source/Scope/registration joins
at every intended native consumer, complete fresh graph implementation,
post-callback mutable checks, original native60s and physical/release gates remain.

Final RGA-01b regression: matching626 pass on actual Python3.14.9 and3.11.15,
source unchanged within each run, zero failures/errors/skips. Receipts:
`/private/tmp/hq-n_7pb45o/receipt.json` and
`/private/tmp/hq-qpyxx6k0/receipt.json`. The original native traversal is evaluated
separately; these regression passes do not close its deadline or full feature.

Fresh original native gate `/private/tmp/hq-yj2pkdxk/receipt.json` fails with
TimeoutExpired60s, source unchanged. Last original progress checkpoint event4
at48.82648s:44 observed/typed, one retired capsule, work963/reserved0. No earlier
setup refusal, skipped traversal, deadline change, speedup or full acceptance is
claimed. The original test was run alone after both regression suites settled.


## RGA-01c: native consumer carrier decision — November 11, 2026 UTC

Read-only source and independent review on executable source
`53e09183849f893e6c04c344a180ff13963767a8` identify the existing carrier:
original resource or consumer -> `_LinkExecution.registration` -> actual
`_NativeScopeRegistration.scope`. The immutable Scope's parent (field 5) retains
the literal original `_PackageSource`; runtime (field 6) retains `_RuntimeSource`
and its original `_Inputs`. The blueprint's runtime must be that same runtime.
The RGA-01b publication joins establish the source pointer at Scope construction.
No new early blueprint field or self-stored source-token is selected merely
because the blueprint lacks a package binding.

This is a source-level carrier decision, NOT completed runtime custody proof or
an enabled reduced audit. `_resource_tail` and `_lifetime_tail` currently call
full `_engine_origin_tail` before `_execution_mirrors`. Moving a reduced checker
into that position would consume a proposed execution before original-root proof.
Moving `_execution_mirrors` first is also insufficient: it calls policy helpers
and validates mutually consistent mirrors, rather than independently selecting
the fixed callee from the early native origin.

Implementation order for RGA-01 is now concrete:

1. At the actual native consumer, establish original owner/Scope/root-cell and
   native registration's ledger/index/slot, using exact native tuple fields and
   the existing independently anchored closed selector before any schema
   omission. Hold the actual original Scope, source, runtime and entry-inputs.
2. Join Scope.runtime, blueprint.runtime, runtime.entry's actual `_inputs` and
   original entry root-cell. Join package/recipe bindings and nested selection
   members to those original inputs; matching copies are not independent roots.
3. Authenticate the fixed graph-audit function and immutable schema/layout from
   original early helper/engine rows. Do not add caller-supplied trusted-source
   parameters or a reduced fallback to the generic APIs.
4. Implement the rooted audit's complete mutable-state predicates. Keep actor,
   activation, package, recipe, selection, runtime, descriptor/receipt, ledger,
   cache/completion, namespace/function/default/closure and failure-state checks
   fresh. Reseal original roots and mutable state after every callback; preserve
   final pre-effect checks. No currentness result survives to a later call.
5. Exercise the actual dispatch on both supported interpreters, then the
   unchanged 60-second native gate alone. A static carrier review is not a pass.

Required causal cases include original successful dispatch; equal execution,
blueprint/runtime/input copies with matching owner mirrors; coherent Scope/source/
input grafts; wrong ledger registration/index/slot; copied original package or
recipe members; post-callback source/input replacement; mutable failed/unknown/
reading/count/close/completion drift; late function/default/closure replacement;
and lost return/cleanup. Refusal must precede any later native effect or
registration. Existing generic validators remain complete and tested separately.

Independent read-only review agreed that the existing Scope is the carrier and
identified the root-first boundary and coherent-copy counterexample. It neither
ran these new dispatch causals nor certified an implementation. No executable
source, installed host/device, permissions or native deadline changed here.

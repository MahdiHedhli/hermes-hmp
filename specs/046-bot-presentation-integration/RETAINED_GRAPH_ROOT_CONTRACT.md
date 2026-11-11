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

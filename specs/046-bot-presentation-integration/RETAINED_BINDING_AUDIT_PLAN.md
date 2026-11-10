# Same-call retained recipe audit consolidation — prerequisite review

Status: selected-helper DATA component implemented as RBH-01; early-root
integration and audit consolidation remain unimplemented. This is not an
authorization shortcut. See SELECTED_RETAINED_HELPER_ORIGIN.md.

The actual EntryFileSnapshotOwner._pure_lineage calls the recipe retained-binding
validator directly and then the package retained-binding validator. For an exact
recipe-derived package, the latter freshly invokes that same recipe validator and
compares its complete binding. The nested audit is later, and this validator has
no sticky failed/uncertain assignment. This differs from activation-current
validation, whose omitted early call changes uncertainty behavior.

Before replacing the first recipe call, prove an independently held ORIGINAL
package helper and nested recipe helper, including actual function/code/globals/
defaults/keyword defaults/closure where applicable. A current method export,
matching returned tuple, callback flag or caller boolean is insufficient. A
replaced package method could return old binding DATA without running the recipe
audit; the existing independent direct call must not be removed on that basis.
Locate existing early EntryOrigin/parent/helper pins before adding new fields.
If absent, add and qualify original helper custody before any audit consolidation.

A permitted exact path must join the held original package scope and exact
manifest to inputs.plugin_binding, require manifest.recipe is inputs.recipe and
full manifest.recipe_binding matches inputs.recipe_binding, call the original
package helper, and rejoin those same originals after return. Type/shape fences
precede getters/iteration. Retain the direct recipe path for legacy/unmatched
packages unless existing acceptance already excludes them. Preserve all entry,
invocation, parent-origin, plan/cache and completion-attempt checks. No proof or
permission result survives a callback or another call as reusable authority.

Required causals: exact normal recipe2 path and nested actual recipe execution;
wrong/missing/foreign/copied recipe/binding/manifest; replaced helper returning a
coherent old binding; mutable recipe document/count/descriptor/plan/fact drift;
package refusal before nested call; final nested-return drift; revoked/stale
entry/activation/cache/completion state. Negative paths must prove original
refusal/sticky behavior, no new native work/debit and original cleanup. Keep all
other startup/native tests and compare complete native/normal paths under the
original deadline on current/minimum Python. No host/device/release acceptance
is inferred from helper call counts or this design.

# Original pre-IO source/cache context

Status: independently reviewed context DATA, not cache observation or admission.

EntryFileSnapshotOwner first fixes its original decoded artifact plan, _Inputs
and root cell. Before allocating an artifact IO owner or beginning completion,
CacheContextOwner retains that exact snapshot/input/plan allocation and derives
source/cache edges using the original interpreter tag, optimization and cache
prefix. The one original input slot and snapshot cell retain partial ownership
before the component's own metadata effects. No caller provides paths, manifests,
qualification flags or verifier callbacks.

The base artifact projection already exists; the cache/acquisition plan must not
be used until this context is attached. Cache probes are not implemented by this
component. They must be reserved on the same unfinished aggregate IO owner before
acquisition, rather than extending a completed owner or resetting its allowance.

## CWD and original allocation joins

Only root-level source resolution requires CWD. In that case retain the fixed
original builtin os.getcwd/posix.getcwd identity, exact modules and original
context before calling it; accept only bounded canonical returned path DATA.
Current queries perform context checks before the getter, then pure held-root,
fact, slot and original parent joins. Normal absolute source candidates retain
no getter/CWD requirement, so unrelated chdir does not invalidate their mapping.
No getter is called from callback-free snapshot or continuation seals.

Own-context failure is sticky and does not restore values, recapture or retry.
Foreign process/thread queries refuse before failure-state mutation. A copied
fact is not an original allocation. Parent-lineage validation does not recurse
through the child context. Partial initialization cannot pass the completed-fact
predicate. Reprs/errors do not print code paths or CWD.

Snapshot freshness captures the context fact BEFORE native parent callbacks and
requires that same fact afterward. Completion performs the last context check
before final pure origin/link/count/resource joins. Continuation retains the
same original context fact before its freshness callbacks and pure-seals it
later. This is not a new native-root freshness API: the surrounding parent and
future runtime factory still own complete native/currentness checks and must
refresh required CWD at authority boundaries after parent effects.

## Candidate states and remaining work

Rows retain each original source edge, planned absolute cache location, any
original declared cache expectation and containing original package expectation.
States mean declared, tree_expected_absent, tree_nonfile or needs_owned_absence.
These are expectations: tree absence requires the actual original successful
scans, and loose absence requires actual no-follow owned probes. A directory at
a cache location is recorded as nonfile rather than silently treated as absent.
Shared cache locations retain every source edge; no source constraint disappears
through path deduplication.

Still open: cache/absence probes and their cumulative accounting before IO ends,
actual source/cache/provenance selection, current plugin/import machinery,
archive/member and ABI/library closure, listener/native/key binding and physical
character delivery. No source DATA fact qualifies those gates or publishes images.

The14 focused cases include root-sensitive/independent chdir, deleted temporary
CWD, callback changes and coherent copies, copied facts, wrong thread/actual fork,
declared cache/nonfile expectations, malformed parent binding refusal before
foreign metadata access, and continuation rejecting a replacement fact.
Root-source fixtures declare a synthetic root path but never create/read that
root file or complete its IO. A separate ordinary fixture completes actual
snapshot/continuation. These are not installed runtime or physical-device tests.

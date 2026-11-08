# Fresh cache input and cached-code contract

Status: next PS1-LOADER contract proposal, not implemented or admitted. The
source compiler's broader regression run remains active; this document does not
qualify it. No cached-code execution, cache write, listener or key service is
being enabled. This remains HMP work; no upstream blocker is established here.

## Original inputs and fresh IO

Select only an actual source/cache row from the original continuation, under the
original magic, optimization, hash mode and cache-path policy. Do not accept a
caller path, header/body, expected hash, verifier or qualified flag. A fresh cache
phase needs its own partial owner, read/effect budget and original descriptor
allocations. It cannot extend a completed installation/read owner or reset that
owner's count. Hold original source/cache/actor/continuation allocations before
callbacks and rejoin afterward.

Declared cache bytes must be read with no-follow, bounded descriptor-relative
operations, metadata stability, full admitted SHA and original input/header
allocation joins. Metadata absence/nonfile must be sampled by actual owned
probes, not inferred from a missing declaration. Cache appearance/change outside
admitted expectations is not authority to load new code. These observations are
sampled, not a promise of persistent filesystem state. Cache writes performed by
an eventual owned writer need their own generated-result registry/generation;
this proposal does not admit other newly appearing caches.

The earlier artifact reader turns read exceptions into a generic refusal and
marks uncertainty. It therefore cannot supply a known cache-unavailable fallback
receipt merely because it raised. Preserve actual known OS outcome/category at
the fixed syscall boundary, before callbacks, with original effects/counters and
known descriptor cleanup. Only a definitive native cache-read/probe unavailability
with intact authority/cleanup may justify the native source fallback. A guard,
metadata/hash/inventory mismatch, actor change, unknown completion or close failure
is not an ordinary cache miss. Never probe by widening permissions or following
unapproved symlinks.

## Exact selection and body failure

Consume actual source metadata/hash and fresh cache observations with the existing
CPython selection rules, including flags2 timestamp semantics and original
checked/unchecked modes. Preserve order/currentness and current-source relation;
header classification alone neither qualifies body bytes nor proves code/source
semantic equivalence. Native source-stat failure/cache-path unavailability and
source-read errors remain distinct outcomes; do not fabricate a successful read
or silently compile around a refused security gate.

A short/invalid header or checked hash/timestamp mismatch can select source. Once
a valid header selects cache, native marshal EOF/non-code/body errors must refuse
that cache load, without an invented source fallback. Actual pinned CPython
_compile_bytecode calls marshal.loads, checks CodeType, then calls native
_imp._fix_co_filename when a source path is supplied. Filename fixing is a native
mutation of the newly decoded code object and needs its own original effect/
actual-result custody, not an assumption of permanently immutable code.

Capture actual marshal.loads, code-type and filename-fixer origins at the original
entry, verify their closed module/builtin resolution before/after callbacks, and
invoke held native functions directly. Hold the actual bounded immutable body/view
and returned CodeType before postchecks; no Python helper/global replacement may
be redispatched. The filename must derive from the original admitted source row.
A malformed returned body, stale context, lost acknowledgement or unknown fix
cannot be retried or promoted into an execution grant.

## Remaining operational gates

Inputs are operator-admitted installed code, not arbitrary phone payloads. Input
size bounds do not establish marshal/parser CPU, RSS or native safety isolation;
worker/resource/deadline qualification remains mandatory before the operational
factory can use this phase. Track simultaneous source/cache payload and temporary
allocations explicitly, including released-source history; do not reuse the
source-only two-buffer claim for a combined cache operation without accounting.

Tests must distinguish known cache absence/directory/read denial from policy/hash/
actor failure and unknown cleanup; cover appearing/replaced cache, original
header/body/magic/mode/source joins, actual body errors with zero source fallback,
original marshal/fixer substitutions, filename/nested-code handling, original
results across callbacks, no replay, original/foreign cleanup, supported actual
interpreters, and no payload execution or live host/device activity. Concrete
cache writes, future-import/ABI/library policy and full native admission stay open.

## Independent contract review checkpoint

Bounded read-only review accepted this order: original marshal/fixer capture,
fresh owned cache IO/outcome/cleanup, then one fixed selection-to-compile/decode
operation. No executable implementation or test qualification follows from that
review.

Freeze fallback categories before implementation. Definitive ENOENT, an observed
leaf directory and explicitly supported read denial may represent unavailable
cache only while original path/ancestors/actor/currentness and every cleanup
outcome remain known. ELOOP, unsafe ancestors, structural ENOTDIR drift, changed
inode/hash, unapproved appearance and lost read/close acknowledgement refuse.
Define accepted disappearance separately from an inventory mismatch. A partial
read followed by a known OS error retains its actual prefix/effect counts and
must clear that prefix before any permitted source fallback; it is not zero IO.

Marshal may accept trailing bytes. Do not claim exhaustive body consumption or
reject native-accepted trailing bytes without a separately reviewed policy.
Retain decoded CodeType privately through the filename-fixer effect; the fixer
returns None and may change nested CodeTypes. Track attempted/returned/unknown
fix state separately from the actual decoded code allocation. No earlier code
fact is immutable evidence until that mutation and its postchecks are complete.


## Original decoder origin implemented in source

The original interpreter now holds the actual frozen _compile_bytecode function/
code/globals, marshal module and native loads builtin, actual CodeType alias and
native _imp filename fixer. Currentness joins the same allocations and closes
module/name/self/type checks before equality or foreign getters. This captures
machinery only; no owned cache read or decode effect is enabled.

17 current and17 actual Python3.11.15 child cases passed; floor source hashes were
unchanged. Metadata refusals cover callable/code/alias/module-map substitutions
and foreign metadata with zero foreign calls. Actual native helper/direct loads+
fix parity covers accepted trailing data, EOF, bad tags, non-code refusal and
nested distinct filenames. Returned code is never executed. Independent bounded
source review accepted the origin-only implementation; the unchanged-source broader shared-startup baseline passed1202 cases.
Linux full-plugin/installed/operational qualification remains separate. Input/cleanup/selection/fixer effect and operational
resource/native admission requirements above remain open.

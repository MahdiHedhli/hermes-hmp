# Owned selected-cache decode — proposed next source step

This is a proposal, not executable qualification. The declared-cache reader's
broader startup suite remains active in a different, frozen worktree. This branch
must not imply completed loader, source-fallback, resource or native admission.

The next owner would accept only an actual completed DeclaredCacheReadOwner,
whose actual original selected input attempt chooses cache. No caller bytes,
path, filename, flags, hash, verifier or qualified boolean are accepted. Before
use, rejoin the original read/continuation/interpreter and seal an immutable
snapshot against the actual original cache SHA and header. A memoryview after
the fixed 16-byte header avoids allocating a second immutable body copy.

Use only native marshal.loads and _imp._fix_co_filename captured at original
entry. Hold the actual returned object in an original preallocated effect slot
before callbacks. Non-CodeType results, malformed marshal, stale custody or an
unknown native result fail the selected-cache operation; none selects source.
The filename comes only from the original admitted source row. Retain the new
CodeType privately through the filename-fixer mutation and its actual None return;
track attempted/returned/unknown for decode and fix separately. Do not publish a
completed code fact before those mutations and postchecks finish. Preserve native
accepted trailing bytes and nested filename behavior, without executing payloads.

Original reader/decoder/activation fact anchors, actor and lifecycle joins must
span callbacks; wrong-thread eligibility precedes attempt consumption. The attempt
is single-use and admitted refusal is sticky. Clear original byte buffers without
redirecting to foreign replacements; release known temporary views/snapshots.
Hold actual native returns even on post-return ownership drift. Ready/current
queries rejoin original results; a code object's later native-mutated filename
must not silently be described as permanently immutable execution evidence.

This is only the selected-existing-cache branch. Typed known OS unavailability,
partial IO cleanup and source fallback remain mandatory separate work. It must
not infer cache misses from CacheReadError or CacheProbeError. The complete fixed
selection/fallback operation remains unfinished until those paths are integrated.

The source step cannot connect an operational factory: native marshal/recursive
filename-fixing CPU/RSS/deadline/worker safety is not qualified. The original
mutable cache payload and one immutable snapshot may coexist (at most 128 MiB
each); memoryview is shared, while native decoded graph allocation and aggregate
source/cache memory remain separate unresolved resource requirements. Tests use
bounded synthetic CodeTypes only, never phone or real-user input or payload exec.

Proposed causal qualification: actual owner composition; correct filenames and
nested distinct filenames; native-accepted trailing data; EOF/bad tag/non-code
selected-body refusal with zero fallback; original load/fixer/module substitutions
before any foreign call; wrong actor/reentrance/replay; pre/post-native ledger,
result and filename drift; original/foreign cleanup, release and lost-ack paths;
actual current and minimum interpreters. No tests or implementation are claimed.

## Bounded independent contract review

The selected-existing-cache branch is a valid independent increment. Known native
OS-outcome fallback remains mandatory for the complete loader, but need not block
this branch, which requires a successful actual declared-cache read and refuses
every unavailability case. This does not relax the complete integration order.

Before dispatch, recompute the cache decision against the held fresh receipt
header/SHA and original source metadata/hash plus captured interpreter magic and
hash mode. Do not trust an unjoined `attempt.input` string. Source metadata remains
sampled original evidence unless separately refreshed; decoding cannot promote
it into a claim about the current filesystem. Audit-capable native decode/fixer
calls need original reentrance exclusion and actual result capture before any
post-return refusal. Every admitted failure, including the first guard refusal,
clears the captured original reader buffer without targeting foreign slots.

The first completed query should expose historical native decode/fix completion
and actual CodeType allocation only. It must expressly avoid current immutable
filename-graph claims: native filename fixing can mutate root or nested CodeTypes
later. Operational consumers need their own immediately current graph/admission
contract. Release the body memoryview before dropping its immutable backing
snapshot; clear payload aliases and raise fresh refusal outside exception handlers.
Native parser/worker/CPU/RSS/deadline gates remain mandatory before operational use.

No executable decoder or test pass is claimed by this review. The next concrete
step is the fixed original-owner implementation and bounded synthetic causal
matrix, in this isolated branch, while the reader baseline stays frozen.

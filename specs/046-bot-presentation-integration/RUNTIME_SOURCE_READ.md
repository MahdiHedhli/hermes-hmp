# Fresh runtime source read

Status: implementation and causal qualification in progress. This is a separately
bounded source-read phase under PS1-LOADER, not an extension of the completed
startup snapshot and not code-loading/runtime/native admission.

`RuntimeSourceReadOwner.retain(continuation, index)` selects only an actual
original source row from the retained continuation. It accepts no file path,
expected digest, verifier callback or qualification boolean. A partial owner is
retained before its own freshness callbacks; selected row/buffer/parent lineage
are held before callbacks and joined afterward. One owner/attempt is allowed
for this phase. This does not complete repeated/future import handling.

The actual source is reread using the existing descriptor-relative no-follow
reader with fresh scope, counters, read effects and SourceDigestContext. It keeps
original chunk/EOF records and immutable digest facts through descriptor closure.
Fresh full SHA256 and complete metadata identity must match the original receipt;
changed source refuses rather than executing a newly substituted file. The old
installation counter is preserved and cannot authorize the new IO.

The phase's source size limit is128MiB. Retained mutable source bytes coexist with
at most one source-sized digest temporary or immutable final snapshot, plus
bounded read chunks, hash/allocator overhead and metadata. This is not an exact
RSS limit. The digest temporary is cleared before the immutable snapshot is
created. A pinned actual native C SHA constructor and fixed HASH descriptor hash
that immutable snapshot. After final callback-bearing guards, pure original
receipt/count/owner joins and exact buffer equality precede publication. Pointer
and length alone are not content integrity. Local immutable aliases are released
on both success and failure; immutable CPython copies cannot be promised zeroed.

The captured original mutable allocation is wiped on failure/release, including
when a mutable owner slot points at a foreign replacement; foreign allocations
must remain untouched. Release checks the original actor and continuation first.
A failed or ambiguous read is sticky and is never automatically replayed.

The returned owner is not a permanent byte-integrity proof. A future fixed code
consumer must revalidate the same successful immutable input or perform the
same content seal immediately before compilation. This API does not compile,
unmarshal, execute, write bytecode, install an import hook, create keys, expose
a listener, serve images, change grants or deploy anything. Concrete source/cache
selection and write effects, all future import/machinery/ABI/library coverage and
actual listener/native/key composition remain required.

The native SHA origin currently qualified here is OpenSSL-backed `_hashlib`.
Other implementations need explicit native-origin/causal qualification; Python
version/commit membership is not a runtime availability allowlist.

Qualification checkpoint:130 focused reader/scanner checks passed;15 actual
Python3.11.15 child cases passed with source hashes unchanged. Independent
bounded read-only review accepted the repaired source. Broad startup regressions
are active/pending; no full-plugin, Linux CI, installed or physical qualification
is claimed. Lint, surface, privacy/log and diff checks pass.

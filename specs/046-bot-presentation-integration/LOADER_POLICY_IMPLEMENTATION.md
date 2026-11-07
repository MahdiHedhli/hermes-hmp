# Runtime loader enforcement implementation checkpoint

Status: exact-source investigation; not implemented or admitted. This is HMP-owned
work under PS1-LOADER, not an established upstream blocker.

The original-owner cache observations in 803eae5 complete only sampled presence/
absence acquisition. A completed snapshot must not be extended to read source or
cache bytes again under its old budget. Actual loader selection must use the
original interpreter/cache policy, original source/cache location rows and actual
receipts, preserving original continuation/currentness across callbacks.

## Verified CPython distinction

Pinned Python 3.14.9 SourceLoader.get_code uses
_imp.source_hash(_imp.pyc_magic_number_token, source_bytes). Python 3.11.15 uses
_imp.source_hash(_RAW_MAGIC_NUMBER, source_bytes); it has no
_imp.pyc_magic_number_token. The public importlib.util.source_hash functions
also use these distinct original globals. Do not infer a universal hashing key
from MAGIC_NUMBER bytes. The actual module/function/code/builtin/key continuity
must be bound before the original hash operation and rejoined afterward.

A synthetic-only public source_hash probe confirmed both actual interpreters
execute their corresponding paths. This is algorithm evidence, not application
loader execution or native admission. Exact local source hashes are retained in
the private loader-source-hash audit receipt.

## Required executable work

1. Bind the actual supported source-hash implementation and original key without
   invoking caller-supplied functions, adopting changed state or guessing by
   version alone. Refuse malformed metadata before coercion/equality hooks.
2. Derive source hash and timestamp/size joins from the original bounded source
   reads, not post-completion reads, declarations or SHA256 substitution. The
   native source_hash API requires a whole buffer; explicit bounded temporary
   ownership, clearing, callback currentness and memory accounting need review.
3. Enforce actual selected source/cache behavior for timestamp, checked and
   unchecked hash modes, including stale cache fallback and write-cache effects.
   Header-format classification alone cannot prove source equivalence.
4. Bind existing and future import machinery to exact approved module origins,
   package search roots and native/system-loader policy. Current loaded_origins
   covers declared dependency prefixes only, not the full runtime.
5. Complete archive/member declarations and bounded decompression/member reads,
   extension ABI/non-system library closure, retirement/currentness, then actual
   listener/native/key/broker composition. Do not qualify a whole archive from
   its outer digest or claim hostile same-UID isolation.

Each enforcement stage needs actual positive execution and refusal causals on
supported interpreters, while fixtures remain isolated from live homes and keys.
No live runtime setting, import hook, installation or device change is made by
this investigation. Physical character delivery remains unfinished.

Independent read-only architecture review accepted this implementation order and
identified the source buffer, original algorithm/key, timestamp and selection/
fallback contracts as concrete prerequisites. No execution was performed by the
reviewer; no stage above is marked implemented by that review.

## Source-hash origin implementation in progress

The interpreter observation now retains the actual frozen external SourceLoader
class and get_code function/code/globals, native source_hash builtin, and exact
loader-selected key owner/name/integer value. Module aliases and primitive
metadata are checked before comparisons. Currentness rejoins the original
allocations; it neither invokes replacement functions nor selects a key from
importlib.util.source_hash. Unsupported loader key schemes refuse.

Initial implementation used utility provenance; independent review correctly
required actual loader provenance instead. The corrected implementation passed
70 focused cases on Python 3.14.9 and 70 actual Python 3.11.15 children. Two
synthetic actual-loader cases observe the key and source bytes used by get_code
while replacing the utility function; synthetic code is compiled/unmarshalled
but never executed. Seven entry-currentness causals cover changed builtin,
function, code, key, globals and malformed metadata.

Broader startup verification completed with 1,041 passes and two fixture
failures: the exact module list omitted the new cache observation module, and
the link close-fault injector now fired during an earlier cache probe. Production
source hashes were unchanged. Independent review accepted the precise fixture
corrections; all 339 affected-module cases passed after those test-only changes. The corrected
lost-close case also passed in an actual Python 3.11 child. No production changes
were needed after the 1,041-pass baseline. This is not a
completed source-hashing/selection stage.
Same-original-read bounded source buffering/hash, timestamp/hash cache selection
and runtime consumption remain unimplemented. No live runtime changed.

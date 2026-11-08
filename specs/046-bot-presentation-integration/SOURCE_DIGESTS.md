# Original-read source digests

Status: bounded source/review and local qualification complete; not cache relation
or runtime admission. No live settings or installed files are changed.

The explicit GatewayPackageOwner.verify_recipe_source_hashes(recipe, entry)
retains the actual original entry/interpreter/hash origin before package file
reads. Its actual context is reused by the pending artifact owner. The legacy
verify_recipe DATA path remains distinct and cannot satisfy selected source
hash consumption; there is no later reopen or implicit upgrade of its receipts.

Each selected .py uses one original temporary bytearray, bounded by the existing
128 MiB file limit. It receives the same chunks passed to SHA256. Memory includes
bytearray allocator overhead, existing chunks, bounded metadata and a 64 KiB
zeroing block; this is not an exact RSS cap. The existing aggregate byte limit is
unchanged. Original source-aware read records are additionally bounded to 65,536
per owner, including EOF; ordinary full-size reads under the 2 GiB aggregate and
1,024-file bounds fit. Pathological excessive short reads refuse.

Before each read syscall the owner retains the actual read allocation. The actual
return count/length tuple is held locally through post-read checks. Immediately
after return, before owner/configuration/SHA callbacks, the file reader captures
the original read and returned tuple. EOF is captured at the same boundary.
Append and finish join these exact captures rather than discovering a replacement
result slot or accepting equal count values. Coherent record/result/count and
rebuilt ledger-entry replacements refuse. Native bytes remain accounted even
when later checks refuse; there is no reset or optimistic retry.

Hash intent precedes the actual retained native builtin/key invocation. Only an
exact eight-byte result joins the original allocation. The original buffer is
overwritten in bounded zero blocks and cleared on all normal/refusal exits;
cleanup uses the captured buffer even if a mutable alias is replaced. Chunk
argument aliases are cleared in helper finally blocks. Unknown acknowledgement,
drift or failed cleanup does not create a retry path or source receipt.

After descriptor closure the immutable SourceDigestFact carries the original
read/return captures and returned hash allocation. Exact owner/scope/type fences
precede metadata access; foreign getters and iterators are not used to reject
malformed state. Receipt representations and errors do not print source bytes.
This is bounded Python-level custody under the selected trusted runtime premise,
not hostile same-process memory isolation or executed-image attestation.

selected_source_hashes accepts only the actual original continuation, enumerates
all original selected .py inputs across prefix and pending receipts exactly once,
joins receipt owner/scope/expected/hash identities to its actual digest fact and
original context, and reseals those same held facts after final continuation
callbacks. Missing legacy evidence refuses. There are no new file reads or
caller-provided verifier/qualification flags at consumption.

Verification: the unchanged prefinal source passed 1,068 affected startup checks
in 812.97 seconds. The final two production deltas reject an explicit None entry
and make acquisition linear by validating the held previous/current count bridge;
complete chain validation remains mandatory at fact creation and every persistent
seal. Final source passed 22 focused cases on Python 3.14.9 and 21 actual
Python 3.11.15 composed child cases with source hashes unchanged. This is not a
full final-head plugin/CI or installed-runtime qualification claim.

Causals cover split reads, absent/foreign entry, malformed metadata with zero
foreign hooks, original-buffer replacement, copied/coherently replaced count/
record/result/ledger state, lost hash acknowledgement and replay. Late historical
read mutation can consume bounded work but cannot publish a fact. A read-result
call budget checks linear acquisition. Final native callback mutations of hash,
read and context state refuse after original continuation checks. Legacy receipts
without source evidence refuse. Independent bounded source reviews accepted the
acquisition, custody repairs, consumer, lazy-import rule and final guard/linear
changes; reviewers did not execute tests. Lint, surface, privacy and diff checks
pass. Source-hash buffer allocation includes allocator overhead, not an RSS claim.

Timestamp/hash cache relationship, actual cache selection/fallback, future import
policy, archive members, ABI/library closure, listener/native/key/broker and
physical character delivery remain unfinished HMP work. No upstream blocker is
established by this implementation.

## Original timestamp extension

The immutable source receipt/fact also retains int(before.st_mtime), converted
from the same held actual stat before file-open/read callbacks. Exact primitive
type/range checks prevent conversion hooks/non-finite values. Consumption rejoins
the original integer; negative-fraction/float-rounding cases prove nanosecond
division is not substituted. See [cache-input rules](SOURCE_CACHE_INPUTS.md).

# Source-loader cache input attempts

Status: timestamp custody, pure CPython rules and original receipt/absence
binding implemented in source; runtime enforcement remains unfinished. This is HMP
work, not an established upstream blocker.

The source receipt and immutable digest fact now retain int(original_stat.st_mtime)
from the same held stat before file-open/read callbacks. Exact primitive types
and a finite signed range precede conversion. Consumers join the same original
integer allocation. Do not reconstruct this value from mtime_ns: negative
fractional seconds truncate toward zero, and float rounding near an integer can
also differ from integer nanosecond division. The original descriptor metadata
and byte/hash observations remain unchanged; no extra source read is introduced.

source_loader_input models which input SourceLoader would attempt given those
known observations, not whether import/compilation succeeds or which code was
previously executed. It performs no IO, unmarshalling or execution.

- Missing source stat skips cache lookup and attempts source. Cache absence,
  nonfile and unreadable states likewise attempt source when actually observed.
- Short header, bad magic or unsupported flag bits fall back to source.
- Flags0 and2 use timestamp validation, including uint32 truncation of source
  mtime and size. Flags2 is accepted by the actual SourceLoader, even though the
  separate canonical header classifier supports only the standard writer forms.
- Flags1 and3 use hash validation: never skips both; always checks both; default
  checks flags3 only. A checked mismatch attempts source.
- A selected cache header does not prove a valid marshalled body or CodeType.
  Errors after header selection must not be invented into a successful source
  fallback. A source input attempt can also fail to read or compile.

The oracle invokes the actual retained SourceLoader.get_code on synthetic
in-memory data and checks source compilation versus cached code attempts. It
never executes payload code, opens real source/cache paths or writes bytecode.
It distinguishes source-stat/read and cache-read failures, malformed cache-body
failure, hash modes, flags2, timestamp/size wrap, negative and rounded time.
Seven malformed-input cases require zero foreign equality/length/conversion
hooks. Combined current checks passed60 cases;52 actual Python3.11.15 child cases
passed with source hashes unchanged. A final parentheses-only lint repair was
followed by36 current rule cases passing. Independent bounded review accepted
timestamp custody and the pure rules; the subsequent binding scope follows below. Lint, surface, privacy and diff checks pass. The first36 rule tests
were followed by a corrected truly short cache fixture and another36-pass run.

## Original-observation binding

selected_cache_input_attempts derives every source from the actual original
continuation and source digest receipt. Preserve source expected/size/mtime/hash,
actual cache candidate location/tag/optimization and original magic/hash mode.
Declared caches need the original full hashed artifact and retained header;
absence/nonfile needs the actual original tree or descriptor-relative before/
after observations. Planned absence or metadata must not be relabeled as an
observed loader read error, and sampling does not prove persistent absence.

Hold original source/cache/context/proof allocations before final callbacks,
then rejoin and reseal them afterward. No caller verifier, path, Boolean
qualification, completed-owner extension or implicit legacy upgrade is allowed.
A default CLI script input is not automatically a SourceLoader code load.
Actual machinery, fresh import/read enforcement, archive members, extension ABI
and libraries, listener/native/key/broker and physical delivery remain separate.

The consumer retains the actual source receipt/digest fact, original cache-context
row, declared cache artifact/header, and actual tree entry or both original
descriptor-relative missing observations. It holds these before final callbacks
and rechecks the original continuation/module/activation cohort before the
callback-free seal. Foreign proof iterators/equality hooks and unequal proof
lengths refuse with the sanitized selection error. Directory entries use the
verified package schema's `directory` label. Twelve focused cases pass, including
checked/unchecked hashes, mismatch/bad magic, absent/nonfile observations and
late source/root/coherent-global substitution. This remains sampled input-attempt
DATA: it performs no extra file read, does not unmarshal or execute cached bodies,
and does not prove a future loader observation or successful import.

The binding matrix also passed nine actual Python3.11.15 child cases with
source hashes unchanged. Three direct malformed-proof cases passed again after
import/line-format cleanup. These are bounded checks, not full-plugin or device
qualification.

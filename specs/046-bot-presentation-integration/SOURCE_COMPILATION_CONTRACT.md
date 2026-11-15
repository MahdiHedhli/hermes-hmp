# Fixed source compilation contract

Status: compile-only implementation in an isolated worktree, with bounded
independent source review accepted; local/floor/broad qualification in progress.
This does not make a code-loading/admission factory operational. Source/cache
selection, cache writes, future import/ABI/library policy and native/key composition
remain required. Compilation must not be used to bypass the chosen cache input.

## Original machinery

Extend the original interpreter capture with the actual frozen SourceLoader's
source_to_code function/code/globals and the actual native builtins.compile
object it resolves. Check closed module/function/dictionary/builtin types before
accessing metadata. Capture function.__builtins__ itself as the actual builtin-resolution dictionary,
not a later globals[__builtins__] value or assumed current module namespace.
Retain original builtin namespace identity, refuse a global
compile shadow or changed resolution, and rejoin the same original allocations
on currentness. Do not recapture a replacement as the original compiler later.
This is an API/origin requirement, not a tested-version or commit allowlist.

Inspected Python3.14.9 and3.11.15 SourceLoader.source_to_code both invoke compile
with the source bytes, source path, mode exec, dont_inherit=True and optimize
(default -1, meaning the interpreter's optimization setting). Their Python frame
helper redispatches a function and is not an authority. The fixed consumer should
call the captured native C builtin directly with flags0, dont_inherit=True and
the original current optimization setting. Causal tests must compare actual
native source_to_code output and errors on both interpreters, including encoding
cookies, future flags, optimization/assert behavior and syntax refusal. Traceback
sanitization is the owned operation's responsibility, not a claim of identical
Python helper frames.

## Owned effect and input

The fixed compile operation accepts only an actual successful fresh source-read
owner, never a caller buffer/path/hash/code/compile callback or qualified flag.
Retain a partial compilation owner and latch one attempt before callback-bearing
checks. Hold the original source owner, scope, continuation, original buffer,
read count/digest fact, expected path/SHA and compiler-origin allocation. Refuse
released/failed/changed source owners and wrong actor. Actor means the source
owner's original process/euid/thread; this does not prove Task identity. Generate a bounded immutable
source snapshot, verify its full SHA with original native hash machinery, then
rejoin context/content immediately before the C compiler effect. Snapshot limits
and lack of immutable zeroization must remain explicit.

The compiler receives only the held immutable snapshot and original source path.
Retain the actual returned object before post-call freshness checks; require
exact CodeType. Rejoin held original roots/cells, compiler origins, source read
facts/count and original buffer content after all callbacks. A replacement of the
builtin, source, context, count, selection or buffers cannot be adopted. An audit
hook exception or ambiguous return is sticky; do not automatically replay. Clear
local snapshot/result aliases and the captured original mutable source allocation
on refusal according to the original ownership/actor cleanup rules. Foreign
replacement allocations stay untouched. A sanitized error must not retain a raw
source-bearing exception context.

A compiled result is an owned immutable fact about that exact compile operation,
not a caller-constructible authority to execute or serve code. No exec, module
publication, import hook, cache write, provider/tool/send operation, listener or
credential activation occurs. A future loader must separately consume original
current owner facts and prove actual fresh cache selection/write effects and
complete runtime policy before code execution.

## Resource and verification limits

The source input remains the separately bounded source phase's128MiB maximum;
immutable snapshot plus mutable source is at most two source-sized payloads, plus
parser/code-object/hash/allocator overhead. This is not a process RSS or compiler
CPU/deadline bound. Inputs are independently operator-admitted installed code,
not arbitrary phone/user source. The operational factory's worker/deadline/resource
policy is still a distinct gate and must not be silently certified by input size.

Meaningful refusal tests: unowned/foreign read owner; released or failed owner;
same-length source mutation; wrong actor; original compiler/global/builtins/code
replacement before and during audit; copied count/digest fact; actual compile
throw/lost acknowledgement; stale continuation; no replay; no payload execution,
cache write or real host interaction; original-buffer cleanup and preservation of
foreign replacements. Broad shared-entry/source-reader regressions and exact
wheel/source binding remain required alongside actual floor tests.

Independent read-only contract review found no architectural blocker, with the
actual function builtins dictionary and accurate actor definition made explicit.
This is contract acceptance only; executable implementation is not yet present.


## Implementation checkpoint

`gateway_entry.py` captures the actual source_to_code function/code and its own
`__builtins__` dictionary plus native compiler before subsequent callbacks.
`runtime_reader.py` retains the actual completed read tuple separately, with a
historical data accessor after release and a current actor-checked accessor before
byte consumption. History does not authorize current bytes or compilation.

`SourceCompilationOwner` accepts only the actual read owner. Original actor
eligibility precedes attempt consumption; a temporary reentrance exclusion does
not consume an attempt for a foreign thread. Every admitted failure clears the
captured original buffer and prevents replay. The actual native return is held
before post-call checks. Success releases source bytes before publishing an
original owned CodeType fact, with later queries holding the same fact/effect/code
across callbacks. This is not a cache-selected get_code result or execution grant.

The first matrix passed37 cases; the strengthened always-on optimized parity
checks passed3 further cases and actual syntax-error sanitization passed1. The
parity child intentionally runs under -O/-OO, so ordinary assert statements are
not used for its verification. 38 actual Python3.11.15 child cases passed with source hashes unchanged;
all floor-tested source hashes also match after reconciling the published
fixture/docs repair. The broader shared-entry/reader baseline passed1185 cases with source hashes
unchanged; no production deployment or native admission is
claimed. The original reader's separate unchanged-source1162-pass baseline does
not qualify these new compiler/reader changes.

The1185-case result is local source qualification for895e832. Linux full-plugin
CI, operational resource/loader/native admission and physical delivery remain
separate; no execution authority follows from this result.

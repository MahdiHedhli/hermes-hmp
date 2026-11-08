# Declared cache byte reader — implementation under review

This branch adds one bounded fresh read of a cache artifact selected from the
actual original continuation. It accepts an original continuation and row index,
not caller bytes, paths, headers, hashes or verifier callbacks. It cannot read an
undeclared, newly appeared or missing cache and cannot authorize source fallback.
The broader cache IO task remains open for typed native unavailability/effects.

A separate root, counter, original mutable byte buffer, descriptor/read ledger and
completion fact are bound to the activation. Exact original SHA, file identity
and first sixteen bytes must agree after fresh descriptor-relative no-follow IO.
A held native SHA function reseals a bounded immutable snapshot; final pure byte
comparison and original ledger joins precede publication. Wrong-thread eligibility
is checked before consuming the attempt. An admitted failure is sticky and clears
the original buffer; foreign mutable replacements are not cleared.

The byte budget is at most128MiB. During final verification the original mutable
payload and one immutable snapshot may coexist, plus fixed read/hash/interpreter
bookkeeping. This does not qualify aggregate source-plus-cache memory, native
parser CPU/RSS, isolation, filename-fixer effects, or actual code loading.
Mutable retained bytes require another consumer content seal. Release destroys
the independently held original allocation without redirecting to a foreign slot.
No cache payload is decoded or executed, and the synthetic fixture payload is
intentionally not valid bytecode.

Fourteen causal cases and five import-boundary cases are prepared, NOT RUN while
the existing probe baseline and its serialized cleanup checks remain active.
Full Ruff, surface/privacy and diff checks pass. Independent read-only review is
requested. Source is uncommitted/unpublished and no runtime/device qualification
or live host/device/settings/grant/provider change is claimed.

## Review findings — unresolved, no admission

Independent read-only review found a wrong header field, missing original-cell
join, lifecycle/primitive fences, and incomplete original syscall read-effect
custody. The direct field/cell/lifecycle/primitive repairs are in progress and
untested. The read-effect issue remains a security blocker for this branch:
retaining mutable `_ReadEffect` row identity and returned/unknown flags does not
freeze actual before/after count allocations, requested length, returned length,
or the cumulative chain including EOF. A final matching buffer digest does not
establish that history. Before any completion/use, capture those actual effects
at the fixed native-read boundary before callbacks, retain them independently,
and rejoin them at publication and current queries. Add causal coherent-ledger
replacement tests; do not infer fallback or operational authority from this work.
This issue is confined to the uncommitted, undeployed reader prototype; the
existing cache-probe test runs use unchanged source in other worktrees.

## Read-effect repair checkpoint — awaiting tests and final review

An exact-owner dispatch now performs cache reads at its own fixed native syscall
boundary. Before each read, an immutable attempt retains the original descriptor,
request size, count cell, mutable effect and preallocated result slot. Actual
returned length and the new count cell enter that original slot before any refusal
check. Normal completion anchors the actual result tuple independently in module,
owner and activation histories. Guard callbacks cannot replace those histories;
adjacent count bridges are checked during acquisition and the full chain (including
EOF) at publication/current queries. Original claim cleanup now also rejoins
owner/activation/root/cell and both original ledger heads; drift leaves unknown
debt and the claim retained. Independent review requested final confirmation.

The reader permits at most4096 native reads including EOF. Acquisition validation
checks at most two adjacent records; history tuple append still copies prefixes,
but total copy work across both histories is explicitly bounded to fewer than
16.8 million entries, plus fixed overhead. Ordinary128MiB input in64KiB chunks
needs2049 reads. Pathologically short reads may exhaust the cap and refuse with
no fallback. Operational CPU/RSS/deadline qualification remains mandatory; these
source bounds alone do not prove it. The earlier review findings are preserved
above as historical findings, not a claim that this repair passed tests.

Final bounded independent read-only source review found no remaining concrete
blocker after the exact cleanup joins. This is source-only acceptance: fourteen
reader cases, actual floor, broader and operational qualification remain pending.

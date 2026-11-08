# Declared cache byte reader — qualification and remaining limits

## Current status — November 8, 2026

The reader baseline passed141 current checks (14 reader and127 scanner),14 actual
Python3.11.15 child cases and the1,244-case shared startup run on `faf6a81` with
unchanged source. Independent bounded source review accepted the effect-custody
repair described below. Those are isolated/historical source results, not current
production or physical qualification.

A later output-path collision lost the original raw1,244-case binding. The
successful log and prior in-session binding inspection remain; the missing record
is not reconstructed. The later combined `1ab9910` run failed215 cases and passed
1,065. Its144-case residual rerun passed125 and failed19, including three reader
fault cases. The reviewed migration subsequently passed164 cases, with each
prior19 failed ID matched to a pass. The repaired1a49174 candidate passed all1,280
configured startup checks on actual Python3.14.9, zero failures/errors/skips and
unchanged source. This resolves the observed fixture regression for that exact
candidate, not operational/native/resource or physical qualification. The164-case
actual3.11 fixture run remains in progress.

The migrated `read_error` fixture injects loss of acknowledgement after a second
actual native read. It retains a known acknowledged65KiB prefix and unknown debt;
that count is not total kernel-consumed bytes or proof of a kernel EIO. No native
error class/errno alone establishes kernel entry. Typed unavailability, fallback,
aggregate resources, operational startup and physical delivery remain open.

## Historical implementation and review record

The following checkpoints preserve their original order and scope. Statements
that work was uncommitted, untested or awaiting review describe those checkpoints;
the focused results above supersede them for that reader baseline only.

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

Focused qualification passed 141 current checks (14 reader and 127 scanner) and
14 actual Python 3.11.15 children. Full Ruff, surface/privacy and diff checks pass.
Independent bounded read-only source review accepted the repaired source. The
source is committed; the shared-startup baseline passed 1,244 checks with source unchanged;
runtime/device qualification remains pending. No live host/device/settings/grant/provider change is claimed.
Earlier review findings and their repair history follow.

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

## Focused qualification result

All 141 current checks passed (14 reader and 127 scanner cases). All fourteen
actual Python 3.11.15 child cases passed; source hashes remained unchanged through
both runs and public-branch ancestry reconciliation. Cases include normal read,
metadata change, wrong thread without attempt consumption, replay, partial-read
error, copied facts, late buffer/effect/ledger/lifecycle replacements, native
post-read count drift, foreign read claims and late activation ownership drift.
The broader shared-startup regression remains pending; operational/resource/native
and physical qualification remain separate. No cache decoding or execution occurs.

The unchanged-source shared-startup baseline on `faf6a81` passed 1,244 cases in
1,710.72 seconds. This covers the shared reader/activation/file-dispatch changes
and does not qualify the later selected-cache decoder or native-IO metadata field.
Operational resource/native/physical qualification remains open.

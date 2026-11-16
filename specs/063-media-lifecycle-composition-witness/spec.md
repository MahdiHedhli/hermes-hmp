# Preserve media source witnesses across lifecycle composition

## Problem and exact scope

The media binding tests' existing readiness/AT1 adapter inverse recovers the
unchanged pre-AT1 SHA f8a5d6a196c3e4622db50dd04303df2eb401467f87feab894d663ab93f68b3a3
through immutable 7c528066 parent. Later presentation lifecycle commit
7c528066cd0e0f4e8ad95a954f39def6df5f3f88 and readiness drain commit
11a70f016737ad80dc675ebd7f22af9bf452a61d change those exact sites. The old
inverse refuses them. The server lexical media count changes from zero to 37 in merge
9ab269583e4b99e9950e4354349a30d93c1b7814, which adds media-readiness APIs.
Later own-Controls commit 30dedf998b9c1bb1951f1bbd327e9a85835b26e3
also changes overlapping server context. Neither observation establishes a
production defect or permits accepting a new baseline hash blindly.

Add a test-only literal inverse for these exact adapter deltas (newest first),
and server deltas in order 30ded, 11a, then 9ab first-parent before the
original lexical projection. Each
unique accepted context block must match exactly; other source remains for the
existing detectors. Keep all original baseline hashes, ownership/capture mutation
checks, dynamic-lookup forms, ordinary mutation checks, route response/callback
assertions and media-reference assertions unchanged.

This inverse is a projection for specific source checks, not an independent
source validator or security/runtime proof. Relocated blocks must either refuse
or fail exact parent recovery. The server check is explicitly historical: the current server does have new
media-readiness references. Lifecycle and new-route correctness remain covered separately
by the owning presentation/readiness tests, not inferred from stripped source.
No production source, host permissions, device software or release change.

## Plan and checks

- [x] Isolate the original two failures and bind both owning Git deltas.
- [x] Verify each of 37 literal inverse hunks recovers its exact Git parent.
- [x] Retain original baseline hashes and all original assertions.
- [x] Add changed/duplicate/relocated block controls and outside-byte preservation.
- [x] Complete binding, inverse controls and owning lifecycle test selections.
- [x] Independent final review and focused publication; current-status sync recorded separately.

## Limits

Source-check success does not qualify full Linux CI, private integration, native
startup/physical rendering, live messages/providers, LLY520 update or release.
The separate broad run retains its original immutable source and process handle;
it is neither modified nor restarted by this work. Frozen registry hash failure
and other broad failures remain distinct and unresolved.

## Exploratory result retained

The initial exploratory five-file run tested an incomplete server chronology and
fails two checks: server exact parent recovery and the old lexical projection.
It also saw a whitespace-only test formatting edit while already imported; it is
not final immutable-source qualification. Evidence is retained, not overwritten.
The corrected inverse includes the missing 30ded and 9ab deltas; a new run must
cover current media-readiness and self-Controls source directly. No source guard
or original baseline was relaxed to make this pass.

The first corrected-chronology run reports 361 cases: 360 pass and one newly
added negative control fails because it prepended text before a leading newline,
leaving the original block substring intact. The control now changes a real
non-whitespace character inside the block. Two static privacy findings caused by
escaped-newline/decorator adjacency in literal formatting are resolved by splitting
adjacent literals, with identical parsed helper AST and unchanged accepted bytes;
scan_private is clean. The failed run is retained; final checks must be rerun on
the corrected immutable source rather than inherit its partial pass.

## Final observed result

Exact executable source affd2993aec761b6a90dee878a652b0a4a884a48 produces
normal JUnit: all 361 cases pass, zero failures/errors/skips, 63.142 seconds on
Darwin/Python 3.14.4. Breakdown: binding 117, composition controls 115,
presentation lifecycle 30, readiness lifecycle 6, readiness worker 13,
media-readiness 51, own-device Controls readiness 29. The checkout stayed clean
through the final run. Exact Ruff 0.16.9, plugin surface and private-value scanner
pass. The log scanner had no captured runtime corpus.

Independent source review accepts all 37 exact Git-parent inverse blocks and
unchanged original binding assertions (normalized AST proof). Current source APIs
are exercised in the separate owning tests above; the historical lexical
projection is not their qualification by itself. Full broad regression and
native/private/device/release gates remain open; the frozen registry expectation
has not been changed.

Published as [Draft PR178](https://github.com/MahdiHedhli/hermes-hmp/pull/178),
stacked on PR177; no deployment is performed by publication.

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
- [ ] Complete binding, inverse controls and owning lifecycle test selections.
- [ ] Independent final review, focused publication and current-status sync.

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

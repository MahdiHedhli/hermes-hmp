# Complete executable-link native lifecycle

November 9, 2026. Source prerequisite for desktop character delivery, not a new
public API, permission, installed feature or upstream dependency. The current
production baseline is `c37925523f9ab7410c656b0bfd4fda383126c2f1`
(documentation successor `b5990a2`).

The existing complete runtime/cache file metadata walk and fresh/startup absence
drivers must remain intact. Do not replace them with another implementation.
The next incomplete native boundary is `StartupArtifactOwner._link_path` and
`_readlink` in `presentation_startup_artifacts.py`. They currently use original
held native callees/actor checks and local accounting, but do not carry the shared
typed operation/result/consume/ACK lifecycle through the complete link traversal.
The actual isolated startup acceptance test now observes all link paths on
Python 3.14.9. Startup completes and closes its held descriptors, but the test
fails its three intended requirements: 129 metadata calls and two readlink calls
have no corresponding in-flight typed operation, and both read records and both
snapshot observations retain actual raw link bytes. These are experimental
source findings, not an exposed service or a new installed feature. The test is
deliberately red until the coupled path is implemented; it is not an additional
passing prerequisite milestone. See
`server/tests/unit/test_presentation_native_link_traversal.py`.

The minimum-Python observer remains unqualified: instrumentation exceeded the
unchanged 60-second child limit, including a restricted first-hop observation.
Those timeouts do not establish the intended causal failures on Python 3.11.15.
Current-Python uses local C-call monitoring; the older interpreter's first-hop
fallback is explicitly narrower and cannot qualify all phases even if completed.
The earlier passing encoding/Scope suites do not satisfy these native tests.

Package/entry enumeration and factory/service admission are separate unfinished
boundaries. `PresentationNativeService` is not registered with routes.

## Fixed traversal

The original retained runtime source owns the exact `ExecutableLinkPlan`, its
`LinkHop` members and final `ExpectedArtifact`. The caller never chooses a path,
operation, policy, arbitrary asset name or remote URL. Before and after snapshots
each observe all original hops, then the original final target. A later metadata
recheck repeats each path without another readlink or byte charge.

The DATA helper requires an independently validated original runtime plan. Its
shape, continuity and privilege consistency checks do not replace the native
plan's private-path allowlist or lexical target-resolution validation. Future
driver tests must reject a copied/replaced plan against the independently held
original. Policy actions describe basename strings; the native driver must hold
the actual encoded bytes from the early retained `str.encode` descriptor and
interpreter filesystem settings, through `encode_basename`. A later
`os.fsencode` export or assumed UTF-8 is not the original encoding authority.

For each original path, preserve the current order:

1. Open root, then fstat it; repeat open/fstat for every parent component, holding
   the actual descriptor allocation immediately before any callback can run.
2. No-follow stat the leaf. Enforce the existing safe-directory and symlink or
   final-regular-file policy, including selected uid, mode, nlink and size.
3. For a hop in before/after only, readlink its original encoded basename using
   its actual parent descriptor. Consume exact bytes matching that original
   hop's target, below the selected CPython/platform bound. Charge the actual
   returned length even if a later check refuses. No readlink occurs in recheck.
4. Repeat leaf stat and compare all nine fields to the actual first result.
5. In original parent order, fstat each held descriptor and no-follow stat its
   original name relative to the original parent, matching the five-field
   directory signature. Preserve root's `dir_fd=None` form.
6. Carry the literal completed path return across one-attempt reverse cleanup
   and into the actual snapshot/publication. An uncertain close is retained as
   uncertainty, never replayed or declared closed.

No missing/error result becomes successful absence, fallback, a new path, or
permission to proceed. The existing total-byte and shared native work budgets
remain authoritative; reserved cleanup must not depend on successful traversal.

## Native integration contract

Capture code/type/member/dispatch and all original immutable policy inputs in the
pre-Scope factory, then seal actual constructor returns. Use a distinct fixed
link resource/consumer on the canonical shared kernel; do not broaden the
directory-consumer owner allowlist or expose a generic operation dispatcher.
Every native effect requires the full current mutable-parent audit after the
original weak/lifecycle/actor observations, original descriptor/argument joins,
and a one-use admitted operation. Never replace that audit with cached equality
or a reusable shallow witness.

The readlink result needs a typed capsule bound to the original operation and
pending phase. Its fixed consumer must prove actual returned-byte/count custody,
apply the exact original target policy, retire raw result storage without
retaining exceptions/tracebacks, and publish only the literal one-use ACK/commit.
Interruption after return, consumption, partial ACK or constructor publication
must preserve uncertainty and block replay. A current history slot cannot recover
a lost original return. Metadata sites must use the same real typed shared
producer/consumer path as other integrated resources, not direct wrapper results.

Finish validation must retain exact owner, scope, runtime, source, original plan,
hop/index/phase, parent allocation chain, counts, actual predecessor and completed
cleanup. Snapshot allocation and final callbacks require another complete pure
seal against the independently held finish. Failed and torn states refuse; an
older healthy finish must not require the shared ledger to stay permanently idle.

## Tasks and evidence

- LP1: implement and review closed traversal policy DATA for hop/target and all
  three phases. `presentation_link_path_policy.py` and its source tests are the
  initial implementation. Its policy constructor must retain original helper
  code, class members/dispatch and exact inputs before allocation, then reject
  callback replacements before invoking a helper or returned-object getter.
  Twelve new constructor fault cases cover those boundaries. It is unconnected
  and cannot admit work, acknowledge a native operation, prove provenance or
  grant access. The same 56 original DATA controls pass on both Python
  versions; the first-helper correction is included in the 86-case preparation
  and later 131/130 integration suites. None qualifies native link effects.
- LP2: bind original policy/engine origins before Scope construction; define
  distinct resource/consumer and typed readlink result custody. Preserve default
  non-native callers without treating them as native qualification.
- LP3: connect the complete `_link_path`/`_readlink` order, real debit/result/
  consume/ACK and literal finish/cleanup/publication. Do not deliver a detached
  readlink helper as completion of this task.
- LP4: focused independent security/contract review and current/minimum causal
  verification, followed by meaningful broader regression on frozen exact source.
- LP5: compose with remaining native owners/enumeration/factory/service work,
  then authenticated runtime, physical Android/iOS and release qualification.

Required causal controls include every metadata role, exact target/bound and
count changes, wrong/copied owner/scope/hop/phase/parent, late actor and mutable
parent changes, raw return/consumer/ACK loss, partial publication, cyclic-GC-off
retirement, quota exhaustion, reverse cleanup after each partial acquisition,
foreign-slot preservation and no retry/refund/new admission. Pure policy tests
must be reported as DATA coverage, separately from actual native-effect tests.

No live host, configuration, phone, permission, provider, model, job or release
action is part of this source task. Full desktop character and host-local image
delivery remain incomplete.

## Scope binding progress

The actual Scope-binding portion of LP2 is implemented in `7042dcc` and covered
by 170 current / 169 selected minimum checks, with the common case set and hashes
verified. See EARLY_LINK_FACTORY_ORIGIN.md for precise scope and the copied-plan
regression. LP2's distinct resource/consumer and the complete LP3 native traversal
are still open; this does not enable character or host-local image delivery.

LP3 must connect metadata operations 3/4 and a distinct typed readlink operation5
through real result custody, fixed consumption, raw retirement and one-use ACK.
Readlink must not impersonate source-read EOF/digest or absence. Pin the actual
filesystem encoder and dependencies early; retain its literal bytes return and
parent descriptor. Drive all original before/after/recheck path sites and reverse
reserved cleanup, retaining literal finishes across snapshot/fact publication.
Recheck is ready-state metadata only, with no readlink/byte debit. Retire actual
returned bytes separately from the original declared target. Keep full current
parent/actor audits, real count/debit deltas, sticky uncertainty and no replay.
Remaining package/entry enumeration, other typed owners and full factory/service
admission remain separate requirements after this path is connected.

## Original encoding prerequisite

`c379255` adds early original filesystem encoding preparation and updates the
actual entry/Scope origin schema consistently. The full 203 current / 202 selected
minimum checks pass with verified artifacts and common cases. See
FILESYSTEM_ENCODING_ORIGIN.md. The enclosing link driver still uses its legacy
path until full LP3 connection; this helper is not native admission or image
availability. No source or native permission is recovered from copied DATA.

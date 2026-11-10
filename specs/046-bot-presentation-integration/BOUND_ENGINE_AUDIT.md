# BI1-BA: original bound engine audit

November 10, 2026. Target source: executable `15eeb14d` on documentation head
`fb1784f2`. This freezes the next implementation boundary; it is not an implemented
optimization or a startup/image-delivery pass. The current source's normal native
contract still exceeds its unchanged 60-second deadline. The exact `15eeb14d` receipt `/private/tmp/hq-lx_7w79e/receipt.json`
is terminal failure with source unchanged and one non-skipped test failure; its
log hash was rechecked. It reaches event 4 at 49.9379 seconds with 44 typed
observations/work 963/reserved 0 before the 60-second timeout. The earlier
`f98ede4` receipt is historical and is not current-source runtime evidence.

## Objective and non-goals

Complete desktop bot character/name/avatar delivery. Reduce repeated immutable
schema parsing only where original factory custody makes it redundant. Preserve
all fresh mutable-state checks, authorization, native-effect/result ownership,
work/byte bounds, failure stickiness and original deadlines. Do not replace the
feature with letter icons, a metadata-only subset or a later-version allowlist.
The separately qualified host-local image path is independent of this blocker.

Startup-only attestation, a cached successful verdict, caller-selected inspection
helpers, carrying an audit result across a callback, and widening the deadline are
not approved alternatives. A microbenchmark cannot close the normal native gate.

## Fixed construction boundary

1. Keep `_engine_origin_tail(origin)` and `retained_binding_origin.current(packet)`
   as complete-schema DATA validators. Their standalone successful return grants
   no authority and remains safe for malformed/copy controls.
2. Construct one fixed bound live-audit object inside the actual `_capture_engine`
   sequence, after the full generic validator and its original post-callback
   primitive/source reseal. Bind the literal returned engine-six tuple, its
   original immutable layout and validated columns strongly. Do not nominate the
   object from a caller-supplied layout, matching tuple or exported replacement.
3. Retain the actual bound object separately in the original early parent, then
   join the same pointer through actual EntryOrigin, STARTED/CELL, native lineage
   and Scope. A coherent cloned environment/engine/layout/carrier is not original.
   Lost/interrupted factory publication has no recovery or substitute capture.
4. Extend the original parent engine dispatch (`link_factory_origin.current`) and
   both final Scope publication windows. Every `_closed_link_engine_origin`,
   `_execution_mirrors` and `_native_link_function` selector must freshly join the
   same original bound pointer before choosing the fixed fast dispatch.
5. Authenticate the fixed checker FunctionType, code, globals, builtins, defaults,
   keyword contents and closure-cell values against the early original record
   before invocation. No supplied function/primitive or mutable success marker.

This is a coherent integration boundary. An unwired carrier helper or a faster
standalone function is not completion of BI1-BA2/BA3.

## Carrier decision and measured representation facts

An exact native `functools.partial` is a possible DATA carrier, not an authority.
Its native `func`, `args` and `keywords` reject direct assignment and retain strong
references. However, the native `__setstate__` method can replace all three on the
same object. Even an empty `keywords` is a mutable dictionary. Read-only attribute
syntax does not establish immutable state or an original factory return.

A fresh isolated `-I -B -S` probe on actual Python **3.14.9** and **3.11.15**
verified nine representation facts on each runtime, including coherent-clone
identity differences, direct-assignment refusal, arbitrary-attribute non-shadowing,
keyword mutation, native state replacement, no callable invocation and actual
strong retention/release. The probe touches only synthetic objects/private output.
Private proof: `/private/tmp/hermes-bound-audit-carrier-facts-current-20261110.json`.
These observations qualify neither a carrier implementation nor its root custody.

The selected carrier is instead an **exact immutable tuple DATA record**, not
partial or a bound callable. This avoids partial constructor/keyword/state and
late callable rereads. Its literal engine/layout/validated-column/checker-row
references are strongly retained, but mutable objects contained in those records
still need their full fresh checks. Independent architecture review accepted this
as the same bound-schema contract with a smaller new trust surface.

The original factory's new return is an exact three-field immutable record:
`(literal_engine_six, literal_engine_layout, fixed_checker_row)`. The third field
is the actual fixed checker row retained before callbacks and present by identity
in the engine's original function rows. Layout contains the validated immutable
columns; no mutable index/cache or caller exclusions are added. Generic standalone
DATA consumers explicitly select field 0 and still invoke the complete validator.
No dual-shape or missing-record fast-path fallback is allowed.
The parent stores the literal return, not an equivalent reconstruction. Original
EntryOrigin/STARTED/CELL/lineage/Scope joins determine eligibility, not the record's
coherent contents alone. Dispatch captures and authenticates the held original
checker and literal arguments, then invokes that checker directly. It never calls
a retained partial or a caller-selected function, and never re-reads a mutable
callable carrier between its last check and dispatch.

Implementation must explicitly account for the current source sites:

- `_capture_engine` currently returns engine-six, and standalone DATA tests use
  that shape. Its explicit new return is the record above. Update those DATA
  consumers to field 0 without changing their malformed/mutation expectations.
  BA2 may retain generic full validation everywhere; fast dispatch stays unreachable
  until the complete record-root chain and BA3 fixed live checker are accepted.
- The early parent environment is currently seven fields (engine/layout at 4/5,
  selected-helper capsule at 6). Add a distinct retained audit-record field; do
  not repurpose the helper capsule or nominate through mutable layout data.
- `_EntryOrigin` currently has eleven fields, with link policy at 10;
  `_NativeFileLineage` has five fields, with policy at 4. Preserve these indices
  and append explicit original audit-record fields when extending root custody.
- `_Scope` currently has eighteen fields, with native link blueprint at 17.
  Preserve that index and append explicit audit-record custody. Extend every
  fixed tuple-length/field/constructor join, including both final Scope blocks.
- Parent/entry/Scope, `_closed_link_engine_origin`, `_execution_mirrors` and
  `_native_link_function` must agree on the same actual record before dispatch.
  The generic engine-six parser remains complete and nonadmitting.

These are implementation prerequisites, not a license for a partially wired
selector. No fast dispatch may become reachable before the complete root chain
and causal controls are in place.

## Allowed omission versus checks that remain fresh

Only immutable tuple/pair widths, duplicate-key parsing and immutable key-column
correspondence already validated at original capture may be omitted by the bound
path. Expected class objects, functions, dictionaries and cells remain mutable.

Keep every current registry/module identity and namespace key-type/cardinality/
static-role check; class bases, complete member key sets and live values/dispatch;
function code/globals/builtins/defaults/keyword contents/closure cells; native
parent/runtime/actor/ledger/custody/resource checks; and all required post-callback
reseals. No live access decision, descriptor state or closure value is memoized.
The same-size missing-None-key and GC-mutated-key refusals remain mandatory.

## Acceptance and review

- Positive generic-versus-bound outcomes match on the actual original engine.
- Malformed generic inputs still refuse. Matching carrier/engine/layout/environment
  copies refuse at both actual STARTED/CELL-rooted publication windows.
- Missing/lost factory return, foreign/subclass carrier, coherent record/argument
  copies and changed checker provenance refuse before foreign invocation. The
  rejected partial design remains covered by its actual state-replacement proof.
- Checker code/default/global/builtin/closure drift during construction and final
  return refuses. Required mutable module/class/function/parent/ledger mutations
  refuse after an earlier successful audit too, without new effects or hooks.
- Existing current/minimum causal suites pass with exact source/case bindings;
  independent source/security and execution review covers the actual integration.
- The actual original native contract completes under **60 seconds**, with its
  original native-operation, raw retirement and closure assertions intact.
  A failed baseline, subset, count or synthetic helper speedup is not a pass.
- Then qualify startup/service/routes/full character projection and rendering,
  physical devices and release separately. Integrating with HMP `6796bfbb` must
  preserve its later media/read-worker fixes and schema-4 migration protections;
  never deploy this older character branch over it as a code-only rollback.

## Tasks

- [x] BI1-BA1: freeze the source-backed boundary and establish carrier-option facts on both
  actual supported runtimes and select the immutable tuple record. Independent read-only architectural review accepted
  the boundary; exact document consistency review is recorded separately.
- [ ] BI1-BA2: implement original construction and same-pointer root custody through
  both publication windows and every selector, without enabling fast dispatch early.
- [ ] BI1-BA3: implement the fixed live-audit body, omitting only the allowed immutable
  reparsing and retaining every fresh mutable check.
- [ ] BI1-BA4: causal/security/differential tests and independent exact-source review.
- [ ] BI1-BA5: actual original native 60-second completion and full startup acceptance.
- [ ] BI1-BA6: integrate current media/runtime source, service/route/character journey.
- [ ] BI1-BA7: physical-device, native-storage, accessibility and release acceptance.

## BA2 construction checkpoint — isolated draft, November 10

The original `_capture_engine` now preholds its literal generic-checker row before
helper callbacks, reuses that exact row in engine functions, constructs the
three-field immutable audit record before the generic checker, retains all full
generic/post-callback checks, and returns the literal record with final identity
joins. A distinct future fast checker still needs its own independently preheld
row. No immutable-schema parsing has been removed.

Three construction-only DATA controls pass on actual Python 3.14.9 and 3.11.15
with the same source maps and no skips. They prove literal engine/layout/checker
joins, presence of the actual record before the validator callback, tuple
immutability, and the distinction between an original record and a coherent DATA
copy. Independent bounded source review found no concrete issue in that subset.

**This draft is not an integrated candidate.** The immediate parent now retains the literal record in environment field 7
(environment width 8); remaining consumers must migrate. Original EntryOrigin/STARTED/CELL/lineage/
Scope root custody, both publication windows and selectors remain incomplete.
No lost-return/copy refusal, fast dispatch, startup, feature or deployment pass is
claimed. BA2 stays unchecked. Do not deploy or merge this draft into the working
media candidate until the coherent integration and its causal review are complete.


### BA2 immediate-parent checkpoint — November 10

`link_factory_origin.capture` retains the literal engine capture return, rather
than constructing an equivalent record. Its DATA validator requires the engine,
layout and uniquely held checker row to match that record before the complete
generic audit, and rejoins record identities after that callback. The selected
helper capsule remains at environment field 6; no existing field is repurposed.

Eight focused cases pass on each actual Python 3.14.9 and 3.11.15 interpreter,
with unchanged source maps and zero failures/errors/skips. In addition to the
three engine construction cases and existing real parent-capture control, a
profile callback observes the actual return and three negative cases replace
individual record fields. These are DATA controls, not original-root coherent
copy rejection. Independent read-only review accepted this bounded delta; it did
not independently rehash the reported test receipts. Private receipts:
`/private/tmp/hq-zr13k0gx/receipt.json` and
`/private/tmp/hq-6s1f9j83/receipt.json`, bound to HEAD b0502551 plus the tested
source delta. EntryOrigin, lineage, Scope, final publication and selectors remain
pending. Full BA2 and startup/deployment acceptance remain open.

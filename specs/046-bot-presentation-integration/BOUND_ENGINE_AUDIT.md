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

## BA3 dispatch clarification — November 10

Independent architecture review resolved the generic-versus-rooted phase split
before implementation. Keep the existing three-field record unchanged: field2
remains the literal generic-checker row. A distinct fixed `_engine_live_tail` row
must be held before capture callbacks and retained by identity exactly once in
original engine function rows. Extend the complete generic required-role checks;
do not nominate the live function from an exported replacement or a new carrier.

Keep `link_factory_origin.current(origin)` explicitly full generic for capture,
EntryOrigin construction and standalone DATA. Introduce a separate strict rooted
entrypoint, tentatively `current_started`, captured as another original parent
function row without shifting existing row indices. It must require independent
original EntryOrigin/STARTED/CELL/invocation/lineage/record joins before selecting
the held live checker. Missing/torn roots refuse; there is no implicit generic
fallback from failed rooted eligibility. Pre-entry callers remain explicitly
on the existing full generic path. Actual Scope callers additionally join their
preheld original record at both publication windows and every selector.

The rooted parent body must preserve every parent/module/type/selected-helper
mutable check and post-callback reseal while replacing only the full engine DATA
parser with fixed original bound live dispatch. Its new row/code/default/closure
provenance and exact count must be included in original capture, both inline
publication seals, selectors and causal controls. Authenticate raw defining
module/root dictionaries before any lookup; do not call a current exported
root helper to bootstrap its own authority. No function/primitive is supplied by
an external caller. The independently held checker receives the literal original
engine/layout arguments directly.

This is an implementation clarification, not a trust-model waiver or accepted
optimization. Generic/rooted differential tests, original missing/copy/lost-return
refusals, live mutations after earlier success, both publication grafts and
current/minimum suites remain required. Fresh-probe normal and the original
60-second full native contract stay open; no performance or device acceptance is
inferred from the root-custody tests.

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
(environment width 8); remaining consumers must migrate. Original EntryOrigin/STARTED/CELL/lineage
now retain the appended record, while Scope root custody, both publication
windows and selectors remain incomplete.
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


### BA2 original-entry/lineage checkpoint — November 10

Original EntryOrigin appends audit_record at index11, NativeFileLineage at index5;
existing link-policy indices10/4 remain unchanged. Entry capture retains the
actual parent record before validation/constructor callbacks; the constructor's
field-identity seal includes that record. Owner startup holds it before owner
construction and passes it to the original lineage allocation. Invocation joins
and original STARTED/CELL retained binding require the same record, without
caching a generic validator verdict or enabling a fast path.

Twenty focused cases pass on each Python 3.14.9 and 3.11.15 interpreter, source
maps unchanged, no failures/errors/skips. They include original module entry,
legacy nonadmitting defaults, entry-constructor coherent-record-copy refusal,
and owner-constructor replacement/copy/lost-return/reentrant refusal before native
bootstrap with no replay. Receipts: `/private/tmp/hq-590go5qa/receipt.json` and
`/private/tmp/hq-c6e22gat/receipt.json`, tested HEAD5b8b709 plus source delta.
Independent read-only source review found no introduced blocker in the entry/
lineage production delta. Reported test receipts were not independently rehashed
by that reviewer. The real-child lineage assertions were extended but that child
was NOT executed in this tranche. Scope, both final publication windows and
selectors still require migration, so full BA2/startup/deployment remain pending.


### BA2 retained-Scope/selector draft — November 10, validation ongoing

Scope appends native_link_audit at index18, preserving blueprint17. Original
entry/lineage/parent record joins now reach both final publication windows and
native metadata/link selectors; the exact generic checker row is joined to the
record in both inline final audits. The common registration tail rejoins actual
ENTRY_ORIGIN, STARTED/CELL and source invocation for linked scopes. Legacy
non-link scopes retain None; fresh-probe constructor expected values explicitly
include that nineteenth nonadmitting field. All full generic and mutable audits
remain; no BA3 optimization or fast dispatch is enabled.

Independent review found two draft issues: new mutable entry-namespace lookups
needed fresh string-key fences before reads and after validator callbacks; the
fresh-probe exact constructor seal needed the appended None. Both source fixes
are present and received bounded re-review. No draft was deployed. Their causal
boundary tests and real fresh-probe acceptance remain pending.

The 115-case regression selection passes on Python3.14.9 and3.11.15 with unchanged
source maps/no failures/errors/skips, receipts hq-v69cplt4 and hq-mhy7nt02. An
existing foreign-sys-root control initially failed on both draft and unchanged
baseline (hq-9gaypkjk/hq-6_xgxxj5 versus hq-kbtcrffe): it injected before retained-
helper capture and therefore hit that earlier refusal. Its injection now occurs
at the actual engine capture call; it observes the returned record field0 and
restores the alias before the parent resumes, preserving the original specific
factory-refusal assertion. No production guard was weakened to make it pass.

The original instrumented publication normal + native traversal contracts both
still time out at their unchanged60-second deadlines (hq-pyrvx267). Publication
stage evidence reached actual Scope construction and last selected return by
2.71seconds, so early negative boundary tests remain feasible even though full
normal traversal is blocked. The separately unobserved normal Scope completion
also times out on current Python (hq-l7uz7m32); minimum Python3.11.15 run also timed out (hq-vbejtxtl). None of this establishes BA2 completion, startup/image delivery or
deployment acceptance. Preserve failures rather than widening deadlines.


### BA2 actual negative-boundary results — November 10

Both original publication-window coherent audit-record grafts pass on both
runtimes: hq-3muu5aa2 / hq-6owt7lpp, two cases each. The synthetic actual-root
journey keeps independent EntryOrigin/STARTED roots while grafting a coherent
copied record/environment/parent/lineage into the current invocation. Real
publication refuses, no registration/success return occurs, and original ledger,
no-replay and failure checks remain. Existing layout/helper graft fixtures now
preserve the appended environment field rather than relying on a truncated schema.

Late entry-key collision at the actual selector's registration-tail and generic-
checker returns, plus malformed entry DATA, pass on both runtimes:
hq-elaz3d9x / hq-e0r7dk9n, three cases each. The actual original Scope/record/
STARTED/CELL witnesses are asserted outside production handlers. No foreign
attribute/equality hook, new selected native effect, ledger charge/attempt or
inflight work survives. These are full early-boundary negative journey tests,
not fabricated registrations or fake authorization. Profiling costs about50s
per case but each meets its unchanged60s deadline. No runtime timing improvement
is inferred. Real normal fresh-probe flow and full normal traversal are still
unqualified; BA2 remains open pending complete review/coverage.


### BA3 cost diagnostic — full generic DATA, not a startup pass

An isolated unchanged-source probe used actual Python3.14.9 and3.11.15. After five
warmups,100 unobserved complete generic audits took0.10044s and0.11786s respectively.
A separate10-call line-traced diagnostic attributed about49%/48% of traced time
to immutable layout parsing and37%/40% to dependency checks. Trace overhead changes
these proportions and they are not unobserved phase costs. No checker/schema/
authorization behavior was changed; all110 observed/unobserved returns per runtime
were the literal original engine. The production file hash stayed unchanged.

Private probe `/private/tmp/hermes-bound-audit-cost-probe-20261110.py`, results
`/private/tmp/hermes-audit-cost-4zxa7nid/current.json` and `floor.json`.
This supports targeting original-bound immutable parsing first while retaining
fresh mutable dependency checks. It does not predict end-to-end speedup or close
any native/startup/feature gate. BA3 implementation remains pending.


### BA3 fixed live body — unwired source draft, November 10

`_engine_live_tail(origin,bound_layout)` now exists as a separate fixed target.
Capture holds its literal function/code/globals/defaults/keyword-pairs row before
callbacks, retains it exactly once in engine function rows, and rejoins it after
the generic callback. Record3 field2 remains the original generic checker row.
Generic schemas explicitly require the additional fixed role; generic validation
remains complete. No startup/parent/Scope selector chooses the live target yet.

Independent source review compared the two bodies with AST normalization: only
the signature/docstring and immutable layout-correspondence traversal differ.
The live body replaces that traversal with literal bound-layout identity/shape/
dependency joins. All other mutable/dependency/role/class/function/kernel checks
remain text-equivalent. Its future rooted caller MUST authenticate the live row's
own defaults/code/builtins/closure before invocation; the body still bootstraps
primitive checks from the generic row. Direct canonical DATA tests are not proof
of that caller provenance or root authority. No unrooted caller is enabled.

124 selected cases pass on each Python3.14.9 and3.11.15, source maps unchanged and
no failures/errors/skips: hq-jhako9cy / hq-79w2czdj. They include all prior113 generic
DATA cases, actual real entry/lineage, literal early live-row retention, copied
layout refusal, fresh missing-None/value/reordering differential controls, code/
export/keyword drift after earlier success, and live-checker code/keyword mutation
at the actual generic-validator return during capture. No foreign callback runs.
The earlier122-case receipts hq-e7wj_yhn / hq-r0vdos61 remain historical partials.

This is not BA3 coherent integration or a demonstrated speedup. Strict rooted
parent dispatch and actual publication/selector callers remain to implement;
full native60s and fresh-probe/startup/feature/device/release gates remain open.


### BA3 strict rooted parent body — source component, November 10

The fixed `current_started` parent entrypoint is now appended at own-function
row7 without moving rows0–6; all fixed parent-width contracts now require8 rows.
`current` remains the complete generic capture/DATA entrypoint. The new body
preserves the original parent/module/type/selected-helper checks, but before
selecting the held live checker requires the actual captured entry module/classes,
EntryOrigin, STARTED/CELL, owner invocation, native lineage and original record.
A held native owner-dictionary descriptor avoids Python getter nomination. The
live row's exact code/globals/builtins/defaults/keyword contents/closure are checked
before direct original-engine/layout dispatch and again after the callback.
Original roots are rejoined before dispatch, after return and before final return.
Missing roots refuse; this is not an implicit generic fallback.

Independent AST comparison found no original mutable statement omitted beyond the
intended engine dispatch replacement. Review caught a missing exact owner-type
recheck after the live callback; all four descriptor reseals now check the exact
original type first. An actual callback changes the owner to a compatible subclass
with trapping dictionary/getattribute hooks; exact refusal and zero hooks are
asserted after native restoration. The draft was never deployed or selected by
production callers. Bounded source correction and fixture fidelity were reviewed;
execution receipts were not independently rehashed by the reviewer.

213 selected cases pass on each Python3.14.9 and3.11.15, sources unchanged and
zero failures/errors/skips: hq-ztj9szti / hq-1gn44cyv. The selection includes the
complete factory DATA suite, earlier generic/live cases, real entry lineage, and
real early started-root positive/negative controls. The latter assert literal
engine/layout arguments, original STARTED/CELL witnesses, exact RuntimeError args,
completed after-return mutations, and zero foreign calls. The first broader run
(hq-8r5irsvp / hq-3v1blsq8) had two stale observer failures indexing engine6 instead
of record3; only those test observers were migrated to field0, preserving their
original earlier-helper-versus-later-engine code-substitution refusal assertions.

No Scope/metadata selector chooses current_started yet. Remaining original generic
engine calls also need a reviewed rooted dispatch path with fresh original-custody
checks; do not replace arbitrary DATA calls or add fallback/cached verdicts.
Both publication seals, actual selectors, their causal observers and unchanged
native60s/full fresh-probe/startup gates remain to qualify before any BA3 acceptance.


### BA3 actual Scope/selector activation draft — November 10

Retained Scope link_rejoin now selects parent ownrow7 current_started; metadata's
closed selector authenticates that row and the independently held live checker.
It holds actual original STARTED/CELL/invocation/lineage/Scope record roots before
callbacks, uses native owner-dictionary inspection with exact original class,
and reseals roots plus both callees' complete provenance after return. No caller
selects a current exported helper. Pre-entry and standalone current remain generic.
Other direct generic engine calls remain unchanged.

Review found the new metadata postcallback needed callee-provenance reseals in
addition to roots; both parent/live code/export/globals/builtins/default/keyword/
closure are now rechecked. Exact actual return-event code/default/export mutations
have dedicated original-root journey cases. Local observer arming at the actual
selector avoids unrelated global profiling. The record/negative assertions remain
outside refusal handlers and foreign code frame events are counted independently.
Bounded source correction and fixture fidelity were independently reviewed.

Integration first failed before injection because blueprint_factory, then
_scope_blueprint_guard retained the previous own-width7. Both were corrected to8,
with positive generic entrypoint coverage. hq-ivmr3ycp/hq-teu_tomj and
hq-cp5yfoxm/hq-3895w9t3 plus the selector failures hq-jrb_r4tp/hq-h3n3beox preserve
those setup failures. Native hq-ihnk_bzp / hq-eqtiydf9 are early2–3second refusals,
not timeouts. Final width-positive/two-graft controls pass on both runtimes:
hq-78fh5hsx / hq-kobzecvf. Parent-return provenance reach case hq-9ewu5mn1 passes.

The final current selection hq-cz1n8gu7 passes223 cases, no skips/errors/failures,
sources unchanged; minimum run is active at this checkpoint. Original native
hq-51u5_0w2 returns to60second timeout, reaching event4 at51.8047s with44 typed
observations/dead capsule1/work963/reserved0. Generic engine calls2810 (earlier
8383) and original parent80 (newparent not instrumented) do not close performance.
Owner_guard inclusive31.31s/runtime7.72s overlap; native/regression runs overlapped,
so no intrinsic timing comparison is claimed. All original native operation,
retirement, close, startup, fresh-probe, feature and device gates remain intact.


### Next candidate: selected-helper bound schema (not implemented)

Independent source/performance review identified repeated selected-helper schema
parsing as the next permitted slice, rather than deleting owner/parent/recipe
audits. It requires a narrow additional construction contract before code:
retain an actual selected packet/layout/live-checker return in an appended helper-
capsule field, preserving existing indices. A literal layout binds original packet
rows, immutable key/value columns and expected references. Its fixed livechecker
row is held before callbacks and freshly authenticated by the original parent.
Keep retained_binding_origin.current(packet) complete for capture/standalone DATA.

Strict started callers must establish independently held original entry/root/
capsule/layout pointer eligibility BEFORE selecting that livechecker; they cannot
bootstrap eligibility from a matching packet or layout. No prior-success token,
implicit generic fallback or cross-callback verdict. Both final Scope copies and
post-engine parent seals need the same rooted immutable-only interpretation.
Every7-module live key/cardinality/static identity/exclusion check,41-class bases/
complete members/dispatch,33-function code/globals/builtins/default/keyword/closure
and all cross-module aliases remains fresh. Counts refer to the current pinned
schema and must be verified before implementation, not hardcoded as universal.

Required causals include packet/layout/capsule/environment/invocation coherent
grafts against independent EntryOrigin/STARTED/CELL at both publication windows;
lost factory return with no recovery; checker provenance before/after callbacks;
missing-None/colliding/GC-mutated keys, dynamic class/function/builtin/alias drift
after earlier success; unchanged generic malformed DATA behavior. Current/minimum
actual-root normal and original60s native gates remain mandatory. This candidate
is not a guarantee of sufficient speedup and is not permission to remove audits.


### Registration getter correction — experimental selector only

Source review confirmed that exact NamedTuple registration instances still have
mutable Python classes: a field property or __getattribute__ changed at the live
checker return could execute during an attribute-based root rejoin. The older
generic-selector final seal shared that pattern; this is not evidence of a newly
exploited/deployed incident. The character draft has not been deployed.

The closed selector now preholds its actual registration kind and original class
row from the literal engine dependency table before validators. Registration
field reads use native tuple.__getitem__; four callback/root fences require exact
kind, original bases, full key types/cardinality and every original member identity
before root use. This catches both same-key property replacements and added
inherited dispatch hooks. No mutable schema or class-state verdict is cached.
Independent finite source review accepted that correction and fixture fidelity.

Actual live-return scope/lineage/entry_module property and __getattribute__ cases
join the previous8 selector controls. Mutation completion, canonical roots,
zero getter/foreign-frame hooks/effects and ledger/cleanup state are asserted
outside handlers, after restoring class state. The current2case smoke passes
hq-v7uc_gye, minimum smoke hq-b4vevh9m. Final227-case source qualification current
passes hq-7ztfc_ig; minimum hq-3kewsfft is active at this checkpoint. Earlier223
hq-cz1n8gu7 / hq-2rauat42 results predate this refinement; native60s failure
hq-51u5_0w2 likewise belongs to that earlier executable snapshot, not a fresh
full-normal run of the getter correction. Whole startup remains unproven.


### Final activation source checkpoint — November 10

Final227-case selections pass on both Python3.14.9 and3.11.15 with unchanged source
maps and zero failures/errors/skips: hq-7ztfc_ig (current), hq-3kewsfft (minimum).
These include all12 actual selector late-root/callee/registration-dispatch cases,
both original publication record graft windows, full generic/factory DATA and
actual started-parent/entry lineage controls. Registration getter correction is
therefore verified for that bounded source/callback matrix, not a deployed incident.

With other qualification runners terminal, the final exact-source original native
contract hq-7f4l9y4c still fails at unchanged60s (one actual failure, source unchanged).
It reaches path event4 at51.0161s,44 observed/typed, retired capsule1, work963 /
reserved0. Generic engine2810, runtime5286, owner5276 and original-parent80 counts
are diagnostics; completed inclusive times3.21s/7.65s/31.08s/0.19s overlap, and the
new started/live helpers are not separately instrumented. This is not full native
or startup acceptance and does not justify deleting any owner/parent/recipe audit.
The next selected-helper immutable-layout proposal remains unimplemented; full
fresh-probe, service, routes, character rendering, device and release gates stay open.


### Selected-helper construction contract and unwired factory — November 10

Keep `capture()` returning packet6 and `current(packet)` complete. The new fixed
`capture_bound()` independently collects candidates, preholds generic/live function
code/default/keyword/global/builtin/role provenance before checker callbacks,
validates packet6 generically, builds original immutable columns, validates again
and returns literal record3 `(packet,layout,live_row)`. Layout4 is `(packet,
module_columns,class_columns,function_columns)`; each column row retains its actual
packet row plus immutable original key/value tuples (function columns concern
keyword pairs). The live row exists before the first checker callback; the record
exists before the second, and its literal return is retained without reconstruction.

`current_live(packet,bound_layout)` currently retains the ENTIRE generic body plus
an exact layout-shape/packet-identity precheck. No immutable parsing is omitted yet.
Neither new factory nor target is selected by a parent/Scope/native caller. This
is construction DATA, not original root authority, live currentness cached across
a callback, optimization or startup acceptance. Independent AST/source review
accepted that bounded stage and callback fixture fidelity; receipt rehashing was
not independently performed by that reviewer.

The parent integration contract remains to implement: append the actual bound
record at helper-capsule7 while keeping packet6 at capsule6 and old fields intact;
retain original capture/current roles0/1 and append capture_bound/current_live.
Prehold actual factory and expected live-function provenance before calling it.
After return, authenticate the literal returned live row against those original
held components and retain that actual row, not a newly equivalent tuple. Original
parent/EntryOrigin/STARTED/CELL/lineage/Scope must join the actual capsule/layout
record before selecting immutable-only live audit. Standalone generic DATA stays
complete; missing/torn roots refuse rather than using a generic fallback.

Initial hq-laxm439e/hq-qzm5uc6v runs had12 failures before callbacks: the collector
shadowed the held checker-provenance namespace. Only collector locals were renamed
to candidate_namespace; provenance references remain separately held. Earlier
review missed that shadowing and later finite re-review confirmed the correction.
Final hq-pymlf1yp/hq-5mzec9mu pass240 selected cases each Python3.14.9/3.11.15,
sources unchanged, no failures/errors/skips. These cover the existing helper and
factory suites plus12 new cases: packet/column/literal-return/preheld-row checks and10
first/second checker-return code/export/keyword mutation controls with external
mutation/reach/zero-foreign-call assertions. The earlier failed cases are not
construction proof. No full native rerun or timeout fix is claimed for this
unwired construction addition; all original qualification gates remain open.

Native refusal-channel repair (2026-11-10): the unused selected-layout factory
and live target previously could invoke a changed custom error constructor
while refusing code drift. The actual first/second checker-return causal test
reproduced this in hq-dgjb35ts; that failure is retained as evidence. New factory
and live-target refusals now use their held native RuntimeError; the factory
also authenticates the original custom-error export, bases and complete members
before and after its unchanged generic callbacks. Its own collector refusal
paths use the same native error. Original capture/current API behavior remains
unchanged; no claim covers all unrelated asynchronous or legacy error paths.

Final dirty-source suites hq-ur3y2n4e (Python3.14.9) and hq-74h80708
(Python3.11.15) each passed243 tests, no failures/errors/skips, unchanged source.
New callback cases require exact native RuntimeError/fixed refusal args and zero
foreign constructor calls; direct malformed live DATA has the same assertion.
The record remains unwired: parent-capsule construction/actual-return retention
and independent original root eligibility are next. No full native rerun,
startup-time improvement, deployment or physical-device acceptance is claimed.

Selected-helper parent integration (2026-11-10, focused qualification passed): the
helper capsule now appends its actual capture_bound record at field7 and retains
packet6 at field6. Existing capture/current roles0/1 remain; capture_bound and
current_live are appended roles2/3. Before dispatch the parent authenticates the
factory defaults against the original checker/live function components, native
primitives, schema objects and original error-class members. After return it
compares the returned live row to the preheld original components, retains that
actual row by identity, and immediately reseals the complete helper prefix before
engine capture. Lost-return recovery remains forbidden by the one-attempt latch.

Both generic and started parent validators still invoke the complete generic
selected-packet validator and additionally validate every immutable layout column
against the actual packet rows. No selected immutable parser has been omitted.
Scope retains the original record/layout from the actual EntryOrigin capsule;
its rejoin and both inline publication seals compare those exact pointers.
Additional tests cover the actual literal return, loss, six default nomination
refusals, nine malformed column/record zero-hook refusals, five late return
code/export/default drifts refusing before engine capture, and coherent copied
selected packet/layout/record/capsule grafts at both publication windows.
Protected combined qualification is in progress; construction or generic DATA
consistency cannot establish original-object authority or startup acceptance.

Next-stage source review (not implementation acceptance): existing original
EntryOrigin -> link_policy -> environment -> helper capsule retains enough
authority; no new success token is needed. In current_started retain the native
primitive/helper prefix before any dispatch, then move original started-root
proof before selecting current_live. Add exact native tuple shape/index fences
for packet6, module rows7, class rows41 and the entry/owner/invocation/lineage
rows. Resolve the canonical entry module through the held real registry; join
its namespace and original ENTRY_ORIGIN/STARTED/CELL/OWNER. Read owner storage
through a held native GetSet descriptor from the actual original owner class,
not a descriptor nominated by unvalidated member-pair DATA. Native tuple reads
and exact class/owner type fences must precede all project getters.

Eligibility must join actual entry owner_type, invocation/lineage, ready/failed
state and original helper capsule/packet/record/layout/checker pointers before
calling the preheld selected live function with the original packet/layout.
Reseal original roots and callee provenance after return and retain final mutable
checks. Missing/torn/pre-entry roots refuse without a generic fallback. Generic
pre-entry capture/current retain full immutable DATA validation; all namespace,
class, code/default/closure/alias and runtime ownership checks remain live.
Add pre-live malformed-root zero-hook/zero-live-call controls, coherent grafts
and post-success mutable drift cases before claiming any parsing omission.

Final integration suites hq-z5lgnxnr (Python3.14.9) and hq-n9wr8h2v
(Python3.11.15) each pass417 tests, no failures/errors/skips, source unchanged.
The first current run hq-nofdr107 also passed417; the final pair additionally
includes the corrected factory documentation. The reviewer accepted the finite
source/causal-test fidelity and next-boundary plan; execution receipt hashes
were not independently rehashed by that reviewer. No selected parsing reduction
or native timing acceptance follows from these focused passes.

Further semantic binding correction: hq-zfr_32l2 actually reproduced a coherent
current_live error-default plus factory live-pair snapshot nomination; the parent
accepted this self-consistent candidate. Before enabling the unused live helper,
the parent now requires its live keyword dictionary to have exact native string
keys/cardinality1 and _error identical to the parent's independently held native
RuntimeError. The new causal requires refusal before any factory or foreign call.
Finite independent source/test review accepted this correction. Expanded418
current/floor suites are active; the prior417 passes do not qualify this delta.

The standalone original native test hq-0ga3ww3d, before this final default guard,
failed by TimeoutExpired60s (not an early setup refusal), with unchanged source.
Last progress was event3 at48.5717s,44 observed/typed, work487/reserved0. Inclusive
diagnostic timings overlap and are not an intrinsic speedup claim. Source after
the final guard still requires a fresh native run alone. Full native/BA3/startup,
character delivery, physical device and release gates remain open.

Final post-guard qualification: hq-qqfoonca (Python3.14.9) and hq-a3g88y8t
(Python3.11.15) each pass418 tests with unchanged source, no failures/errors/skips.
The final native run hq-2r2e92z5 ran alone and again failed TimeoutExpired60s,
with source unchanged; it is not an early setup error or native acceptance.
The integration and semantic binding are reviewed/tested source progress only.
Next work must complete original-root-before-selected-live eligibility and the
reviewed immutable-only audit reduction together, preserve all fresh mutable
checks and generic DATA validation, then rerun the unchanged full native gate.
No newer source was deployed and no physical build was changed.

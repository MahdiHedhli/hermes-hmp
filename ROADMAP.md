## November 9 — shutdown ownership checks pass; media integration remains open

MR-PUSH1 source `fc06ef3` retains push task/coroutine intents, one shielded close
owner, and actual borrower drain beyond the bounded network close. The listener carries
push debt until drain finishes. Independent review caught that task-only cancellation
could leave native authorization threads running; the final repair separately tracks
and shields authorization/key/gate borrowers. A blocked real-thread causal test proves
cancelled dispatch/drain waiters do not retire that work early. Both pinned runtimes
pass 500 selected tests unchanged, zero failures/errors/skips; finite read-only review
accepted this repair. This proves bounded task/borrower settlement, not successful relay
resource closure or all native lifetime contracts. Failed dispatcher startup retention,
other borrowers, partial adapter recovery, native media authority/migration and physical
qualification remain open. No deployment, provider/send, grants or media activation.

MR-START2d source `574899c` pins the approval test generation to the original
listener context/service and immediate shutdown fence. Copied context fields cannot
authorize a replacement or revive a retired generation. Three new synthetic cases
cover replacement/restore, pre-start replacement and lost shutdown publication.
491 combined tests pass unchanged on each pinned runtime, zero failures/errors/skips;
one outdated ordering-only fixture was corrected to implement the current drain contract.
Independent/full-native and physical qualification remain pending. Source inspection
also confirms a separate push retirement gap: bounded close is not actual borrower
drain and task creation acknowledgement loss needs retained ownership. That gate,
partial adapter recovery, other borrowers, migration and native media authority remain
open. No deployment, permission change, push send or media activation occurred.

MR-START2c source `c5222b6` retains the optional operator-read service before
startup, gives startup one shielded actual task, and joins that task before teardown.
Caller cancellation cannot abandon the service; unknown task-publication acknowledgement
cannot retry startup or certify cleanup. Original-service replacement is refused before
any foreign service is stopped. Five new synthetic cases cover cancellation, startup
failure, pre/post-enqueue return loss and replacement. Both pinned Python runtimes pass
380 selected tests with unchanged source and zero failures/errors/skips. This is not
independent/full-native review or device qualification. Approval/push auxiliary startup,
partial adapter recovery, all Store borrowers, migration and native media authority
remain open. No deployment or media opt-in change; images/characters remain unfinished.

MR-START2b2 source `3eee7d2` adds one retained shutdown attempt and checks the
original context/resource cohort after cleanup waits. Lost task-creation acknowledgement
cannot replay cleanup or certify Store drain. Three synthetic substitution cases verify
that context, direct-send dependencies and runner replacement stop further cleanup.
Both Python 3.14.9 and 3.11.15 pass 375 selected cases with unchanged tracked source,
zero failures/errors/skips. This is bounded source evidence, not full lifecycle or
physical qualification. Auxiliary startup publication, partial adapter recovery,
all Store borrowers, migration/native media authority and device/release gates remain
open. No new deployment: both hosts retain `5ecd2ba`; bot characters and host-local
images are still unfinished. The broader feature goal stays active.


MR-START2b1 source `641e39c` retains the original runner/site before awaitedstartup
effects and one shielded actualstartowner. Stop fencesstartup and joins thatowner
beforecleanup; cleanupreturnloss keeps runner/knownstopowner without replay orfalse
closedproof. Unknownstart/watcherpublication staysunresolved. Both370combinedcases
pass unchanged on3.14.9/3.11.15 plusRuff; independentfinite review found no new
concreteblocker in thisbounded slice. Six new syntheticstages are not allnative/
Store qualification; blockedsetup maydelaystop indefinitely. Context-wideteardown,
stopownercreation, auxiliaryservice/dispatcher publication, adapterpartialrecovery,
otherborrowers, builder/migration/nativepublication and physical/release gates remain
open. No checkpointdeployment; image service staysinactive and livehosts remain5ecd2ba.


Read-context parity audit is completed: synthetic16ca49c control reproduced missing
callerContextVars in directpool submission. Perread copy_context+Context.run now
restores to_thread semantics without changing actualFuture/debt/drain. Independent
finite review passed; both593-case backport and364-case feature suites pass on
3.14.9/3.11.15 plus Ruff/Doctor. Pinned5ecd2ba7e580e86e3d91bcae38f0584bcc366077
is deployed on bothhosts:109files, freshmatched gateway/listenerPIDs, expectedTLS,
and unchanged configuration/device-controls/schema snapshots verified. Native
versions stay0.22.7/0.23.0; priorhealthstates remain, includingLucas/Serenity unavailable
onLLY520 (aggregateexit1). No realcontextvalues inspected/logged or nativeprofile/
authbypass effect claimed. Onlythissmallreadrepair is deployed; featurebootstrap,
mediaretirement/service remainuninstalled. Partialbuilder/listenercleanup, other
borrowers, migration/nativepublication and physical/release gates remainopen.


MR-START2a source `bd7feef` retains the actual componentFuture and successfulreturn
ctx/Store/boundclose across cancellation or unknownenqueue. Explicitcleanup can
close an unpublished context once afteractualFuturecompletion, rejoining theheld
scope aroundgenerationcallbacks. Initialclose/cohort substitutions were reproduced
and fixed; partiallistener resources are retained rather than prematurelyclosed.
CallerContextVars are copied beforeenqueue and isolated inworker; missingtransfer
was reproduced beforefix. Both363 combined cases pass unchanged on3.14.9/3.11.15,
Ruff passes and independentfinite review found no furtherconcrete blocker. Failed-
builder allocation/partialrunner/TLScleanup and fullnativeauthority remainMR-START2b
or latergates. Audit earlierread-worker backport contextpropagation next; no live
profileeffect/authbypass inferred. No sourcebranch deployment/mediaactivation; both
hosts remainc7482f1, and physical/release qualification is stillpending.


MR-START1 source `d524059` serializes adapter connect/disconnect and blocks retry
or false-connected results after unresolved startup/shutdown. A retained730e908
control reproduced2 component workers active together; successful concurrentcalls
now share one syntheticTLSlistener and failed attempts remain sequential. Both350
combined cases pass unchanged on3.14.9/3.11.15 plus Ruff; independent finite review
found no further concrete blocker. Only explicitcleanup with actualStorecloseproof
clears disconnect uncertainty; startup uncertainty stays latched. MR-START2 actual
bootstrapFuture/partial-resource ownership and recovery are NOT implemented by this
exclusion lock. No live incident/deployment or media activation claimed; livehosts
remainc7482f1. Other borrower, migration, nativepublication and physical/release gates
remain open. This source-only protection is not a runtime qualification claim.


MR-LIFE2b source `5f684b8` retains each original adapter server/context/Store/close
owner before dropping its listener pointer. Pending/failed/unknown retirement blocks
connect beforeopen_components; cancelled waiters do not cancel actualowners and
unknown creation/close outcomes never trigger automatic replay. Originalscope is
rejoined afterdrain andaftergenerationcleanup; a failing40ac2e0 control reproduced
the missing server-reference recheck and is retained. Both342-case combined suites
pass unchanged on3.14.9/3.11.15 plus Ruff, including25 existing adapter cases and9
new faults; independent finite review found no further concrete blocker. This is
boundedsource verification, not concurrent startup/allborrower/migration/native
publication or physical/release qualification. The adapter still starts no new
media service; both live hosts remain on c7482f1 with no changes this turn.


MR-LIFE2a source `13703e9` adds optional original-context media retirement retention
to HmpServer, defaultNone/noactivation. Network cleanup can finish while media debt
remains; actualstop+closed and originalctx/readservice/mediaowner/Store rejoin around
eachawait precede debt clearance. Both308-case combined suites pass unchanged on
3.14.9/3.11.15 plus Ruff; independent finite review found no further concrete blocker,
and the final guard wrap is AST-identical to reviewed d7dfcba. Initial305 run failed
two historical route-count assertions for the earlier GET diagnostics; exactroute
matching remains and that failed receipt is not qualified. Adapter Store-owner/
reconnect protection, broader borrower retirement, schema/native/config publication
and physical/release tests remain open. This is only the listener half of MR-LIFE2;
no adapter supplies the coordinator and deployed hosts remain c7482f1 unchanged.


Media-lane retirement source `1f8fd9a` now closes admission/publication before
awaiting original service workers and actor SQL settlement. It retains one owner
through waiter cancellation, unknown scheduling/submit outcomes and changed scope;
it neither closes Store nor claims HTTP/read/native borrowers are finished.
Both199-case combined suites pass unchanged on3.14.9/3.11.15 plus Ruff; independent
finite source/delta reviews found no further concrete blocker. Eight new cases
cover actual Store rollback, cancelled waiter, uncertain submission, creation/
callback acknowledgement loss and changed-generation refusal. Unknown creation
must stay owned by the future adapter and cannot justify dropping the Store.
This coordinator and media service remain unwired/uninstalled. Whole-listener
integration, migration/rollback, native/config publication and physical/release
qualification remain open; live hosts retain only the reviewed c7482f1 safety backport.


Minimal read-worker backport `c7482f131a5414c6b0d63ed5cb8ffb61b61fbfdc` is now
installed on ColPanicM2 and LLY520. Both51-case read/FD and592-case listener/adapter/
CLI/access/ownership suites pass on3.14.9/3.11.15; independent review, Ruff and
Plugin Doctor pass. All109 installed files, fresh gateway/listener PID binding,
expected TLS identity and preserved configuration/device-controls/schema snapshots
were verified. Native versions remain0.22.7 and0.23.0 respectively. ColPanicM2's3
profiles are ready; LLY520 retains ready Hermes/Belac/SchoolBot and prior unavailable
Lucas/Serenity (health exit1, not all-bots success). RSWORK1 is repaired in this
verified deployment; no live incident or production fault injection claimed. This
backport adds no media/schema4/CLI features and changes no grants or host flags.
Physical tests and separate image-service/native-authority integration remain open.


Read-service prerequisite source `aaa29aa` fixes a demonstrated lifetime flaw: a
cancelled asyncio.to_thread Task could retire capacity while its actual read thread
remained blocked. Corrected979fbe0 control reproduced0 instead of1 retained borrow;
the first control's cleanup timeout is separately retained. New actual concurrent-
Future/intent tracking passes191 combined cases on each supported runtime plus
Ruff; independent finite review found no additional blocker after setup reads moved
before capacity acquisition. AST readback confirms31 prior test definitions unchanged
by formatting. OPEN RSWORK1: the same pattern exists in deployed5e247a6 source; no live
incident observed. The fix is source-only until a minimal independently reviewed
backport is tested/deployed. This does not activate schema4/media service or qualify
all native/HTTP shutdown; physical image display remains pending.


CLI source `8b15a7a` now routes confirmed image-access decisions through the verified
one-exchange service, preserving exact typed consent and fresh context/readback.
The direct CLI Store write and any unavailable-service SQL fallback are removed.
Both186-case combined suites pass unchanged on3.14.9/3.11.15, full Ruff passes, and
independent finite CLI review found no concrete blocker. Actual confirmation/client/
service/actor/Store fixtures cover allow/deny/wrong/EOF while prohibiting the CLI
mutator; host TLS/live context is mocked, not runtime-qualified. Read-only status
and global mutating-command TTY guard remain. Adapter activation, actor/listener
retirement, schema4 quiesced migration, other-process/native/config publication and
physical/release gates remain open. No live permission/flag or deployed build changed.


Verified host IPC client source `3503b48` is now implemented but unwired. It checks
fixed private socket/peer/parent identity, exact challenge IID/nonce/generation,
bounded expiry and one-send unknown-outcome handling without SQL fallback/retry.
Independent review found no concrete client blocker. Both160-case combined suites
pass unchanged (35 focused service/client cases), full lint passes. The original
seven fake-server cleanup failures remain unqualified; the cross-version fixture
correction does not relax protocol checks. Live TLS/listener verification and exact
typed host consent remain caller obligations; the CLI's direct Store writer is not
yet replaced. No runtime activation/image display/release claim. Only two completed
owned synthetic scratch trees were removed after retained receipt/log/XML hash
verification, restoring about1GB; failed evidence and source remain untouched.


Independent review then found pre-submission allocation/registration and budget-return
loss accounting gaps. Source `e948e83` records the original intent before capacity
acquisition, cleans only proven-unacquired reservations, and retains/poisons unknown
acquisition without a guessed refund. Both148-case combined suites pass unchanged
(23 service cases), full lint passes, and independent delta review found no new
concrete blocker in the fix. Conservatively unresolved acquisition may block drain
indefinitely; it never authorizes Store closure. The service remains unwired, with
CLI consent/client, whole-listener retirement, native/config publication, migration
and physical qualification still open. Latest observed Mac capacity is443MiB free;
large builds/tests need a new capacity check. No broader feature completion claimed.


Mutation service source `be1f84b` passes142 combined read/FD/layout/codec/CAS/service
cases on both Python3.14.9 and3.11.15, plus full Ruff. The17 service cases now cover
malformed frames, waiting-client bound, foreign connection challenge/cohort, worker
timeout/cancellation and post-enqueue lost acknowledgement. A causal failing control
reproduced late wrapped worker diagnostics reaching the async log; the source fix
consumes that late exception without early worker retirement. The failed control is
retained. The service is still unwired and independent service review is pending;
no host/device/release upgrade or resolved native publication gate is claimed.


Separate operator transport source `b719992` now has a single-use connection challenge,
same-UID peer check, fixed private socket, bounded workers and actual concurrent-worker
retirement after timeout/cancellation. Seven synthetic socket/Store/actor cases pass
on Python 3.14.9 and 3.11.15; full Ruff passes. The initial test-module import and
missing fixture environment failures are retained, not counted as passes. This service
is unwired: no host starts it and no CLI human-consent path is implemented. Malformed
frame/capacity/ambiguous-submit and full lifecycle coverage, independent service review,
native authority publication, migration/rollback and physical display remain open.
These tests qualify only their observed cases, not local-image delivery or release.

The post-lint1,176-case minimum-Python suite now passes in a fresh capacity-qualified
run, matching the current-Python pass. The earlier floor run failed with ENOSPC
before final XML/receipt and remains unqualified; only completed owned synthetic
pytest scratch was removed, preserving and rehashing source/result evidence.
Separate namespace preparation `c3ae41b` passes56 read/FD/layout cases on each
Python version plus full lint; the default read socket/parser remains read-only.
A future media socket name/frame bound does not install a write handler. Challenge,
peer/cohort/admission and actual-worker lifetime integration remain incomplete.
No live permissions, host settings, installed build or deployment changed.

Operator response preparation `adf41e2` has attempt-bound committed/conflict/
refused/unknown codecs: committed means the exact requested decision and next
revision; other statuses carry no grant. Both69-case suites pass; independent
review found no concrete codec blocker. Missing/malformed post-write responses
must remain unknown, not refused. No transport or live permission route is enabled.
Accumulated lint cleanup at `ade8fce` clears full server/tools Ruff checks and360
focused regressions; a new1,176-case integration run is active, not yet qualified.
Runtime peer/consent/admission and native publication coordination remain open.

Operator executor preparation `d788615` now performs real coordinated Store CAS
and readback on worker threads with original listener/actor/Store binding and
pre/postcommit cohort/deadline checks. Both43-case suites pass: duplicate old
snapshots do not repeat a grant, post-CAS cohort drift rolls back, and committed
readback loss remains unknown/no replay. Independent source review found no concrete
blocker in this unwired layer and narrowing checks. It verifies no peer or human
consent; transport/admission/deadline provenance and native coordination are still
missing. No route/socket/CLI calls it, and no live permission or deployment changed.

Operator coordination task LM-ENT1-OP1 now has a strict request codec at1794e43:
closed fields, exact device/expected-state DATA, bounded parsing and canonical
signed64-bit decimal counters. Both35-case suites pass; independent review found
no concrete codec blocker. It is not a write endpoint or authorization proof.
Same-UID transport, actual listener/nonce/generation binding, typed operator
consent, daemon CAS/readback and unknown-response handling remain unimplemented.
No permissions, socket mutation service, host or installed build changed.

LM-ENT1-N1 now has exact native source evidence: checkout0f0e96fc's inspected
HMP authorization/routing path returns live Booleans and may enter profile scope;
it supplies no revision/read lease/pure publication claim in those exported calls.
Independent review confirmed this bounded gap, not whole-SDK absence or fresh
runtime-byte qualification. [Pinned contract census](https://github.com/MahdiHedhli/hermes-hmp/blob/23437de/docs/research/media-publication-native-contract-20261108.md)
describes the required native writer coordination. HMP Store/operator/lifecycle
work can continue independently; cached grants, polling and private scope shortcuts
are not substitutes. No native code, private settings, permissions or hosts changed.

Shutdown preparation `07a02c5` separates publication close from original Store
mutation retirement. Debt is reserved before begin and survives missing receipts,
close and drain timeouts; exact-receipt cleanup has independent bounded capacity
and never restores publication or implies a known commit. Both291-case suites pass;
independent delta review found no new concrete blocker under the fixed ended-SQL
handoff assumption. Unknown debt cannot be force-cleared or used to close Store.
The actor remains unwired; operator/native/config and actual listener lifecycle
integration remain unfinished. No production responsiveness or release claim.

Publication actor preparation `d6f57d4` adds bounded worker-to-listener handshakes
for the optional Store observer, refusing loop-thread waits and late acknowledgements.
Queue debt is retained until actual callback retirement; sticky failure/cohort drift
is checked after currency operations. Independent review confirmed the two identified
actor refinements fixed. Both287-case suites pass, including real Store worker and
synthetic deadline/allocation/failure cases. The actor remains unwired; operatorIPC,
full Store/lifecycle and native/config coordination remain absent. This does not
close the existing final-collector responsiveness defect or qualify deployment.

Store publication preparation now reaches real transaction boundaries: optional
construction-time observer at code `ab2fd5e` invalidates before SQL and records
confirmed commit/rollback certainty under the original lock. No begin receipt
means no SQL/settlement; lost SQL or observer acknowledgements never trigger replay.
Review found and confirmed repair of a None-receipt handling defect. Both280-case
Store/publication suites pass with matching server fingerprints (floor113b611 adds
documentation only). The observer is not installed by any listener. Startup/raw
helpers, other-process/operator writes and native/config coordination remain open;
no authorization, responsiveness, runtime or deployment clearance is claimed.

Publication preparation `385b1de` now has24 tests on each supported Python version,
including exact real-code line/return interruptions at begin, settlement, close,
candidate and publication-claim handoffs. No acknowledgement means the example
caller starts no write/sample/publication; completed definite settlement is not
replayed after a lost return. These examples do not qualify real CLI/store/native
orchestration, which remains unwired. Initial settlement defect is independently
confirmed fixed; causal handoff-test review is requested. P1 responsiveness, all
writer coordination, native/config evidence and device/release gates remain open.

LM-ENT1-P2 source `22e5a58` prepares an UNWIRED listener-thread publication
currency state machine: bounded single-use request/cohort tickets, invalidation
before mutation, nested pending barriers and sticky uncertain outcomes. Independent
review found a partial-settlement gap; source now poisons before releasing pending
and retains the barrier across interrupted advancement. Fourteen tests pass on each
Python version. Re-review and more interruption coverage remain pending. This
helper supplies no authentication or writer-coverage proof and does not fix P1
until Store/operator/native/config mutations participate. No live behavior changed.

Measured open blocker LM-ENT1-P1: an isolated synthetic150ms delay in a final
main-thread media settings callback causes151.5ms event-loop heartbeat latency
(baseline5.7ms) on exact f7f5084; source unchanged. This confirms the documented
responsiveness risk, not a live-host benchmark or access bypass. New diagnostics
remain undeployed. A bounded publication/authority design review is active; the
repair must preserve current authorization, deadline refusal and actual worker
permit lifetime rather than substituting stale cached permission.

Paired media source qualification: backend `f7f5084` passes both 1,063-case
combined suites (Python 3.14.9 and 3.11.15), zero failures/errors/skips and unchanged
source. Mobile `5ca14a9` pinned to that backend passes 66 client and 73 app/chat/
accessibility tests; whole client/app analysis is clean. Private scan has no new
findings, retaining its existing 170 baseline exclusions. These are scoped source
checks, not full release review, rendered/device acceptance or live serving.
Performance/contention, legacy fallback and safe migration remain open. No install.

The repaired media backend `f7f5084` now passes its combined 1,063-case current
Python suite with zero failures/errors/skips and unchanged source. The matching
floor run is active. Focused backend branch `feat/media-read-entitlement-20261108`
and mobile branch `feat/media-readiness-mobile-20261108` are published. Mobile
integration commit `5ca14a9` pins that exact HMP commit for reproducible source
review; mobile tests against this new submodule pin remain to be rerun. No live
migration, grant, opt-in, build installation or release occurred. Performance,
legacy fallback, migration quiescence and runtime/device gates remain open.

Media freshness regressions now have isolated negative controls: restoring the
matching prior server implementations reproduces stale HTTP 200 responses where
503 is required. One initial mismatched callback-count case was excluded and rerun
against the correct intermediate source; its mutation then reached stale delivery.
Candidate `f7f5084` remains unchanged and its combined 1,063-case current-interpreter
run is active; no result or floor run is claimed yet. These controls establish
regression sensitivity, not atomic revocation, performance or release acceptance.

Independent review found final-callback and request-context freshness gaps in
undeployed media backend `fb82aef`, despite its passing 1,059-case integration run.
Source `f7f5084` repairs post-callback media checks, original request/dependency
cohort binding, clock ordering and final IID/listener-generation seals. Both
89-case readiness suites pass, including causal callback/context regressions;
independent re-review verified the identified defects resolved on exact f7f5084.
This is delta review only. Performance/contention, non-atomic source reads,
legacy fallback revocation, migration and runtime/device gates remain open.
No source-review or release clearance, grant, opt-in or deployment is claimed.

Mobile media independence repair `463c6bf` keeps image inspection available when
the separate jobs/model diagnostic fails, preserving scope/generation checks.
All 67 combined UI/chat tests and six large-text accessibility regressions pass;
focused analysis is clean. Independent review, backend final-check latency,
rendered/device acceptance and schema/deployment gates remain open. No new install.

Mobile media UI source `6485c25` adds independent image-access guidance to the
chat overview readiness panel, with no grant/Fix action. It distinguishes missing
image rights, disabled host opt-in and unavailable API; existing scope/refresh
fences discard late results after bot changes. Ten focused panel tests and 56
selected-bot/Bot Chat regressions pass; focused Flutter analysis is clean.
This completes the first source UI path, not review/runtime/physical qualification.
Independent review, backend final-check latency and schema/deployment gates remain;
no new build was installed and no live rights/settings changed.

Mobile media lifecycle source `0dcbbb4` binds discovery and bot diagnostics to
the captured foreground API and original pairing lifecycle scope. Switching during
either await cancels the result; late revocation affects only its original host.
All 52 focused media domain/API/context and existing AR1 context tests pass;
focused analysis has no issues. UI profile/request-generation binding, visible
image guidance, independent review and device qualification remain open.
No live host request, permission change, build installation or deployment occurred.

Mobile media API source `467e576` now reads discovery and per-bot diagnostics
through the existing pinned authenticated transport. Discovery-only 404/405 is
legacy unknown; malformed success is protocol unknown; bot 404 remains a refusal.
No alternate route, remote grant, or feature mutation is attempted. All 53 focused
Dart domain/media-wire/existing-AR1 tests pass and focused analysis has no issues.
Context lifecycle integration, UI, independent review and device qualification
remain open. This source is not built/installed/deployed.

Both 256-case media-readiness/contract/plugin-surface suites at `fb82aef` have
now passed, zero failures/errors/skips and unchanged source. Mobile branch
`feat/media-readiness-mobile-20261108` source `46bee41` adds strict content-free
discovery/readiness DTOs: 34 Dart tests pass and focused analysis reports no issues.
This is decoder-only progress; authenticated API transport, context lifecycle and
phone UI are not implemented yet. No device/build/deployment qualification claimed.

Media-readiness discovery is implemented at source `e1edd5f` through authenticated
`GET /media-readiness/capabilities`: protocol support only, explicitly no remote
permission writes. Its 85-case current-interpreter readiness suite passes.
Contract documentation at `fb82aef` defines closed DTO axes, older-host 404 fallback,
per-instance/device/profile lifecycle and remaining review/qualification gates.
The broader 256-case readiness/contract/plugin-surface run is in progress; no pass
is claimed for it yet. Mobile decoder/display remains unfinished, and no new
backend source or permission/schema change is deployed.

Media-readiness final-delivery source `bbd75f3` rechecks authenticated bot/session
scope after the worker await and compares the private permission revision before
removing that internal snapshot from the wire DTO. Post-worker deny/regrant,
listener-generation drift and bot revocation tests reject stale responses.
Both 84-case readiness suites pass on Python 3.14.9 and 3.11.15 with zero
failures/errors/skips and unchanged source. This final synchronous recheck can
perform SQLite/native configuration I/O; event-loop latency has not been qualified.
Independent security/performance review, capability negotiation, mobile wiring,
broader contract tests and physical acceptance remain open. No live deployment.

Media-readiness causal tests at `d41750f` now revoke media rights or bot access,
change listener generation, or change host opt-in inside a sampled callback.
All discard the snapshot without a media DTO or unrelated controls changes.
Both expanded 81-case suites pass with zero failures/errors/skips on Python
3.14.9 and 3.11.15, unchanged source. These are callback-drift proofs, not final
post-worker delivery/revocation qualification. Final delivery-fence review,
mobile wiring, route contract/capability negotiation and physical testing remain.

Media readiness source `701783e` now adds an authenticated, per-bot read-only
`GET /bots/{p}/media-readiness` route with separate rights/host/API axes and
no image-existence probe. Both 77-case readiness suites pass (Python 3.14.9
and 3.11.15; zero failures/errors/skips, unchanged source). Mobile wiring,
capability negotiation, independent review, broader route-contract coverage
and physical acceptance remain pending. No remote self-grant or live deployment.

Independent media-read entitlement backend is implemented on focused source
`1f39122` (not deployed). Store schema 4 adds explicit per-device allow/deny
with revision-fenced issuance/fetch and operator-only typed confirmation;
it does not grant approval-answer, jobs, models or bot membership. The integrated
797-case suite at `8c88920` passed on Python 3.14.9 and 3.11.15 with no failures,
errors or skips and unchanged source. Six additional operator interruption cases
cover cancel, listener nonce/generation drift, expiry, a concurrent decision and
lost acknowledgement; the resulting 15-case runtime suite passes on both versions.
Readiness/capability negotiation and mobile diagnostics remain unfinished.
No schema migration, media grant, host opt-in or device acceptance is claimed.
Deployment must drain the old process before schema migration; cold old-version
startup rejects schema 4, but an already-running old process is not stopped by
that check. Legacy approval-owner fallback remains unversioned: removal denies
fetch, but restoration can revive an old reference. Explicit media deny/regrant
is revision-fenced and does not revive old references. This legacy limitation
remains open; no universal revocation qualification is claimed.

Declared bytecode-cache reader work has advanced separately: frozen producer
`9d5e549` adds exact-type preflight and original-cohort cleanup, with three
malformed-field cases passing on both interpreters (3 each, no skips, unchanged
source and verified log/XML bindings). Descendant `6f84dee` integrates
a fixed buffer/hash/header and actual-EOF consumer plus caller ACK closure;
The 18-case cache-reader run on `6f84dee` finished 17 passing and one failing:
activation-owner drift was refused but its read claim had already been cleared.
The failed source/log/XML evidence is retained. Repair `8afe009` adds activation
owner/cell joins before publication; independent finite review found no new
blocker. Normal plus owner-drift cases passed on each Python version (2 each,
unchanged source, verified log/XML). Its 34-case suite, including partial-ACK
interruptions and prefix-wrapper retirement checks, passed on Python 3.14.9:
zero failures/errors/skips, unchanged source, source/receipt/log/XML rehashed.
The same 34-case suite also passed on Python 3.11.15, with zero failures/errors/
skips and unchanged source; source/receipt/log/XML bindings were independently
rehashed. Both runs qualify this cache-reader slice only. The separate floor
linear-read timeout remains open; no complete startup, six-operation, runtime/
service or physical qualification is claimed.

Separate unqualified metadata preparation `b63aed9` inventories all39 stat/fstat
sites and both missing-stat diagnostics, captures primitive stat DATA, allocates
lazy original declared-file site plans and retains the actual plan in its walk
handoff. Review corrected the plan to match final ancestor checks. Eleven focused
plan/caller cases passed on each supported Python version (11 each). Resource
`e593cde` passed five composed cases on each version, and operation preparation
`0884893` passed eight on each; all sources/receipt/log/XML bindings were rehashed.
These qualify preparation slices only. Directory-consumer preparation `bbf877d`
retains original scope/material/lifetime bindings and one-use result ownership;
nine focused cases passed on each interpreter. Subsequent causal constructor
mutation tests reproduced a missing final material-closure check on the control;
repair `cefd515` passed all12 cases on each interpreter. Each injected mutation
was refused before publication. Fixed directory-policy DATA source `d537500`
passed20 cases on each interpreter. Exact source/log/XML hashes were rechecked.
Latched-cohort preparation `a19560a` separates structural joins from unclaimed
admission; all14 dedicated cases passed on Python3.14.9 with unchanged source
and rehashed source/log/XML evidence. All14 also passed on Python3.11.15,
with source/log/XML hashes rechecked. Fixed ACTIVE-state guard `a131932` passed
all20 cases on Python3.14.9 with unchanged source and rehashed evidence; its
same20 cases also passed on Python3.11.15 with unchanged source and rehashed
source/log/XML evidence. Finite review found no new concrete defect after the
explicit phase/failure-slot checks. These remain guard-only passes.

Separate uninstalled directory producer `f47a1be` passed29 original intent/
admission/pending-return cases on each supported interpreter. Candidate
`8f12da7`, with production bytes unchanged from ACK source `520b08d`, then passed
all45 selected synthetic native/policy/ACK cases on each interpreter, including
10 source-store interruptions. Source/receipt/log/XML hashes were rechecked.
These component passes are not complete caller, runtime or device acceptance.

A new negative control on unchanged production `4072412` reproduced lost producer
return on both interpreters: the actual return-event fault fired, the caller
received no value, raw/envelope remained pending and the ledger was still healthy;
the one-unit charge remained. Each original test failed once as expected, with
exact private stage evidence rehashed. Those failures remain failures. Producer
finally alone does not establish caller receipt; current stored rows cannot be
adopted as returned receipts. The uninstalled candidate remains unqualified.

Directory custody migration `b6b8322` moved retained result/consumer raw-bearing
cells behind one detachable payload link. Its 58-case current-version regression
finished55 passing/3 failing, with no errors/skips and unchanged source. All
three failures reached the original60-second child deadline; no cause is yet
established. The failed source/receipt/log/XML evidence was rehashed and retained;
that candidate is not qualified and its floor lane did not start.

Successor `963b0a6` fixes reviewed state/equality and captured-cell ordering gaps,
captures actual cells before C, stores the raw return immediately, and rejoins
original lifecycle/material/native/budget state after custody callbacks. Its11
memory checks passed on each supported interpreter, including actual marker-
return cell replacement and GC-disabled synthetic reclamation. Its four fixed
producer cases also passed on each version, including revocation after custody
capture with zero observed callee c_call events and normal-case calibration.
These events are not kernel-entry receipts. Source/receipt/log/XML bindings were
rehashed. The full62-case selection then passed on Python3.14.9 with zero
failures/errors/skips, unchanged source and rehashed source/receipt/log/XML.
The same62 cases passed on Python3.11.15 too, with zero failures/errors/skips,
unchanged source and rehashed bindings. These qualify that selected source,
not the later caller or a complete runtime/feature.

Test-only `6d3a8cd`, with production identical to `b6b8322`, ran one original
timeout case with a private45-second stack sampler and unchanged60-second
deadline. It passed at26.093 seconds before sampling, leaving an empty stack
file. This supplies no timeout cause and does not erase the original failures.
A fresh static recheck of installed native source `ed1afb0` finds the public
`hermes-gateway-v1` session-authority contract (typed submissions/request IDs,
receipts, snapshots and mutation). This is a potential integration route, not
qualified HMP phone access: native transport ticket/actor authorization must be
mapped explicitly, and session attachment changes subscription/lifecycle state
rather than acting as a passive health read. Legacy peer sends generate a fresh
delivery key; contract presence alone does not resolve external message identity
or the duplicate-history bug. No live requests, grants or session operations
were performed. Independent read-only review confirms that the public runner
reference is not itself a device-authority issuer. No qualified per-device native
read/submit delegation route was identified in the inspected paths; this is not
proof the entire SDK lacks one or that upstream code changes are required.
Native authorize can also restore/mount cold sessions, so passive readiness must
not invoke it. See the current native session-authority source note.

Fixed-site DATA preparation `e285873` adds original row variants allocated with
the plan before descriptor acquisition. Structural role/op/component checks,
current resource and latched-consumer variant joins are source-reviewed, with
no new concrete DATA preparation blocker;19 plan tests now pass on each
supported interpreter, with unchanged source and source/log/XML hashes rechecked.
The tail is not full canonical-order or original-plan proof. Future fixed
callers must carry actual plan/variant returns across callbacks and bind all
predecessors/resources/actor/budget phases. No dispatcher, effect site or walker
finish-guard change is introduced; this code remains separate and uninstalled.

The next source draft `872e0fb` adds original-actor eligibility before caller
custody allocation/latching while retaining the later ACTIVE sample. Independent
source review found no new blocker. An unchanged-production cross-thread control
then failed on each interpreter: actual rejection and zero native calls still
changed preparation and metadata-progress state. Those failures remain failures.
The early-actor repair passed the same case on each interpreter with all nine
observed shared-state fields unchanged; it did not add effect authority. Uninstalled leaf-policy
preparation `d85d5d2` preserves declared regular-file type/owner/link/size/mode
checks in primitive DATA;23 tests pass on each supported interpreter, with
unchanged source and rehashed evidence. This proves selected policy checks,
not native-result/declaration provenance or admission. It
excludes anchor/configuration policies; actual leaf/ancestor consumers, original
mtime/hash/EOF checks, complete plan ACK progress and device/runtime integration
remain required. The refreshed39-site inventory matches all prior semantic
entries with current five-file hashes and diagnostic function locations checked.

The same source `e597dfe` subsequently passed the full71-case selected metadata,
memory and caller regression on each interpreter (71 each, no failures/errors/
skips, unchanged source and rehashed evidence). A separate test-only single-
interruption control `9808a93` then found pre-detach payload retention on both
interpreters; post-detach controls reclaimed it. Each control suite remains one
failure and one pass, not qualification. Corrected diagnostics reached actual
producer/native/arm/injection checkpoints exactly once, with GC disabled and
original debit/failed phase preserved; earlier missing-diagnostic refusals remain
inconclusive. Isolated repair `779312e` rechecks original actor and pre-effect
custody before a final conditional memory-only detach. Both before/after cases
now pass on each interpreter (2 each), with payload reclaimed and no invented
retirement/ACK marker. Lint and plugin-surface checks pass. The broader73-case
repair regression now passes on Python3.14.9 (zero failures/errors/skips,
unchanged source and every source/log/XML hash rechecked). The same73 cases
also passed on Python3.11.15 with zero failures/errors/skips, unchanged source
and all source/log/XML hashes rechecked. Independent repair review found no new blocker for the
single interruption. Four selected combined actual-caller cases on `cc9603e`
now pass on each interpreter: normal, wrong actor and before/after-detach
interruption, with unchanged source and rehashed evidence. The broader121-case
selected regression of that exact source now passes on Python3.14.9, with zero
failures/errors/skips, unchanged source and every source/log/XML hash rechecked.
The same121 cases also passed on Python3.11.15, with unchanged source and
source/log/XML bindings rehashed. Separate constructor controls on both versions
then reproduced accepted snapshot identity/mtime drift after an actual native
return. Those negative controls are retained as failures, not qualification.
Isolated repair `b2deb97` rejoins primitive returned fields to held native-derived
inputs before publication; independent finite review found no new blocker.
Separate identity-only and timestamp-only regressions plus normal/interrupted
caller cases now pass on both Python3.14.9 and3.11.15 (5 each, zero failures,
errors or skips, unchanged source and rehashed receipt/log/XML). All four causal
constructor checkpoints prove post-native refusal, no producer publication/ACK,
reclaimed payload with GC disabled and preserved original debit/failed state.
The121-case baseline did not cover this later constructor defect; its negative
controls remain retained and the repair has only the stated focused scope. Other isolation/
repeated-interruption cases, actual-site integration and physical/runtime
qualification remain open. The older73-case baseline does not cover the later
cross-thread preparation defect; the separate repair/control evidence above
must not be replaced by that passing baseline. This is not a completed image-delivery feature.

Separate caller source `e597dfe` has now passed13 memory cases and seven actual
synthetic native caller cases on each supported interpreter (20 each), with
zero failures/errors/skips, unchanged source and rehashed source/receipt/log/XML.
The caller holds actual factory custody before effects and actual producer/
policy/ACK returns. With cyclic GC disabled, tests verify owned capsule
reclamation for normal operation, actual lost producer return, revocation,
foreign public slot and copied inner marker. Late marker drift and a finalizer
revoking activation during disposal preserve the real ACK/cursor/debit while
failing the original operation; no native replay, refund or FD close is used.
The call counter observes callee c_call events, not kernel-entry receipts.

This handles the original lost-return counterexample in the isolated new caller;
the original failing control remains preserved. It does not prove interruption
at every store, wrong-actor cleanup, arbitrary foreign alias erasure, complete
retained-root graphs or real directory/site integration. The original timeout
cause remains unknown; no deadline was raised. These local implementation and
runtime/device gates stay open; no prototype is installed. An ordinary ledger-
field replacement finding was withdrawn after source verification showed the
fields are immutable named tuples; unneeded defensive code was reverted. No
runtime vulnerability or incident was established for that invalid example.
The [caller and repair contract](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/046-bot-presentation-integration/NATIVE_METADATA_RESULT_CUSTODY.md)
and dated39-site inventory document the local work. Caller integration, all
metadata/tree/link/missing-stat sites, six operations plus enumeration, original
aggregate budgets/reserved cleanup, complete factory/service/key/runtime, the
open minimum-version timeout and physical character delivery remain unfinished.
No character-prototype activation, device/feature/release pass or observed
user-data exposure is claimed. This startup bytecode/character custody work is separate from the
reviewed host-local chat-image deployment, which the owner has now authorized
and which is installed separately as recorded below. Physical acceptance remains
open. No character prototype is represented as installed.

Source-specific leaf-before policy `4c6f33c` now preserves the actual snapshot's
`st_mtime` conversion: exact numeric types, strict64-bit bounds and integer
truncation toward zero, including pre-epoch fractions; nanoseconds are not used
as a replacement. Forty focused leaf/timestamp DATA cases pass on each supported
interpreter, unchanged source and receipt/log/XML rehashed. Independent policy
review found no new blocker; its source-only scope is explicit, so cache or
non-source reads do not gain a new timestamp requirement. This remains a
prerequisite for the shared fixed-site consumer, not native admission or a
completed walker. Fresh static inspection of installed Hermes0.23.0/0f0e96fc
still finds the unbounded native avatar getter; no qualified safe shortcut was
established, no getter was called and no upstream change was made.

The shared metadata engine now retains original raw-free ACK history in
`c82a97a`: one predecessor link per consumer, original attempt/result/consumer
joins, exact ordinal fences before indexing, and another join after material/
native closure. Its33 selected cases pass on each supported interpreter with
unchanged source, receipt/log/XML and six actual-result checkpoints rehashed.
The after-append/before-cursor interruption keeps partial history, the old
cursor, sticky failure and original debit; payload is reclaimed with GC disabled.
The initial `b7df9ef` run remains30 cases with27 passes/3 fixture failures (an
attached-payload assertion after retirement), not relabeled passing. Its source
review also found type-order and copied-prefix storage problems corrected by
`c82a97a`. Retained predecessor references are linear; full-chain audit CPU and
the separate minimum-version timeout are not qualified by this statement.
Three additional two-directory causal cases on test-only `9a96111` (production
unchanged from `c82a97a`) pass on both Python3.14.9 and3.11.15 (3 each). Sources
were unchanged; receipt/log/XML and all six causal checkpoints were rehashed.
They retain real first/second ACKs without test refunds or history rearming, and
copied or missing history blocks the second metadata C call/debit. The old walker
stays refused intentionally. This is not a complete leaf/ancestor or runtime pass.
See the [ACK history contract](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/046-bot-presentation-integration/NATIVE_METADATA_ACK_HISTORY.md).

LLY520's R3 installation does not opt into image access: a fresh read-only
single-leaf check found its local-media flag absent/off and no configured
approval-owner list. Jobs/model controls do not grant that role. No flag, owner
role or device grant was changed. [LM-ENT1](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/011-local-image-serving/MEDIA_READ_ENTITLEMENT_PLAN.md)
records a reviewed HMP-owned proposal for a separate default-deny media-read
permission, preserving existing owner-only fallback and all bot/image bounds.
Its proposed operator commands are not implemented; no live opt-in is implied.
Approval authority must not be granted merely as an image-access shortcut.

Open-registration source `1aa605d` passed all 1,434 configured startup cases on
Python 3.14.9 with zero failures, errors or skips; its eight focused cases passed
on both Python 3.14.9 and 3.11.15. Exact source/receipt/log/XML bindings were
verified. Earlier `77ae4dc` retains its separate 1,426-case pass and 183 focused
passes on each interpreter. The original `9e6f02a` failed run remains preserved.

Later coupled open/close source `5439fee` finished its 412-case focused run:
400 passed and 12 failed, with no errors/skips and unchanged source. Source,
receipt, log and XML bindings were rechecked. Eleven positive cases hit the
existing 60-second child deadline; one failed a close-ACK assertion. Diagnosis
continues without extending the deadline or relabeling failures as passing.
Unrun intermediate queues were consolidated into this descendant only after
ancestry and selected-case coverage checks; no active test was interrupted and
no unrun candidate is claimed passing. Its floor and full regression runs depend
on resolving the focused failures. No complete native IO/cleanup/quota/runtime
or device qualification is claimed.

Separate uninstalled source `9dc2875` finished its 68-case reader selection:
38 passed and 30 failed. Its first normal-case refusal was traced using only
synthetic guard function/line metadata: the caller passed an entire five-part
walk receipt instead of its original plan. Successor `2312e0b` corrects that join
and the optimistic close-status mirror without weakening the original-ledger
validator. The first 14 focused cases passed on Python 3.14.9. The repaired source then
passed all 130 selected read/close cases on that interpreter with zero failures,
errors or skips and unchanged source. Actual source, receipt, log and XML hashes
were rechecked. Python 3.11.15 then finished 129 passing and one failure: the
synthetic source-digest `linear_reads` child exceeded its existing 60-second
deadline. Source was unchanged; receipt/log/XML bindings were verified. This
floor suite is not qualified. Test-only `daf6350` prepares a 45-second bounded
stack diagnostic without changing the deadline. It reproduced the timeout,
but the parent did not persist child output. Test-only `ca2ea03` repairs private
raw-output persistence and adds two failure-preservation checks; all three
isolated cases passed, with the linear case at58.038 seconds. A further test-only
`01b586c` saved a private45-second stack even on success and passed at59.128s.
The sample shows repeated parent-package descriptor-history validation during
entry-file completion, not proof of an exclusive cause. Review found no safe
direct audit deletion across callback/import boundaries. The original timeouts
remain preserved; no deadline extension, weakened test or full floor pass is
claimed.
The original failures remain preserved, not relabeled passing; no complete
startup, six-operation, runtime/service or device/image qualification is claimed.

Corrected isolated EOF source `708beff` passed29 cases on each Python3.14.9 and
3.11.15 with zero failures/errors/skips and unchanged source; all bindings were
rechecked. Its original `7a4d42f`26-pass/3-failure fixture run remains preserved.
Cleanup diagnostic `b3115ee` passed its two mock evidence tests but still failed
the normal60-second timeout and close-status check. The latter now passes on
2312e0b; the profiling timeout cause is still unresolved. No deadline was raised.
The unstarted repeat on test-only3102341 was deferred before any child ran,
allowing source diagnosis first; no active test was interrupted.

Host-local media and desktop characters have separate source paths. Reviewed
local-media package `5e247a6` plus client source `56d517c` do not depend on the
unfinished character-source admission stack. After explicit owner approval,
ColPanicM2 received the exact reviewed109-file HMP package and a single native
graceful restart. Its new gateway retains native0.22.7/ed1afb0 and three profiles;
TLS identity and send/jobs/model readiness checks pass. LLY520 completed its
native0.23.0/0f0e96fc update, then received the same reviewed HMP package and a
supported graceful restart. Five profiles remain served; Belac/default/School Bot
channels are ready, while Lucas/Serenity retain their prior unavailable status.
LLY520 configuration and paired-device/control fingerprints are unchanged across
the HMP install/restart. Compatibility checks report local-media availability;
no actual phone image-display pass or per-device/API execution is claimed.
Existing paired-device legacy controls-decision warnings are retained for a
separate access review; no grants were changed. Character factory/runtime admission, remaining cache/metadata/link/
diagnostic integration and enumeration are still unfinished. Separate source
486bf04 prepares original cache journal joins and transient head handling; its
new helper is unused DATA validation. The actual cache producer, fixed consumer,
header/EOF acknowledgment and causal tests remain to implement.

Device-local sections/static icons and selected-bot readiness are implemented in
app source, with physical qualification pending. Desktop character parity and
host-local image delivery remain unfinished. No upstream prerequisite has been
established for the remaining HMP integration. Public integrated code remains
`34b862e` for the unfinished character work; the separate R3 image package
deployment above does not qualify that stack. The connected iPad
still refused automated launch as locked; no launch/crash acceptance is claimed.
## November 8 — selected registration checks passed; device features unchanged

The separate source candidates passed on actual Python3.14.9 and3.11.15:
ledger1b47c95 (16 cases each), scope registry731e7ac (14 each), original scope
slot874d6bf (20 each), and repaired partial file-walker threadingfffa1b3
(22 each). Exact source/config/receipt/log/XML bindings were verified. Initial
walker failures (21 setup failures, then19 passes/2 legacy failures) remain
preserved; root-shape and legacy import fixes did not weaken native checks.

Cache/link forwarding11ff67b passed55 current-version cases; its actual3.11.15
run remains pending. Fresh-probe0d74d65 has9 new plus16 existing cases queued
sequentially behind it. These remain unpublished source candidates, separate
from this review branch's34b862e code. No selected result is whole-plugin, native
runtime, device or release qualification. No host/device/deployment changed.

Bot characters and host-local images remain unfinished. Remaining work includes
entry metadata/tree registration forwarding, original per-step/consumer plans,
six fixed native-operation and separate enumeration effects, shared quota and
reserved cleanup, production native/key/service wiring and physical delivery.
No upstream prerequisite was established for the remaining HMP integration.
Earlier pending checkpoints below are historical and superseded only for the
exact source/results named above.

## Integrated startup verification — November 8, 2026

The latest verified integrated source `1a49174` passed **1,280 configured startup
cases** on actual Python3.14.9 with zero failures/errors/skips and unchanged source.
The reviewed fixture matrix also passed164 cases on actual3.11.15. These are
source checks, not installation, whole-plugin, native service or device acceptance.

The older `1ab9910` run (215 failures/1,065 passes) and its125/19 residual result
remain preserved failure history. The fixture repair preserved production native
alias and continuity checks. See
[fixture migration and limits](specs/046-bot-presentation-integration/NATIVE_IO_FIXTURE_MIGRATION.md).

Original-lineage source5883690 subsequently passed all1,290 configured startup
cases across35 modules on actual3.14.9 in2,508.53 seconds: zero failures/errors/
skips and unchanged source. Its10 actual3.11.15 selected cases retain their scope.
Unwired stat classifier66f7897 passed18 cases on each actual3.14.9/3.11.15. Exact
receipt/source/log/XML bindings were verified. These source increments are now
integrated for review, without a claim of operational image delivery.

Separate unpublished ledger/scope-registry candidates remain under serialized
16-case and14-case current/floor qualification. Original step/consumer claims,
all six fixed dispatch paths, shared accounting with reserved closes, independent
cleanup, native service wiring and physical delivery remain implementation tasks.

Source-level startup, cache and transport components do not yet establish an
operational presentation service. Native listener/key ownership, complete runtime
closure, broker terminal custody, authenticated avatar delivery and physical
mobile display remain required. No new startup component is installed on a host
or device. The installed iPad candidate remains build `2026110702`; Apple's latest
launch attempt was rejected as locked before app execution, so it provides no
launch-crash verdict. Device-local sections/static icons and host-local images
retain separate implementation and physical qualification gates.

## Internal signed CANCEL routing checkpoint — November 6, 2026

The retained credential cleanup route now composes signed CANCEL on the original
cleanup Task/channel/window, retaining its one-shot owner before native effects.
Five direct cases and two actual private-socket broker correlations cover seq1/
seq2 receipt/window/end, with real READY/resource staging but synthetic native
peer/authority. Worker GO remains unattempted; PENDING is not CLOSED or ACK.

**1,516 affected tests passed, one skipped**, 75.77 seconds; configured lint passed.
Independent read-only review accepted the retention-order repair. Earlier fixture
failures are retained in the evidence; updated tests distinguish dedicated signed
routing, legitimate automatic CANCEL suffixes and historical close facts from new
validation after metadata drift.

Known no-IO role/signing refusal still retains automatic local-cleanup debt; no
close is claimed merely because a role-neutral helper exists. Uncertain IO and
remote custody remain separate. Production startup, pre-READY cancellation,
results/terminal custody, worker relay/native publication/STATUS and physical/
release qualification remain open. Character delivery is unavailable. No live
host/settings/device or installed build changed.
See [evidence and limits](docs/research/presentation-cancel-route-2026-11-06.md).

## Work-writer final-tail repair checkpoint — November 6, 2026

New synthetic tests confirmed final descriptor-tail gaps in earlier writers:
base `8ac1edf` sent 2,586 BEGIN bytes and 1,617 GO bytes after late key retirement
or work-task cancellation. No live traffic was involved. Fixed callback-free
custody/policy/clock/budget fences now precede retained role and original actor/
caller checks after all descriptor callbacks. Refusal preserves original intent
and debt rather than sending or retrying.

Nine new zero-send causals plus two existing CANCEL tail cases passed. Selected
affected regression: **909 passed**, 48.13 seconds; configured lint passed after
a test-only line-wrap/local-name correction. Independent read-only source review
accepted the repair. Earlier green runs remain historical and did not cover this
boundary; the failing byte observations are retained explicitly.

This is a source repair, with no host/device/settings/build deployment. Production
CANCEL routing, remote results/custody/worker relay/startup/native publication and
physical/release qualification remain open. Character delivery is unavailable.
See [evidence and limits](docs/research/presentation-work-write-tail-2026-11-06.md).

## Signed CANCEL write checkpoint — November 6, 2026

The original cleanup writer now transmits only the retained signed CANCEL plus
native frame under the same consumed preparation and frozen end. Actual bounded
byte progress, settled IO and final role/actor/budget checks precede the native
completion bool and private local fact. Partial/uncertain writes retain debt
without retry or deadline renewal. Both prior writers use typed CANCEL slot
handoffs; local closure does not become a remote ACK or custody proof.

Twelve direct writer cases and **1,500 affected tests passed, one skipped**,
75.26 seconds; configured lint passed. Independent read-only review accepted GO
intent typing and final descriptor-tail role/budget/actor repairs. Tripwires prove
zero foreign callbacks or sends after late retirement/cancellation. Prior signer
`86667eb` passed [CI766](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/42300606324).
Current writer CI is not yet qualified.

Production CANCEL routing, pre-READY cancellation, remote closure/results/terminal
custody, worker relay/startup/native publication/STATUS and physical/release
qualification remain open. Character delivery remains unavailable. No live host,
settings/device or installed build changed.
See [evidence and limits](docs/research/presentation-cancel-write-2026-11-06.md).

## After-READY CANCEL signing checkpoint — November 6, 2026

The original cleanup signer now consumes exactly one native CANCEL preparation
and binds its actual seq1/seq2, frozen 16-byte window and frame hash to original
signed work context. Current role/cleanup checks and earliest end remain separate
from retired work authority. Partial preparation is retained; no retry or renewed
interval follows. This owner signs data only, with no socket completion credit.

Eight direct signing cases and **887 selected affected tests** passed, 44.67 seconds;
configured lint passed. Independent read-only review accepted the after-READY
scope. Key retirement, expiry before/after preparation and malformed row/end
tripwires withhold signed output, invoke no foreign callbacks and preserve the
budget's original work/end values. Signing an after-READY CANCEL does not qualify
pre-READY cancellation, remote custody, release or production deployment.

CANCEL transport, pre-READY cancellation, signed results/terminal custody, worker
relay/startup/native publication/STATUS and physical/release qualification remain
open. Character delivery remains unavailable. No host/device/settings/build changed.
See [evidence and limits](docs/research/presentation-cancel-commitment-2026-11-06.md).

## Cleanup role-material checkpoint — November 6, 2026

The fixed original cleanup Task can now validate current role/input/transcript
material after joined work and policy retirement, without borrowing live-work
permission. Existing work actor/caller/native authorization checks remain around
the separate work entry. The cleanup entry requires original allocation, frozen
intent, known work join, write-quiescence/cancel facts and current role material.
It signs/sends nothing and cannot revive policy/GO authority.

Six direct cleanup actor/tail cases and **878 selected affected tests** passed,
43.35 seconds; configured lint passed. Independent read-only review accepted
allocation/slot tuple/type/identity fences after native-tail substitution tests
proved zero foreign indexing and unchanged budget/no network attempt. This is
material-only source qualification, not authenticated CANCEL completion.

CANCEL signing/transport, results/terminal custody, worker relay, startup/native
publication/STATUS and physical/release qualification remain open. Character
delivery remains unavailable. No live host/device/settings or installed build changed.
See [evidence and limits](docs/research/presentation-cleanup-role-material-2026-11-06.md).

## Internal signed GO dispatch checkpoint — November 6, 2026

The original credential work path now composes signed GO transport through the
existing native admission and single GO_SENT transition, with exact full-write
proof and separate fixed post-GO_SENT material checks. The original task parks
on its fenced shared cause instead of entering an unsupported unsigned result
reader. No result token, broker receipt or execution acknowledgement follows.

Six direct dispatch cases and **872 selected affected tests** passed, 44.25 seconds;
configured lint passed. Independent read-only review accepted cause/scheduler
fences and callback-free role-material resealing after final native checks. Late
failures retain full-wire/native-phase facts while withholding public success.
This selected run is narrower than the prior writer's 1,466-test regression.
Prior writer CI760 is still running; new-source CI is not qualified.

Startup, signed cleanup/results/terminal custody, worker relay/native publication,
STATUS and physical/release qualification remain open. Character delivery remains
unavailable. No live host/device/settings or installed build changed.
See [evidence and limits](docs/research/presentation-signed-go-dispatch-2026-11-06.md).

## Signed GO write checkpoint — November 6, 2026

The original-task GO writer now sends the retained fixed signed GO record and
frame on one original native GO write intent. Actual byte progress, current
role/native/clock checks and owned write-readiness settlement precede the native
write fact. Partial/uncertain IO keeps original admission/intent/debt and cannot
retry. The completed BEGIN owner recognizes only an exact reciprocal GO IO-slot
handoff. Historical local closure follows held original proofs, not mutable
foreign cleanup metadata.

Independent read-only source review accepted the final historical-release repair
and completion check. **1,466 affected tests passed, one skipped**, 67.04 seconds;
configured lint passed. Twelve writer cases include complete/partial/EAGAIN,
unknown send/registration, zero send, key retirement, initial refusal, wrong actor,
intent drift and foreign postjoin cleanup/allocation tripwires. Prior signer
`beb4599` passed [CI758](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/42296434170).
Current writer CI is not yet qualified.

Production sender dispatch, GO_SENT, broker custody/worker relay, startup, later
output/terminal/publication/STATUS and physical/release qualification remain open.
Character delivery remains unavailable. No live host/device/settings/build changed.
See [evidence and limits](docs/research/presentation-signed-go-write-2026-11-06.md).

## Fixed GO commitment checkpoint — November 6, 2026

The new original-work signer derives only gateway/g2b GO sequence1 for the
original empty frame after actual native GO_INTENT and consumed admission. It
joins completed BEGIN/READY/transition, current role material and original end;
no socket write, GO_SENT, resource or execution permission follows. Production
GO transport remains closed.

Independent read-only review accepted the fixed GO state seam and metadata
repairs: closed primitive rows/exact integer ends before comparison, then exact
expected values derived from retained READY. Selected regression before the final
value join: **853 passed**, 39.49 seconds. After it: **eight focused cases passed**,
2.16 seconds; configured lint passed. Admission/expiry assertions preserve actual
pre-attempt refusal/native UNKNOWN; no rollback is inferred. Prior cancellation
uncertainty remains recorded. No host/device/settings or installed build changed.
See [evidence and limits](docs/research/presentation-signed-go-commitment-2026-11-06.md).

## Internal signed READY dispatch checkpoint — November 6, 2026

The credential branch now uses the signed exchange through the existing original
work/caller READY barrier, with explicit producer/remote/transition receipt joins.
Three direct cases cover valid signed READY, bad signature and cleanup request
winning during fresh PRE_GO. Generic GO/CANCEL/result fallbacks remain closed;
startup/key selection and resource admission remain unqualified.

Full affected regression before the final explicit producer/remote identity check:
**1,444 passed, one skipped**, 65.99 seconds. After that check, **172 focused tests**
passed in 13.57 seconds; configured lint passed. Independent read-only review
accepted the dispatch slice and final identity-check readback. Earlier
unexplained cancellation failure remains recorded. No live host/device/settings
or installed mobile build changed. Character delivery remains unavailable.
See [evidence and limits](docs/research/presentation-signed-ready-dispatch-2026-11-06.md).

## Bot-character delivery source checkpoint — November 6, 2026

[Draft PR #138](https://github.com/MahdiHedhli/hermes-hmp/pull/138) now includes
reviewed original-work native READY transition after completed signed READY and
fresh PRE_GO authorization. Actual native STARTING/READY state, successful native
return, current keys and fixed post-transition scope are required. Failures after
mutation are terminal with no rollback/retry. No GO permission is created.

Final affected regression: **1,438 passed, one skipped**, 63.41 seconds;
configured lint passed. Independent read-only review's foreign-equality phase
finding was repaired with identity checks and a zero-callback tripwire. Earlier
836-pass/one-failure cancellation observation remains unexplained and recorded;
later passes do not erase it. The fixture now surfaces the underlying completed
control-task outcome rather than reading an unfinished notification Future.
See [evidence and limits](docs/research/presentation-native-ready-transition-2026-11-06.md).

Production dispatch, later signed phases, resource admission/worker GO relay,
startup, native publication, STATUS and physical/release qualification remain
open. Character delivery is unavailable. No host/device/settings/mobile build changed.

Original-task exchange composition now joins the reviewed signed BEGIN writer,
READY reader and fresh PRE_GO/native READY transition in one one-attempt method.
Independent read-only review accepted it, including early exact-task rejection.
Selected affected regression: **841 passed**, 37.97 seconds; lint passed. This
is narrower than the prior 1,438-test transition regression and grants no startup
or GO authority. Production selection remains closed.

## Native image verification checkpoint — November 6, 2026

Independent review accepted the 120 never-started base-phase observations at exact source `5e247a6`: all 3,120 artifacts, 1,508,640 copied-source SHA/literal Git identities, 240 outcomes, 1,200 known commands without expiry/settlement, and 39/39 borrows with closed DB/listener/workers/hooks/writers. It also accepted two separately reviewed fresh Phone observations for base pair 323 (case 6, selector 16): 52 artifacts, 25,144 copied files and 20 known commands; deactivation refused then freshly accepted 15 rows, while changed eligibility refused then remained ineligible. These are bounded native observations, not production or device qualification.

Both historical paired attempts remain refused. Later terminal-zero settlement and fresh single-phase successes do not establish success under the old paired 12-second limit or prove its timing cause. The changed startup/cumulative-resource/timing context is explicit. Earlier accepted evidence retains its actual sources: original `21937dc` prefix (174 pairs / 348 phases), fresh `5c96927` observations, and `e8653d5` prefix (201 jobs / 296 phases, 5,416 artifacts and 2,526,369 copied files). Observed residual/ABA accepts remain limitations. Final cross-source phase reconciliation is independently accepted; no single-source full paired-matrix pass is claimed.

The full additional ordinary/delegated-child scope completed all 144 fresh single-phase jobs from frozen, exact CI-tested `5e247a6`, using the reviewed committed supplemental owner with explicit `per_phase_v2`. The actual controller exited 0 with a complete 144-row journal, no current job and scope execution marked complete. The separately reviewed artifact collector and independent artifact review completed successfully: 3,744 artifacts, 1,810,368 copied-source identities, 1,440 known commands and 39/39 borrows per process. Independent final reconciliation accepted all 912 distinct declared phases across the six actual-source scopes: 17,604 artifacts, 8,081,617 copied-source identities and 6,604 known commands. See [the bounded composite and limits](docs/research/local-media-native-writer-composite-2026-11-06.md). The outer controller's actual read-only preflight, 19 refusal causals and unchanged-once/late-evidence guard checks passed independent source review. All 17 accepted-evidence pins are checked before every original driver call; private fresh roots, 33 GiB per-job capacity admission, source/archive pins, the unchanged 12-second observation limit and retained actual settlement remain required. No automatic retry, old-root adoption or promotion of either old refusal is provided. Exit 0 alone is insufficient if capacity refusal leaves the scope incomplete.

[PR #136](https://github.com/MahdiHedhli/hermes-hmp/pull/136) and [PR #137](https://github.com/MahdiHedhli/hermes-hmp/pull/137) retain the source/spec/task history. Exact executable source `5e247a6` passed [CI 42205520797](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/42205520797): 8,101 tests, 190 subtests (33 skips, 18 warnings), configured lint, closed plugin/privacy and 96 Unicode cases each on Python 3.12/3.13/3.14. Log hygiene had no captured acceptance logs to scan. A separate read-only audit confirmed all eight execution helpers unchanged from `e8653d5`, with only inert added planning definitions and docs/tests changed; this does not relabel older observations as `5e` execution.

Root accepted the bounded C6b native-evidence task, joining the separately accepted cost/allocation, modeled mint, RSS and writer observations without transferring their actual-source limits. See [the root disposition](docs/research/local-media-c6b-root-acceptance-2026-11-06.md). Independent exact HMP delivery-source review and runtime-only artifact review are accepted at `5e247a6`; see [the source/package review and limits](docs/research/local-media-delivery-source-review-2026-11-06.md). Full plugin loading, current-listener activation/verification, exact signed-phone display and release qualification remain open. Read-only ColPanicM2 preflight found the saved image flag already true and installed source different; no host change followed. No real provider call, host permission/config change, deployment or store submission is part of these fixtures.

## Heavy-case fresh partition samples reviewed — November 6, 2026

Two separately reviewed fresh single-phase experiments at `5c96927` completed
under the unchanged 12-second limit. Each preserved the largest 98-session/full-
prompt Bot shape, both proof contexts, history and one selected tool row.
`deactivate:ids0` and `deactivate:page` each refused the concurrent binding with
`rows_changed`, then freshly returned `ok` with an empty accepted selection.
Independent readback accepted all 52 artifacts, source/Git/runtime/entry/cache
bindings, 39/39 borrows per process and cleanup. No expiry or settlement-only
success was used. The original paired attempt remains refused and unchanged.

The pure remaining planner preserves all 418 never-attempted phases from pairs
175..383 in 301 jobs, splitting only the largest shape; its source review and
17 model cases passed. Its output is not execution authority and excludes the
refused pair. The combined related suite passed 696 tests. Completed-prefix
artifact audit, source-bound execution integration and supplemental coverage
remain open. No full-matrix, delivery or release pass is claimed.

## Cached single-phase lineage sample — November 6, 2026

A fresh native sample at `0397803` used the reviewed optional archive-clone path
and independently checked Git/archive/source identities before executing one
largest-shape Bot ordinary-child phase (98 sessions, full prompts, 128 selectors).
It completed under the unchanged process limit: `tip_changed` first, then fresh
`not_eligible`, two public native mutation calls, 39/39 borrows and closed
DB/listener/workers. All ten commands had known outcomes; no expiry/settlement,
ordinary-copy fallback or metadata removal occurred. Independent readback accepted all 26 artifacts and source/runtime/clone
bindings. This is one phase, not a full matrix or a measured storage bound.

The original matrix at `21937dc` remains stopped after 174 completed pairs and
one refused pair; 209 pairs never started. Reusing its verified source archive
neither reruns nor rehabilitates the refused workload. Broader single-phase
partition/remaining execution and independent evidence review remain open.

# Roadmap

## Native binding process-memory observations reviewed — November 6, 2026

[Current RSS evidence](docs/research/local-media-native-binding-rss-2026-11-06.md)
at `e299092` covers all 24 fresh-process kind/shape/selector pairs. Independent
read-only review accepted 672 artifact hashes/private modes, source/literal Git/
runtime/report identities, arithmetic and cleanup. Each process balanced 36/36
borrows and closed its databases/listener/workers. Current RSS deltas ranged
from −622,592 to 10,059,776 bytes; new cumulative peak growth from 0 to 3,948,544.
Prior preparation peaks remain explicit, including 17 zero-new-peak cases that
do not imply zero allocation. These are warm sequential process observations,
not native-C bounds, cold calls, production memory budgets or a new ceiling.
Root's 328 focused checks/lint passed. Mint PR132 is integrated at `0e4f5bc`
with successful final CI. Current writer/control/refusal/residual/ABA evidence,
C6b, physical display/activation and release qualification remain open.

### Writer refresh pilot checkpoint

[PR134](https://github.com/MahdiHedhli/hermes-hmp/pull/134) now includes
independently reviewed DB-close barriers and scenario oracles at `8167016`.
The bounded 12-phase native pilot passed: 24 exact first/second outcomes,
336 artifact/source/runtime bindings, 39/39 borrows per process and verified
writer/hooks/DB/listener/worker closure. It exercised nine successful public
native mutation calls, five synthetic Phone-store calls and one native guard
refusal. Residual stale acceptance and Phone-store ABA acceptance remain
limitations. Root's 559 focused checks/lint passed; no reviewer execution.
The full 624-phase matrix, storage layout and native fork/reset applicability
remain open, so C6b and delivery/release are not complete.
[Exact pilot scope](docs/research/local-media-native-writer-pilot-2026-11-06.md).

### Constructed-child and paired-runner checkpoint

Four constructed branch/reset child-isolation phases at `befa0f7` passed independent source/artifact review: eight exact parent-binding outcomes, 112 artifacts and 39/39 native borrows per process with verified cleanup. These do not exercise actual gateway fork/reset admission.

The paired runner at `f6c693f` passed independent source review after a type-exact checkpoint repair. Two largest-history paired processes completed four phases with fresh DB/home scopes, four durable checkpoints, 60 reviewed artifacts, 53/53 borrows per process and verified cleanup. Child isolation retained exact parent selections; Phone append/deactivation refused the concurrent read and the fresh read accepted the expected 128/127 rows. No deadline extension, retry, guard bypass or reviewer execution.

The declared full matrix contains 768 unique phases in 384 pairs. Full-matrix execution, operational fork/reset applicability, C6b, activation, physical display and release qualification remain open. The related suite passed 601 checks before the finite checkpoint type repair; 304 targeted checks passed afterward, with lint clean.

## Native-bound modeled mint-memory sample reviewed — November 6, 2026

[Current evidence](docs/research/local-media-native-mint-memory-2026-11-06.md)
at `6453386` covers 24 fresh isolated samples and 1,160 verified refs using
production registry/Binding/descriptor types over actual native binding results.
Independent source/artifact review accepted all 672 top-level artifacts, source/
literal Git/runtime/report identities, known commands and cleanup. Each process
balanced 35/35 native borrows. Traced peaks were 3,844/14,224/81,616 bytes for
1/16/128 refs, retained before explicit cleanup with shared field objects.
This is a modeled mint loop, not input preparation, native binding, S4 route/
authorization/event-loop cost, RSS/native-C or full-capacity registry memory.
Root's 277 focused checks/lint passed. Current RSS and writer/control/refusal/
residual/ABA work remain required; C6b and delivery/release stay open. PR131's
binding-cost work is integrated at `4925e06` with all final CI jobs successful.
No live settings, grants, providers, gateway, app install or release changed.

## Current complete-binding cost checkpoint — November 6, 2026

The [current native sample](docs/research/local-media-native-binding-cost-2026-11-06.md)
completed all 24 Bot Chat/Phone workload-selector pairs at `85c83f8`, yielding
72 warm timing values and 24 Python allocation samples. Both proof contexts and
full verified prompts are retained per database; 40/40 borrows, database and
listener/worker closure held in each process. Independent aggregate artifact
review accepted all 672 artifact and source/runtime/report bindings. Exact-source
CI is tracked separately. The earlier observation
expiry remains a refused run, not a pass. Current mint-memory, RSS and writer/
control/residual/ABA evidence remain required, so C6b stays open. No phone image
display, production activation or release qualification is claimed.

HMP follows the [feature list](FEATURES.md), [unified gateway research](HermesUnifiedGatewayResearch.md), and [requests for Nous](NOUS_GATEWAY_OBSERVATIONS.md). The research describes a target architecture, not a remote API available to HMP today. The following is a historical September 29 checkpoint, not a current upstream status check: Nous [PR #106742](https://github.com/NousResearch/hermes-agent/pull/106742) is open with conflicts; its [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) places authenticated remote clients in a later cutover.

| Investment | Work | Boundary |
| --- | --- | --- |
| Current qualified Hermes | Pairing, Bot Chat reads and guarded sends, read-only setup and bot health checks, and owner-gated scheduled jobs and default-model previews. | Use the minimum supported version and required APIs; tested-sample evidence is not a per-version allowlist. Keep the owner and per-bot gates; do not widen the legacy send route to arbitrary sessions. |
| Release hardening | Integrate the draft features, run isolated gateway fixtures, then review the exact release candidate and device artifacts. | No live-host switch or external beta based solely on source tests. |
| Plugin updates | Add a read-only release-aware HMP update and compatibility check, then an explicit pinned update with rollback ([issue #18](https://github.com/MahdiHedhli/hermes-hmp/issues/18)). | `hermes update` does not advance the pinned plugin. Never silently update HMP across an unqualified Hermes boundary. |
| Installer footprint | Keep the current full-tree security scan and explain its caution findings to operators. | A quieter bare install needs Hermes to support a verified install file set; do not suppress scans or hide executable tests. |
| Search | The distinct authorized start page is in draft; the companion app draft matches locally across available Bot Chats or within one. | Keep older-HMP, compaction-reset, incomplete-scan, and request bounds visible. Hermes-wide search still needs the upstream raw-query log fix. |
| Approvals and choices | Converted to the minimum-version policy in source: `approvals` and `phone_chat` availability members, owner-only streaming, native-answer classification and generation and binding fences. Next: independent focused review, sampled evidence on locally present pinned builds, then an owner-local dogfood decision. | Security clearance; upstream capability flag and release containing the session-stream approval notifier; phone Phone-chat composer UI; no exact-build qualification is required |
| Bot lifecycle and session writes | Request complete remote bot create/delete and stable canonical session metadata operations. | A profile alone is not a Bot Mode bot; destructive or uncertain results need exact recovery. |
| Canonical gateway | Prepare capability discovery and fixtures for durable admission, replay or snapshot, and Desktop/mobile ownership. | Wait for an authenticated remote entry with one execution authority; do not invent admission IDs or event watermarks in HMP. |

## Adoption gate for a new Hermes release

1. Confirm canonical runtime and authenticated remote entry have landed in the target release.
2. Identify and authorize the exact installation, profile, and session; negotiate supported operations. Missing capabilities fail explicitly.
3. Re-run the HMP read/send, Cron, and model fixtures in an isolated Hermes home as tested-sample evidence.
4. Prove the [research acceptance cases](HermesUnifiedGatewayResearch.md#20-hmp-acceptance-tests-derived-from-upstream): shared Desktop/mobile session, no duplicate turn after a lost acknowledgement, replay or authoritative snapshot after reconnect, stale-control refusal, profile isolation, and restart recovery.
5. Add a versioned canonical-gateway adapter only after those checks pass, with a rollback for qualified older builds.

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

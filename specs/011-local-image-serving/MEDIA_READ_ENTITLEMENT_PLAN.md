# LM-ENT1: independent host-local media read permission

Status: implemented on isolated backend source `fb82aef` and mobile source
`463c6bf`, pending independent review and integration/runtime/device qualification.
No live schema migration, grant or opt-in has been performed. Installed R3 remains
owner-only; source implementation must not be confused with deployed behavior.

## Observed need

The updated LLY520 has R3 installed but no `local_media.enabled` opt-in and no
configured approval-owner list. Jobs/model controls do not imply that role.
Enabling one flag alone cannot make its images available. Granting approval
answer authority solely to obtain image access would bundle unrelated rights.
No such change was made. Software installation is separate from access.

## Required contract

- Negotiate an explicit independent media-read capability. Older hosts keep
  their existing owner-only behavior; clients explain that limitation instead
  of recommending a silent approval-role grant.
- Keep the host-wide media opt-in, authenticated active device, original token
  scope, per-bot membership, immutable descriptor provenance and bounded image
  checks. A media permission grants none of pairing, bot membership, prompt
  answers, mode changes, jobs, model management or arbitrary host file access.
- Introduce an operator-managed per-device media-read decision. An explicit
  allow can grant that right to a non-approval-owner; an explicit deny closes
  it. Missing decisions preserve existing owner-only behavior and deny other
  devices. Do not migrate absent decisions into new allows.
- Effective precedence is explicit deny, explicit allow, then the unchanged
  missing-decision owner fallback. Bind each decision to the original instance
  and verified stable device identifier, never a label or token string. Persist
  decisions atomically with an authoritative revision/generation shared by
  issuance, fetch and final publication checks. Concurrent writes need a
  reviewed conflict rule and readback; a lost acknowledgement is not a retry.
- Use a separately reviewed local operator command, provisionally
  `hermes hmp devices grant-media-read <verified-device-id>` and its deny/readback
  counterparts. These commands exist on the isolated source branch only. Require
  current verified active pairing identity and authoritative stored/effective
  readback. A future media access-request transport remains required; the current
  mobile UI offers operator guidance only and cannot grant itself permission.
- Do not alter approval-owner configuration or job/model controls. An explicit
  media allow remains independent of those decisions. Preserve their own deny
  rules and never reframe a media-only grant as approval authority.
- Recheck the current decision and device/bot authority at descriptor issuance,
  fetch admission and before response publication. Close stale generations and
  late replies on revoke, unpair, entitlement denial or instance/profile change.
  Never treat a cached descriptor or prior successful fetch as renewed access.
  Revocation cannot retract bytes already delivered or guarantee instant worker
  termination. It must prevent late publication, close the corresponding cache
  generation and preserve real worker permit lifetimes and outstanding debt.
- Readiness must separate host opt-in, API/dependency eligibility, operational
  health, per-device entitlement and per-bot authorization. Reveal precise
  reasons only within authenticated authorized scope, with no resource-existence
  leak. Disclose the host-wide impact before enabling a host flag/restart.
  Default masked route denial precedes host-flag, descriptor/reference and file
  lookup. Do not advertise the new capability until its effective-decision path
  exists; supporting one read-only status field is not complete capability.

## Acceptance and tasks

1. Freeze/review the wire capability, store transition and operator authorization
   contract before implementing a mutating command. Keep default-deny migration
   and existing owner behavior explicit.
2. Implement the independent effective decision and read-only readiness with
   current authority/generation binding. Preserve existing owner-only fallback.
3. Implement the reviewed operator grant/deny/readback path. A missing or lost
   acknowledgement requires authoritative inspection, never automatic replay.
4. Apply the decision consistently to issuance, fetching, cancellation and late
   worker completion; preserve image/type/size/path and profile isolation.
5. Verify old-owner behavior, non-owner default denial, media-only allow, explicit
   denial, inactive/revoked/wrong device, wrong bot/instance, concurrent grants,
   stale awaits and lost acknowledgements. Prove every unrelated permission and
   provider/model/job value remains unchanged. No prompt answer or job execution
   is part of these tests.
6. Qualify packaging/runtime and Android/iOS display separately. Only then seek
   the owner's explicit opt-in and exact device grant decisions for deployment.

No upstream Hermes change is established as a prerequisite for this HMP-owned
permission separation. It does not resolve the separate character-reader work.


## Source checkpoint — November 8, media readiness

Focused branch `feat/media-read-entitlement-20261108`, source `701783e`, adds
`GET /bots/{p}/media-readiness` without changing the existing AR1 response.
The new response separates entitlement, host opt-in and runtime API state, with
closed reasons and `contact_host_operator`; it does not advertise an unimplemented
Request access or Fix transport. Image availability is explicitly `not_probed`.
It reuses the existing authenticated per-bot authorization/deadline/worker-budget
fence and rereads rights/settings before disclosure. Unknown authority is refused,
not represented as missing rights. No file/reference lookup or mutation occurs.

The 77-case current-Python readiness suite passes with zero failures/errors/skips;
the same 77 cases pass on Python 3.11.15. Broader route-surface/contract coverage
remains pending.
Mobile decoding/display and capability negotiation, causal revocation/lost-await
route coverage, independent review and runtime/physical qualification remain open.
The legacy owner-fallback revocation-generation limitation remains open. Nothing
from this schema-4 branch is installed on a live host.


## Integration review checkpoint

The source path now includes schema-4 store decisions, CLI grant/deny/status,
revision-bound descriptor issuance/fetch, authenticated diagnostics/discovery,
and mobile decode/API/context/chat guidance. This does not complete the feature.
Backend source `fb82aef` is under a combined 1,059-case integration run and focused
independent review. Mobile source `463c6bf` has 67 UI/chat plus six large-text
regressions passing; earlier domain/API/context evidence is retained separately.

Open release blockers include independent review findings, final synchronous
native/config/SQLite read latency, legacy fallback policy revision limitations,
safe old-process drain before schema migration, real packaging/runtime/device
qualification, and explicit host/device opt-in decisions. No automatic rollback
from schema 4, mobile self-grant, approval privilege expansion, or new permission
is authorized by this implementation document.

## Independent review — blockers on fb82aef

Read-only reviewer verified exact backend fb82aef and mobile 463c6bf. No concrete
mobile lifecycle blocker was found in the inspected paths; this is not full release
review. Backend delivery remains blocked by two findings:

1. The final authority checkpoint can invoke a bot/auth callback after media
   comparisons. Re-sample media decision, settings and API after the last callback,
   compare the held authority, and prohibit further authority-bearing callbacks
   before publication. Add a final-callback causal mutation regression.
2. Across the worker await, the handler retains a context without rejoining the
   request application's current context and original identity/store/bridge cohort.
   Reject a replaced app context or dependency before final collection/publication.
   Add an original-context replacement regression.

No deployed host contains these new diagnostics. Fixes and independent re-review
remain required. Synchronous final-check latency and migration gates remain open.


Repair checkpoint f7f5084: all reviewed callback/context findings have source
repairs and causal tests; 89 readiness cases pass on both interpreters. Independent
re-review is pending; prior blockers are not declared closed by self-testing.

Independent reviewer subsequently verified exact f7f5084 and resolved the identified
ordering/context defects, with no new blocker in the inspected delta. This is not
full security, performance, runtime or release qualification.

Causal negative controls restore matching pre-repair server implementations in an
isolated worktree and reproduce stale200 responses at the reviewed failure sites.
The mismatched callback-count control is excluded, with corrected control retained.
A fresh combined1,063-case f7f5084 suite is running; floor not launched yet.

Both fresh f7f5084 combined suites now pass1,063 cases each. Paired mobile5ca14a9
passes66 client plus73 app/chat/accessibility cases after pinning. Full analysis
is clean; runtime/performance/migration/legacy fallback and physical gates remain.

## LM-ENT1-P1 — bounded publication responsiveness (open)

An isolated loopback probe on exact f7f5084 injected150ms into the first
main-thread settings callback. The largest5ms heartbeat gap increased from5.7ms
to151.5ms; request elapsed increased from2.3ms to153.4ms. Both returned200. This
is a synthetic causal availability demonstration, not a live-host performance
benchmark. Source remained unchanged. Final synchronous authority checks therefore
remain an integration/deployment blocker; passing functional tests do not close it.

Required repair: keep blocking native/config/SQLite reads off the event loop while
retaining current-instance/device/bot/media/flag/cohort freshness checks. A timeout
must fail closed without cancelling the real worker, returning its permit early,
or publishing a late DTO. Do not substitute stale cached authorization or a
thread-local timestamp for an authoritative publication boundary. Inspect existing
Store mutation coordination and native/config generations first; distinguish
in-process writes, supported operator-process writes and native authority changes.
An independent design review is requested before choosing the publication seam.

Acceptance must include injected slow callback and contended-store cases, another
request/heartbeat remaining responsive, fixed deadline refusal, no late DTO after
revoke/flag change/cohort replacement, and exact worker-permit retention until real
completion. Keep generation/authority negative controls. Real runtime latency and
physical/device qualification remain separate from synthetic fixture evidence.

Independent design census found no complete pure authority-publication seam in
inspected HMP paths. Store locks/transactions and SQLite epochs may block;
listener readiness_generation is not a revision of every authority mutation.
Operator read snapshots do not coordinate permission writes. The bridge native
bot/config helpers do not expose a published pure revision receipt in inspected
paths. This is a scoped evidence gap, not proof that every current upstream API
lacks a suitable contract.

Next bounded HMP-owned task LM-ENT1-P2: define listener-owned immutable publication
DATA and a monotonic invalidation epoch; fixed workers collect complete actual
request authority while the loop checks only original request/cohort/revision
and a single-use publication claim. Invalidate before each participating mutation,
settle after commit/rollback; unknown or lost acknowledgement remains refused.
Cover same-process store/CLI changes, then route supported operator-process writes
through the same authority owner. Do not treat PRAGMA, file watch, polling or TTL
as cross-process/native invalidation. Inventory exact native bot/config mutation
paths and supported lease/revision hooks before enabling a pure final gate.

P2 is necessary preparation, not sufficient completion. Final authorization cannot
be relabeled an observation or replaced by stale cached grants. The new source
route remains undeployed until the conjunction of mutation sources is justified;
existing deployed features/rights are not disabled or changed.

P2 preparation22e5a58 is an unwired currency primitive, not authorization.14cases
pass on both interpreters. Initial review interruption finding has a source repair;
re-review/line-return fault coverage and all writer coordination remain open.
Candidate must be minted BEFORE worker sampling begins and held through claim.

P2 handoff checkpoint385b1de:24 cases pass each interpreter, including exact-line
and return-event interruption. Example callers require original receipt before
write/sample/publish. Lost settlement acknowledgement never triggers mutation or
settlement replay; definite completed settlement may remain internally settled.
This does not qualify actual caller wiring, still required before integration.

P2 Store checkpoint:ab2fd5e optional observer encloses real transaction handoff,
known commit/rollback settlement and uncertainty. ReviewNone-receipt finding fixed.
280cases pass bothPythonversions with matchingserverfingerprints; floor113b611
is documentation-only descendant. The listener does not install an observer;
writer census/coordinator/native contracts remain incomplete. See published
docs/architecture/MEDIA_PUBLICATION_WRITERS.md on the focused source branch.

P2 actor checkpointd6f57d4: worker-only listener rendezvous and postoperation
failure/cohort seals prepared;287cases pass eachPython. Independent review confirms
two actor findings repaired. No listener installs it, operatorIPC/native/config
writer coverage is missing, and P1 remains unresolved on the actual serving path.

P2 shutdown checkpoint07a02c5 reserves original debt beforebegin, preserves it
throughpublicationclose, and provides exactcleanup-only retirement with separate
capacity.291cases pass eachPython and finite independent review reports no new
blocker. Unknown debt neverforceclears; endedSQL relies on fixedStorefinally, not
receipt possession alone. No actuallistener/native/operator integration yet.

LM-ENT1-N1 native contract census is source-pinned at0f0e96fc and independently
reviewed; exact inspected HMP path lacks a revision/lease/finalclaim return.
This is a bounded path finding, not allSDKabsence or runtimebyte proof. See
docs/research/media-publication-native-contract-20261108.md at23437de. Continue
HMP Store/operator/lifecycle work; do not substitute cachedBoolean or private
profile-scope shortcut. Existing deployed features and minimum-version policy stay.

OP1 requestcodec1794e43 is implemented as DATAonly;35cases pass bothPython and
independentreview found no concrete codecblocker. No socket, consent, runtime
nonce/peer/listener check, CAS or response execution is supplied by thecodec.
Operatortransport/handler and allnativepublication obligations remain open.

OP1 executord788615 prepares actualworkerCAS/readback using originalactorStore,
completeexpectedsnapshot and finalcohort/deadline checks.43cases passbothPython,
reviewreportsnoconcrete blocker in unwiredlayer. DuplicateCASdoesnotreplaygrant;
postcommitreadbackloss staysunknown. Peer/consent/admission/deadlineprovenance and
nativecoordination are separate missingtransport/lifecycle prerequisites.

OP1 responsecodec atadf41e2 distinguishes committed/conflict/refused/unknown;
committed fields mustmatch exact requestedtransition.69cases pass eachPython and
reviewfoundnoconcrete codecblocker. Replycorrelation isnot runtimeauthority proof.
Branchlintcleanupade8fce passes fullserver/toolsRuff plus360focusedcases; fresh
1,176-case integration running, no combined qualification claimedyet.

Transportnamespacec3ae41b preservesreadonlydefault, addsfixedseparatename/frame
layoutonly.56read/FD/layoutcases passbothPython/fullRuff; futurewritehandlerstill
absent. Fresh1176floorcapacityretry passes; priorENOSPCrunretainedunqualified.
Originalfailed testsubsetimportorder was fixed viaexplicitadapterfixture, notwaived.
Onlycompletedownedsyntheticscratchwasremoved; receipt/log/XMLhashesreverified.


## Reviewed CLI IPC integration — 8b15a7a

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


## Read worker lifetime prerequisite — aaa29aa

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


## Read-only safety backport deployed — c7482f1

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


## MR-LIFE1: original media-lane retirement source reviewed

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

- MR-LIFE1: helper implemented/reviewed/tested; no whole-listener close authority.
- MR-LIFE2: integrate the retained media coordinator with original HmpServer/adapter teardown and other borrower drains without default activation.
- MR-LIFE3: qualify quiesced schema4 migration, cross-process writer coordination and rollback.
- MR-LIFE4: native-owned final authority publication remains a separate inspected contract gap; no cached boolean substitute.


## MR-LIFE2a optional listener retention reviewed

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

MR-LIFE2b next: retain each original server/Store retirement owner in the adapter; block replacement/reconnect on unresolved creation/drain/close outcome; never close a new ctx Store via an old callback. Preserve known normal teardown and no default media activation.


## MR-LIFE2b retained adapter owners source reviewed

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

Next qualification: serialize/capture concurrent startup and bootstrap cancellation ownership, inventory every HTTP/native/thread Store borrower, then qualify quiesced schema4 migration/rollback. Native final authority publication remains blocked on an inspected contract, not substituted by a cached boolean. No activation from this checkpoint.


## MR-START1 lifecycle exclusion reviewed

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

MR-START2 next: retain the actual component-opening concurrent Future and original startup scope/context/server before publication; reconcile caller cancellation/unknown task creation/partial startup without guessed cleanup or replay, then permit recovery only after known original resources retire. Preserve controlled False results and tested normal behavior. No default media activation.


## MR-START2a actual component ownership and unpublished cleanup

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

Next checkpoint: context-propagation parity audit for earlier read-worker pool/backport, without inferring a live profile leak. MR-START2b then needs stage-owned runner/TLS startup/failed-builder allocation cleanup, actual-resource retirement and scope readback before recovery. Other borrowers/migration/native publication and device qualification remain open.


## Read context parity audit and minimal repair deployed

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

Next MR-START2b: retain runner/site objects before every startup await, reconcile known partial listener setup and failed builder allocation, and require original-scope actual resource cleanup before permitting recovery. No default media activation; broader borrower/migration/native final-authority constraints remain.


## MR-START2b1 original runner/site/start ownership reviewed

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

MR-START2b2 next: seal teardown to original context/dependency owners across awaits; protect stop-task creation acknowledgement loss against replay; then qualify auxiliary service publication and explicit adapter partial-listener cleanup. Never infer whole Store retirement from this startup slice.


## MR-START2b2 bounded stop ownership checkpoint

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

Next: qualify auxiliary service publication and partial adapter recovery; do not activate media before the remaining authority, borrower and migration gates are resolved.


## MR-START2c operator-read startup ownership

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

Next: qualify approval/push auxiliary publication and recover partial adapter listeners only after actual original-scope cleanup; preserve all remaining borrower, native authority and release gates.


## MR-START2d approval context scope and push gate

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

Next: MR-PUSH1 retain creation intents and actual push drain owners, then integrate original-owner debt into Store retirement. Do not substitute bounded close for actual settlement.


## MR-PUSH1 actual task/native borrower drain

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

Next MR-PUSH2: retain failed dispatcher/relay startup resources and distinguish actual task settlement from successful resource closure; then finish original-listener partial adapter recovery.


## MR-PUSH2 retained failed startup and relay success

MR-PUSH2 source `0adba02` retains returned relay and dispatcher ownership before
startup effects. Failed construction/start keeps cleanup ownership; one shared relay
close operation is retained across bounded observation and unknown Task acknowledgement.
Failed close cannot certify retirement or trigger replay. Original dispatcher/relay
owner substitution is rejected. Both pinned runtimes pass 507 combined tests unchanged,
zero failures/errors/skips; finite independent read-only review accepted the repair.
This proves successful return of the original relay close coroutine, not an independent
audit of implementation-internal resources or a factory that fails before returning.
Next is explicit cleanup/recovery of an adapter's retained partial listener. Failed
builder allocations, other borrowers, native media authority/migration, full regression
and physical/release qualification remain open. No deployment/provider/send/grant/media
activation; images and characters are still not complete.

Next MR-RECOVER1: original partial listener stop/drain, verified bootstrap/Store ownership transfer and explicit reconnect recovery; no new media activation.


## MR-RECOVER1 original partial listener recovery

MR-RECOVER1 implementation `cfc0692`, test-complete source `34329d7`, adds
explicit recovery of the original partial listener: join its component Future and actual
stop/drain, transfer the original Store close to one retained task, and clear startup
uncertainty only after known closure plus scope rejoin. Cancellation—including after
Store closure—cannot replay cleanup; callback drift/lost close acknowledgement refuse
reconnect. 514 selected cases pass unchanged on both pinned runtimes, zero failures/
errors/skips; finite read-only review accepted implementation and causal tests. Reconnect
coverage proves admission to next component opening, not a second native listener startup.
Failed builder allocations, other native/Store borrowers, media authority/migration,
full-plugin regression and physical/release gates remain open. No deployment or activation;
user-visible host-local images and characters remain unfinished.

Next: audit remaining component-builder/resource ownership and whole-plugin regression separately from mobile visible feature integration; no native/media/physical release pass is inferred.


## Wide unit regression — unresolved contract gates

Wide unit regression at `428583f` is NOT qualified: 47 failed, 8,182 passed,
15 skipped; 190 passing subtests are additional JUnit nodes. Repair `7f3ac82` restores
readonly push-status counts on exact known schema 3/4 without migration/auth/writes,
with unknown schemas still refused; an outdated synthetic drain port was corrected.
544 focused cases pass on both pinned runtimes. A short private harness root separately
resolves 17 Unix socket-path fixture failures; all 67 affected-module cases pass on
both runtimes without weakening product bounds. Nineteen original failures remain
unresolved (frozen/inverse/route contracts, migration expectations, S5 media references
and module manifest). No full rerun after repair, no automatic repinning or release pass.
Fresh readonly inventory: iPad installed 2026110702, Android beta 6 connected, iPhone15
currently disconnected. No app launch/install/UI qualification or host/media activation.

Next: diagnose S5 media reference provenance and migration/version claims, then frozen inverse/route/module contracts with independent review; do not replace a failed guard with automatic acceptance.


## Reviewed original failure reconciliation — full rerun pending

Reconciliation source `1afc818` addresses the remaining original media/migration/
source-contract failures in selected checks. S5 now uses actual current permission
generations, explicitly rejects unversioned/wrong-generation callers, and retains native
kind-forgery refusal. Legacy migrations prove no explicit media grants and preserved
controls/data. Historical hashes remain unchanged behind exact test-only composition
inverses; eleven new modules are individually enumerated. Review found and resolved a
newline-normalizing witness reader; actual-file CRLF/lone-CR tests now protect raw bytes.
1,127 selected cases pass unchanged on both pinned runtimes, zero failures/errors/skips;
finite independent review accepted these test contracts, not all native semantics.
Together with prior socket checks they cover all47 original failure cases. Full unit
rerun is still required;14 missing native prerequisites and1 Linux-only skip remain.
No deployment/activation or device qualification; broader feature goal stays active.

Next: rerun complete unit selection with short owned paths and preserve all outcomes; configure exact native prerequisites separately, never convert skips or historical composition into release approval. Builder/native media authority/migration and physical gates remain.


## Full unit reruns and initial physical launch checks

Full reconciled unit reruns at `889a31b` report zero failures/errors with unchanged
source: current8,257passed/15skipped; floor8,255passed/17skipped, plus190passing
subtests each. Strict qualification remains false: native prerequisites, Linux-only
coverage and two floor UUID7 cases remain explicit. Subsequent test-only SDK verifier
`72a27a9` follows Hermes0.23 explicit class re-exports without native import/execution;
26checks pass for each ed1/0f0 committed-source sample and23portable parser checks pass
on3.11. Finite review accepted declaration checks, not effective native behavior.
Device observations: Android beta6 launches, unpaired onboarding and demo entry/exit
observed; iPad702 launch/activation accepted with matching PID/executable observations
more than2minutes apart. No cold-start/UI/persistence qualification. LB1-T008 staysopen;
Android host preference awaits the owner and iPhone15 is disconnected. Existing hosts
still match expected5ecd installed-file checks; no new install/config/grant/media activation.
New lifecycle fixes remain source-only; a minimal schema-preserving host backport is next.

Next: minimal migration-free lifecycle backport after exact review/tests; paired organizer/persistence after owner host choice; native media authority/migration, failed-builder allocation, wider native probes and release/device gates stay open.

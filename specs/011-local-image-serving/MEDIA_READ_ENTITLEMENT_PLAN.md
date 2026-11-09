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

# Media publication writer coordination — incomplete development branch

The optional Store observer on `feat/media-authority-publication-20261108` is
currency coordination only. No listener installs it, no live host is changed, and
it does not authorize media access. Stores created without it remain unobserved.
This does not resolve the final synchronous-check responsiveness defect.

## Observed Store boundary

A syntactic census of Store at6c8be35 found37 methods containing mutation,
transaction-control or dynamic SQL calls. That is not37 proven authority writers:
`push_status_snapshot` has a read-only BEGIN, while `_in` helpers depend on their
caller's connection/transaction. Context presence alone does not prove ordering.

| Path | Prepared coordination | Remaining evidence |
| --- | --- | --- |
| `transaction()` | Original construction-time observer begins before lock/SQL; exact receipt retained; definite commit/rollback certainty recorded under lock; settlement afterward | Actual listener actor, blocking-rendezvous refusal and exact handoff faults |
| `_owned_write` methods | Join `_serialized_writer` then observed transaction | Complete entry/call-site census and actor coverage |
| `_serialized_writer` methods | Existing owner joins once; otherwise observed transaction | Mixed-thread/ownership and complete call-site qualification |
| `_in` push helpers | No new implicit transaction | Prove callers hold original Store transaction; no foreign raw connection |
| `push_status_snapshot` | Read-only private BEGIN remains separate | Must not mistake transaction control for authority mutation |
| `migrate()` | Startup path intentionally unobserved | Must run before publisher admission; quiesce old processes |
| `close()` | Intentionally unobserved | Listener must close publisher before store retirement |
| Other Store objects / CLI processes | Default unobserved | Supported writes need typed daemon-owned coordination before effect |
| Native bot/profile/config writers | No coverage established | Exact native writer/revision/lease contract inventory required |

## Failure contract

No original begin receipt means no SQL and no attempted settlement, including
None or lost return. Never recover ownership by inspecting a current pending
mutation. Confirmed body-error rollback may settle certainly while preserving the
body error. Lost COMMIT/ROLLBACK acknowledgement poisons Store and settles
uncertainly, even if independent readback later shows a persisted result. A lost
observer settlement acknowledgement must not replay or roll back committed SQL.

The observer is fixed at construction and its bound methods held locally across
the transaction. It is not a provider/request-selected callback. A future actor
must reject a listener-thread blocking rendezvous before waiting. Full publication
cannot be enabled until all relevant writers invalidate before effect and settle
under the same authority owner. Polling, TTLs and cached grants are insufficient.

## Listener actor preparation — d6f57d4

The unwired MediaPublicationActor now implements the in-process observer protocol.
Only fixed currency operations run on the original listener thread. Worker callers
wait up to250ms for acknowledgement; listener-thread rendezvous is refused before
enqueue.32 queued-operation slots bound admission. A callback releases its original
slot only after actual retirement; unknown enqueue/acquisition retains debt and
closes admission, while proven-unused reservations can be released. Futures are
not cancelled on observation timeout. Sticky failure is checked before and after
candidate/claim operations, together with original publisher/loop/thread identities.

Seven actor tests and the existing Store/currency regressions pass (287 cases on
each interpreter). A real Store worker fixture holds SQL while listener sleep
remains responsive, then settles; queued-deadline loss starts no write. Worker
failure during actual currency-clock callbacks refuses output. Allocation failure
before enqueue releases all proven-unused capacity and closes admission. The first
timeout fixture had a scheduling race; its failed evidence is retained, and the
corrected fixture prevents delivery until after the deadline.

No adapter installs this actor. Typed operator IPC, original listener lifecycle
binding, complete Store entry/retirement/migration coverage and native bot/config
mutation contracts remain required. The existing final synchronous diagnostic
collector is unchanged. Actor tests therefore do NOT close LM-ENT1-P1 or qualify
complete authority, responsiveness, runtime, device or release behavior.

## Shutdown/lifetime preparation — 07a02c5

Publication close and mutation lifetime retirement are distinct. The actor stores
an original debt intent BEFORE requesting a mutation receipt, retains that receipt
before acknowledging it, and preserves unknown/unsettled debt through close.
Closed settlement may retire only exact original debt; it cannot restore currency
or provide a business-success acknowledgement. Cleanup has separate bounded
capacity and releases the original reservation only when its callback really ends.

wait_drained is available only on the original closed loop and requires empty
mutation debt. It does not prove arbitrary worker threads terminated or that an
uncertain COMMIT/ROLLBACK outcome became known. A timeout never erases debt or
authorizes Store close. Unknown begin/partial settlement may conservatively retain
debt indefinitely. The listener must keep cleanup delivery alive until its owned
SQL work can settle; it cannot stop the loop first and infer successful retirement.

The fixed original Store-finally path is the required ended-SQL handoff. Merely
possessing a receipt is not independent ended-worker proof; do not expose cleanup
as a user/remote mutation API. Tests cover a held real Store worker across close,
no early drain, original-receipt cleanup, unknown begin return debt and cleanup
under saturated new-begin admission. Both291-case suites pass. Independent delta
review found no new concrete blocker under these assumptions. Adapter lifecycle,
operator/native/config coordination and complete serving-path qualification remain
unimplemented; no live resources are managed by this actor yet.

## LM-ENT1-OP1 — operator mutation request contract (source preparation)

A future separate same-UID local mutation endpoint must retain existing bounded
parent/socket/peer/inode checks. The current read-only socket stays read-only.
The human CLI's existing exact typed confirmation, current listener validation and
repeated snapshot remain required; socket possession is host-UID authority, not
proof of human consent. Mobile never gets this interface.

The closed request is protocol1 / host_media_read_decide with exact instance,
listener nonce, listener generation, random attempt identifier, stable device ID,
expected complete MediaReadDecision and exact Boolean allowed. Signed64-bit
revision/epoch counters use canonical decimal strings in this new protocol to
avoid JSON integer rounding; the codec does not reinterpret older read protocol.
No arbitrary operation, path, provider, job or other privilege is accepted.

Before SQL: verify current original listener/cohort and active pairing; reserve
publication invalidation through the original actor; apply Store's complete
snapshot CAS only. Settled readback must match original request and committed
revision. A duplicate/stale CAS cannot repeat the write. Missing/lost response is
unknown, never automatic retry; explicit read-only status/readback determines next
operator action. Attempt IDs correlate responses, not a fabricated durable replay
ledger. Listener restart invalidates old nonce/generation. Mutation execution,
response receipt, lifecycle and transport are not implemented by a request codec.

OP1 codec checkpoint1794e43: closed request DATA parsing/encoding is implemented,
with35 cases passing on each interpreter. It retains the full signed64-bit Store
counter domain as canonical decimal strings and validates complete expected-state
consistency. Independent read-only review found no concrete codec blocker. No
transport, response receipt, runtime scope/nonce/peer verification, consent proof,
CAS execution or listener wiring is provided by this codec. Attempt IDs are
correlation only, not durable exactly-once authority. These remain explicit tasks.

## OP1 trusted-local execution preparation — d788615

The unwired MediaOperatorExecutor captures the original Store/observer, listener
identity/bridge/IID/generation, publisher/failure state and bound transaction/CAS/
read methods. Loop-thread calls refuse before native or SQL work. A bounded fresh
monotonic deadline is mandatory; its provenance remains the future transport's
responsibility, not something nonce/generation or a client-supplied float proves.

A worker joins one coordinated Store transaction, checks the original cohort
around identity callbacks, applies the complete expected snapshot CAS, and checks
again before commit. Authoritative readback and postcommit cohort/deadline checks
precede any result, including conflict. Missing results once SQL could start are
fixed unknown outcomes; committed data is never rolled back or replayed by this
layer. The object verifies neither socket peer identity nor human CLI consent.

Both43-case codec/execution suites pass, including actual Store grant/revision1,
duplicate old snapshot conflict without revision advance or Controls change,
prewrite scope/deadline/loop refusals, postcommit readback loss, post-CAS/precommit
cohort-drift rollback, and replaced publisher refusal. Independent source review
found no concrete blocker in the initial unwired executor; independent review also found no concrete issue in the narrowing delta.
Transport/admission/consent/deadline origin, response framing, operator
IPC and native/config publication coordination remain incomplete. No route calls
this executor and no live permission changed.

## Transport namespace preparation — c3ae41b

A separate focused branch prepares closed read/media socket layouts. The default
read socket and512-byte read parser/handler remain unchanged. Only the fixed
media-operator.sock namespace can select a4096-byte future envelope bound; this
selection alone still installs no mutation handler. Bound-parent/entry checks and
cleanup use the original selected name, with one inode sample at cleanup. Full
server/tools lint and56 read/FD/layout tests pass on each interpreter. Independent
read-only review found no concrete namespace/FD regression in the finite refactor.
An isolated subset exposed an existing adapter-fixture import-order dependency;
it now declares that fixture explicitly, retaining the failed run's evidence.

The write service is NOT implemented. Before enabling it: bind one short-lived
server challenge to one verified same-UID connection and original listener cohort,
consume it before queueing, bound accepted connections and actual worker futures,
and preserve original worker/debt through timeout and stop. A cancelled async
wrapper is not proof that its underlying thread finished. Existing read sockets
must never acquire mutation operations by fallback or unknown operation parsing.
Human CLI consent and actual current authority remain separate obligations.

## Unwired mutation service and bounded integration — be1f84b

The fixed separate media socket now has its own handler, verified same-UID peer,
connection-specific single-use challenge and server-origin two-second deadline.
The service bounds waiting clients and admitted worker operations separately at
two. A complete request passes the closed mutation codec before dispatch. No
adapter starts this service and no human-consent CLI client is wired to it.

Only the original concurrent Future's completion retires an admitted operation.
Caller timeout/cancellation returns unknown without cancellation or replay of SQL.
A possibly enqueued submission whose acknowledgement is lost poisons admission
and retains an unresolved operation even after a test separately observes commit;
stop cannot certify that Store safe to close. This condition needs explicit
lifecycle handling, not a forced debt reset. The existing direct CLI Store writer
and other-process/config/native writers remain outside this actor protocol.

A causal late-failure test reproduced an unhandled wrapped Future exception after
timeout at113f8a8. The be1f84b fix consumes eventual wrapper exceptions without
logging diagnostic text or granting that callback worker-retirement authority.
That specific logging defect is fixed in this unwired source; deployment is absent.

The unchanged source passes142 combined cases on Python3.14.9 and3.11.15, covering
existing read/FD/layout, request/reply codecs, actual Store/actor CAS and17 new
service cases. Those service cases cover foreign challenge/nonce/generation/peer,
malformed duplicate/oversize/deep/extra/type frames, waiting-client bound, cohort
replacement, actual-worker retention after timeout/cancellation, uncertain enqueue
and late-error consumption. This does not establish human consent, full listener
retirement, native authority freshness, schema migration/rollback or physical image
display. Those remain release gates. Independent service review is pending.

## Reservation interruption repair — e948e83

Independent review found allocation/registration and then reservation-return loss
windows in pre-submission accounting. Intent allocation now precedes any budget
reservation; registration occurs before acquisition. Known registration failure
therefore cannot have submitted work or acquired capacity. Definite False removes
only the known-unacquired intent. Acquisition exception/nonboolean result retains
that original intent, poisons admission and returns Unknown without guessing a
refund. Subsequent submission and actual-Future retirement retain the same ledger.
Stop reads ledger-derived debt rather than a separately allocated integer counter.

The reviewed correction passes148 combined cases on each interpreter, including
23 service cases and new allocation, before/after registration, before/after
acquisition-return loss and definite-capacity-refusal checks. Full Ruff passes.
Independent read-only delta review found no new concrete blocker in this fix.
Unknown acquisition can conservatively block drain indefinitely despite no actual
SQL; that is an unresolved lifecycle condition, not permission to close the Store.
CLI consent/client, listener lifecycle integration, native/config/cross-process
publication, migration/rollback and device/release qualification remain open.

## Verified one-exchange host client — 3503b48

The new unwired client uses only the fixed media-operator.sock under a verified
private held parent, validates peer UID and repeated parent/socket identity, and
requires a closed challenge matching the exact IID/nonce/generation. Its absolute
local two-second deadline also bounds the accepted server expiry. It makes one
send only, marking the outcome potentially submitted BEFORE sendall; truncated,
malformed or missing reply, late binding/deadline drift or close failure thereafter
is Unknown with no retry or direct Store fallback. A pre-send rejection reports
that no decision was submitted. Filesystem syscalls are not proven nonblocking.

Caller-verified live TLS/listener identity and fresh exact typed consent remain
mandatory and are not implemented by the transport function. The CLI still uses
its earlier direct Store mutation path; replacing that path and installing the
service require separate coordinated lifecycle work, not an implicit fallback.
Independent read-only review found no concrete blocker within this unwired client.

Both35-case focused suites pass (23 service plus12 client cases). Real socket/Store
commit and stale snapshot conflict, wrong peer, pre-send binding change, postreply
binding/decode loss and malformed/wrong/expired server challenge are covered. The
initial current run failed7 cleanup cases because newer asyncio removes its Unix
socket on close; the fixture correction retains missing-ok cleanup for the older
runtime, without relaxing protocol assertions. The initial failed receipt remains
unqualified. No host activation, live permission change or phone display is claimed.

## CLI source integration — 8b15a7a

The grant/deny CLI now retains read → exact typed confirmation → fresh context
comparison, then submits one closed request through the verified socket client.
It no longer calls Store.set_media_read or falls back to a direct SQL write when
the service is absent. A pre-send unavailable result is distinct from Unknown;
Unknown/malformed/missing outcomes require inspection without automatic replay.
A committed reply still requires authoritative stored and original live-context
readback. Read-only media-read status and existing global CLI TTY guards remain.

Both186-case combined suites pass unchanged on Python3.14.9/3.11.15, full Ruff
passes, and independent read-only CLI review found no concrete blocker in the
finite delta. Four new synthetic cases run the actual confirmation function,
actual socket client and service, actor and Store CAS for allow/deny/wrong/EOF.
The CLI Store mutator lookup is forbidden in that fixture; the service uses its
original captured mutator. Host TLS/listener context is explicitly mocked in this
fixture and therefore not runtime-qualified. Seven additional CLI boundary cases
cover unavailable/unknown/conflict/refused/malformed replies and read-only status.

This replaces the earlier direct-writer checkpoint only in isolated source. The
adapter does not start the service; deployed5e remains unchanged. Listener/actor
retirement, schema4 quiesced migration, other-process/native/config publication and
physical/release checks remain open. No live device grant or host flag changed.

## Read-service actual-worker prerequisite — aaa29aa

The existing read-only service used a Task wrapping asyncio.to_thread and retired
its Store borrow when that Task completed. A corrected causal control at979fbe0
cancelled all async waiters in an isolated loop while the synchronous read remained
blocked: operator budget incorrectly became0 instead of1. The earlier569e571 test
masked that assertion with cleanup timeout; its failure is retained separately.

The repair uses a bounded original concurrent Future pool and intent ledger for
read-only operations too. Only actual Future completion retires the original
budget; async cancellation/timeout cannot. Registration/preconditions precede
acquisition, uncertain acquisition/submission retains debt with fail-closed
admission, eventual wrapped exceptions are consumed, and delivery rechecks original
context/budget/generation/deadline. Stop closes admission and shuts the pool without
cancelling actual work. This does not prove all native/HTTP work has retired.

Both191-case combined suites pass unchanged on3.14.9/3.11.15; full Ruff passes.
Independent finite source review found no additional blocker after setup reads
moved before acquisition. AST comparison verified all31 prior top-level definitions
in test_operator_read.py unchanged by the last formatting delta; three new test
functions add acquisition loss, submit loss and original-budget replacement checks.

OPEN RSWORK1: the same Task-based pattern is in the deployed5e247a6 baseline.
No live incident is observed or claimed. This repair currently exists only in
isolated source; a minimal separately reviewed/tested backport and deployment is
needed before the production risk is considered resolved. Do not activate schema4
or the media mutation service merely to deploy the read-only lifetime repair.

## Original media-lane retirement preparation — 1f8fd9a

An unwired MediaOperatorRetirement now captures the original service, actor, Store,
budget, executor, operation/mutation ledgers and publication/failure objects plus
loop/thread and identity/bridge/IID/generation/nonce scope. Shutdown closes service
admission and actor publication before any await. One retained Task joins actual
service worker debt and actor SQL settlement; cancelling a waiter does not cancel
that owner. Completion requires the original scope and both original ledgers empty.

It NEVER closes Store or claims all HTTP/read/native borrowers finished. Its
completion check is valid only for that exact Store and original scope. Unknown
creation retains its coroutine and sticky state, never inferring that it was
unqueued or creating a replacement owner. The adapter must retain unresolved
coordinator/coroutine ownership. Failed/cancelled owner work returns a distinct
private failure token, not success or private unhandled-task diagnostics. A known
retained Task may be observed again after reporting registration loss; this waits
on the same owner rather than replaying shutdown or SQL.

Both199-case combined suites pass unchanged on Python3.14.9/3.11.15 and full Ruff
passes. Independent finite source/delta reviews found no further concrete blocker.
Eight retirement cases cover idle/idempotent/exact-Store/noclose, cancelled waiter
with actual worker borrow, actual Store rollback and actor settlement, unknown
submission despite separately observed commit, before/after scheduling return
loss, callback registration loss and changed-generation refusal. Whole-listener
integration and resource ownership, schema migration, native/config publication,
physical image display and release qualification remain open. No deployed host
uses this coordinator or the new media mutation service.

## MR-LIFE2a: optional listener retention — 13703e9

HmpServer can now retain an explicitly supplied exact media coordinator for its
original context/Store; the default remains None and nothing starts the service.
The synchronous begin closes admission/publication before shutdown awaits. A
retained sentinel forces later Store-close handling through combined read/media
drain while ordinary network cleanup proceeds even if media owner creation is
unknown. Unknown creation stays latched; it cannot be silently retried or cleared.

Drain requires an actual listener stop owner and completed network teardown. It
holds and rejoins the original server context, read service, media owner and Store
before/after every await and before clearing debt. Source review identified these
early-call/postawait drift gaps; the narrowing fixes and causal tests are included.
The final style-only guard wrap is AST-identical to reviewed d7dfcba.

Both308-case combined suites pass unchanged on3.14.9/3.11.15, full Ruff passes, and
independent finite review found no further concrete blocker in this listener delta.
New cases cover synthetic runner cleanup while actual media work remains, unknown
owner creation, constructor scope refusal, premature drain refusal, and context/
owner replacement during await. The initial305 run failed two stale route-count
assertions from the prior two GET diagnostics; exact declared-route equality was
preserved and those GETs are now explicit. The failed receipt remains unqualified.

This is NOT completed MR-LIFE2: adapter-retained Store owner/reconnect protection,
all other borrower retirement, schema migration, native/config publication and
physical/release qualification remain open. No adapter supplies the coordinator,
no media service starts by default, and live hosts remain on c7482f1 only.

## MR-LIFE2b: retained adapter Store owners — 5f684b8

The adapter records the original server/context/Store/bound close method before
dropping its listener pointer. Every retirement keeps its own coroutine, actual
Task and opaque completion/failure result. A sticky setup latch covers allocation,
registration and unknown scheduling; a lost handle never authorizes retry. A
cancelled disconnect waiter leaves the actual close owner alive. Failed/cancelled
owners return a private failure token rather than leaking an unhandled exception.

Connect checks retained owners before open_components. Pending, failed or unknown
retirement blocks replacement; only the actual retained Task's successful close
result can be reaped. Scope is rejoined after drain and again after generation
cleanup before invoking the original bound close once. A causal40ac2e0 control
showed that omitting the second server-reference check could falsely complete after
a generation callback installed another server sharing that Store; the narrowing
fix and failing control are retained separately.

Both342-case combined suites pass unchanged on3.14.9/3.11.15 and Ruff passes.
Independent finite source/delta review found no further concrete blocker. Nine
synthetic fault cases cover pending reconnect before open_components, cancelled
waiter, before/after scheduling loss, close acknowledgement loss, context/Store and
generation/server callback drift. Existing25 adapter cases remain in the suite.
No live Store, configuration, permissions or deployed code changed in this work.

This completes the bounded retained-owner/reconnect source slice, not whole
activation qualification. Concurrent startup/bootstrap cancellation, all other
HTTP/native/thread borrowers, migration/rollback, final native authority publication
and physical/release acceptance remain separate gates. The media service is still
not started by the adapter, and deployed hosts retain c7482f1 only.

## MR-START1: lifecycle exclusion source — d524059

A per-adapter lock now serializes connect/disconnect. The730e908 causal control
reproduced two component-opening workers active together. Successful concurrent
connects now share one synthetic real TLS listener; failed attempts may run again
only sequentially. Disconnect waits for an executing startup. Cancellation while
waiting for the lock does not poison the lifecycle.

An executing connect that loses completion latches startup uncertainty, preventing
another bootstrap even after a fixture separately observes worker end. Executing
disconnect failure/cancellation similarly refuses the old server shortcut rather
than reporting a stopping listener connected. Only explicit disconnect cleanup
with no current server and actual retained Store-close proof clears that latch.
Unhandled failures are conservative; controlled False paths retain their behavior.

Both350-case combined suites pass unchanged on3.14.9/3.11.15 and Ruff passes.
Independent finite source/delta review found no further concrete blocker within
this exclusion scope. It is NOT MR-START2 bootstrap ownership/recovery: actual
component Future, partial context/listener cleanup and controlled failure cleanup
still need qualification. The startup latch deliberately does not auto-clear.

No live incident is observed, no deployment was performed and media remains
inactive. Concurrent-opening protection exists only in this source branch; retain
that distinction until a separately qualified update is deployed. Remaining other
borrowers, schema migration/rollback, native publication and physical/release gates
are unchanged.

## MR-START2a: actual component Future and returned context — bd7feef

BootstrapOpening is recorded before enqueue, owns one actual concurrent Future,
and retains a successful native function return/context/Store/bound close before
that Future completes. Caller cancellation cannot cancel this worker or drop those
resources. Unknown enqueue retains the owner even if a fixture separately sees its
context return; no cleanup or retry is inferred from that observation.

Before a listener object exists, explicit disconnect may await that same Future
and close the exact unpublished context once. Original adapter/opening/future/ctx/
Store/bound-close identities are held and rejoined around generation cleanup; any
lost close acknowledgement prevents replay. Source review found mutable close/
coherent-context substitutions in the initial version; bf5623a controls reproduced
both and are retained. Close-state flags require exact False without foreign bool.
A partial listener is retained before its first startup await and is NOT guessed
to be cleaned up. Its recovery remains MR-START2b; previous eager Store close was
removed. Controlled IdentityError False behavior retains the existing builder
contract, not a new claim that every partial builder failure is qualified.

The native worker preserves asyncio.to_thread caller-context semantics using one
original copy_context captured before enqueue, context.run on the worker, and no
context logging. The e972a56 control reproduced missing context transfer before this
repair. That context may contain ambient scope references and must stay retained
until actual completion/known transfer, never dropped due to waiter cancellation.

Both363-case combined suites pass unchanged on3.14.9/3.11.15; Ruff passes and
independent finite source/delta reviews found no further concrete blocker. New
checks cover cancelled caller plus actual returned-context cleanup, close return
loss, unknown enqueue, close/cohort substitution, retained partial listener,
malformed close flags and context inheritance/isolation. They do not qualify all
native profile authority, failed-builder allocation, partial runner/TLS cleanup,
other borrowers, migration, publication or phone/release behavior.

Next: audit context propagation in the earlier read-worker backport separately;
then retain/reconcile each partial listener setup stage and failed builder resource.
No native profile side effect or auth bypass is inferred from the context audit.
Nothing from this source branch was deployed; live hosts remain c7482f1.

## Read-worker context parity audit completed — 81f3725 / 5ecd2ba

The earlier direct read-pool submission lost caller ContextVars compared with
asyncio.to_thread. A synthetic marker control on16ca49c reproduced the mismatch;
no real context values were inspected/logged or native profile/auth effect claimed.
Each read now copies its caller context before any reservation and runs the same
collector through that context on its original actual Future. Debt/settlement,
late-error handling, timeout and same-origin checks are unchanged.

Both593-case minimal-backport regression suites and364-case feature suites passed
unchanged on3.14.9/3.11.15, plus Ruff, Plugin Doctor and independent finite source
review. Pinned5ecd2ba7e580e86e3d91bcae38f0584bcc366077 is now installed on both
hosts, with109 files, fresh matched gateway/listener PIDs, expected TLS identity and
unchanged configuration/device-controls/schema snapshots verified. Prior channel
states remain; LLY520 Lucas/Serenity still produce aggregate health exit1.

This deploys only the small read-context parity repair atop the earlier safety
backport. The feature-branch bootstrap/retirement/media additions remain uninstalled.
Partial listener/builder resource recovery, all other borrowers, migration, native
publication and physical/release qualification remain open.

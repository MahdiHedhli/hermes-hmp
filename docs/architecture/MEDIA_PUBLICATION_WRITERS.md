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

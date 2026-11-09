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

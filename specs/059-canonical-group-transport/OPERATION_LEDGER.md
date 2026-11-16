# GT2-LEDGER portable accounting model

This component has no production caller. It does not close GT1 or GT2, connect to
Hermes, grant authority, retain credentials/payload, start a worker or prove native
resource settlement. It is a prerequisite for integrating those actual owners.

GroupOperationLedger requires explicit positive bounded integer limits, with no
production defaults. It is confined to the constructing Thread object. Operations
and reservations use exact builtin object identity registered in that ledger;
foreign objects are refused before hash/equality/format/conversion hooks. Private
Python implementation fields are trusted, not claimed tamper-proof.

The trusted future owner supplies a nonrenewing absolute deadline captured before
queue waiting, measured descriptor/payload byte sizes and monotonic clock samples.
These are internal data, never client-supplied authority. Lossy integer-to-float
samples are refused, as are bool/custom objects, nonfinite/negative/backward time.
Queue-to-pending transition does not renew the deadline. Temporal publication
eligibility is not device/room/bot authorization and must never replace it.

Queue, pending, descriptor, reservation-count and retained-byte accounting is
shared across generations. Retire fences output out-of-band even at full capacity,
without freeing debt. A new model generation cannot reset old records or budget.
Expiry also fences output without automatically freeing records. Reservation
release is once-only from the originally recorded size. Operation release refuses
while model reservations remain. Stale and cross-owner handles do not reclaim a
new record; deleted records leave no accumulating tombstone table.

Crucially, release_operation with zero model bytes does NOT establish that any
actual actor/socket/writer stopped. The future actual owner must establish and
retain that evidence separately before invoking release. A model ledger alone
cannot authorize reconnect, settle a lost start/close, close Store or certify
cleanup. Application byte accounting is not a decoder/native-memory/RSS bound.
Numeric caps remain provisional until full canonical shapes are qualified.

## Verification

Exact source and tests were formatted and pass focused Ruff. The67-case suite
uses fresh isolated HOME/HERMES_HOME/runtime, disabled auto-plugins and no native
service. Review found lossy integer clock coercion; it was fixed before publication
and adjacent/decreasing large-integer boundary cases now pass. Independent byte,
count and queue tests avoid mutually masking guards.

Disposable module-copy causal checks preserve the production source throughout:
removing deadline expiry causes2 failures; removing reservation count causes1;
resetting retained bytes on new generation causes1. All67 unchanged positive tests
pass after each process uses the original source. No runtime or physical pass is
inferred from these model tests. Native snapshot, phone group grants, complete
frame/decoder shapes and concrete transport custody remain unresolved GT1 work.

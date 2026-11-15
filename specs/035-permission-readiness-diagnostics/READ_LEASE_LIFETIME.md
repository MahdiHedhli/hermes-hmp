# HTTP readiness read lease — implementation contract

Status: independently accepted implementation contract; source and integration independently accepted after 653 passing cases with 556 bound inputs unchanged. This supports Mobile AR1-P1/spec049; no new endpoint or permission is activated here.

One listener/context-owned read service uses the original shared ReadWorkerBudget (active4, operator subset2), existing readiness limiter30 and2-second deadline. It owns a direct lazy ThreadPoolExecutor(max_workers4); the existing operator pool/authority are unchanged. No allowance or worker is added to a read merely because HTTP timed out. Pool thread lifetime is not equated with read-call retirement.

## Original activity and two-end retirement

An operation intent is rooted before capacity acquisition/submission. Reserve false removes the unacquired intent; a throwing/nonboolean acquisition poisons shared accounting and retains uncertainty. The returned concurrent Future is bound BEFORE callback registration. Registration can run immediately for an already-completed Future. An unknown submit or callback-registration outcome fences the service and retains the original intent/capacity; it never refunds, resubmits or replaces an executor.

The Future callback only marshals to the original loop. A closed loop or failed marshal retains debt, with no off-loop Store access. Exact intent/Future identity rejects duplicates. Worker-terminal notification alone cannot retire: the HTTP handler still owns its post-await authority/readback/serialization tail. An async context-manager lease ends that caller half in finally on normal return, timeout, cancellation or error. Only BOTH actual Future terminal and caller-tail ended can release the original charge, once. A release attempt is claimed before the possibly failing ledger call; ambiguity retains ownership and poisons capacity rather than retrying.

Copy contextvars for the original work. Pin context, Store, identity, bridge, budget and generation; reject retargeting. Worker exceptions cross the boundary only as fixed contract/readiness failures, never arbitrary callback text. Shield the asyncio wrapper; cancellation/timeout does not cancel or retire the actual worker. Never run an arbitrary callback or SDK operation while holding the budget lock. Service bookkeeping is origin-loop-only.

## Shutdown and all close paths

Stop fences admission before one known executor.shutdown(wait=False,cancel_futures=False) attempt. A failed shutdown remains owned/unavailable; do not retry an uncertain effect. Reads already in flight keep both halves and Store until actual drain. Draining is an I/O lifetime fact, not proof that every idle SDK Thread has died.

HmpServer tracks readiness debt and exposes wait_readiness_drain. Normal disconnect, identity change, failed startup and runner/application cleanup all stop admission. Every adapter dependency-close branch includes readiness debt; deferred close waits for readiness, operator and presentation drain before Store.close. A pending readiness closer blocks reconnect/replacement; existing operator-only reconnect policy is not broadened or silently changed. Failed/cancelled closers remain retained. A stopped context never silently constructs a new read service.

Drain cannot wait from its own active caller lease or worker context, a callback, service lock or Store lock. Record the exact caller Task, distinguish worker context from an inherited context in a detached shutdown owner, and reject an actual self-wait. All legitimate close call sites must be reviewed as outside those locks/scopes. Context/reconnect replacement never turns an unknown prefix into absence.

## Migration and acceptance

Both existing HTTP jobs/model readiness and media readiness migrate to this lease. Preserve media's final authority fence INSIDE the caller scope; do not remove it for a nonblocking claim. Its existing synchronous I/O remains separately described. The new self-only endpoint later must avoid unbudgeted blocking callbacks.

Causal tests must use actual concurrent futures/workers for instant completion, timeout, caller cancellation, running-worker cancellation attempts, queued-then-throw submit, callback registration failure and stop/drain. Cover duplicate retirement and release failure, exact source/generation replacement, independent operator subset/shared capacity, and Store remains open until both ends. Handler/adapter tests must prove all normal, identity-change and failed-start dependency-close branches and reconnect refusal while readiness debt remains. No live host, provider, token/grant mutation, new endpoint, device or release claim follows from these tests.

Implementation ownership includes exact context/Store/identity/bridge/budget/generation binding and a sticky observed-source-loss fence. The context service field is init=False: dataclasses.replace creates a new unbound context rather than copying an old runtime owner. Foreign, stopped or drifted services are rejected without replacement. Only successful dependency-close tasks leave the readiness closer set.

Verification (2026-11-15): both causal omissions fail on their intended premature refund/Store-close assertions; restored implementation passes. Twelve existing baseline modules were added by literal name to the closed module inventory, preserving exact equality and extending import checks; readiness_work.py is the sole new product module. Private terminal receipts retain earlier setup and stale-inventory failures separately. No host, phone, endpoint or release qualification is asserted.

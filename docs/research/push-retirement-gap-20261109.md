# Push retirement gap — November 9, 2026

Read-only source inspection at `574899c`, not a live incident or deployed qualification.

`PushDispatcher.start` creates worker tasks before publishing the insertion observer. A task creation exception closes the coroutine even though enqueue acknowledgement may be unknown. `_schedule` has the same acknowledgement ambiguity for trailing tasks. `close` cancels known tasks and bounds `asyncio.wait`; it consumes late failures but does not provide a proof that every borrower has actually settled. The existing cancellation-resistant-close test intentionally exercises that bounded return. `HmpServer._start_push_dispatcher` suppresses cleanup failures after construction/start failure and publishes the dispatcher only after `start` returns.

These are unresolved ownership/lifetime gates for the new lifecycle/media branch. No authorization bypass or observed live data exposure is claimed. Do not treat a bounded close or private callback as all-Store-borrower retirement. Keep branch undeployed pending repair/review.

Required next slice:

1. Record original coroutine/intent before task creation; unknown publication stays retained and prohibits replay. Never close a possibly enqueued coroutine based on an exception alone.
2. Retain the dispatcher/relay at the listener before startup effects. Separate availability from lifetime ownership.
3. Keep bounded network shutdown, but expose an original-owner drain that joins actual tasks, retains unknown task creation, and does not cancel actual ownership because one waiter is cancelled.
4. Include push debt in listener/adapter Store retirement, rechecking context, prompt Store, relay, insertion observer and listener identity across awaits. Never close a replacement owner or clear a replacement observer.
5. Cover cancellation-resistant worker/relay, creation acknowledgement loss before/after enqueue, failed constructor/start, lost close acknowledgement, replacement/revocation and no replay. Use synthetic ports; no actual push/provider/send or host redeploy.

Approval generation context pinning is a separate bounded repair; it does not resolve this gap. Partial builder/listener recovery, other Store borrowers, migration/native media authority and physical qualification remain separate gates.

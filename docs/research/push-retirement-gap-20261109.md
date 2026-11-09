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

## MR-PUSH1 finite repair checkpoint

Exact source `fc06ef3f5487124d8708fedf883d5f5aa46d37b8` adds original coroutine/wrapper/task journals, one shielded close owner, no replay after unknown task-publication acknowledgement and actual-task drain after bounded network close. Original ctx, prompt Store, hint collection and relay are pinned. Listener retains the dispatcher and carries nonzero borrower debt until its drain completes.

Independent read-only review found that the initial `b9d7505` task-only journal did not own native `to_thread` authorization work after cancelling dispatch. Final `fc06ef3` runs both explicit authorization threads, key reads and the gate callback in separately journaled shielded borrower Tasks. Dispatcher shutdown cancels workers/slots but not these borrowers. The causal test uses a real blocked authorization thread through observe→ready; cancelling dispatch and a drain waiter cannot discharge it. The thread must actually return. Reviewer accepted this finite repair, with no new blocker; direct cancellation of the actual private borrower Task or event-loop destruction remains outside that guarantee.

500 selected tests pass unchanged on Python 3.14.9 and 3.11.15 with zero failures/errors/skips:
- `/private/tmp/hermes-qa-push-actual-drain-current-bsug_824/receipt.json`
- `/private/tmp/hermes-qa-push-actual-drain-floor-kwa1tfek/receipt.json`

The earlier 494/497/498/499-case checkpoints do not qualify the final native-borrower repair. No suite or review certifies successful relay closure: result-consuming ownership proves task settlement, not successful resource closure. Failed dispatcher constructor/start retention still needs repair. Other Store borrowers, partial adapter recovery, native media authority/migration and physical qualification remain open. No host install/restart, provider/send, grant or media activation occurred.

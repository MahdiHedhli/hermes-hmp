# Listener shutdown ownership checkpoint — November 9, 2026

Source: `171a394` (not deployed).

Shutdown records its attempt and coroutine before creating its one cleanup task. If task creation raises before returning its handle, repeated shutdown refuses to replay cleanup. A privately running task returns its failure as a result so a lost handle cannot emit an unobserved task exception. Retained callers receive the original exception; cancellation of a caller still leaves the actual task shielded.

Causal tests exercise both pre-enqueue refusal and post-enqueue acknowledgement loss. The latter may actually finish network cleanup, but cannot certify Store drain without the retained task handle. Existing cleanup acknowledgement-loss behavior remains covered.

Validation: 372 selected tests passed on Python 3.14.9 and 3.11.15, with unchanged tracked source during each suite, zero skipped tests, failures or errors.

Private receipts:
- `/private/tmp/hermes-qa-listener-stop-ownership-current-sd5xef2q/receipt.json`
- `/private/tmp/hermes-qa-listener-stop-ownership-floor-axjly8d5/receipt.json`

Remaining: context/dependency ownership across every teardown await, auxiliary startup publication, partial adapter recovery, all Store borrowers, native media publication contract and physical qualification. This is neither full lifecycle qualification nor release approval. Hosts retain deployed `5ecd2ba`; no flag, grant, model or provider changes occurred.

## Context/resource cohort follow-up

Source `3eee7d2` retains the read-service handle before its stop await and only detaches read, dispatcher, watcher and runner handles after known cleanup return and original-cohort checks. Context, Store, push hints, direct-send dependencies and the retained resource cohort are checked before further cleanup and after awaited stages. Three synthetic read-stop substitutions (context, dependencies, runner) refuse further effects and never report closed. This does not qualify auxiliary startup publication or all native/Store borrowers.

375 selected tests passed on each pinned interpreter with unchanged tracked source, zero errors/failures/skips:
- `/private/tmp/hermes-qa-listener-stop-scope-current-a6x60lqj/receipt.json`
- `/private/tmp/hermes-qa-listener-stop-scope-floor-welex3kr/receipt.json`

No deployment. The isolated test interpreters do not contain Ruff; no new lint pass is claimed for this follow-up.

## Operator-read auxiliary startup ownership

Source `c5222b6`: retain the original service before startup, run startup under one shielded retained Task, and join the exact Task before teardown. Unknown Task creation acknowledgement prevents retry and prevents cleanup certification. A substituted service cannot be closed in place of the retained original. Caller cancellation does not cancel the actual startup task.

Five synthetic cases cover cancellation during startup, definite startup failure, pre/post-enqueue task creation acknowledgement loss and service replacement. 380 selected cases pass unchanged on Python 3.14.9 and 3.11.15, with zero failures/errors/skips:
- `/private/tmp/hermes-qa-operator-start-ownership-current-a39isqrg/receipt.json`
- `/private/tmp/hermes-qa-operator-start-ownership-floor-s_t336y0/receipt.json`

The earlier 379-case run at `32fcecc` predates the original-service replacement guard and is not evidence for that final guard. Independent review, approval/push auxiliary publication, partial adapter recovery, full borrower/native authority/migration and physical qualification remain open. No runtime deployment or media activation occurred. Current plugin extension guidance was rechecked at https://hermes-agent.nousresearch.com/docs/developer-guide/plugins; exact pinned source remains the authority for these internal HMP lifecycle methods.

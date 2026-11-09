# Listener shutdown ownership checkpoint — November 9, 2026

Source: `171a394` (not deployed).

Shutdown records its attempt and coroutine before creating its one cleanup task. If task creation raises before returning its handle, repeated shutdown refuses to replay cleanup. A privately running task returns its failure as a result so a lost handle cannot emit an unobserved task exception. Retained callers receive the original exception; cancellation of a caller still leaves the actual task shielded.

Causal tests exercise both pre-enqueue refusal and post-enqueue acknowledgement loss. The latter may actually finish network cleanup, but cannot certify Store drain without the retained task handle. Existing cleanup acknowledgement-loss behavior remains covered.

Validation: 372 selected tests passed on Python 3.14.9 and 3.11.15, with unchanged tracked source during each suite, zero skipped tests, failures or errors.

Private receipts:
- `/private/tmp/hermes-qa-listener-stop-ownership-current-sd5xef2q/receipt.json`
- `/private/tmp/hermes-qa-listener-stop-ownership-floor-axjly8d5/receipt.json`

Remaining: context/dependency ownership across every teardown await, auxiliary startup publication, partial adapter recovery, all Store borrowers, native media publication contract and physical qualification. This is neither full lifecycle qualification nor release approval. Hosts retain deployed `5ecd2ba`; no flag, grant, model or provider changes occurred.

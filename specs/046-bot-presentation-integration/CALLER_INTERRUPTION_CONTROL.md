# Directory caller interruption control — November 8, 2026

This is isolated, uninstalled source evidence. It does not qualify a live host, mobile image feature, or physical device.

The test-only source at `9808a9309b489fc098e72d34c54500ab52fca2ed` preserves production code from `e597dfe`. A missing `os` import in the new diagnostic path was corrected before interpreting the controls. Earlier refusals without checkpoint files remain inconclusive; they are not reproductions.

Both Python 3.14.9 and 3.11.15 ran the two trace-free controls serially. Each suite has two tests: one failure before detachment, one pass after detachment, zero errors or skips, and unchanged source hashes. These are negative-control results, not passing qualification suites.

Each control observed exactly one actual producer return, native callee profile event, trace arm and injected interruption. A C profile event is not a kernel-entry receipt. With GC disabled, the pre-detach control retained the original payload through its original owned link; the post-detach control observed the weak target reclaimed. Both preserved the native debit and failed phase. The historical retirement markers remained false; the test did not invent a completed retirement or ACK.

The unresolved issue is interruption before the conditional owned-link detach in the unwired caller. A repair must retain the original actor/custody checks, preserve foreign entries and real accounting/ACK history, avoid native retries and refunds, and dispose owned raw-bearing payload aliases. Both interpreter controls and the existing caller/component suite must be checked after repair. Repeated arbitrary interruptions and wrong-actor behavior require explicit separate coverage; the current experiment proves neither.

The prior 71-test selected suite passed on both interpreters at `e597dfe`. Those passes do not cover this new interruption and do not prove actual-site integration, runtime behavior, or physical feature completion. Public feature/gist integration remains pending the repair checkpoint.

# Original signed envelope wait hold — November 6, 2026

The envelope cancellation receipt now carries a payload-free hold created before
await: original envelope scope, waiter, native scope, Future, deadline and byte
counters. Both immediate cancellation and later historical release must match
those identities. The hold does not retain the partial header bytes; existing
failure cleanup still wipes the bounded header buffer.

The new causal case substitutes all three waiter Future aliases and the native
receipt Future together only after the immediate wait checks, at cancellation
validation entry. The original pre-await hold must still reject that substitution.
Actual original-task cancellation is retained; no successful retirement is forged.

This is preparatory source work. Envelope cleanup-cause wake, signed cooperative
reader transfer, full cleanup/terminal/ACK and production composition remain open.
No device, runtime, role key, provider, grant or deployment changed. Existing
historical broker failures and sender-destination risk remain unresolved.

Verification is recorded in the private envelope-hold checkpoint after the serial
regression completes. An initial regression command named a nonexistent body test
file and ran no tests; it provides no verification credit. Independent review also
identified that the initial test injected too early and was already rejected by
old checks; the injection was moved to the actual post-wait validation boundary.

Final affected envelope/body-preflight/readiness/cancellation regression: 212 passed
in 62.16s. Lint/whitespace pass; independent read-only review accepted the revised
causal and source. This is not a new complete expanded-suite run.

# Original frozen-budget cleanup-time control — November 6, 2026

This source component continues the original signed control cursor across known
work expiry into the existing native cleanup budget. It adds no renewable timer,
new parser Task, unsigned fallback or resource/worker GO permission. Standalone
first-frame staging without a native cancellation owner remains work-time-only.

`CredentialControlCursor._time_current` checks original role material, actual
actor, service/socket/registry/input/native budget and exact signed work end.
Only a qualified exact work-clock sample establishes known expiry; generic clock
failures do not synthesize it. Work is retired before further cleanup reads.
Native local cause freezes the existing earliest cleanup end; pre-existing causes
are preserved, and the cap never exceeds original work end plus 250 milliseconds.
The signed input, registry work deadline and scope are never rewritten.

A readiness deadline may continue only after the original wait proves either its
exact registration retired or it never registered, with original scope/Future/
WakeBinding/cutoff and no unknown debt. The original qualified clock must also
confirm that wait cutoff expired. Initialization and fresh native-guard failures
are outside this timeout-continuation handler. A guard-raised TimeoutError cannot
masquerade as settled readiness. Every subsequent wait remains on the SAME Task,
socket and stream cursor, preserving original partial offsets/targets/buffer.
There is no protocol resend, cursor restart or retry of uncertain registration.

Only authenticated CANCEL can proceed during cleanup. Late GO is refused before
its header/body, and no unauthenticated prefix or invalid signature adopts a
remote window. Completed CANCEL rechecks the current original time-state before
native effects, inherits only the minimum valid window, and never re-freezes an
already retired budget. Key retirement refuses remote effects while solely local
owned cleanup remains separate. Existing native notification and dedicated
original-service consumption are unchanged in authority.

Independent source/test review accepted this bounded slice without execution.
Root affected regression passed **1,181 tests, one skipped**, 39.68 seconds;
configured repository-wide lint passed. Final focused module: **84 passed**, 12.61 seconds. New tests use actual selector deadline crossings with
partial auth/header/body before and after GO, earlier local cause, expired tail,
revoked keys, bad signature, late GO, unknown readiness and generic/TimeoutError
clock failure. They verify the same offset/target/buffer at the transition,
unchanged signed work deadline, no wait retry on uncertainty, earliest budget
conservation and no resources/worker relay.

Fixtures use synthetic role keys and peer/clock policy with real disposable
sockets/native Tasks/registry. READY remains an explicit synthetic prior grammar
fact, not a signed READY write or actual resource-start evidence. These tests do
not qualify production source/peer startup, separate-process enrollment, devices
or release.

Remaining: signed READY from actual admitted resources/input, resource/worker GO
relay and its native authority, later signed result/terminal/ACK IO and release,
production startup, native publication, STATUS and physical/release qualification.
Full character delivery is unavailable. No live host/device/mobile build,
permission, provider or key installation changed. Frozen image deployment
approval and the earlier unresolved native-destination incident remain separate.

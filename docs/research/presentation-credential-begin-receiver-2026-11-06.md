# Original broker-task signed BEGIN receive cursor

Independent read-only review accepted this bounded source/test slice. The new
`CredentialBeginReceiver` is retained on its original channel before initialization
and belongs only to the completed broker handshake's original task, event loop,
socket, clock/deadline and role context. No production startup constructs it yet.
While its claim is active or uncertain, ordinary external channel IO and close
paths refuse reuse. The unsigned phase gate remains closed after success too.

One retained private bounded cursor reads exactly the HBA1 record, HBR1-v2
prefix/header and BEGIN input body. It verifies the role signature and held
context before reading a body, validates the bounded header before allocating/
reading the input, then verifies the complete frame and independently decoded
input3/hash/scope/deadline relationship. It does not read ahead into a later
phase. It conserves the earlier broker accept deadline without rewriting the
original signed input deadline. No new task, replacement read cursor or timer
budget is created. The local maximum is 11,276 retained wire bytes, not a result
buffer or a production latency guarantee.

Pending read bytes are retained before native postchecks. Cancellation, EOF,
malformed data or retirement preserves the original claim, target/consumed byte
counts and UNKNOWN IO debt, without retry or completed-read release. Terminal
refusal clears transient payload aliases and pending/copy references and wipes
only the scope-captured original private buffer; a replaced current buffer is
neither accessed nor wiped. The new exception is raised outside the original
handler to avoid retaining the original payload-bearing error context. No memory
zeroization or arbitrary same-UID isolation is claimed.

Success retains `ConsistentBeginInput` plus historical local-read completion.
That release permits only known local IO cleanup; it does not authorize a profile,
adopt native input, reserve a registry ticket, create resources, start a child,
send GO, or establish result/terminal/native publication custody.

Root's final affected regression passed **967 tests, one skipped**, in 27.92
seconds; configured repository-wide Ruff passed. Ten focused receiver tests use
actual disposable sockets and synthetic keys with MOCKED channel/kernel/clock
qualification. They cover exact bytes/no read-ahead, signature/scope refusal,
header limit before body read, partial EOF, cancellation, earlier accept end,
context-free error/payload cleanup, and final-body native-boundary key retirement
or foreign-buffer substitution with zero foreign length/wipe callbacks. The
fixture owns and closes its disposable sockets after joining tasks; that is not
production unknown-custody settlement. The reviewer ran no tests/live actions.

Remaining: integrate the original service actor's production runtime/source/key
admission, actual registry/native input/resource validation, remaining signed
phase/direct-writer/cleanup paths, exact completed transfers, GO, terminal ACK/
journal/native publication, STATUS and physical/release qualification. No host,
key installation, permission, model, job, provider or device changed. The earlier
destination-custody incident is not resolved by this receiver.

## Earlier exact-source CI readback

Signer source `80fb5b1` CI708 plugin job128009138935 passed 8,259 tests,
190 subtests, 33 skips and 18 warnings in 408.65 seconds. Input-check source
`3c7fa4c` CI710 plugin job128012143359 passed 8,275 tests and 190 subtests,
33 skips and 18 warnings in 342.87 seconds. All three Unicode jobs and plugin
steps passed in both runs. This does not qualify receiver source `87bc9a9`.

# Original service connection's one-attempt credential input adoption

Independent read-only review accepted the bounded source/test slice. The source-only
`BrokerServiceSpine._adopt_credential_begin` derives its receiver from the exact
retained connection/channel. It requires the original service registry, enrollment,
connection membership, original task and successful original read owner. It accepts
no caller packet, registry, statement, key, replacement ticket or authorization flag.
No production dispatcher calls this seam yet.

The original receiver's completed input is reverified from its retained signed
bytes and exact frame, with current role-key/task/socket/clock context. One
connection attempt is consumed before callback-bearing admission checks. The
fixed original BEGIN enters existing grammar and `BrokerRegistry.reserve`, with
existing replay/capacity checks. The exact returned ticket is retained before
postchecks; existing `bind_input_receipt_once` binds that same original packet.
Repeated native/current/service fences surround each effect. No worker, reader
resource allocation, native profile read, GO or publication path is called.

The deadline distinction is explicit in CREDENTIAL_WIRE: all handshake/BEGIN reads
and adoption must finish under the original earlier local admission cap. Registry
work keeps the exact signed/input3 work end established before the handshake. No
end is calculated from adoption time or rewritten to fit another end. Legacy
unsigned dispatch retains its existing stricter predicate. Current key/native/work
checks remain independently mandatory; these deadlines are not permissions.

On a late refusal, the original queued ticket and any input receipt remain
retained. The connection's failed latch stays true and complete stays false.
The registry may still know a queued ticket; it is not relabeled UNKNOWN merely
to match the connection. Every future credential resource/GO path must retain the
same connection/registry/ticket/receiver join, require completed and not failed,
and independently enforce current native phase/key/generation/work authority.
Ticket existence, receipt existence, capacity readiness or a caller boolean alone
is insufficient. The existing unsigned phase gate remains closed. No retry or
unqualified debt release is introduced.

Root's final affected regression passed **1,099 tests, one skipped**, in 27.90
seconds; configured repository-wide Ruff passed. This expands the prior affected
selection to include existing registry and lifecycle/replay tests; it does not
mean 132 new tests were added. Six new adoption cases compose the actual private
service/socket/registry and synthetic native policy input with modeled peer/clock
qualification: one successful exact bind and duplicate refusal, pre-adoption key
retirement, retirement after reserve or after bind, substituted registry refusal,
and successful earlier local cap with both original ends preserved. Late failures
retain the exact ticket/receipt, start no resources, and cannot use unsigned phase
IO. The fixture closes only its own descriptors; registry debt is not released.
The initial fixture used `counts()` instead of the existing property and failed
its final count assertions; correcting that test call changed no production guard.
No reviewer tests or live host/device/provider actions occurred.

The preceding receiver source `87bc9a9` passed CI712 plugin job128018540623:
8,286 tests, 190 subtests, 33 skips, 18 warnings, 368.90 seconds. Plugin steps and
all three Python 3.12–3.14 Unicode jobs passed. That result does not qualify this
newer adoption source. Production runtime/source/key admission, remaining signed
work/cleanup/direct IO, GO/result/terminal/native publication, STATUS and physical/
release qualification remain open. The earlier destination-custody incident remains
unresolved; no live key installation, settings, permissions or host deployment changed.

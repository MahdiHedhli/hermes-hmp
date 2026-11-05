# Enrolled private service spine — bounded source acceptance

This joins real private socket IO, HBR1, lifecycle grammar, shared replay/registry
and actual reader resources. It is the first stage of the full external broker,
not a replacement for metadata/classic/blobatar/custom static image delivery.
No production CLI, service installation, character capability or route is added.
Independent source/model review accepts the29-case local slice. Kernel peer is
explicitly mocked in those tests; real separate-process qualification remains open.

## Fixed startup enrollment and socket ownership

`StartupEnrollment` is one immutable iid/listener/broker-boot scope plus exact
non-root gateway/service UID/PID and independently selected installation generation.
The installation generation concerns the broker's own code/interpreter/parser
closure. It is not a Hermes compatibility allowlist: later/unknown Hermes versions
retain the minimum-version/best-effort policy and actual API/security checks.
The processes must differ. Trusted startup supplies the same enrollment to both
sides only after qualifying code, runtime, manager and current generations. It is
context, not attestation. No HELLO, frame enrollment, mutable registration/reset,
PID lookup, fresh boot acceptance or peer-reported hash can qualify that startup.

`BrokerServiceSpine` adopts an already privately bound/listening native socket
and retained `BrokerEndpointOwner`/observation from that startup. It neither binds,
unlinks nor repairs stale endpoints. A failed constructor retains its partial
owner. Each accepted socket is retained before fallible authentication. The server
checks current endpoint and expected gateway kernel UID/PID before reading header
or body. Gateway-side channels require expected service identity and exact peer
pathname; server channels require the exact local pathname. No arbitrary URL,
credential forwarding, profile/header-derived peer identity or fallback exists.

Endpoint permission policy remains exact private ancestry/directory/socket policy.
Connected socket descriptor identity uses FD/device/inode/file type, not fstat
permission bits: Darwin clears read/write readiness mode bits on half-close.
That legitimate change does not change endpoint filesystem permission authority.
Observed descriptor/context drift remains sticky and prevents a replacement close.
Timeout/EOF/peer refusal can still dispose a known owned local socket once.
Closed state requires an original owner-minted local fact, native closed FD and
EBADF observation; a flag alone or restored identity cannot forge it. Exact
primitive/snapshot guards precede comparisons and post-native boundaries recheck
integrity, including the duplicate-close path.

## Framing, concurrency and deadlines

A pending holder is allocated and retained before native accept; even postaccept
channel-allocation failure leaves its socket reachable and unknown. An allocation
or retention failure before accept performs no native accept effect.
At most22 locally live/unknown connection owners (six active plus sixteen waiting)
are retained. A readiness-only future carries no accepted socket: native nonblocking
accept and retained connection insertion happen in the same task without an
intervening await. Readiness cancellation removes only the owned registration;
unknown registration remains retained debt. Known local socket close can retire
only that transport slot. Registry
capacity, replay and unknown operations persist independently. One event loop owns
all service calls; no foreign constructor/reaper or concurrent external registry
mutation is admitted. A single accept intent is allowed at a time; accepted
connections can progress independently under their original budgets.

The source-only `decode_scope_header` checks canonical header/body shape and fixed
iid/listener/boot before body allocation. Channel/operation are untrusted per-
connection correlation and pass through grammar and the one shared registry.
Existing full-binding decoder remains strict for subsequent frames. Header length
is checked after eight bytes and before reading the header; kind-specific body
length is checked before receiving body. This stage refuses RESULT transport and
caps bodies at8196 bytes. Transport prefix/header/body temporaries are bounded by
three times the9228-byte wire bound per connection, separately from existing
registry/reader budgets. Future RESULT integration must join its larger aggregate
budget, not silently reuse this bound.

Each recv/send uses only remaining absolute monotonic time, rechecking after awaits.
No slow-byte progress renews it. Pending Task.cancelling state is checked before
another accept, read/write progress return or reader start, including the inspected
Python3.11 wait_for completed-future cancellation behavior. Cleanup remains allowed
under its own retained owner after work cancellation. Deadlines are checked before
creating an IO coroutine so an expired call cannot leave an unawaited coroutine. Initial admission is bounded by two seconds;
validated input3 must retain its original earlier deadline. Grammar records send
intent before a possibly partial write. Any failed/partial write retires that
channel; there is no reconnect/replay retry. At most one read and one write may
progress concurrently; same-direction reentry refuses.

## Actual dispatch, cancellation and retained ownership

BEGIN validates input3 and reserves through the shared replay/capacity registry.
Queued work observes capacity without new launch/deadline; early received CANCEL
seals only a known never-launched owner. Otherwise the real resource binder starts,
retains input and emits READY. Concurrent cancellation is received under the
original budget. GO is always refused in this stage: peer authentication is not
native original authorization. No worker GO, RESULT or publication is permitted.

Cancellation, disconnect, expiry or shutdown invalidates grammar before awaiting
cleanup. The exact resource binder's frozen local cleanup deadline governs local
drain. Started records remain PENDING even after local drain; socket EOF never
becomes CLOSED or a global ACK. STATUS returns only CLOSED/PENDING/UNKNOWN from
existing retained registry state and never replays a result. Only an exact known
never-launched CLOSED can be globally ACKed under the existing grammar. New boot
or unknown operation stays UNKNOWN, never a fresh BEGIN/resumption.

`stop_local_sockets` cancels each owned accept/connection task once, lets its own
finally retain/drain ownership, and closes only known local listener/channels.
Its boolean concerns those sockets only. Registry, pending tasks and unknown
resources stay reachable; it is never service/child/native/remote closure.

## Gates still required for the full feature

- Independent source/security and actual separate-process socket/service fixtures;
  current local tests explicitly mock kernel peer identity.
- Externally qualified startup installation/service/code/boot/current generation;
  synthetic verifier and manager fixtures do not mint production admission.
- Exact remote operation owner and original native INITIAL/BEFORE/PRE_GO/PRE_EMIT,
  policy-thread join, output/work/source proof and larger RESULT budget.
- Started terminal binder joining actual local custody with qualified boot/recipe
  and audited no-spawn/no-transfer runtime; local drain alone is insufficient.
- Freeze cross-process cancellation cleanup timing: the existing bodyless CANCEL
  cannot convey an earlier gateway cleanup-start timestamp. This stage makes no
  global250ms or started-release claim. Preserve uncertainty rather than renewing
  or inventing an end-to-end cleanup budget; resolve before production transport.
- Restart/multi-operation shutdown, supported Linux/runtime qualification,
  authenticated routes, full rendering/cache/header/custom parity, signed devices.

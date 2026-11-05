# BI1 original cancellation budget and versioned framing

## Implemented boundary

`presentation_cancel_budget.py` defines a fixed 250 ms cancellation window and
one event-loop-confined minimum owner per operation. Values use exact integers
in the existing signed-63-bit monotonic domain. The work deadline reserves room
for the cleanup interval; overflow, coercion, wrong length, future inherited
starts and starts beyond the original work deadline refuse. Sampling tolerance
is zero. Backward samples and malformed adoption poison the owner.

Local EOF, timeout and revocation must share this owner. Every cause or duplicate
can only shorten its frozen end. A delayed local cause is capped at work end
plus 250 ms. A local window returned for transport carries the earliest retained
start/end, never a fresh allowance. An expired inherited interval has zero time
remaining. No resource completion or reservation release follows from arithmetic.

The closed frame codec accepts explicitly selected version 2. Its CANCEL body is
exactly 16 bytes: network-order unsigned 64-bit start and end. Semantic decoding
then requires `end = start + 250000000`, signed-domain bounds and the original
operation ceiling. Framing alone intentionally cannot validate clock, deadline,
authority or lifecycle. Every other control body remains empty. Version 1 stays
the default; a selected receiver refuses a different version without fallback.
The existing service/enrollment still selects v1 and therefore cannot accept v2.

## Required next integration (not implemented or qualified)

Before either transport end selects v2, trusted startup must independently
qualify the exact kernel-authenticated peer's native monotonic clock domain.
A wire hash/HELLO or same UID is not clock attestation. Linux CLOCK_MONOTONIC is
time-namespaced: retain the broker's actual namespace identity and match the
peer's actual time namespace; anchor the peer with pidfd before fixed procfs
reads and verify liveness afterward. Missing APIs/access or uncertain identity
refuse. Darwin requires the common native Mach clock and observed same boot
session. Boot/domain drift invalidates enrollment. No duration or wall-clock
fallback, namespace changes, signal or reaping probe is permitted.

Sources: [Python monotonic clock](https://docs.python.org/3.14/library/time.html#time.monotonic)
and [Linux time namespaces](https://man7.org/linux/man-pages/man7/time_namespaces.7.html).
These sources describe clocks, not qualification of this runtime.

Bind the qualified domain and explicit protocol selection to retained enrollment,
channel and original operation. Both local cleanup and received CANCEL must
adopt the same minimum before cleanup effects. A dedicated retained cleanup
owner must survive work-task cancellation without bypassing authority for GO or
result delivery. Disconnect/lost cancellation retains unknown debt; a later
broker-local deadline cannot certify the gateway's earlier cleanup bound.

Native observer, selected startup enrollment, both-end transport adoption,
async GO intent, typed started-terminal proof, result validation, credential
retirement, manager/runtime latency and physical rendering remain open. This
source slice changes no service, route, live host, app artifact or device.

## Ownership and test acceptance

Independent review accepted the bounded arithmetic/codec source with 384 focused
cases on Python 3.13. Every future caller must retain and seal this pure owner,
original work end, qualified clock and operation; private numeric fields and
caller-supplied samples are not runtime attestation. The service remains v1.

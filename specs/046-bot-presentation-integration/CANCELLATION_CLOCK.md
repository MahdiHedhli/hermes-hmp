# BI1 original cancellation budget and versioned framing

## Implemented boundary

`presentation_cancel_budget.py` defines a fixed 250 ms cancellation window and
one creating-thread-confined minimum owner per operation, with consistent
read-only policy-thread inspection. Values use exact integers
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
Explicit startup enrollment can select v2 framing with a retained native clock.
The [coupled transport source](INHERITED_CANCEL.md) joins a one-use gateway
cleanup sender to the broker receiver and private BEGIN/READY/GO/CANCEL dispatch.
Both ends use their original budgets and the receiver adopts only the earlier
cutoff. Existing service paths default to v1; publication/status/release remain closed.
Dedicated [private result validation](RESULT_TRANSPORT.md) shares original work ownership.

## Original owner binding (source only)

Parent reservation now retains one budget at the earliest original parent/job
ceiling, before native observation or policy work. The remote owner retains that
same object and seals its reference. Explicit parent cancellation retires the
original listener fence before sampling its existing clock and freezes the first
cause immediately; duplicate or late cancellation cannot renew it. Clock failure,
reentry or drift retains unknown debt and irreversibly refuses the budget.

Broker reservation likewise retains its budget before child/resource effects.
Managed resources must adopt exactly that owner and original deadline. Resource
abort/reentry and cleanup polls shorten or consume the same window, capped at the
original work end plus 250 ms. Both launch paths and capacity observation refuse
a caused/failed budget, including after foreign clock callbacks.

Each publication has an immutable named-tuple payload, private mint, increasing
generation and retained reference. Shape-compatible replacement, old-generation
rollback and in-place field changes cannot clear the first cause. A policy read
racing a publication refuses transiently without poisoning; malformed stable
state and foreign-thread writes irreversibly refuse. This protects the declared
local reference boundary, not arbitrary hostile Python-memory modification.

This local budget binding alone is not cross-process clock attestation. The
subsequent [retained task source](REMOTE_CLEANUP.md) joins selected-v2 work before
local socket/clock closure; stalled work retains debt. Coupled version2
cancellation is source-tested, not production-qualified. Parent native-policy
DRAIN still requires integration; no wire deadline or local close alone is authority.

## Transport premises and remaining qualification

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
adopt the same minimum before cleanup effects. The native observer now has a reviewed irreversible local-only cleanup-clock
mode after successful initialization; it does not authenticate new frames. A
dedicated retained async cleanup owner now survives caller cancellation in the
selected-v2 transport source without bypassing authority for GO or result delivery.
Inherited transport and runtime qualification remain separate. Disconnect/lost cancellation retains unknown debt; a later
broker-local deadline cannot certify the gateway's earlier cleanup bound.

The [native observer source](NATIVE_CLOCK.md) now exists separately; it does not
itself activate production transport. Remaining:
async GO intent, typed started-terminal proof, result validation, credential
retirement, manager/runtime latency and physical rendering remain open. This
source slice changes no service, route, live host, app artifact or device.

## Ownership and test acceptance

Independent review accepted the bounded arithmetic/codec source with 384 focused
cases on Python 3.13. Every future caller must retain and seal this pure owner,
original work end, qualified clock and operation; private numeric fields and
caller-supplied samples are not runtime attestation. The service remains v1.

# BI1 retained native common-clock observer

## Scope and premises

`presentation_clock.NativeClockOwner` observes the existing authenticated private
SocketChannel, not a caller-supplied clock ID. It sends nothing and cannot select
protocol v2, authorize work or release any native/registry debt. It retains exact
channel/enrollment/descriptor identity, process/effective UID/thread context,
selected CPython monotonic implementation, boot identity and Linux namespace FDs.
Constructor failure exposes the partial owner through ClockAcquisitionError.

Trusted installation and root/same-UID administrator, exclusive FD ownership,
no concurrent namespace or clock-provider changes, and the channel's audited
no-transfer/runtime premises remain required. This is not a Python-memory
sandbox. Snapshot checks do not prevent a privileged actor changing and restoring
a namespace between observations. No native syscall latency or hard realtime
bound is claimed. Actual runtime/manager/code admission remains separate.

## Native paths

Darwin requires the actual nonadjustable monotonic `mach_absolute_time()`
implementation and fixed bounded `sysctlbyname(kern.bootsessionuuid)` observation.
The connected AF_UNIX peer shares the local boot/Mach clock under these premises.
Missing or malformed native identity refuses; no wall-clock/duration fallback.

Linux requires selected 64-bit x86_64/aarch64 libc ABI and CPython's
`clock_gettime(CLOCK_MONOTONIC)`. The retained `/proc` root and fixed boot_id FD
must actually be procfs by native fstatfs. Namespace descriptors must be nsfs.
Following fixed kernel `self/ns/time` and authenticated peer PID `ns/time` links
is deliberate; `time_for_children` is never used. Actual `(dev, ino)` identities
must match, and later samples must still match both held descriptors and paths.
Boot reads are fixed-size canonical UUID reads; nothing accepts request paths.

SO_PEERPIDFD is acquired from the exact connected socket, retained before
further validation and required to be a noninheritable native pidfd. Polling
before/after fixed proc lookups rejects a dead original process. A numeric
pidfd_open(peer_pid) fallback is deliberately absent: old SO_PEERCRED can survive
original process exit and numeric PID reuse. The original socket's process
reference anchors the proc lookup. Unsupported kernel/API/permissions refuse.
No pidfd signal, wait/reap, namespace entry or process scan exists here.

Each work sample rechecks context/provider/channel/domain and nondecreasing exact
integer nanoseconds, then rechecks integrity after native boundaries. Refusal is
sticky, recursive sampling poisons, and a swallowed close/refusal cannot publish
a sample. Metadata shape/ref checks precede operations that could invoke foreign
comparison/iteration callbacks.

## Local descriptor retirement

Every acquisition has a retained record before its syscall. A returned descriptor
is retained before fstat/flags/origin checks. Native OSError-without-FD is distinct
from an uncertain interrupted acquisition or failed descriptor validation.

Cleanup records one close intent, verifies native EBADF after returned close and
retains uncertainty without retry. Closure of other FDs cannot erase ambiguous
ones. Local clock-FD retirement is not channel, peer-process, native credential,
policy-thread, work-budget or registry closure.

## Verification and remaining integration

Causal tests use explicit mocked Linux/kernel observations and real private local
channels; they are not Linux runtime qualification. An additional actual native
fixture uses one exact owned helper and private Unix socket with real kernel
peer identity and common-clock observation. It performs no BEGIN/GO, profile read,
manager action or v2 work. Darwin own-boot and private-channel checks pass locally;
Linux native cases must be assessed separately on their actual kernel/ABI.

Next, trusted startup must retain this exact owner and explicitly bind protocol
v2, original operation and the nonrenewing cleanup-budget owner at both transport
ends. No transport switch is enabled by this source. Async GO intent, typed
terminal proof, result validation, secret retirement and full character routes /
rendering / signed physical checks remain required.

## Primary contract references

- [Python monotonic implementation and process-common clock](https://docs.python.org/3.14/library/time.html#time.monotonic)
- [Linux active time namespaces](https://man7.org/linux/man-pages/man7/time_namespaces.7.html)
- [Linux v6.6 SO_PEERPIDFD implementation](https://github.com/torvalds/linux/blob/v6.6/net/core/sock.c)
- [Linux v6.6 socket option ABI](https://github.com/torvalds/linux/blob/v6.6/include/uapi/asm-generic/socket.h)
- [Linux v6.6 filesystem identities](https://github.com/torvalds/linux/blob/v6.6/include/uapi/linux/magic.h)
- [Linux v6.6 statfs layout](https://github.com/torvalds/linux/blob/v6.6/include/uapi/asm-generic/statfs.h)

Independent review accepts the repaired bounded observer source after 46 passing
cases and one Linux-native skip on Python 3.13. Native no-op-close, foreign
metadata and swallowed sampling-reentry findings are repaired with causal tests.
This does not certify startup admission or the full image feature.

## Fresh upstream alternative check

Read-only public source pin `36b29e812a2ca5edbae3172508a41f04efbe68be`
(November 5) still implements `profiles.get_asset` in
`tui_gateway/methods_profiles.py` with `is_file()` followed by unbounded
`read_bytes()` and base64 construction. This inspected Desktop/TUI method is not
proof of a bounded HMP presentation route or per-device profile authorization.
It does not replace the existing bounded-reader contract. No upstream source,
installed Hermes or private profile was changed or read in this check.

## Irreversible cleanup-only local clock

`cleanup_sample()` now requires the same owner's successful initial qualification
identity and exact immutable domain-value seals. It retires work before native
calls, keeps the original monotonic history and observes only the original local
clock/provider/boot/own namespace and retained FDs. It never consults a departed
peer or claims continued remote clock agreement. Work sampling stays refused;
this mode cannot send frames, read results, authorize GO or release a reservation.

Failure planes are prospective. Local context/provider/boot/own-namespace/FD,
backward-time, reentry and ambiguous exceptions permanently poison local time.
Only explicitly typed kernel peer exit or isolated peer namespace unavailability /
mismatch may refuse work while retaining local cleanup eligibility. A generic
SocketChannel refusal deliberately masks multiple causes and therefore poisons
local clock eligibility; it is never retrospectively declared peer-only. A
transport EOF can go directly to cleanup on the previously qualified owner,
without retrying the work sampler on a known failed connection.

The actual owned-helper test now retires work and freezes the existing
CancellationBudget before closing transport, observes the exact helper's exit,
then samples the original local clock and verifies that the first cleanup end is
unchanged. Independent convergence passes 62 cases with one Linux-native skip on
Python 3.13. These facts do not implement the retained async cleanup task, bind
its original native operation, switch transport to v2 or prove terminal drain.

## Selected channel lifecycle

The [explicit selected-protocol source](SELECTED_PROTOCOL.md) now retains a
NativeClockOwner before initializing a selected-v2 channel. Enrollment guards
include the ninth protocol field. Concrete clock sampling/closure boundaries
resist instance overrides; socket and clock-FD close facts remain separate.
v2 cancellation, status lifecycle, broker dispatch and native work are still
closed until the original-budget/cleanup integration is complete.

## Proc PID realm repair before selected-v2 publication

The [self-pidfd/fdinfo realm qualifier](PROC_PID_REALM.md) now runs before
numeric peer namespace paths. Actual procfs origin alone was insufficient for
a foreign PID-namespace proc mount. Two additional retained descriptors prove
the caller/proc realm without PID1 access, and native namespace type checks
require active time namespaces. Trusted unmodified proc layout remains explicit;
this does not defend against a privileged administrator replacing submounts.

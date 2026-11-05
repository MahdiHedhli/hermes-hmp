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

Each sample rechecks context/provider/channel/domain and nondecreasing exact
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

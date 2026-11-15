# BR4a kernel peer-identity observation — independently accepted source slice

This source slice observes a connected local stream's kernel peer UID/PID only.
It does not authenticate code, authorize a bot, prove peer liveness/child custody,
secure a socket path or activate the broker. BR4 endpoint/provenance work remains.
No PID returned here is authority to signal, wait for or inspect another process.

Require an actual socket.socket, AF_UNIX and SO_TYPE SOCK_STREAM, and expected
non-root service UID1..2^32-2. Optional independently captured expected peer PID
must be integer1..2^31-1, never bool. No request/header-supplied UID/PID is accepted
by a future caller. Observations are immutable uid/pid; no advisory groups or
arbitrary OS metadata leave the helper. Mismatch, closed/unconnected socket,
unsupported OS/option/schema or any OS error is unavailable with fixed content-free
failure; no network/TCP/credential fallback or UID0 default.

Linux: use Python's SO_PEERCRED at SOL_SOCKET, exact12-byte native-endian standard
layout iII (signed pid32, uid32, gid32). Missing constant refuses. Kernel values
must have valid UID/PID shape, then match the expected trusted startup values.

Darwin: this Python3.14.9 build exposes neither getpeereid nor LOCAL_PEER* constants.
The actual Xcode27 macOS SDK sys/un.h documents SOL_LOCAL0, LOCAL_PEERCRED1 and
LOCAL_PEERPID2; sys/ucred.h defines xucred version0 with uint32 version/uid,
short group count and16 advisory gid32 values (76-byte layout IIh2x16I).
This is marked __APPLE_API_UNSTABLE in that SDK: qualify the exact current ABI,
require version0 and group count1..16, and fail on unsupported options/shape/version.
Do not infer support from macOS version strings or guess another layout on failure.
Retrieve peer PID as exact4-byte native signed int. These are connection credential
snapshots, not proof that a process has not exited/execed/changed credentials.
Actual socketpair probe on the current macOS returns76-byte version0 credentials,
UID matching the current account and peer PID matching the creating process.
That is preliminary ABI evidence, not a cross-process endpoint qualification.

Plan/checklist:
- [x] Independent review of this narrow API/ABI/refusal contract.
- [x] Implement source-only helper with strict trusted arguments/closed decoders.
- [x] Actual temporary private Unix listener + separately launched synthetic client:
  compare observed PID to its retained Popen PID (not a client claim); UID matches
  current account; wrong UID/PID refuses. Bounded fixture timeout, exact own-child
  cleanup only, no Hermes home/keys/real socket or other user's account access.
- [x] Causal malformed Linux/Darwin byte/schema/type/range cases and closed/nonlocal
  socket refusal. Fixtures do not certify a platform not actually exercised.
- [x] Independent implementation review and mandatory scanner/lint checks.
- [ ] Remaining BR4: pathname ownership/symlink/race policy, held endpoint identity,
  peer code/runtime/service identity, shutdown/restart and bounded transport.

No deployment, new permission, service-manager install or broker activation occurs.

## Kernel and convergence evidence

Current Darwin returned ENOPROTOOPT42 for SO_ACCEPTCONN on an actual connected
Unix stream. The implementation explicitly chooses Linux-only SO_ACCEPTCONN;
it never attempts the known-unsupported query on Darwin or falls back after a
failed observation. AF_UNIX/SO_TYPE STREAM and successful getpeername/getSockname
are required on both; unconnected/listening sockets refuse. Descriptor number,
device/inode and socket mode must match before/after observation. These checks
detect observed replacement, not arbitrary same-UID descriptor tampering; caller
exclusive ownership remains mandatory.

Independent review found a missing Linux-API constant could escape as AttributeError.
Required integer API constants now normalize to the fixed unavailable error, with
causal absence/type and unsupported-platform tests. Independent final39 peer tests
pass, including a separately launched child's actual Darwin UID/PID versus its
retained Popen PID and wrong-identity refusals. Root peer/codec/skeleton368 tests
pass on Python3.11 and3.14.9 on this Mac; this is not an actual Linux kernel sample.
Ruff and mandatory closed-surface scanner pass. No native/host/device mutation or
service install occurred; all endpoints and children were bounded private fixtures.

# GT3-SOCKET contract — proposed unactivated POSIX exchange

Root implementation; independent source review accepted the scoped component.
The synthetic Linux results below do not qualify native integration.
No production caller, live native ticket, gateway start, phone grant or remote
endpoint is authorized by this component. Only synthetic private Unix peers are
used during development. This does not complete GT1 or full GT3.

A retained registry is constructed once by the future original adapter owner,
bound to its actual loop and lifetime, with explicit capacity at most16 exchanges.
It creates one-shot exchange owners for previously verified native endpoint DATA:
fixed socket path/profile/IID, never HTTP-selected values. One live/unsettled owner
per exact binding; all bindings share the same retained registry budget. Unknown
close/construction keeps that owner and binding registered. Replacing a binding
uses the existing budget; making a fresh registry is not reconciliation proof.
The actual adapter must retain this registry through replacement/shutdown.

The component does no path discovery or filesystem permission attestation.
Original native path/PID/listener-generation and current HMP authority remain
caller prerequisites. Kernel same-user peer identity and echoed bindings are not
by themselves proof of the original native process. Unsupported peer-credential
primitives refuse; no path-only authentication fallback is allowed.

Each owner is one-shot even after success/failure. Retirement before start prevents
an attempt. At entry it retains the actual exchange task and completion future;
socket-construction intent is recorded before the constructor and the actual
socket is retained before connect or any await. A missing constructor result is
unknown debt, not a fresh slot. Mark send/mint uncertainty before the first send.

Use non-blocking loop.sock_connect/sendall/recv under one original absolute loop
monotonic deadline bound by prepare before caller queueing. exchange uses that
stored value; an explicitly supplied different deadline is refused before socket
construction. There is no public deadline reset. The explicit budget ceiling
is at most30 seconds; no phase, retry or dequeue renews it. Deadline expiration
fences output and does not prove a stalled event loop/kernel operation stopped.
No helper thread or independently scheduled I/O child is created by the exchange.

Verify actual kernel peer UID BEFORE send: Linux SO_PEERCRED or Darwin
getpeereid, matching the process OS UID. The fixed request/reply uses the existing
profile-scoped restart-refusal codec. Read at most65,536 body bytes plus LF,
with bounded chunks and one finite response buffer. Stop after the complete line;
future peer bytes are not parsed or reused. This is not the large group/media RPC
transport. Account simultaneous request/buffer/copy/decoded input separately;
logical input bounds do not prove exact Python heap/RSS or the full app envelope.

Retirement is synchronous/out-of-band and immediately fences output at subsequent
checks, even with full capacity. It does not silently claim outstanding I/O ended.
Final publication requires known socket close and another deadline/current check.
Close is attempted once; unknown closure keeps the original object and debt and
is never retried using a possibly reused descriptor number. Clearing known I/O
never claims an unobserved server-minted credential was revoked. No automatic
mint/replay, gateway start or policy-dropping compatibility retry exists.

A private completion future records only this scoped exchange cleanup boundary,
not parent HTTP-task termination or all Python references being retired. Registry
drain retires, then shields/observes the original completion futures. Self-drain
from an exact active exchange task is refused. Observer cancellation cannot
cancel those futures; a canceled future is not settlement. A known failed close
makes drain false and retains debt, rather than a fabricated clean shutdown.
Actual adapter/Store closure must depend on these results before activation.

Snapshots and failures contain fixed phases/reasons and close/send uncertainty
flags only, not endpoints, raw errors, tickets or local identities. Token repr
hygiene is not secure erasure. Real native/WebSocket admission and HMP room/history/
bot/device grants, complete RPC/media shapes and signed-device/release tests stay
separate. Successful synthetic peer I/O is not a native or deployed-host pass.


Independent source review identified a renewal gap in the first unactivated draft:
exchange accepted a fresh now+budget value after preparation/queue wait. The
corrected interface binds the absolute deadline at prepare and tests held-queue
expiry plus attempted renewal before any socket construction. Earlier passing
cases are preserved as draft evidence, not retroactive proof of the correction.


Linux credential decoding is selected only on actual Linux and reads unsigned32
fields matching kernel include/linux/socket.h struct ucred (pinned v6.12 source).
Darwin uses getpeereid; other POSIX layouts do not get a Linux-layout fallback.
Four high/low UID ABI cases are pure byte simulations, not platform spoofing or
runtime Linux qualification. Real Linux SO_PEERCRED still requires the separate
Linux job. Shared OS UID is not original native-process identity.


## Scoped implementation evidence

The unactivated source passes205 combined cases on actual Darwinarm64 with
CPython3.11.15:67 ledger,85 codec and53 socket cases. The socket suite includes
real private Unix peers/getpeereid plus explicitly simulated constructor/close/
registry/future faults and pure Linux unsigned-UID bytes. Removing bound-deadline,
peer-UID, close-uncertainty, observer-shield and final-publication guards in
disposable copies causes the intended1/1/1/1/2 failures with unchanged source.
These failures are causal checks, not passing runtime outcomes. No upstream core,
native control socket, real credential, paired phone, provider or user message is
used. Existing200/201 draft results remain dated evidence, not proof of final code.

A separate push-only Linux matrix is prepared for CPython3.11 and3.14. It uses
read-only repository permissions, pinned actions/patched uv0.13.5, frozen dependency
lock with project installation/source builds disabled and no cache. It preserves
all existing CI gates. The helper requires actual Linux/SO_PEERCRED/CPython minor,
source readback and exact67/85/53 distinct unskipped passing cases including the
actual kernel-positive case. Duplicate JUnit identities, skips and missing kernel
cases are refused by pure DATA checks; helper startup itself refuses Darwin.
Only fixed before/after metadata and synthetic JUnit XML are uploaded for2days.
The dated preparation above is superseded by the verified run below.

The actual future adapter must retain the registry across listener replacement;
this component does not enforce another Python caller's lifetime. Its endpoint
DATA/kernel UID is not native PID/generation or HMP authorization. No full GT1/GT3,
Windows equivalent, native integration, physical-device or release pass is claimed.

## Verified synthetic Linux socket checkpoint — November 16, 2026

[Run43845881095](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/43845881095),
exact source `2f3bb17345b318e1a9a4f39aea187be76d4834ca`, passed on actual Linux
x86_64 with CPython3.11.17 and3.14.9. Each matrix entry passed205 distinct cases:
67 ledger,85 codec and53 socket, with no failures/errors/skips and an actual
SO_PEERCRED peer check. Artifact archive digests, JUnit digests and all six source
hashes were independently read back locally; before/after source hashes agree.
This qualifies synthetic components only. The native group adapter, original
native-process binding, phone group permissions, mobile group UI and physical/
release acceptance remain unfinished. No real ticket, host restart or grant was used.
The earlier run43845005376 failed workflow validation before any job started;
its job-level runner-context error was corrected without changing component source.

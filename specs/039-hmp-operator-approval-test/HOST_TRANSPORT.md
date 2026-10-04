# AT1-T003 — Private local operator connection

Status: source authoring under the accepted caller-v4 contract. No current CLI,
adapter or server registers this endpoint, and no production handler exists.
`hermes hmp approval-test begin` remains a proposed, unavailable command.

This implements a necessary caller connection rather than a phone permission
shortcut. The endpoint authenticates the same local OS user through Linux
`SO_PEERCRED` or macOS libc `getpeereid`. Unsupported platforms fail closed.
The existing private listener directory must already belong to that user and
have mode0700 or stricter; no directory is created or broadened. A pre-existing
sidecar prevents startup. Socket teardown checks captured parent/socket inode,
device, UID and type, and leaves a replacement untouched. Same-UID hostile
processes are outside the existing operator trust boundary; a pathname or
generation nonce alone is not authentication.

The request frame and required write-half-close share a two-second read budget.
The strict DATA codec remains unchanged. Four accepted connections and one
held begin lease are allowed, with no unbounded thread/task queue. Each response
write is capped at two seconds. Only an actually failed write requests owner
cancellation; expected request EOF or a vanished idle client is not settlement.
The final response is withheld until the handler lease returns. Owned teardown
stops admission, waits for owner shutdown and joins connections before unlink;
a cancelled observer does not cancel cleanup. Held cleanup may keep the socket
generation unavailable indefinitely, rather than claiming success or killing
native work. Every response lease is explicitly retained and closed/joined even
when encoding, response ordering or failed-write notification raises. The owned
join survives cancellation of its connection observer. An unknown or failed
finalizer retires the generation, retains its connection/begin capacity debt and
prevents successful teardown/unlink. A returned or already-exhausted generator
cannot erase a previously observed finalizer failure.

The client checks private path/ownership and socket identity before and after
connect, authenticates the peer before sending selectors, half-closes only for
framing and enforces reply order, operation ID and bounded frame allocation.
It verifies final EOF before exposing a final response. It never retries or
interprets closing its iterator as cancellation. A begun completion can wait
for actual cleanup indefinitely; once a frame starts, its remainder has a
two-second cap.

`HostHandler` is a future trusted listener-owned port. It is not a production
authority object and must not be instantiated as a bypass. Its responses method
must be an async-generator function whose finally awaits actual owner cleanup;
generic async iterators without this explicit close port are refused. This type
check is lifecycle shape enforcement, not proof of native cleanup or authority.
Before integration,
the reviewed bridge must prove ACTIVE device/family, approval-owner and bot
grants, current generation/member/API/session association before and after
awaits; own the private native waiter, one-row mapping and cleanup; and supply
only the fixed reviewed response lifecycle. The transport cannot prove those
facts from a returned value. The CLI must still prove current private record
generation, TTY/session guards and supported listener lifecycle. Separate
typed authenticated phone projection/answer/cancel and native/physical checks
remain unfinished. No genuine prompt is inserted, no provider/tool/model is
called, and no grant or permission is changed by this source prerequisite.

Definitions cover kernel UID handling, path/mode/ownership/inode safety,
stale generations and malformed/oversized/trailing/slow/EOF requests, four
connections/one begin, held cleanup, cancellation of close observers, observed
write failure, exceptional response/finalizer cleanup, cancelled connection
observers, client authentication before transmission, and final framing.
Local socket tests use only short0700 temporary directories and memory-event
fake handlers. Linux mock credentials are not actual Linux kernel proof;
current-platform socket checks, native card checks and phone/release checks
must be reported separately. Definitions are not executed or passed evidence.

Source must undergo independent review before root admits these isolated tests.
No current gateway deployment, live host socket, phone bearer/card, push event,
report submission or release follows from this task.

Primary credential contracts: [Apple getpeereid](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html)
returns the peer's effective credentials at connection/listen time, and
[Linux unix(7)](https://man7.org/linux/man-pages/man7/unix.7.html) specifies
SO_PEERCRED and pathname socket limits. Filesystem mode is an additional guard;
neither platform's socket mode is substituted for kernel identity.

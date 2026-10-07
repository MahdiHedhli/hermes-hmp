# AT1-T003 — Private local operator connection

Status: private listener/routes source proposal on clean union9535, with the separately
accepted authority/service and CLI components as exact prerequisites. Definitions are
not execution admission, current gateway deployment or native/device qualification.

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

## Accepted profile-scoped listener integration (source proposal)

This source follows the exact accepted profile-scoped amendment a66f38c3 with independent
review7483e6e9. It supersedes the attempted combined AP3 ordering in historical listener
V1/V2 and unaccepted V3 research. No combined authority/freshness guarantee is fabricated.

Activation follows successful creation of this listener's private same-nonce record,
using current iid and actual PID. One attempted optional activation is allowed; no new
directory/mode, fallback transport, retry or replacement service escapes an occupied owner.
The actual owning adapter and root-plugin identities are captured alongside existing
closed modules/native bindings. Replacement followed by restoration cannot revive AT1.

Shutdown fences immediately and shields its retained owner through actual endpoint,
service, connection, native cleanup and authority-worker joins. The adapter's record,
PromptStore and Store remain until proven join. Unknown cleanup retains dependencies.
No observer cancellation is represented as settlement.

GET /hmp/v1/bots/{p}/approval-tests/current calls actual full phone_card(request, profile=p)
and serializes its fixed version1/null-or-card DTO after the final authority await, with
synchronous identity/bearer/service checks and no later suspension. The existing standalone
GET and independent answer/cancel routes remain. Standalone DATA cannot mint profile UI
eligibility. There is no public HTTP begin or permission fallback. Exact path routing,
foreign/stale opacity, strict query/body/header/UTF8/duplicate/unknown validation, exact
once/deny integer1 control schemas,256-byte body and1024-byte no-store response are retained.
Length text has the existing8192-byte header bound;0007 declares7 bytes, and declared or
observed body above256 still has its own413 result.

Ordinary AP3/AP4 are restored exactly to the current styled baseline source. Synthetic
read/failure never delays or modifies their prompt/Desktop decisions, and no extension is
emitted. The same common mobile screen uses independent scoped reads; its revised client
binding and debt/older-host handling require separate source and actual test qualification.
Legacy DATA decoder tolerance is not control authority.

The fixed card exposes only test_id32hex, title Synthetic approval test, message No action
will run., ordered once/deny choices. HTTP202 means typed control intent accepted only.
No native settlement/cleanup, provider/model/tool/shell/message action, prompt insertion,
push, grant/mode or native core change is inferred or introduced.

Prior68 listener/control/authority/ordinary test causes are rebound to this amendment.
Additional source definitions cover exact scoped routing and full service native rereads,
changes during authority awaits, final identity failure/refusal, unknown older-host route
compatibility, independent ordinary and synthetic progress, held open-Bot Desktop reads,
and query/body attempts to replace a foreign path profile. Expected counts/names are not
actual collection/pass. The exact ordinary AP3/AP4 body and original assertion files are
pinned unchanged. Root alone reviews/applies/executes the complete joined source; no SDK,
parser/import/linter/tests/live listener/native/provider/device execution was done by author.

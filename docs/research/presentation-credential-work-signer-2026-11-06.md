# Original native work-task BEGIN signature producer

The source adds a fixed `NativePhaseWorkOwner` on the original retained cleanup
owner. Construction runs on the original handshake/caller task after both task
allocations exist and before the original start barrier opens. A failed factory
uses the existing closed barriers, retained tasks and UNKNOWN debt; it does not
create a new task or unlock work. Concrete cleanup guards run again after the
handshake clock boundary before Future dispatch or allocation indexing.

Only allocation 1 may prepare BEGIN. The original caller, a foreign receiver,
cleanup allocation or another task is not a signer. The producer consumes the
SAME previously reserved native `_BeginWriteIntent`, without a second native
send admission. It takes no statement, frame, digest, profile, key or replacement
intent argument. A first-attempt latch precedes native callbacks and crypto.

The statement derives from the exact retained input3 packet, original native
binding and original four signed handshake records. The transcript is separately
reverified against pinned keys during construction and its primitive values are
sealed. The resulting phase record commits the entire original HBR1-v2 BEGIN
frame, input and scope hashes, exact original deadline, boots/channel/transcript,
role, generation and sequence zero. Matching caller data is not authority.

Native policy/thread/closed-input ownership, live listener/lease/epoch, original
work allocation/coroutine, caller/work cancellation, current role key custody,
clock and exact socket identity are checked before signing and after crypto.
Frame/scope/canonical preparation precedes a fresh pre-key-use guard. A retirement
or metadata change during preparation/signing withholds the returned record and
keeps the first attempt consumed. Signature data is not actual transfer evidence.

Root's final affected regression passed **940 tests, one skipped**, in 27.56
seconds. Configured repository-wide Ruff passed. The focused 20-case native-input
module covers an independently verified valid signature and exact full frame,
original caller refusal, allocation-1 operation, duplicate refusal, constructor
foreign-allocation substitution after the clock boundary, foreign receiver getters,
pre-sign key/transcript drift and post-sign key/listener/policy retirement. It
also retains the original no-IO reservation/native-input causals. Tests use real
local policy-thread/job/socket ownership with synthetic native authorization and
modeled peer/clock facts. No host/provider/device activity occurred.

The unsigned phase-transport gate remains CLOSED. No application bytes, GO,
child, complete-write fact, result, terminal receipt or native publication follows
from this producer. READY/GO/RESULT signing, cleanup actor credentials,
broker-side unadopted BEGIN validation, all direct writer paths, STATUS,
operator-selected production startup/capacity/rotation and physical/release
qualification remain open. Historical destination-custody risk is not resolved
by this source change. The prior CI 702 qualifies only earlier source 6c31d43;
it does not qualify this signer.

Independent read-only review accepted the corrected source/test slice, including
final-constructor tuple/identity fencing and its zero-callback causal. No reviewer
tests or live actions ran. This acceptance does not qualify complete transport.

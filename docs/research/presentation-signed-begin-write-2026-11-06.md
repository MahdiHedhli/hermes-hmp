# Original native work-task signed BEGIN write — November 6, 2026

`NativeBeginWriter` sends only the fixed original signed BEGIN record plus its
original HBR1/input3 frame. There is no production caller. The existing
`RemoteOperationOwner._begin_ready_exchange` and generic credential transport
refusals remain unchanged. Tests intercept the still-closed legacy send seam only
to qualify this helper on the actual original native cleanup owner's index-1 work
task, after normal PRE_GO/BEGIN_INTENT and its already reserved native send intent.
This is not a READY/GO/resource/publication or full character-delivery pass.

## Original ownership and sticky boundaries

Factory admission checks original work task/allocation/coroutine/slot, loop,
process/thread, original producer/remote/cleanup and already signed record/intent
without calling native guards. It retains a partial typed writer in both producer
and channel before native callbacks. It neither reserves nor authorizes BEGIN
send again. The producer's exception for channel writing derives only from this
exact retained original writer and active claim, never a caller permission flag.

`write_begin()` uses callback-free metadata and actor admission, then consumes its
one write attempt before callback-bearing native guards. The signed transcript,
original native input digest/scope, role signature and committed frame are
independently checked. Native authority/key/deadline/task/socket guards surround
every syscall/await. Concrete native descriptor/nonblocking/timeout checks follow
peer/clock callbacks. Actual positive progress over BOTH original signed record
and HBR1 frame is captured immediately from the held pre-call offset. Known zero
refuses without retry; uncertain exceptions/results or drift retain native write
debt. Only exact native EAGAIN/EWOULDBLOCK with unchanged held intent/cursor can
wait through owned writability under the original deadline. Unknown registration
or retirement cannot clear the write claim.

After all original bytes and current guards, one sticky completion-authorization
attempt invokes the existing native `_authorize_send_completion` with the original
packet object/frame/binding/deadline. A final guard follows that boundary. Only
then are the existing `_BeginWriteFact` on the SAME reserved intent and a private
full-signed-wire completion fact published. Native write evidence does not mean
peer receipt, child input read, execution acknowledgement, native release or GO.
Generic READY/GO/CANCEL/result paths remain closed even with a completed BEGIN
fact. Both original channel/remote handshake aliases remain joined in historical
writer checks; clearing mutable channel markers cannot revive unsigned fallback.

Input3's four-byte envelope is included: packet maximum INPUT_LIMIT+4 = 8,196;
total signed wire ceiling 2,048+8+1,024+INPUT_LIMIT+4 = 11,276. The maximum valid
input test uses existing parser-accepted JSON whitespace inside the input3
producer before the original native packet binding. It does not substitute the
packet after binding. A constrained test socket forces real kernel backpressure
while an independent raw peer drain observes actual complete wire bytes.

Historical writer retirement requires original work task joined and known settled
local IO. It does not require live signing keys, but exact original static joins
remain mandatory. It grants no native write-quiescence, resource, remote cleanup
or publication credit. Ambiguous IO remains retained. A separate negative fixture
proves protocol close refuses, then disposes ONLY its own synthetic socket/clock
FDs without restoring fields or claiming protocol/native release.

## Review and verification

Independent read-only source/test review accepted the final writer, boundary
latches, envelope correction, completion fact and signed-channel provenance fence.
The reviewer ran no tests/native actions. Root's native-binding module passed
32 cases, including 12 new transport cases. They cover actual signed wire,
partial sends, EAGAIN, real maximum input/kernel backpressure, known zero,
unknown syscall/registration, offset drift, post-send key retirement, first native
guard failure/restoration without retry, one completion-authorization refusal,
wrong caller/work task and old unsigned-phase refusal. Existing signing-only
production-path tests retain their original zero-application-byte behavior.

During development, the initial test had a missing import; the first unknown-send
fixture incorrectly required protocol close even after proving unknown debt. A
separate explicit test-owned teardown corrected that assertion without relaxing
source protections. The first max-input attempt had no concurrent raw peer drain
and correctly expired under actual backpressure; the fixture now drains under
the original deadline. No deadline, native intent or authority guard was weakened.
Initial source review also corrected pre-native attempt latching and the omitted
four-byte envelope before acceptance. Final affected regression: **1,408 passed,
one skipped**, 60.31 seconds; configured repository-wide Ruff passed. New-source
CI is pending. Exact CI/source binding is in the current feature checkpoint and
private receipt.

Native authorization/peer/clock qualification remains synthetic; policy thread,
shared native slot model, tasks, private sockets and syscall observations are
actual test behavior. No live host/device/settings, role-key installation,
permissions/providers or mobile build changed. Production resource admission,
signed READY reception and later signed phases, worker GO relay, runtime/startup,
native publication, STATUS and physical/release qualification remain incomplete.
The earlier native-destination incident remains separate and unresolved.

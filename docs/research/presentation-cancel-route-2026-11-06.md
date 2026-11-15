# Internal signed CANCEL routing and broker correlation — November 6, 2026

The exact retained credential branch of `SocketChannel.send_cancel` now composes
the fixed signer and writer on the original cleanup allocation, leaving ordinary
unsigned behavior and generic credential work gates unchanged. Pure actor/channel
joins precede the route. The partial signer is retained before the first native
check, consumes one preparation, and preserves its original frame/window/sequence.
Full write proof/current original budget precede local-send return. Exceptions
remain conservative unknown/refused without retry or unsigned fallback.

Known no-IO role/signing refusal is distinct from uncertain native send/readiness.
The automatic path now attempts solely-local socket/clock retirement on the
original cleanup actor and frozen budget. It reseals the failed signer/no raw/no
writer proof after native boundaries; channel close independently proves retained
IO retirement. Remote UNKNOWN and the original exception remain unchanged.
Deadline expiry, cancelling cleanup and unknown-read causals earn no close credit.
Unknown IO cannot borrow this path to settle protocol custody.

Five direct route cases cover before GO, after GO, retired-key no-send, wrong-task
no attempt/budget mutation, and initial native failure. The latter retains its
failed signer; restoring the synthetic native condition/private failed flag cannot
reacquire or perform another preparation/sign/send. No real state restoration or
permission change occurs in production.

Two further cases use actual private sockets/original accept/service allocations,
real handshake and BEGIN adoption, disposable child/input staging and the real
signed READY producer/writer. Normal gateway READY/GO/CANCEL reaches the actual
broker control cursor and signed consumer. The retained minted receipt has exact
seq1/seq2/window/end matching gateway native preparation. Worker GO is never
attempted and registry PENDING is not relabeled as CLOSED/ACK. Native peers/clocks/
authority are synthetic; this is not production enrollment or physical coverage.
Own disposable streams/waits and local sockets are disposed independently, with
service/resource retirement observations kept separate from remote settlement.

Initial correlation queried a generic receipt API after successful signed consumer
adoption; that correctly refused. Assertions now inspect the signed consumer's
original receipt/consume completion without relaxing the old guard. Initial full
regression had 17 failures/1,498 passes/one skip/two teardown errors from fixtures
assuming CANCEL was still closed, a wrong-task error type, or no prior legitimate
closure. Representative failures were reproduced. Updated fixtures permit the
new dedicated route, parse actual automatic signed CANCEL after GO, and preserve
historical close facts while rejecting new validation after metadata drift.

Independent read-only review accepted the pre-native retention repair and bounded
routing/correlation scope. Focused updated tests: 134 passed. Final full affected
regression: **1,516 passed, one skipped**, 75.77 seconds; lint and whitespace
checks passed at the routing checkpoint. Follow-up local-refusal qualification:
100 focused tests passed; independent read-only review accepted the repeated
no-IO eligibility fence. Production startup, pre-READY cancellation,
signed results/terminal custody, worker relay and
physical/release qualification remain open. No host/settings/device/build changed.

Qualification limit: the follow-up full affected run finished with 1,518 passed,
one skipped and one failure in the pre-existing broker service wrong-spine case
(`signed_control_native_service_wrong_spine-2`), refusing at `_creator_current`
after native cleanup guard. Its exact isolated rerun passed (one test, 0.73s).
The timing/cause remains unproven; this is not a full-suite pass. A formatting
edit also initially caused a collection indentation error; it was corrected
before that completed full run. Configured lint now passes.

Follow-up investigation: 14 service cases passed with duplicate collection, and
all 130 adoption cases passed after adding test-only exception notes. The notes
preserve the original service exception and report the actual original controller
Task outcome and retained notice/failure/debt flags if it recurs. They neither
repair state nor extend deadlines. Failure remains unresolved, not reclassified.

Subsequent focused run reproduced an analogous wrong-task case refusal: six
passed, one failed. The original controller had failed with FrameError before
notice completion, with unknown-IO false. This is stronger localization, not a
resolved cause or timeout diagnosis. A later 14-case repeated run passed. Test
notes retain only exception class and bounded source-function/line locations,
not arbitrary exception messages or payloads.

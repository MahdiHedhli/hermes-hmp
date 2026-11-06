# Internal signed CANCEL routing and broker correlation — November 6, 2026

The exact retained credential branch of `SocketChannel.send_cancel` now composes
the fixed signer and writer on the original cleanup allocation, leaving ordinary
unsigned behavior and generic credential work gates unchanged. Pure actor/channel
joins precede the route. The partial signer is retained before the first native
check, consumes one preparation, and preserves its original frame/window/sequence.
Full write proof/current original budget precede local-send return. Exceptions
remain conservative unknown/refused without retry or unsigned fallback.

Known no-IO role/signing refusal is distinct from uncertain native send/readiness.
The automatic path currently retains local-cleanup debt in that known case; it
does not claim descriptor/clock close happened merely because an independent
role-neutral close helper is available. Unknown IO cannot borrow that helper to
settle protocol custody. Completing this known-refusal cleanup is still open.

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
checks passed. Production startup, pre-READY cancellation, known-refusal
local cleanup completion, signed results/terminal custody, worker relay and
physical/release qualification remain open. No host/settings/device/build changed.

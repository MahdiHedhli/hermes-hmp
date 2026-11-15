# Actual parked CANCEL expiry causal — November 6, 2026

The existing broker failures were retained, not reclassified as passing tests.
One guard failure occurred at the parked Future's stop/cancellation lifecycle
check. A controlled actual-peer test now distinguishes expected expiry behavior
from a new permission or success path. No production source changed.

The original gateway sends a real signed CANCEL. The original broker controller
authenticates and adopts it, publishes its actual notice and parks under its
ORIGINAL250ms timeout. The original service fixture waits that actual task to
terminate instead of consuming immediately; the outer bound is only the existing
original work ceiling. No replacement clock sample, budget, timeout or fake
completed record is used. Native Timeout.expired is observed after completion.
The task is done/noncancelled with the existing wrapped cancellation-adoption
FrameError, the park Future is cancelled and there is no authorized stop intent.
The original frozen cleanup end remains unchanged after failure handling.

Late original-service consumption then refuses. The actual CancelReceipt remains
retained from authentication/adoption, but consume_complete remainsFalse and
consume_failed isTrue. No result token or job credit release follows. A valid
retained receipt is DATA, not perpetual current consumption/native closure.
Unknown broker transport can refuse protocol close; the fixture disposes only
its own FD/clock after refusal without repairing flags or minting release facts.

Independent read-only review accepted the actual expiry causal, unchanged end and
separation of retained receipt from failed consumption and unreleased credit.
Reviewer performed no execution or native actions. Root's final exact new case
passed1 in1.56s. A nearby matrix with all14 notice cases, actual partial-body notice,
the two earlier failing cases and this expiry case passed18 in7.27s. Runs overlap;
counts are not added. Lint/whitespace pass. No new broad/full or CI pass is claimed.

Two initial fixture assumptions were wrong and remain preserved: it expected bare
TimeoutError rather than the source's wrapped CANCEL_ADOPTION_REFUSED, then it
expected the producer receipt to be erased rather than retained. Both corrected
assertions follow actual source semantics; no guard, deadline, state, receipt or
permission was relaxed to pass. Failed logs remain private evidence.

This controlled expiry explains one legitimate refusal PATTERN, not the cause of
`go_current_wrong_actor-2` or `go_relay_result_sign_write_body_adopt_notice_ambiguous-2`
in the prior broader runs. Their exact state notes have not yet been observed on
a reproduced failure, and the earlier causes remain unproven. Do not mark those
issues resolved from focused passing reruns. Current signed cleanup consumer,
concurrent signing, same-reader drain/terminal/ACK and production/physical image
qualification remain open. No build/deploy/device/config/grant/provider changed.
The native sender-destination incident also remains unresolved.

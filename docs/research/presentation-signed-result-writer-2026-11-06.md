# Original-service signed RESULT writer — November 6, 2026

## Actual source boundary

`presentation_credential_result_write.py` retains one writer on the original
producer and channel before its first native initialization check. Wrong-task
admission does not consume that slot; admitted failure is sticky. The original
service Task streams the signed HBA1 record, canonical RESULT header and immutable
native payload slices no larger than 65,536 bytes, without concatenating a full
frame. RESULT grammar intent precedes I/O. The generic credential work gate and
unsigned RESULT path remain closed.

A fixed historical READY-to-RESULT write-slot handoff describes only this exact
writer's active flag. Before each native socket send, the writer rechecks current
producer authority, peer/socket identity and nonblocking/noninheritable descriptor,
then ends on a callback-free original role/custody/actor/cause seal. Actual returned
counts are retained before mutable-alias validation. Exact EAGAIN is zero-byte
readiness, not a retry of unknown I/O; zero, short-then-zero, uncertain sends and
post-write drift cannot mint full transfer or start another send attempt.

Original cancellation first withdraws producer/writer payload aliases before
cleanup clock sampling. After freezing the original budget, the original controller
may cancel only the exact active, not-yet-failed original service Task once.
Cancellation during selector wait retires that original readiness allocation.
Unknown selector/write debt remains explicit. No new receive task, replacement
sender, renewed deadline, ACK or resource settlement is created.

Known readiness settlement and final currentness precede the metadata-only local
transfer fact. Successful cleanup then performs only pure payload withdrawal and
write-slot release: no native callback remains after fact publication. Failure
never returns a fact. Payload references are withdrawn in both producer and
writer on terminal attempt; immutable bytes are not claimed securely erased.
The fact's scope retains owners and bounded metadata, not a direct payload field.

## Verification and preserved failures

Thirteen focused private-peer cases passed in 7.70 seconds before final added
outcome assertions. They use real private socket sends and disposable synthetic
native workers, with modeled peer/clock authority. Cases cover complete exact
wire/count, wrong task, final descriptor-tail key/control/foreign phase changes
(zero sends and no foreign equality), actual seven-byte partial and unknown writes,
post-write alias drift/count preservation, sticky initial native-check refusal,
readiness refusal/returning key retirement, and actual EAGAIN followed by original
controller cancellation. Final affected exact-source regression: 1,599 passed, one skipped in 101.50
seconds; lint/whitespace pass. Independent read-only review accepted the repairs
and final channel type/truthiness guard; no live provider/user content or device is exercised.

Review found and repaired final-descriptor authority fencing, fact-before-settlement
and pre-retention native-check gaps. An intermediate seven-case run had six passed
and one failure: a failed writer remaining active caused a later controller abort
to cancel the service during fixture cleanup. Cancellation eligibility now excludes
already failed sends; the repaired seven-case run passed in 4.40 seconds, followed
by the thirteen-case run above. Fixture formatting/lint errors were corrected
before execution, without changing protocol deadlines. Historical independent
broker wrong-spine/controller intermittency remains unresolved.

## Remaining complete-delivery work

This is a directly tested component, not production dispatch. Integrate original
service dispatch and gateway signed RESULT parsing on its sole original work
cursor, retain cancellation/discard ownership, complete signed terminal/ACK and
installed-runtime/native publication gates. No local transfer fact proves remote
receipt, native release, execution acceptance or HTTP publication. Physical mobile
and release qualification remain separate; no host/build/device/config/grant/key
installation changed.

The prior broader run passed 1,598/one skipped in 102.34 seconds before the final
foreign-channel guard/test. The final run above includes that delta. The guard
checks exact channel type before any new handoff attribute access and uses exact
`is True` rather than foreign truthiness. No historical failure is reclassified.

# Original gateway signed RESULT envelope — November 6, 2026

## Implemented cursor boundary

`presentation_credential_result_read.py` adds a distinct retained
`NativeResultEnvelopeReceiver` after the actual completed original native GO_SENT
write. The partial owner is attached to the original GO writer/channel before its
first native guard. It does not replace `RemoteResultOwner`, claim its closed
native candidate slots, open generic credential work or add production dispatch.
The factory admits only the original retained work Task and current native GO
writer; wrong-task calls leave the original owner unpoisoned, while admitted
failure is sticky and cannot acquire another receiver.

The same original Task reads at most 2,048 bytes of HBA1 authentication and at
most 1,032 bytes of outer header. Prefix sizes are checked before the next read.
It verifies the original pinned broker/gateway keys, native transcript/input/scope,
generation/operation/channel, RESULT phase/direction/sequence1, and the committed
selected-v2 bounded RESULT header. This authenticates metadata/header only.
It deliberately does not read or hash image body, finish result2, populate native
result slots, advance native phase or certify a complete result.

Actual read counts and pending bytes are retained before mutable aliases are
validated. Each native descriptor tail ends on the reviewed fixed GO_SENT
custody/role/work-actor/cause seal. An exact reciprocal historical READY-to-RESULT
read-claim description permits only this fixed owner's active flag; it grants no
current work authority. It avoids clearing the read flag to borrow idle GO guards.

Actual EAGAIN waits retain the original selector allocation and deadline. Local
cancellation retirement requires the exact minted readiness receipt, original
scope/future/end/binding/registration and original Task's cancellation state.
After wipe, the historical local retirement fact carries counts, not cursor bytes;
known release additionally requires the original Task done and cancelled. Generic
cancellation or a forged end keeps I/O debt instead of inventing known retirement.
Other admitted failures remain conservative/unknown; no retry or competing reader
is created. Local FD retirement is not image discard, terminal ACK or publication.

## Verification and limits

Twenty focused actual private-socket/original-work cases passed in 6.24 seconds;
lint passed. They cover valid and fragmented envelope, signature/scope/sequence,
oversized auth/body declarations, wrong kind, unknown actual native read and
post-count drift, final key/policy/expected-row changes (zero next reads/foreign
callbacks), wrong factory/task nonpoisoning, one-shot/initial failure/deadline,
known partial/unstarted cancellation and rejected generic/forged retirement.
Earlier 14-case and 18-case runs passed in 4.82 and 5.94 seconds respectively.
Initial test setup lacked the explicit local fixture import/parameter; that was a
fixture setup error before any case body, then corrected. Formatting/lint-only
issues were fixed without protocol timing changes. No coverage credit comes from
that initial setup error.

Independent read-only source review accepted the envelope-only boundary and its
retirement distinction; reviewer ran no tests or native actions. Final broader
regression is recorded when complete. Historical broker/controller intermittency,
including the preceding GO_SENT-prerequisite run's existing cancellation refusal,
remains unresolved; later passing runs do not establish its cause or resolution.
The separately recorded native sender-destination incident remains open.

## Complete image delivery still required

Extend this same cursor through committed body streaming into the original native
result2 buffer and independent parent/revision validation. Preserve original
candidate withdrawal and actual framing/digest through cleanup discard and signed
terminal/ACK continuation; never insert a second reader. Connect reviewed broker
writer/service dispatch only with the original gateway continuation and qualified
startup/native publication gates. Physical/mobile and release qualification remain
separate. No host/device/build/keys/grants/providers/settings changed here.

The first broader run had one failure, 1,626 passed and one skipped in 106.05s.
An existing partially constructed broker BEGIN channel had no new optional result
receiver field; the new external-idle check read the snapshot attribute directly.
The repaired check uses the same absent-optional-field convention as adjacent
credential owners, validates the reciprocal alias, then exact type and historical
release if present. No work gate is changed. The exact failed BEGIN node plus all
twenty envelope cases passed after repair (21 passed, 5.94s); independent read-only
review accepted that delta. Final full regression is recorded separately. This
concrete failure is not classified as historical broker intermittency.

Before the final premature-admission delta, broader verification passed 1,627/one
skipped in 111.12s after the optional-field compatibility fix. A final audit then
made premature-phase refusal explicit before allocation/attachment: actual native
RUNNING/GO_SENT and consumed admission are checked with pure original custody.
The new test first obtains a real complete GO write while still native GO_INTENT,
proves no receiver slot/poison is consumed, then continues the original transition
and normal envelope read. It passed in 1.66s and independent read-only review
accepted the fence; final exact-source broad coverage follows separately.

Final exact-source affected regression: **1,628 passed, one skipped in 108.30s**.
Lint and whitespace checks passed; independent read-only review accepted the
source, exact cancellation distinction, optional-field repair and premature-phase
fence. The broader run includes all twenty-one envelope cases. No earlier failure
or unresolved incident is reclassified by this passing result.

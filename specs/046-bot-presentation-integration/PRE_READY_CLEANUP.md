# Original pre-READY cleanup reader

This source prerequisite extends the original-reader cleanup coupling to selected
v2 operations before GO. It does not enable character/image serving, terminal
qualification, ACK parsing, native credit release or gateway routes.

## Ownership and transition

Healthy BEGIN/READY work does not publish write quiescence. On the first cause,
the retained cleanup owner captures metadata before poisoning normal work, then
freezes the original shared cleanup budget. A failed capture cannot be retried or
reinterpreted as a post-GO result reader.

`ready` retains the original pre-result cursor, consumed offsets and buffer while
READY is incomplete or fully buffered. `ready_wait` retains the same original
work Task after its internal READY notification, before any GO request. Selection
requires exact reciprocal remote/channel/cleanup ownership, the original caller
and work allocations, immutable scope/state, no GO intent/admission/fact, and
known readiness custody. Captured attempted/retired flags cannot lose proof;
actual selector inspection proves the original active subscription or absence.
No cleanup selector inspection removes a subscription.

After native selector checks, callback-free fences revalidate the original
owner, cause Future and unchanged, nonfailed cleanup end before selection.
The original work Task retires its original wait and performs a typed switch.
Only that Task publishes write quiescence and the read fact. The existing cleanup
Task sends one CANCEL while that original reader drains under the same earliest
budget. An armed cleanup wait can inherit a shorter end through its existing
owned change notification; it cannot obtain a replacement allowance.

## Framing and outcomes

- Before READY: TERMINAL sequence 0, or READY 0 followed by TERMINAL 1.
- After the READY notification: TERMINAL 1 only.
- RESULT, GO, wrong sequences and duplicate READY are refusals; no scanning for
  a later valid frame and no ACK/retry is permitted.
- Decoded terminal data remains unaccepted and retains UNKNOWN/native debt.
- Local socket/clock closure needs actual original-work join and known local IO
  closure within the original budget. EOF is not native credit release.
- Generic or forged switches wipe only the original captured buffer. Changed
  records, foreign work or buffers cannot redirect disposal.

The broker's original-controller stop/join remains a separate fact from its
cancellation-adoption notice. Coupled tests stop/join that controller and observe
real peer EOF before expecting gateway local closure.

## Verification checkpoint — November 5, 2026

Independent source review accepted the bounded pre-READY/ready-wait coupling,
its readiness/final-boundary repairs and the causal tests. The reviewer ran no
fixtures. Root's exact-source, serial nine-module regression passes **334 cases
on Python 3.11.15** and **334 on Python 3.14.4**, without unobserved-task warnings.
The dedicated module contains 74 cases. These counts overlap, not add.

Coverage includes partial and fully buffered READY, healthy READY-to-GO,
cause/public-notice ordering, existing committed-public-GO cancellation fallback,
malformed frames, partial cursor/notice/change initialization, record substitution,
generic/forged switches, shortening and change-signal failure. Two independently
admitted synthetic operations use distinct profiles, devices, authorities,
operation bindings and sockets: a refused borrow leaves the other's budget,
partial bytes, native calls and work intact, and that operation subsequently
completes its original READY exchange.

Parent policy threads and Unix IO are real; native authority, peer identity and
clock qualification premises are mocked. UNKNOWN-reader fixtures dispose only
captured synthetic resources after observing the original Tasks stopped; this
does not manufacture production closure or credit facts.

Earlier concurrent regressions had policy setup refusals and an interrupted
wait; their exact cause is unproven. Later serial green is not a causal repair.
An attributed unobserved-work refusal was addressed by observing exact original
Tasks in two deliberately UNKNOWN tests after their outcome assertions. Initial
legacy closure expectations were migrated to actual CANCEL/EOF/controller joins,
without changing the deadline or weakening the UNKNOWN gates.

Full isolated CI, integration and runtime/physical qualification remain pending.
The [joined terminal transport contract](TERMINAL_TRANSPORT.md), qualified
producer/receiver admission, ACK, PRE_EMIT/DRAIN and authenticated routes remain
separate required work for complete desktop character and host-local image delivery.

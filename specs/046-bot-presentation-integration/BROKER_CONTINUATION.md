# Original broker controller continuation

This implements the cancellation-notification portion of the existing joined
terminal contract. It is not terminal permission, ACK dispatch, or image serving.
The actual qualified terminal producer/receiver factory remains a prerequisite.

## Frozen contract

Retain the cancellation notification and park Future allocations before their
initialization and before the original controller Task can run. A partial native
initializer retains its owner and cannot be retried or treated as harmless.

Only that original controller may mint a cancellation receipt. It binds the
original complete CANCEL frame, decoded window, record/budget/scope, Task
allocation and notification Future after header-first retirement, complete window
adoption and a fresh check of the same original cleanup budget. The notification
does not prove Task completion, local socket/clock closure or native release.

Clear only the consumed original cursor, synchronously and with cumulative byte
offsets preserved. Keep the original reading claim and Task alive. Park against
the same earliest absolute cleanup end; do not create a new allowance. The park
does not receive bytes, so queued early ACK bytes remain unread. No wake can grant
ACK or ordinary work. Expiry, ambiguous wake or drift retains UNKNOWN read debt.

The service waits for the exact notification or original Task failure, rather
than requiring that Task to return. It independently validates the receipt before
resource cleanup. Never-launched journal sealing is not controller/FD closure.
The existing retirement path must stop and join the original controller before
closing its local socket and clock. A known stop intent binds the original Task,
park Future, timer and deadline before Task cancellation; foreign cancellation
cannot mint this fact. Repeated abort never repeats cancellation.

## Verification and remaining work

Use isolated synthetic roots, no child launch and explicitly mocked peer/clock
premises. Test notification/receipt substitution, partial Future initialization,
header/body ordering, retained offsets and unread queued bytes, service cleanup
ordering, repeated abort, cancellation before/after notification, deadline
exhaustion and cross-operation isolation. Original live fixture sessions must not
be restarted or run against a competing native fixture.

After this prerequisite, the same controller still needs qualified terminal-write
and receiver permission before ACK parsing. Pre-READY gateway work, accepted
terminal transport, native PRE_EMIT/DRAIN, credential retirement, runtime and
physical qualification remain open. No host/device deployment is implied.

## Recorded source verification

Independent source review accepted the coupling, integer-before-comparison
repair and concrete native-descriptor dispatch checks. Root execution of six
no-child/pure modules passed 347 cases on each of Python 3.11.15 and 3.14.4,
including 25 new continuation causals. The reviewer did not run native fixtures.
No child/process/supervisor suite ran alongside unresolved original fixture
sessions; complete isolated CI and runtime qualification remain separate gates.

Historical nonpasses remain recorded: nine skips from the unsafe temporary
ancestor; nine fixture setup failures from inherited checkout group metadata;
one remaining legacy test awaiting Task completion instead of the new adoption
notice; and the first Python 3.14 rejection of its changed native bound-method
representation. These are not extra passes or relaxed safety requirements.
The corrected final runs retain exact cutoff, cursor, unknown-debt and callback
assertions, and do not change any cleanup allowance.

Observed continuation drift is sticky: notification consumers retire only their
original owner metadata and retain unknown read debt before propagating refusal.
Restoring a receipt, bound method or timer does not revive known-stop/local-close
permission. These latches do not follow a substituted clock, scope or another
operation's budget. Tests preserve that other budget before and after refusal;
fixture-only handle disposal follows the frozen unknown outcome.

## Full CI fixture migration

The first exact cloud run (42113671221, source 8bc56cc) failed one existing coupled
sender/receiver test, with 7,117 passed, 21 skipped and 190 subtests. That test
still awaited controller Task completion as cancellation notification; the new
bounded park correctly expired instead. Its reviewed test-only migration waits
for the actual service adoption notice and explicitly asserts the original
controller/read claim remain held. Original window equality, pending journal,
retained headers and exact abort/join/local-close checks are unchanged.
The corrected single coupled test passes on each of Python 3.11 and 3.14; this is
not a replacement for a fresh full cloud run or a deployment qualification.

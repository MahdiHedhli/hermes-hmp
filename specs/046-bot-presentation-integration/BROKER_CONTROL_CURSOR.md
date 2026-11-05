# Original broker control cursor: readiness integration

The selected-v2 broker controller retains its original Task and bounded bytearray
through GO/CANCEL parsing. It now uses concrete nonblocking recv rather than an
async receive Future that could consume bytes before the Task resumed. The
original buffer, cumulative received count and current frame base remain bound;
only complete grammar-accepted GO can clear its bytes and advance that base.
Cumulative consumption is never reset. Pending bytes and a sticky receive/commit
intent precede further checks or awaits. Arithmetic uses primitive counters held
before the syscall, and buffer extension uses the original exact bytearray.
Foreign metadata or uncertain receive/commit refuses without callbacks or a
fabricated read-retirement fact.

Try the bounded concrete recv immediately under the current original qualified
budget/native/grammar checks. Only an exact integer EAGAIN/EWOULDBLOCK leads to
owned readiness notification. This preserves the prior scheduling behavior:
when GO and CANCEL are already queued, the same controller can retire the queued
CANCEL before a notified service relays resources. Do not insert an unconditional
readiness await between those queued frames. A readiness callback carries no
payload and cannot authorize resource relay.

Retain each notification allocation before initialization/registration. Retry
only after its original read registration is known retired or no registration
was attempted. A valid elapsed end reports TimeoutError without registering.
A known timeout samples the SAME native clock and original first-cause budget;
original work expiry may enter its existing cleanup interval, retaining partial
header/body bytes on this same Task. It cannot renew a cleanup deadline or infer
cleanup eligibility from a clock error. Active shortening/wake under an earlier
cause remains a separate coupled lifecycle requirement.

Known zero-byte EOF refuses the frame but is a settled receive. Unknown selector
retirement, receive or cursor commit leaves the original read claim asserted,
even after the Task ends. No generic finally reset, alternative reader or socket
closure fact can erase that uncertainty. Synthetic fixture disposal after joining
the Task is explicitly separate from production closure/qualification facts.

This changes only normal GO/CANCEL control reading. The controller still returns
after CANCEL adoption. Continuing that SAME cursor toward a qualified ACK,
terminal acceptance, native PRE_EMIT/DRAIN and credential retirement remains
unfinished. No route, image publication, native authorization or release opens.

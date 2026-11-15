# Darwin process-exit observer contract

Fixture-only prerequisite for the broker containment experiment. This helper does
not install a service or activate character/image routes.

`tools/compat/darwin_process_exit_observer.py` registers one retained kqueue
EVFILT_PROC/NOTE_EXIT observer while the independently verified broker holds its
reader unreaped. The controller must already establish exact private job, kernel
peer, nonce and child identity. A numeric PID alone is insufficient.

## Registration and observation

The Darwin SDK `sys/event.h` and kqueue manual define EV_RECEIPT as 0x0040.
Python does not expose that constant on the inspected runtime. The helper checks
its other required select constants and refuses unsupported platforms. It uses
ADD, ENABLE, ONESHOT and RECEIPT, with an unpredictable registration cookie.
One matching EV_ERROR receipt with data zero means registration succeeded; it is
never an exit fact. Registration is followed by a nonblocking predrain. An exit
already pending invalidates the experiment, although its original observation
can remain available for bounded cleanup.

`ensure_pending(binding)` requires another empty pre-stimulus drain.
`poll(binding)` can return only the original frozen PID/observed-at fact minted
from a matching exit event. Observed-at means controller read time, not kernel
exit time. The interval between predrain and stimulus remains a causality limit:
an event may have queued in that interval. The event does not supply reap status,
descendant absence, pipe closure, manager causality or release authority.

## Custody and refusal

The owner retains the native queue before calling its methods. It binds its
original context, opaque experiment reference, primitives, descriptor identity,
non-inheritable state and immutable observation/cleanup deadlines. Acquisition
failure exposes a retained failed owner; it never retries registration. Wrong
external binding refuses without poisoning the valid owner. Observed internal
identity drift or reentry permanently invalidates that owner, including after
restoration, and forbids further native queue IO. Native-boundary checkpoints
prevent a swallowed reentrant refusal from minting a successful exit observation.

Malformed event/IO uncertainty retires observation work. It cannot be cleared by
restored values or cleanup polling. Where exact queue custody remains intact,
local disposal can still be attempted once. Close success requires native queue
close, native closed state and EBADF from the original descriptor; a wrapper flag
or no-op close is insufficient. Ambiguity never permits a retry or replacement
close. Queue closure is solely a local monitor fact.

Cleanup polling uses the original separate deadline, at most twenty seconds from
construction. It cannot renew work or make an invalid experiment eligible.
Exclusive descriptor ownership, trusted native primitives and a trusted same-UID
host administrator are premises. This is not protection against arbitrary
same-process descriptor interference or a malicious root administrator.

## Evidence and remaining integration

Model causals exercise receipt/error validation, preexisting exits, expiration,
wrong binding, descriptor/context drift, ambiguous close and swallowed reentry at
native boundaries. The Darwin native fixture uses two short controller-owned
Python children: EOF retires one, the other remains pending, and parent reap is
recorded separately. It neither launches a service nor claims manager containment.

The actual broker-crash integration and the separately instrumented manager-
causality control remain open. Unmodified readers may exit voluntarily on stdin
EOF after broker death. Reader-output EOF is not observable by the controller
without a separately reviewed ownership/transfer contract; do not invent that
measurement from broker-control EOF. Linux needs its own retained-pidfd and
service-manager contract and is not qualified by Darwin observations.

Primary API references: [Python select](https://docs.python.org/3.14/library/select.html)
and [Apple kqueue](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/kqueue.2.html).

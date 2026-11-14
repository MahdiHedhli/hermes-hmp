# Original-work write-quiescence prerequisite

This binds known completed native client writes to the original retained work
Task before cleanup can consume its connection. It is not a Task join, reader
handoff, transport closure, native permission or terminal qualification. The
whole-work-task join and reading=False CANCEL gates remain mandatory outside
the separately reviewed [post-GO cleanup coupling](CLEANUP_READER.md). That
coupling binds this fact to an active original read scope; the fact alone never
replaces those gates.

## Allocation and immutable fact

RemoteCleanupOwner retains the exact Future allocation and independent barrier
tuple before Future initialization and before either Task initialization. Unknown
partial initialization remains retained; only known initialized Futures are
settled during failure. The original immutable TaskAllocation, channel, native
clock, original CancellationBudget and actual BEGIN/GO write facts are bound into
one metadata-only _WriteQuiescence fact. No image/header dictionary alias or
second payload copy is retained. Future completion alone cannot mint the fact.

Only the exact original work Task may produce it: after completed GO, before
result reads, or in its guarded finally after known BEGIN with no GO attempt or
the exact completed GO. An active/torn/unknown client write produces no fact.
The producer irreversibly retires future ordinary BEGIN/GO writes with a separate
channel latch; channel refusal/work-clock/result-read behavior is not conflated.
Native clock/budget/reference guards bracket minting, under original work time or
the same first-cause cleanup interval. There is no new allowance.

Producer intent is recorded before native boundaries. Partial/failed minting is
sticky and cannot be retried by finally. Historical success is reused without
another sample or fact. A non-mutating write-completion inspection is used by
the producer so a torn GO does not prematurely mark cleanup UNKNOWN before its
existing original Task join. The old cleanup decision still records uncertainty
after join, preserving no-appended-CANCEL behavior.

## Consumption and failure

CANCEL's original cleanup actor additionally requires the retained exact fact,
Future/result identity and original scope. It consumes the fact once before
CANCEL intent/encoding/IO; no failure restores or replays it. Wrong actors,
forged Future success, changed scope/allocation/reference, native sample failure
and partial initialization refuse without foreign callbacks or foreign cleanup.

This prerequisite alone does not replace whole-task join or reading=False.
The post-GO coupling adds only original-scope cleanup reading and one CANCEL;
no ACK, registry/native release, reauthentication or image publication is enabled.
The full contract in [TERMINAL_TRANSPORT.md](TERMINAL_TRANSPORT.md) still needs
pre-READY cleanup, same-controller ACK continuation, qualified producer/receiver
acceptance, native PRE_EMIT/DRAIN and credential retirement.

Consumed historical facts still retain their original owner graph. Future native
credential retirement must account for references reachable through that owner,
barrier and fact after qualified DRAIN; consumption is not credential release.

These guards assume trusted installed Python and exclusive owner memory. They
are not an arbitrary Python-memory sandbox or production runtime qualification.

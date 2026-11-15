# Original signed READY wait cancellation retirement — November 6, 2026

This implements the first prerequisite of
[the signed pre-READY cleanup contract](../../specs/046-bot-presentation-integration/SIGNED_PRE_READY_CLEANUP.md).
It enables no pre-READY signer, wire CANCEL, ACK, remote/native release or image
publication. Existing post-READY cleanup and ordinary failure rules are preserved.

The receiver catches only an exact internal owned-readiness cancellation whose
minted receipt matches its original Task/socket/loop/scope/Future/handle/binding,
cutoff and unchanged cursor counts/bytes. Actual original Task cancellation is
required. Native readiness retirement checks are followed by the local cursor
and actor checks; disposal does not require reviving work or role authority.
The original cancellation is rethrown and operation failure remains permanent.

After validation, the original partial buffer is wiped. A distinct payload-free
historical fact retains original scope/readiness and consumed/target counts.
Historical local release additionally requires the original Task done **and
cancelled**, exact empty-buffer shape and current retained readiness retirement.
Unknown registration/read intent, substituted receipt/end, stale progress and
generic/fake cancellation preserve unknown IO. No retry or flag restoration.

Independent read-only review found and repaired two issues before qualification:
the initial positive path retained partial bytes in a transient values receipt;
and it accessed an exception attribute before exact-type checking. Neither initial
shape was committed as qualified. Final seven cancellation causals include empty
and partial-prefix wait, retired role key, generic cancellation, foreign cutoff,
progress drift and exception-subclass getter trap. They check payload-free facts,
wiped buffers and final traceback/context payload disposal, plus wrong-channel
release refusal. All 104 READY-reader module cases pass; configured lint passes.
An initial test-edit collection indentation error was corrected. A first negative
progress case expected FrameError, but the implementation correctly preserved
actual cancellation while retaining unknown debt; that assertion was corrected.

Full affected regression: 1,525 passed, one skipped in 84.46 seconds. This
passing run does not resolve or reclassify the earlier intermittent broker
controller failure. Exact source binding is recorded in the private checkpoint. Production startup, separate BEGIN-derived signing,
broker terminal/result custody and physical qualification remain open. No live
host, provider, device, deployment, key installation or settings changed.

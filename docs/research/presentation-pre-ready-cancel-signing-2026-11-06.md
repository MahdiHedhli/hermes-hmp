# BEGIN-derived pre-READY CANCEL signing — November 6, 2026

`NativePreReadyCancelCommitment` is a distinct signing-only owner. It requires
the original completed signed BEGIN writer and exact payload-free cancelled READY
wait retirement. No fabricated READY transition, no GO attempt and no unsigned
fallback are accepted. The original cleanup allocation must have joined its
original work Task, retain known intent and satisfy existing cause, quiescence,
qualified clock and earliest frozen cleanup budget gates.

The partial signer is retained before native/crypto effects. It consumes native
`_prepare_cancel` once, producing exact seq1/frame/window from the already-frozen
minimum end. Actual original BEGIN signature, retained role/material/actor and
cleanup custody are rechecked around preparation and signing. The final reader
release crosses native checks; retained material and callback-free key/handshake,
cleanup state, budget identity and actor seals follow that boundary. Failed or
consumed owners cannot be replaced, re-prepared or retried. Existing post-READY
signing refuses any retained pre-READY signer; no cross-scope replacement path.

This owner returns signed data only. It has no socket writer, IO/native completion,
remote ACK/custody, terminal/publication or startup authority. Test fixtures run
it on the original actual cleanup Task then deliberately refuse transport;
cleanup remains UNKNOWN rather than claiming delivery or resource settlement.

Eleven causals cover successful empty/partial-prefix signing, revoked-key acquisition, wrong-task
no-slot effect followed by original actor, expired budget, key retirement after
actual native preparation, preparation refusal, foreign sequence getter trap,
and final released-reader key/unknown/intent mutations. Final guards must refuse
immediately; no production flags are restored. The first wrong-actor fixture
checked held results before its awaited child finished; it now awaits the
original cleanup Task with a fixture-only bound, not a renewed protocol budget.

Independent read-only review accepted the final custody-tail repair. Earlier
selected runs passed 933 and 934 cases before the final custody repair; final
selected regression passed 936 tests in 54.84 seconds, with lint passing. The
additional partial-prefix case passes in the final 115-case READY-reader module
run (21.98 seconds); earlier runs are not promoted to coverage for that later
fixture. Configured lint and whitespace checks pass.
No live host, provider, device, deployment, credential installation or settings
were changed. Full character delivery and release qualification remain open.

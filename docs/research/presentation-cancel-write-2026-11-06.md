# After-READY original-cleanup signed CANCEL write — November 6, 2026

The fixed writer retains the exact completed CANCEL signer, original native frame,
sequence and frozen cleanup end before native callbacks. It does not call native
preparation again. Actual nonblocking send counts are sealed before current checks;
only exact EAGAIN uses owned write readiness under that same absolute cleanup end.
Full signed record plus frame, settled IO and final current role/actor/budget checks
precede the existing native `_cancel_write_completed` bool plus a private local
completion fact. Partial/uncertain IO retains preparation, window and debt without
retry, deadline renewal, broker receipt, execution or remote settlement credit.

Completed BEGIN and GO owners recognize only typed reciprocal CANCEL slot claims.
Their handoffs describe IO state and grant no permission. The signer accepts the
native completed bool only through the same retained writer's full-count fact.
Historical local closure admits only the original cleanup Task or its actually
done Task, with original process/thread/loop/coroutine references and known IO;
role retirement does not become a condition for solely local descriptor cleanup.
Production sender dispatch and pre-READY cancellation remain unimplemented.

Twelve causal cases pass: full seq1/seq2, partial writes, exact EAGAIN, uncertain
native send, key retirement after send, zero send, uncertain readiness registration,
wrong task, foreign GO-intent tripwire, final-descriptor key retirement and actual
cleanup-task cancellation. Last-tail refusal cases send zero bytes. Uncertain
send/registration and metadata drift retain UNKNOWN/debt. The tests observe actual
cancelled cleanup separately, never relabeling it as successful settlement.

Independent review found missing GO-intent typing and final native-tail material,
frozen-budget and actor checks. Independent final readback accepted the repairs. Final affected regression:
**1,500 passed, one skipped**, 75.26 seconds; configured lint/whitespace checks
passed. Prior signer `86667eb` passed CI766/run42300606324; current writer CI
is not yet qualified. Initial six-case run had a post-GO fixture assertion
that expected no admission despite actual completed GO; its corrected assertion
preserves the consumed admission without changing protocol behavior. No live host,
settings/device, installed build or physical/release qualification changed.

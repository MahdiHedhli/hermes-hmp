# Pre-READY signing-refusal local cleanup — November 6, 2026

A fixed no-IO predicate now recognizes exactly one original retained failed
post-READY or pre-READY signer, with reciprocal owner aliases and the other slot
absent. No raw signed output, writer or native CANCEL completion may exist. The
original cleanup Task must remain current/uncancelled, its original intent known
and work joined. Fixed signer metadata is selected internally, never supplied by
caller or wire; no current signing role is revived to dispose local resources.

The complete predicate and exact signer/scope identity are repeated after both
native cleanup guard/remaining-budget boundaries. Socket close independently
proves all retained IO is settled. Clock close occurs only if the same original
allowance and known owner remain valid after actual socket close. The original
refusal survives, remote UNKNOWN stays true and no CANCEL is sent or retried.
This refactors the existing post-READY helper and adds the distinct pre-READY
owner without generalizing credential gates or admitting uncertain read/write.

Thirteen focused cases pass: eight existing route/refusal cases plus pre-READY
known key refusal and four causals. Expiry before close, cancelled cleanup Task
and uncertain read receive no new close credit. Expiry after actual socket close
retains socket=true/clock=false, rather than erasing a historical fact or claiming
complete cleanup. No failed flags, buffers or budget are restored in production.

Independent read-only review accepted the fixed predicate/refactor and final
causal coverage. Full affected regression: 1,556 passed, one skipped in 84.02
seconds; configured lint and whitespace checks pass. Earlier passing reruns do
not resolve or reclassify historical broker intermittency. Remote acknowledgement,
resource/terminal/native release, startup, worker relay, publication/STATUS and
complete character/physical/release qualification remain open. No live host,
settings, credentials, provider, device, mobile build or deployment changed.

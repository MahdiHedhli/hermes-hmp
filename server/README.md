# HMP implementation

`hmp_plugin/` contains the Hermes platform adapter, operator CLI, pairing and authorization store, HMP wire handling, guarded send path, and compatibility gate. Its `register(ctx)` entry point adds exactly one platform adapter and one CLI command. The repository root contains the install wrapper used by Hermes's bare `owner/repo` installer.

The package source is preserved from the private F1 implementation. See [HMP v1](../docs/architecture/contracts/HMP_V1.md) for its wire contract, [deployment](DEPLOYMENT.md) for profile routing, and [contributing](../CONTRIBUTING.md) for checks.

The internal `presentation_credential_terminal_write.py` normal writer counts
immediate nonblocking TERMINAL sends on the original authenticated service socket.
A fixed original RESULT-to-terminal ownership handoff admits its write claim;
unknown delivery never replays or clears changed ownership. EAGAIN waiting,
receiver acceptance, ACK and native release remain separate.

The internal `presentation_credential_terminal.py` normal exporter signs and
verifies a bounded TERMINAL/2 envelope from the original signed-result/native-local
producer and exact canonical handoff. It has no transport method and no ACK or
release authority. Cleanup/aborted exporters and counted delivery remain separate.

The internal `presentation_credential_result_completed.py` validator binds the
completed signed RESULT byte count and body digest after output withdrawal to
its original actor, control and native local resource closure. The terminal
producer's normal signed branch can mint historical claim DATA; signed terminal
export/delivery, late cleanup transitions and acceptance remain unqualified.

The internal `presentation_credential_cleanup_budget.py` stage publishes only the
minimum of an authenticated sender stamp and the original native cleanup end.
It admits only the original actor, refuses active/competing readers, and retains
unknown publication without restoration or replay; no ACK or release is granted.

The internal `presentation_credential_cleanup_claim.py` stage compares a canonical
TERMINAL/2 handoff with original request/context and completed RESULT-body DATA.
It returns a one-shot correlation fact, never budget adoption, ACK or release.

The internal `presentation_credential_payload_digest.py` and
`presentation_credential_cleanup_payload.py` stages retain bounded RESULT-body
SHA-256 consistency DATA for later terminal correlation. They preserve the
original native/full-frame hashes and do not authorize output or release.

The internal `presentation_credential_cleanup_frame.py` stage continues one
newly authenticated frame on the retained reader/socket/task, including a fully
captured auth record with zero post-cause auth bytes and retained outer header. It returns bounded
consistency data only and is not registered for production delivery. Scope and
remaining lifecycle gates are tracked in
[the signed result contract](../specs/046-bot-presentation-integration/SIGNED_RESULT_READ.md).

`presentation_credential_cleanup_body.py` separately completes the same captured
partial-body digest. Its result is consistency DATA; it does not restore the old
image buffer, accept a terminal or authorize native release.

`presentation_credential_cleanup_terminal.py` owns the explicit successor
TERMINAL/2 authentication record after actual RESULT/1 consistency completion.
It retains original read ownership and byte accounting. Terminal frame/body
handling and release remain separate unfinished work.

`presentation_credential_cleanup_terminal_frame.py` admits a distinct frame from
its original verified TERMINAL/2 auth receipt. It uses fixed owned-slot dispatch
through the shared frame reader. Returned bounded metadata/hash consistency is
not terminal claim, ACK or native release acceptance.

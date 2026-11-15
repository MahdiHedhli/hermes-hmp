# Fixed GO commitment on original native admission — November 6, 2026

`NativeGoCommitment.retain(producer)` accepts only the exact original work Task,
retained completed signed BEGIN/READY/transition and actual native GO admission.
The existing `_go_exchange` performs fresh PRE_GO, creates `_GoAdmission`, and
consumes native GO_INTENT before the synthetic test intercepts its closed sender.
The new signer does not create that admission, undo it, send bytes or establish
GO_SENT. It uses fixed GO_INTENT material/native checks, not the STARTING/READY
fence. Original current keys, socket, clock/end and native work allocation remain
joined before and after cryptographic boundaries. The only signed statement is
gateway/g2b GO sequence 1 for the original empty frame and signed input context.

The partial signer is retained before native callbacks, and signing latches once
before callbacks/crypto. Failure after admission retains actual consumed native
state and debt without rollback, retry, native write credit or worker execution.
The signer refuses existing GO write intent/fact. Production `send_go`, startup,
resources and generic signed-channel fallbacks remain closed.

Eight direct-native cases cover fixed sign/verification, wrong-task factory,
retired keys before and during signing, substituted admission, expiry, and foreign
expected-row/end callback tripwires with no callbacks or signed raw publication.
Independent read-only source review found a metadata schema/type gap; closed
primitive row validation and exact integer ends repair it. Review accepted the
repair within signing-only scope. Selected affected regression before the final
exact-value join: **853 passed**, 39.49 seconds. After requiring fixed GO values
derived from retained READY, eight focused cases passed in 2.16 seconds and
configured lint passed. Independent final source readback accepted this tightening.

Initial added admission/expiry assertions wrongly expected a consumed signing
attempt and GO_INTENT after native expiry; actual evidence showed preflight refusal
before signing and native UNKNOWN after expiry. Those assertions were corrected
to preserve observed native state; no protocol behavior or deadline was weakened.
Prior unexplained cancellation failure remains separately recorded. No live host,
settings, installed app or physical/release qualification changed.

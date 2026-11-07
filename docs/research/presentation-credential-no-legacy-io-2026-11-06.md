# Refuse unsigned direct IO on credential channels

Independent read-only review accepted this source fix and the separate signed
control implementation contract. Inspection found that the legacy GO/CANCEL
controller reads directly from the socket, outside generic SocketChannel.send/
receive gates. Its retain/constructor/read path therefore needed an explicit
credential-mode refusal before resource startup could be composed safely. This
was a latent draft-source fallback, not a confirmed deployed-host exposure; no
production credential startup currently exists.

Legacy `BrokerCancellationOwner.retain` now refuses a credential channel before
claiming its controller slot. Direct initialization also refuses before capturing
another operation's failure grammar/budget or allocating a native Task/Future.
The exact-type/one-initialization guard prevents replacing an original or partial
task/cursor. Reader guards refuse later credential attachments before raw GO/
CANCEL reads. Solely local owned cleanup remains separate and is not disabled by
this network-IO refusal.

The shared legacy result native-IO boundary and result sender/receiver retain
paths also refuse credential channels before payload/candidate custody claims.
Existing unsigned channels keep their prior behavior; this is no Hermes version
allowlist or feature qualification switch. Do not remove these guards to compose
the new transport. Implement the actual signed cursor/context described in
[SIGNED_CONTROL_OWNER](../../specs/046-bot-presentation-integration/SIGNED_CONTROL_OWNER.md)
first, retaining the original task, phase receipts, scope and earliest budgets.

Root's affected regression passed **1,116 tests, one skipped**, in 29.86 seconds;
configured repository-wide Ruff passed. The 144-case control/result/adoption/input
subset passed in 17.75 seconds. Actual completed-credential service tests prove
no legacy control/result owner claim, unchanged original grammar/budget and no
native Task/Future allocation on direct refusal. The native-input fixture proves
gateway result custody stays unclaimed. A live disposable legacy controller test
proves reinitialization cannot replace its original task, cursor, scope or Futures.
Tests use synthetic keys/policy data and modeled peer/clock qualification.
Reviewer execution did not occur. Unrelated legacy-test formatting was restored
with exact AST equivalence; no production source or test semantics changed after
the final broad run.

Earlier queued-owner source `baf2212` passed CI718 plugin job128032351060:
8,307 tests, 190 subtests, 33 skips, 18 warnings, 403.30 seconds. Plugin checks
and Python 3.12–3.14 Unicode jobs passed. That does not qualify this newer fix.
Signed GO/CANCEL, resource/READY startup, remaining signed/direct IO, production
runtime/source/key admission, native publication, STATUS and physical/release
qualification remain open. No host/device/permission change or key installation
occurred. The separate earlier destination-custody incident remains unresolved.

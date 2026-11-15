# Original service current GO read — November 6, 2026

Terminal tracing confirmed an earlier actual dependency: authenticated GO is a
read fact, not worker relay. Existing generic credential work/GO gates remain
closed. Neither RESULT transfer nor normal OK TERMINAL can be implemented by
pretending the child executed from this receipt. See the reviewed
[fixed native relay contract](../../specs/046-bot-presentation-integration/SIGNED_GO_RELAY.md).

`CredentialGoPhase.creator_current` adds the missing original-service read-side
validator. It uses original actor/notification admission, then rechecks exact GO
signature/frame, original retained context/pins, current role, native work clock,
uncased original budget, native control state and creator after boundaries.
It returns the existing exact native GO receipt. No new permit/token is minted;
worker relay, result or release permission is not enabled. Wrong actor and
not-yet-notified calls cannot poison the original owner. Admitted currentness
failure latches a consumer refusal, preventing restored time/material from
reviving that read path while original controller cleanup remains separate.

Six actual private-peer stages pass: before READY, READY, after GO and three
current-GO checks (normal, wrong actor before original actor, deadline refusal).
The service checks before notification refuse without poisoning. Actual GO
Future/receipt identity is preserved; a sampled deadline refuses and repeated
lookup cannot re-enter native sampling. The same original controller then handles
CANCEL/window/end as before. Worker/control-pipe GO remains unattempted and the
registry remains PENDING, not remote closure. Disposable resources and modeled
native peer/clock/authority are not production startup or physical qualification.

Independent read-only review accepted both read validator and next relay contract.
The relay still needs a distinct one-shot original-service owner and a fixed
reciprocal credential fence AFTER final existing native control-pipe callbacks,
BEFORE actual write. Merely calling the legacy registry relay after validation
would not satisfy that contract. Actual control delivery, execution/result,
terminal/ACK/native DRAIN/PRE_EMIT and publication remain separate requirements.

Full affected regression: 1,559 passed, one skipped in 84.32 seconds; configured
lint and whitespace checks pass. No live host/config/grant,
credential installation, provider, mobile build, device or deployment changed.
The full character feature and broader roadmap remain incomplete. Historical
broker intermittency is retained, not resolved by isolated passing observations.

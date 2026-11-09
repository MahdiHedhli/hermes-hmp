# Schema-three push lifetime backport — November 9, 2026

Status: regression isolated; repair not yet deployed or qualified.

The schema-three baseline cancels push workers and slots during bounded close. Native authorization invoked through asyncio.to_thread can continue after its awaiter is cancelled. Server stop detaches the dispatcher without retaining its actual borrowers; adapter store retirement currently considers only operator-read debt. A dispatcher-only patch therefore cannot establish safe store lifetime.

A synthetic blocked authorization thread reproduced bounded close returning before thread completion on source f66ba37. The new regression then fails because the baseline has no retirement_pending contract. This is an expected red contract test, not proof of a live incident or of store access after close. Evidence: /private/tmp/hq-ju8jhbm4/receipt.json (one failure, zero errors/skips, source unchanged). The finally block releases the synthetic thread and joins any available drain; no live home, native authority, relay transmission, or host mutation is used.

Required migration-free repair: retain original dispatcher/relay/startup resources, shield actual authorization/key/gate borrowers from waiter cancellation, retain a single relay close attempt, expose actual drain debt through server stop and adapter store retirement. Preserve schema three, permissions, configuration and feature surface. Constructor failure before relay return and failed context-builder allocation ownership remain separate audit requirements; do not claim full lifecycle qualification from this regression.

Next: implement this ownership chain without importing the media/schema-four branch; causal cancellation, delayed close, failed startup, waiter cancellation, repeated stop and scope substitution tests must pass before deployment consideration.

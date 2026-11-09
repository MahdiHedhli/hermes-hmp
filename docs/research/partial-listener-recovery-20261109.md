# Original partial-listener recovery — November 9, 2026

Implementation `cfc06922ce1a8cbc17c06fe2378f3cc16c358a40`, test-complete source `34329d7e71e1a669f177abaa82be0d67fb3eb893`. Not deployed.

Explicit disconnect may now reconcile a retained partial listener. It rejoins the original component Future/context/Store/bound close, awaits that listener's actual stop owner, and transfers cleanup to one retained Store retirement task. The bootstrap mirror records that transfer so unpublished close cannot replay. Original opening/listener/context/Store/bound-close ownership is checked after awaits and before/after generation cleanup. Only actual successful closure followed by scope rejoin clears the bootstrap pointer and startup uncertainty. Cancelled observers retain the original cleanup task; lost close acknowledgement refuses replay and reconnect.

514 selected tests pass unchanged on Python 3.14.9 and 3.11.15, zero failures/errors/skips:
- `/private/tmp/hermes-qa-partial-listener-recovery-current-26ywwkyr/receipt.json`
- `/private/tmp/hermes-qa-partial-listener-recovery-floor-28tfedxe/receipt.json`

Seven added cases use actual HmpServer lifecycle ownership with synthetic runner/site ports: failed setup cleanup, cancellation during startup/recovery, failed Store close/no replay, cancellation after Store closure but before recovery resumes, held original close versus replaced method, and opening/context drift during generation cleanup. The reconnect probe proves actual admission to the next component-opening function, then intentionally refuses before allocation; it does not prove a second successful native listener startup. Existing nonconforming partial-listener test ports without stop/drain remain refused.

Independent read-only review accepted the bounded implementation and the test-only follow-up, including direct late-cancellation coverage. No full builder/native/other-borrower or physical qualification is inferred. Component-builder failures before successful return, native media publication/migration, whole-plugin regression and device/release qualification remain open. No host install/restart, provider/send, grant or media activation occurred.

# BEGIN/GO final native-tail audit and repair — November 6, 2026

Base source `8ac1edf` with new synthetic causals reproduced final descriptor-tail
revocation gaps: GO sent 1,617 bytes after key retirement and after work-task
cancellation; BEGIN sent 2,586 bytes in both cases when the hook was placed at its
second/final presend guard. The first BEGIN test hook fired at an earlier guard
and passed because a later guard caught it; that was not coverage of the actual
presend boundary. No live host or real user traffic was involved. Prior green
runs are not relabeled as coverage of these newly tested tails.

BEGIN now applies its existing fixed callback-free native custody/policy/clock/
budget fence after descriptor calls, followed by retained current role, exact work
actor/caller cancellation and held scope checks. GO uses a separate fixed
GO_INTENT pure custody fence: actual RUNNING/GO_INTENT, consumed admission and
original ledger/binding/policy/budget. No caller-selected phase or new native GO
authorization is added. Both role/actor seals occur after all descriptor callbacks
and before the next send, with original write intent/progress retained on refusal.

Nine new causals cover BEGIN key/task/policy/listener and GO key/task/policy/
listener/admission substitution; together with the two existing CANCEL tail cases,
11 focused cases pass with zero sends after late refusal. Admission drift retains
unknown metadata debt rather than inventing local release. Independent read-only
source review accepted this bounded repair. Selected affected regression:
**909 passed**, 48.13 seconds. Configured lint/whitespace checks pass after a
test-only local-name/line-wrap correction; executable source stayed unchanged.

No production startup, permissions, provider, device build or live host changed.
The wider character pipeline and physical/release qualification remain open.

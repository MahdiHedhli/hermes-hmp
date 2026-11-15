# Internal signed GO dispatch and fixed GO_SENT — November 6, 2026

The credential branch of the existing original-work GO exchange now composes the
fixed GO signer and writer after the existing native GO_INTENT admission. It
checks original producer/remote/full write fact before the existing single native
GO_SENT transition and uses a fixed post-GO_SENT material/signature guard afterward.
The noncredential sender is unchanged; generic credential `send_go` still refuses.
GO_SENT proves local transmission, never broker receipt or execution.

After the existing GO notice and write-quiescence fact, the original signed work
Task parks on its retained cause rather than entering an unsigned result reader.
No result owner/token/candidate is created. The native Future methods, scheduler,
original barriers/cause/loop are sealed after quiescence callbacks and before wait.
The shared cause Future is not cancelled by Task cancellation. Startup, resource
admission, signed result/terminal/cleanup and worker relay remain separate.

Six direct actual-original-allocation cases pass: successful GO, native post-GO_SENT
error, post-transition key retirement/cancellation, foreign cause method at final
quiescence boundary, and key retirement on the last native GO_SENT check. Full wire
and actual GO_SENT remain historical facts on refusal; public success is withheld,
no result token/execution is credited, and original cause/debt is preserved.

Independent review identified the cause-method fence and final native-check key
reseal gaps. Repairs, six causal tests and independent final source readback pass. Selected
affected regression: **872 passed**, 44.25 seconds; configured lint passed.
This selected scope is narrower than the prior writer regression. Initial late-failure fixture assertions expected pending
result notices, but existing cleanup correctly publishes False; assertions now
preserve that observed refusal without changing behavior. No live host/settings,
installed build or physical/release qualification changed.

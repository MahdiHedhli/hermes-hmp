# Fixed pre-READY CANCEL writer — November 6, 2026

`NativePreReadyCancelWriter` transmits only the exact original BEGIN-derived
signer's bounded seq1 raw-record/frame, on the original cleanup allocation and
already-frozen native end. The partial owner is retained on signer/channel before
native guards. The fixed typed BEGIN reciprocal join permits this exact writer's
active state without recursive authority checks or a fake READY/GO transition.
Existing post-READY signing/writing stays separate; no generic credential gate
opens. The explicit local SocketChannel release branch accepts only fixed types.

Each native send is counted before subsequent validation; exact would-block
retires its owned write-interest on the same earliest end. Known full wire plus
settled/current role/actor/custody/budget checks precedes the private local fact
and original native completion bool. Any uncertain send/registration retains IO
debt and refuses retries. Current key authority is unnecessary for already proven
local IO disposal, which still requires original actor or actual original cleanup
Task completion/context. No remote ACK, resource or terminal release follows.

Thirteen focused causals pass: actual full wire, two actual sends with a short
first write, owned EAGAIN wait, unknown send, zero count, uncertain registration,
expired budget, first-write guard failure, wrong actor before original execution,
final descriptor-tail key/task cancellation/cleanup-unknown drift (zero send),
and historical known local release after key retirement. Consumed/failed writers
cannot be reacquired or retried. Actual received wire is compared with retained
exact raw+frame; missing completion never gets a private fact.

Initial 23-byte-every-call positive exhausted the original 250ms cleanup interval
and correctly withheld completion. The success fixture now uses two actual sends;
no protocol deadline was extended. Another initial assertion conflated a known
no-IO cleanup-custody refusal with uncertain send debt because both case names
ended in unknown; expectations now use the exact cases, without source relaxation.

Independent read-only review accepted this writer slice and final tests. Root
execution: full affected regression 1,551 passed, one skipped in 83.14 seconds;
configured lint and whitespace checks pass. The earlier intermittent broker
failure remains unresolved; this pass does not establish its cause or repair. Automatic
pre-READY routing/broker correlation, startup, results/terminal, physical devices
and full character delivery remain open. No live host/config/key installation,
provider, mobile build or deployment changed.

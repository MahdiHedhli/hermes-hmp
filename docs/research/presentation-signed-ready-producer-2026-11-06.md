# Fixed READY signing from actual resource/input facts — November 6, 2026

This source component signs only the original broker READY statement, after
checking actual independently started/staged resources and a completed native
input-pipe write observation. It starts no process/resources, writes no socket,
observes no READY grammar, relays no worker GO and grants no native publication.
Production admission/startup remains closed.

`ControlInputWriteObservation` is retained only after all original bytes have
been written to an exact native FileIO stream. It binds original owner, handle,
child, stream/descriptor, process/thread context, input hash and length. Late
reference drift, uncertainty, sticky work refusal or failed reentry prevents
publication even if a legacy aggregate flag is restored. Partial/unknown writes
retain refusal and never mint the observation or retry. Legacy wrappers may keep
their old input behavior but cannot obtain this native observation.

`CredentialReadyProducer.retain(control)` accepts only the original service
creator and retained signed-controller context. It retains a consumed partial
owner before native callbacks. It joins the original active registry record,
resource/process/control pipe, native input receipt, exact input context and
write observation. The fixed `prepare_ready()` consumes one signing attempt before
callbacks. It revalidates the original four-record credential transcript and
independently derives input/scope hashes; mutable BEGIN claim data cannot select
what is signed. It signs only broker/b2g READY sequence0 using the retained role
key and exact original work end.

Original current material/generation, resource state, live owned child, input
receipt, native pipe descriptor and remaining work time are checked before key
use and after crypto. Final concrete pipe/child checks follow late clock/material
callbacks, with original local seals. A last-sample closed/rebound pipe or retired
key withholds the record and preserves uncertainty. Returned signature data is
not a successful write, child-input-read acknowledgement, GO grant or publication.

Independent source/test review accepted this signing-only slice without execution.
Root final affected regression: **1,262 passed, one skipped**, 47.68 seconds;
configured repository-wide lint passed. Focused READY cases: **12 passed**,
2.82 seconds; control-pipe/resource cases: **68 passed**, 3.92 seconds. Final full
adoption/controller fixture module: **96 passed**, 14.97 seconds. Tests cover
actual disposable child processes/input pipes, wrong task, missing resources/
input/fact, wrong input hash, role retirement before/after crypto, last-sample FD
close/dup2 replacement, foreign resource phase with zero comparisons, forged BEGIN
claim ignored, uncertain partial input write and sticky post-write reentry.

Resources in these fixtures are independently started through the existing
standalone registry API on NEW synthetic homes. This is not production credential
resource admission. Workers receive input but no GO. Fixture teardown reaps its
actual owned child and closes only known disposable streams/selectors; it does
not claim protocol/native reservation release. Keys and peer/clock policy remain
synthetic. No live host/device/mobile build/permissions/provider/key installation
changed, and physical/release qualification is not inferred.

## Prior CI failure and bounded fixture repair

Exact prior source 9dcda68 failed CI736 plugin tests: two failures, 8,372 passes,
33 skips, 18 warnings and 190 passing subtests; Unicode jobs passed. One GO/CANCEL
fixture constructed its 250ms cancellation window before broker BEGIN/GO setup
had finished, and its service consumer correctly refused when no time remained.
The earlier-cause fixture assumed local cause happened before a peer-created
window; CI observed the reverse and correctly retained the earlier remote end.
These failures are not reclassified as passes.

The revised fixtures establish actual local cause with an Event before encoding
a deliberately later remote window, and observe the original native GO-read
notification before generating the next CANCEL window. That fixture notification
is not a production execution acknowledgement. Both waits remain bounded by the
original work end. No protocol deadline or 250ms interval is lengthened, expiry
refusals remain, and earliest-end assertions are preserved. Independent read-only
review accepted the ordering repair. The new exact-source CI result is pending.

Remaining: actual signed READY write with retained write/grammar facts, production
resource admission and worker GO relay, later signed result/terminal/ACK IO,
production startup, native publication, STATUS and physical/release qualification.
Full character delivery remains unavailable. Frozen image deployment approval and
the earlier unresolved native-destination incident remain separate.

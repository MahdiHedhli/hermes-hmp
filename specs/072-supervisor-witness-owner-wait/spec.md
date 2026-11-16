# Retain supervisor completion while waiting for a native witness

Four supervisor tests awaited only native.entered. If the original supervisor finishes before that stage, the event need never be set; the test can wait forever without reporting the original outcome. The broad immutable8efd6c1f run is still live and last logged PRE_GO-1-False at19:56UTC. Its in-process owner task state was not externally observed, so this source gap is not a proven root cause of that run. The isolated original case passes with this change.

Own a separate witness task and wait for it OR the original supervisor. A finished supervisor wins simultaneous completion: retrieve its original exception/cancellation, or fail with fixed content if it returned before a currently blocked stage. Success requires the witness and a still-pending original operation. Finally cancel/join only the witness. Preserve every original test assertion, fault point, deadline and production byte; do not change authority, native lifecycle or delivery.

Both pending futures still wait: no new timeout or false terminal claim. Caller cancellation leaves the original supervisor with its existing owner. Selected native presentation service qualification remains independent of this preserved legacy harness.

# AR1-035-T014b: native write dispatch currentness

Accepted bounded source scope: create/edit scheduled jobs and set a profile default
model. These three routes use synchronous native bridge operations in a worker.
Delete/pause/resume loopback transport and native transactional authorization
remain separate open work. No live operation is part of this implementation.

Retain original request context/store/bridge/identity/instance/listener generation,
phone/token family, canonical profile, raw headers and request task before initial
authorization and body awaits. Headers remain request-local, redacted and unlogged.
Rejoin original dependencies before native authorization dispatch and after every
initial authorization/endpoint await; charge the rate limit once. After bounded
body parsing/validation, sample current authority again. Never adopt a replacement
context/profile/bridge or refresh a token to make a failed write proceed.

Retain the exact native callable and arguments in a one-shot worker handoff. The
worker checks observed request cancellation/completion and current original-scope
authority immediately before invoking that callable. A refused or cancelled
handoff invokes no mutation. A queued handoff never retries or reselects a worker,
endpoint or profile. Native prompt/model validation and hard-deny checks remain.

This check is a freshness observation, not a lease or atomic cross-store/native
transaction. Revocation after native dispatch cannot be rolled back by HMP.
Do not post-filter a completed mutation into a new authorization refusal or claim
it never happened. Preserve existing success/error/uncertain-result semantics;
no retry after native success, exception, cancellation or lost acknowledgement.
Cancellation once the native call begins does not prove the side effect stopped.

Causals: access/family/bot/flag changes during body read or worker scheduling,
original dependency/generation/profile drift, observed cancellation before worker
start, positive exact-once dispatch and native exception with no retry. Existing
read currentness, validation, rate limits and fixed errors must remain intact.

Mutating native response exposure/revocation after dispatch and cross-system
atomic authorization need a separate full contract; this partial mitigation does
not close T014, qualify a host/device, grant controls or change actual jobs/models.

## Source acceptance checkpoint

Independent contract and implementation review accepted this mitigation.150
focused read/write/cron/model/readiness checks pass with source hashes unchanged.
Ruff, closed plugin surface, privacy and log scans pass. The worker uses captured
headers/authority/dependency references, never parses a request, and joins the
held application/context without mutable request rediscovery. It samples the
original task's done/cancelling state before and after currentness checks. These
are observations, not atomic cancellation or a native rollback mechanism.

A lock protects its single attempted handoff. Started is retained before native
invocation, including native exceptions. Preflight HmpError remains distinct from
native failures; cron validation refusals retain400 and native model failures
retain503. No native exception is retried or interpreted as proof of no effect.
No loopback mutation, live host, actual model/job change or device acceptance was
performed. Post-dispatch response/authority and transactional guarantees stay open.

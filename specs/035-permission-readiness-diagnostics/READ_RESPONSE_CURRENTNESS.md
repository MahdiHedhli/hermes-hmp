# AR1-035-T014: jobs/model read response currentness

Scope: GET jobs list, current default model and model options only. This is a
partial operation-authority repair, not completion of T014 or a write lease.

Retain the original request context, store, bridge, identity, instance, listener
readiness generation, canonical profile, bearer headers and authenticated caller
before the initial asynchronous authorization. Rejoin them after authorization,
endpoint resolution and the native/loopback read. Before each next read and final
response, authenticate the original headers anew, require the same caller, current
identity and listener generation, current device controls, current bot authority,
and the corresponding current feature flag/API availability. No recharged rate
limit, token refresh, endpoint retry, scope substitution or response fallback.

Failures use existing fixed auth/not-found/feature-unavailable errors; native data,
headers and endpoint details must never appear in diagnostic output or owner repr.
The read may already have happened when access is revoked, but its result must
not be returned after an observed denial. These checks do not create an atomic
native transaction or promise to prevent revocation after the final check, and
must not be used as a native write authorization primitive.

Causal tests: revoke controls/token family/bot authority or disable the feature
while a read is waiting; replace context/bridge/store/identity/instance or listener
generation; ensure the result is refused. Change authority during endpoint lookup
and ensure no subsequent catalog/jobs read. Preserve a successful same-scope read,
existing error shapes, no additional writes and one initial rate charge.

Mutating create/edit/delete/pause/resume/model-update body and worker boundaries,
native transactional authorization, exact installed host and physical device
qualification remain separate open tasks. No live grants, jobs, providers or
host settings change as part of this source repair.

## Source acceptance checkpoint

Independent focused contract and implementation review accepted this bounded
read-only slice. The final source passes105 focused read-currentness, existing
cron/model and readiness tests with file hashes unchanged during the run.
Ruff, closed plugin-surface, private-data and test-log scans pass. Read dispatch
uses the retained bridge/profile/caller, including the initial authorization
await. Final identity/bot/feature sampling follows the last store/controls
callbacks and ends with the original dependency seal. These separate reads
do not become a native transaction.

Initial owner/limiter callback dependency substitution, late endpoint generation
drift, final bot-callback bridge replacement, final authentication policy changes
and final controls-callback feature disablement have causal refusal tests.
No host/device behavior or mutating operation is certified by these checks.

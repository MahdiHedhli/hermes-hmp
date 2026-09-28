# Approvals review status

**Draft, security review rejected. Do not merge, release, or enable this branch.** This branch ports the F3 server proposal for review only. It is based on the public HMP migration and contains no app code or private review reports.

The F3 patch is applied on the latest F1 source, preserving the later additive tool-output fields and their tests.

Two independent reviews rejected the design. The blockers are:

1. Prompt expiry is not enforced, and the observation list has no bound.
2. Owner-only authorization is not enforced for each device.
3. The `direct_send` flag can be bypassed while the base gate is open.
4. Phone chat enables `allow_gateway_control`, exposing gateway control and creating a self-approval race.

The reviews also called for total loopback POST timeouts, SSE CRLF and buffer bounds, redirect and resource limits, avoiding unknown-request lock allocation and spam, fixing fallback deadlock and lock leakage, and keeping approval answers out of logs. These are open findings, not accepted risk.

Hermes owns the approval timeout. Its `approvals.timeout` default is 300 seconds, and `agent.clarify_timeout` defaults to 3,600 seconds per profile. There is no expiry event. Late replies receive `409 approval_not_pending` through the API server. HMP must account for this behavior before the feature is considered ready.

F3 expands the qualified-send `bridge_files` set by three approval-related Hermes files. The existing fingerprint is intentionally left at its pre-F3 value, so sending fails closed pending human requalification. The initial migration branch does not change that fingerprint.

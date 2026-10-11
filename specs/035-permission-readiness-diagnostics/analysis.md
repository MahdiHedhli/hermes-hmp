# AR1 implementation analysis — accepted contract v3 checkpoint

## Requirement coverage

| AR1 requirement | Spec / contract | Plan | Verification task |
|---|---|---|---|
| T001 pairing and post-pairing UX; supported, entitled, disabled/unavailable; shared control scope | R1–R5, R8–R9, R18–R19 | mobile refresh and safe actions | T009–T013 |
| T002 negotiated authenticated schema, reasons, freshness, privacy | R1–R17; readiness-v1 | endpoint/status flow | T001–T008 |
| T003 admin/device request, grant, deny, explicit confirmation | R9, R20–R21 explicitly defer mutation | separate future lane | future T003 |
| T004 revocation and stale state | R6–R7, R17–R18; point-in-time limit | server rechecks, no durable cache, forced same-scope reads before actions | T005, T012–T014 |
| T005 authoritative grant readback/lost acknowledgement | R20–R21 future contract only | out of first slice | future T005 |
| T006 complete Spec Kit and independent review | this directory | v3 contract accepted; source review remains pending | T001–T003 |
| T007 host and mobile readiness, safe guidance | R15, R18–R19 | source and mobile tables | T004–T013 |
| T008 causal and negative tests | checklist/security.md | bounded worker tests | T008, T013–T014 |
| T009 physical devices and release | explicitly separate, not claimed | separate qualification | T015 |

## Source findings and implications

1. **Authentication is suitable but handler order matters.** `auth.py` binds a
   bearer to an active device, current instance, token family and expiry.
   `server.py` runs current-key, error, peer and parser middleware before
   compatibility middleware. Its handler-level bearer is what gives the new
   capability exception a private authenticated response. The public `/ready`
   response must not be repurposed.
2. **The existing jobs/model gates conflate their failure causes.** In
   `server.py`, both `_cron_endpoint` and `_model_profile` check
   `is_owner_device` before awaiting `require_bot_authorized`, then check live
   feature flag/API eligibility. They do not re-authenticate or recheck device
   controls after the await. Those handlers also return one feature-unavailable
   code for multiple causes. This proposal reports a fresh own-device status
   after bot authorization and explicitly leaves the operation-path gap open.
3. **Capability is version/API evidence, not an allowlist.** `compat.py`
   has distinct jobs/model `FeatureStatus` values and `hermes_version.py`
   defines both feature floors. The proposed response maps only status/reason;
   it discards labels, fingerprints, SHAs and missing-dependency names. Unknown
   or newer versions are not refused solely for being unsampled.
4. **Permission is one shared control.** `request_ctx.py`'s effective
   `is_owner_device` uses the host decision when present and legacy owner-list
   fallback when absent. Jobs and model share this privilege. The proposed
   payload has per-feature capability/setting axes but the same effective
   entitlement for each. It reveals only the caller's own result.
5. **Endpoint configuration is not reachability.** The existing bridge
   resolver can collapse missing, malformed, or ambiguous configuration to
   `None`; the readiness projection must not call that `missing`. A separate
   strict projection reports configured/missing only from a well-formed source
   read and otherwise reports `unknown` or fixed unavailable as specified.
   It opens no socket. Existing jobs/model data routes are forbidden as
   diagnostic probes; `api_reachability` is fixed to `not_probed`.
6. **The current listener health snapshot is not a phone authorization
   response.** `adapter._health_snapshot` is host-local diagnostic material
   and can mark channels ready from static gates and endpoint presence. It
   cannot be copied to a mobile route as proof of current entitlement or
   network reachability.

## Boundaries retained for source review

- API reachability remains `not_probed`; this slice cannot distinguish a
  network outage from a route-level API failure.
- Existing jobs/model route authorization after asynchronous bot checks needs
  its own independent source/security review and tests. It is not repaired by
  refreshing the diagnostic and is not a readiness guarantee.
- Actual Request access delivery, notification, grant, deny, or Fix action
  needs a distinct admin/operator contract and explicit permission.
- Parent's one-time host change/restart is external evidence and is not used
  here as source behavior or a task completion claim.

## Review state

Draft for S5 independent contract/security review. All AR1 and local source,
mobile, test, install, and release tasks remain unchecked. This analysis is a
source-backed design checkpoint, not a test or runtime receipt.

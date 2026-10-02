# Feature: Approvals under the minimum-version policy

Status: **Root decisions D1-D8 frozen 2026-10-01** (see [`ROOT_DECISIONS.md`](ROOT_DECISIONS.md)); source
implementation in progress on an isolated local branch and awaiting independent review. Nothing here is
self-certified. It amends
[spec 013](../013-minimum-version-compatibility/spec.md) (constraint "the eligibility feature set
is closed: no media and no approvals member") and HMP v1 §7b only after root freezes it.

Base: HMP `4d6863e` (minimum-version policy, no approval lane). Source of the approval lane:
the reviewed draft line ending at `1bcb586` (runtime equal to `f584b91`). Hermes source references:
release `v2026.9.24` (`f97608f1`), development builds `8afaab37`, `ca705dbf` and `ac0cfa7d`.

## Summary

An owner who pairs their phone, lists it as an approval owner and enables guarded sends can answer
Hermes's own dangerous-command approvals (once, session, always, deny) and Phone chat clarify
questions from the phone. HMP attempts the feature on every Hermes at or above its minimum version,
including unlisted and development builds. It closes the feature only when a required Hermes API is
actually missing or a security check fails, and it reports an actual failure with a compatibility
warning and a user-reviewed GitHub issue draft. No exact build list, fingerprint or process latch
admits or refuses approvals.

## User stories and acceptance scenarios

1. As the owner, I can answer a Bot Chat approval from my approval-owner phone.
   - Given Hermes emits `approval.request` on the session stream HMP opened for my send, when I
     choose an offered answer, then HMP forwards exactly `{choice, request_id}` to
     `/v1/runs/{stored run_id}/approval` with that profile's scoped key and reports `applied:true`
     only when Hermes returns `resolved > 0`.
2. As the owner on a Hermes whose session stream has no approval notifier (for example release
   `v2026.9.24`), Bot Chat sends still work; no card is invented; Hermes keeps its own fail-closed
   behavior. Phone chat approvals still work when their helpers exist.
3. As the owner on a newer or development Hermes not sampled by HMP, approvals are attempted.
   No warning appears unless something actually fails.
4. As an operator whose Hermes lacks a required helper, `hermes hmp compat` names the failed
   feature with fixed reason and HMP dependency labels, and `--issue-draft` produces a reviewable
   draft. Nothing is submitted automatically.
5. As a non-owner device, a controls-only device, or a host-denied device, I receive `404` on every
   approval route and never see `open_requests`.

## Requirements

### Availability (replaces the legacy exact approval gate)

- R1. Two eligibility members are added: `approvals` (Bot Chat approval lane: stream binding, AP-3
  and AP-4 for `bot_chat` rows) and `phone_chat` (AP-6, Phone-chat approval and clarify rows, AP-4
  for `phone_chat` rows). Both require read and send availability. (Two members, frozen D3.)
- R2. Floor: both use Hermes `0.21.5` / `2026.9.24` (frozen D4). A version that declares itself
  below the floor is refused for these members without importing their helpers. Unknown, placeholder,
  unlisted, newer and development versions are attempted.
- R3. `phone_chat` probes only what HMP calls in process: `tools.approval.resolve_gateway_approval`
  (named `request_id` and `resolve_all`), `tools.approval.list_gateway_approvals`,
  `tools.clarify_gateway.resolve_gateway_clarify`, `mark_awaiting_text`, `get_clarify_timeout`,
  `tools.approval_context._get_approval_timeout`, the base adapter's `_send_exec_approval_prompt`
  and `send_clarify` hooks, and the `MessageEvent.allow_gateway_control` dataclass field. A missing
  field or a `**kwargs`-only resolver is missing. `retire_clarify_card` is deliberately not probed:
  source inspection of `f97608f1`, `8afaab37` and `ac0cfa7d` shows it is not defined on
  `BasePlatformAdapter` at all. Hermes finds it with `getattr(type(adapter), ...)` on the adapter's
  own class, so a base-class probe would close `phone_chat` on every build. (Correction to the
  architecture report, section 4.1.)
- R4. `approvals` adds no static Hermes dependency beyond send. The session-stream approval hook
  (`APIServerAdapter._register_session_stream_approval` on sampled builds) is reported as a neutral
  diagnostic fact and in issue drafts. It never gates, and it never establishes a release minimum.
- R5. No runtime path reads `approval_supported_builds.json`, `direct_send_supported_builds.json`, a
  source fingerprint, a Git SHA or a process latch for approvals. Availability is computed once when
  the listener opens, like spec 013.

### Authority, fences and lifecycle (unchanged from the reviewed lane unless stated)

- R6. Route order per request: bearer; approval owner (exact `owner_device_ids` entry AND no explicit
  host denial; controls grant alone never qualifies); per-device read/action bucket; per-bot
  authorization; `direct_send.enabled` AND send available; member availability; profile endpoint
  (loopback literal and the profile's own scoped key). Any failure returns before endpoint
  resolution, listing, resolver or delivery.
- R7. Rows are process memory keyed `(iid, user_id, profile, request_id)`; Bot Chat rows store the
  `run_id` from `run.started`; Phone rows store the server-built session key. The client never
  supplies `run_id`, session key, `all` or `resolve_all`. Unknown or another user's ID is `404`.
  Bot Chat rows are answered only through Hermes's native run-approval route, so Hermes's own
  key, room-grant and run-ownership checks apply; HMP never substitutes the in-process resolver.
- R8. Fresh authoritative reads: owner, denial, flag and bot authorization are read live per request;
  Phone rows reconcile with `list_gateway_approvals` on list and outbound notice; Bot Chat answers are
  decided by Hermes (`409 approval_not_pending|approval_not_active` and `404 run_not_found` mark the
  row stale). Expiry is a display hint plus 30 s grace; Hermes's own wait decides.
- R9. Generation fence: each listener open creates a new prompt generation; rows and bound streams
  of an older generation are never listed or answerable. A gateway process restart drops all rows.
- R10. Binding fence (frozen D6): after the `phone_chat` probe passes, HMP captures strong references to
  the Hermes callables it actually calls for `phone_chat`. If a later use finds a different object bound
  in the module, HMP closes the local Phone-chat generation: its rows are expired locally, `phone_chat`
  stays closed until the next listener open, and a fixed outcome is logged. This is an object-identity
  check with no disk or manifest path. It is not authenticity, loaded-bytecode proof or attestation.
  Closure invalidates HMP's local observations only; it does not establish that Hermes's pending request
  expired, so it never reports native expiry or `notPending`. Bot Chat `approvals` eligibility stays
  independent. A stale stream bound to the closed generation cannot reinsert rows into a new one.
- R11. Transport (frozen D2b): HMP opens the session stream only for a send whose device is an
  effective approval owner for that bot; all other sends keep the existing synchronous route
  unchanged. The choice is made before the send; HMP never falls back after a stream failure.
- R12. Bounds stay as reviewed: separate 60/min/device read and action buckets; SSE 64 KiB frame,
  128 KiB buffer, 24 h total, 90 s idle; approval POST 15/10 s with a 64 KiB body; 256/60 s/8 KiB
  observations; blocking Hermes helpers off the event loop.
- R13. Logs carry only fixed outcomes and 8-character ID prefixes (SEC-4).

### Operation-bound failure classification and reporting

- R14. Native answer results. Only a bounded, parsed native JSON error code makes a row stale:
  `409 approval_not_active`, `409 approval_not_pending` and `404 run_not_found`. An unknown `409` code,
  a non-JSON or malformed `404`, `401`, `403`, `3xx`, `5xx`, a timeout, an oversized body and every
  other error are `api_server_unavailable` and leave the observation open. A `200` proves application
  only when its bounded JSON body has a non-bool integer `resolved` greater than zero; a missing,
  non-integer, boolean or non-positive `resolved`, or a malformed `200`, is `api_server_unavailable`.
  Response text is never echoed or logged. There is no transport retry and no fallback.
- R15. A helper raising `ImportError`, `AttributeError` or `TypeError` at use time is an actual
  capability failure: fixed log outcome, `503` without `applied`, never a fabricated success.
- R16. `--issue-draft` accepts `--feature approvals|phone_chat` with `write_gate_closed` or
  `api_server_unavailable`, labelled operator-reported. Drafts may include the boolean diagnostic
  from R4. Permission and routing codes stay their own reason (spec 013).

## Clarifications

- Q: Does a missing session-stream hook disable approvals? A: No. It is a diagnostic. Hermes either
  emits `approval.request` or keeps its own fail-closed behavior.
- Q: Does the reviewed exact-build receipt still mean anything? A: Yes, as sampled evidence for
  `8afaab37` with the earlier runtime. It is not a runtime prerequisite and does not cover the
  converted runtime.
- Q: Must every future Hermes be requalified? A: No. Candidate evidence is sampled on existing
  fixtures; later builds are attempted.

## Out of scope

Push/urgent notifications, media and attachments, the Phone chat composer UI, new-bot routing
(own lane, D5: no `routes.py`, config writer or PyYAML dependency here), the `owner_package` manifest editor, a runtime failure ledger (spec 013 F1), new wire error codes, Hermes core changes,
automatic issue submission, live host changes, and the pending SD3/SD5 human fixes.

## Residuals recorded by root

- D8 coupling: a device in `owner_device_ids` with no host controls decision also receives jobs/model
  controls under the legacy allowlist (`request_ctx.is_owner_device`). The runbook and a read-only
  `setup check` notice describe it. No decision, allowlist entry or authority is changed, and no
  separation-of-privilege redesign is part of this conversion. A host denial still removes approval
  ownership.
- Future Hermes control semantics (`allow_gateway_control`) are not statically detectable.
- Sampled fixture evidence is neither a runtime allowlist nor a required test of future builds.

## Implementation notes (worker, not review)

- Reason code `requires_send` is added to the internal `Unavailable` enum for the two new members
  when send is unavailable; it is a fixed non-failure reason and drafts nothing.
- The stream-hook diagnostic is a bounded file read of `gateway/platforms/api_server.py` (no import,
  no gating), carried as evidence on `Eligibility`.
- D8 `setup check` notice: the CLI cannot read the host config allowlist (existing documented limit),
  so the read-only notice counts active devices with no recorded controls decision from the store and
  prints a fixed sentence when there is at least one. It names no device and changes nothing.

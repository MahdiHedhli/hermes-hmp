# F3 approvals and Phone chat — security revision

Status: remediation implemented for review; **not qualified for release or enablement**.
The direct-send fingerprint remains stale. No live configuration is changed by this patch.
Contract: HMP v1.3, `docs/architecture/contracts/HMP_V1.md` §7b, under OD-F16.
Hermes source authority: commit `8afaab3703e336d72a72c812dd2dd249f04f166a`.
This revision supersedes the rejected proposal's ownership, gateway-control, expiry,
observation and fallback rules. It implements server behavior only.

## Ownership and gates

An **owner device** is an active paired device whose exact `device_id` the host operator puts
in `gateway.platforms.hmp.extra.owner_device_ids`, a list of strings. Missing, malformed or
empty configuration grants no device ownership. Pairing and per-bot authorization alone do
not grant ownership. Nothing in an HTTP body can add a device to this list.

The list belongs to the HMP listener configuration. The same device may access only profiles
for which its paired `user_id` is bot-authorized. Re-pairing that creates a new device ID
requires an explicit new entry. Revocation still invalidates the bearer. The list is read from
the live adapter config on each request; loading a config-file edit into that object follows
Hermes's normal reload/restart behavior.

All three F3 routes require, in order: authenticated device, owner-device membership, the
F3 per-device rate limit, per-bot authorization, and the direct-send gate.
Prompt reads have a 60/minute/device bucket; answers and Phone sends share a separate
60/minute/device action bucket. Both span all profiles and request IDs and reject excess
requests with `429 rate_limited` before authorization/body parsing/resolution/delivery.
The foreground phone cadence is 3–15 seconds (4–20 periodic reads/minute). Even one immediate
refresh after every answer at the fastest cadence totals 40 reads/minute, leaving 20 for
opening/resuming the view and retries. Answers never compete with those reads; an answer and
a Phone send every three seconds total 40 actions/minute. This covers sustained client cadence
across fixed-window boundaries without granting unbounded reads or mutations. Malicious or
broken clients still hit their own device's limit. Tests use three-second prompt polling and
fail immediately on HTTP errors instead of disguising 429 as an empty prompt list.
A non-owner receives `404 not_found`, including a paired, authorized device sharing the owner's
`user_id`. `direct_send.enabled` must be explicitly true even if the base write gate is OPEN.
The dependency fingerprint/probe and loopback endpoint checks remain in force. No gate failure
may reach a resolver or deliver a Phone-chat event.

Rows remain keyed by `(iid, user_id, profile, request_id)`. Multiple explicitly owner-marked
devices for the same user can answer the same row, under one serialized, idempotent decision.
Ownership is not implied by originating a turn. A non-owner snapshot omits `open_requests`;
that field also disappears when the flag is off. Ordinary transcript reads retain their
existing authorization rules.

**Owner decision required before enablement:** accept this device allowlist definition and
provision the owner's actual device IDs locally. No device is automatically grandfathered in.

## Two prompt producers

### Bot Chat

An already-guarded DS-4 send uses only `POST {prefix}/api/sessions/{tip}/chat/stream`.
There is no synchronous fallback. HMP stores `approval.request` immediately, bound to the
`run_id` established by `run.started`. Any later supplied `run_id` must match. An approval
without that binding is rejected. Answers POST only the stored run/request IDs and the selected
stored choice to `{prefix}/v1/runs/{run_id}/approval`; never `all` or `resolve_all`.

The consumer outlives the phone HTTP request. At `ADMISSION_WAIT_S`, the client receives the
existing accepted/queued/submitted vocabulary. A stream failure finalizes the cmid as unknown,
without automatic retry. A terminal/disconnected stream retires its open prompt observations.
Desktop mailbox delivery emits no approval request in the pinned build; its `desktop_held`
marker lasts only while the stream is open. It is not proof an approval is pending on Desktop.

**Round 5 source correction:** the extracted stock-base (`04fa849e`) and experimental
(`7e8c8f07`) session-chat routes do **not** register a gateway approval notifier, populate
`_run_approval_sessions`, or emit `approval.request`. Those behaviors exist only in
`/v1/runs`. A flagged terminal call returns nonblocking `pending_approval`, then the turn
can end without a card. The consumer above describes the required contract, not a capability
these builds provide. T7 remains a mandatory positive qualification test; neither build may
qualify until its actual session-chat route provides the complete approval lifecycle. A fixture
config change, synthetic card, alternate route, or accepting an empty prompt list is not a fix.

The session-chat agent has no clarify callback. Its `execute_code` path is unattended and
never cards; the normal dangerous-terminal-command path can emit approvals. These existing
Hermes limitations remain visible product limitations.

### Phone chat

Phone chat uses the existing user's `default` HMP conversation and a server-derived session
key. Every inbound Phone event has `internal=False` and **`allow_gateway_control=False`**.
The optional `defer_policy` is `reject` when the pinned event shape supports it.
On that shape, `_gateway_accepted` records task scheduling, not durable admission. HMP waits
up to five seconds for `admission_ticket.reported`: only `admitted` yields `202 submitted`, a
`refused_*` result refuses the send, and a missing outcome yields a durable `200 unknown` for
that cmid. A replay never starts another turn. Stock builds without admission tickets retain
their synchronous acceptance behavior.

Source evidence at the pin:

- `gateway/platforms/event.py:106-112`: a control-disabled event is not a slash command.
- `gateway/platforms/base.py:3971-3972`: plaintext command coercion is control-gated.
- `gateway/platforms/base.py:3996-4040`: busy slash dispatch depends on `get_command()`, and
  clarify text interception checks `allow_gateway_control`.
- `gateway/run_busy.py:499-551`, especially line 529: bare yes/always/session routing is
  control-gated. A waiter appearing after HMP's preflight therefore cannot self-approve.
- `gateway/platforms/base.py:2811-2825`: outbound `send_exec_approval` constructs the prompt
  and calls `_send_exec_approval_prompt` independently of the inbound event's control flag.
- `gateway/run_turn_runner.py:1474-1550`: the native prompt hook and plaintext fallback are
  outbound delivery; disabling inbound control does not disable prompt delivery.

Only `POST …/prompts/{request_id}` answers approval or clarify. Phone composer text never
answers either. While a known wait is pending, sends return `409 stale`, `applied:false`.
This preflight is a UX refusal, not the security boundary; the event flag closes the race.
`/approve`, `/deny`, `/stop`, other slash commands and bare approval words carry no gateway
control authority. They may be ordinary model input when the conversation is otherwise idle.

### Ambiguous binding and recovery

`ExecApprovalPrompt` lacks a request ID. The adapter reads `list_gateway_approvals` with the
stored Phone session key. One unmatched exact command match gets the prompt's offered choices.
Multiple matches get a **deny-only recovery card per known ID**. If redaction prevents an exact
match, unmatched IDs in that same session also get deny-only recovery, with an empty command
and explicit unbound-approval copy; HMP does not expose the queue's raw command or guess which
operation should be allowed. Recovery is only offered if the native prompt offered deny.

The owner can release each wait through the normal ID-bound answer route. HMP never sends an
automatic denial and never enables chat approval. When no valid pending ID can be obtained,
HMP fails closed and Hermes's own finite approval timeout releases the wait; there is no HMP
permanent fallback lock or FIFO answer path. A later outbound notice/poll reconciles vanished
waiters. Plaintext fallback is an unanswerable, bounded observation, not a card.

## Prompt lifecycle and expiry

`bridge.approval_timeout_s(profile)` and `bridge.clarify_timeout_s(profile)` enter that exact
profile's runtime scope before calling Hermes's config helpers. They run in worker threads.
The stream producer and both adapter hooks pass the target profile explicitly.

| Kind | Config | Display hint |
|---|---|---|
| Approval | `approvals.timeout`, default 300, Hermes's platform-safe clamp | `observed_at + max(0, timeout)`; nonpositive means immediate timeout, not unlimited |
| Clarify | legacy `clarify.timeout`, otherwise `agent.clarify_timeout`, default 3600 | `observed_at + timeout`; nonpositive means null/unlimited |

Hermes owns the actual wait. There is no API expiry event at this pin. A 409
`approval_not_pending`, a resolver reporting no waiter, a vanished queue entry observed on
poll/outbound notice, clarify retirement, or termination of the bound stream expires HMP's
row. Outbound notice text is never parsed as an answer or as authoritative state.

As a cleanup backstop, an open row expires once the hint is exceeded by **more than 30 seconds**.
During that grace period Hermes still decides. Expiry only removes HMP's ability to answer;
it does not resolve or extend Hermes's wait. List and answer paths enforce it independently.
An expired answer always returns `409 stale`, `applied:false`, even without a cached response.

Settled/expired rows retain replay evidence for 24 hours. Purge removes both row and lock;
active and queued answerers pin the pair with a reference count. Unknown IDs allocate neither.
The listener watchdog purges periodically, including when nobody is polling. Accepted replay
and changed-answer conflict retain the existing AP-5 behavior. Chosen answers are never logged;
the sole successful answer outcome is `resolved` (SEC-4).

## Observation and network bounds

Phone observations have a global 256-entry cap, 60-second TTL and 8 KiB text limit. Durable
role/text matches discard corresponding observations permanently. Observations have no stable
Hermes message ID or lineage, so they are **never appended to snapshot/history message arrays**.
Those arrays contain only durable Hermes rows. This prevents an old observation from reappearing
when the durable fetch window moves, or from corrupting message cursors. Replies become visible
when Hermes persists them; interim notices may not appear in durable history.

Loopback clients keep `trust_env=False`, literal `127.0.0.1`/`::1` only, pinned resolution and
`allow_redirects=False`. Approval POST: 15-second total, 10-second read timeout. SSE: 24-hour
total, 90-second idle/read timeout (Hermes emits keepalives). These are transport resource
ceilings, not approval timers; a longer configured wait can outlast the stream ceiling.

SSE requires `text/event-stream`, handles LF and CRLF across arbitrary chunk boundaries,
limits each frame (and therefore every field) to 64 KiB and buffered input to 128 KiB.
Approval response bodies are limited to 64 KiB. Frame/identity failures close the consume
without logging body content. Connect deadlines remain unchanged.

## Finding → fix → regression test

Review A is `agy-flash-3.8`; review B is `daybreak-blue`. Full private reports are not copied
into this public repository. Test names below are in `server/tests/unit/`.

| Finding | Fix | Regression test |
|---|---|---|
| B1 BLOCKER: paired device treated as owner | Explicit device allowlist on every F3 route; snapshot prompt filtering | `test_non_owner_device_cannot_use_any_prompt_route`; `test_owner_devices_share_one_answer_and_revocation_is_live`; `test_snapshot_cannot_bypass_prompt_ownership` |
| B2 BLOCKER: flag bypass under OPEN | Unconditional false-flag refusal | `test_flag_off_even_with_full_guarantees` |
| B3 BLOCKER: gateway control/self-approval race | Control-disabled events; prompt route exclusively answers | `test_phone_event_cannot_control_gateway_when_waiter_appears_during_delivery` (six inputs); `test_phone_message_while_clarify_is_pending_is_not_a_new_turn` |
| A2 BLOCKER: stale prompts remain answerable | Profile hints, grace, authoritative retirement, purge | `test_expiry_hides_refuses_and_purges_lock`; `test_retired_clarify_is_never_forwarded`; `test_expiry_hint_has_grace_but_authoritative_gone_expires_immediately`; `test_prompt_timeout_hints_use_target_profile_a_b_a`; `test_profile_timeout_is_used_by_both_adapter_hooks`; `test_waiting_answer_rechecks_expiry_after_lock` |
| A1 BLOCKER: unbounded observations/corrupt history | TTL/global cap/size limit; durable discard; no snapshot injection | `test_observations_have_global_cap_ttl_and_no_snapshot_injection` |
| A3, B4 SHOULD-FIX: unbounded loopback HTTP | Total/read deadlines, no redirects, bounded response, exact content type | `test_clients_set_finite_timeouts_and_disable_redirects`; `test_http_response_policy_without_network`; `test_http_redirects_and_content_type`; `test_approval_response_body_is_bounded` |
| A4, B4 SHOULD-FIX: SSE framing/resources/binding | CRLF-safe bounded parser; run-ID validation | `test_sse_crlf_split_and_mismatched_run`; `test_sse_oversized_frame_rejected` |
| B5 SHOULD-FIX, A6 NIT: spam/unknown locks/leaks | Separate bounded read/action buckets per device, no unknown allocation, pinned lock cleanup | `test_prompt_buckets_are_bounded_separate_and_per_device`; `test_phone_polling_and_answers_across_windows`; `test_unknown_ids_allocate_nothing`; `test_purge_cannot_replace_a_lock_with_waiting_answerers` |
| A5 SHOULD-FIX: plaintext fallback deadlock | ID-bound deny-only recovery; no text approval | `test_ambiguous_binding_has_deny_only_recovery` |
| B6 SHOULD-FIX: chosen answer in logs | `outcome=resolved` only | `test_logs_do_not_contain_the_command` |

## Compatibility, verification and owner decisions

Only `bridge.py` reaches the approval internals. Existing documented plugin API exceptions
remain unchanged. No request-time relative imports, core patches, private clarify-index reads,
new Hermes dependencies or fingerprint requalification are introduced. No code writes to the
installed Hermes tree or live home.

Before enablement the owner must accept the allowlist definition, prompt-only clarify UX,
deny-only recovery, durable-only snapshot display, and the stated transport resource ceilings.
The fixture suite now explicitly marks its paired reference device as owner through isolated
fixture config. Its real gateway/PTY execution and all environment-limited checks must pass
before release. See `REVIEW_STATUS.md` for the actual run results; unit fakes are not T7/T8 proof.

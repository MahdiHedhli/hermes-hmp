# Approvals review status

**Security remediation implemented; release remains blocked on validation and owner review.**
Do not merge, release or enable this branch as a qualified build. Both independent reviews
rejected the original design. This revision addresses every BLOCKER and SHOULD-FIX, plus the
lock-leak NIT, with regression coverage. The review reports themselves stay outside this public
repository. The installed Hermes tree was read only at commit
`8afaab3703e336d72a72c812dd2dd249f04f166a`.

## Finding → fix → test

Review A: `agy-flash-3.8`. Review B: `daybreak-blue`.
The full design and pinned source citations are in [DESIGN.md](DESIGN.md).

| Finding | Fix | Regression test |
|---|---|---|
| B1 BLOCKER: paired device treated as owner | Explicit device allowlist on every F3 route; snapshot prompt filtering | `test_non_owner_device_cannot_use_any_prompt_route`; `test_owner_devices_share_one_answer_and_revocation_is_live`; `test_snapshot_cannot_bypass_prompt_ownership` |
| B2 BLOCKER: flag bypass under OPEN | Unconditional false-flag refusal | `test_flag_off_even_with_full_guarantees` |
| B3 BLOCKER: gateway control/self-approval race | Control-disabled events; prompt route exclusively answers | `test_phone_event_cannot_control_gateway_when_waiter_appears_during_delivery` (six inputs); `test_phone_message_while_clarify_is_pending_is_not_a_new_turn` |
| A2 BLOCKER: stale prompts remain answerable | Profile hints, grace, authoritative retirement, purge | `test_expiry_hides_refuses_and_purges_lock`; `test_retired_clarify_is_never_forwarded`; `test_expiry_hint_has_grace_but_authoritative_gone_expires_immediately`; `test_prompt_timeout_hints_use_target_profile_a_b_a`; `test_profile_timeout_is_used_by_both_adapter_hooks`; `test_waiting_answer_rechecks_expiry_after_lock` |
| A1 BLOCKER: unbounded observations/corrupt history | TTL/global cap/size limit; durable discard; no snapshot injection | `test_observations_have_global_cap_ttl_and_no_snapshot_injection` |
| A3, B4 SHOULD-FIX: unbounded loopback HTTP | Total/read deadlines, no redirects, bounded response, exact content type | `test_clients_set_finite_timeouts_and_disable_redirects`; `test_http_response_policy_without_network`; `test_http_redirects_and_content_type`; `test_approval_response_body_is_bounded` |
| A4, B4 SHOULD-FIX: SSE framing/resources/binding | CRLF-safe bounded parser; run-ID validation | `test_sse_crlf_split_and_mismatched_run`; `test_sse_oversized_frame_rejected` |
| B5 SHOULD-FIX, A6 NIT: spam/unknown locks/leaks | Shared per-device limiter, no unknown allocation, pinned lock cleanup | `test_prompt_rate_limit_shared_across_routes`; `test_unknown_ids_allocate_nothing`; `test_purge_cannot_replace_a_lock_with_waiting_answerers` |
| A5 SHOULD-FIX: plaintext fallback deadlock | ID-bound deny-only recovery; no text approval | `test_ambiguous_binding_has_deny_only_recovery` |
| B6 SHOULD-FIX: chosen answer in logs | `outcome=resolved` only | `test_logs_do_not_contain_the_command` |


## Validation evidence

The regression suite was run against a temporary export of the original branch `0c17860` before
remediation: **35 failed, 78 passed, 2 skipped, 4 deselected**. The test-only injected clock was
adapted to the pre-fix constructor; no behavioral assertions were relaxed. All 35 failures pass
on the revised code. Additional coverage verifies expiry after lock waiting, snapshot ownership
and off-loop authorization.

- Ruff 0.16.9, full `server tools` scope: PASS.
- `tools/ci/check_plugin_surface.py`: PASS. No added Hermes import surface or request-time
  relative imports.
- `tools/ci/scan_logs.py`: PASS on the focused tests' captured log. The default scan also ran,
  and reported no default captured artifacts.
- `tools/ci/scan_private.py`: PASS, zero baseline. The new test file was also scanned explicitly.
- Focused approvals/security/bridge run: **113 passed, 2 skipped, 4 deselected**.
- Full CI unit/tool command: **1071 passed, 146 failed, 10 skipped**
  (142 socket-permission failures, 3 dependent listener startup failures, 1 protected-cache failure). Failures are environmental, not waived:
  socket binding is denied by this sandbox; dependent listener tests time out; the offline
  wheel test cannot initialize the protected default uv cache. No skips were added for these
  failures, and no assertion was weakened to make them green.
- Approvals fixture integration was invoked: **15 skipped**, all explicitly reporting missing
  `HMP_HERMES_BUILDS_DIR` with extracted builds. PTY allocation was tested and **is available**;
  it is not the blocker in this session. Real gateway execution also requires loopback sockets
  and a human-qualified fingerprint. Collection/skipping is not T7/T8 evidence.

Re-run the full CI command and T7/T8 in a socket-capable environment with extracted qualified
fixture builds before release. The fixture explicitly adds only its paired reference device
ID to isolated owner config; pairing itself does not grant ownership.

## Owner decisions before enablement

1. Accept `gateway.platforms.hmp.extra.owner_device_ids` as the owner-device definition: exact
   paired IDs, default empty, host-managed, in addition to existing bot authorization.
2. Accept prompt-route-only clarify answers, deny-only ambiguous-binding recovery cards,
   and snapshots that show only durable transcript rows (no provisional cursor IDs).
3. Accept transport ceilings: POST total/read 15/10 seconds; SSE total/read 24 hours/90 seconds;
   frames/responses 64 KiB, SSE buffer 128 KiB; display-expiry grace 30 seconds.

No live owner configuration was edited. The original F3 expansion of `bridge_files` remains
intentionally unqualified; the fingerprint was not changed. Enabling the feature still requires
human requalification. These pending validation and owner decisions are tracked here as open
release blockers, not accepted security risk.

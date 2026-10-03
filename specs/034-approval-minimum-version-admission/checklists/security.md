# Security checklist (reviewer-owned; the implementation worker ticks no box)

Each negative case needs a test at the actual route or bridge boundary.

- [ ] N1 Paired, bot-authorized non-owner (same `user_id`): `404` on AP-3/AP-4/AP-6; no `open_requests`.
- [ ] N2 Controls grant without allowlist entry: `404`.
- [ ] N3 Allowlisted but host-denied: `404`; denial recorded while a card is open closes the next answer.
- [ ] N4 Flag off: `503 write_gate_closed`; no endpoint, listing, resolver or delivery call.
- [ ] N5 Bot not authorized: ERR-3 before any gate work.
- [ ] N6 Same device, other profile, exact ID: `404`; Hermes run ownership also refuses.
- [ ] N7 Unknown or guessed ID: `404`; allocates no row or lock.
- [ ] N8 Answer after Hermes timeout: native `409 approval_not_pending|approval_not_active` or JSON `404 run_not_found`: `409 stale`, `applied:false`; row expired. Unknown `409` code stays open.
- [ ] N9 Same-body replay returns stored result; different body `409 idempotency_conflict`.
- [ ] N10 Choice not offered: `409 invalid_choice`; no Hermes call.
- [ ] N11 `all`/`resolve_all` in body: `400`; never forwarded.
- [ ] N12 Phone text, bare yes, `/approve` while pending: `409 stale`; no `handle_message`.
- [ ] N13 `MessageEvent` without `allow_gateway_control`: `phone_chat` unavailable; delivery also raises.
- [ ] N14 Resolver without named `request_id`: `phone_chat` unavailable; never FIFO.
- [ ] N15 `approval.request` unbound or with mismatched `run_id`: no row; stream error.
- [ ] N16 Oversized SSE frame or buffer: closed, `unknown`, no retry.
- [ ] N17 Non-literal loopback, redirect, proxy environment: refused.
- [ ] N18 Native `401`/`403`: `api_server_unavailable`, row stays open, fixed log.
- [ ] N19 Non-JSON or malformed `404`, unknown `409` and malformed or non-positive `200` are `api_server_unavailable` with the row open; only JSON `run_not_found` is stale.
- [ ] N20 Listener reconnect: older generation rows never listed or answerable.
- [ ] N21 Process restart mid-wait: no row; answer `404`; nothing applied.
- [ ] N22 Rebound helper: local generation closed, rows expired locally with no native-expiry claim; `phone_chat` closed until reopen; `approvals` unaffected; a stale stream cannot reinsert rows.
- [ ] N23 Notifier-absent build: send succeeds, no fabricated card, no warning.
- [ ] N24 Unknown or newer version with renamed hook: attempted; no warning without failure.
- [ ] N25 Below floor: both members refused; no helper import.
- [ ] N26 Non-owner send uses the synchronous route; outcome unchanged from `4d6863e`.
- [ ] N27 Desktop-held mailbox: no phone card; marker only while the consume is open.
- [ ] N28 Read and action buckets separate; `429` before authorization or body parsing.
- [ ] N29 Logs never contain command, description, question, choice, text or keys.
- [ ] N30 Editing or deleting any `*_supported_builds.json` changes no availability.
- [ ] N31 Owner removed from allowlist while a card is open: next answer `404`.
- [ ] N32 Revoked device: `401`.
- [ ] N33 Constructor defaults for the new availability fields are False.
- [ ] N34 SD3 and SD5 remain open, unedited and unwaived.

## Implementation coverage map (worker's pointer for the reviewer; no box above is ticked)

Tests are under `server/tests/unit/` and run in the affected suite. They were mutation-checked: each
named protection was broken once and a test failed.

| N | Test(s) |
|---|---|
| N1, N2 | `test_approval_route_gates.py::test_n1_n2_*`; `test_approval_security.py::test_non_owner_device_*`, `test_controls_grant_alone_*` |
| N3, N31, N32 | `test_approval_route_gates.py::test_n3_*`, `test_n31_*`, `test_n32_*`; `test_approval_security.py::test_controls_denial_*` |
| N4, N5 | `test_approval_route_gates.py::test_n4_*`, `test_n5_*`, `test_both_members_closed_*` |
| N6, N7 | `test_approval_route_gates.py::test_n6_*`, `test_n7_*`; `test_approval_security.py::test_unknown_ids_allocate_nothing` |
| N8, N18, N19 | `test_approval_native_answer.py` (classification table, request function, route) |
| N9-N12 | `test_approvals.py` (replay, conflict, choice not offered, `all`/`resolve_all`, Phone text) |
| N13, N14 | `test_approval_availability.py::test_n13_*`, `test_n14_*`; `test_bridge.py::test_n13_*` |
| N15-N17 | `test_approvals.py::test_stream_*`; `test_approval_security.py::test_sse_*`, `test_http_*` |
| N20-N22 | `test_approval_fences.py`; `test_bridge.py` binding tests |
| N23-N25 | `test_approval_availability.py::test_n24_*`, `test_n25_*`, `test_n23_*`; `test_approval_use_time_failures.py::test_n23_*`; `test_issue_draft.py` member tests |
| N26, N27 | `test_approval_transport.py`; `test_approvals.py::test_mailbox_keepalive_*`, `test_desktop_held_*` |
| N28, N29 | `test_approval_security.py::test_prompt_buckets_*`; `test_approval_use_time_failures.py::test_n29_*` |
| N30 | `test_approval_availability.py::test_n30_*`, `test_no_manifest_*`; `test_approval_merge_regressions.py::test_h4_*` |
| N33 | `test_approval_availability.py::test_n33_*` |
| N34 | Not a test: `git diff 4d6863e` shows no change to `devices list` or any key-length code. |
| Merge hazards H1-H6 | `test_approval_merge_regressions.py` |

Native fixture cases (`server/tests/integration/test_approvals_fixture.py`) are written but have not
been run by the worker. The real-build capability mutants are in `tools/compat/phone_chat_probe.py`
and have not been run either.

# F3 Approvals — design

| | |
|---|---|
| Status | Design only. No contract edit, no code, no commit in this document's change. |
| Owner | OD-F16 (`docs/architecture/R0_OWNER_DECISIONS.md`, 2026-09-28): implement both paths below. |
| Contract | Additive **HMP v1.3** on `docs/architecture/contracts/HMP_V1.md` (current revision 1.2, §7a). Earlier 1.x clients ignore the new routes and fields (V-3, V-4). |
| Builds on | F2 direct send (`specs/002-send-messages/DESIGN.md` v5, DS-1..DS-10) and F1 pairing, reads, and the inert P6 trigger. |
| Hermes pin | `~/.hermes/hermes-agent` `8afaab3703e336d72a72c812dd2dd249f04f166a`. Every Hermes line below is from that tree. |
| Plugin pin | `server/hmp_plugin/` as integrated with F1 reads and F2 direct send (the implementation this design extends). |

This document is the spec an implementer can build from. It does not edit `HMP_V1.md`; the v1.3 amendment is task T0.

## Owner decision

OD-F16, recorded verbatim in substance: **"Both."**

1. **Bot Chat stays the default.** When Hermes Desktop is not holding that bot's canonical Bot Chat live, phone sends use `api_server`'s **streaming** session route so tool approvals (`once` / `session` / `always` / `deny`) reach the phone and are answered from it. When Desktop holds the Bot Chat live, approvals stay on Desktop. The phone shows **Waiting for approval on your Hermes Desktop**.
2. **Optional per-bot Phone chat** goes through HMP's own messaging path, the way Discord and WhatsApp do: a normal platform turn, with approval buttons and clarify (choices, plus Other). It is a separate conversation from the Bot Chat. This partly reopens OD-F13 for that optional chat only.
3. **Both paths move to Nous's session-chat approval events once those exist.** The owner's intent: use these paths so the app has the feature now, and change when upstream does.

OD-F14's "show it, answer elsewhere" (contract DS-5) remains the rule when the owner-only send flag is off. OD-F16 replaces it, for that flag's scope only, with the two paths above.

## Key decisions

| ID | Decision | Why |
|---|---|---|
| KD-1 | Bot Chat sends that already pass DS-2/DS-4 call `POST …/chat/stream` on every such send. Hermes's own handler decides mailbox vs local run. | The stream route checks the live Desktop owner before it registers an approval callback (`api_server.py:3563-3565`, then `3683-3693`). A pre-check in HMP would race that decision. |
| KD-2 | HMP holds the SSE socket until the stream ends. The phone's send still returns at `ADMISSION_WAIT_S` (5s). | Disconnecting a locally running stream interrupts the turn (`api_server.py:3670-3673`). |
| KD-3 | There is no fallback from the stream route to sync `POST …/chat`. | The sync handler's `_run_agent` call does not pass an approval callback (`api_server.py:3343-3352`, `3529`). A fallback would recreate the unanswerable turn. |
| KD-4 | The phone never receives `run_id` or a session key. HMP stores them on the prompt row and answers Hermes with the stored `run_id` plus the Hermes `request_id`. | ADR-0006 binds an answer to the request. A client-supplied session key would let one device resolve another session's queue (`tools/approval.py:148-156` matches only `session_key` + optional `request_id`). |
| KD-5 | Answers never use FIFO or `resolve_all`. | `resolve_gateway_approval` without `request_id` pops the oldest entry (`tools/approval.py:157-161`). Discord's buttons do that (`plugins/platforms/discord/adapter.py:6364`). HMP does not. |
| KD-6 | Phone chat reuses the F1 `default` conversation (same `chat_id`, same session key). It does not reopen SUB-1. | OD-F13 retired that conversation for *sends into Bot Chat*. OD-F16 revives it as its own optional thread. SUB-1 stays gated on GU-4 `"open"`, which no supported build advertises. |
| KD-7 | Both paths sit behind `gateway.platforms.hmp.extra.direct_send` (default false), the same owner-device flag as DS-10. | OD-F15/OD-F14 limit writes to the owner's own paired devices. |
| KD-8 | Prompt rows are process memory. Hermes's queues are too (`tools/approval.py:118-119`, `tools/clarify_gateway.py:32-35`). | A row that survives a gateway restart would offer an answer Hermes can no longer apply. |
| KD-9 | HMP does not add an approval policy of its own. | ADR-0006 and the Authority invariant: if Hermes asks, the phone renders and relays; if Hermes allows, the phone adds nothing. |
| KD-10 | On the Bot Chat stream, clarify is unavailable and `execute_code` does not card. The design says so in the UX and does not invent a callback `api_server` does not set. | See §2.4 and §2.5. |

## 1. What stays as it is

- Pairing, P6 `POST /bots/{p}/authorize`, the inert trigger, roster, SES-1/SES-2, and the DS-1..DS-4 guard (in-process lock, Bot Chat resolution, lease lineage, `expected_head`) are unchanged.
- DS-3 still reserves the cmid **before** the loopback call. A replay of the same `(text, expected_head)` returns the stored outcome and does not open a second stream.
- DS-6's loopback rules stay: literal `127.0.0.1` or `::1`, `trust_env=False`, pinned resolver, per-profile `API_SERVER_KEY`, `401` means the gate is closed, no proxy, no token in the log (SEC-4).
- `adapter.py` still imports only `BasePlatformAdapter`, `SendResult`, and `Platform` at module level. New Hermes calls live in `bridge.py`, imported only after the compat gate, and the adapter reaches them through the object `connect` already builds.
- `open_requests` on the Phone-chat snapshot is filled from the prompt store. Today it is hard-coded empty (`reads.py:419`, `433`).

## 2. Path 1 — Bot Chat via the streaming session route

### 2.1 What the sync route does today

`direct_send.aiohttp_loopback_call` posts `{"message": text}` to `{path_prefix}/api/sessions/{live_tip}/chat` (`direct_send.py:199-213`). That is sync `POST /api/sessions/{session_id}/chat` (`api_server.py:97`, `3509-3529`).

`_prepare_session_chat` builds `run_kwargs` with no approval callback (`api_server.py:3343-3352`). `_handle_session_chat` either hands the turn to a live Desktop mailbox (`3424-3451`) or calls `_run_agent(**run_kwargs)` (`3529`). `_run_agent` registers a notify callback only when the caller passes both `approval_notify_callback` and `approval_session_key` (`4222-4229`). The sync caller passes neither.

Inside a running gateway `HERMES_EXEC_ASK=1` (`gateway/run.py:5797-5798`). `_presence` therefore leaves `is_ask` true for `api_server` on purpose, so `/v1/runs` can bridge approvals (`tools/approval.py:934-948`). With ask set and **no** notify callback, a flagged terminal command does not take `unattended_mode` (`tools/approval.py:1193-1201`) and does not block: it returns `pending_approval` (`850-905`, the `notify_cb is None` branch at `894-905`). The phone cannot answer that. DS-5 told the UI to show it read-only. OD-F16 replaces that for flag-on sends.

### 2.2 The stream route

`POST /api/sessions/{session_id}/chat/stream` (`api_server.py:97`, handler `3555`).

Order inside Hermes:

1. Same prepare as sync (`3560-3561`).
2. **Mailbox first.** `_stream_through_live_bot_chat` (`3471-3507`) calls `_admit_to_live_bot_chat` (`3396-3422`). If this session's compression tip is the canonical Bot Chat and a Desktop owner holds it, the turn is delivered to that owner's mailbox. The SSE body is `run.started`, then either `assistant.completed` + `run.completed` (settled), `run.queued` (still queued/claimed at the budget), or `error`, then `done`. No `approval.request`. A client disconnect on this branch logs and returns (`3505-3507`); it does not interrupt Desktop.
3. **Otherwise this process runs the turn.** It mints `run_id = "run_" + uuid` (`3573`), records the run owner (`3579`), and registers `_register_session_stream_approval` (`3605`, `3683-3693`). The map value is the run id itself: `_run_approval_sessions[run_id] = run_id`. The notify closure redacts the command (`113-126`, `_redact_approval_command`), stamps `choices`, sets status `waiting_for_approval`, and enqueues SSE event `approval.request`.
4. `_run_agent` is called with that callback and `approval_session_key=run_id` (`3615-3619`). The agent thread's platform is `api_server` (`_bind_api_server_session`, `4040-4057`), which is an unattended platform (`tools/approval_context.py:131-145`), so `_is_gateway_approval_context()` is false (`157-174`). Ask mode is still on, so a flagged **terminal** command reaches `_human_decision` (`tools/approval.py:852-870`), finds the notify callback (`541-543`), and blocks in `_await_gateway_decision` (`tools/approval_gateway_wait.py:130-210`).
5. The entry gets `request_id` before notify (`approval_gateway_wait.py:29-32`, notify at `201`). The SSE payload is that dict plus the `_run_event` envelope `{"event","run_id","timestamp",…}` (`api_server_runs.py:176-178`) and `choices` from `_approval_event_choices` (`api_server.py:107-110`): `once`/`deny`, plus `session` and `always` unless smart-deny or the permanent/session flags suppress them.
6. The human answers `POST /v1/runs/{run_id}/approval` (`api_server.py:86`, `api_server_runs.py:238`, handler `1168-1216`). Body `choice` (aliases `approve`/`approved`/`allow` → `once`) and optional `request_id`. Allowed choices `once|session|always|deny`. It looks up `approval_session_key` for that run and calls `resolve_gateway_approval(session_key, choice, resolve_all=…, request_id=…)`. `resolved <= 0` is HTTP 409 `approval_not_pending`. Missing session key is 409 `approval_not_active`.
7. On SSE disconnect or task cancel, Hermes interrupts the live run (`api_server.py:3670-3677`). The approval map entry is dropped when the run task finishes (`3648-3650`).

Keepalive comments are written every 10s (`CHAT_COMPLETIONS_SSE_KEEPALIVE_SECONDS`, `api_server.py:234`, used at `3662`).

### 2.3 Sequence — Desktop is not holding the chat

```
Phone                HMP                         api_server (this gateway)
  | POST DS-1          |                              |
  |------------------->| DS-2, DS-3 reserve, DS-4     |
  |                    | POST .../chat/stream         |
  |                    |----------------------------->| not the live owner
  |                    | SSE run.started              |
  |                    |<-----------------------------|
  | 202 submitted      |  (5s elapsed; consumer stays)|
  |<-------------------|                              |
  |                    | SSE approval.request         |
  |                    |   run_id, request_id,        |
  |                    |   command, description,      |
  |                    |   choices                    |
  |                    |<-----------------------------|
  |                    | store prompt (memory)        |
  | GET .../prompts    |                              |
  |<-------------------| card                         |
  | POST .../prompts/  |                              |
  |   {request_id}     |                              |
  |   {choice}         | POST /v1/runs/{run_id}/      |
  |------------------->|   approval {choice,request_id}
  |                    |----------------------------->| resolve_gateway_approval
  | 200 resolved       | 200 resolved>0               |
  |<-------------------|                              |
  |                    | SSE run.completed / done     |
  |                    | DS-7a, finalize DS-3 row     |
  | poll SES-2         | reply row                    |
  |<-------------------|                              |
```

HMP's consumer is a task owned by the send, not by the phone HTTP request. At 5s (`ADMISSION_WAIT_S`, contract §13) the phone gets the same DS-7 vocabulary it gets today:

| Stream by 5s | Phone response |
|---|---|
| `run.completed` with an assistant message, and DS-7a passes | `200 accepted` + reply, as DS-7 |
| `run.queued` or the mailbox `done` without a local approval registration | `202 queued` |
| still open (`run.started`, deltas, `approval.request`, keepalives) | `202 submitted` |
| connect failure, non-200, `401` | `503 api_server_unavailable` or gate closed, as DS-6/DS-7 |

The cmid row stays `pending`/`submitted` until the consumer sees a terminal SSE event or the socket dies. DS-8 then reports that outcome. `interleave_detected` is written on the row when the consumer finishes DS-7a, including after the phone already received `202`. Death of the socket before a terminal event finalizes the row `unknown` (same rule as a cancelled sync wait) and interrupts the Hermes turn. HMP does not open a second stream for that cmid.

`approval.request` is stored as soon as it arrives, including before the phone's `202` is sent. The command stored is the redacted SSE value. HMP does not un-redact it.

### 2.4 Sequence — Desktop holds the Bot Chat

The stream is the mailbox branch (§2.2 step 2). HMP never sees `approval.request`. The prompt store gets a **turn marker**, not an answerable card: `{surface:"bot_chat", desktop_held:true}` for the life of that SSE consume (through `done`).

The phone, while that marker is present and no answerable prompt exists, shows the standing line **Waiting for approval on your Hermes Desktop**. Hermes does not tell HMP whether Desktop is actually blocked on an approval. The mailbox returns only the settled reply or queued/claimed (`api_server.py:3493-3503`). Desktop's queue is another process: `tui_gateway` emits an `approval` socket request and resolves it in-process (`tui_gateway/server.py:782-815`). `resolve_gateway_approval` only matches its own process's `session_key`. The banner is therefore the state of a Desktop-held turn, not a detection of a pending card.

Polling SES-2 still reveals the reply when the turn settles. The marker clears when the SSE consume ends. If the consume ends with `run.queued` because Desktop's wait budget expired, the marker clears and the existing F2 "Queued in Hermes Desktop" send state remains (`active_context.dart` mailbox path). The banner does not outlive the marker.

### 2.5 Clarify on path 1 — what the agent and the user see

`api_server.py` never sets `clarify_callback` (no `clarify` reference in that module). The session-stream agent is created by `_create_agent` inside `_run_agent` and is not a `TurnRunner` turn. `TurnRunner` is what assigns `agent.clarify_callback = _clarify_callback_sync` (`gateway/run_turn_runner.py:1287`, implementation `1339-1455`). Desktop assigns its own callback (`tui_gateway/agent_callbacks.py:144-145`) which blocks on a `clarify` socket request (`tui_gateway/server.py:1356-1371`).

`clarify_tool` with `callback is None` returns the tool error `"Clarify tool is not available in this execution context."` (`tools/clarify_tool.py:17`, `226-227`).

So, on a turn **this gateway** runs for the phone:

- The agent receives that tool error and continues the turn without a user choice.
- The user sees no clarify card. They see whatever the assistant then writes (via SES-2).
- HMP does not synthesize choices. There is no id to answer.

On a **Desktop-held** turn, Desktop's callback is the one that runs. Clarify is answered on Desktop. The phone shows the §2.4 banner for the held turn and no card.

### 2.6 `execute_code` on path 1

`check_execute_code_guard` consults `_unattended_contexts()` **before** the ask/notify branch (`tools/approval.py:1270-1280`). `api_server` is in that set (`approval_context.py:134-145`), so `execute_code` resolves from `approvals.unattended_mode` (default `deny`, `hermes_cli/config_defaults.py:1642-1660`) and never enqueues `approval.request`.

The agent sees a BLOCKED tool result. The user sees no card. A later `terminal()` call on the same turn still cards, because the command guard uses the notify callback when ask is set (`tools/approval.py:1193-1201`, `852-870`).

This is a Hermes split, not an HMP policy. Phone chat (§3) does not have it: that turn's platform is `hmp`, which is not in the unattended set, so `execute_code` takes the gateway prompt.

### 2.7 What path 1 will not answer

Slash confirms (`send_slash_confirm`, `gateway/platforms/base.py:2845-2853`) are a platform-adapter hook. The stream route is not an adapter turn. They do not appear on path 1.

`POST /v1/runs` approvals (`api_server_runs.py:824`, `850-859`) are a different client. HMP does not subscribe to them. Only the session-stream run HMP itself opened is answerable here.

## 3. Path 2 — optional Phone chat

### 3.1 What it reuses

F1 already has one conversation per `(user, bot)`, id `default` (`contract.py` `CONVERSATION_ID`). `authorize.ensure_chat` mints the `chats` row. `HermesReadBridge.request_authorization` builds a `MessageEvent` and calls `adapter.handle_message` (`bridge.py:575-618`). The event text is the fixed inert string, `allow_gateway_control=False` (`bridge.py:64-67`, `331-354`). `adapter.send` drops the body (`adapter.py:376-385`), so Hermes's pairing-code reply is never relayed (PR6-2).

`conversation_ref` derives the session key with `gateway.session.build_session_key` (`bridge.py:632-639`). The layout is `<ns>:<platform>:<chat_type>[:…]` (`gateway/session.py:673-714`). For this adapter the platform value is `hmp`, chat type `dm`, so the key is `namespace:hmp:dm:…`. `GatewayRunner._set_session_env` binds `HERMES_SESSION_PLATFORM` from `source.platform.value` (`gateway/run.py:4252-4275`). `hmp` is not in `_UNATTENDED_APPROVAL_PLATFORMS`, so a Phone-chat turn is a gateway approval context (`tools/approval_context.py:157-174`).

OD-F11's session list keeps that session: `is_mobile` is set when the row is this conversation's session (`reads.py:517-540`). Phone chat does not create a second session. The Bot Chat (title `"Bot Chat"`) stays the other visible row.

P6 is still how the bot becomes authorized. Phone chat sends nothing until `require_bot_authorized` says so, and Hermes's own inbound authz still runs inside `handle_message`. The inert trigger is unchanged and is still the only GU-4 exception that fires while the user is `pending_operator`.

A new client does not send user text to `POST …/conversations/default/messages` (SUB-1). That route stays unregistered-for-write. The new route is §4.2.

### 3.2 Sequence

```
Phone                HMP adapter                         Hermes gateway
  | POST phone/messages|                                    |
  | {cmid, text}       | authz, cmid reserve                |
  |------------------->| MessageEvent allow_gateway_control |
  |                    | handle_message ------------------>| normal platform turn
  | 202 submitted      |                                    | session key …:hmp:…
  |<-------------------|                                    |
  |                    | _send_exec_approval_prompt <------| TurnRunner
  |                    |   or send_clarify                  | (run_turn_runner.py)
  |                    | store prompt                       |
  | GET .../prompts    |                                    |
  |<-------------------|                                    |
  | POST .../prompts/id| resolve_gateway_approval(          |
  | {choice}|{text}    |   session_key, choice,             |
  |------------------->|   request_id=…)  ---------------->| queue unblocks
  | 200 / 409          |   or resolve_gateway_clarify       |
  |<-------------------|                                    |
  | poll default       | send() delivered the reply         |
  | snapshot           |                                    |
  |<-------------------|                                    |
```

`handle_message` (`gateway/platforms/base.py:3954-3994`) is the shared inbound entry. While the session is busy, `/approve` and `/deny` bypass the guard (`3996-4018`); both commands are `busy_policy="dispatch"` (`hermes_cli/commands.py:96-100`). A pending clarify is also dispatched inline when `allow_gateway_control` is true (`base.py:4022-4040`). The runner's text intercept matches the reply (`gateway/run_inbound.py:364-416`).

Phone chat does not use that text bypass for approvals. See §5.4.

### 3.3 Adapter hooks

Implement these on `HmpAdapter`. Each one schedules work onto the bridge collaborator. The default base methods stay the documentation of the contract.

| Hook | Role |
|---|---|
| `send` | Deliver an outbound reply (and the plain-text approval fallback, if the runner uses it) into the Phone-chat transcript the snapshot already reads. F1's drop-on-the-floor behavior remains for the inert-trigger reply: if the outbound is the pairing-code response to `INERT_TRIGGER_TEXT`, `send` still returns success and stores nothing (`adapter.py:376-385` stays the rule for that message id prefix). |
| `_send_exec_approval_prompt` | Override so `supports_exec_approval_buttons` is true (`base.py:2805-2809`). The runner then calls `send_exec_approval` (`run_turn_runner.py:1474-1482`) instead of the `/approve` text. Render is not a platform widget; it persists a prompt and returns `SendResult(success=True)` once the prompt is stored. |
| `send_clarify` | Override. `clarify_id` is an argument (`base.py:2855-2865`). Persist a clarify prompt. Do not call the base numbered-list implementation (`2866-2885`): that calls `mark_awaiting_text` immediately, which would make the next phone message look like free text before the user taps Other. |
| `retire_clarify_card` | The runner calls this when the wait ends with no answer (`run_turn_runner.py:1433-1440`, notice `_CLARIFY_EXPIRED_NOTICE` at `run_turn_runner.py:62`). Mark the prompt expired. |

`ExecApprovalPrompt` has no `request_id` field (`base.py:1618-1635`). The runner redacts the command and passes `session_key`, command, description, and the choice tuples (`run_turn_runner.py:1471-1481`) but not the id. The id is already on the queue: notify runs only after the entry is appended (`approval_gateway_wait.py:164-167`, then `201`), and `list_gateway_approvals(session_key)` returns those dicts including `request_id` (`tools/approval.py:192-195`).

Binding rule inside `_send_exec_approval_prompt`:

1. `pending = list_gateway_approvals(prompt.session_key)`.
2. Keep entries whose `command` equals `prompt.command` and whose `request_id` is not already stored on an open card.
3. Exactly one match: store the card under that `request_id`, with `choices` taken from `prompt.choices` (the runner already applied smart-deny / session / permanent filtering, `base.py:2792-2803`).
4. Any other count: return `SendResult(success=False)` **and** do not let a later `send` of an approval paragraph become an answerable card. The runner may fall back to text (`run_turn_runner.py:1530-1550`, metadata `is_approval_prompt`). That text is stored as an unanswerable notice. The agent blocks until Hermes times out (fail closed). HMP does not call `resolve_gateway_approval` without an id.

The session key used in step 1 is `prompt.session_key` from the runner, which is the key HMP's own `handle_message` established. It is not taken from the phone.

`register_gateway_settle` (`tools/approval.py:198-206`) is optional. The poll discovers a vanished id (§4.5). A settle hook that marks the row expired on timeout is an optimization, not required for correctness.

### 3.4 Clarify buttons

`send_clarify` receives `clarify_id`, `question`, `choices`, `session_key` (`base.py:2855-2857`).

- Choice tap: `resolve_gateway_clarify(clarify_id, response)` (`tools/clarify_gateway.py:90-98`). `False` means already resolved, expired, or unknown. HMP reports that as stale and does not apply a second answer.
- The string passed is the offered choice, after the `(Recommended)` suffix is stripped the way `strip_recommended` does (`tools/clarify_tool.py:44-49`). The tool adds that suffix before the callback (`clarify_tool.py:228-229`). Matching ignores the suffix (`clarify_gateway.py:113-120`).
- `multi_select`: the body carries the selected labels. HMP passes `json.dumps(labels)` as `response`, which is the shape the text matcher stores (`clarify_gateway.py` multi path, used by `attempt_text_response_for_session` at `207-217`). At most four choices (`clarify_tool.py:9`).
- **Other:** `mark_awaiting_text(clarify_id)` (`clarify_gateway.py:225-231`). The prompt stays pending with `awaiting_text: true`. The next answer body is `{"text":"…"}` and calls `resolve_gateway_clarify(clarify_id, text)`.
- Open-ended (no choices): `register` already sets `awaiting_text` (`clarify_gateway.py:46-51`). The card is a text field from the start. There is no Other row.
- A choice-card text body that is not a known choice and is not in awaiting-text mode returns `409 invalid_choice` and leaves the Hermes entry pending. It does not send the prose through `handle_message`. Hermes's intercept would cancel the clarify on free prose (`run_inbound.py:421-437`, `TEXT_REJECTED_PROSE`). The phone must not do that by accident.

`retire_clarify_card` runs on timeout, `/new`, and supersede. The phone's next poll omits the card or shows it expired. A late answer gets `False` from `resolve_gateway_clarify` and is reported stale.

### 3.5 Outbound replies

`send` appends an HMP observation the existing `conversations/default` snapshot can show. Hermes remains the transcript authority: the next snapshot read (`bridge` message reads) replaces the observation with the durable row, the same way Bot Chat treats a streamed reply as provisional until SES-2 shows it. HMP does not write `state.db` itself.

Phone-chat send idempotency mirrors DS-3 at a smaller scope: key `(iid, user_id, profile, cmid)`, hash of `text`, reserve before `handle_message`. Same payload replays the stored HTTP outcome and does not call `handle_message` again. A different payload is `409 idempotency_conflict`. There is no `expected_head` on this route. Phone chat is a messaging thread, like Discord: two devices of the same user are two `user_id`s and two session keys. This route does not claim DS-4's single-writer guard, and it must not be described as having it.

The phone HTTP call returns `202 {"state":"submitted"}` once `handle_message` has accepted the event (`MessageEvent._gateway_accepted`, `base.py:3957`, `3994`). It does not wait for the model. The reply arrives through `send` and the snapshot poll.

### 3.6 Write-gate exception

Phone chat hands **user text** to Hermes while GU-4's `"open"` state is false. That is a new, named exception, authorized by OD-F16, and it is narrower than opening SUB-1:

- Registered only when `direct_send` is true and the direct-send dependency probe passes (the same gate as DS-2(b)).
- Flag off: `POST …/phone/messages` returns `503 write_gate_closed` and does not call `handle_message`. Prompt routes return the same `503`.
- The inert authorize trigger is still the only hand-off while the user is not yet authorized.
- `"open_guarded"` remains the Bot Chat send gate. Phone chat does not report `guarantee_level:"guarded"` and does not take `expected_head`.

## 4. Wire — HMP v1.3

Auth on every route below is the existing bearer plus the per-bot gate (ERR-3), then `require_bot_authorized`. Profile segment `{p}` is the same served-profile name as every other `/bots/{p}/…` route.

### 4.1 Read

`GET /hmp/v1/bots/{p}/prompts`

```
200 {
  "prompts": [ Prompt, ... ],
  "desktop_held": false
}
```

`Prompt`:

| Field | Approval | Clarify |
|---|---|---|
| `kind` | `"approval"` | `"clarify"` |
| `surface` | `"bot_chat"` or `"phone_chat"` | `"phone_chat"` only (path 1 never emits one, §2.5) |
| `request_id` | Hermes `request_id` | Hermes `clarify_id` (same JSON name; the path parameter is this value) |
| `choices` | subset of `once`,`session`,`always`,`deny` | the offered labels, `(Recommended)` already on the first when Hermes sent it; omitted when open-ended |
| `command`, `description` | redacted command and the reason string | absent |
| `question` | absent | the question |
| `multi_select` | absent | bool |
| `awaiting_text` | absent | true after Other, or true from the start when there are no choices |
| `expires_at` | unix seconds | unix seconds |

`desktop_held` is true while §2.4's marker is set. `prompts` is then empty of `bot_chat` approvals (a phone-chat card can still be listed). An old client never calls this route.

The Phone-chat snapshot (`GET …/conversations/default`) gains nothing new in its schema: `open_requests` already exists (`HMP_V1.md` RO-3) and starts being populated with the `phone_chat` prompts, mapped to the RO-3 shape (`kind`, `request_id` or `clarify_id`, `command`/`description` or `question`, `choices`, `multi_select`). `awaiting_text`, `expires_at`, and `surface` are extra fields on those objects. A client that does not know them still renders the card from the fields RO-3 already defined. Bot Chat prompts are **not** stuffed into that snapshot. They appear only on `GET …/prompts`, because that snapshot is the Phone-chat transcript.

### 4.2 Phone-chat send

`POST /hmp/v1/bots/{p}/phone/messages`

```
{"client_message_id":"<UUIDv7>", "text":"<string>", "sent_at":<int>?}
```

| Outcome | HTTP |
|---|---|
| `handle_message` accepted | `202 {"state":"submitted"}` |
| Same cmid, same text | the stored response, no second hand-off |
| Same cmid, different text | `409 idempotency_conflict` |
| Flag off / probe failed | `503 write_gate_closed` |
| Not authorized | the existing per-bot forbidden response |
| Approval pending for this phone session | `409 {"error":{"code":"stale"}}` with `"applied":false` — the message was not delivered (§5.4) |
| Body empty or over `MAX_BODY_BYTES` | `400` / `413` |

No `expected_head`. No reply body. The transcript is the existing snapshot and history.

### 4.3 Answer

`POST /hmp/v1/bots/{p}/prompts/{request_id}`

The path id is the only id. The body is one of:

| Kind | Body | Hermes call |
|---|---|---|
| Approval | `{"choice":"once"\|"session"\|"always"\|"deny"}` | `POST {path_prefix}/v1/runs/{stored_run_id}/approval` with `{"choice","request_id"}`. HMP never sends `all` or `resolve_all`. |
| Clarify choice | `{"choice":"<label>"}` or `{"choices":["<label>", …]}` when `multi_select` | `resolve_gateway_clarify` |
| Clarify Other | `{"other":true}` | `mark_awaiting_text`; response `200 {"status":"awaiting_text","applied":false}` |
| Clarify text | `{"text":"<string>"}` | `resolve_gateway_clarify` when the stored prompt is awaiting text or has no choices |

`choice` and `text` together, or `other` together with either, is `400 bad_request`. A `kind` field in the body is ignored; the stored row decides the kind. A body kind that the row cannot accept is `409 invalid_choice` and is not applied.

Success:

```
200 {"status":"resolved", "applied":true}
```

`applied:true` means Hermes accepted the resolution (`resolve_*` returned non-zero, or the runs endpoint returned `resolved > 0`). It does not mean the command finished. The UI clears the card only after a later poll omits it, or after `approval.settled` / `clarify.retired` on the live tail (§4.6). That is INT-2.

### 4.4 Expiry

| Kind | Default | Source |
|---|---|---|
| Approval | 300s | `approvals.timeout`, `tools/approval_context.py:239-247`, default in `hermes_cli/config_defaults.py:1657`. The wait uses it (`approval_gateway_wait.py:58`). |
| Clarify | 3600s | `tools/clarify_gateway.py:259-284` (`clarify.timeout`, else `agent.clarify_timeout`, else 3600). `<= 0` means unlimited; HMP then sets `expires_at` null and does not locally expire the row. |

`expires_at` is `observed_at + timeout`, read through the bridge (function-local import, flag on only). It is a display hint and the log's reason code. Hermes is the authority: an answer whose local clock is past `expires_at` is still offered to Hermes once. Hermes returning "nothing pending" is what makes the phone response stale. A local clock that fires first does not drop a wait Hermes still holds without that call.

### 4.5 Idempotency, stale, replay

The prompt row stores `answer_hash` once an answer has been **accepted by Hermes**.

| Situation | Result |
|---|---|
| First answer, Hermes accepts | `200`, `applied:true`. Row remembered until retention. |
| Retry, same body, already accepted | the stored `200`. Hermes is not called again. |
| Retry, different body, already accepted | `409 idempotency_conflict`, `applied:false`. The first choice stands. |
| Hermes returns 0 / `approval_not_pending` / `approval_not_active`, or `resolve_gateway_clarify` returns `False` | `409 stale`, `applied:false`. The row is marked expired. The choice was not applied by this call. |
| Two in-flight answers for one id | one resolver, in order of arrival under a per-id lock. The second sees the stored outcome. |
| Unknown id, or an id stored for a different `user_id` | `404 not_found`. No Hermes call. |
| `choice` not in the stored `choices` | `409 invalid_choice`, `applied:false`. No Hermes call. |
| Flag off | `503 write_gate_closed`. |

Crash window: Hermes accepted the choice and HMP died before recording it. The retry calls Hermes, gets "nothing pending", and returns `409 stale` / `applied:false`. The first choice did apply. The client copy is "This prompt already ended." It does not offer the other buttons as a fresh decision. This matches DS-3's ambiguous-outcome rule: do not send a second decision under a new id.

Rows are dropped `IDEMPOTENCY_RETENTION_S` after they settle or expire (contract §13, 24h), same as cmids. The process-memory rule (KD-8) means a restart drops them immediately; retention only bounds a long-lived process.

### 4.6 How the phone finds a prompt

F1 does not register the EV-1 SSE route (`server.py` leaves write/SSE/intervention routes unregistered). Discovery that ships with F3 is polling.

- While a Bot Chat send is `submitted` or `queued`, or a Phone-chat turn is in flight, the client polls `GET …/prompts` on the same 1s-backoff-to-15s schedule CL-5 already uses for lookup. It also refreshes the transcript it already polls (SES-2 for Bot Chat, the `default` snapshot for Phone chat).
- On foreground and on reconnect it polls once even if idle (EV-8's existing "re-read on reconnect").
- Idle, with no in-flight turn, it does not spin. Opening the bot is the poll.

v1.3 also names the live-tail frames, so a later revision that registers EV-1 does not invent a second vocabulary. They match EV-7's existing names:

| Event | When |
|---|---|
| `approval.requested` | prompt stored, `surface` included |
| `approval.settled` | Hermes accepted an answer, or the row expired |
| `approval.unanswerable` | path-1 clarify is not this event; this event stays the GU-6 read-only case for a build whose `approval_request_id` flag is false |
| `clarify.requested` / `clarify.retired` | Phone chat only |
| `notice` `{"kind":"desktop_held","text":"Waiting for approval on your Hermes Desktop"}` | §2.4 marker set; a matching notice with empty text clears it |

Until the tail exists, those names are the poll's diff, not bytes on a socket. The poll remains the reconciliation path after the tail exists (a missed frame must not be the only copy).

`approval_request_id` in the capability map (GU-2) is not what gates these routes. The routes exist because HMP holds the `request_id` itself (path 1 from SSE, path 2 from `list_gateway_approvals` / `clarify_id`). A false flag still means the old read-only copy for any approval HMP cannot bind. An unbound prompt is never given buttons.

## 5. Security

### 5.1 Who may answer

The bearer device is resolved to `user_id` by the existing token middleware. The prompt row is stored under `(iid, user_id, profile, request_id)`. The answer route loads the row by `request_id` **and** `user_id`. A match for another user is `404`, the same as an unknown id (no existence oracle beyond the per-bot gate, which already requires this user to be authorized for `{p}`).

The client does not send `session_key`, `run_id`, `chat_id`, or `profile` inside the answer body. `{p}` is the route's profile, checked against the row. The Hermes session key is the one stored when the prompt was created:

- Path 1: the key is the `run_id` Hermes itself registered (`api_server.py:3687`, `4228-4229`). HMP sends that `run_id` only to loopback.
- Path 2: the key is `build_session_key` of the source HMP built for this `user_id` and `chat_id` (`bridge.py:632-639`). `resolve_gateway_approval` is called with that key and `request_id=` (`tools/approval.py:138-156`).

`resolve_all` is never passed. A body field `all` or `resolve_all` is `400` and is not forwarded. The runs endpoint would honor it (`api_server_runs.py:1186-1205`).

### 5.2 Owner devices only

`direct_send` false → both new routes `503 write_gate_closed`, no loopback, no `handle_message`, no `resolve_*`. The flag is the host switch OD-F15 turns on for the owner's Hermes. Pairing is still required: the flag does not authorize a device by itself, and a paired device cannot send while the flag is off. That is the DS-10 scope, reused, not a new ACL.

### 5.3 `allow_gateway_control`

The field means "may this event resolve gateway commands and control prompts?" (`gateway/platforms/event.py:88-90`). `is_command()` is false when it is false (`107-108`).

| Event | Value |
|---|---|
| P6 inert trigger | `false` (`bridge.py:348-351`). Unchanged. |
| Phone-chat user message | `true`, and only for a body the answer route did not claim. |
| Anything HMP fabricates (notices, prompt bookkeeping) | never a `MessageEvent`. |

A prompt answer is not a `MessageEvent`. It cannot be laundered into `/approve` by the text the user typed, because it never enters `handle_message`.

### 5.4 Slash gating, and why the card does not use `/approve`

Slash gating is off until the operator sets `allow_admin_from`. Once set, a non-admin's floor is `help` and `whoami` (`gateway/slash_access.py:17-19`) unless `user_allowed_commands` adds more. `/approve` is then denied with the admin-only text (`gateway/run_busy.py:1097-1121`). `/approve` itself resolves FIFO, with no `request_id` (`gateway/slash_commands.py:1187-1199`). Bare `yes` / `always` / `session` while a blocking approval exists is rewritten into that same handler (`gateway/run_busy.py:499-551`).

HMP does not add `approve` to `user_allowed_commands` and does not document slash as the phone UI.

Server rule, so a modified client cannot take the FIFO path either: if `list_gateway_approvals` for this phone session is non-empty, `POST …/phone/messages` does not call `handle_message`. It returns `409 stale` / `applied:false`. The composer is not a way to say "yes". The card's answer route is the way.

While a clarify prompt is pending, a phone message whose text is the answer is handled as §4.3 by the message route as well as the answer route (same function). It is not a new turn. That closes the gap where the busy-session intercept (`base.py:4028-4040`) would treat the text as the answer and, on free prose, cancel the clarify.

### 5.5 Replay and expiry

Covered by §4.5. The properties the tests pin:

- A second `once` does not call Hermes again after a recorded accept.
- A follow-up `always` after a recorded `once` is `idempotency_conflict` and is not applied.
- An answer after Hermes has dropped the entry is `stale`, `applied:false`, and the tool does not run because of that call.
- A `request_id` minted by the client, never stored, is `404`.

### 5.6 Logging (SEC-4)

`log_event` only (`logging_policy.py:54-65`): event code, outcome code, 8-character id prefixes.

| Log | Allowed | Forbidden |
|---|---|---|
| `prompt_store` / `prompt_answer` | outcome `stored`,`resolved`,`stale`,`invalid_choice`,`conflict`,`desktop_held`; prefixes of `user_id`, `request_id`, `run_id` | command, description, question, choice text, `text`, `API_SERVER_KEY`, `Authorization`, the SSE body |
| `phone_send` | outcome `submitted`,`replay`,`conflict`,`refused` | message text |
| loopback | the existing direct-send outcomes | URL userinfo, bearer, response body |

`choice` is an enum. It may be logged as an outcome suffix only for approvals (`resolved_once`, `resolved_deny`, …), never for clarify labels (those are free text). Clarify outcomes stay `resolved` / `awaiting_text` / `stale`.

### 5.7 Phone-chat authz

Same stack as P6:

1. Bearer device → `user_id`.
2. `require_bot_authorized` (Hermes pairing via `_is_user_authorized_for_source`, the check `bridge.authz_state` already uses).
3. `handle_message` runs Hermes's inbound authorization again. HMP's check is what returns a structured error; Hermes's check is what drops a forged in-process event if the two ever disagree. On disagreement HMP fails closed (no prompt is stored for a turn Hermes did not accept).

`allow_from` / instance-wide grants keep their existing disclosure (PR6-3). Phone chat does not widen them.

## 6. UX

Copy strings below are the contract for the client. Scope words (`once` / `session` / `always`) stay Hermes's; the buttons use Hermes's own labels from `base.py:2788-2789` ("Allow Once", "Allow Session", "Always Allow", "Deny"). A-GAP-19 (no longer explanation of those scopes) stays open. The buttons do not invent a glossary.

| State | Where | What the user sees |
|---|---|---|
| Approval card | Bot Chat (path 1) or Phone chat (path 2), when a prompt with `kind:"approval"` is in the poll | The redacted command, the description, and one button per `choices` entry. Four buttons when Hermes sent all four; fewer on smart-deny or a tirith-only prompt (§2.2 step 5). Tapping a button shows a pending state until the prompt leaves the poll. |
| Stale tap | same card | "This prompt already ended." The buttons disable. The command does not show as allowed. |
| Clarify card | Phone chat only | The question, one button per choice, and **Other**. Other reveals a text field. Open-ended is the text field without buttons. `multi_select` allows several choices and a confirm. |
| Desktop-held turn | Bot Chat, `desktop_held:true`, no `bot_chat` prompt | Standing line: **Waiting for approval on your Hermes Desktop**. The Bot Chat composer keeps today's queued/submitted behavior. No approval buttons. |
| Clarify on a local Bot Chat turn | Bot Chat | No card (§2.5). The assistant's following message is the only surface. |
| `execute_code` blocked on a local Bot Chat turn | Bot Chat | No card (§2.6). |
| Phone chat entry | Per bot, secondary to Bot Chat | A row labeled **Phone chat**. Bot Chat stays the default landing and keeps the label **Bot Chat**. Phone chat is not auto-selected. The first open shows the existing `default` transcript (often empty until the user sends). It does not start a pairing turn; pairing stays the existing authorize flow. |
| Flag off | both | Composers stay as F2 left them for Bot Chat (read-only / gate closed). Phone chat is hidden. |
| Not authorized | Phone chat | The existing pending-operator instruction. No text field that submits user content. |

The approval card and the clarify card are observations. Losing them on process restart matches Hermes dropping the wait. The client drops its local copy on `404`/`stale` and on an empty poll.

## 7. Compatibility and `bridge_files`

### 7.1 New Hermes surface

Path 1 adds **no Python import**. It is the HTTP contract `api_server` already advertises (`session_chat_streaming`, `run_approval_response`, `api_server.py:67-72` and `:86`). Same loopback client, same key, path suffix changed from `/chat` to `/chat/stream`, plus `POST {path_prefix}/v1/runs/{run_id}/approval`. This is the GAP-2 class of dependency (a product route, not a `bridge_files` symbol).

Path 2 adds bridge imports, function-local, only after the direct-send gate is open:

| Symbol | File | Used for |
|---|---|---|
| `resolve_gateway_approval` | `tools/approval.py:138` | card answer, with `request_id=` |
| `list_gateway_approvals` | `tools/approval.py:192` | bind `request_id` onto the card; the §5.4 busy check |
| `resolve_gateway_clarify` | `tools/clarify_gateway.py:90` | choice and text |
| `mark_awaiting_text` | `tools/clarify_gateway.py:225` | Other |
| `get_clarify_timeout` | `tools/clarify_gateway.py:272` | `expires_at` |
| `_get_approval_timeout` | `tools/approval_context.py:239` | `expires_at` |

`list_gateway_approvals` and `resolve_gateway_approval` are already named in `HMP_V1.md` §12 (E-GAP-9). `clarify_gateway._session_index` / `._entries` are named there too (E-GAP-20). This design does **not** read those private dicts. It uses `resolve_gateway_clarify`, `mark_awaiting_text`, and `get_clarify_timeout`. INT-4's "do not answer clarify until P12" was about indexing private entries and a resolver that is not session-scoped (`resolve_gateway_clarify` keys only on `clarify_id`, `clarify_gateway.py:90-98`). The mitigation that ships here is HMP's own `(user_id, request_id)` row: an id the phone did not receive from a prompt HMP stored for that user is `404`, so a guessed `clarify_id` never reaches Hermes. That is the ownership check INT-4 asked for, done outside the private index. Record it as the v1.3 resolution of INT-4 for Phone chat only. Path 1 still has no clarify.

`handle_message`, `send`, `build_session_key`, and `MessageEvent` are already bridge dependencies.

### 7.2 `bridge_files`

Add to `direct_send_supported_builds.json`'s `bridge_files` (not to `read_compat_builds.json`; reads do not import these):

- `tools/approval.py`
- `tools/approval_context.py`
- `tools/clarify_gateway.py`

`gateway/platforms/base.py` is already listed. The fingerprint changes. The current owner-local row (`fingerprint` `a509ad1a…`, git `8afaab37`) will fail closed until a human requalifies it, which is the F2 rule: flag on with a stale fingerprint keeps the gate closed. The probe list `DIRECT_SEND_DEPENDENCIES` (`compat.py`) grows six `DependencySpec`s for the symbols above. Probe is import and signature only, same as the read probe, and runs only when the flag is on.

`adapter.py`'s import allow-list does not grow. A function body in `adapter.py` that imports `tools.approval` is a review reject.

### 7.3 Contract text T0 must change

- New §7b (or a §7a addendum) for the stream switch, the prompt routes, Phone chat, and the GU-4 exception in §3.6.
- DS-5 narrowed: "answer elsewhere" applies when the flag is off, and when `desktop_held` is set. When the flag is on and this process runs the turn, approvals are answerable.
- INT-4 narrowed as §7.1 says.
- §12 table gains the six symbols and the three files.
- No new error code. `stale`, `not_found`, `invalid_choice`, `idempotency_conflict`, `write_gate_closed` already exist. `applied` is an additive field.

## 8. Tasks

Order is dependency order. Later tasks can start against fakes once the row they depend on is merged.

| ID | Depends | Work |
|---|---|---|
| T0 | — | Amend `HMP_V1.md` to v1.3 as §7.3. Docs only. |
| T1 | T0 | Prompt store (memory), `GET/POST …/prompts`, authz, idempotency, SEC-4. No producer yet: the routes answer an empty list and `404`. Unit tests for the table in §4.5 with a fake resolver. |
| T2 | T1 | `direct_send`: stream URL, background consumer, DS-7 mapping, persist `approval.request`, loopback `POST …/approval` using the stored `run_id` and `request_id`, `desktop_held` marker, no sync fallback. DS-3 replay does not open a second stream. |
| T3 | T1 | Phone chat: `POST …/phone/messages`, cmid reserve, `handle_message` with `allow_gateway_control=true`, §5.4 suppression, `send` / `_send_exec_approval_prompt` / `send_clarify` / `retire_clarify_card` via the bridge, snapshot `open_requests`. Inert trigger still dropped. |
| T4 | T2, T3 | `bridge_files`, `DIRECT_SEND_DEPENDENCIES`, fingerprint note. Gate stays closed on the old fingerprint. |
| T5 | T1 | Flutter: poll `GET …/prompts` from the existing Bot Chat refresh (`hmp_client` `active_context.dart`) and from the `default` conversation refresh. Approval card. Desktop-held line. Stale copy. |
| T6 | T3, T5 | Flutter: **Phone chat** entry per bot, clarify card, Other, composer rules in §6. Hidden when the gate is closed. |
| T7 | T2 | Fixture-gateway integration, path 1. A real Hermes at the pinned commit (or the repo's fixture gateway if it already boots `api_server`): one send while no Desktop owner holds the Bot Chat asserts an `approval.request` on the loopback stream and a phone answer that unblocks a flagged command; one send while a mailbox owner holds it asserts no phone card and the banner marker. Assert clarify is absent on the local-run stream. Assert `execute_code` does not produce a card. |
| T8 | T3 | Fixture-gateway integration, path 2. Inbound phone message runs a platform turn (`HERMES_SESSION_PLATFORM=hmp`). A flagged command yields four choices (or fewer when the fixture forces smart-deny) and `resolve_gateway_approval(..., request_id=)` is the call that unblocks it. A clarify with choices plus Other unblocks via `resolve_gateway_clarify` / `mark_awaiting_text`. A second device's bearer gets `404`. A body that includes a session key is ignored. Restarting the gateway mid-wait yields `stale` / `applied:false`. |
| T9 | T5, T6 | Client tests for the four UX states and for "poll stops when idle". Widget tests are enough where no browser harness is part of this repo's phone UI; the fixture tests in T7/T8 are the end-to-end proof. |

T2 and T3 share the store and can be implemented in parallel after T1. T7 needs a gateway that actually blocks on approval; a mock that only checks HTTP shapes is not a substitute for T7. T7 may stub Desktop's mailbox rather than launching the Desktop app: the contract under test is "SSE contained no `approval.request` and contained `run.queued` or a settled mailbox receipt."

## 9. Risks

| Risk | What we do |
|---|---|
| The SSE consumer dies and Hermes interrupts a running Bot Chat turn (`api_server.py:3670-3673`). | The consumer is independent of the phone socket. HMP shutdown cancels it and finalizes the cmid `unknown`. The user can send again only as a new cmid (CL-3). |
| `ADMISSION_WAIT_S` is 5s and an approval waits up to 300s. | The phone gets `202 submitted` at 5s. The consumer keeps reading. |
| Two identical commands in one queue. | Hermes coalesces them (`approval_gateway_wait.py:138-162`). The binder requires exactly one unmatched entry. Zero or many → unanswerable notice, fail closed. |
| `request_id` is not on `ExecApprovalPrompt`. | Bind through `list_gateway_approvals` at send time (§3.3). Do not copy Discord's FIFO click (`discord/adapter.py:6364`). |
| Clarify id is global in Hermes, not session-scoped (E-GAP-20). | The phone can answer only an id HMP stored for that `user_id` (§7.1). |
| `execute_code` on Bot Chat never cards (§2.6). | Documented in the UX. Phone chat is the path that cards it. Do not set `unattended_mode: approve` to paper over this; that would auto-run code. |
| Clarify on Bot Chat is a tool error (§2.5). | The model may improvise. Product copy does not promise a Bot Chat clarify card. |
| Desktop banner is not proof an approval is pending (§2.4). | The string is the held-turn state OD-F16 asked for. It clears when the mailbox stream ends. |
| Operator enables `allow_admin_from` and expects `/approve` from the phone to work. | It may be denied by slash policy, and the server refuses the message while a card is pending (§5.4). The card does not use slash. |
| `tools/approval.py` import is heavy. | Probe and import only while the flag is on, function-local, inside the bridge. |
| Fingerprint change closes the gate until requalification. | Intended. T4 does not flip `direct_send`. |
| A future Hermes build removes `chat/stream` or stops putting `request_id` on the SSE payload. | The direct-send probe does not import `api_server`. T7 is the behavioral pin. A T7 failure closes the gate for that build the same way a probe failure does. |
| HMP and Hermes timeouts drift. | Display uses Hermes's functions. Accept/reject uses Hermes's return value (§4.4). |
| Session-chat streaming and the mailbox path both exist, and a bug picks sync. | KD-3: no fallback. A missing `session_chat_streaming` capability fails the send as `api_server_unavailable`. |

## 10. When Nous ships session-chat approval events

OD-F16's third sentence: both paths move to those events once they exist. What changes, and what does not, depends on what the events actually cover. The phone's routes in §4 stay. They are the stable API. Only the producer behind the store changes.

**If the events are "the session-chat SSE (and the sync route, and the mailbox) now emit `approval.request` and accept the same `POST /v1/runs/{run_id}/approval`":**

- Path 1's private knowledge of an undocumented-to-us event becomes a documented one. The consumer stays; the parse stays.
- If the **mailbox** stream starts emitting `approval.request` for a turn Desktop is running, the §2.4 banner stops being the whole story: HMP stores a real card, and the phone answers, only if the answer endpoint resolves the **Desktop process's** queue. Today it cannot (`tui_gateway/server.py:782-815` is process-local). Shipping the event without a cross-process answer channel does not remove the banner. The banner comes off only when an answer posted by HMP to loopback actually unblocks the Desktop-held turn. T7 gains that case.
- Sync `POST …/chat` is still not used, unless the new events are also available on a call that does not die at `ADMISSION_WAIT_S` and does not require HMP to hold a socket. A documented long-poll or a detachable run id would let HMP drop the "hold SSE until done" rule (KD-2). Until then KD-2 stays.

**If the events include clarify on session chat:**

- Path 1 grows a clarify card from those events, and §2.5's tool-error behavior is deleted for builds that emit them.
- The answer route already has a clarify body. It starts calling whatever resolver the new event documents. If that resolver is still `resolve_gateway_clarify`, the call stays.

**Phone chat:**

- Phone chat does not need the new events to function. It is a platform turn.
- OD-F16 still says both paths move. When Bot Chat can answer approvals **and** clarify while Desktop holds the chat, the reason to keep a second conversation shrinks to "the user wants a thread that is not the Bot Chat." That product choice stays until the owner closes OD-F16's reopen of OD-F13. The engineering move is: Phone-chat cards may be **produced** by the same event consumer if Hermes starts emitting them for `hmp` turns, and the adapter hooks become a thin store. The hooks are not removed in the same change as the parser. Remove them only when a pinned build no longer calls `_send_exec_approval_prompt` / `send_clarify` for this platform.
- `bridge_files` entries for `tools/approval.py` and `tools/clarify_gateway.py` stay as long as the answer route calls those functions. They leave when the answer route calls only HTTP.

**What the phone team does not redo:** the poll, the card widgets, the `request_id` answer route, the stale/replay table, or the "no client session key" rule. A new event is another producer into the T1 store.

## PR plan

Each PR is mergeable on its own. The flag stays off, so none of them turns the feature on for the owner's Hermes. Requalification (OD-F15's second switch) stays a controller action outside these PRs.

| PR | Title | Depends | Contains |
|---|---|---|---|
| PR-1 | HMP v1.3 prompt routes | — | T0, T1. Contract amendment and the store/routes/unit tests. Producers absent. |
| PR-2 | Bot Chat stream approvals | PR-1 | T2, T7. `direct_send` consumer, loopback answer, fixture for both mailbox and local-run. |
| PR-3 | Phone chat platform turn | PR-1 | T3, T4, T8. Adapter hooks, bridge imports, `bridge_files`, fixture for approval and clarify. |
| PR-4 | Phone UI for both paths | PR-1, and PR-2/PR-3 for the manual pass | T5, T6, T9. Poll, cards, Desktop-held line, Phone chat entry. |

PR-2 and PR-3 can be reviewed in parallel after PR-1.

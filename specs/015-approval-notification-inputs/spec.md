# Feature: Approval-lane inputs for priority notifications (I-1, I-2, I-6)

Status: **source accepted by root, 2026-10-02**, after independent focused review and
bounded test repairs. This implements the three in-process inputs; it is not native, device,
push or deployment acceptance. Root decisions remain in [`ROOT_DECISIONS.md`](ROOT_DECISIONS.md).

Base: HMP `150bd0f` (spec 034 source and two isolated native samples accepted; owner deployment
pending). Consumer: spec 014 (approval push registration, design frozen, docs-only PR #74).
Its owner and provisioning choices remain pending. The native samples cover the base, not 015.

## Summary

Spec 014 needs three inputs absent from base `150bd0f`, now implemented by this amendment:

- **I-1** a non-throwing notification, delivered outside the prompt-store lock, when an approval
  row is actually inserted;
- **I-2** an authoritative classification of why a row stopped being open;
- **I-6** one shared "visible now" seam that AP-3 itself uses, with AP-3 behavior unchanged.

This spec amends the approval lane (spec 034) with exactly those three seams. It adds no route,
wire field, error code, authority, persistent storage, Hermes dependency, version floor or
per-build allowlist, and it implements no push registration, dispatcher, resolver or relay. With no
observer registered (the only state this lane ships), every route, response and Hermes call is
unchanged, and so is every log line, except the one fail-closed diagnostic-multiplicity
difference recorded in NI-6.5 (a raising member callable).

It also records source confirmation for I-3, I-4 and I-5. Those need no lane change.

## Source facts at `150bd0f` (verified by reading; anchors are in plan §1)

- `PromptStore.put` returns `None` and signals nothing (I-1 absent).
- An applied answer sets `status = "resolved"`. Every other settle path sets `status = "expired"`:
  native `stale` answers, Phone listing omission, local expiry by `purge`, listener close, the
  binding fence, the end of a bound stream (`expire_run`) and clarify retirement. Nothing records
  which one happened (I-2 absent).
- AP-3 visibility is spread across `PromptStore.list_visible` (purge, open, held filter),
  `prompts.list_prompts`, and a member filter in `server.handle_prompts_list` (I-6 absent).
- `PromptStore._guard` is a `threading.Lock`. The listener watchdog runs `purge` on a worker
  thread. The answer path writes `row.status` on the event loop without `_guard`.
- Bot Chat rows are inserted from the send task's SSE consumer on the listener loop. Phone-chat
  approval rows are inserted from `AdapterHooks.on_exec_approval`, which Hermes schedules onto the
  gateway loop from the agent thread and waits on for up to 15 s (sampled build `ac0cfa7d`). There,
  an exception escaping the hook is classified as a failed send and Hermes falls back to plain
  text, so an exception from a notification observer would change a native outcome.

## User stories and acceptance scenarios

1. As the 014 implementer, I can register one insertion observer per prompt generation and receive
   one event per inserted approval row.
   - Given an observer is registered, when a Bot Chat `approval.request` or a Phone-chat exec
     approval inserts a row, then the observer is called once, after `_guard` is released, on the
     thread that called `put`, with `(key, surface, generation, expires_at)`.
   - Given the key already exists, the row is a clarify, the generation is closed, or the Phone
     side is closed, when `put` is called, then the observer is not called.
   - Given the observer raises, when an approval row is inserted, then the row is stored, `put`
     returns normally, the SSE consumer continues, `on_exec_approval` still returns `True`, and a
     fixed log outcome is written.
2. As the 014 resolver, I can tell an authoritative settlement from a local one.
   - Given an answer Hermes applied (`resolved > 0`), a native `409 approval_not_pending` or
     `approval_not_active`, a native JSON `404 run_not_found`, or a successful Phone listing that
     omits the row, then the row's cause is authoritative.
   - Given local expiry, listener close, the binding fence, the end of a bound stream or run
     (D4), a Phone resolve returning no count, clarify retirement or no recorded cause, then the
     cause is non-authoritative.
3. As the 014 dispatcher and resolver, I evaluate visibility with the same predicate AP-3 uses.
   - Given any mix of rows, held markers, member states and clocks, when AP-3 lists prompts, then
     the response body equals the `150bd0f` response for the same state and clock.
   - Given a settled row, when I ask for its view, then I learn whether it is hidden now (held or
     member closed) without mutating the store.
4. As an operator, nothing I can observe changes.
   - Given no observer is registered, when any approval, Phone-chat, snapshot or send route runs,
     then status, body and Hermes calls are identical to `150bd0f`, and so are logs, except that
     when an AP-3 member callable raises, the count of `bridge_exception` diagnostics may differ
     from the per-item count of `150bd0f` (both fail closed to the same body; NI-6.5).

## Requirements

### NI-1 Insertion observer (I-1)

- **NI-1.1 Slot.** Each `PromptStore` (one prompt generation) has at most one insertion observer
  (`RD-1`). `set_insertion_observer(fn | None)` takes `_guard`, may be called from any thread, and
  is a no-op on a closed store. The default is none.
- **NI-1.2 Event.** A frozen value `ApprovalInserted(key, surface, generation, expires_at)`.
  `key` is the row key `(iid, user_id, profile, request_id)`, `surface` is `bot_chat` or
  `phone_chat`, `generation` is the store's opaque generation token (`RD-2`), `expires_at` is the
  row's display hint. It carries no command, description, choices, run ID or session key.
- **NI-1.3 When.** Exactly once per call to `put` that inserted a row with `kind == "approval"`.
  Inside `_guard`, `put` decides whether it inserted and reads the observer reference. It releases
  `_guard`, and only then calls the observer. A duplicate key, a clarify row, a closed generation
  or a Phone row in a Phone-closed generation does not insert and does not notify. An unbound
  stream approval never reaches `put` and does not notify.
- **NI-1.4 Thread contract.** The observer runs synchronously on the thread that called `put`. On
  sampled builds that is the listener loop for Bot Chat and the gateway loop, awaited by the agent
  thread, for Phone chat; HMP starts its listener on that same loop. The contract does not depend
  on that: the observer must be thread-agnostic, constant time, non-blocking and non-awaiting, do
  no I/O, take no lock held by an approval producer, and hand off with `put_nowait` on its own loop
  or `loop.call_soon_threadsafe` otherwise (014 PN-DSP-2).
- **NI-1.5 Isolation.** `put` catches `Exception` (including `ExceptionGroup`) and
  `asyncio.CancelledError` raised by the observer and logs `prompt_observer outcome=error`. Every
  other `BaseException` propagates unchanged: `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`,
  a `BaseExceptionGroup` not caught above, and any other direct `BaseException` subclass
  (`RD-3`). Containing `CancelledError` is safe because the observer is called synchronously
  with no `await`: a `CancelledError` it raises is a callback failure, not the delivery of the
  enclosing task's own cancellation, which happens only at an `await`. An observer failure
  caught here never changes the inserted row, the return of `put`, a send, a stream, an answer or
  a Hermes hook result. The log carries no observer or row data.
- **NI-1.6 Lifecycle.** `close()` clears the observer inside the same `_guard` section that sets
  `closed`. A notification for a row inserted just before `close` can still be delivered after it;
  the consumer re-checks the generation (I-3, 014 PN-DSP-3). `close_phone_chat()` keeps the
  observer, because Bot Chat rows stay insertable. A stream bound to an older generation calls
  `put` on that older, closed store and so never notifies a newer observer.

### NI-2 Settle cause (I-2)

- **NI-2.1 Field.** `PromptRow.settle_cause`, process memory only, `None` while open. It is never
  on the wire, in a log or in SQLite.
- **NI-2.2 Closed set.** Authoritative: `answer_applied`, `native_not_pending`,
  `phone_listing_omitted`. Non-authoritative: `local_expiry`, `generation_closed`,
  `binding_fence`, `run_ended`, `phone_not_resolved`, `clarify_retired`. A settled row with
  `None` is `unknown` and non-authoritative. `is_authoritative(cause)` is true only for the first
  three.
- **NI-2.3 Mapping (every status writer at `150bd0f`).**

  | Writer | Status | Cause |
  | --- | --- | --- |
  | `answer_prompt`, approval verdict `accepted` (Bot Chat `resolved > 0`, Phone resolve count > 0) | `resolved` | `answer_applied` |
  | `answer_prompt`, clarify verdict `accepted` | `resolved` | `answer_applied` |
  | `answer_prompt`, Bot Chat verdict `stale` (only the three native codes, R14) | `expired` | `native_not_pending` (`RD-5`) |
  | `answer_prompt`, Phone approval verdict `stale` (resolve returned 0 or a coerced non-int) | `expired` | `phone_not_resolved` (`RD-4`) |
  | `answer_prompt`, clarify verdict `stale` (`resolve_gateway_clarify` or `mark_awaiting_text` returned false) | `expired` | `phone_not_resolved` |
  | `reconcile_approvals` after a successful `list_gateway_approvals` (AP-3 and `reconcile_chat`) | `expired` | `phone_listing_omitted` |
  | `purge` past `expires_at + EXPIRY_GRACE_S` | `expired` | `local_expiry` |
  | `close` | `expired` | `generation_closed` |
  | `close_phone_chat` | `expired` | `binding_fence` |
  | `expire_run` (terminal SSE event or consume end) | `expired` | `run_ended` (D4) |
  | `AdapterHooks.retire` | `expired` | `clarify_retired` (`RD-6`) |

- **NI-2.4 Precedence.** Paths that use `expire` change only an open row: the first writer wins and
  sets status, `settled_at` and cause together. The answer path keeps its `150bd0f` behavior and
  overwrites status and `settled_at` unconditionally after its awaited Hermes call, and now writes
  its cause in the same step (`RD-7`). This holds even when another path (`purge`, `close`,
  `close_phone_chat`, `reconcile_approvals`, `expire_run` or `retire`, on a worker thread or the
  loop) already settled the row during that await. So the cause always belongs to the last status
  writer. Recorded, intended consequence: a Phone cause recorded as authoritative by a concurrent
  writer (for example `phone_listing_omitted` from AP-3 or `reconcile_chat` during an in-flight
  Phone answer) can be replaced by the answer path's non-authoritative `phone_not_resolved`.
  Status is `expired` either way and the 014 resolver then fails closed. This is a downgrade, not
  a merge, and no merge rule is added. Bot Chat rows cannot be affected, because reconciliation
  touches only rows with a session key.
- **NI-2.5 Atomicity and single writer.** Every write of status, `settled_at` and cause happens
  inside one `_guard` section, including the answer path (today it writes `row.status` without
  `_guard`). `PromptStore.settle_answer` is the only answer-path writer of `status`, `settled_at`
  and `settle_cause`, all three in one `_guard` section. `_remember` writes only the replay fields
  (`stored_status`, `stored_body`, `answer_hash`): its `settle` parameter is removed entirely and
  it writes no `settled_at` (`RD-13`). `_remember` follows `settle_answer` with no `await` between
  them, so a queued answerer for the same key never observes `status == "resolved"` with
  `answer_hash is None`. The replay fields stay outside `_guard` because their only reader at
  `150bd0f` is `answer_prompt` (`_replay`), under the per-row `asyncio.Lock` on the loop. The
  answer path still holds that lock; no `await` happens while `_guard` is held.
- **NI-2.6 No behavior change.** Status values, `settled_at`, stored replay bodies, HTTP results,
  logs and Hermes calls are unchanged on every path. D4 stays frozen: run completion is never
  authoritative.
- **NI-2.7 Answer-path clock and checks.** `settle_answer` receives the `now` variable as
  reassigned by `now = max(now, int(store._clock()))` before the awaited `_apply`
  (`prompts.py` 595). It never samples `store._clock` or `ctx.now()` itself and writes
  `settled_at = now` unconditionally (`RD-7`). The pre-await `row.status` checks and the replay
  and conflict branches (597–609) are unchanged; only the post-await writes at 612–619 move into
  `settle_answer`. `awaiting_text` (627) is not a settle write and stays an unguarded loop write
  (the recorded RO-3 residual, plan §5).

### NI-6 Shared visibility seam (I-6)

- **NI-6.1 Predicate.** One pure predicate in `prompts.py`, evaluated inside `_guard` on values
  only:
  - `open_now` = `status == "open"` and not (`expires_at` is set and `now > expires_at +
    EXPIRY_GRACE_S`). This is exactly the `purge(now)` rule, without the mutation.
  - `hidden_now` = (`surface == "bot_chat"` and the `(iid, user_id, profile)` Desktop-held marker
    is set) or the row's surface member is closed.
  - `visible_now` = `open_now` and not `hidden_now`.
  - `retention_deleted_now(key, row, now)` = `row.settled_at is not None` and
    `now - row.settled_at >= IDEMPOTENCY_RETENTION_S` and no `_lock_users` entry for `key`
    (`not self._lock_users.get(key)`). These are exactly the retention-delete conditions of
    `purge` (`prompts.py` 236–243), including its active-lock exemption, evaluated on stored
    values without deleting anything (`RD-11`). It adds no timer, observer, cache or authority.
- **NI-6.2 Member state.** `ServerContext.approval_members_now()` returns a frozen
  `MemberState(bot_chat, phone_chat)` from `is_approvals_available()` and
  `is_phone_chat_available()`, failing closed. Callers compute it **before** entering the seam, so
  no callable runs under `_guard`.
- **NI-6.3 Views.** `PromptStore.view_row(key, *, now, members)` and
  `PromptStore.view_visible(iid, user_id, profile, *, now, members, include_wire: bool = False)`
  return frozen `RowView` snapshots: key, kind, surface, generation, status, `settle_cause`,
  `expires_at`, `settled_at`, held, `open_now`, `hidden_now`, `visible_now`, plus `wire` and `session_key`.
  Both take `_guard` once, read the held marker and rows in that one section, call no callable,
  and mutate nothing: no purge, no expiry, no deletion.
  - **Row set and order.** `view_visible` returns one `RowView` for every row of
    `(iid, user_id, profile)` in `_rows` iteration (insertion) order, open or not, with
    `open_now`, `hidden_now` and `visible_now` set, except a row the retention mask suppresses.
    It also returns the held flag. AP-3 emits `wire` for the `visible_now` rows, in that order.
  - **Retention mask (`RD-11`).** A row for which `retention_deleted_now` is true is one the next
    `purge(now)` would delete. `view_row` returns `None` for it and `view_visible` omits it. The
    mask never deletes. A missing key also yields `None`.
  - **Wire and session key (`RD-12`).** `wire` and `session_key` are populated only when
    `view_visible` is called with `include_wire=True`, which only AP-3 does, in both of its
    `view_visible` phases (reconcile candidates and the final listing, plan §2.4). Otherwise they
    are `None`. `view_row` never populates either, so 014 never receives a session key.
  - **Immutability.** `wire` is built inside the same `_guard` section by the pure
    `wire_prompt(row)` and stored as a `types.MappingProxyType` over a fresh dict owned by the
    view, whose `choices` is an owned `tuple`. It is never shared with a row or another view.
    `wire` is declared `compare=False, hash=False`; every other `RowView` field is immutable, so
    a `RowView` is hashable and compares without `wire`. `json_response` (`_plain`) turns the
    mapping and the tuple back into a JSON object and array, so the AP-3 body bytes equal those
    of `150bd0f`.
  - **Live rows (scope).** `view_row` and `view_visible` return only frozen snapshots, and their
    callers (AP-3's new path and 014) read no live `PromptRow`. The legacy live-row APIs
    `list_visible` (RO-3 through `reads.py`), `get`, `open_clarifies` and `answer_row` are
    unchanged and still return live rows. That is a recorded residual (plan §5).
- **NI-6.4 AP-3 uses the seam.** `handle_prompts_list` keeps its gate order, its `purge` calls,
  Phone reconciliation (same candidates, same `HelperUnavailableError` handling) and response
  shape. The sequence is an exact equivalence with `150bd0f`:
  1. Gate order is unchanged (owner, limiter `ctx.now()`, bot grant, `_require_approvals_gate`),
     and the `store is None` early return still returns `{"prompts": [], "desktop_held": False}`.
  2. `t1 = ctx.now()` is sampled once and used for both `store.purge(t1)` and
     `view_visible(now=t1, members=ALL_OPEN, include_wire=True)`, which supplies the reconcile
     candidates (`visible_now` approval rows of the Phone surface with a session key).
  3. The reconciliation loop is unchanged byte for byte: the `is_phone_chat_available()` gate, its
     own `ctx.now()` per `reconcile_approvals` call, `except prompts.HelperUnavailableError` as
     the only catch, and the `{item["request_id"] for item in pending if "request_id" in item}`
     set, so a `BridgeError` from a non-list listing still propagates.
  4. `t2 = ctx.now()` is sampled once and used for both `store.purge(t2)` and the final
     `view_visible(now=t2, members=members, include_wire=True)`, where
     `members = ctx.approval_members_now()` is captured after reconciliation and before that
     call, outside `_guard`.
  5. No `ctx.now()` sample is added or removed (the differential test's scripted clock depends on
     the count), and the response keys stay in order `prompts`, `desktop_held`. `prompts` is the
     `wire` of each `visible_now` view in `view_visible` order, and `desktop_held` is the held
     flag of that same snapshot.

  `prompts.list_prompts` keeps its signature and gains an optional `members`
  argument whose default is all members open (its `150bd0f` meaning, since the member filter lived
  in the server). `PromptStore.list_visible` keeps its signature, purge and return type and
  delegates to the same predicate with all members open, so the RO-3 snapshot path in `reads.py` is
  unchanged in code and behavior (`RD-8`).
- **NI-6.5 Equivalence.** For every serialized schedule, AP-3's status and body equal the
  `150bd0f` result for the same store state and clock values, including: expiry grace boundary
  (`expires_at + 30` listed, `+ 31` not), `expires_at` null, Desktop held (Bot Chat hidden, Phone
  kept, `desktop_held` true), each of the four member combinations, closed and Phone-closed
  generations, other users and profiles, two or more rows of mixed surfaces (to pin order), and
  Phone reconciliation that omits, keeps or fails. Reading the held marker and rows in one
  `_guard` section can only return a result the old two-section read could also return (`RD-9`).
  "Equivalence" covers HTTP status, body bytes and Hermes calls, and the production member
  callables (`adapter.py` 186–187) are pure lambdas over local values that cannot raise. The only
  permitted difference is the multiplicity of `bridge_exception` diagnostic lines when an injected
  member callable raises: `150bd0f` evaluates a member once per listed item (zero times when
  nothing is listed), the seam once per member per request. Both fail closed to the same body.
- **NI-6.6 What the seam does not do.** It does not reconcile Phone rows with Hermes (014 PN-RES-4;
  the withdrawn-Phone-row residual, 014 analysis A20), keep a sticky hidden bit, or record history.
  It evaluates current visibility only (014 C6). It never deletes: a row the next `purge` would
  delete under the retention rule is reported as absent (NI-6.3), and the physical deletion
  still happens only in `purge`.

### NI-C Confirmations (no lane change)

- **I-3** confirmed. The current generation is `ServerContext.prompt_store`. `closed` and
  `phone_closed` are monotonic booleans written under `_guard`. `PromptStore.get(key)` exists but
  returns the live mutable row; 014 reads rows through `view_row` (NI-6.3) instead.
- **I-4** confirmed with 034 semantics: `is_approval_owner_device` (exact `owner_device_ids` entry
  and no explicit host denial; a synchronous store read), `approval_surface_available`,
  `direct_send_effective` (`request_ctx.py`), and the route gate `_require_approvals_gate`
  (`server.py`; module-private, also resolves the profile endpoint off the loop). 014 calls these
  and does not reimplement them.
- **I-5** confirmed. Generations close through `HmpAdapter._close_generation` (from `disconnect`
  after `HmpServer.stop`, from `_listener_closed` after the identity-change stop, and on a failed
  `connect`). `HmpServer.stop` already cancels the watchdog and in-flight sends. The lane adds only
  NI-1.6 (observer cleared on close). Cancelling 014's dispatcher and discarding hints and slots is
  014 code in the listener stop path.

### NI-S Security and compatibility

- Owner, surface, profile grant, member and generation gates are unchanged and not duplicated.
  The seams decide nothing about who may see a row; route gates still run first.
- No exact build, fingerprint, manifest or process latch is read. Minimum-version behavior
  (spec 013, spec 034 R1–R5) is unchanged.
- No callable runs under `_guard`. No new thread, task, queue or timer is created by the lane.
- Logs: one new fixed outcome code, `prompt_observer outcome=error`, with no ID fields.

## Out of scope

Push registration, issuance, dispatch, hint resolution, relay, provider work and every 014 table,
route or setting; attaching an observer at listener open (014); clarify notifications; a sticky
hidden bit or settle history; Phone reconciliation inside the seam; changes to `direct_send.py`,
`bridge.py`, `adapter.py` or `reads.py`; the native fixture harness or its test-tool fingerprint
bootstrap; HMP v1 wire text (no observable change); SD3 and SD5; any Hermes core change.

## Settlement timestamp input amendment (2026-10-02; review pending)

The bounded 014 hint lifetime needs the actual settlement timestamp, not the
time at which a resolver first observes settlement. `RowView` includes immutable
`settled_at: int | None`, captured with status and cause in the existing `_guard`
section. Neither view exports it on the wire; AP-3 bytes and all existing writers,
authority, expiry and retention rules remain unchanged. This is an additive 015
input amendment, subject to independent review with the resolver candidate.
Tests must prove coherent cause/timestamp snapshots, no mutation, exact 60-second
hint settlement margin, frozen prior views and unchanged AP-3 output.

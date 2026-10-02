# Implementation plan: approval-lane inputs I-1, I-2, I-6

Status: design frozen by root, 2026-10-02, after independent review and the bounded amendments
for findings F1–F11. No implementation or runtime evidence is claimed. No source is changed by this plan. Line numbers refer to HMP
`150bd0f`.

## Constitution check

| Principle | Effect |
| --- | --- |
| I. Hermes owns agent behavior | I-2 marks a row authoritatively settled only on a Hermes answer: applied count, a native not-pending code, or a Hermes listing that omits the row. Local expiry, close, fences, run end and ambiguous helper results stay non-authoritative. No Hermes call is added. |
| II. Device trust is explicit | No gate changes. Owner, bot grant, member and generation checks still run in the routes, before any seam. |
| III. Public by default | No identifiers, hosts or owner evidence in tracked files. The one new log outcome carries no ID. |
| IV. Contract before code | This spec precedes code. No HMP v1 wire text changes, because nothing observable changes. |
| V. Verify on Hermes | Source-only unit evidence. The native gate (034 T14) is unchanged and is not repaired here. No build fingerprint is read. |
| VI. Review security findings | Thread and lock behavior changes inside the approval lane. Independent focused review before root acceptance (T060). |

## 1. Source anchors (`150bd0f`)

| Fact | Anchor |
| --- | --- |
| `_guard` is a `threading.Lock`; generation flags `closed`, `phone_closed` | `prompts.py` 147–161 |
| `close` expires all rows, clears Desktop markers | `prompts.py` 163–170 |
| `close_phone_chat` expires Phone rows (AP-10) | `prompts.py` 172–185 |
| `expire` (open → `expired`, `settled_at`) | `prompts.py` 208–212 |
| `expire_run`, `reconcile_approvals` | `prompts.py` 214–225 |
| `purge`: local expiry at `now > expires_at + EXPIRY_GRACE_S`, retention delete | `prompts.py` 231–244 |
| `put`: insert under `_guard`, log after release, returns `None` | `prompts.py` 254–269 |
| `record_stream_approval` → `put` (`kind="approval"`, `bot_chat`) | `prompts.py` 271–303 |
| `desktop_held` read in its own `_guard` section | `prompts.py` 317–319 |
| `list_visible`: purge, held, open rows of the triple, held filter | `prompts.py` 430–444 |
| `list_prompts`: purge, `list_visible`, separate `desktop_held` read | `prompts.py` 493–504 |
| Answer path samples `now = max(now, int(store._clock()))` before the awaited `_apply` | `prompts.py` 595 |
| Answer path writes `row.status` without `_guard` | `prompts.py` 611–619 |
| `_remember(..., settle=True)` is a second, unguarded `settled_at` writer; replay fields are read only by `answer_prompt` (`_replay`) | `prompts.py` 553–567, 597–601, 613, 619 |
| `awaiting_text` is an unguarded loop write | `prompts.py` 627 |
| `AdapterHooks.reconcile_chat` → `reconcile_approvals` | `prompts.py` 747–765 |
| `AdapterHooks.on_exec_approval` → `put` (`phone_chat`) | `prompts.py` 770–843 |
| `AdapterHooks.retire` writes status under `store._guard` | `prompts.py` 884–895 |
| SSE consumer → `record_stream_approval`; terminal events and `finally` → `expire_run` | `direct_send.py` 290–320, 340–342, 406–410 |
| R14 native classification (`resolved > 0`; three stale codes) | `direct_send.py` 528–563 |
| Live resolver: Bot Chat via `aiohttp_approval_call`; Phone resolve `> 0` | `server.py` 862–879 |
| Phone resolve coerces a non-int result to `0` | `bridge.py` 1348–1356 |
| Surface gate | `server.py` 904–928 |
| AP-3: owner, bucket, bot grant, gate, `list_visible`, Phone reconcile, `list_prompts`, member filter | `server.py` 935–978 |
| AP-3 `ctx.now()` samples: limiter 943; `t1` for `list_visible` 950; one per reconciled session 967; `t2` for `list_prompts` 970 | `server.py` 941–977 |
| Watchdog runs `purge` on a worker thread | `server.py` 1350–1355 |
| `is_approvals_available`, `is_phone_chat_available`, `approval_surface_available`, `is_approval_owner_device`, `direct_send_effective` | `request_ctx.py` 212–264, 301–303 |
| Generation built in `open_components` (worker thread); close sites | `adapter.py` 205–250, 495–525 |
| RO-3 snapshot reads `list_visible` on a worker thread | `reads.py` 477–485; `server.py` 451 |

Native caller of the Phone hook, sampled build `ac0cfa7d` (read only, no fetch): the agent thread
schedules `send_exec_approval` onto the turn's running loop and waits up to 15 s
(`gateway/run_turn_runner.py` 87–92 and 1473–1482, `gateway/run_turn.py` 4141). An exception is
classified `failed` and Hermes falls back to plain text (`gateway/run.py` 769–790). This is the
reason for NI-1.5. It is not used as a general claim about other builds.

## 2. Design

### 2.1 Shared contract types (frozen first, T010)

All in `prompts.py`, no behavior:

```text
ApprovalInserted   frozen: key, surface, generation:int, expires_at:int|None
SETTLE_AUTHORITATIVE      = {answer_applied, native_not_pending, phone_listing_omitted}
SETTLE_NON_AUTHORITATIVE  = {local_expiry, generation_closed, binding_fence, run_ended,
                             phone_not_resolved, clarify_retired}
is_authoritative(cause) -> bool          (None and unknown values are False)
MemberState        frozen: bot_chat:bool, phone_chat:bool;  ALL_OPEN constant
RowView            frozen: key, kind, surface, generation, status, settle_cause, expires_at,
                   held, open_now, hidden_now, visible_now,
                   session_key: str|None  (None unless view_visible(include_wire=True)),
                   wire: Mapping|None     (None unless include_wire=True; MappingProxyType over
                                           an owned fresh dict, `choices` an owned tuple;
                                           field(compare=False, hash=False))
                   every other field is immutable, so RowView is hashable and compares
                   without `wire`
VisibleSet         frozen: held:bool, rows:tuple[RowView, ...]   (all rows of the triple, in
                   `_rows` order, minus retention-masked rows)
PromptRow.settle_cause: str | None = None
PromptStore.generation: int   (process-wide, assigned at construction from a module-level
                   itertools.count(1), advanced under a module-level threading.Lock that is not a
                   store `_guard`; no GIL assumption: stores are built on a worker thread by
                   `open_components`, and `requires-python` admits free-threaded builds)
```

`view_row(key, *, now, members)` never populates `session_key` or `wire`. `view_visible(...,
include_wire: bool = False)` populates both only when true, and only AP-3 passes true (§2.4).

### 2.2 I-1 insertion observer

```text
put(row):
  with _guard:
      if refused or duplicate: return
      insert
      observer = self._observer if row.kind == "approval" else None
  log "prompt_store stored"              (unchanged)
  if observer is not None:
      try: observer(ApprovalInserted(...))
      except (Exception, asyncio.CancelledError): log "prompt_observer error"
```

- `except (Exception, asyncio.CancelledError)` contains `Exception` (including `ExceptionGroup`)
  and `CancelledError`. Every other `BaseException` propagates unchanged: `KeyboardInterrupt`,
  `SystemExit`, `GeneratorExit`, a `BaseExceptionGroup` that is not an `Exception` (even one
  wrapping only `CancelledError`) and any other direct `BaseException` subclass. Containing
  `CancelledError` is safe because the observer is called synchronously with no `await`: one it
  raises is a callback failure, never the delivery of the enclosing task's own cancellation
  (delivered only at an `await`). This matches `RD-3`.

- The observer reference is read under `_guard` together with the insert decision, so a
  concurrent `set_insertion_observer` or `close` either precedes or follows the whole decision.
- Calling the captured reference after release is the only place user code runs. It never runs
  under `_guard`, so the observer can call any store method without deadlock.
- Thread map: Bot Chat `put` runs in the send task on the listener loop. Phone `put` runs in
  `on_exec_approval` on the gateway loop while the agent thread waits. HMP starts its listener in
  `connect` on the gateway loop. Tests also call `put` from worker threads. The contract (NI-1.4)
  holds for any caller thread.
- Registration is 014's job. It is safe from any thread, after `open_components` returns.

### 2.3 I-2 settle cause

- `expire(row, now, *, cause)`: the keyword is required, so each of the five internal call sites
  must name its cause. It remains first-writer-wins.
- `PromptStore.settle_answer(row, *, status, cause, now)`: one `_guard` section that writes
  status, `settled_at` and cause unconditionally (the answer path's existing semantics). It is the
  only answer-path writer of those three attributes and replaces the two unguarded
  `row.status = …` writes at 612 and 618.
- `_remember(row, result, digest)` keeps only the replay fields (`stored_status`, `stored_body`,
  `answer_hash`): the `settle` parameter is removed entirely (both call sites pass `True` today,
  so its only effect moves into `settle_answer`), and so is the then-unused `now` argument. At
  both sites `_remember` follows `settle_answer` with no `await` between them, so a queued
  answerer for the same key never sees `status == "resolved"` with `answer_hash is None`. The
  replay fields stay outside `_guard` because their only reader at `150bd0f` is `answer_prompt`
  (`_replay`, 597–601), under the per-row `asyncio.Lock` on the loop (`grep`: no other reader in
  `server/hmp_plugin`; tests read them only as assertions) (`RD-13`).
- Clock: `settle_answer` receives the `now` variable exactly as reassigned at 595
  (`now = max(now, int(store._clock()))`, sampled before the awaited `_apply`). The helper never
  reads `store._clock` or `ctx.now()`. It writes `settled_at = now` unconditionally, overwriting
  any settlement a worker-thread or loop-side path made during the await (`RD-7`). The pre-await
  `row.status` checks (597–609) are unchanged, and `awaiting_text` (627) stays an unguarded loop
  write.
- A concurrent writer's authoritative Phone cause can be replaced by the answer path's
  `phone_not_resolved` through that unconditional overwrite. This is an intended fail-closed
  downgrade, not a merge (NI-2.4).
- The answer-path cause comes from `(row.kind, row.surface, verdict)`: an accepted verdict gives
  `answer_applied`; a stale verdict on a Bot Chat approval gives `native_not_pending`; any other
  stale verdict gives `phone_not_resolved` (`RD-4`, `RD-5`). `_apply` already carries the
  verdict through its result code, so `answer_prompt` needs no new resolver return.
- `AdapterHooks.retire` sets `clarify_retired` within its existing `_guard` section.

### 2.4 I-6 visibility seam

```text
members = ctx.approval_members_now()            # outside _guard; fail closed
with _guard:                                    # one section, no callables
    held = (iid, user, profile) in _desktop
    for key, row in _rows.items() (insertion order), rows of the triple:
        if retention_deleted_now(key, row, now): skip   # pure mask, nothing deleted
        RowView(predicate(row, held, members, now), wire/session_key only if include_wire)
```

`view_visible` returns a view for every non-masked row of the triple, open or not, with
`open_now`, `hidden_now` and `visible_now` set. It does not return only visible rows. `view_row`
looks the key up in the same way and returns `None` for a missing or masked row. The mask is the
`purge` retention condition (`settled_at` set, `now - settled_at >= IDEMPOTENCY_RETENTION_S`, no
`_lock_users` entry) evaluated on values, so a row purge would delete at `now` is reported as
absent without being deleted. After `purge(now)` at the same `now` it is a no-op, so AP-3 and
`list_visible` behavior are unaffected (`RD-11`).

AP-3 after the change, in the same order, as an exact equivalence of the `150bd0f` clock and call
sequence (`server.py` 941–977):

1. Owner, limiter (`ctx.now()`), bot grant, `_require_approvals_gate(member=None)`: unchanged.
   `store is None` still returns `{"prompts": [], "desktop_held": False}`.
2. `t1 = ctx.now()` once. `store.purge(t1)`, then `view_visible(now=t1, members=ALL_OPEN,
   include_wire=True)`. Reconcile candidates are the `visible_now` approval rows of the Phone
   surface with a `session_key`. With `ALL_OPEN` that is the set `list_visible` returned, because
   Phone rows are never held-hidden. `session_key` exists on the view only because of
   `include_wire=True`.
3. The reconciliation loop is unchanged byte for byte: the `is_phone_chat_available()` gate, one
   fresh `ctx.now()` per `reconcile_approvals` call, `except prompts.HelperUnavailableError` as
   the only catch (with its `approval_helper outcome=unavailable` log), and the
   `{item["request_id"] for item in pending if "request_id" in item}` set. A `BridgeError`
   from a non-list listing still propagates.
4. `t2 = ctx.now()` once. `store.purge(t2)`, then `members = approval_members_now()` (after
   reconciliation, before the final view, outside `_guard`), then `view_visible(now=t2,
   members=members, include_wire=True)`. Response `{"prompts": [v.wire for v in views if
   v.visible_now], "desktop_held": held}` in `view_visible` order and in that key order, status
   200, through the same `_prompt_result` helper path as today.
5. No `ctx.now()` sample is added or removed. `purge(t1)`/`purge(t2)` are idempotent at equal
   time, so the one `purge` per phase replaces the old double purge.

Both `view_visible` phases pass `include_wire=True`: the candidate phase needs `session_key`,
the final phase needs `wire`, and `include_wire` is the single definition of "AP-3 only".

`list_prompts(..., members=ALL_OPEN)` and `list_visible` call the same predicate. `reads.py`,
`direct_send.py`, `bridge.py` and `adapter.py` are not edited.

## 3. Affected modules and contracts

| Area | Planned change | Verification |
| --- | --- | --- |
| `server/hmp_plugin/prompts.py` | §2.1 types; I-1 slot, `put` notify, `close` detach; I-2 `expire(cause=)`, `settle_answer`, `_remember` reduced to replay fields (no `settle`), causes at all 9 writers; I-6 predicate with retention mask, `view_row`, `view_visible(include_wire=)`, `list_visible`/`list_prompts` delegation; locked generation counter | new unit tests below; existing approval suites unchanged and green |
| `server/hmp_plugin/request_ctx.py` | `approval_members_now()` composing existing predicates | fail-closed and composition tests |
| `server/hmp_plugin/server.py` | `handle_prompts_list` uses the seam (§2.4); nothing else | route-level differential equivalence test |
| `server/hmp_plugin/logging_policy.py` | none (the fixed code passes the existing shape check) | log scan |
| Wire contract (`HMP_V1.md`) | none | contract tests unchanged |
| Fixtures, native harness | none | not run |
| `specs/README.md` | add 015 row (014 row lands with PR #74) | docs review |

New test files: `test_approval_input_contract.py`, `test_approval_insert_observer.py`,
`test_approval_settle_cause.py`, `test_approval_visibility_seam.py`, all under
`server/tests/unit/`.

## 4. Smallest causal verification

Each test must fail on the named mutant. Root defeats each guard once (034 practice).

| Input | Test | Mutant it must kill |
| --- | --- | --- |
| I-1 | Approval insert on each surface notifies once with the exact event | no notify; notify twice |
| I-1 | Clarify, duplicate key, closed, Phone-closed: no notify | `kind` filter removed; notify before the duplicate check |
| I-1 | Observer probes `_guard.acquire(blocking=False)` and it succeeds | observer called inside `_guard` |
| I-1 | Observer raises `RuntimeError`, `ExceptionGroup`, then `CancelledError`: row stored; `_apply_sse_frame` continues to the terminal event; `on_exec_approval` returns `True`; one fixed log line each | `try` removed; `except Exception` only |
| I-1 | Observer raises `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, `BaseExceptionGroup` wrapping only `CancelledError`, and a direct `BaseException` subclass: each propagates out of `put` unchanged, with the row already stored and no `prompt_observer` log | `except BaseException` |
| I-1 | `put` from a worker thread calls the observer on that thread | dispatch moved to a captured loop |
| I-1 | `close` then `put`: no notify; `set_insertion_observer` after close is a no-op | detach removed |
| I-2 | Table test over the 11 rows of NI-2.3 through the real paths, including `classify_native_answer` for each native code and `_LivePromptResolver` for Bot Chat and Phone | any cause swapped; `run_ended` made authoritative |
| I-2 | `purge` on a worker thread while an answer awaits, then the answer applies: `resolved`, `answer_applied` (today's status) | first-writer-wins on the answer path |
| I-2 | Guarded-write probe: a row whose `status`, `settled_at` and `settle_cause` attribute writes assert `store._guard.locked()`, driven through the real answer path (resolved and stale) | the old unlocked writer (`row.status = …` outside `_guard`); `_remember` still writing `settled_at` |
| I-2 | The answer path writes `settled_at` equal to the value of `now` after the `max(now, int(store._clock()))` line, sampled before the awaited resolver, with a clock that advances during the await; the helper reads no clock | `settle_answer` sampling `store._clock` or `ctx.now()` itself |
| I-2 | While an answer awaits, a worker-thread `purge`, `close` or `reconcile_approvals` settles the row; the answer then overwrites status, `settled_at` and cause (including `phone_listing_omitted` replaced by `phone_not_resolved` for a Phone stale answer) | first-writer-wins or a merge on the answer path |
| I-2 | Status and `settled_at` sequences per path equal `150bd0f` (existing suites unchanged) | any status change |
| I-6 | Differential test: frozen `150bd0f` AP-3 oracle (copied into the test) against the new route over the NI-6.5 grid, including two or more mixed-surface, mixed-status rows in `_rows` order and a scripted clock that counts `ctx.now()` samples. Bodies compare as serialized bytes or `_plain`-normalized bodies, never raw `dict ==` (a tuple is not `==` a list) | grace `>` turned into `>=`; held filter dropped; member filter dropped; purge removed; order changed; a `ctx.now()` added or removed |
| I-6 | Reconcile loop: `HelperUnavailableError` keeps the row; a `BridgeError` from a non-list listing still propagates; `reconcile_approvals` receives its own per-call `ctx.now()` | catch widened; clock reused |
| I-6 | A raising injected member callable: same status and body as `150bd0f`, fail closed; only the count of `bridge_exception` diagnostics may differ (the test pins body, not log count) | member error leaks or opens a member |
| I-6 | `view_row`/`view_visible` leave rows, statuses, `_rows`, `_locks` unchanged, including for a row past the grace and a retention-masked row | seam calls `purge`, `expire` or deletes |
| I-6 | Retention mask: a settled row with `now - settled_at == IDEMPOTENCY_RETENTION_S` gives `view_row` `None` and is omitted by `view_visible`; at `IDEMPOTENCY_RETENTION_S - 1` it is returned. A row with an active `_lock_users` entry is still returned at and past the boundary. A never-settled row is never masked. The row is still in `_rows` afterwards | mask uses another comparison; `_lock_users` exemption dropped; mask deletes |
| I-6 | Members callable asserts `_guard` is free | members evaluated inside `_guard` |
| I-6 | View is unchanged after the row is later mutated: mutate the original row (`awaiting_text`, `status`, replaced `choices`), then the view and its `wire` equal the earlier snapshot; item assignment on `wire` and mutation of `wire["choices"]` raise; two views never share a `wire` or `choices` object | view aliases the live row; `wire` a plain dict; `choices` a list |
| I-6 | `view_row` and a default `view_visible` return `session_key` and `wire` as `None`; only `include_wire=True` populates them | exposure without `include_wire` |
| I-6 | `view_visible` returns all triple rows (open, resolved, expired) in `_rows` order with flags | filters to visible only; reorders |
| I-6 | Hidden part for a settled row (held, member closed) | `hidden_now` computed only for open rows |

Commands (from `CONTRIBUTING.md`): the focused new and existing approval test files, then the full
unit suite, Ruff, `check_plugin_surface.py`, `scan_private.py`, `scan_logs.py`. No native fixture,
dependency install, live host or device.

## 5. Security and compatibility review

- **Trust boundaries.** Unchanged. The seams expose process-memory state to in-process code only.
- **Failure modes.** Observer failure is contained (NI-1.5). Member reads fail closed (NI-6.2).
  An unknown cause is non-authoritative (NI-2.2).
- **Resource bounds.** No new collection. One observer reference and one int per generation, one
  string per row.
- **Concurrency.** The change removes the unguarded answer-path status write, adds no callable
  under `_guard`, and makes AP-3 read held and rows atomically. The generation counter is
  advanced under its own module-level lock, not a store `_guard`.
- **Recorded consequences.** An authoritative Phone cause can be downgraded to
  `phone_not_resolved` by the unconditional answer overwrite (NI-2.4, fail closed). Views apply
  the purge retention rule as a pure mask, so a row due for deletion reads as absent before the
  next `purge` (NI-6.3). A raising AP-3 member callable can change only the count of
  `bridge_exception` diagnostics, never the body (NI-6.5).
- **Residuals, unchanged and recorded.** The legacy live-row APIs `list_visible` (RO-3 through
  `reads.py`), `get`, `open_clarifies` and `answer_row` still return live `PromptRow` objects; only
  the new `view_row` and `view_visible` return frozen snapshots. The RO-3 snapshot still renders
  live rows on a worker thread (`reads.py`); the fields it reads are immutable after insert, except `awaiting_text`, which the
  answer path writes on the loop. AP-3 still propagates a `BridgeError` from a non-list Phone
  listing as today. `is_approval_owner_device` is still a synchronous store read on the loop in
  AP-3. A notification may arrive after its generation closed (NI-1.6), so the consumer re-checks.
- **Build fingerprints.** None read or changed.

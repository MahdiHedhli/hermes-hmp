# Security checklist (reviewer-owned; the implementation worker ticks no box)

Each item needs a test at the actual store, producer or route boundary named in plan §4.

## Insertion observer (I-1)

- [x] S1 The observer is called only after `_guard` is released, never inside it.
- [x] S2 Exactly one call per inserted approval row; none for clarify, a duplicate key, a closed
      generation or a Phone row in a Phone-closed generation.
- [x] S3 An observer raising `Exception` (including `ExceptionGroup`) or `asyncio.CancelledError`
      leaves the row stored, `put` returning normally, the SSE consumer running and
      `on_exec_approval` returning `True`. Every other `BaseException` (`KeyboardInterrupt`,
      `SystemExit`, `GeneratorExit`, an uncaught `BaseExceptionGroup`, a direct `BaseException`
      subclass) propagates unchanged.
- [x] S4 The observer runs on `put`'s caller thread. Nothing in the lane assumes a loop, creates a
      task, queue or thread, or awaits.
- [x] S5 `close` clears the observer in the same `_guard` section that sets `closed`; a stream bound
      to an older generation cannot notify a newer observer.
- [x] S6 The event carries no command, description, choices, run ID or session key. The failure log
      line is the fixed `prompt_observer outcome=error` with no ID fields.
- [x] S7 No production code registers an observer in this lane.

## Settle cause (I-2)

- [x] S8 Only `answer_applied`, `native_not_pending` and `phone_listing_omitted` are authoritative;
      `None` and every other value are not.
- [x] S9 Run completion and the end of a bound stream (`run_ended`, D4), local expiry, listener
      close, the binding fence, a Phone resolve without a positive count and clarify retirement are
      non-authoritative.
- [x] S10 `native_not_pending` is reachable only from the three R14 native codes through the live
      Bot Chat resolver; an unknown `409`, a non-JSON `404`, `401`, `403`, a timeout and a malformed
      `200` leave the row open as today.
- [x] S11 `phone_listing_omitted` is set only after a successful `list_gateway_approvals`; a raising
      lister changes nothing.
- [x] S12 Every status, `settled_at` and cause write is inside one `_guard` section; no `await` while
      `_guard` is held. `settle_answer` is the only answer-path writer of the three, `_remember`
      writes only replay fields (no `settle` parameter), and no `await` sits between them.
      `settle_answer` receives the pre-await `now` and reads no clock.
- [x] S13 Status, `settled_at`, replay bodies, HTTP results and logs are unchanged on every path.
      A concurrent authoritative Phone cause may be replaced by the answer path's
      `phone_not_resolved` (recorded, fail closed, NI-2.4).
- [x] S14 `settle_cause` never reaches the wire, a log or SQLite.

## Visibility seam (I-6)

- [x] S15 AP-3 status and body equal the frozen `150bd0f` oracle over the NI-6.5 grid at the real
      route, including the grace boundary, null expiry, Desktop held, the four member states, closed
      and Phone-closed generations, other users and profiles, mixed ordered multi-row cases, and
      Phone reconcile omit, keep and fail. Bodies are compared as serialized bytes. The only
      allowed difference is `bridge_exception` diagnostic multiplicity when a member callable
      raises (same fail-closed body).
- [x] S16 AP-3 gate order is unchanged: owner, bucket, bot grant, surface gate, then the seam. The
      `ctx.now()` sequence (limiter, `t1`, one per reconcile call, `t2`), the `store is None` early
      return, the reconcile loop and the response key order are unchanged.
- [x] S17 The seam mutates nothing: no purge, expiry or deletion, for open, expired, settled and
      retention-masked rows.
- [x] S18 Member state is computed outside `_guard`; no callable runs under `_guard`.
- [x] S19 `view_row` and `view_visible` return only frozen snapshots, and their callers read no
      live `PromptRow`; mutating the row afterwards (including `awaiting_text` and `choices`) does
      not change a returned view, and `wire` is a `MappingProxyType` with a tuple `choices`. The
      legacy `list_visible`, `get`, `open_clarifies` and `answer_row` still return live rows
      (recorded residual). `view_row` never exposes `session_key` or `wire`, and `view_visible`
      does so only with `include_wire=True` (AP-3).
- [x] S20 A row hidden now (held or member closed) reports `hidden_now` whether or not it is open.
- [x] S21 `list_visible` and the RO-3 snapshot are unchanged in behavior; `reads.py` is not edited.
- [x] S26 The retention mask uses exactly `purge`'s retention-delete conditions (`settled_at` set,
      `now - settled_at >= IDEMPOTENCY_RETENTION_S`, no `_lock_users` entry): `view_row` is `None`
      and `view_visible` omits a row at the boundary, an active-lock row is not masked, and no
      deletion, timer, observer, cache or authority is added.
- [x] S27 `view_visible` returns every non-masked row of the triple in `_rows` order with flags, and
      AP-3 emits `wire` for the `visible_now` rows in that order.

## Generation token

- [x] S28 `PromptStore.generation` comes from `itertools.count(1)` advanced under a module-level
      `threading.Lock` that is not a store `_guard`; tokens are distinct for stores built from
      several threads, with no GIL assumption.

## Scope

- [x] S22 No new route, wire field, error code, authority, persistent storage, Hermes dependency,
      floor, manifest, fingerprint read or per-build allowlist.
- [x] S23 No change to owner, controls, surface, bot-grant or generation gates, and no second copy
      of them.
- [x] S24 `direct_send.py`, `bridge.py`, `adapter.py`, `reads.py`, `HMP_V1.md`, fixtures and the
      native harness are unchanged.
- [x] S25 No push registration, dispatch, resolver or relay code is present.

## Root acceptance scope — 2026-10-02

These boxes record independent focused review and root source-unit/static verification of the
unchanged three production modules, followed by bounded test repairs and the final source suite.
They do not certify native, phone, provider or deployment behavior. S12's no-await adjacency is
verified by reading; the equivalent mutation is not killed by a test. S18 applies to the new seam:
the preexisting `AdapterHooks.retire` clock callback under the guard remains recorded. S13's
stale replay-field write and S15/S16's held-state change during listing now have discriminating
route tests. The frozen oracle blocks and forbidden source paths remain unchanged. See the final
checkpoint in `tasks.md` for counts, skips, mutation setup errors and preserved residuals.

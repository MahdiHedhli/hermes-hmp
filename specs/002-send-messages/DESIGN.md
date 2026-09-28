# F2 "Send messages" — design proposal

| | |
|---|---|
| Status | **v5: IMPLEMENTATION AUTHORIZED (2026-09-27).** The owner's ruling recorded verbatim as OD-F14 ("I want to get to the part where we can actually send messages"... "Reduced mode now, upgrade later"... "Reply directly with a guard"..."Show it, answer elsewhere") and OD-F15 (the two live-config approvals) in `docs/architecture/R0_OWNER_DECISIONS.md`, and `AGENTS.md`'s phase gate now names F2 authorized. This supersedes v4's "planning only" status. Live sends on the owner's actual Hermes still require OD-F15's two approvals to be *executed* by the controller (enabling `api_server`, then the owner-only `direct_send` flag) — this document's own authorization does not itself flip either. |
| Author | F2 design worker (`f2/w-sends-design`); v5 by the F2 SERVER worker (`f2/w-server`, merged onto `f1/connect-and-browse` @ `304c98b`) |
| Revision | v5, 2026-09-27 — records the owner's authorization to implement, and the final OD-F numbering the controller assigned when consolidating this document's OD-N1/OD-N2/OD-N3(mechanism)/OD-N7/OD-N10 rulings into `R0_OWNER_DECISIONS.md`'s own series: **OD-F12** ("for 1.0, let's do the Bot chats... just the ones from the bot view"; supersedes OD-N3(target-scope)/OD-N10 verbatim — the canonical Bot Chat only, other sessions and Desktop tabs deferred to the gateway rewrite), **OD-F13** ("One shared bot chat"; the phone-only `/conversations/default` conversation is retired for *sends* on a new client — this is the ruling on §1.9.2's flagged "load-bearing change to F1's existing model", and it also answers §3.6/T-N00x's "how is the Bot Chat read exposed" question: reuse SES-1/SES-2 unmodified, no new read route — the simplest option, since SES-1 already lists nothing but the canonical Bot Chat under OD-F11), **OD-F14** (supersedes OD-N1/OD-N2's "reduced mode now, auto-upgrade to C" *and* OD-N3(mechanism)'s "reply directly with a guard" *and* OD-N7's "show it, answer elsewhere" — all three, together, as one ruling: Option D (§1.9), gated to the owner's own devices, is the shipped mechanism; §1.7's Option B/C auto-upgrade material stays background/fallback only, unscheduled, exactly as v4 already treated it), **OD-F15** (the owner's approval of the two live-config changes T-N018/T-N019 named: enabling `api_server` on the default profile, loopback-only, and turning on the owner-only `direct_send` flag once the build qualifies — both to be performed by the controller, the flag activation preceded by a ping to the owner, never unilaterally by this worker). **This document does not add or renumber `OD-F#` entries itself** — OD-F12..OD-F15 are recorded, verbatim, only in `R0_OWNER_DECISIONS.md`; this table cross-references them. The wire contract these rulings authorize is now committed: `docs/architecture/contracts/HMP_V1.md` §7a, v1.2, clauses DS-0..DS-10. v1-v4 are preserved in this branch's git history; every §1.9/§3.1.8/§3.2/§3.3/§3.6 mechanism v4 designed is carried into §7a unchanged in substance — v5 is a ratification and wire-text pass, not a redesign. |
| Binding sources | `docs/architecture/contracts/HMP_V1.md` rev 1.0 + v1.2 §7a (`HMP_V1.md`); `docs/architecture/R0_OWNER_DECISIONS.md` (OD-F1..F15); `docs/architecture/FIRST_FEATURE_PLAN.md`; `docs/research/HERMES_PLUGIN_DURABILITY.md` (`DURABILITY.md` below); `specs/001-connect-and-browse/spec.md` (F1, for conventions); `specs/001-connect-and-browse/amendments/A1-session-browsing.md` (A1, OD-F9/OD-F10/OD-F11, merged into `f1/connect-and-browse`); Hermes source at four refs (below) |
| Hermes sources read | Owner's live build `~/.hermes/hermes-agent` @ `8afaab3703e336d72a72c812dd2dd249f04f166a` (git install, `main`, 2026-09-26) — **read-only, never modified, never run**, confirmed via `git rev-parse HEAD` in that checkout; extracted `stock-base` (`04fa849e70`, F1's read-compatible entry); extracted `experimental` (`7e8c8f07a1`, carries HP-6's capability map and P1-P4 admission); scratchpad `pr106742` (upstream PR 106742 head `d7f5c13d73784b4e536bf6fe0d20a48089523ec0`, package `0.21.5`, "one gateway owns every local session") |
| Nothing enabled by this document | No `~/.hermes` write, no device use, by this worker. Enabling live sends on the owner's own Hermes is OD-F15's own two-step live-config action, performed by the controller, not by writing this document or its accompanying code. |

---

## v5 addendum: Bot Chat creation finding (DS-9), evidence re-confirmed

Re-verified directly, read-only, against the same owner build (`8afaab3703e336d72a72c812dd2dd249f04f166a`)
while implementing `HMP_V1.md` §7a's guard (DS-4(2)): `gateway/platforms/api_server.py`'s
`_handle_list_sessions` exact-title branch **resurrects** (unarchives) a previously-created,
since-archived Bot Chat, but does **not create one from nothing** — `db.get_session_by_title`
returning no row leaves the session list empty, no insert happens. `tools/bot_live_delivery.py`'s
`find_canonical_owner` (the same primitive DS-4(2) calls) likewise returns `None` with zero side
effect when no row exists. The only path that actually creates a Bot Chat row is Hermes Desktop's
own `session.create` JSON-RPC call (`apps/desktop/src/plugins/hermes-bots/canonical-chat.ts:405-448`,
`title: CANONICAL_CHAT_TITLE, hidden: true, follow_profile_config: true`, over `tui_gateway`), which
is Desktop's own internal RPC surface — not documented or reachable as a platform-plugin dependency
(§3.1.2 already established this; re-confirmed here specifically for the creation question, not only
the "attach to an existing session" question §3.1.2 originally asked). **Conclusion, unchanged from
v4's T-N005 acceptance criterion: no plugin-reachable supported path creates a Bot Chat that does not
already exist.** `HMP_V1.md` DS-4(2) therefore returns `409 no_bot_chat` when the resolution fails,
with copy directing the operator to open the bot once on Hermes Desktop first — this is final
behaviour, not a placeholder pending a future capability, and `HERMES_API_GAP` is raised: a
platform-plugin-reachable way to create/materialize a bot's canonical Bot Chat does not exist today.

**Correction to §3.6's bridge_files claim.** v4 asserted "`bridge_files` grows by exactly one
file: `hermes_cli/active_sessions.py`" (§3.6). Verified false while implementing
`bridge.resolve_bot_chat` against the extracted `stock-base`/`experimental`/`upstream` trees:
`SessionDB.get_session_by_title` (DS-4(2)) is defined in `hermes_state_titles.py`
(`SessionTitlesMixin`), a separate file from `hermes_state_sessions.py` where `get_session`/
`list_sessions_rich` (A1) live and which v4 assumed, by analogy, also held this method. **Two
files are new, not one**: `hermes_cli/active_sessions.py` and `hermes_state_titles.py`. Both are
present, with the expected signatures, on all three extracted trees
(`tools/compat/bridge_files.py --dependencies-attr DIRECT_SEND_DEPENDENCIES`, run against each).
`server/hmp_plugin/direct_send_supported_builds.json`'s `bridge_files` list is corrected
accordingly. This does not change any conclusion about whether Option D is buildable, only the
exact qualification-list content — recorded here so a later worker does not repeat v4's
unverified assumption.

---

## Review response (round 2) — independent review of `a51dc1b` (Grok 4.7, `APPROVE-WITH-CHANGES`, 4 BLOCKERS)

Full text: `grok-f2server-review.md` (scratchpad). This review re-read the F2 SERVER worker's
implementation itself (`server/hmp_plugin/{direct_send,bridge,contract,gate,store,server}.py`),
not the design document — every claim below was re-verified directly, read-only, against
`~/.hermes/hermes-agent` @ `8afaab3703e336d72a72c812dd2dd249f04f166a` (the same pinned checkout
round 1 used) during this round's fix pass. **Every BLOCKER was confirmed correct.** No finding is
disputed.

| # | Finding | Severity | Verified | Fix (round 2, this pass) |
|---|---|---|---|---|
| 1 | Idempotency/timeout: a `pending` cmid fell through to a second loopback call on retry; `ADMISSION_WAIT_S` was declared but never enforced (`total=None`, no `asyncio.wait_for`); cancelling HMP's own wait does not stop Hermes (`_run_agent` runs via `loop.run_in_executor`, and that worker thread is explicitly left running after the submitting coroutine is cancelled); the mailbox path (`_admit_to_live_bot_chat`) admits before any wait completes; `401`/other non-`200`/`202` left the row dangling `pending` forever instead of closing it; `expected_head` was snapshotted before the per-`(profile, tip)` lock, letting two concurrent sends both pass the precondition. | BLOCKER | Confirmed directly: `api_server_runs.py`'s `_submit_api_worker` (`loop.run_in_executor(None, _counted)`, worker-lifetime count held independent of the submitting task); `api_server.py`'s `_handle_session_chat` (`_answer_through_live_bot_chat` mailbox check, then `_run_agent`); round-1 code's `direct_send.py:205-210` (pending row still called the network), `:279-289` (non-200/202 left `pending`), `:245-265` (`expected_head` read before the lock). | `direct_send.py` redesigned: the guard-plus-call-plus-finalize sequence now runs as one independent, server-owned background `asyncio.Task` per reserved cmid (`_execute`, tracked in the new `PendingSendTasks`), never cancelled by the HTTP handler giving up on it. `handle_direct_send` awaits it via `asyncio.wait_for(asyncio.shield(task), ADMISSION_WAIT_S)` and answers `202 submitted` on timeout without touching the row — the task keeps running and finalizes it whenever it actually concludes. `store.reserve_cmid` now returns `(row, inserted)`; a retry that did not itself insert the row never calls the network again — it awaits the SAME tracked task (bounded, same way) or, if no task is tracked (already finished, or a fresh process since a restart), reports the row's current state without touching anything. Any HTTP response Hermes actually returns (401 included) now closes the row (`accepted`/`rejected`); only a genuine connection failure/timeout (no response at all) stays `pending`. The DS-4(1) lock now wraps the ENTIRE guard-plus-call sequence, `expected_head` is re-read fresh INSIDE it, and lock acquisition itself is bounded (`LOCK_WAIT_S = 3.0s`, documented in `direct_send.py`) — a stuck turn cannot block a queued second send forever; it gets `session_busy` instead. DS-8's lookup route now derives `submitted` (a live task tracked in this process) vs. `unknown` (no task tracked — including durably after a restart, since a fresh process starts with an empty registry) from that same registry, and reports the mailbox `202` outcome as a distinct `queued` state, never conflated with `accepted`. |
| 2 | Lease chain: compression moves the "Bot Chat" title onto the child session and clears it from the ancestor (`hermes_state_titles.py`), so `get_session_by_title` can hand back an id that is itself the tip (or a mid-chain id), and `get_compression_chain` only walks FORWARD from whatever id it is given — silently dropping every pre-compression ancestor from the DS-4(3) busy check. A lease left on the pre-compression id (the "CLI after `/compress`" case) was invisible. | BLOCKER | Confirmed directly against `hermes_state_compression.py`: `get_compression_chain` (`_CHAIN_STEP_SQL`, forward-only) vs. `get_compression_lineage` (walks BACKWARD via `parent_session_id`/`end_reason == "compression"` to the true root first, THEN forward via the same child-selection rule) — the latter is a public `SessionDB` method, already reachable (it resolves, via `inspect.getsourcefile`, to `hermes_state_compression.py`, already in `direct_send_supported_builds.json`'s `bridge_files` for `get_compression_chain`'s own sake), and returns the correct full lineage regardless of which id in it the caller started from. | `bridge.resolve_bot_chat` now calls `db.get_compression_lineage(root_id)` instead of `get_compression_chain`, and uses its result (ancestors through tip) as `BotChatTarget.compression_chain` — the DS-4(3) busy check (`direct_send.py`) already checked every id in `compression_chain`; it now actually receives the full lineage. `compat.DIRECT_SEND_DEPENDENCIES` gained `SessionDB.get_compression_lineage` (no new `bridge_files` entry needed — already contained). `tests/unit/test_bridge.py::test_resolve_bot_chat_resolves_the_live_tip_and_full_chain` plus `fake_hermes.FakeSessionDB.get_compression_lineage` (walks the fake's reverse `children` map) cover it; `tests/unit/test_direct_send.py::test_session_busy_on_pre_compression_chain_id` (round 1's own test, still passing) exercises the guard side. |
| 3 | Loopback: `localhost` was accepted as a configured value and used as the literal URL host with no resolution pinning; `::1` was interpolated unbracketed (not a valid HTTP authority); nothing verified the configured bind was ACTUALLY listening there; aiohttp's own client-side loggers were never silenced (a sufficiently verbose root logger config could log request headers, including the Bearer token, from `aiohttp.client` at DEBUG). | BLOCKER | Confirmed against round-1 `bridge.py`/`direct_send.py`: `_LOOPBACK_LITERALS` included the string `"localhost"` and returned it verbatim as `DirectSendEndpoint.host`; `aiohttp_loopback_call` built `f"http://{endpoint.host}:{endpoint.port}..."` with no bracketing; no socket-level check anywhere; no `logging.getLogger("aiohttp...")` level ever set. | `bridge.direct_send_endpoint`: `"localhost"` is rewritten to the `127.0.0.1` literal immediately (never resolved by HMP itself); `_LOOPBACK_LITERALS` is now exactly `{"127.0.0.1", "::1"}`; a new, injectable `_verify_loopback_listener` performs a real, bounded (`_LOOPBACK_VERIFY_TIMEOUT_S = 0.5s`) TCP handshake against the resolved (host, port) and the endpoint is `None` (fail closed) unless it succeeds. `direct_send.py`'s `_format_host` brackets an IPv6 literal (`[::1]`) before it ever reaches a URL. `logging.getLogger("aiohttp.client")`/`"aiohttp.internal"` are set to `WARNING` at `direct_send.py` import time. `trust_env=False` and no `proxy=` (already correct in round 1) are unchanged. New tests: `test_direct_send_endpoint_localhost_alias_maps_to_loopback_literal`, `test_direct_send_endpoint_fails_closed_when_the_listener_is_unverifiable` (`tests/unit/test_bridge.py`). |
| 4 | Post-hoc interleave: the check compared active row COUNTS against `expected_head`'s own count plus 2, per the module's own docstring — a >32-id heuristic in the actual code. Message ids are one global `AUTOINCREMENT`; a normal other writer (a few rows) stayed under 32 (false negative, silently accepted as clean); a long tool turn or an ordinary compression exceeded 32 (false positive on a normal turn, including the review's own explicit "ordinary reply must never false-flag" ask). The lookup route (DS-8) never surfaced the flag at all. | BLOCKER | Confirmed against round-1 `direct_send.py:299-311`: `advance = refreshed.head_message_id - target.head_message_id; if advance > 32: interleave_detected = True` — a pure row-distance heuristic, not the text/timestamp/`source` identity check `HMP_V1.md` §7a DS-7a itself specifies; `server.py`'s `handle_chat_lookup` (round 1) never read `interleave_detected` from the stored record. | `direct_send._check_interleave` reimplemented as an identity check on the post-compression tip lineage (using the loopback response's own `effective_session_id` when a mid-turn compaction rotated it): passes only if the FIRST row after `expected_head` is HMP's own user row (exact text, a bounded timestamp window, `_INTERLEAVE_TIMESTAMP_WINDOW_S = 120`), and no OTHER `user`-role row appears before HMP's own assistant reply is located in the same read (tool/assistant rows of our own turn are allowed anywhere in between); any ambiguity — a reset/rewrite, a read failure, the expected row missing, our own reply never found — fails safe to `True` ("never under-reports"). Rows appended only AFTER our own matched reply are never examined, so a later, unrelated turn is never mistaken for an interleave of THIS send (the review's own false-positive concern). `interleave_detected` is now persisted in the stored outcome and returned from BOTH the `POST` response and the DS-8 `GET` lookup route. The residual this check cannot close — two identical texts sent very close together by different writers, since `session_chat` carries no per-message client id — is stated plainly in `_check_interleave`'s own docstring, unchanged from `HMP_V1.md`'s own DS-7a text. New tests in `tests/unit/test_direct_send.py`: true-positive (`test_interleave_true_positive_another_user_row_before_our_reply`), true-negative with a tool row in between (`test_ordinary_reply_never_false_flags_as_interleaved`), a later unrelated turn never flagged (`test_interleave_never_flags_a_later_unrelated_turn`), and two fail-safe cases (reset reason; our own reply never found). `tests/unit/test_server.py::test_chat_lookup_surfaces_interleave_detected` covers the DS-8 route surfacing. |
| 5 | SHOULD-FIX: default-listener key coupling didn't read `extra.key` first (api_server.py:1191's own precedence) or apply the 16-char usability floor for a named profile's scoped key; the `direct_send` host flag was captured once at listener-start despite the adapter's own comment claiming a per-request re-check; `assert endpoint is not None` would surface as a bare `500` if ever violated; `resolve_bot_chat`/`lease_snapshot`/`profile_runtime_scope` ran synchronously on the event loop; `ProfileLocks` never evicted an entry (unbounded growth, one per compression rotation, for the life of the process); the loopback URL path segments were not quoted. | SHOULD-FIX | Confirmed each independently against `bridge.py`/`direct_send.py`/`adapter.py`/round-1 code, and against `api_server.py:1191`/`_expected_api_key`/`hermes_cli/auth.py`'s `has_usable_secret(min_length=16)` for the key-precedence claim. | `bridge.direct_send_endpoint`: the DEFAULT profile now reads `extra.get("key")` first (falling back to the scoped secret, unchanged), exactly mirroring `api_server.py`'s own `extra.get("key", ...)`; a NAMED profile never reads `extra.key` at all and must clear a `_has_usable_secret` length-16 floor (a partial, documented mirror of `has_usable_secret`) on its own scoped secret. `request_ctx.ServerContext.direct_send_flag` is now a zero-arg callable, re-invoked every request via the new `direct_send_enabled()` method; `adapter.py` binds it to a closure over the LIVE `adapter.config.extra` (cheap, no I/O) instead of a one-time bool. The `assert` before the loopback call is now a fail-closed `503 api_server_unavailable`, at both the pre-task-launch site and defensively inside `_execute` itself. `handle_direct_send`/`_execute` now call `resolve_bot_chat`/`lease_snapshot`/`direct_send_endpoint` via `asyncio.to_thread` throughout. `ProfileLocks` is now an LRU-bounded (`max_entries`, default 4096) `OrderedDict`, evicting the least-recently-used UNLOCKED entry once over the bound. `direct_send.aiohttp_loopback_call` quotes the session-id path segment (`urllib.parse.quote`); `bridge.direct_send_endpoint` quotes the profile name in `path_prefix`. |
| 6 | Missing suite (T-N015/T-N016): no fixture-gateway integration suite for direct send existed at all. | Required, not previously blocking | — | See the CI report for this round (F2 SERVER worker's own handoff) for the fixture-gateway integration suite added under `server/tests/integration/` and its result against `stock-base` (and `experimental` where cheap). |

**Additional finding, beyond this round's own review (surfaced only by actually running the new
fixture suite against `experimental`, not by either round of review text).** `experimental`'s own
capability map genuinely satisfies GU-4's `"open"` floor (`admission_precondition: 2`,
`defer_policy_reject: 1`) -- the state `HMP_V1.md` §7a DS-2(b) says "no supported build advertises
... today". Round 1 and this round's own fix both left `handle_direct_send` resolving a
`DirectSendEndpoint` only for the guarded branch, never for a genuinely `"open"` base gate --
under `experimental`, this meant the route unconditionally failed (`endpoint` stayed `None`, and
`_execute`'s own defensive check turned that into `503 api_server_unavailable` on every attempt),
because DS-2(b)'s own text describes a native Hermes admission path for the genuinely-open case
("available under that full guarantee, unchanged from SUB-1..SUB-10") that plainly does not exist
in this codebase (F1 registers no write route, FR-053). Fix: `handle_direct_send` now resolves the
endpoint whenever the base gate is genuinely `OPEN` too (not only when the owner-dogfood flag is
on), and still uses the same DS-6 loopback mechanism -- the only one actually implemented -- rather
than reporting the route as unconditionally unavailable for such a build. The response is still
correctly reported as full, un-gated guarantee (`server.py`'s existing `guarded = base_gate.state
is not WriteGateState.OPEN`, untouched). A genuinely-open gate with no resolvable endpoint at all
(no native path, and the loopback endpoint itself could not be positively determined) still fails
closed, `503 api_server_unavailable`, retryable -- never a bare `500`. New unit tests:
`tests/unit/test_direct_send.py::test_genuinely_open_gate_still_resolves_and_uses_the_endpoint`,
`::test_genuinely_open_gate_with_no_resolvable_endpoint_fails_closed`.

None of round 2's findings are disputed. All 4 BLOCKERs and both SHOULD-FIXes are addressed above;
the residual DS-7a text-identity limit is unchanged from `HMP_V1.md`'s own stated residual, not a
new gap introduced by this pass.

---

## Review response (round 3) — independent review of the round-2 fixes (`APPROVE-WITH-CHANGES`)

Hermes re-checked read-only at `8afaab3703e336d72a72c812dd2dd249f04f166a`. Each row has a unit test that failed on the round-2 code and passes after this pass.

| # | Finding | Fix |
|---|---|---|
| 1 | Lease chain still partial: `get_compression_lineage` (`hermes_state_compression.py:689-719`) can return only `[session_id]` when its forward spine omits the start id, and `resolve_bot_chat` then drops ancestors. | Independently walk `parent_session_id` upward from the live tip via `SessionDB.get_session` (`hermes_state_sessions.py:786`, already a supported read) and union those ids with the lineage. If the walk cannot be established (missing parent, cycle, bound), `resolve_bot_chat` raises and the send fails closed as `session_busy`. |
| 2 | In-place compaction: `bridge.after` returns `HISTORY_REWRITTEN` (any `ResetReason`) and that alone set `interleave_detected`. A reply past 64 rows did too. | A reset is not itself an interleave. Re-read the post-compaction transcript (`lineage().lineage_tip` or the caller's `effective_session_id`) and apply the same text/role/timestamp rule. If that re-read cannot be done, log `direct_send` / `interleave_unverified` and leave `interleave_detected` false. Page (`64` × up to `16`) until the reply is found. |
| 3 | `HmpServer.stop` did not cancel send tasks. Cancel or any exception before finalize left the row `pending`; the next POST returned `submitted` while DS-8 returned `unknown`. | `stop` cancels and awaits `PendingSendTasks` up to `SHUTDOWN_TIMEOUT_S`. Cancel or any exception before a definitive finalize stores `unknown` (never left `pending`). A POST for a row with no live task reports `unknown`, the same state DS-8 reports, never `submitted`. |
| 4 | `ProfileLocks` could evict a lock that was handed out but not yet acquired, and the key was the pre-lock tip. | Refcount plus held/waiters: never evict a lock that is held, has waiters, or has been handed out and not released. Key is the lineage root (`compression_chain[0]`), stable across compression. |
| 5 | `reserve_cmid`'s `BEGIN IMMEDIATE` could overlap: one sqlite connection, `check_same_thread=False`, called from `to_thread`, no mutex. | `threading.Lock` around every `transaction()` (`BEGIN IMMEDIATE` through `COMMIT`/`ROLLBACK`). |
| 6 | The loopback check connected and closed, then a later connection carried `API_SERVER_KEY`. | No probe socket. The aiohttp request is the verification: connector resolver pinned to the literal loopback address, connect timeout `0.5s`, `trust_env=False`. Connect failure is `api_server_unavailable`. |
| 7 | The default profile's `extra.key` was not length-checked. | Same 16-char floor as a named profile's scoped secret. A short inline key fails closed (gate closed) and is not sent. |

---

## 0. Why this document exists, and what it does not decide

F1 ships read-only. The owner now wants to see sends work. Before any code, HMP_V1.md's own
write gate (GU-4) already answers "can F1's client submit against the owner's *actual*, unmodified
Hermes today": **no**. `write_gate.state` is `open` only when both `no_defer` and `atomic_anchor`
derive `true` from `gateway.platforms.base.PLATFORM_ADAPTER_CAPABILITIES` (HMP_V1.md GU-2, GU-4,
lines 672-714), and that map is **absent** from the owner's build and from stock Hermes generally
(§1 below, with file:line evidence). OD-F3 additionally forbids write-enabled dogfood in this
phase and holds the write-supported release matrix empty until RV-3/RV-4 pass independent
verification (`R0_OWNER_DECISIONS.md` OD-F3). This document is the plan for closing that gap
honestly — not a way around it.

---

## Review response (independent review of v3, Grok 4.7, `PROCEED-WITH-CHANGES`, 5 BLOCKERS)

Full text: `grok-f2design-review.md` (scratchpad). Every claim below was re-verified directly against
`~/.hermes/hermes-agent` @ `8afaab3703e336d72a72c812dd2dd249f04f166a`, read-only, during this
revision — the citations in the "Verified" column are this worker's own, not copied from the review.
**Every BLOCKER was confirmed correct.** No finding is disputed.

| # | Finding | Severity | Verified | Change in v4 |
|---|---|---|---|---|
| 1 | Route is `/api/sessions/{id}/chat`, mirrored verbatim as `/p/<profile>/api/sessions/{id}/chat` — **not** under `/v1`. `SHARED_LISTENER_MIRROR_PATHS` is unrelated (it documents the OpenAI-compatible prefix, not the router's mirror rule). | BLOCKER | Confirmed: `self._app.router.add_route(method, f"/p/{{profile}}{path}", handler)` mirrors every route verbatim (`api_server.py:4429-4431`). v3's `/v1`/`/p/<profile>/v1` claim was wrong. | §1.9.1 rewritten with the correct paths. |
| 2 | Body field is `message` (or `input`), not `text`. | BLOCKER | Confirmed: `_session_chat_user_message` reads `body.get("message") or body.get("input")` (`api_server.py:661-665`). | §1.9.1, §3.2 corrected: HMP translates its own `text` field to `message` when constructing the loopback body. |
| 3 | Per-profile key coupling: the default listener's key is `self._api_key` (set once at `connect()`, itself guarded to be a real ≥16-char secret or the adapter refuses to start, `:4363-4390`); a `/p/<profile>/` request is checked against a **fresh**, independently-scoped `get_secret("API_SERVER_KEY")` for that profile (`_expected_api_key`, `:1529-1544`), never the default's value. Capabilities' `session_chat:true` does not prove a usable key exists. `401` must be treated as gate-closed, not retried with a guess. | BLOCKER-adjacent (SHOULD-FIX in the review, treated as blocking here since it changes the credential design) | Confirmed exactly, including that `connect()`'s own startup guard makes the *default* profile's empty-key bypass (`:1559-1562`) unreachable in practice for a running listener — but HMP must not rely on that reasoning either. | §1.9.1 rewritten: HMP resolves the key **per target profile** using the same rule Hermes itself uses (default vs. named-profile scoping), never assumes validity from `/v1/capabilities`, and treats any `401` as "this instance's write gate is closed for this profile," not a retryable error. |
| 4 | Guard misses real writers: `_run_agent` never calls `try_acquire_active_session` (already known from v3); additionally, `/v1/runs` (a second api_server entry point with its own session targeting and idempotency store), `run_internal_session_turn` (in-process wake, "no HTTP, no API key"), ACP (zero `try_acquire_active_session` references anywhere under `acp_adapter/`), Desktop before its first prompt in a session (`active_session_lease: None, # claimed lazily on the first turn`), and CLI after `/compress` (updates `self.session_id` but never re-acquires the lease, so the lease stays on the now-ended parent) are all invisible to a lease-registry snapshot. | BLOCKER | All confirmed directly: `api_server_runs.py:660-705` (`/v1/runs`); `api_server.py:3021-3027` (`run_internal_session_turn`, "no HTTP, no API key"); zero hits for `try_acquire_active_session` under `acp_adapter/`; `tui_gateway/methods_session.py:387` (`"active_session_lease": None, # claimed lazily on the first turn`); `hermes_cli/cli_session_mixin.py:979-985` (`self.session_id = self.agent.session_id` with no lease re-acquisition). | **Substantially resolved by the separate OD-N10 ruling, received while this response was being drafted** (§3.1.8's opening paragraph): scoping sends to the canonical Bot Chat means the Desktop-holds-it case is now covered *natively* by `_admit_to_live_bot_chat`'s mailbox mechanism (confirmed also used by `/v1/runs`, `api_server_runs.py:746`), not by a guard check at all. ACP and general CLI/Discord/Telegram sessions are out of scope entirely under OD-N10, not merely unchecked. What remains, exactly per §3.1.8(iii)'s enumeration: Desktop-before-its-first-prompt, a second concurrent api/peer-dm caller, wake, and cron — each an accepted, likelihood-assessed residual for this owner's single-owner deployment, not silently assumed closed. §3.1.8's guard (ii) is also independently corrected regardless of OD-N10: correct `registry_home`, checks every id in the compression chain, fails closed on any snapshot exception. |
| 5 | Post-hoc check as designed (single-writer-wins-the-race framing) both misses the actual interleave case (two concurrent `_run_agent` calls can each see no interleave from their own vantage point) and false-flags an ordinary compression rotation (the post-compression transcript often does not contain `expected_head` at all, since compression is not "another writer," it's the same turn's own housekeeping). There is no `client_message_id` on this route; rows are stamped `source="api_server"`. A Bot Chat `202 queued` outcome has not written the row yet, so an immediate post-hoc check is meaningless for it. | BLOCKER | Confirmed: `api_server.py:3543-3552` (completion body, `effective_session_id = result.get("session_id")`, showing the response itself reports the post-rotation id); `:4272-4280` (compression rotation during a turn is normal, not a foreign writer); `:3446-3449` (Bot Chat `202 queued`/`claimed`, settled later). | §3.1.8's post-hoc check fully redefined: pass only if the *only* rows committed after `expected_head` (on the post-compression transcript) are our own user row and its own assistant reply; explicit rule for identifying "our row" without a cmid (text + timestamp window + `source="api_server"`, with its stated limits); explicit handling for a mid-call compression rotation (compare against the response's own `effective_session_id`) and for the Bot Chat `202` path (defer the check until the delivery settles). |
| 6 | Loopback bind is not guaranteed (`API_SERVER_HOST=0.0.0.0` still starts, with only a log warning, "host-user RCE"); a proxy-honoring HTTP client would send the Bearer token off-box; same-loop HTTP must not block the gateway's own event loop. | BLOCKER | Confirmed: `listen_address()` defaults to `127.0.0.1` but config/env can override it, and `connect()` only warns (`is_network_accessible`, `:4441-4456`), never refuses. | §1.9.1 adds an explicit loopback-bind check (HMP reads the same config/env `listen_address` reads, fails closed if the result isn't loopback or can't be determined) and specifies an async `aiohttp.ClientSession(trust_env=False)` call pinned to `127.0.0.1`/`::1`, never a hostname, never honoring proxy env vars, run on HMP's own coroutine (no `to_thread` — it's already async I/O on the shared gateway loop). |
| 7 | Idempotency: the cmid is recorded only after a definitive response; the `202`/timeout window leaves an unfenced in-flight turn a client's "Send as new" could duplicate. Session chat has no server-side idempotency key (unlike `/v1/runs`). | BLOCKER (folded into the review's #4) | Confirmed: no `Idempotency-Key` handling in `_prepare_session_chat`/`_handle_session_chat`. | §3.1.8 guard (i) rewritten: HMP reserves the cmid **atomically before** the loopback call (not after), holds it through the `202`/timeout window, and timeout reconciliation (polling) never triggers an automatic resend under the same or a new cmid — matching `CL-4`'s existing "no automatic retry" rule, now also closing this specific duplication window explicitly. |
| — | NITs: completion body is at `:3547-3552` not `:3536-3541`; `get_compression_chain` cross-tree byte-identity was asserted, not verified, in v2/v3; Kanban as a same-session writer was not verified. | NIT | Line ref corrected above. The other two are now stated as unverified, not implied-verified, in §3.6/§3.1.8. | Citations corrected; unverified claims now say so. |

None of the review's findings are disputed. All six BLOCKERs (the review's own #3/#6 are folded together above as they're both credential/route-shape corrections) and both SHOULD-FIXes are addressed below. **A separate owner ruling, OD-N10, arrived while this response was being drafted** and independently resolves the largest share of finding #4 (native Desktop-mailbox coverage for the only session sends now target) — noted in finding #4's row above, and detailed in §1.9.2/§3.1.8.

---

## Owner rulings (2026-09-27, relayed by the coordinator)

The owner answered three of the nine decisions this document raised. These are rulings, not
recommendations — where they differ from v1's recommendation they win, per this project's own
convention (`R0_OWNER_DECISIONS.md` line 4: "these are owner rulings... these rulings win"). Detail
and the resulting design changes are in the sections cross-referenced below; this table is the
record.

| Decision | Ruling | Where designed |
|---|---|---|
| **OD-N1 / OD-N2** | **"Reduced mode now, upgrade later."** Ship Option B (reduced guarantees on stock Hermes) now, gated to the owner's own devices only. This explicitly lifts OD-F3 for owner dogfood **only to this extent** — it is the new decision that does so (the controller should record it in `R0_OWNER_DECISIONS.md` as the next `OD-F#` in that series; this document does not renumber or edit that file). Then switch to Option C automatically when PR 106742 (or an equivalent durable-admission mechanism) is detected on the running host build. | §1.7 (revised), §1.8 (new: auto-upgrade detection), §2 |
| **OD-N3 (scope)** | **"Reply into any session."** The phone must be able to send into ANY session, including Desktop-, CLI- or other-platform-originated sessions browsed via A1 (`f1/w-sessions-design`, OD-F9/OD-F10). Investigated on the owner's own build (`8afaab37`, read-only). | §3.1 |
| **OD-N3 (mechanism, 2026-09-27, verbatim)** | **"Reply directly with a guard. Remember our plan to check if it's the latest message or fail. We only send messages when all messages are in sync between device and mobile."** This **replaces v2's fork-and-seed recommendation** as the primary path. Fork-and-seed is kept only as a documented rejected alternative (§3.1.7). The ruled mechanism is `api_server`'s `POST /api/sessions/{session_id}/chat`, reached over loopback from the HMP plugin, guarded by a client-declared head precondition plus server-side liveness checks (§1.9, §3.1.8). | §1.9 (new), §3.1.8 (new) |
| **OD-N7** | **"Show it, answer elsewhere."** Approvals/clarify raised mid-turn stay read-only on the phone — confirms v1's recommendation. | §3.8 (unchanged design, now marked RULED) |
| **OD-N10 (new, 2026-09-27, verbatim)** | **"Right now, bot chats are only done in one channel at a time. I don't think our app should communicate with terminal and Discord/telegram channels... just the ones from the bot view."** **Narrows OD-N3's scope**: the phone sends only into the session Hermes Desktop's Bots view shows for a bot — the canonical `(profile, "Bot Chat")` session — never a CLI/terminal, Discord, Telegram or other channel session. This resolves most of the review's guard-coverage BLOCKER natively, because that one session already has a Hermes-native single-writer mechanism (the Desktop-mailbox hand-off, §1.9.2) that a general "any session" design could not rely on. | §1.9.2 (rewritten), §3.1.8 (rewritten) |

OD-N4, OD-N5, OD-N6, OD-N8 and OD-N9 were not ruled on. This revision keeps v1's recommended
defaults for those five and marks each **"controller default, owner may override"** in §2's decision
table — they remain open for the owner to override at any time and are not being treated as settled.
**OD-N1/OD-N2's "reduced mode now, auto-upgrade to C" ruling (v2) is superseded for the *primary*
send mechanism by the OD-N3 mechanism ruling above** — Option D (§1.9), not Option B or its
auto-upgrade to C, is now the mechanism being designed for the primary send path. §1.7 is revised
accordingly; Options B/C's technical material is kept as background and as a possible degraded
fallback (§1.9's own "relationship to B/C" note), not deleted, since it remains the more honest
description of what stock Hermes gives *without* api_server enabled on the target profile.

---

## 1. The key question: minimal safe path to sending on the owner's actual build

### 1.1 What is actually on the owner's build today (evidence)

| Claim | Evidence |
|---|---|
| `PLATFORM_ADAPTER_CAPABILITIES` exists **only** in the experimental build | `grep -rn PLATFORM_ADAPTER_CAPABILITIES` over `stock-base/src` and `pr106742` returns **zero** hits. It is defined at `hermes_builds/experimental/src/gateway/platforms/base.py:1906` (`PLATFORM_ADAPTER_CAPABILITIES: Dict[str, int] = {...}`), with the "feature-detect by version, never by symbol" rule documented immediately above it (`base.py:1898-1904`). |
| `MessageEvent.defer_policy` exists **only** in the experimental build | `defer_policy` appears throughout `experimental/src/gateway/run_busy.py`, `run_turn.py`, `turn_context.py`, `shutdown_flush.py` (e.g. `run_busy.py:85`, `getattr(event, "defer_policy", "hermes") != "reject"`). It is **absent** from `stock-base` and from `pr106742` (`grep -rn defer_policy` over both returns zero hits in `gateway/`). |
| The owner's build (`8afaab37`) is upstream `main`, not the experimental branch | `DURABILITY.md` line 16: "Owner's current build \| upstream `main` @ `8afaab3703` ... git install". It is 2,659+ commits ahead of `stock-base` (`04fa849e70`) and shares upstream `main` lineage with `pr106742`'s base, not with `experimental` (`_refs/hermes-agent-r0e`), which "carries our unmerged P1-P4 and HP-6 capability map" (`DURABILITY.md` line 19). |
| Therefore, under HMP v1 as specified, `write_gate.state` is `closed` on the owner's build today | `gate.py`'s `derive_guarantees` (already implemented for F1, unused there) returns every flag `false` when `capabilities` is `None`/absent (`server/hmp_plugin/gate.py:41-63`); `write_gate` is `CLOSED` unless both `no_defer` and `atomic_anchor` are `true` (`gate.py:83-87`, mirroring HMP_V1.md GU-4). |

This confirms the task's premise with file:line evidence, not just the prior research summary.

### 1.2 What stock Hermes (including the owner's build) actually does with an inbound message

Absent `defer_policy="reject"`, `BasePlatformAdapter.handle_message` on stock builds does **not**
refuse a message when the session is busy — it queues, debounces or interrupts, per config:

- `gateway/platforms/base.py:3950` `handle_message` sets `event._gateway_accepted = False`, then
  either dispatches immediately or (if the session is already active) calls
  `_handle_message_while_active` (`base.py:3992`).
- `_handle_message_while_active` (stock-base): bypass commands dispatch inline; otherwise a text
  follow-up is **debounced/merged** (`_is_queue_text_debounce_candidate`, `base.py:4045-4050`,
  `busy_text_mode=queue`) or handled by `_busy_session_handler`, i.e. **queued against whatever the
  conversation looks like when it eventually runs**, not against the head the client observed at
  submit time.
- This is exactly the FZ-R-9 risk the write gate exists to close: "a first submission could be
  deferred and executed later against a changed conversation" (`HMP_V1.md` GU-4, line 706).

Stock Hermes does give one thing HMP can use for **duplicate suppression** even without
`defer_policy`: `SessionDB.has_platform_message_id(session_id, platform_message_id)`
(`stock-base/src/hermes_state_messages.py:1491-1500`), described in-source as "the gateway's
transient-failure dedupe", plus the append path's own `platform_message_id` column
(`hermes_state_messages.py:283,305`). This is real, but it detects "did *this id* already write a
row", not "will Hermes ever admit a *second, different* attempt against a stale head" — it does not
give atomicity or a busy-refusal.

### 1.3 Option A — HMP v1 guarantees as specified (needs Hermes changes)

**What it is.** Wait for (or land) HP-6 (`PLATFORM_ADAPTER_CAPABILITIES`) and the P2/P3 admission
work (`defer_policy="reject"`, `AdmissionPrecondition`) upstream, exactly as prototyped in
`experimental`. Once a build advertises `defer_policy_reject >= 1` and `admission_precondition >=
2`, GU-4 opens the write gate and F2 ships exactly per HMP_V1.md §7-§9 as already designed
(SUB-1..SUB-10, CL-1..CL-7).

**What would need to land upstream**, per `DURABILITY.md` Q3's per-symbol status table and the P0
recommendations:

1. `gateway.platforms.base.PLATFORM_ADAPTER_CAPABILITIES` (HP-6) — a versioned, monotonic capability
   map read by symbol-version, never by presence (`experimental/src/gateway/platforms/base.py:1898-1906`
   documents the exact contract HMP already assumes).
2. `MessageEvent.defer_policy="reject"` honoured at **every** deferral/queue site, including the
   fail-closed edges DURABILITY.md's `defer_policy_reject` comment enumerates: no handler wired, no
   busy-session runner wired, task-cancelled-before-start, and the generic catch-all
   (`experimental/src/gateway/platforms/base.py:1912-1919`).
3. `AdmissionPrecondition` (compare-and-send) checked **atomically** with the append, "including the
   turn-start compaction commit" and "fails closed" (`base.py:1921-1932`, describing v2's two checks:
   the lease-level check and the transaction-level compare-and-append backstop reachable from every
   writer, including compaction).
4. `BasePlatformAdapter.on_message_admission` / `on_turn_settled` callbacks Hermes actually invokes
   (the `exec_approval_request_id`/`turn_settled` capability rows, same file).
5. Independent verification of RV-3/RV-4 (the admission and compaction obligations OD-F3 names)
   before any build is admitted to the write-supported matrix.

**Correctness.** This is the only option that gives HMP_V1.md's full guarantee set: no lost or
duplicated sends across retries or restarts (SUB-3's idempotency plus `atomic_anchor`'s
compare-and-append), a definitive `busy` refusal (P2's `defer_policy="reject"`), and confirmed
settlement (`confirmed_settle`). It is the design the rest of the contract (§7-§9) was written for.

**Cost.** Upstream PRs are out of scope for this phase entirely (`AGENTS.md`: "Not authorized: ...
upstream submissions"; `R0_OWNER_DECISIONS.md` OD-2: "targeted upstream Hermes PRs for generic
primitives... every upstream proposal must be generic"). Timeline is not ours to control, and the
owner's build tracks upstream `main`, not the experimental branch, so shipping F2 this way means
waiting for someone else's merge decision.

### 1.4 Option B — reduced guarantee set on stock Hermes via `handle_message` + `message_id` idempotency

**What it is.** HMP sends through the documented, stable inbound path
(`adapter.handle_message(event)` — `DURABILITY.md` Q3 marks this "No" for gap status, i.e. it is
already the supported inbound seam) with `MessageEvent.message_id = <client_message_id>`, and
implements SUB-7/SUB-8-style lookup using `SessionDB.has_platform_message_id` (E-GAP-6/7, already a
read-bridge dependency for F1) instead of Hermes-side `defer_policy` admission. The write gate
becomes a **new, explicitly reduced** gate (call it `write_gate.state == "open_reduced"` or similar
— an owner decision, §2) that opens on any build satisfying a *lower* floor: the read-compatible
list plus a `handle_message`/`has_platform_message_id` capability probe, not the GU-2 map.

**What it honours and what it explicitly does not:**

| Property | Option B |
|---|---|
| Duplicate suppression for the *same* `client_message_id` | Yes — `has_platform_message_id` is a real, indexed lookup (`hermes_state_messages.py:1491-1500`) |
| No lost sends across a client retry | Only if the client never retries under a *new* id before confirming the old one — same CL-4/CL-5 discipline as F1, unaffected by this option |
| Refusal instead of silent defer when busy | **No.** Stock `handle_message` queues/debounces/merges by default (`base.py:3992-4050`); there is no `busy` refusal without `defer_policy="reject"`. This is the guarantee HMP_V1.md's GU-4 was written to withhold precisely because of this gap. |
| Atomic compare-and-send against a stale head | **No.** No `AdmissionPrecondition` equivalent exists on stock Hermes; a send can be admitted against a conversation that has since compacted or changed underneath it. |
| Confirmed turn settlement | **No** — `confirmed_settle` still requires the same missing capability signal; F1's `EV-6`/`turn.ended` fallback (`confirmed:false`) applies unchanged. |
| Stop | Unaffected — `/stop` already always forwards regardless of the write gate (INT-5, GU-4's permanent exception), independent of this option. |

**Correctness bottom line.** Option B removes the two things HMP_V1.md's write gate exists to
prevent (silent deferral, stale-head execution) and replaces them with an owner-accepted residual:
"a send may be admitted at a different point in the conversation than the client anchored to, and a
send made while the bot is busy queues/merges/interrupts per Hermes's own config instead of being
definitively refused." This is not a smaller version of the HMP v1 contract — it is a **different,
weaker contract** that must be named as such on the wire (a distinct `write_gate` state, never
`"open"`) so a client cannot mistake it for GU-4's guarantee.

**Where it's honest and useful anyway.** For an *owner-only, single-active-session* usage pattern
(one person, one phone, not racing the CLI), the residual risk is bounded: no concurrent writer
means "stale head" and "busy" are rare in practice, not absent by contract. That is a materially
different risk profile than "any HMP client, any time" — which is exactly why OD-F3 requires this
to be an explicit owner decision, never a default.

### 1.5 Option C — PR 106742's durable admission (`admit_native`), if/when it merges

**What PR 106742 actually does**, read from the scratchpad extraction (unmerged, head
`d7f5c13d73784b4e536bf6fe0d20a48089523ec0`):

- `SessionAuthority.admit_native(event)` (`pr106742/gateway/session_authority.py:232-247`) is the
  entry point a platform adapter would call. It runs `prepare_native`, resolves the session, then:
  ```python
  row = admit_session_input(self.db, epoch=self.epoch, principal_id='messaging:' + identity,
                            session_id=ref.session_id,
                            request_id=str(payload['native_text_v1']['event']['message_id'] or uuid.uuid4().hex),
                            payload=payload)
  event._gateway_accepted = True
  ```
  — `request_id` is derived **from the event's own `message_id`**. If HMP sets
  `MessageEvent.message_id = client_message_id`, the durable admission's `request_id` *is* the HMP
  `cmid`, and `event._gateway_accepted = True` fires only after the durable commit, not before.
- `admit_session_input` (`pr106742/hermes_state_runtime.py:86-114`) is a **real compare-and-commit
  idempotency store**: it looks up `(principal_id, target_session_id, request_id)`, and if a row
  already exists, compares a `payload_digest` (`admission_fingerprint`, computed from the canonical
  target and payload) — an identical payload replays the stored row, a different payload raises
  `RuntimeStoreError('admission_conflict')` (`hermes_state_runtime.py:104-107`). This is **structurally
  the same shape as HMP_V1.md SUB-3**: scope key, payload hash, same-payload replay, different-payload
  conflict (compare `SUB-3`'s "`payload_hash = SHA-256` over the canonical `(text, base_message_id,
  attachments=[])`... A different payload returns `409 idempotency_conflict`", `HMP_V1.md` lines
  566-569). Only Hermes owns this store now, not HMP.
- **Durability across restart.** `recover_native_sessions` (`session_authority.py`, the block
  following `admit_native`) rejects unbound sessions and raises `RuntimeStoreError('unknown_execution')`
  when any admitted row's status is `'unknown'` (mirrored in `claim_session_input`,
  `hermes_state_runtime.py:130-139`, same check). This is exactly the "`unknown` after restart" state
  named in the task brief: a send admitted just before an owner-side crash/restart can come back as
  `unknown`, pausing that session until resolved — a state a client needs a UX for (§3.7; this is the
  background/fallback Option C path specifically, not Option D's own guard, §1.9.3).
- **P6 (authorize trigger) evidence, same PR, already run** (`DURABILITY.md` "P6 under the new
  durable admission FIFO"): unapproved-user inbound returns *before* admission (zero admissions, zero
  model calls); approved-user inbound never reaches `admit_native` for the fixed authorize text
  (no trigger outside `PENDING_OPERATOR`); the RV-7 approval race, if it fires, now creates a
  **durable** `intent=queue` admission instead of an in-memory one — same accepted residual, more
  durable now.
- **`defer_policy` is still absent on this PR's base** (`grep -rn defer_policy pr106742/gateway`
  returns nothing) — PR 106742 replaces the *admission/idempotency* half of what HP-6+P2/P3 promise,
  not the busy/defer half. `DURABILITY.md`'s own read: "P2's busy-bot 'reject' is an
  experimental-build-only guarantee, as RV-7 already states."

**Correctness.** Option C is strictly stronger than Option B on the two axes that matter most —
duplicate execution (real compare-and-commit, not just a dedupe probe) and lost-after-restart
detection (explicit `unknown_execution`) — but it does **not** by itself supply `atomic_anchor`'s
compare-and-append against `base_message_id`/conversation head (SUB-3's Hermes-side precondition is
a *different* mechanism than admission idempotency: idempotency stops a duplicate *attempt*;
`atomic_anchor` stops a *first* attempt from landing against a head the client didn't anchor to). It
also does not supply `no_defer`'s busy-refusal — a queued admission still runs later, merged or
interrupted per Hermes's own policy, same as Option B. So Option C should be read as **"Option B's
idempotency half, done properly by Hermes instead of approximated by HMP,"** not as a full
replacement for Option A.

**Durability against upstream churn.** Better than pinning to `experimental` (a fork HMP does not
control), because PR 106742 targets `main` and, if merged, becomes the ordinary upstream path every
future build inherits — consistent with the plugin-durability report's core finding that
`experimental`-only capabilities cannot be a shipping strategy (`DURABILITY.md` risk R1: "the
owner's build is unsupported today... between two 3-day-apart builds, 11 of 16 bridge files
changed"). It is currently **unmerged**, so it carries normal pre-merge risk (shape may still change,
no upstream commitment yet).

### 1.6 Comparison table

| Axis | A (upstream HP-6+P2/P3) | B (stock, `message_id` dedupe) | C (PR 106742 `admit_native`) |
|---|---|---|---|
| Duplicate-attempt correctness | Full (GU-2 admission + SUB-3) | Partial — dedupe probe, no atomic commit-time conflict check | Full — real compare-and-commit idempotency (`admit_session_input`) |
| Lost-send / stale-head correctness | Full (`atomic_anchor`) | **None** — no compare-and-send | **None by itself** — `admit_native` has no `base_message_id` precondition; would need pairing with a head check (§3.2) |
| Ack semantics client can rely on | `200 accepted` only after Hermes admits | Fire-and-forget `event._gateway_accepted` set pre-dispatch, in-memory, non-durable (`handle_message`, `base.py:3950-3987`) | `_gateway_accepted=True` only after the **durable** admission commit — a real ack boundary |
| Busy behaviour | Definitive `409 busy` | Hermes's default queue/interrupt/merge, config-dependent, never a defined client-visible refusal | Same as B — admission still resolves later per the drain's own policy |
| Streaming reply visibility | Out of scope (F1 excludes SSE); same for F2 v1 (§3.4) | Same | Same |
| Restart durability | Full — admission is durable by definition of the guarantee | **None** — in-memory guard only, a restart silently loses the fire-and-forget send | Explicit `unknown` state on restart — worse UX than "just works," better than silent loss |
| Security surface added | None beyond existing HERMES_API_GAP list | New `HERMES_API_GAP`: relies on `has_platform_message_id`, a private `SessionDB` method (already E-GAP-6/7) | New `HERMES_API_GAP`: `admit_native`/`SessionAuthority` internals, currently private, PR-only |
| Durability against upstream churn | High once merged; today, in limbo | Low — depends on `handle_message`'s current busy-dispatch internals, which are not part of the documented compat contract (`DURABILITY.md` Q2/Q3) | Medium — unmerged but targets `main`; better shape than a permanent fork dependency |

### 1.7 Recommendation — RULED (OD-N1/OD-N2, 2026-09-27), superseded as the primary mechanism by OD-N3 (below)

**Status update.** The OD-N1/OD-N2 ruling below was made first (relayed alongside OD-N3's *scope*
ruling). The owner's later, separate ruling on OD-N3's *mechanism* ("reply directly with a guard",
§1.9) is more specific and — per this project's rule that a later, more specific ruling controls —
now describes the actual primary send transport. This section is kept because it is still the
correct record of *that* ruling and because Option D (§1.9) reuses its idempotency design almost
verbatim; read it as background for Option D, not as the current primary-mechanism plan.

**v1 recommended Option C, contingent on PR 106742 merging, with Option B as a named fallback. The
owner ruled the inverse order: ship Option B now, gated to owner-only dogfood, and auto-upgrade to
Option C the moment the running host build exposes it — not waiting for a merge before shipping
anything.** This section is updated to match the ruling; v1's reasoning for *why* C is stronger than
B is unchanged and still governs the auto-upgrade design (§1.8):

- **Now: Option B, gated.** `write_gate.state == "open_reduced"` is reachable only when **both**
  hold: (a) the running build passes the reduced-write qualification probe (§3.6), and (b) the host
  operator has explicitly turned on the owner-dogfood gate (§3.2's new config flag, mirroring A1's
  own host-side kill-switch pattern, `A1-T08`). Because every paired device was itself confirmed by
  the operator at pairing time (SAS confirmation, PR3-2), "gated to the owner's own devices" needs no
  new per-device ACL: it is enforced by the existing pairing trust boundary (SEC-1's "operator
  boundary... up to the Hermes OS-user boundary") plus the new host-level opt-in flag, which only the
  operator can set. This is the *new* decision that lifts OD-F3's "no write-enabled dogfood in this
  phase" — narrowly, for this flag, on this deployment, never as a general precedent.
- **Automatic: upgrade to Option C on detection.** §1.8 (new) specifies the probe. The moment a build
  exposes PR 106742's `admit_native`/`admission_fingerprint` shape (or, later, upstream's own
  eventual name for the same mechanism), HMP switches the reduced gate's *mechanism* from B to C
  without any wire change visible to the client (`guarantee_level:"reduced"` stays the client-visible
  contract either way — §3.2, §3.3) and without needing a new owner ruling to do so, because the
  upgrade only ever **strengthens** the guarantee within the reduced tier the owner already approved,
  never opens the full, un-gated `"open"` state (that still requires the original GU-2 floors, §1.1,
  untouched by this section).
- **Eventual: Option A remains the un-gated target.** Nothing here changes v1's conclusion that
  `PLATFORM_ADAPTER_CAPABILITIES`/`defer_policy`/`AdmissionPrecondition` landing upstream is what
  opens GU-4's original, strongest `"open"` gate automatically, for every user, not just the owner's
  dogfood devices. The reduced mode is a bridge to that, not a replacement for it.
- **Do not build Option A's exact machinery speculatively**, unchanged from v1 (OD-2: "do not move
  Hermes Bot Mobile product semantics into Hermes core for convenience").

**Single biggest risk of the ruled plan:** the auto-upgrade detector is the new load-bearing
component (it did not exist in v1's plan, which treated B and C as separate, manually-chosen ship
targets). A detector that mis-classifies a build — claiming Option C's stronger guarantee on a build
that does not actually have it, or silently missing a build that does — is now a **wire-visible
correctness bug**, not just a missed optimization, because `guarantee_level` is client-facing. §1.8
specifies the detector as probe-verified (never symbol-presence-only, GU-3's existing discipline)
specifically to bound this risk; see R-C1 (revised) and new R-C9/R-C10 in §6.

### 1.8 Auto-upgrade detection: Option B → Option C (new, per OD-N1/OD-N2 ruling)

**Goal.** On every process start (and only then — never mid-conversation, matching the "prompt
caching is sacred... never mid-conversation" discipline the hermes-developer skill states for
capability changes), the running build is probed once and classified into exactly one of three
mechanisms for the reduced gate: `none` (write gate stays fully closed), `"B"` (stock
`handle_message` + `has_platform_message_id`), or `"C"` (PR 106742-shaped durable `admit_native`).
The result is cached for the process lifetime, mirroring how GU-2's own capability derivation is
read once and not re-polled per request.

**Probe, in order (cheapest and most certain first), extending `compat.py`'s existing
`READ_DEPENDENCIES`/`probe_read_dependencies` pattern with a parallel `WRITE_DEPENDENCIES` probe run
only when the reduced-gate host flag (§3.2) is on:**

1. **Symbol existence check (necessary, never sufficient alone — GU-3's rule applied to this new
   probe):** does `gateway.session_authority.SessionAuthority.admit_native` (or the dependency
   spec's configured dotted path, so a future upstream rename is a one-line config change, not a code
   change) exist, importable, with the expected parameter shape (`inspect.signature`, matching
   `admit_native(self, event)`, per `pr106742/gateway/session_authority.py:232`)? If absent →
   candidate mechanism is `"B"` (if `has_platform_message_id` exists, `stock-base` path — see below)
   or `none`.
2. **Behavioral confirmation (required before advertising `"C"`, never symbol presence alone,
   matching gate.py's existing GU-3 "downgrade only, never upgrade on symbol alone" discipline):**
   in an isolated scratch session created for this purpose only (never a real user's session), submit
   one synthetic admission through the candidate `admit_native` path with a known `message_id`, then
   (a) submit the **same** `message_id` again and assert the same row/receipt is returned
   (`admit_session_input`'s payload-digest replay, `pr106742/hermes_state_runtime.py:104-107`), and
   (b) submit a **different** payload under the same `message_id` and assert a distinguishable
   conflict outcome (`RuntimeStoreError('admission_conflict')`, same file `:106`). Both must pass for
   the build to classify as `"C"`; a partial match (symbol present, behavior does not match) falls
   back to `"B"` and logs the inconsistency, exactly as `cross_check_guarantees` already does for
   GU-3 (`gate.py:69-79`).
3. **`has_platform_message_id` probe (for `"B"`):** does `hermes_state.SessionDB.has_platform_message_id`
   exist with the expected signature (`stock-base/src/hermes_state_messages.py:1491`)? If neither
   probe passes, the reduced gate never opens (`none` — same as today's fully-closed default), and no
   bridge call for either mechanism is attempted, matching ERR-2a's existing "make no bridge call"
   discipline for an unqualified build.

**This is a new, third `WRITE_DEPENDENCIES`-style probe, not a reuse of GU-2's `capabilities` map** —
it deliberately does not touch `PLATFORM_ADAPTER_CAPABILITIES` at all (that map stays reserved for
the full, un-gated guarantee set, §1.1). It is its own qualification path, feeding its own matrix
entry (§3.6's `reduced_write_supported_builds.json`, extended with a `"mechanism":"B"|"C"` field per
build, populated by the same human-reviewed process as every other build list — not scheduled by a
specific task number in this revision's list, §5, since it is the background/fallback path only).

**What the client sees.** Nothing new. `guarantee_level:"reduced"` is unchanged whether the server is
running mechanism B or C underneath — the *auto-upgrade* is a pure server-side strengthening. A
client written against v1's design needs no change to benefit from the upgrade. (A future contract
revision **may** choose to surface the mechanism for diagnostics only, e.g. a `guarantee_mechanism`
field on `/ready`, additive per V-3 — not required for F2 v1, recorded as a nice-to-have, not a
decision this document needs the owner for.)

### 1.9 Option D — RULED (OD-N3 mechanism, 2026-09-27): `api_server` session_chat + HMP-side guard

**This is now the primary send mechanism this design targets.** It reaches an arbitrary existing
session directly (satisfying OD-N3's scope ruling in full, not just in spirit — no fork, no
divergent lineage), by calling the same `POST /api/sessions/{session_id}/chat` (non-streaming) route
investigated in §3.1.1, but from **inside** the guard design the owner specified rather than bare
and unguarded. Full guard mechanics are in §3.1.8; this section covers the transport itself.

#### 1.9.1 Reaching the route: loopback, credential, route shape, enablement — CORRECTED (v4, review findings #1/#2/#3/#6)

- **Route shape, corrected.** The route is `POST /api/sessions/{session_id}/chat`
  (`api_server.py:1738`), and it is mirrored **verbatim**, path unchanged, under `/p/<profile>`:
  `self._app.router.add_route(method, f"/p/{{profile}}{path}", handler)`
  (`api_server.py:4429-4431`). So HMP's own request path is:
  - `POST /api/sessions/{session_id}/chat` when HMP's served profile is the default profile;
  - `POST /p/<profile>/api/sessions/{session_id}/chat` when it is a named secondary profile.

  **v3's claim that the secondary path is `/p/<profile>/v1/...` was wrong** — `SHARED_LISTENER_MIRROR_PATHS
  = {"api_server": "/v1", ...}` (`gateway/config.py:291`) documents where the **OpenAI-compatible**
  surface (`/v1/chat/completions` etc.) and `GET /v1/capabilities` are mirrored; it says nothing about
  `/api/sessions/...`, which the router mirrors through the separate, generic
  `add_route(method, f"/p/{{profile}}{path}", handler)` call applied to *every* route in
  `_http_route_table()`, unconditionally. Fixed for good by reading the actual router-construction
  code, not a docstring-adjacent constant whose name looked relevant.
- **Body field, corrected.** `_session_chat_user_message` reads `body.get("message") or
  body.get("input")` (`api_server.py:661-665`) — **not** `text`. HMP's loopback request body is
  `{"message": <text>}` (or `"input"`, but the design standardizes on `"message"`); HMP's own wire
  field stays `text` (§3.2's `POST /hmp/v1/.../messages` body is unaffected — this translation happens
  only inside the server's own loopback call construction, invisible to the phone).
- **Credential, corrected: per-profile coupling, never inferred from capabilities.** Hermes couples
  the key to the profile the request is scoped to, and HMP must reproduce that coupling exactly, not
  assume one key works everywhere:
  - **Default profile:** the key is `self._api_key`, resolved once at `connect()` from
    `extra.get("key")` or `_get_scoped_secret("API_SERVER_KEY", "")` (`api_server.py:1191`), and
    `connect()` itself refuses to start the listener at all unless that value is present and
    `has_usable_secret(..., min_length=16)` (`_api_key_passes_startup_guard`, `api_server.py:4363-4390`).
    **Practical consequence HMP can rely on:** if the default listener answers at all (the route probe,
    §1.9.1 "Enablement" below, succeeds), its key is already a real, strong secret — Hermes's own
    startup guard already proved that, HMP does not need to re-derive strength.
  - **A named (secondary) profile:** `_expected_api_key()` does a **fresh**, independently-scoped
    lookup, `agent.secret_scope.get_secret("API_SERVER_KEY", "")`, checked again for
    `has_usable_secret(min_length=16)` (`api_server.py:1529-1544`) — **never** the default's
    `self._api_key` value. A secondary profile with no key of its own configured 401s
    unconditionally (`_check_auth`'s "named profiles fail closed rather than inherit the owner's
    key", same file, comment at `:1554`).
  - **HMP therefore reads the key server-side per target profile**, using
    `get_scoped_secret("API_SERVER_KEY", "")` scoped to *that* profile (the same documented,
    plugin-usable helper, `gateway.platforms._shared.get_scoped_secret`, `DURABILITY.md` Q3), never
    reusing a value read for a different profile, and never persisting or logging it (SEC-4).
  - **`/v1/capabilities`'s static `session_chat: true` flag proves nothing about key validity** — it
    is a fixed, always-`True` entry in `_STATIC_FEATURE_FLAGS` (`:70`), unconditional on auth state.
    HMP's own route probe (§3.6) must therefore include an authenticated call, not just the
    capabilities check, to learn anything about whether *this* profile's key actually works.
  - **`401` from the loopback call is treated as "this instance's write gate is closed for this
    profile"** — `write_gate` reports `"closed"`, not `"open_guarded"`, and HMP does not retry with a
    different key, guess at one, or fall back to the default profile's key for a secondary profile's
    request. This is the SHOULD-FIX the review raised (finding #6/§5's "treat 401 as gate-closed").
- **`api_server` must be enabled on the target profile, under the multiplexed root gateway.**
  Unchanged conclusion from v3, with the path detail corrected above:
  1. Under multiplexing, only the default profile ever binds api_server's port; a secondary profile's
     api_server is a mirror on the default's own listener, never a second listener
     (`gateway/config.py:280-292`: `PORT_BINDING_PLATFORM_VALUES` includes `"api_server"`;
     `SHARED_LISTENER_MIRROR_PLATFORMS = frozenset({"api_server", "webhook"})`). Confirmed in the
     reconciler: `gateway/run_adapters.py:1171-1177`.
  2. The owner's default profile has no `API_SERVER_*` configuration today, verified directly and
     read-only (name-only check, no secret values read): `grep -n api_server ~/.hermes/config.yaml`
     and `grep -o '^API_SERVER_[A-Z_]*' ~/.hermes/.env` both return no match. This is the live-config
     change §5's owner-action task names.
- **Loopback bind enforcement — new in v4 (review finding #6, BLOCKER).** `listen_address(extra)`
  resolves `host = extra.get("host", os.getenv("API_SERVER_HOST", "127.0.0.1"))`
  (`api_server.py:214-225`) — config wins over env, default is loopback, but **neither Hermes's config
  loader nor `connect()` refuses a non-loopback bind**; `is_network_accessible(self._host)` only logs
  a warning ("Agent work dispatched through this endpoint runs as the host user with full
  terminal/file access", `api_server.py:4441-4456`). **HMP MUST independently refuse to use this
  mechanism unless it can positively confirm the bind is loopback**:
  - HMP reads the same two config points `listen_address` reads (the profile's
    `platforms.api_server.extra.host`, via the same `gateway.config` dependency it already has, then
    `API_SERVER_HOST`) and applies the same precedence, deliberately **not** importing
    `listen_address` itself (that would pull in `api_server.py`'s module, reintroducing the
    private-adapter-import risk §1.9.1 was written to avoid) — instead, a small, independently
    tested copy of the same two-line precedence, checked against the real function's output as part
    of qualification (§3.6's route probe).
  - The resolved host MUST be `127.0.0.1`, `::1`, or a name that resolves *only* to a loopback address
    at the moment of the check — no DNS-resolved hostname is trusted blindly. **If the host cannot be
    determined (a config read failure, an unexpected value), HMP fails closed**: the write gate never
    reports `"open_guarded"` for that profile. This mirrors `try_acquire_active_session`'s own
    "ownership uncertainty fails CLOSED" discipline (`hermes_cli/active_sessions.py`, cited already in
    §3.1.8), applied to a bind check instead of a lease check.
  - HMP's own outbound request is pinned to the resolved loopback literal (`127.0.0.1`/`::1`), never a
    hostname, closing the "DNS rebinding" class of concern as a side effect.
- **HTTP client: async, no proxy environment, never blocking the gateway loop — new in v4 (review
  finding #6).** HMP's loopback call uses `aiohttp.ClientSession(trust_env=False)` (aiohttp is already
  a core Hermes dependency, `DURABILITY.md` Q9/Q10) — `trust_env=False` means the client **never**
  reads `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` or any proxy-adjacent environment variable, so the
  Bearer token can never be sent off-box via a configured proxy, regardless of the operator's shell
  environment. The call is `await`ed directly on HMP's own coroutine — **no `asyncio.to_thread`** —
  because it is genuine async I/O on a socket, not blocking work; DURABILITY.md Q4 already establishes
  that "adapter coroutines run on the gateway's single event loop," and an async HTTP client is
  exactly the kind of I/O that loop is designed to interleave, unlike the blocking `SessionDB` calls
  HMP's read bridge already wraps in `to_thread` for a different reason (those are synchronous SQLite
  calls with no async form; this is a real async socket operation with one).
- **Enablement is a config axis, not a source-code axis** — unchanged from v3: whether api_server is
  enabled, and whether its bind is loopback, are per-deployment configuration facts, independent of
  which Hermes build is running. This is Option D's own, third gate axis (alongside the profile-scoped
  key and the route-shape probe, §3.6), never a `read_compat_builds.json`-style build list entry.

#### 1.9.2 Resolving the target session — REWRITTEN for OD-N10: the canonical Bot Chat, not an arbitrary `session_ref`

**OD-N10 (2026-09-27) narrows the send target to exactly one session per bot: the session Hermes
Desktop's own Bots view shows** — never a `session_ref`-addressed arbitrary A1-browsed session. This
section replaces v3's `session_ref`-mapping design with the actual selector, read directly from the
Desktop client and the shared server-side helper it and `tools/bot_live_delivery.py` both already
use.

**The exact selector, with evidence:**

- **Each bot has exactly one "forever chat," identified by name, never by a stored pointer**: the
  session on that bot's own Hermes profile whose `title` is exactly `"Bot Chat"`
  (`apps/desktop/src/plugins/hermes-bots/canonical-chat.ts:20-28`, `CANONICAL_CHAT_TITLE = 'Bot Chat'`,
  docstring: "Each bot has ONE forever chat, identified by NAME... the core `UNIQUE(title)` index makes
  `(profile, "Bot Chat")` an exact registry... Stored-id pins... are REMOVED: every lost-chat incident
  traced to a dangled or stolen pointer"). The same constant, same value, appears server-side as
  `BOT_CHAT_TITLE = "Bot Chat"` (`tools/bot_mode_probe.py:31`, "the only session title that receives
  the protocol section... Must match the desktop plugin's `createCanonicalChat` title and the `-c
  "Bot Chat"` resume target") and is exactly what `tools/bot_live_delivery.py:32-49`'s
  `find_canonical_owner` already resolves (`db.get_session_by_title("Bot Chat")`, then
  `db.get_compression_tip(row["id"])` for the live lineage tip) — the same function `api_server.py`'s
  own `_admit_to_live_bot_chat` already calls (§1.9.1/§3.1.1). **HMP resolves the send target with
  this exact call, server-side, per profile** — no new lookup, no new table, the same primitive three
  independent parts of Hermes (Desktop, the CLI resume target, and api_server's own mailbox check)
  already agree on.
- **The Bots view opens and always operates on this one session, never an alternative.**
  `openBotCanonicalChat` (`canonical-chat.ts:547-577`) is the click-to-open path: find the existing
  `(profile, "Bot Chat")` row and open its lineage tip, or create it if absent. `last_session`
  (`data.ts:1494-1512`, "the profile's newest visible conversation... Canonical Bot Chats are hidden
  from the session list by design") is a **roster-row activity/preview signal only** — it decides what
  a bot's row shows as its "last active" timestamp, it is never an alternative chat-pane target. There
  is no "New session" multi-tab concept for a bot's own chat in this codebase; a bot has exactly one
  chat surface, and it is this one. This directly answers the coordinator's question: **the bot view
  lists (and opens) exactly one session per bot, never more.**
- **Alignment with A1.** The coordinator states A1's own session-browsing list is being narrowed to
  the same bot-view selector in parallel (on `f1/w-sessions-design`, not this branch). This design
  uses the **identical** selector (`(profile, "Bot Chat")`, live compression tip) so that, once both
  land, the session a mobile reply targets and the session A1's `is_mobile`-equivalent flag would mark
  as "the bot view" are provably the same row — a single shared definition, not two independently
  derived ones that could drift. This document does not edit A1's own spec; it records the dependency
  so the controller can fold the two together at merge.
- **Consequence for F1's existing `/conversations/default`.** F1 shipped a *separate*,
  mobile-originated conversation (`conversation_ref(user_id, profile)`, `bridge.py:483-502`, an
  HMP-originated session distinct from any Desktop Bot Chat, per `CON-1`/`CON-3`). OD-N10's "one
  channel at a time" framing reads as rejecting that separation for the *write* path going forward:
  the mobile app's conversation with a bot should be the same canonical Bot Chat Desktop shows, not a
  second, disconnected mobile-only lineage (which is exactly what v2's rejected fork-and-seed
  proposal would have perpetuated, and what F1's original mobile-only conversation already was).
  **This document's recommendation: F2 sends target the canonical Bot Chat exclusively; F1's
  `/conversations/default` read route can continue to exist for backward read-compatibility, but a new
  send should not create or grow a second, separate mobile lineage.** This is a real, load-bearing
  design change to F1's existing model, not a small addendum, and needs explicit owner/controller
  confirmation before implementation — it is flagged, not silently assumed (§2 decision table,
  OD-N3/target-session-scope row).

#### 1.9.3 Relationship to Options B/C

Option D does not depend on `defer_policy`, `AdmissionPrecondition` or `admit_native` at all — it
substitutes an HMP-engineered guard (client-declared head, HMP-side liveness read, HMP-side
idempotency store, post-hoc verification) for the Hermes-side admission guarantees B/C were built
around. This has one significant advantage over both: **Option D's qualification does not depend on
which Hermes build is running** (`try_acquire_active_session`, `active_session_registry_snapshot` and
`api_server`'s session_chat route are all present, structurally identical, on `stock-base`,
`experimental` and the owner's own `8afaab37` — none of them are experimental-only or
PR-106742-only). It trades that build-independence for a real, quantified residual race (§3.1.8) that
Option A's true atomic admission would close and Option D cannot. **Options B/C's idempotency design
(client_message_id dedupe, an HMP-side record of accepted ids) is reused verbatim inside Option D's
guard (§3.1.8's "Idempotency")** — this is not wasted work from v2, it is the one piece of B/C that
survives into the ruled mechanism unchanged.

---

## 2. Decision table — owner decisions this design needs

Numbered `OD-N#` ("N" for "next feature") to avoid colliding with `R0_OWNER_DECISIONS.md`'s `OD-F#`
series. Each needs an explicit ruling before F2 implementation is authorized; none of them is
decided by this document.

| # | Decision | Options | Status / recommendation |
|---|---|---|---|
| **OD-N1** | Which correctness path does F2 target? | (A) wait for upstream HP-6+P2/P3; (B) ship a reduced-guarantee mode on stock Hermes now; (C) build against PR 106742's `admit_native`, contingent on merge | **RULED (2026-09-27): B now, auto-upgrading to C on detection** (§1.7, §1.8) — the owner chose the inverse of v1's recommended order (v1 recommended C-first, B-fallback). |
| **OD-N2** | Is a reduced-guarantee write mode ever acceptable, and to whom? | Never; owner-only dogfood only, gated by a new OD; general release once qualified | **RULED (2026-09-27): owner-only dogfood only**, gated by a new host-side opt-in flag (§3.2) enforced through the existing pairing trust boundary. This is the decision that lifts OD-F3 for exactly this case — the controller should record it in `R0_OWNER_DECISIONS.md`'s own series; this document does not renumber that file. |
| **OD-N3 (scope)** | Which session does a mobile send go to — the phone's own HMP conversation, or an existing non-HMP session (e.g. continuing Desktop's session, per OD-F9/OD-F10)? | HMP-only conversation; true same-session injection into an existing Desktop/CLI/other-platform session | **RULED (2026-09-27): must support sending into ANY session** (A1-browsed or not). |
| **OD-N3 (mechanism)** | How is a same-session send made safe, given §3.1's finding that no mechanism is both a true same-session write path and double-writer-safe without a new guard? | Fork-and-seed (v2's recommendation, a divergent copy, never truly same-session); a client-declared head precondition plus a server-side liveness/busy guard around a true same-session write (`api_server` session_chat) | **RULED (2026-09-27), verbatim: "Reply directly with a guard. Remember our plan to check if it's the latest message or fail. We only send messages when all messages are in sync between device and mobile."** True same-session write via `api_server`'s `POST /api/sessions/{session_id}/chat`, guarded (§1.9, §3.1.8). Fork-and-seed is demoted to a rejected alternative (§3.1.7), kept only as documentation of why it was considered and set aside. |
| **OD-N3 (target-session scope, superseded by OD-N10)** | Which sessions, among "any session," does a send actually need to reach? | Every session A1 can browse (Desktop, CLI, Telegram, Discord, ...); only the sessions Desktop's own Bots view shows for a bot | **RULED (2026-09-27), verbatim: "Right now, bot chats are only done in one channel at a time. I don't think our app should communicate with terminal and Discord/telegram channels... just the ones from the bot view."** Only the canonical `(profile, "Bot Chat")` session (§1.9.2) — never CLI, Discord, Telegram or other channel sessions, even though A1 may still let those be *read*. |
| **OD-N4** | Busy behaviour the client must show, given no `defer_policy="reject"` on the target build | Definitive "bot was busy" (needs Option A); "message queued, may merge with what's already running" (Options B/C); refuse client-side and never send while turn is running | **Controller default, owner may override: "Queued, may run after/merge with the current turn"** — honest framing of Hermes's real default, not a promise HMP cannot keep. Client-side pre-check of `turn.observed_state` before allowing Send is a UX nicety, not a guarantee (`turn` is an HMP *observation*, PR-1). |
| **OD-N5** | Reply visibility without SSE (F1 excludes live stream; is it still excluded in F2 v1?) | Keep polling-only (repeat F1's `GET .../conversations/default` read path on an interval / pull-to-refresh); add a lightweight "new activity" signal; bring SSE in now | **Controller default, owner may override: keep polling-only for F2 v1** (§3.4) — SSE is a bigger transport/security surface (EV-1..EV-9) that is orthogonal to admission correctness and should not gate send. Revisit once F2's write path is proven. |
| **OD-N6** | Stop/cancel for a message that is queued-but-not-yet-running (Option B/C, no true `busy` refusal) | No cancel — rely on Hermes's own `/stop` once a turn starts; add a client-side "withdraw before it runs" using Hermes's own cancel-queued primitive if the target build exposes one | **Controller default, owner may override: use Hermes's existing `/stop` (INT-5) for a running turn only.** A queued-admission cancel (PR 106742 exposes `cancel_queued`, `session_authority.py`) is a new `HERMES_API_GAP` to evaluate only if Option C ships; do not build client UX promising cancellation of a not-yet-running send until that capability is confirmed reachable through the platform-adapter surface (§3.5). |
| **OD-N7** | Approvals/clarify raised mid-turn by a mobile-originated send (F1 excluded both; a send can now trigger one) | Still out of scope, show a stuck/blocked state; bring minimal read-only approval visibility into F2; full answer support | **RULED (2026-09-27): "Show it, answer elsewhere."** Read-only visibility only (F1's existing `approval.unanswerable`/clarify-read-only rendering, HMP_V1.md EV-7, INT-4) — confirms v1's recommendation. Answering stays a later feature (§3.8). |
| **OD-N8** | Automatic retry (F1 disabled it as CL-4's temporary limitation) — revisit now? | Keep disabled; enable per CL-4's future-rule conditions (a,b,c,d,e) | **Controller default, owner may override: keep disabled for F2 v1.** CL-4(c) requires `no_defer` and `atomic_anchor` both `true` *and* `write_gate` `open` — under the ruled reduced mode (B or its C upgrade) the gate is never the strong `"open"` state, so the condition cannot be met. No new decision needed here beyond "don't weaken CL-4 to fit a reduced mode." |
| **OD-N9** | Build qualification: does F2 need its own write-supported-matrix entry process distinct from GU-2c's read list? | Reuse GU-2a's matrix (`write_supported_builds.json`) unchanged; add a parallel "reduced-write-qualified" list for Option B/C builds | **Controller default, owner may override: add a distinct, separately-named list** (§3.6), now carrying a per-build `mechanism:"B"\|"C"` field per §1.8's auto-upgrade design — GU-2a's matrix is explicitly reserved for the *full* GU-2 guarantee set (OD-F3: "stays empty until the admission and compaction obligations... pass independent verification"); silently repurposing it for a weaker guarantee would violate PR-4 ("honest guarantees") and OD-F3 itself. |

---

## 3. Wire, UX and security design

Everything below is a **design**, not a spec-ready contract text — it is scoped to inform an eventual
HMP v1.x amendment (additive per V-3) or a v2 discussion, gated on OD-N1..OD-N9.

### 3.1 Which session a send goes to — RULED (OD-N3, 2026-09-27, mechanism; OD-N10, 2026-09-27, scope)

**v1's answer ("HMP-only conversation, out of scope for F2 v1") is superseded by the owner's rulings:
OD-N3 required the phone to reply into a real session with a guard; OD-N10 then narrowed which
session — only the one Desktop's own Bots view shows for a bot (the canonical Bot Chat, §1.9.2),
never a CLI-, Discord-, Telegram- or other-channel session, even one A1's read-only browsing might
surface.** This section preserves the original mechanism investigation (§3.1.1-§3.1.6) as the
evidence base for *why* the ruled mechanism needs a guard at all; §1.9.2 has the final, OD-N10-scoped
selector. All investigation below is read-only against the owner's actual build
(`~/.hermes/hermes-agent` @ `8afaab3703e336d72a72c812dd2dd249f04f166a`, confirmed by
`git rev-parse HEAD` in that checkout — never modified, never executed).

#### 3.1.1 Mechanism 1 — `api_server`'s `POST /api/sessions/{session_id}/chat`

**What it is.** A genuine, path-addressed "post a turn into an arbitrary existing session" route:
`_get_existing_session_or_404(session_id)` (`gateway/platforms/api_server.py:3155` region, called
from `_prepare_session_chat:3296`) accepts **any** Hermes session id, of any source, then
`_handle_session_chat` (`:3505-3541`) runs the turn synchronously through `_run_agent`
(`:4128-4230`), in-process, inside the same gateway process HMP's own plugin adapter already lives
in (one gateway process = one Hermes instance, OD-4; adapters share the gateway's single event loop,
`DURABILITY.md` Q4).

**Auth.** A **separate** credential: `API_SERVER_KEY`, required to even declare `X-Hermes-Session-Key`
(`_parse_session_key_header`, `api_server.py:1828-1832`, "requires API key authentication"), and
implicitly required for the route generally (the adapter's own bearer/API-key check, not shown in
the excerpt above but structurally separate from `api_server.py`'s admission wrapper
`@_admit_api_agent_request`). This is a **host-operator secret**, architecturally unrelated to HMP's
own per-device bearer tokens (P5). Reaching this route from HMP means either minting/holding a second
credential type the wire contract (§5, HMP_V1.md §5) was never designed to carry, or making HMP a
privileged holder of the operator's own API key — both are new security decisions, not wiring.

**Concurrency / double-writer risk.** `_run_agent` in `api_server.py` **does not call
`hermes_cli.active_sessions.try_acquire_active_session`** anywhere (confirmed: no match for that
name in `gateway/platforms/api_server.py`, vs. real matches in `cli.py:923`,
`tui_gateway/session_lifecycle.py:74`, and `gateway/run_busy.py:227`, the three surfaces that *do*
take the cross-process active-session lease before running a turn). The **only** guard against a
second writer is a narrow, purpose-built special case:
`_admit_to_live_bot_chat`/`_answer_through_live_bot_chat` (`api_server.py:3399-3448`) checks whether
the target session's compression tip equals `find_canonical_live_owner`'s session — a lease entry
whose metadata explicitly opts in with `bot_live_delivery_consumer: True` and a `live_session_id`
(`tools/bot_live_delivery.py:54-60`; the matching opt-in is written by Desktop's own
`tui_gateway/session_lifecycle.py:63-76`, `_lease_metadata`). **This fires only for one specific
Desktop feature (the title-`"Bot Chat"` session, per `find_canonical_owner`,
`tools/bot_live_delivery.py:32-49`, `db.get_session_by_title("Bot Chat")`), not for sessions in
general.** For an ordinary Telegram-, Discord-, CLI-(non-Bot-Chat)- or other-platform-originated
session — exactly what A1's OD-F9/OD-F10 exposes for reading — calling
`/api/sessions/{id}/chat` while that surface is concurrently live on the same session id is a **real,
unguarded double-writer race**: two `_run_agent`-equivalent calls can run against the same session
concurrently, with no fencing at all. This is the same class of risk `HMP_V1.md`'s own GU-4 exists to
prevent for the write gate generally (FZ-R-9), now at the session-ownership layer instead of the
message-admission layer.

**Plugin-surface fit.** Not documented as reachable from a platform-adapter plugin at all. The
platform-adapter guide (`DURABILITY.md` Q3, APA:95-99) documents `BasePlatformAdapter`,
`MessageEvent`, `Platform`/`PlatformConfig` and a handful of `gateway.platforms._shared` helpers —
never `api_server.py`'s own ~4,700-line private surface, which is a *different, sibling* platform
adapter (`_SESSION_SOURCE = "api_server"`, `api_server.py:1707`) with its own HTTP listener, own
route table and own session-provenance stamp. Reaching it means either (a) an HTTP loopback call to
that listener (needs the operator's `API_SERVER_KEY`, and every resulting row is attributed to
`source="api_server"`, not to HMP — a provenance mismatch A1's own `source` badge design (§4's
"Source badge") would then have to special-case), or (b) importing its private internals directly —
a large, brittle, undocumented `HERMES_API_GAP` far bigger than anything F1/A1 currently carry.

#### 3.1.2 Mechanism 2 — `tui_gateway` RPC (`session.resume` + prompt submit)

**What it is.** Desktop's own JSON-RPC surface (`tui_gateway/server.py`, `methods_session.py`).
`tui_gateway/session_lifecycle.py:69-88` (`_claim_active_session_slot`) **does** call
`try_acquire_active_session` before a turn starts, correctly participating in the same host-wide
lease `api_server` skips. This is, structurally, the *correct*, fenced way to attach to and drive an
existing session that might be live elsewhere.

**Auth and reachability.** Desktop's own loopback WebSocket protocol, with its own session/auth
model, entirely undocumented for third-party platform plugins — the platform-adapter guide never
mentions `tui_gateway` as a plugin-reachable surface (`DURABILITY.md` Q3's coverage table has no row
for it). Using it from HMP would mean HMP acting as a second, unofficial Desktop client speaking an
internal RPC protocol never designed for this — a materially larger and less stable `HERMES_API_GAP`
than any single internal HMP already depends on (HMP_V1.md §12's existing list is all `SessionDB`/
`runner` reads and the documented `handle_message` write path; this would be a new, whole-protocol
dependency).

#### 3.1.3 Mechanism 3 — ACP adapter

**What it is.** The Agent Client Protocol adapter (`acp_adapter/`) tracks one `acp_session_id` per
editor-integration client connection, mapped to a live Hermes `session_id` via
`acp_adapter/provenance.py` (`build_session_provenance`, `:32-38`, keyed off
`parent_session_id`/`end_reason`, the same lineage columns A1 already reads for compression chains).
It is built for one interactive editor client owning one session for the life of that connection —
not for "post one message into someone else's already-open session and disconnect." It is also not a
documented platform-plugin surface (a `kind: platform` adapter in Hermes's own taxonomy is the
messaging-style surface HMP already is; ACP is a distinct, protocol-specific adapter family). Not a
fit, for the same reachability reason as tui_gateway, and for a worse semantic mismatch (session
ownership is 1:1 with an editor connection by design).

#### 3.1.4 Mechanism 4 — `MessageEvent`/`SessionDB` routing (`build_session_key`, `profile_routes`)

**What it is.** The path HMP's own plugin already uses (`adapter.handle_message(event)`,
`DURABILITY.md` Q3: documented, "No" gap). A fresh `MessageEvent` is routed to a session via
`gateway.session.build_session_key(source)` (`build_session_key`, referenced at
`gateway/session.py:673` per A1 §1.4), which **computes** a key from `(ns, platform, chat_type,
chat_id, thread_id, user)` — it does not accept an arbitrary target session id. Two ways this could
theoretically reach an existing foreign session, both rejected:

- **Impersonate the foreign platform's identity** so `build_session_key` reproduces that session's
  stored `session_key` (the DB column A1 §1.2/§1.4 already identified as private, and explicitly
  recommended **never** disclosed on the wire, precisely because "it can embed a Telegram chat id, a
  Discord guild/channel id, a phone number... from **other people's** conversations"). Even granting
  HMP server-side read access to that column (which it already structurally could have, as
  Hermes-internal), constructing a `MessageEvent` that claims `source.platform == TELEGRAM` (etc.)
  risks tripping platform-specific branches inside `handle_message` gated on exactly that field (the
  Telegram-topic-recovery branch, photo-burst debounce, and others visible in
  `gateway/platforms/base.py:3950-4060`) — a fragile, easy-to-get-subtly-wrong impersonation, not a
  designed capability.
- **A generic "override target session" parameter to `handle_message`.** No such parameter exists in
  the documented or observed `MessageEvent`/`BasePlatformAdapter` surface (`DURABILITY.md` Q3's
  `MessageEvent` coverage: only `reply_expected` is new at `8afaab3703`, no session-override field).

This mechanism gets the fencing right (it is exactly `_claim_active_session_slot`'s own path,
`gateway/run_busy.py:213-243`, when the event is genuinely HMP's own), but has no supported way to
retarget an existing foreign session without impersonation.

#### 3.1.5 Mechanism 5 — PR 106742's "attach"

**What it is.** `pr106742/gateway/host_attach.py` exists, but it answers a **process**-level
question — "is there one live host gateway already serving this profile, or should this CLI/cron
invocation start its own?" (`ATTACH`/`RESCAN`/`REPLACE_HOST`/`REFUSE`/`START`, module docstring
lines 8-19) — not a **session**-level one. It is PR 106742's structural fix for exactly the class of
problem OD-N3 raises (today, independent CLI processes and the gateway can each become a writer),
but it works one layer up: by making one gateway process the sole owner of a *profile's* sessions, it
removes the CLI-vs-gateway race at the process level. It does **not**, by itself, ship a "client
attaches to canonical session id and gets fenced, cross-surface send access" API — `admit_native`
(§1.5) is the closest primitive, and it is a **message-admission** mechanism (idempotent write
queueing), not a **session-selection-with-liveness-fencing** one. Confirmed: no `attach`-named method
in `pr106742/gateway/session_authority.py` takes a session id and returns "this is safe to write
into, nobody else holds it" — `register(source)` (used inside `admit_native`, §1.5) resolves or
creates a session from a `source`, the same identity-driven resolution as stock Hermes's
`build_session_key`, not an arbitrary-session attach.

#### 3.1.6 Comparison, and the ruling

| Mechanism | Reaches an arbitrary existing session? | Double-writer safe? | Reachable from a platform plugin without a new large `HERMES_API_GAP`? |
|---|---|---|---|
| 1. `api_server` session_chat | Yes | **No, natively** (except the narrow Desktop "Bot Chat" case) — **made safe by an HMP-engineered guard, per the ruling (§3.1.8)** | Yes, over loopback (§1.9.1) — not in-process, but a bounded, documented HTTP dependency |
| 2. `tui_gateway` RPC | Yes | **Yes, natively** | No — Desktop-only protocol, undocumented for plugins |
| 3. ACP adapter | No (1:1 editor session model) | N/A | No |
| 4. `MessageEvent`/`build_session_key` | Only by impersonating another platform's identity | Yes, but only if impersonation is exact and safe (unverified, fragile) | Partially — it's HMP's existing path, but retargeting needs impersonation |
| 5. PR 106742 "attach" | No (process-level, not session-level) | N/A to this question | N/A |

**This comparison's original conclusion stands as investigation, not as the final answer: no
mechanism natively gives both true same-session write access and reliable double-writer safety,
reachable from a platform plugin without a large new dependency or an identity-impersonation risk.**
v2 of this document treated that as decisive and recommended fork-and-seed (now §3.1.7, rejected).
**The owner's ruling (2026-09-27, verbatim in the table above) instead accepts mechanism 1's native
gap and closes it with an explicit, HMP-engineered guard** — a client-declared head precondition plus
a server-side read of the same liveness data mechanism 2 (`tui_gateway`) gets natively, applied from
outside that protocol. §3.1.8 specifies the guard. This is a deliberate trade: mechanism 1 alone is
not double-writer-safe; mechanism 1 **plus the guard** closes the common cases and leaves a
quantified, bounded residual race (§3.1.8's "Residual race"), which the owner's ruling accepts
implicitly by choosing this mechanism over the alternative that had none (fork-and-seed had zero
residual race, at the cost of not being a real same-session reply at all).

#### 3.1.7 Rejected alternative: fork-and-seed (v2's recommendation, superseded)

Recorded for history, per this project's own discipline of not silently deleting a considered and
reasoned-through alternative. v2 recommended: read the target session, create a **new**, HMP-owned
session via the existing `handle_message` path (never retargeting `build_session_key`, mechanism 4),
seed its first turn with the copied history as context, and show a permanent banner making clear the
two conversations are independent. This was **rejected by the owner's ruling**, which asked for a
direct, same-session reply instead. Its analysis remains useful context for why Option D needs a
guard at all (fork-and-seed was the *zero-residual-race* alternative — it avoided the double-writer
question entirely by never writing into the foreign session), and for why the guard's residual race
(§3.1.8) is a real, accepted cost of the owner's choice, not an oversight: the owner was in effect
asked to choose between "no race, but not a real reply" and "a real reply, with a small, bounded
race," and chose the latter.

#### 3.1.8 Guard design — RULED (2026-09-27), REWRITTEN in v4 for the review's blockers and OD-N10's narrowed scope

**What OD-N10 changes about this guard.** The target is now always exactly the canonical `(profile,
"Bot Chat")` session (§1.9.2), never an arbitrary A1-browsed session. This matters because that one
session already has a **Hermes-native single-writer mechanism**: `_admit_to_live_bot_chat`/
`_answer_through_live_bot_chat` (`api_server.py:3396-3452`, confirmed also used by `/v1/runs` at
`api_server_runs.py:746`, not only by session_chat) checks `tools/bot_live_delivery.py`'s
`find_canonical_live_owner` — if a Desktop process currently **holds this exact session's lease with
`bot_live_delivery_consumer:True`** (set only once Desktop has sent its first prompt in this run,
`tui_gateway/session_lifecycle.py:63-88`), the turn is hand-delivered to that owner's mailbox and runs
**there**, as the sole writer — HMP's call gets back a `200` (settled) or `202` (`queued`/`claimed`,
not yet settled), never runs a competing agent in this process. **This resolves the Desktop-holds-it
half of BLOCKER #4 entirely, natively, with no HMP-side code at all** — HMP's guard exists for
everything the mailbox mechanism does **not** cover: the "nobody currently holds it live" branch, and
the small set of other writers enumerated in (iii) below.

**(i) HMP's own serialization — new, closes the review's idempotency BLOCKER.** Before anything else,
HMP:

1. **Acquires an in-process lock keyed by `(profile, live tip session id)`** — resolved fresh each
   time via (iv) below, since the tip can move between attempts. This serializes HMP's *own* concurrent
   attempts (two phones, a double-tap, a retry racing a first attempt) against each other; it says
   nothing about a writer outside HMP's own process, which (ii)/(iii) cover.
2. **Reserves `client_message_id` atomically in HMP's own store, *before* the loopback call** — not
   after, as v3 designed it. The reservation records `(scope, cmid, payload_hash, status="pending")`
   and is held through the entire request, including a `202`/timeout outcome. A second attempt under
   the **same** `cmid` while a reservation is `"pending"` is refused locally (`idempotency_conflict` if
   the payload differs, or a synchronous wait/replay if identical) — it never reaches the loopback call
   a second time.
3. **Timeout reconciliation never resends.** If the loopback call times out or the process cannot tell
   whether it landed, the reservation stays `"pending"` (never silently deleted) and the outcome is
   surfaced to the client as UNCONFIRMED (`CL-2`/`CL-3`'s existing vocabulary) — reconciliation is a
   **read-only** poll of the Bot Chat's own history (§3.4), matching `CL-5`'s existing "reconciliation
   never uses POST" rule. "Send as new" (the client's own explicit action) always mints a **new**
   `cmid`, never resends the pending one.

**(ii) The lease-registry check, corrected — closes the review's `registry_home`/compression-chain/
fail-open BLOCKER.** For the "nobody holds it live" branch specifically (the mailbox check in this
section's opening paragraph already answered "does Desktop hold it"; this is the broader "does
*anything else* the lease registry can see hold it" check, covering CLI and any other lease-taking
surface):

- **`registry_home` is resolved to the *target session's own profile's* home**, never left at the
  default (`active_session_registry_snapshot`'s own default, `get_hermes_home()`,
  `active_sessions.py:171-176`, is the **wrong** value for any non-default profile — v3 never set
  this explicitly, which the review correctly flagged as a false "not busy" risk). HMP already knows
  the target profile from routing (§1.9.1); it resolves that profile's own home the same way its
  existing `_profile_runtime_scope`/`gateway.config` dependency (HMP_V1.md §12) already does for
  reads.
- **Every id in the Bot Chat's full compression chain is checked, not just the current tip.** HMP
  calls `get_compression_chain` (already a bridge dependency) to get every historical id in the
  lineage, and treats a lease on **any** of them as busy — not only the live tip — because a stale but
  still-open CLI session (leased on a now-superseded id, §3.1.8(iii) below) is exactly the case the
  review's finding #4 named (`hermes_cli/cli_session_mixin.py:979-985`: `/compress` moves the CLI's
  own bookkeeping id but never re-acquires the lease, so the lease can sit on an id that is no longer
  the tip while that same CLI process is still actively driving the conversation through it).
- **Any exception from the snapshot call — not just an empty/missing result — fails closed.**
  `409 session_busy` (or, if the ambiguity is closer to "we cannot prove anything about this instance
  right now" than "we proved it's busy," `503`, distinguished in the response `why`) is returned, and
  the write gate does **not** silently treat "I couldn't check" as "clear." This mirrors
  `try_acquire_active_session`'s own documented discipline verbatim: "Ownership uncertainty fails
  CLOSED" (`hermes_cli/active_sessions.py:482-494`) — v3 only failed closed on a *positive* hit; v4
  fails closed on an *inconclusive* read too, per the review's explicit finding.

**(iii) Writers the lease registry cannot see on `8afaab37` — explicitly enumerated, not implied
covered.** For each: a cheap additional check where one exists, otherwise an accepted residual with
its likelihood **for this owner's single-owner, OD-N2-scoped deployment**, not a general multi-tenant
host:

| Writer | Visible to (i)/(ii)? | Mitigation, or accepted residual + likelihood |
|---|---|---|
| Desktop holding the Bot Chat live (has sent its first prompt this run) | **Yes — natively**, via the mailbox hand-off (this section's opening paragraph). Not a guard gap at all. | N/A — this is the mechanism's strength, not a residual. |
| Desktop with the Bot Chat open but no prompt sent yet this run (`active_session_lease: None`, `tui_gateway/methods_session.py:387`) | **No.** No lease exists yet, so `find_canonical_live_owner` returns `None` and HMP's call runs the turn directly — exactly as if nobody were there. If the Desktop user's *own* first message then races HMP's in-flight call, both could run concurrently. | **Accepted residual.** No cheap check exists (there is nothing to read — no lease has been taken yet by definition). Likelihood: **low-medium** for a single owner — it requires the owner to have the Bot Chat open in Desktop *and* be about to type into it *at the same moment* the phone sends, a narrower window than "Desktop has it open" alone. Caught after the fact by the post-hoc check below, not before. |
| CLI with an active `hermes -c "Bot Chat"` (or resumed) session, after `/compress` moved the live tip | **Now yes** — (ii)'s full-compression-chain check catches the lease on the pre-compression id, which (ii) now checks explicitly. | Closed by (ii)'s fix, not a residual. |
| Another `api_server`/`/v1/runs` caller targeting this same Bot Chat concurrently (a second phone, a manual API call, a genuine remote `hermes peer dm`) | **No — a real gap.** Neither route takes a lease for its own `_run_agent` call (confirmed: no `try_acquire_active_session` reference in `api_server.py:4128-4295` or `api_server_runs.py:668-703`). (i)'s own lock only serializes HMP's *own* calls against each other, not a genuinely separate caller. | **Accepted residual.** Likelihood: **low** under OD-N2's owner-only scope — the only other expected caller of this route on this deployment is a genuine cross-host `hermes peer dm` delivery (agent-to-agent messaging, `tools/bot_mode_dm.py`), which is infrequent and itself goes through the *same* mailbox check first. Caught after the fact by the post-hoc check. |
| In-process wake, `run_internal_session_turn` ("no HTTP, no API key", `api_server.py:3021-3027`) | **No.** Runs in-process with no lease at all. | **Accepted residual.** Likelihood: **low** — wake turns are a background-notification mechanism triggered by specific scheduled/internal conditions, not concurrent with an ordinary user-initiated reply except by coincidence. Caught after the fact. |
| ACP (zero `try_acquire_active_session` references under `acp_adapter/`) | **No**, but **out of scope under OD-N10** — ACP drives an editor-integration session, never the canonical Bot Chat by construction (its own session identity is 1:1 with an editor connection, §3.1.3). | **Not applicable** — ACP is not a plausible writer to *this specific* session at all, not merely an unchecked one. |
| Cron (`cron/scheduler.py:2496`, mints `cron_{job}_{timestamp}`) | **No**, but generally **not the same session** — a cron job would have to be deliberately configured to post into this exact Bot Chat. | **Accepted residual, likelihood: low**, and operator-controlled (the owner would have configured any such job themselves). Not independently verified this revision (Kanban's status as a same-session writer is likewise unverified — both are NIT-level per the review). |

**(iv) Head precondition, computed on the post-compression tip.** The client sends `expected_head`
(wire-compatible with `base_message_id`, generalized). Server-side, HMP:

1. Resolves the canonical Bot Chat's session id (§1.9.2), then its **live compression tip**
   (`get_compression_chain`, already a bridge dependency) — never the possibly-ended root id.
   **This also routes around a real Hermes-side gap the review found**: `_get_existing_session_or_404`
   (`api_server.py:3003-3010`) does a raw `db.get_session(session_id)` lookup that **accepts an ended
   parent** and does not itself follow the tip — if HMP posted to the root id, the handler would not
   correct it. HMP therefore **always sends the resolved live tip as the URL's `{session_id}`**, never
   the canonical registry's root id, sidestepping the bug entirely rather than relying on api_server to
   self-correct it.
2. Reads that tip's current head message id (the same value RO-3/A1's `SES-2` already compute).
3. Compares to `expected_head`. **Mismatch → `409 stale_head`.** The client MUST refresh before
   another send is allowed — never a silent retry with a stale value.

**(v) Authz, the per-device write flag, and the route-availability axis — unchanged from v3's design,
carried over.** The existing per-bot gate (ERR-3), the OD-N2 owner-dogfood host flag (§3.2), and the
target profile's `api_server` route being reachable, enabled and loopback-bound (§1.9.1's third axis)
all still gate the write independently of (i)-(iv), and all still fail closed independently. These run
in whichever order a real implementation profiles as cheapest (an unauthorized bot or a disabled
route should never pay for a head-resolution read) — this document does not mandate a specific
sub-order between (v) and (i)-(iv), only that every one of them fails closed on its own.

**Residual race, quantified (narrower than v3, per (iii)'s table).** Between the guard completing and
the `api_server` call's own commit, the only writers that can still land unseen are exactly (iii)'s
"No" rows: a first-ever Desktop prompt racing HMP's call, a second concurrent api/peer-dm caller, wake,
or a misconfigured cron job — each independently assessed **low or low-medium likelihood** for this
specific, single-owner deployment. This is bounded and small, not eliminated; it is the reason the
post-hoc check below exists, and closing it fully needs Option A's atomic Hermes-side
`atomic_anchor` (§1.3), still the eventual, un-gated target.

**Post-hoc verification — REDEFINED per the review's finding #5 (BLOCKER).** v3's rule ("our new row
landed directly after `expected_head`") was unsound: two concurrent `_run_agent` calls can each
satisfy that check from their own vantage point, and an ordinary compression rotation mid-turn would
false-flag as an interleave. v4's rule:

- **On the post-compression transcript** (re-resolved after the call returns, using the response's own
  `effective_session_id` — `result.get("session_id")`, `api_server.py:3547-3552` — since a turn-start
  compaction during *this very call* rotates `agent.session_id`, `:4272-4280`, and that rotation is
  the turn's own housekeeping, never a foreign write), **the check passes only if the *only* rows
  committed after `expected_head` are our own user row and its own assistant reply.** Any additional
  row — from any source — fails the check: `interleave_detected:true` (§3.3).
- **Identifying "our own row" without a `client_message_id` on this route** (session_chat has none;
  rows are stamped `source="api_server"`, `api_server.py:1767-1769`, with no per-message client id):
  HMP matches by **text equality plus a bounded timestamp window plus `source="api_server"`** — the
  row whose text equals what HMP just sent, stamped `source="api_server"`, with a `created_at` within
  a few seconds of the call's own start. **Stated limits, not glossed over:** two identical texts sent
  close together (a genuine duplicate send, or an unlikely coincidence) are indistinguishable by this
  method — this is a real, residual identification gap, mitigated only by (i)'s own cmid-based
  duplicate prevention already stopping HMP from creating that situation itself, not by the post-hoc
  check's own text match, which cannot tell two identical rows apart.
- **The Bot Chat `202 queued`/`claimed` (mailbox) path has not written the row yet.** The post-hoc
  check is **deferred** for this outcome — HMP polls the mailbox delivery's own settlement (already
  the natural reconciliation path, §3.4) and only runs the post-hoc comparison once the delivery
  record reports `"settled"` (`api_server.py:3441-3449`'s own status vocabulary), never immediately
  after the `202`.
- If another writer's row *did* land (a real interleave), HMP does not undo or hide it (`PR-1`) — it
  is surfaced to the user distinctly (§3.7's `interleave_detected` state), never silently rendered as
  an ordinary success.

**Consider: does `hermes peer dm` give a better, more "supported" path than raw HTTP?** No — checked
directly. `hermes peer dm <peer>[/<name>] < <tmp>` (`tools/bot_mode_dm.py:1-13`) is a **CLI
subcommand** meant to be spawned as a background subprocess by an agent's own `message_agent` tool
call (`terminal_tool(background=True, ...)`), not a library function or RPC a plugin can call
in-process or over a stable API. For a **local** (same-host) peer, the tool instead shells out to a
plain `hermes -p <name> chat -c "Bot Chat" ...` CLI invocation — a different transport again, and one
that would make HMP responsible for spawning and managing `hermes` CLI subprocesses from inside the
gateway process, a materially worse dependency than one HTTP call. For a **remote** peer, `hermes peer
dm` ultimately reaches the target host's own `api_server` over the network — i.e., **the raw HTTP call
this design already makes to the local api_server is exactly the same underlying mechanism Hermes's
own cross-host agent-to-agent delivery uses**, just addressed to `127.0.0.1` instead of a remote
tailnet address. This is confirmation, not a missed alternative: HMP's design is already using
Hermes's own supported inter-host Bot Chat delivery path, in its most direct (local) form.

**Idempotency — see (i) above (moved earlier in this revision to close the timing BLOCKER).** Recorded
here only as a pointer: the scope key is `(iid, user_id, profile)` (OD-N10 removes the
`conversation_id`/`session_ref` axis — there is exactly one target session per bot now), same
payload-hash same-payload-replay / different-payload-conflict rule as `SUB-3`.

### 3.2 Submit route — revised for Option D (RULED, §1.9/§3.1.8)

**Revised again for OD-N10: no `session_ref` field.** v3 (pre-OD-N10) added a `session_ref` field so
the route could target an arbitrary A1-browsed session. OD-N10 removes that need entirely — there is
exactly **one** send target per bot, the canonical `(profile, "Bot Chat")` session (§1.9.2), resolved
server-side the same way for every request. The wire shape stays `SUB-1`'s existing route, extended
with only the one new client-supplied field the guard needs:

```
POST /hmp/v1/bots/{p}/conversations/default/messages
{"client_message_id":"<UUIDv7>", "expected_head":<int>|null, "text":"<string>", "sent_at":<int>?}
```

`conversations/default` is kept as the path segment for wire compatibility with F1's existing route
shape (`SUB-1`) — it no longer names "the phone's own separate conversation" (§1.9.2's "Consequence
for F1's `/conversations/default`") but simply "the one conversation this route ever targets for this
bot," which is now the canonical Bot Chat. Server-side, HMP translates the outbound `text` field into
`api_server`'s own `"message"` body field (§1.9.1, review finding #2) when constructing the loopback
call — this translation is internal to the server and never visible on the phone's own wire.

`expected_head` replaces `base_message_id` as the field name to signal the changed semantics (a
client-observed head the server re-verifies, not merely an anchor Hermes admits against) — additive
per V-3 as a new optional field; a `base_message_id`-only older client is treated as sending no
`expected_head`, which the server MUST refuse (`400 bad_request`) once Option D ships, since the
guard requires it (§3.1.8(iv)) — this is the one deliberately breaking edge of an otherwise additive
change, and needs its own contract-revision note (a `1.x` client without `expected_head` cannot use
Option D at all; it sees the gate as closed, §3.3).

- **Host-side owner-dogfood gate flag (OD-N2 ruling, §1.7), unchanged design.** A new config flag,
  e.g. `gateway.platforms.hmp.direct_send.enabled` (mirroring A1-T08's own host-side kill-switch
  pattern), **default OFF**. `write_gate.state` can be `"open_guarded"` (renamed from v2's
  `"open_reduced"` — see below) only when this flag is on **and** §1.9.1's third axis (api_server
  reachable and configured for the target profile) is satisfied. With the flag off, or api_server
  unreachable, the gate behaves exactly as F1 shipped it. This flag remains the sole enforcement
  point for "gated to the owner's own devices only," unchanged from v2's reasoning.
- **`write_gate` grows a third state, renamed `"open_guarded"` (was `"open_reduced"` in v2).** The
  rename reflects that Option D's guarantee does not come from a *reduced Hermes admission floor*
  (v2's framing, still accurate for Options B/C) but from an **explicit HMP-engineered guard** around
  a full, direct write — a materially different claim, and PR-4 ("honest guarantees") requires the
  wire vocabulary say what is actually true. `"open_guarded"` is never returned alongside the full
  GU-2 `"open"` state — mutually exclusive by construction, same as v2. A client that does not
  recognize `"open_guarded"` treats it as `"closed"` under V-4, the safe default.
- **`POST .../messages` still returns `503 guarantees_unavailable`** when the gate is fully closed.
  When it is `"open_guarded"`, the route runs the full §3.1.8 guard, then calls `api_server`
  (§1.9.1). Response carries `"guarantee_level":"guarded"` (renamed from v2's `"reduced"`) on
  `200 accepted`/`202 submitted` — additive, ignored under V-4, never present on a full-guarantee
  accept.
- **Idempotency**, per §3.1.8(i): `client_message_id` reserved atomically **before** the loopback
  call (not after — the review's own idempotency BLOCKER), scope `(iid, user_id, profile)` — OD-N10
  removes the per-session-ref axis entirely, since there is exactly one target per bot now. Same
  payload-hash same-payload-replay / different-payload-conflict rule as `SUB-3`. This is
  HMP-side only — `api_server`'s session_chat route has no cmid concept of its own (§3.1.8's closing
  note) — a genuine, named limitation relative to what Option C's Hermes-native `admit_session_input`
  would give (§1.5), accepted because Option D's mechanism was ruled on its own terms.
- **Head precondition — now `expected_head`, client-supplied and server-verified, not merely
  HMP-computed** (a refinement of v2's "HMP-side best-effort head precondition," §3.1.8(iv) for the
  full mechanics, now computed on the post-compression tip). `409 stale_head` (new code, not
  `409 conversation_changed`) signals a mismatch against the Bot Chat's current state, since
  `conversation_changed`'s existing meaning (`HMP_V1.md` ERR-2) is scoped to Hermes's own
  admission-time precondition — using a distinct code keeps the two failure classes (client's stale
  view vs. Hermes's own admission-time refusal) separately actionable, per V-4's action-class
  discipline.
- **`409 session_busy`** (new code): guard (ii) failed (the lease-registry check, corrected per the
  review) — another surface currently holds the Bot Chat, or the snapshot read itself failed and the
  guard failed closed on the ambiguity (§3.1.8(ii)). Client action: same shape as `busy` in `ERR-2`'s
  existing table ("Restore the draft" — non-definitive, since Hermes never saw this attempt at all).

### 3.3 Response shapes — revised for Option D

Reuse `SUB-4`'s table unmodified for the definitive outcomes already defined (`accepted`, the refused
error set, gate-closed). Add:

| Outcome | Response | Definitive? |
|---|---|---|
| Accepted under the guarded gate | `200 {"state":"accepted", "message_id", "head_message_id", "guarantee_level":"guarded"}` | yes, for *this attempt reaching Hermes* — not a promise no interleave occurred; see the post-hoc-verification flag below |
| Guard (iv) failed: client's view of the Bot Chat is stale | `409 {"error":{"code":"stale_head", ...}}` | yes — the client MUST refresh before retrying (§3.1.8(iv)) |
| Guard (ii) failed: another surface holds the Bot Chat, or the liveness check itself failed | `409 {"error":{"code":"session_busy", ...}}` | no — Hermes never saw this attempt; restore the draft, allow a plain retry once the busy state clears |
| Post-hoc verification detects an interleave (§3.1.8) | `200 {"state":"accepted", ..., "interleave_detected":true}` — an additive field on the same `200`, never a separate error, since Hermes *did* execute the send; only the ordering guarantee is in question | yes for the send itself; the `interleave_detected` flag is informational, driving the UX state in §3.7 |

No error code is withdrawn from `ERR-2`'s general table; `stale_head` and `session_busy` are new,
additive codes specific to Option D's guard (V-3: "new error codes that fall into an existing client
action class" — `stale_head` behaves like `conversation_changed`'s action class, `session_busy` like
`busy`'s).

### 3.4 Reply visibility without SSE

F1 excludes SSE entirely; OD-N5 (controller default, owner may override) keeps that exclusion for F2
v1. **New for Option D:** `api_server`'s non-streaming `POST /api/sessions/{id}/chat` is itself
**synchronous** — its own HTTP response already carries `{"message": {"role": "assistant", "content":
...}}` once the turn finishes (`api_server.py:3505-3541`, `_handle_session_chat`'s return value,
confirmed by reading that handler directly). This means the reply is **often available immediately
in the send response itself**, with no poll needed for the common case — a strictly better outcome
than v2's Option B/C design, which was fire-and-forget by construction. HMP's own `200 accepted`
response (§3.3) MAY therefore carry the reply text directly when `api_server` returned it
synchronously within a bounded local wait (recommend reusing `ADMISSION_WAIT_S`'s existing 5-second
budget, §13, as the bound before HMP itself gives up and returns `202 submitted` instead of blocking
the phone's HTTP request indefinitely on a long-running turn). **Polling remains the fallback and the
confirmation mechanism for the general case** (a long turn, a dropped loopback connection, a `202`
outcome) — the design below is unchanged from v2 for that case:

- After a `200 accepted`/`202 submitted`, the composer shows a local "sending" affordance and the
  client polls the **existing** snapshot/history routes (`RO-3`, `RO-6`) on a short backoff (reusing
  `CL-5`'s lookup backoff shape: start 1s, cap 15s) until either the new row appears (matched by
  `client_message_id` per `RO-3`'s "`client_message_id` is present on rows that HMP originated") or
  `CLIENT_RETRY_WINDOW_S` elapses, at which point it falls back to the existing UNCONFIRMED UX
  (`CL-3`).
- This reuses `SUB-7`/`SUB-8` (`GET .../messages/by-client-id/{cmid}`) as the fast dedicated
  reconciliation path, exactly as F1's contract already specifies for lookup, rather than
  reimplementing polling logic. No live streaming, no partial/live_id text — the user sees the final
  message once the poll picks it up, not word-by-word.
- **Cost:** perceptibly slower than SSE, and indistinguishable, from the UI's perspective, between
  "still running" and "already replied, poll hasn't landed yet" until a poll succeeds. Acceptable for
  v1 given SSE's much larger transport/security footprint (`EV-1`..`EV-9`) is explicitly deferred.

### 3.5 Stop/cancel — revised for Option D

- **Once a turn is actually running**, F2 reuses `INT-5` verbatim: `/stop` always forwards, `202
  {"state":"forwarded"}`, independent of the write gate (GU-4's existing permanent exception already
  covers this — no design change needed).
- **"Before a turn starts" barely exists as a distinct state under Option D.** Unlike v2's Option
  B/C (a `handle_message` hand-off that could sit queued behind another follow-up,
  `_pending_messages`), Option D's guard (§3.1.8(ii)) already refuses with `session_busy` if
  anything is in flight, so a call that passes the guard proceeds straight into `_run_agent`
  synchronously (§1.9.1) — there is no supported, HMP-visible "admitted but not yet started" window
  to cancel, only the small, already-quantified residual race (§3.1.8), which is over before the
  client could act on it anyway. **Recommend: still no queued-send cancel in F2 v1** — the reasoning
  is now "there is essentially nothing to cancel," not v2's "the primitive exists but isn't
  reachable." `/stop` (once a turn is confirmed running, `turn.observed_state`) remains the only
  supported interruption, unchanged.

### 3.6 Compat impact — new Hermes internals, `bridge_files`, and the route probe (revised for Option D)

**New Hermes internals touched, beyond HMP_V1.md §12's existing list and A1's two read additions:**

| Internal | Used for | Already in `bridge_files`? |
|---|---|---|
| `hermes_cli.active_sessions.active_session_registry_snapshot` | guard (ii), §3.1.8 | **No — new file.** `hermes_cli/active_sessions.py` is not in the committed 16-entry `bridge_files` list (`read_compat_builds.json`, cited in v1's Appendix) nor in A1's proposed 17th entry (`hermes_state_common.py`). This is a genuinely new source file HMP now imports. |
| `gateway.platforms._shared.get_scoped_secret` | reading `API_SERVER_KEY` server-side, §1.9.1 | **Yes.** `gateway/platforms/_shared.py` is already in `bridge_files` — no new fingerprinted file for this specific read (it is also already a *documented* plugin helper, `DURABILITY.md` Q3, lower risk than a private internal). |
| `gateway.config.PORT_BINDING_PLATFORM_VALUES` / `SHARED_LISTENER_MIRROR_PLATFORMS` / `SHARED_LISTENER_MIRROR_PATHS` | resolving the `/v1/...` vs `/p/<profile>/v1/...` request path, §1.9.1 | **Yes.** `gateway/config.py` is already in `bridge_files` (used today for `Platform`/platform config, HMP_V1.md §12). |
| `bridge.latest`/`bridge.lineage` (existing) and A1's `list_sessions_rich`/`get_session` (A1-T01) | head resolution, §3.1.8(iv) | Already covered by existing `bridge_files` entries plus A1's own additions — no further change from this document. |
| The `api_server` HTTP route itself (`POST /api/sessions/{id}/chat`, `GET /v1/capabilities`) | the loopback call and its own compat probe, below | **Not a `bridge_files` concern at all** — HMP never imports `gateway/platforms/api_server.py`'s Python symbols, it only speaks its documented HTTP contract over loopback (§1.9.1). This is a genuinely different kind of dependency (a runtime route-shape probe, not a source-fingerprint), handled separately below. |

**`bridge_files` grows by exactly one file: `hermes_cli/active_sessions.py`.** Per A1's own
methodology (`A1-session-browsing.md` §1.5, reused here without inventing a new rule): the committed
list is the union of `bridge.py`'s own direct imports and `inspect.getsourcefile` of each
`READ_DEPENDENCIES`/(new) `WRITE_DEPENDENCIES` entry — adding `active_session_registry_snapshot`
adds exactly its own source file, nothing transitively. **This forces a requalification of
`stock-base`, `experimental` and the owner-local build** (`tools/compat/run_matrix.py` re-run, new
fingerprints in whichever list records it — the new `reduced_write_supported_builds.json`, §3.6
below, not `read_compat_builds.json`, since this is a write-path dependency, never needed for reads).
Independently spot-checked: `hermes_cli/active_sessions.py` exists with the cited function at the
cited line on all three trees (`stock-base`, `experimental`, owner's `8afaab37`) — the file itself
was not diffed byte-for-byte across all three as part of this design pass (that is `T-N015`'s job,
the actual qualification run), but its presence and the cited signature were confirmed directly on
the owner's build during this investigation.

**The loopback HTTP dependency needs its own, distinct compat check — a versioned route probe, not a
`bridge_files` fingerprint.** Because whether `api_server` is enabled is pure per-deployment config
(§1.9.1), and because the route's *shape* (its JSON keys, its auth ladder) is a product HTTP contract
that could still drift across Hermes releases independent of any Python import HMP makes, this
document specifies a **third compat axis**, alongside GU-2c (read build identity) and the new
`WRITE_DEPENDENCIES` probe (§1.8, still used for the background/fallback B/C path, §1.9.3):

1. **Cheap existence probe, at request time (not just process start, since api_server's enablement
   can change without an HMP restart):** `GET /v1/capabilities` against the resolved loopback URL
   (§1.9.1), checked for `"session_chat": true` in the response's static feature-flag map
   (`gateway/platforms/api_server.py:67-75`, `_STATIC_FEATURE_FLAGS`) — the **same self-describing
   capability-flag discipline** GU-2 already established for `PLATFORM_ADAPTER_CAPABILITIES`, applied
   to a different Hermes surface. A `404`/connection-refused (api_server disabled) or a response
   missing the flag both mean the `write_gate`'s third axis (§1.9.1) is unmet — fail closed, same as
   any other unmet floor.
2. **Behavioral confirmation, at qualification time only (T-N015, not per-request):** one synthetic
   `POST /api/sessions/{id}/chat` against a throwaway fixture session, confirming the response shape
   HMP's parser expects (`{"object":"hermes.session.chat.completion", "session_id", "message":
   {"role","content"}, ...}`, `api_server.py:3536-3541`) actually matches — mirroring §1.8's own
   "symbol presence is never enough, confirm behavior" discipline, now applied to an HTTP contract
   instead of a Python symbol.

**A new, distinct qualification list**, e.g. `server/hmp_plugin/direct_send_supported_builds.json`
(renamed from v2's `reduced_write_supported_builds.json` to match §3.2's `"open_guarded"` vocabulary),
mirroring `write_supported_builds.json`'s shape but recording, per build: the `bridge_files`
fingerprint (now including `hermes_cli/active_sessions.py`), and — separately, since it is a
per-deployment config fact, not a build fact — whether the qualification run's *own* fixture host had
`api_server` enabled when the route probe above was exercised. It starts **empty**, same as every
other matrix (`write_supported_builds.json` is `{"format":1,"builds":[]}` per OD-F3, unchanged).

**Qualification tests**, extending `tools/compat/run_matrix.py`'s existing shape (fixture self-check
+ read suite) with a **guarded-write suite** exercising, per candidate build, **with a fixture
`api_server` explicitly enabled for the test run**:

- **Native mailbox path**: a fixture Desktop process holds the canonical Bot Chat's lease with
  `bot_live_delivery_consumer:True` — the send is delivered to that mailbox (`202 queued`/`claimed`,
  settling later), never runs a competing `_run_agent` in the same process (§3.1.8's opening
  paragraph). This is the primary, most common path under OD-N10 and must be the first fixture, not an
  afterthought.
- guard (iv): a stale `expected_head` is refused with `409 stale_head`, resolved against the **live
  compression tip**, and a correct one proceeds;
- guard (ii): a fixture CLI-style lease (`try_acquire_active_session`, held for the fixture's
  simulated process lifetime), taken on the Bot Chat's **pre-compression** id, is still caught as
  `409 session_busy` after a simulated compression rotation moved the tip — this is the specific fix
  for the review's "CLI after `/compress`" finding, and it is its own required test case, not folded
  into a single generic "busy" test. A second fixture asserts the correct **per-profile**
  `registry_home` is used (a secondary-profile Bot Chat's lease must not be missed because the
  snapshot read the default profile's registry). A third fixture forces the snapshot call itself to
  raise, and asserts the result is `session_busy`/`503`, never a silent "not busy."
- residual-writer fixtures (§3.1.8(iii)): a send that runs directly (nobody holds the Bot Chat live)
  concurrently with a simulated first-ever Desktop prompt on the same session, and a send concurrent
  with a simulated second `api_server`/`/v1/runs` caller — both are **expected to be caught only by
  the post-hoc check below, not by the pre-call guard**, and the test suite must assert exactly that
  (a guard-level false "safe" here would be a regression of the review's finding, not a pass);
- idempotency: the cmid reservation (§3.1.8(i)) is made **before** the loopback call, is held through
  a simulated timeout, and a same-cmid retry during that window is refused locally without a second
  loopback call; same-`cmid` replay after a definitive outcome returns the stored result;
  different-payload-same-cmid returns `409 idempotency_conflict`;
- post-hoc verification, redefined: a fixture that deliberately interleaves a second writer's row
  between the guard's head-check and the `api_server` call's own commit surfaces
  `interleave_detected:true`; a **separate, required negative fixture** exercises an ordinary
  compression rotation happening *during* HMP's own call (no other writer at all) and asserts
  `interleave_detected` is **never** set for it — directly testing the review's "false-flags
  compression" finding, not just the true-positive case;
- this suite MUST run against **synthetic fixtures only**, unchanged from v2 and from F1's existing
  discipline (never the owner's live database, `R0_OWNER_DECISIONS.md` bounded amendment 3).

**`GU-2a`'s existing matrix (`write_supported_builds.json`) is untouched, unchanged from v2.** A build
only ever enters it by independently earning the full GU-2 guarantees (OD-F3's bar), never as a side
effect of qualifying for Option D's guarded list.

**Options B/C's own qualification design (v2's original §3.6, `reduced_write_supported_builds.json`
with a `mechanism:"B"|"C"` field, §1.8's auto-upgrade detector) is retained, unmodified, as the
qualification path for the background/fallback transport only** (§1.9.3) — it is no longer the
primary matrix a real deployment needs populated to ship F2's main path, since Option D's own list
above is what gates the ruled mechanism.

### 3.7 Client composer states — revised for Option D

Extending F1's existing `PairedInstanceState`/read-only UX vocabulary (`data-model.md`), the composer
needs at minimum:

| State | Trigger | Notes |
|---|---|---|
| **idle** | write_gate not closed, nothing pending | Composer enabled |
| **sending** | user tapped Send, request in flight | Text stays visible, not yet a message row (`CL-1`: pending record persisted before first transmission) |
| **stale — refresh to reply** | `409 stale_head` (§3.1.8(iv), §3.3) | The client's view of this session is out of date. Draft is kept locally; the view auto-refreshes (a silent re-read, not a user-initiated pull-to-refresh) and Send is re-enabled only once the refreshed `expected_head` is current — never a silent resend with the old value (§3.2). |
| **busy — try again shortly** | `409 session_busy` (§3.1.8(ii), §3.3) | Non-definitive: another surface (Desktop, CLI, or an active platform turn) currently holds this session. Restore the draft; offer a plain retry, no automatic one (OD-N8 unchanged). Copy should name the possibility honestly: "Someone else is using this conversation right now." |
| **sent (guarded)** | `200`/lookup `accepted` under `guarantee_level:"guarded"` | Shown distinctly from a full-guarantee accept, but — unlike v2's Option B/C framing — this is a **direct, same-session send that passed the guard**, not a queued/possibly-merged one. Copy should reflect that: a normal "sent" indicator, not a hedge, *unless* `interleave_detected` is also set (next row). |
| **sent — check for a crossed reply** | `200 {..., "interleave_detected":true}` (§3.3, §3.1.8's post-hoc verification) | The rare, quantified residual-race case: another writer's row landed between HMP's head-check and its own commit. The message **was** sent — never shown as failed — but flagged distinctly: "This may have crossed with another message — check the conversation." Never silently rendered as an ordinary success (R-C11, revised, §6). |
| **failed** | any `CL-2` REJECTED/NOT-TRANSMITTED class | `CL-3`'s existing Discard / Review & Send actions, unchanged |
| **unconfirmed** | any `CL-2` UNCONFIRMED class (loopback/timeout ambiguity, §1.9.1's HTTP dependency) | `CL-3`'s existing Check again / Send as new / Remove actions, unchanged |
| **offline** | no connection to the active instance | Reuses F1's existing unreachable state; Send stays disabled, draft stays local (`CL-1`) |
| **send unavailable on this instance** | `write_gate` is `"closed"`: the owner-dogfood flag is off, or `api_server` is unreachable/disabled for the target profile (§1.9.1's third axis) | Composer is read-only, same visual treatment F1 already uses for a fully-closed gate — the copy should distinguish "not enabled by the operator" from "temporarily unreachable" where the server can tell the two apart (`UX_CONTRACT_GAP`, not resolved here). |

**Retry policy:** unchanged from F1 — `CL-4` stays in force (OD-N8): no automatic retry in F2 v1.

**Entry point (OD-N3, §3.1.8, superseding v2's fork-and-seed entry point).** Opening a non-`is_mobile`
session via A1's browsing (S7, source-badged) now shows the **same composer** as the phone's own
conversation, inline in that view — not a separate "continue as a new conversation" action, since the
ruled mechanism is a genuine same-session reply, not a fork. The header subtitle A1 already specifies
("on ⟨instance⟩ · ⟨source badge⟩" for a non-mobile session, `A1-session-browsing.md` §4) is the only
visual cue distinguishing "you are replying into a Desktop/CLI/other-platform conversation" from the
phone's own — deliberately understated, since the send genuinely lands in that same session now, and
overstating the distinction would misrepresent what actually happens. The `stale`/`busy`/`interleave`
states above apply identically regardless of which session is open.

### 3.8 Security design

- **Replay.** Unchanged from `SUB-3`/idempotency — a resend under the same `cmid` never re-executes.
  Under Option C, Hermes's own `admit_session_input` payload-digest check is a second, independent
  backstop against a replayed attempt reaching the agent twice, even if HMP's own record were somehow
  bypassed (defense in depth, not a reason to relax HMP's own claim check).
- **Rate limits / size caps.** Reuse `TR-6` (`MAX_BODY_BYTES`, rate limits) unchanged — nothing about
  the guarantee level changes the transport-layer limits; `busy` is still not rate-limited per the
  existing `ERR-2` note ("submit is not rate-limited in v1.0").
- **Content neutralisation.** Message text crosses into Hermes as ordinary agent input, same as any
  other platform adapter's inbound text — no new HMP-side sanitisation is invented here; standard
  prompt-injection considerations belong to Hermes's own agent-loop handling, out of scope for HMP's
  transport role (`PR-1`: "HMP MUST NOT ... execute anything on Hermes's behalf").
- **Approvals/clarify raised mid-turn — RULED (OD-N7, 2026-09-27): "Show it, answer elsewhere."** F1
  explicitly excludes approval/clarify answering. A mobile-originated send can now cause Hermes to
  raise one. F2 v1 keeps this **read-only**, confirmed by the owner:
  the existing `approval.unanswerable`/clarify-read-only rendering already defined in `HMP_V1.md`
  `EV-7`/`INT-4` applies unchanged — the UI shows "this turn needs approval on another Hermes
  surface", not a blocked composer. No new security surface: no approval-answering endpoint is added
  in F2.
- **Loopback credential handling (new for Option D, §1.9.1).** `API_SERVER_KEY` is read server-side
  only, via the same documented `get_scoped_secret` helper `api_server.py` itself uses
  (`api_server.py:1191`) — never stored in HMP's own store, never included in any response to the
  phone, never logged (SEC-4's existing rule, restated because this is definitionally a secret token
  in a way most of HMP's own §12 dependencies are not). The loopback request itself never leaves
  `127.0.0.1` (`TR-4`'s existing bind restriction is about HMP's *own* listener; this is a distinct,
  new statement about a request HMP's server makes as a *client* of another local listener, and it
  MUST be pinned to loopback explicitly, never resolved through any DNS or tailnet path).
- **`HERMES_API_GAP` additions this design would introduce**, each needing the same rigor F1's §12
  table applies:
  - `hermes_cli.active_sessions.active_session_registry_snapshot` (guard (ii), §3.1.8) — public,
    exported, already used by three independent Hermes surfaces (`cli.py`, `tui_gateway`,
    `gateway/run_busy.py`) for exactly this kind of liveness check, so lower risk than a fully private
    internal, but still outside the documented plugin contract (`DURABILITY.md` Q2/Q3's coverage never
    mentions it).
  - `api_server`'s `POST /api/sessions/{id}/chat` route and `GET /v1/capabilities`'s `session_chat`
    flag (§1.9.1, §3.6) — a documented **product** HTTP contract (used by any OpenAI-compatible
    client), not a private Python internal, but reached over loopback with a credential HMP does not
    own the lifecycle of, and its own compat/versioning story is `api_server`'s, not HMP's own
    `HMP1-*` contract's — a structurally different kind of dependency from everything else in this
    list, flagged as such (R-C13/R-C14, §6).
  - The guard's read-then-act sequence (§3.1.8) is not a new Hermes dependency, but it is a new,
    quantified **race** HMP accepts responsibility for, mitigated (not closed) by the post-hoc
    verification — the security review must treat this as a named, bounded residual, not a solved
    problem.
  - `SessionAuthority.admit_native` / `SessionDB.has_platform_message_id` (Options C/B) remain listed
    from v2, now scoped explicitly to the background/fallback transport only (§1.9.3), not the primary
    mechanism's security surface.

---

## 4. Acceptance plan — revised for Option D

Per the task brief: **synthetic fixtures first, then the owner's live Hermes only after sign-off —
and only after the owner has separately approved enabling `api_server` on the target profile
(§1.9.1, §5's `T-N00x` "owner action" task), since that is a live-config change this design cannot
authorize on its own.**

1. **Fixture-only phase (this phase and all of F2's initial implementation, if ever authorized).**
   Extend F1's existing isolated-Hermes-home fixture harness (`tools/fixtures/`,
   `tools/compat/run_matrix.py`) with `api_server`-enabled fixtures on the `stock-base`,
   `experimental` and `pr106742` extracted trees (never the owner's `~/.hermes` install). Exercise:
   happy-path direct send with an immediate synchronous reply (§3.4); guard (iv) `stale_head`; guard
   (b)/(c) `session_busy` for both identity spaces (a fixture CLI-style lease and a fixture
   gateway-messaging-style per-turn lease, §3.6); same-cmid replay; different-payload-same-cmid
   conflict; the deliberately-interleaved-writer fixture proving `interleave_detected` fires (§3.6);
   approval/clarify raised mid-turn rendered read-only, never silently dropped (OD-N7); the background
   B/C path's own fixtures, retained from v2, exercised only as the documented fallback (§1.9.3).
2. **Independent review gate**, matching F1's discipline ("no self-certification", `AGENTS.md`):
   security review of the new `HERMES_API_GAP` entries, the loopback credential handling, and the
   guard's quantified residual race (§3.8); UX review of the composer states (§3.7), including the
   `interleave_detected` copy specifically (R-C11, revised, §6); a protocol review of the `write_gate`
   third state, `guarantee_level`, `stale_head` and `session_busy` for consistency with `PR-4`
   ("honest guarantees") before any wire text is finalized.
3. **Owner sign-off checkpoint** — explicit, before OD-N4/N5/N6/N8/N9 are treated as decided (OD-N1/
   N2/N3/N7 are already ruled), and before any live-Hermes check. This document does not claim that
   checkpoint has happened.
4. **Live Hermes phase — gated, narrow, and only after sign-off, with TWO distinct owner approvals
   required, not one:** (i) the OD-N2 dogfood-flag activation (`T-N019`), and (ii) a **separate, new**
   approval to enable `api_server` at all on the default profile (`T-N018`, below) — today it has no
   `API_SERVER_*` configuration (§1.9.1, independently verified). Even then: OD-L9's existing
   `BLOCKED_OWNER_INPUT: TEST_BOTS` discipline applies
   (`FIRST_FEATURE_PLAN.md`) — designated test bots or a test profile, never the owner's real
   bots/profiles.

---

## 5. Task outline (dependency-ordered, for a future implementation worker — not authorized yet)

Each task lists its acceptance test. **OD-N1/N2/N3/N7/N10 are now ruled (2026-09-27): OD-N3's
mechanism is ruled ("reply directly with a guard"), and OD-N10 narrows its target to the canonical
Bot Chat only — superseding both the earlier "OD-N3 needs a fork-and-seed sign-off" framing and v3's
general "any A1-browsed session" design; OD-N4/N5/N6/N8/N9 still carry only the controller's
default.** This revision (v4) also incorporates every fix required by the independent review of v3
(Grok 4.7, `PROCEED-WITH-CHANGES`, "Review response" table at the top of this document). None of
these tasks may start until a separate implementation authorization is given (this document remains
planning only).

1. **T-N001 (revised) Remaining decision confirmation.** OD-N1/N2/N3 (scope, mechanism, and the
   OD-N10 target narrowing)/N7 are ruled; this task is now: (a) confirm or override the
   controller-default OD-N4/N5/N6/N8/N9, and (b) confirm §1.9.2's recommendation that F2 sends target
   the canonical Bot Chat exclusively, retiring F1's separate mobile-only conversation for the *write*
   path — a real, load-bearing change to F1's existing model that this document flags but does not
   decide unilaterally. *Acceptance: a recorded decision note for both, the same way
   `R0_OWNER_DECISIONS.md`'s "Freeze decisions" section records one.* Blocks everything below.
2. **T-N001b Controller records the new OD.** The OD-N2 ruling needs a permanent, numbered entry in
   `R0_OWNER_DECISIONS.md`'s own series; OD-N10 likewise. This document deliberately does not assign
   or edit that numbering. *Acceptance: new `OD-F#` rows exist there, cross-referencing this design.*
3. **T-N001c Align the bot-view selector with A1.** A1's session-browsing list is being narrowed to
   the same `(profile, "Bot Chat")` selector in parallel, on `f1/w-sessions-design` (not this branch).
   *Acceptance: the controller confirms both branches resolve the selector identically (same title
   constant, same compression-tip logic, same evidence citations, §1.9.2) before either merges —
   two independently-derived selectors that happen to agree today is not the same guarantee as one
   shared definition.* Cross-feature dependency, not scheduled by this document alone.
4. **T-N002 Server: `write_gate` third state (`"open_guarded"`) + `guarantee_level`/`stale_head`/
   `session_busy`/`interleave_detected` contract text (§3.2, §3.3).** Depends on T-N001. *Acceptance:
   `HMP_V1.md` amendment reviewed against V-3's additive-only rule (except the one deliberately
   breaking edge: a client without `expected_head`, §3.2); existing F1 conformance tests still pass
   unmodified.*
5. **T-N002b Host-side owner-dogfood gate flag** (§3.2's new config flag,
   `gateway.platforms.hmp.direct_send.enabled`). Depends on T-N002. *Acceptance: with the flag off
   (the default), the gate never reports `"open_guarded"` regardless of §1.9.1's route probe result.*
6. **T-N003 `API_SERVER_KEY` server-side read, per profile, with correct coupling** (§1.9.1, review
   finding #3): the default profile's key via `get_scoped_secret("API_SERVER_KEY", "")`; a named
   profile's key via a **fresh**, independently-scoped lookup for *that* profile, never the default's
   cached value; a `401` from the loopback call is treated as gate-closed for that profile, never
   retried with a different key. Depends on T-N002. *Acceptance: unit test confirming the key is never
   logged or stored by HMP; a fixture test with two profiles, each with a different (or absent) key,
   confirming a request to one profile never succeeds with the other's key or a stale cached value.*
7. **T-N003b Loopback bind enforcement + async, no-proxy HTTP client** (§1.9.1, review finding #6,
   BLOCKER). Read the same config/env `listen_address` reads (replicated, not imported, to avoid
   pulling in `api_server.py`'s private module); refuse (fail closed) unless the resolved host is
   `127.0.0.1`/`::1` or unresolvable-to-anything-but-loopback; construct the outbound call with
   `aiohttp.ClientSession(trust_env=False)`, `await`ed directly on HMP's own coroutine (no
   `to_thread` — genuine async I/O). Depends on T-N002. *Acceptance: a fixture with
   `API_SERVER_HOST=0.0.0.0` (or any non-loopback value) — the gate never opens; a fixture with
   `HTTP_PROXY` set in the environment — the call is proven (via a fake proxy that would record any
   traffic routed through it) to never touch it; a fixture confirming the gateway's event loop
   continues to serve other requests during a slow loopback call (no blocking).*
8. **T-N004 Route probe (§3.6, corrected route/body per review findings #1/#2): `POST
   /api/sessions/{id}/chat` (default) / `POST /p/<profile>/api/sessions/{id}/chat` (secondary), body
   `{"message": ...}`, plus `GET /v1/capabilities`'s `session_chat` flag as a cheap existence check
   only (never proof of key validity) and a qualification-time behavioral confirmation of the real
   response shape.** Depends on T-N003, T-N003b. *Acceptance: a fixture asserting the mirrored path is
   used for a secondary profile, never `/v1/...`; a fixture asserting `capabilities.session_chat:true`
   alone never opens the gate without a separate authenticated probe succeeding too.*
9. **T-N005 Bot Chat selector resolution** (§1.9.2, rewritten for OD-N10): resolve `(profile, "Bot
   Chat")` via the same primitive `tools/bot_live_delivery.py`'s `find_canonical_owner` already uses
   (`get_session_by_title`, `get_compression_tip`) — server-side only, no `session_ref`, no new
   mapping table. Depends on T-N002. *Acceptance: a fixture with no existing Bot Chat for a profile
   resolves to "not found" cleanly (never auto-creates one on the send path — creation, if ever
   needed, is a distinct, explicit decision this document does not make); a fixture with a
   compression-rotated Bot Chat resolves to the live tip, not the root.*
10. **T-N006 Guard (iv): head precondition on the post-compression tip.** Depends on T-N005.
    *Acceptance: fixture test with a stale client view caught before any write is attempted; a fixture
    test with a Bot Chat whose stored id was superseded by compression since the client last read it,
    confirming the *live tip's* head is what's compared, and that the resolved live tip (not the
    registry's root id) is what's sent as the URL's `{session_id}` (routing around
    `_get_existing_session_or_404`'s "accepts an ended parent" gap, §3.1.8(iv)).*
11. **T-N007 Guard (ii): the corrected lease-registry check.** Read-only call to
    `active_session_registry_snapshot` (`hermes_cli/active_sessions.py:711-740`, new `bridge_files`
    entry, §3.6) with the **target profile's own `registry_home`**, checked against **every id in the
    Bot Chat's full compression chain**, failing closed (`session_busy`/`503`) on **any** exception
    from the snapshot call itself. Depends on T-N005. *Acceptance: (a) a fixture CLI-style lease on
    the Bot Chat's live tip yields `409 session_busy`; (b) a fixture CLI-style lease on a
    **pre-compression** id (simulating `/compress` without lease movement) is *also* caught, via the
    full-chain check specifically — the review's exact finding, its own required test case; (c) a
    fixture with the wrong (default-profile) `registry_home` used against a secondary-profile Bot Chat
    fails the test until the profile-scoped fix is applied — a regression test for the review's
    specific `registry_home` finding; (d) a fixture that forces the snapshot call to raise an exception
    asserts `session_busy`/`503`, never a silent "not busy."*
12. **T-N007b Native mailbox path — verification, not new code.** Confirm `_admit_to_live_bot_chat`
    already redirects to Desktop's mailbox when it holds the Bot Chat live, with no HMP-side
    involvement beyond calling the route (§3.1.8's opening paragraph). Depends on T-N004, T-N005.
    *Acceptance: a fixture Desktop process holding the lease with `bot_live_delivery_consumer:True`
    causes HMP's call to receive `202 queued`/`claimed`, settling later, and never spins up a second
    agent in HMP's own request — this is the task that proves OD-N10's central claimed benefit is
    real, not assumed.*
13. **T-N008 Idempotency: atomic cmid reservation before the call** (§3.1.8(i), moved earlier per the
    review's timing BLOCKER), a per-`(profile, live-tip)` in-process lock, and timeout reconciliation
    that never resends. Depends on T-N002. *Acceptance: a fixture asserting the reservation exists
    *before* any loopback call is attempted; a fixture simulating a timeout, then a same-cmid retry
    during the pending window, asserting no second loopback call is made; same-cmid replay after a
    definitive outcome returns the stored result; different-payload-same-cmid returns
    `409 idempotency_conflict`.*
14. **T-N009 The `api_server` loopback call itself**, corrected route/body/client (§1.9.1): construct
    and send `POST [/p/<profile>]/api/sessions/{live_tip_id}/chat` with `{"message": <text>}`, the
    resolved per-profile key, and `aiohttp.ClientSession(trust_env=False)`; parse the synchronous
    reply when present (§3.4); handle the async/`202`/timeout paths. Depends on T-N003, T-N003b,
    T-N004, T-N005, T-N008. *Acceptance: a fixture test against a real (fixture) `api_server`
    listener, confirming the response shape matches §3.6's behavioral-confirmation probe exactly.*
15. **T-N010 Guard ordering + submit route wiring** (server): compose (i)/(ii)/(iv)/(v) in the order
    §3.1.8 specifies, then T-N009's call. Depends on T-N006, T-N007, T-N007b, T-N008, T-N009.
    *Acceptance: the full `SUB-4` response table plus §3.3's additions; a test confirming guard
    failures never reach the loopback call at all.*
16. **T-N011 Post-hoc verification, redefined** (§3.1.8, review finding #5, BLOCKER): on the
    post-compression transcript (using the response's own `effective_session_id`), pass only if the
    only rows after `expected_head` are our own user row and its own assistant reply, identified by
    text + timestamp window + `source="api_server"` (with the stated limits on that identification);
    defer the check entirely for a `202 queued`/`claimed` outcome until the mailbox delivery settles.
    Depends on T-N010. *Acceptance: the interleaved-writer fixture surfaces `interleave_detected:true`;
    a **separate, required** fixture of an ordinary mid-call compression rotation with no other writer
    asserts `interleave_detected` is never set (the review's specific false-flag finding); a fixture of
    a `202` mailbox outcome asserts the check runs only after settlement, never immediately.*
17. **T-N012 Reply-visibility polling fallback** (client): extend F1's existing snapshot/history read
    path with the backoff poll for the non-synchronous case (§3.4). Depends on T-N010. *Acceptance:
    fixture test where a delayed reply is picked up within the poll window and matched by text/source
    (no `client_message_id` on this route, §3.1.8), and a test where `CLIENT_RETRY_WINDOW_S` elapses
    first and the UI falls back to UNCONFIRMED.*
18. **T-N013 Composer states** (client): implement §3.7's revised state machine (`stale`, `busy`,
    `sent (guarded)`, `interleave`, `send unavailable`) as an extension of F1's existing pending-record
    machinery (`CL-1`..`CL-7`). Depends on T-N010, T-N012. *Acceptance: state-machine unit tests for
    every row in §3.7's table, plus a UX review sign-off (independent, per §4).*
19. **T-N014 Stop (already-running turn only)**: verify `INT-5` is reachable unchanged once sends
    exist — no new code expected, only a regression test. Depends on T-N010. *Acceptance: fixture
    test, send → turn starts → `/stop` → `202 forwarded` → (if `confirmed_settle`)
    `turn.settled{outcome:"stopped"}`, else the existing local "stop sent" fallback (`INT-6`).*
20. **T-N015 Build/route qualification: `direct_send_supported_builds.json` + guarded-write suite**
    (§3.6). Depends on T-N003 through T-N011 existing in reviewable form. *Acceptance:
    `tools/compat/run_matrix.py` extended per §3.6, run against `stock-base`, `experimental` and
    `pr106742` extractions **with a fixture `api_server` explicitly enabled**, producing candidate
    entries for human review — never auto-populating the committed list, matching the existing
    T063/T064 split.*
21. **T-N016 Negative test suite — required, per the review's §5, mapped to OD-N10's narrowed writer
    set (§3.1.8(iii)):** api_server-vs-api_server (two concurrent callers on the same Bot Chat);
    `/v1/runs` targeting the same Bot Chat concurrently with a session_chat call; a simulated wake
    (`run_internal_session_turn`) racing a send; Desktop-before-its-first-prompt racing a send;
    CLI-after-`/compress` (covered by T-N007's own fixtures, referenced here for completeness);
    double-tap / two phones sending near-simultaneously; a timeout followed by a retry under the same
    `cmid` (T-N008); compression occurring mid-send (T-N011); a non-loopback bind (T-N003b); a proxy
    environment variable set (T-N003b). ACP and general CLI/Discord/Telegram sessions are explicitly
    **not** tested as send targets — they are out of scope under OD-N10, not an oversight. Depends on
    T-N007 through T-N011, T-N003b. *Acceptance: every listed scenario has a named, passing (or
    explicitly-residual-and-documented) test; `interleave_detected` is never treated as proof of
    full synchronization until every scenario in this list passes, per the review's own closing
    instruction.*
22. **T-N017 Security review of the full write path.** Depends on T-N015, T-N016 and every task above
    existing in reviewable form. *Acceptance: independent review sign-off covering the new
    `HERMES_API_GAP` entries (T-N007's registry read, T-N009's loopback+credential dependency), the
    guard's quantified residual race and the (iii) enumeration table's likelihood assessments,
    replay/idempotency (T-N008), and the approvals/clarify read-only boundary (§3.8) — blocking, per
    F1's "no self-certification" discipline.*
23. **T-N018 "Owner action": enable `api_server` on the default profile.** **This is a live-config
    change on the owner's actual Hermes install, not code** — `~/.hermes/config.yaml` today has no
    `api_server` entry and `~/.hermes/.env` has no `API_SERVER_*` key (verified directly, read-only,
    §1.9.1). Depends on T-N017. *Acceptance: an explicit, recorded owner action (or an explicit owner
    delegation to the controller to perform it) setting `gateway.platforms.api_server.enabled: true`
    (or equivalent) and a generated `API_SERVER_KEY` in `.env`, on a build T-N015 has qualified —
    nothing earlier in this list can substitute for this, and no task in this document performs it
    unilaterally.*
24. **T-N019 Owner dogfood activation.** Distinct from T-N001b's *decision* record and from T-N018's
    config change: this is turning T-N002b's flag on, for the owner's own instance. Depends on T-N017,
    T-N018. *Acceptance: an explicit, recorded owner action naming the specific build and profile the
    flag was enabled on.* Only after this may §4's "live Hermes phase" begin, and only against
    designated test bots per OD-L9 until further owner input.

---

## 6. Risks

Options B/C's own risks (v2's R-C1/R-C4/R-C5/R-C9/R-C10) are **retained below but rescoped to the
background/fallback transport only** (§1.9.3) — they are no longer about the primary send path, since
Option D (§1.9) does not use `defer_policy`, `admit_native` or the auto-upgrade detector at all for
the ruled mechanism. R-C11 is rewritten twice now (v3: fork-and-seed-illusion → interleave; v4: the
post-hoc check itself corrected per the review). R-C12/R-C13/R-C14 are updated for OD-N10's narrower
target, and R-C15/R-C16/R-C17 are new, added directly from the independent review's BLOCKERs.

| # | Risk | Severity | Notes |
|---|---|---|---|
| R-C1 (background only) | **PR 106742 is unmerged and upstream-controlled.** Relevant only to the background/fallback transport (Option C, §1.9.3), not the ruled primary mechanism. | Low | Not scheduled in the current task list; recorded for if/when the fallback is built. |
| R-C2 | **A guarded-but-direct write mode, once it exists on the wire, is a permanent temptation to broaden** past owner-only dogfood. | High | Mitigation unchanged: T-N002b's flag defaults OFF and is the sole gate; T-N001b requires the lift to be permanently recorded in `R0_OWNER_DECISIONS.md`'s own series. |
| R-C3 (revised in v4) | **Option D's guard is a read-then-act sequence, not atomic — the residual race is real, quantified, and now *narrower but not zero* per OD-N10's (iii) enumeration** (§3.1.8): a first-ever Desktop prompt racing HMP's call, a second concurrent api/peer-dm caller, wake, or a misconfigured cron job. A test suite that only exercises the mailbox-covered common case would let this be quietly treated as fully solved. | Medium (down from Medium-High in v3 — OD-N10's native mailbox coverage removed the largest share of this risk, but did not remove all of it) | Mitigation: T-N011's acceptance test requires a *deliberately interleaved* fixture proving `interleave_detected` actually fires, for each of (iii)'s "No" rows specifically, not just one generic case. |
| R-C4 (background only) | **Busy/queue/merge behaviour under stock Hermes is config-dependent**, relevant only to the background/fallback transport — Option D refuses closed on `session_busy` or defers to Desktop's mailbox rather than relying on Hermes's queue/merge behavior at all. | Low | Not scheduled in the current task list; recorded for if/when the fallback is built. |
| R-C5 (background only) | **`SessionDB.has_platform_message_id` and `SessionAuthority.admit_native` are private, undocumented internals**, relevant only to the background/fallback transport. | Low | Same mitigation pattern as always: pin exact builds, treat as `HERMES_API_GAP` — deferred to if/when the fallback is built. |
| R-C6 | **The composer's guard-driven states (§3.7: stale/busy/interleave) may read as ambiguous or alarming to a real user.** | Low-Medium | `UX_CONTRACT_GAP`, flagged not resolved here; needs the same independent UX review F1 required. |
| R-C7 (resolved) | v2's risk ("the fork-and-seed answer might be a bait-and-switch") no longer applies — the owner's mechanism ruling specified a same-session guard instead. | N/A (historical) | See R-C11 for the residual risk in the mechanism actually chosen. |
| R-C8 | **Approvals/clarify raised mid-turn (OD-N7, ruled) may make "read-only visibility" feel broken.** | Low | Unchanged; matches F1's own existing residual for approval-heavy bots. |
| R-C9 (background only) | **The owner-dogfood gate flag (T-N002b) is a single boolean on a shared host config.** | Medium | Unchanged mitigation: an explicit design choice, named to the owner plainly. |
| R-C10 (background only) | **The auto-upgrade detector (§1.8) is retained but demoted** — only matters if the background/fallback transport is ever built. | Low | Not scheduled in the current task list. |
| R-C11 (revised in v4) | **The interleave-detected case (§3.1.8, §3.3, §3.7), now precisely defined**, is the successor of v2's fork-and-seed-illusion risk. v3's version of this check was itself unsound (review finding #5) — a user could see a false `interleave_detected` on an ordinary compression rotation, or miss a real interleave the old check couldn't catch. v4's redefinition (post-compression transcript, text/timestamp/source identification with stated limits, deferred for the mailbox path) closes both failure modes the review found, but the **identification-limit residual remains**: two identical texts sent close together are indistinguishable by the post-hoc check. | Medium | Mitigation: T-N011 now requires both a true-positive (real interleave) and a true-negative (ordinary compression, no interleave) fixture — the review's own explicit ask; copy effectiveness remains a UX-review question. |
| R-C12 (revised in v4) | **The loopback credential and the `api_server` route shape remain a materially different kind of dependency from anything else in HMP's `HERMES_API_GAP` list.** v4 corrects the specific route/body/credential errors the review found (findings #1/#2/#3), and adds loopback-bind + no-proxy enforcement (finding #6, T-N003b) — but the *underlying* risk that a future Hermes release changes this generic product API without any awareness HMP depends on it is unchanged in kind. | High | Mitigation: §3.6's versioned route probe, now including an authenticated behavioral check (not `capabilities.session_chat` alone, per finding #3) — a best-effort signal, not a guarantee. Still the single biggest structural risk of the ruled mechanism. |
| R-C13 (revised for OD-N10) | **Every send now depends on `api_server`'s availability, key, and loopback bind — not as a v3-style "recommended uniformity" choice, but as the mechanism itself** (OD-N10 removed the alternative "phone's own separate conversation" path entirely, §1.9.2). If `api_server` is disabled, misconfigured, or its key rotates, the composer goes read-only for every bot, not a subset. | Medium | Stated plainly, not an oversight (§1.9.2's "Consequence for F1's `/conversations/default`"). Mitigation: §3.7's "send unavailable" state must clearly distinguish this cause; T-N018/T-N019's owner actions are the operational control point. |
| R-C14 (superseded by (iii)'s table) | v3's single "queued gateway follow-up" residual is now one specific row inside §3.1.8(iii)'s full enumeration, which also names Desktop-before-first-prompt, other api/peer-dm callers, wake, and cron — a more complete accounting than a single risk row can carry. | See §3.1.8(iii) | Retained as a pointer only; the per-writer likelihood assessments live in the guard section itself, not duplicated here. |
| R-C15 (new, from review finding #4) | **`registry_home` and full-compression-chain correctness are new, subtle correctness requirements** (§3.1.8(ii)) — a wrong `registry_home` (e.g. left at the default for a secondary profile) or a check against only the live tip (missing a lease on a pre-compression id) both silently produce a false "not busy," exactly the class of bug the review caught in v3. | High (until T-N007's specific regression tests pass) | Mitigation: T-N007's acceptance criteria require dedicated fixtures for both failure modes specifically, not folded into a generic "busy" test — this is a "prove the fix, don't just claim it" requirement. |
| R-C16 (new, from review finding #6) | **A non-loopback `api_server` bind, or an HTTP client that honors proxy environment variables, turns a local convenience mechanism into a host-user RCE / credential-exfiltration surface** — Hermes itself only warns, never refuses, on a non-loopback bind (`api_server.py:4441-4456`). | High | Mitigation: T-N003b's explicit bind check (fail closed if not provably loopback) and `trust_env=False` — both new in v4, both blocking per the review. |
| R-C17 (new, from review finding #4/(i)) | **HMP's own idempotency reservation, if implemented as "record after success" (v3's original design) rather than "reserve before the call," leaves an unfenced window** where a timeout or crash between the call and the recording lets "Send as new" start a genuine second agent turn. | High (until T-N008 ships as specified) | Mitigation: T-N008 moves the reservation to before the call, held through the timeout window, with timeout reconciliation that never auto-resends — this was the review's own explicit fix, not a design choice this document made independently. |

---

## Appendix: file:line evidence index

- `PLATFORM_ADAPTER_CAPABILITIES` definition and doc comment: `hermes_builds/experimental/src/gateway/platforms/base.py:1898-1932` (scratchpad extraction).
- `defer_policy` usage sites (experimental only): `hermes_builds/experimental/src/gateway/run_busy.py:85,90,111,113,391`; `run_turn.py:1995,2002,2022,2186,2191`; `turn_context.py:57-58`; `shutdown_flush.py:82,86,98,125`.
- Stock `handle_message` busy/queue dispatch: `hermes_builds/stock-base/src/gateway/platforms/base.py:3950-4060`.
- Stock `has_platform_message_id` dedupe probe: `hermes_builds/stock-base/src/hermes_state_messages.py:1491-1500` (append path: `:283`, `:305`).
- PR 106742 `admit_native`: `pr106742/gateway/session_authority.py:232-247`.
- PR 106742 `admit_session_input` (durable idempotency): `pr106742/hermes_state_runtime.py:86-114`.
- PR 106742 `unknown_execution` on restart: `pr106742/hermes_state_runtime.py:130-139`; `pr106742/gateway/session_authority.py` (`recover_native_sessions`, immediately following `admit_native`).
- F1's existing `gate.py` (GU-2/GU-3/GU-4 already implemented, unused by F1's routes): `server/hmp_plugin/gate.py`.
- F1's `write_supported_builds.json` (OD-F3's empty matrix): `server/hmp_plugin/write_supported_builds.json`.
- `docs/research/HERMES_PLUGIN_DURABILITY.md` lines 697-716 ("Upstream PR 106742... evidence, 2026-09-26") — this design's starting point for §1.5.

**OD-N3 investigation (§3.1), all against the owner's live build, read-only, `git rev-parse HEAD`
confirmed `8afaab3703e336d72a72c812dd2dd249f04f166a` in `~/.hermes/hermes-agent`:**

- `api_server` route table (`/api/sessions/{session_id}/chat` and siblings): `gateway/platforms/api_server.py:1731-1744`.
- `_prepare_session_chat` (arbitrary-session addressing, `session_history_delivery` opt-in note): `gateway/platforms/api_server.py:3288-3350`.
- `_handle_session_chat` (`_run_agent` call, no active-session lease acquired anywhere in this file): `gateway/platforms/api_server.py:3505-3541`.
- `_run_agent` definition (searched for, and not containing, any `try_acquire_active_session` call): `gateway/platforms/api_server.py:4128-4230`.
- `_admit_to_live_bot_chat` / `_answer_through_live_bot_chat` (the narrow "canonical Bot Chat" exception, and its own doc comment explaining the double-writer risk in Hermes's own words): `gateway/platforms/api_server.py:3399-3448`.
- `X-Hermes-Session-Key` / `API_SERVER_KEY` auth requirement: `gateway/platforms/api_server.py:1820-1839`.
- `find_canonical_owner` / `find_canonical_live_owner` (Bot-Chat-titled session only, consumer opt-in required): `tools/bot_live_delivery.py:32-60`.
- Desktop's own lease acquisition, correctly using the active-session registry, with the matching `bot_live_delivery_consumer` opt-in: `tui_gateway/session_lifecycle.py:63-88`.
- `try_acquire_active_session` (the general, cross-process, fail-closed, per-session exclusivity primitive) and its docstring ("Per-session exclusivity is CORRECTNESS, enforced unconditionally"): `hermes_cli/active_sessions.py:482-570`.
- Callers of `try_acquire_active_session` confirmed by grep across the whole owner-local tree: `cli.py:923`, `tui_gateway/session_lifecycle.py:74`, `gateway/run_busy.py:227` — `gateway/platforms/api_server.py` is **not** among them.
- Gateway messaging-platform lease acquisition, keyed by `session_key` (not the Hermes-internal `session_id`): `gateway/run_busy.py:213-243`; call site `gateway/run_inbound.py:1330-1334` (`_quick_key = self._session_key_for_source(source)`, acquired "before any await... without this sentinel a second message... spins up a duplicate agent").
- `session_key` construction format (private, never on the mobile wire): `gateway/session.py:673`, `build_session_key`, as already cited by A1 §1.4.
- ACP session-to-Hermes-session provenance (1:1 editor-connection model): `acp_adapter/provenance.py:5-38`.
- PR 106742 `host_attach.py` (process-level "one gateway owns every profile", not session-level attach — module docstring, five outcomes): `pr106742/gateway/host_attach.py:1-19` (docstring), `:49-53` (`START`/`ATTACH`/etc. constants).
- A1's own evidence for `session_key`'s sensitivity and the private `sessions` schema columns, reused directly in §3.1.4/§3.1: `specs/001-connect-and-browse/amendments/A1-session-browsing.md` (branch `f1/w-sessions-design` @ `100d021`), §1.2, §1.4, §2 SES-1c.

**OD-N3 mechanism ruling investigation (§1.9, §3.1.8, §3.6), same owner build, same read-only
discipline, all additionally confirmed by direct `sed`/`grep` reads during this revision:**

- `api_server`'s `POST /api/sessions/{id}/chat` route table entry: `gateway/platforms/api_server.py:1738`.
- `_check_auth` (`Authorization: Bearer` ladder): `gateway/platforms/api_server.py:1554-1569`.
- `API_SERVER_KEY` read via the documented `get_scoped_secret` helper: `gateway/platforms/api_server.py:1191` (`self._api_key: str = extra.get("key", _get_scoped_secret("API_SERVER_KEY", ""))`).
- `/v1/capabilities` static feature flags, including `"session_chat": True`: `gateway/platforms/api_server.py:67-75`.
- `_handle_session_chat`'s synchronous JSON reply shape: `gateway/platforms/api_server.py:3505-3541`.
- Port-binding and shared-listener-mirror constants (`PORT_BINDING_PLATFORM_VALUES`, `SHARED_LISTENER_MIRROR_PLATFORMS`, `SHARED_LISTENER_MIRROR_PATHS`): `gateway/config.py:280-292`.
- The multiplex reconciler's own skip-and-mirror log lines for `api_server`/`webhook` on a secondary profile: `gateway/run_adapters.py:1171-1177`.
- The owner's default profile has no `api_server` config and no `API_SERVER_*` key today: verified directly, read-only, name-only check (no secret values read) — `grep -n api_server ~/.hermes/config.yaml` (no match) and `grep -o '^API_SERVER_[A-Z_]*' ~/.hermes/.env` (no match); `API_SERVER_KEY` appears only in the general `_ENV_CONFIG_KEYS` frozenset that routes it through `.env` if ever set, `hermes_cli/config.py:856-864`.
- `try_acquire_active_session`'s docstring ("Per-session exclusivity is CORRECTNESS, enforced unconditionally") and body: `hermes_cli/active_sessions.py:482-570` (re-confirmed this revision for the guard's exact wording).
- CLI's own whole-process-lifetime lease claim (`_claim_active_session`, "Claim a global active-session slot for this CLI process"): `cli.py:915-935`.
- `active_session_registry_snapshot` (the exact function this guard reads, read-only, pruning dead entries before returning): `hermes_cli/active_sessions.py:711-740`.

**v4 review-response and OD-N10 investigation, same owner build, same read-only discipline:**

- Correct route path and mirror rule: `_http_route_table`'s `session_chat` entry, `gateway/platforms/api_server.py:1738`; the generic `/p/{profile}` mirror over every route, `:4429-4431`.
- Correct body field (`message`/`input`, not `text`): `_session_chat_user_message`, `api_server.py:661-665`.
- Per-profile credential coupling: `_expected_api_key` (default vs. named-profile scoping), `api_server.py:1529-1544`; `_check_auth`'s "named profiles fail closed rather than inherit the owner's key" comment, `:1554`; the default listener's startup guard (`_api_key_passes_startup_guard`, refuses to start without a real key), `:4363-4390`.
- `/v1/capabilities`'s static, auth-independent `session_chat` flag: `api_server.py:67-75`.
- `_handle_session_chat`'s completion body and `effective_session_id`: `api_server.py:3540-3552`.
- `_get_existing_session_or_404` accepting an ended parent, no tip-following: `api_server.py:3003-3010`.
- Compression rotation during a turn, `agent.session_id` change: `api_server.py:4265-4280`.
- `/v1/runs`'s own idempotency store and live-tip resolution (`_resolve_live_session_id`), and its own call into `_admit_to_live_bot_chat`: `gateway/platforms/api_server_runs.py:660-705`, `:746`, `:538` (`_resolve_live_session_id` def).
- `run_internal_session_turn`, "IN-PROCESS (no HTTP, no API key)": `api_server.py:3021-3027`.
- Desktop's lazily-claimed lease ("claimed lazily on the first turn"): `tui_gateway/methods_session.py:387`.
- CLI `/compress` updating `self.session_id` without moving the lease: `hermes_cli/cli_session_mixin.py:970-990`.
- `listen_address`'s host/port precedence (config wins over env, default loopback) and the network-accessible warning (never a refusal): `api_server.py:205-225`, `:4441-4456`.
- Zero `try_acquire_active_session` references anywhere under `acp_adapter/` (grep, this revision).
- `BOT_CHAT_TITLE`/canonical-session gate: `tools/bot_mode_probe.py:1-31`.
- `CANONICAL_CHAT_TITLE`, "Each bot has ONE forever chat, identified by NAME": `apps/desktop/src/plugins/hermes-bots/canonical-chat.ts:1-47`.
- `openBotCanonicalChat`, the Bots view's own click-to-open path, always resolving to the canonical session: `canonical-chat.ts:547-577`.
- `last_session` as a roster-row activity signal only, never an alternate chat-pane target, and "Canonical Bot Chats are hidden from the session list by design": `apps/desktop/src/plugins/hermes-bots/data.ts:1494-1512`.
- `hermes peer dm`'s CLI-subprocess transport (local: plain `hermes -p <name> chat -c "Bot Chat"`; remote: reaches the target host's own `api_server`): `tools/bot_mode_dm.py:1-13`.
- `find_canonical_owner`/`find_canonical_live_owner` (already cited in v3, re-confirmed): `tools/bot_live_delivery.py:32-60`.
- `_admit_to_live_bot_chat`/`_answer_through_live_bot_chat` (already cited in v3, re-confirmed, now also shown shared with `/v1/runs`): `api_server.py:3396-3452`.

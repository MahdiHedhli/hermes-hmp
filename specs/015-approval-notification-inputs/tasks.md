# Tasks: approval-lane inputs I-1, I-2, I-6

Dependency-ordered. One checkable item per reviewable change. Workers tick no review box and do
not self-certify. Root froze `ROOT_DECISIONS.md` on 2026-10-02 (T002); Phase 1 is authorized.
No task starts a native fixture, installs a dependency, touches a live host or device, or edits
the native harness or its test-tool fingerprint bootstrap.

## Phase 0: root

- [x] T001 Root architecture review of spec, plan, tasks, root decisions and security checklist.
- [x] T002 Root freezes RD-1..RD-13 (or amends them) and authorizes Phase 1.

## Phase 1: shared contract (single worker; blocks everything after it)

- [x] T010 Add the plan §2.1 types to `prompts.py`: `ApprovalInserted`, the two cause sets and
      `is_authoritative`, `MemberState` and `ALL_OPEN`, `RowView`, `VisibleSet`,
      `PromptRow.settle_cause` (default `None`), `PromptStore.generation`. No call site changes;
      the full unit suite stays green unchanged.
- [x] T011 Contract test `test_approval_input_contract.py`: frozen dataclasses, exact cause sets,
      `is_authoritative(None)` is false, generation tokens differ per store (including stores
      built concurrently from several threads), `settle_cause` is absent from `wire_prompt` and
      `phone_open_request`. `RowView` is hashable and `wire` is excluded from compare and hash
      (`compare=False, hash=False`); `wire` is a `MappingProxyType` whose `choices` is a tuple;
      `session_key` and `wire` default to `None`.
- [x] T012 Root checkpoint: the types are frozen. Later tasks may not change them; a needed change
      returns to root.

## Phase 2: the three inputs (each one commit, own tests, independently revertible)

Order: strictly sequential, I-2 (T020), then I-1 (T030), then I-6 (T040), one commit per input,
by a single worker (`RD-10`, root choice). T020, T030 and T040 all edit `prompts.py`, and T040's
`RowView` carries `settle_cause` from T020, so no parallel worktrees. Each task starts only after
the previous one is committed.

- [x] T020 **I-2.** `expire(..., cause=)` at the five internal sites; `settle_answer` as the only
      answer-path writer of `status`, `settled_at` and `settle_cause` in one `_guard` section,
      replacing the unguarded writes in `answer_prompt`; `_remember` reduced to the replay fields
      (the `settle` parameter removed entirely, no `await` between `settle_answer` and it);
      `settle_answer` takes the pre-await `now` (595) and reads no clock; cause derivation per
      NI-2.3; `clarify_retired` in `AdapterHooks.retire`. Tests: `test_approval_settle_cause.py`
      (NI-2.3 table through the real paths, D4 `run_ended` negative, Phone resolve `0` and coerced
      non-int negative, the in-flight purge race and cause overwrite including the recorded
      `phone_listing_omitted` downgrade, the pre-await clock, and the guarded-write probe whose
      mutants are the old unlocked writer and `_remember` still writing `settled_at`). Existing
      approval suites pass unmodified.
- [x] T030 **I-1.** Observer slot, `set_insertion_observer`, notify after release in `put`, detach
      in `close`, fixed `prompt_observer outcome=error`, containment of `Exception` (including
      `ExceptionGroup`) and `asyncio.CancelledError` only. Tests: `test_approval_insert_observer.py`
      (plan §4 I-1 rows, including the real `_apply_sse_frame` and `AdapterHooks.on_exec_approval`
      paths with a raising observer, and propagation of every other `BaseException`). No observer
      is registered anywhere in production code.
- [ ] T040 **I-6.** Predicate with the pure retention mask, `view_row`, `view_visible`
      (`include_wire`), `ServerContext.approval_members_now`, `list_visible`/`list_prompts`
      delegation, `handle_prompts_list` refactor with the exact clock and call sequence (plan
      §2.4). Tests: `test_approval_visibility_seam.py` with the frozen `150bd0f` AP-3 oracle
      copied verbatim into the test, the NI-6.5 grid (including mixed ordered multi-row cases) at
      the real route, serialized-byte comparison, scripted `ctx.now()` count, no-mutation, retention
      boundary and active-lock exemption, aliasing and `include_wire` exposure, and
      members-outside-lock checks. `reads.py` is not edited and its tests pass unmodified.

## Phase 3: verification and review

- [ ] T050 Run the focused new and existing approval tests, the full unit suite, Ruff,
      `check_plugin_surface.py`, `scan_private.py` and `scan_logs.py` (`CONTRIBUTING.md`).
      Record counts and skips; preexisting skips stay explained.
- [ ] T051 Mutation check: apply each mutant in plan §4 once and record the test that fails.
      Revert every mutant.
- [ ] T052 Diff audit: `git diff 150bd0f` touches only `prompts.py`, `request_ctx.py`,
      `server.py` (`handle_prompts_list` only), the four new test files and spec docs. No change to
      `direct_send.py`, `bridge.py`, `adapter.py`, `reads.py`, `HMP_V1.md`, manifests or fixtures.
      `_remember` has no `settle` parameter and writes no `settled_at`.
- [ ] T053 Add the 015 row to `specs/README.md`.
- [ ] T060 Independent focused review (not the author) of T020–T040 against
      `checklists/security.md`, including thread and lock behavior.
- [ ] T061 Root verification: rerun T050, defeat each guard once, accept or return findings as
      bounded defect tasks.
- [ ] T062 Root updates spec 014 section 10 status for I-1, I-2 and I-6 on its own branch. 014
      stays unwired until then (014 T003).

## Not tasks here

Native sample evidence (034 T14), packaging (034 T15), any 014 task, push relay work, owner and
provider choices, and repair of the native fixture setup.

## Shared types root checkpoint — 2026-10-02

T010–T012 have root source acceptance. Independent bounded review identified immutable
choices sharing on an already-tuple input; the one-expression repair and two discriminating
assertions are accepted. Root passed 22 final contract cases, killed the original alias mutant,
and passed configured Ruff, privacy, plugin-surface and diff checks. Before that bounded repair,
the full unit suite passed 1,565 cases with 16 explained native/Python-version skips. These
are source-unit checks, not native or operational notification evidence. The independent
reviewer did not read the mandatory app/skill documents; its authority is confined to its
recorded type/diff review. Root reviewed the frozen contract and actual finite source delta.
T020 source acceptance is recorded below. Later implementation gates remain unchecked.

## I-2 root checkpoint — 2026-10-02

T020 has independent bounded source acceptance and root verification: 216 focused cases passed,
with no skips. Root killed four causal mutants (unlocked writer, a second timestamp writer,
clock resampling and first-writer-wins). Configured Ruff, source privacy, plugin-surface and diff
checks passed. The author passed all 80 new cases and the existing approval suites; its one
skipped native probe requires an explicitly configured isolated Hermes source and interpreter
and was intentionally outside this source-only slice.

The independent reviewer found no runtime blocker. Its first reading record used the wrong
installed skill path; the private correction preserves that mistake and records the requested
1.3.63 skill separately. This is not final T060 security review. Three bounded test-hygiene
notes remain: stale replay-field omission is not detected by current route tests because the
expired-row branch returns before replay; a stale-test comment is stronger than its call-count
assertion; one lock-holder test has an unbounded event wait despite a 0.25-second hold. Root's
mutation subprocesses were bounded to 45 seconds. No native, provider, device or operational
notification evidence is claimed. T030, then T040, remain the implementation order.

## I-1 root checkpoint — 2026-10-02

T030 has incremental root source acceptance: 338 focused approval cases passed with no skips;
Ruff, plugin-surface, source privacy and diff checks passed. Root killed eleven causal mutants
covering missing/duplicate notification, clarify and duplicate filtering, lock placement,
exception containment and propagation, detach, captured reference and caller thread. Four
initial mutant transformations failed before tests started; their corrected runs failed the
intended tests. Root changed the nonblocking lock probe to return on failed acquisition, so
the assertion outside the observer detects that violation without deadlocking.

No production observer is registered. This checkpoint is not final T060 independent security
review, native evidence, priority notification delivery or a deployed change. T040 is next.

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
- [x] T040 **I-6.** Predicate with the pure retention mask, `view_row`, `view_visible`
      (`include_wire`), `ServerContext.approval_members_now`, `list_visible`/`list_prompts`
      delegation, `handle_prompts_list` refactor with the exact clock and call sequence (plan
      §2.4). Tests: `test_approval_visibility_seam.py` with the frozen `150bd0f` AP-3 oracle
      copied verbatim into the test, the NI-6.5 grid (including mixed ordered multi-row cases) at
      the real route, serialized-byte comparison, scripted `ctx.now()` count, no-mutation, retention
      boundary and active-lock exemption, aliasing and `include_wire` exposure, and
      members-outside-lock checks. `reads.py` is not edited and its tests pass unmodified.

## Phase 3: verification and review

- [x] T050 Run the focused new and existing approval tests, the full unit suite, Ruff,
      `check_plugin_surface.py`, `scan_private.py` and `scan_logs.py` (`CONTRIBUTING.md`).
      Record counts and skips; preexisting skips stay explained.
- [x] T051 Mutation check: apply each mutant in plan §4 once and record the test that fails.
      Revert every mutant.
- [x] T052 Diff audit: `git diff 150bd0f` touches only `prompts.py`, `request_ctx.py`,
      `server.py` (`handle_prompts_list` only), the four new test files and spec docs. No change to
      `direct_send.py`, `bridge.py`, `adapter.py`, `reads.py`, `HMP_V1.md`, manifests or fixtures.
      `_remember` has no `settle` parameter and writes no `settled_at`.
- [x] T053 Add the 015 row to `specs/README.md`.
- [x] T060 Independent focused review (not the author) of T020–T040 against
      `checklists/security.md`, including thread and lock behavior.
- [x] T061 Root verification: rerun T050, defeat each guard once, accept or return findings as
      bounded defect tasks.
- [x] T062 Root updates spec 014 section 10 status for I-1, I-2 and I-6 on its own branch. 014
      T003 is source accepted at `66874cf`; 014 runtime consumers remain unwired.

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

## I-6 root checkpoint — 2026-10-02

T040 has incremental root source acceptance. Root passed 542 focused cases with one explicitly
unconfigured native-probe skip, then the complete source suite passed 2,000 cases with 16
explained native-fixture or Python-version skips and one existing aiohttp deprecation warning.
Configured Ruff, plugin-surface, source privacy and diff checks passed. Root killed eighteen
causal mutants covering visibility, grace, retention, member failures, ordering, clock sequence,
reconciliation, immutable views, exposure and lock placement. The original missing test-node and
three malformed mutant transformations failed before tests; corrected runs killed those mutants.
No mutation changed the source files. This records source verification only; it does not prove
native integration, device behavior, push delivery or deployment. Final T060/T061 remain open.

## Final root source acceptance — 2026-10-02

T050–T061 have root acceptance for the three in-process inputs. Independent focused security
review accepted the unchanged production sources at `3fb19ec`, with no runtime blockers.
Root reviewed the bounded test-only repairs for N1, N2, N4 and N11: final-snapshot held changes
during the real listing await, stale replay-field writes, bounded and joined lock-holder work,
and the trailing blank line. Their four new cases detect mutants the prior tests missed.

Root passed 482 focused cases with three unconfigured native-probe skips, then 2,004 complete
source cases with 16 explained native-fixture or Python-version skips and one existing aiohttp
warning. Ruff, plugin-surface, zero-baseline source privacy and diff checks passed. The log scan
had no captured logs to scan; it is not a log-canary result. Root's final clean control passed
180 cases. Fifteen additional causal mutants failed actual assertions; the earlier four I-2,
eleven I-1 and eighteen I-6 checks remain recorded above. Some guards were checked more than
once; these counts do not describe distinct security guarantees. Transformation and collection
errors were preserved and excluded from the kills; all scratch mutations were restored.

The production-source hashes are unchanged from independent review. The finite diff audit
confirms only the three allowed production modules, four new test files, the 015 specification
and its index entry. The copied AP-3 oracle remains unchanged. `_remember` writes replay fields
only. No production observer, push runtime, native dependency, authorization or wire change
is present. The no-await-between-settlement-and-replay invariant is confirmed by source reading;
its semantically equivalent mutant survives and no test proof is claimed. The preexisting
`retire` clock callback under the guard is outside the new visibility seam.

Spec 034's two-sample native evidence covers `150bd0f`, not this 015 amendment. No native, device,
provider, operational notification or deployment acceptance is claimed here. T062 is closed by the
separate 014 branch update at `66874cf399209cde1704985dfc83ecc9a3c9cf6f`: section 10 and
T003 record the accepted inputs. Runtime implementation follows its own contract gates.

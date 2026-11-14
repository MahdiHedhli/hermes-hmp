# Root decisions (frozen 2026-10-02 after independent review and bounded F1–F11 amendments)

Root accepts the recommended choices RD-1–RD-9 and the explicit root choices RD-10–RD-13.
The independent architecture review required F1–F11; root reviewed and accepted their bounded
documentation amendments. The original freeze was design acceptance. Final source acceptance is recorded in `tasks.md`;
native, device, push and deployment evidence for this amendment remain pending.
All items are **R** (root design choice, reversible in source). None is an owner, account or
provider action, and none authorizes one.

## Inherited, not reopened

| Source | Decision | Effect here |
| --- | --- | --- |
| 014 D4 (frozen) | Run completion is not an authoritative settlement | `run_ended` is non-authoritative (NI-2.2) |
| 014 C6 (frozen) | Current visibility; no sticky hidden bit, no history observer | NI-6.6 |
| 014 D20 (frozen) | Both approval surfaces; clarify excluded | NI-1.3 notifies approvals on both surfaces only |
| 034 R9, R10, R14 | Generation fence, binding fence, native classification | reused unchanged |

## Accepted design decisions

| ID | Decision | Options | Recommendation |
| --- | --- | --- | --- |
| RD-1 | Observer cardinality per generation | (a) one slot; (b) a subscriber list | (a). 014 is the only consumer. A list adds unbounded registration and ordering questions with no current use. |
| RD-2 | Generation identity in the event | (a) an opaque int per `PromptStore`; (b) the `PromptStore` object | (a). It gives the consumer no reference to mutable state, and it compares safely across threads. 014's "prompt generation" maps to this token plus `ServerContext.prompt_store`. |
| RD-3 | Which observer exceptions are contained | (a) `Exception` (including `ExceptionGroup`) and `asyncio.CancelledError`; every other `BaseException` propagates (`KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, a `BaseExceptionGroup` not caught above, any other direct `BaseException` subclass); (b) `Exception` only | (a). On the sampled Phone path an escaping `CancelledError` would end the hook and Hermes would classify the card send as failed and fall back to text. (b) leaves that path open. Containing `CancelledError` is safe because the observer is called synchronously with no `await`, so one it raises is a callback failure and not the enclosing task's own cancellation. |
| RD-4 | Phone `resolve_gateway_approval` returning no positive count | (a) non-authoritative `phone_not_resolved`; (b) authoritative | (a). `bridge.py` coerces a malformed or non-int result to `0`, so an exact zero is not distinguishable from an unknown answer without a bridge change, which is out of scope. The Phone listing omission remains the authoritative Phone signal. |
| RD-5 | How the answer path knows a Bot Chat `stale` was native | (a) derive from row kind and surface plus the existing verdict, pinned by a test that the live Bot Chat resolver returns `stale` only from `classify_native_answer`; (b) widen the resolver verdict set | (a). It changes one function and no protocol. If a future Bot Chat resolver path returns `stale` for another reason, the pinned test fails. |
| RD-6 | Clarify retirement | (a) non-authoritative `clarify_retired`; (b) authoritative | (a). It is not in 014's closed set, and clarify rows never notify (D20). |
| RD-7 | Precedence between the answer path and concurrent local expiry | (a) keep today's unconditional answer overwrite and record its cause; (b) first writer wins everywhere | (a). (b) would change AP-4 results when a watchdog purge lands during an awaited Hermes call. That breaks the equivalence requirement. The overwrite covers any concurrent local settlement and uses the pre-await `now` (`prompts.py` 595). It can downgrade a recorded authoritative Phone cause to `phone_not_resolved`; that is intended and fails closed, with no merge rule. |
| RD-8 | `list_visible` (RO-3 snapshot via `reads.py`) | (a) delegate to the same predicate, signature and purge unchanged; (b) leave its own copy | (a). One predicate, so dispatch, resolve, AP-3 and the snapshot cannot drift. `reads.py` is not edited. |
| RD-9 | Reading the held marker and the rows | (a) one `_guard` section; (b) keep the two sections of `150bd0f` | (a). For each serialized schedule the result is identical. Under a concurrent set or clear it returns one of the results the old code could return. It also makes the `desktop_held` flag consistent with the listed rows. |
| RD-10 | Phase 2 sequencing | (a) I-2 first, then I-1 and I-6 in parallel worktrees; (b) strictly sequential I-2, I-1, I-6 | **Root choice: (b)**, one commit per input. T020, T030 and T040 all edit `prompts.py`, and T040's `RowView` carries `settle_cause` from T020. |
| RD-11 | Retention deletion in the pure views | (a) a pure retention mask mirroring `purge`'s exact retention-delete conditions, comparison and `_lock_users` exemption, with no mutation; `view_row` returns `None` and `view_visible` omits the row when the next `purge` would delete it; (b) record it as a residual | **Root choice: (a).** Views then agree with 014's "purged row is `404`" before the watchdog next runs. No new timer, observer, cache or authority. |
| RD-12 | `RowView` immutability and exposure | (a) `wire` is a `MappingProxyType` over an owned fresh dict with a tuple `choices`, `compare=False, hash=False`; `view_visible(..., include_wire=False)` populates `wire` and `session_key` only when true (AP-3, both phases); `view_row` never does; (b) a plain dict, or a session key on every view | **Root choice: (a).** Frozen snapshots are really immutable, `RowView` stays hashable, 014 never receives a session key, and AP-3 bytes stay identical through `_plain`. |
| RD-13 | The second `settled_at` writer in `_remember` | (a) remove `_remember`'s `settle` parameter entirely, leaving replay fields only; `settle_answer` is the only answer-path writer of `status`, `settled_at` and cause, and `_remember` follows it with no `await`; (b) fold the replay fields into `settle_answer` | **Root choice: (a).** Replay fields have one reader (`answer_prompt`, under the per-row lock on the loop), so they need no `_guard`. |

## Prerequisite gaps (recorded, not decided here)

| Gap | Kind | Owner |
| --- | --- | --- |
| 034 T14 now has two-sample native evidence for base `150bd0f` (13 selected cases per sample, no skips). It does not cover this amendment. This spec neither runs nor repairs that matrix; 015 evidence remains source-only. | `EVIDENCE_GAP` | Root (034 T14) |
| Phone hook thread and wait bound read on one sampled build (`ac0cfa7d`) only. NI-1.4 does not depend on it. | `EVIDENCE_GAP` (bounded) | HMP |
| Cross-surface coverage (Desktop, CLI, cron, other platforms) is unchanged. 015 notifies only for rows the 034 lane inserts. | `EVIDENCE_GAP` (014 T005) | Project |
| RO-3 snapshot renders live rows on a worker thread, and the legacy `list_visible`, `get`, `open_clarifies` and `answer_row` still return live rows; AP-3 propagates a `BridgeError` from a non-list Phone listing; AP-3 reads the owner predicate synchronously on the loop. All preexisting and preserved for equivalence. | Residual | HMP (later lane) |
| 014 owner and provisioning choices O1–O6. | `OA`, pending | Owner |

# Original cleanup actor's current stop-data consumer — November 6, 2026

`SignedReadNotice.current_stop_for_cleanup` adds a fixed ORIGINAL cleanup actor,
separate from the original-work publisher. Shared stopped-cursor metadata selects
no actor; the two public internal entry points each enforce their own retained
allocation/current task. A live uncancelled original work task is mandatory. A
delivered historical Future cannot revive completed work or borrow its actor.

The consumer joins actual notice Future/fact allocation, correlated original
signed envelope/body wake retirement, output withdrawal, actual write-quiescence,
current complete retained-role material and earliest original cleanup budget.
Actual FD/selector and cleanup-clock checks precede repeated role/actor/stop/end
and allocation seals. A captured end is only a ceiling: every query enforces the
current minimum and remaining budget. Admitted currentness failure becomes sticky
notice/cleanup unknown; wrong actor, premature or completed-work queries create no
new authority. This returns only the existing stop FACT, not read/CANCEL permission.

## Original cleanup loop coupling

The original cleanup loop now waits on the SAME retained notice Future OR its
original work task under existing remaining cleanup time. It can examine a current
stop while that original work task is live, before the old work join. No reader,
new task, replacement deadline, legacy read fact or fabricated joined flag is
introduced. The signed request STILL RETURNS FALSE and ordinary external Task
cancellation remains. Concurrent CANCEL is still refused while work is live.
The existing whole-work join/signing gates are unchanged.

Independent review caught an important dispatch boundary: computing `_remaining`
can run callbacks after a Future tuple was selected but before asyncio.wait uses
it. Root now holds the ACTUAL notice allocation/Future/loop and original work
allocation/task, computes remaining time, then rechecks original aliases and
native Future AND Task dispatch plus scheduler before registration. Post-await
checks compare the SAME held originals, not freshly followed aliases. Final-clock
Future dispatch shadow/paired substitution refuse before any foreign callback.

## Actual actor tests and harness failures

An actual original work task publishes its signed stop and waits a fixture Event;
the actual allocated cleanup task queries while the work task remains live. The
sender cannot query as cleanup. Successful data queries repeat without granting
CANCEL. The actual cleanup loop also queries; no replacement task or completed
record is fabricated. A later query on that same cleanup actor AFTER actual work
join refuses without poisoning the historical notice. Copied fact, paired Future
and role retirement during the actual receiver clock refuse without restoration.
Actual thirteen-byte partial-body stop uses the same sender/cleanup rendezvous.

Initial harness runs failed because the public caller can correctly refuse at
first cause before the sender/cleanup rendezvous finishes, and a broad publication
future-fault suffix also matched the receiver fault case. Observers now await the
ACTUAL original task(s) under the existing work ceiling and preserve any actual
actor exception; selectors distinguish publisher and receiver cases. No done,
phase, intent or IO flags were repaired to pass. The initial old cleanup loop also
joined work before the new notice could arrive; the bounded original notice/work
wait is the actual source integration, not a fake task wrapper. A final stale-work
assertion initially raced actual cleanup completion; the observer now awaits the
actual cleanup task. All failed logs remain private evidence.

Four receiver cases passed1.95s; two root dispatch causals join them (six passed
2.71s). The final pre-body-extension nearby matrix passed24 in8.59s. Actual body
receiver passed1 in1.82s. These overlap. Independent read-only review accepted final
source/causals and performed no tests/native operations. Exact expanded outcome
is recorded after its actual terminal completion. Lint/whitespace pass.

Read admission/running cleanup cursor, concurrent-CANCEL signing, same-reader
discard/authenticated grammar-bound TERMINAL/ACK, production/physical image
qualification remain open. Stop DATA alone cannot select any of those permissions.
Prior broker failures and native sender-destination incident remain unresolved.
No deployment/device/build/config/grant/provider changed.

## Adjacent original-work join dispatch fence

A source audit found the existing subsequent work join had the same callback
registration pattern: `_remaining` could change Task dispatch before asyncio.wait.
It now holds the ORIGINAL work allocation/task and cleanup loop, computes remaining
time, reseals ownership and native Task/scheduler dispatch, then waits that held
task. It rechecks the actual original allocation/task before recording work_joined.
No uncancelled-task or fresh live work/role condition was added: joining cancelled
owned work remains valid local cleanup. No budget, join or CANCEL gate was relaxed.

The causal uses an actual unsigned cooperative reader and actual permitted CANCEL
write; the final join clock shadows that original work Task's add_done_callback.
The join refuses before foreign invocation, retains unknown, and grants no work
join/FD/clock closure or job credit. Only after the fixture peer finishes its own
stream and the ACTUAL original task is terminal does fixture teardown remove its
method shadow. No protocol replay or state/phase/intent repair follows. It passed
together with preserved normal caller-cancel cleanup (two in0.91s). The first
attempt passed the behavior but failed teardown because vars(native Task) is not
supported on this runtime; exact stage-controlled deletion after real terminal
replaced it. That failed log remains recorded.

Independent read-only review accepted the adjacent fence and causal, with no
reviewer execution. The earlier expanded consumer run passed1,843/one-skip in
160.30s BEFORE this adjacent fence; it is prior evidence, not final-source coverage.
The final exact expanded outcome is recorded after actual terminal completion.
Earlier intermittent broker failures remain unresolved regardless of a later pass.

Final exact-source expanded regression completed: **1,844 passed, one skipped in
162.91s**. Lint/whitespace pass. Focused/body/join runs overlap and are not added.
This is local affected-source coverage, not CI/native installation/physical/release
qualification. The prior two intermittent broker failures did not reproduce here;
passing now does not establish their causes or mark them resolved.

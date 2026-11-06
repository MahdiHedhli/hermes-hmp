# Pure remaining-phase partition (not execution authority)

The original run at `21937dc` completed 174 pairs, then pair 174 exceeded the
unchanged 12-second observation limit. Its retained actor settled to terminal 0,
but that attempt stays refused; indices 175..383 never started. Existing evidence
is retained. There is no automatic resume, retry, deletion or deadline extension.

`local_media_native_writer_partition.py` is inert on import and performs no IO,
process admission or native calls. Its input catalog must have the exact digest
of the immutable 384-pair base source, including order. This is an offline test
provenance constraint, never a product feature/version allowlist. Malformed,
expanded, duplicate, reordered or mismatched-count inputs refuse.

For the actual 174/174 boundary, the output contains every unattempted phase
exactly once: 418 phases from 209 pairs. Only the largest 98-session/full-prompt
shape (case modulo four equals three) is divided into one phase per process;
all other pairs stay paired. Both proof contexts, prompts, history and selector
sizes remain required inside each phase. This yields 301 jobs: the original
phase scope is preserved, not reduced to make a test pass. The existing
single-phase driver path already has one bounded cached heavy sample; it does
not prove all proposed jobs or establish a runtime/storage ceiling.

Every job retains its original pair/phase coordinates. Pair 174 and all completed
indices are excluded. Even successful execution of these jobs plus the prefix
would leave pair 174's two phases unaccepted: it cannot prove all 768 phases.
Any future fresh repartition experiment for that case needs its own explicit
reviewed plan, new roots and evidence; it cannot rehabilitate the old attempt.
The additional ordinary/delegate scope remains separately source-bound.

The output deliberately reports full-matrix completion false and requires
source-bound terminal-receipt reconciliation. This pure planner does not read
or certify any journal/receipt. A future execution owner must independently
verify the original terminal state, completed/refused request mapping and exact
source/artifact bindings before admission. It must keep exclusive fresh roots,
current capacity checks, source pinning, original worker settlement and the
unchanged per-process observation limit. No execution runner is implemented by
this planner and no job has run from it.

Root's 17 pure model cases pass, including all original coordinates, heavy-only
splitting, count/type failures, expanded/duplicate/permuted catalogs and boundary
indices. Independent source review and execution-contract integration remain
required. Native prefix artifact review, the refused-case acceptance gap,
supplemental execution, C6b and physical/release qualification remain open.

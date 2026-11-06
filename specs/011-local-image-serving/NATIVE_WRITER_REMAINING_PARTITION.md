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

## Heavy-case fresh partition samples reviewed — November 6, 2026

Two separately reviewed fresh single-phase experiments at `5c96927` completed
under the unchanged 12-second limit. Each preserved the largest 98-session/full-
prompt Bot shape, both proof contexts, history and one selected tool row.
`deactivate:ids0` and `deactivate:page` each refused the concurrent binding with
`rows_changed`, then freshly returned `ok` with an empty accepted selection.
Independent readback accepted all 52 artifacts, source/Git/runtime/entry/cache
bindings, 39/39 borrows per process and cleanup. No expiry or settlement-only
success was used. The original paired attempt remains refused and unchanged.

The pure remaining planner preserves all 418 never-attempted phases from pairs
175..383 in 301 jobs, splitting only the largest shape; its source review and
17 model cases passed. Its output is not execution authority and excludes the
refused pair. The combined related suite passed 696 tests. Completed-prefix
artifact audit, source-bound execution integration and supplemental coverage
remain open. No full-matrix, delivery or release pass is claimed.

## Source-bound executor candidate

`local_media_native_writer_remaining.py` adds a separate offline execution owner.
It requires four canonical private single-link evidence files with explicit
SHA-256 references: prefix proof, independent review record, terminal matrix
journal and original refused native receipt. The review record is an operator-held
attestation to the actual independent review, not a cryptographic reviewer
identity or any server/device permission. It binds the accepted prefix digest,
source and exact scope counts.

Admission reconciles every completed/current pair to the historical catalog,
compares recorded fields canonically (boolean/float substitutions refuse), and
requires the original native actor's known terminal-zero settlement record. An
unsettled actor, pending/mismatched review, wrong source/request or changed file
refuses before a new state or job is written. The accepted prefix remains bound
to old source `21937dc`; it is not relabeled as execution of this candidate.

The operator supplies an exclusive fresh 0700 root, expected current HMP source,
native source and explicit reviewed archive cache. Each job rechecks 32 GiB plus
1 GiB capacity admission, owns a new root and uses the existing source-pinned
single/paired driver as planned. Returned completion and source must agree.
Any exception or uncertainty keeps the exact attempted job and prevents all
later admission. No root is adopted/reused, prior artifact deleted, failed job
retried or original observation deadline extended. Native receipts remain
necessary if an I/O failure prevents the latest parent journal write.

The executor can complete only the unattempted scope (301 jobs / 418 phases).
Its full-matrix flag stays false and original-refusal-preserved stays true.
The two accepted fresh repartition observations are separate evidence. Additional
ordinary/delegate scope, final composite acceptance, C6b and device/release gates
remain open. Root's 716 related guard/model tests and lint passed; read-only
preflight against the actual evidence also passed. Independent execution-source
review is pending, and this executor has launched no native job yet.

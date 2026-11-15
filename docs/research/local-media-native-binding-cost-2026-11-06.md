# Current native complete-binding cost sample — 2026-11-06

## Scope and method

Root completed 24 fresh isolated processes at HMP
`85c83f897b3e455e890a24700bbad3b0f00418cc` against native
`ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`, using native PM Python 3.14.9
and aiohttp 3.14.5. Transport authority, profile routing and Phone-store inputs
are synthetic; SessionDB reads/writes and registry borrowing are genuine.
No live home, actual provider, permission, model or gateway is an input.

The four lineage/prompt shapes each contain BOTH Bot Chat and Phone lineages,
plus an unprompted extra. Public native reads verify four or 196 distinct exact
262,144-character prompts in the large-prompt databases. Each conversation has
258 history rows, including 128 image assistant/tool pairs split evenly between
legacy and generated cache layouts. No image path is opened or materialized by
the binding sample. Complete binding must classify and accept the exact selected
IDs; both proof contexts remain populated even when measuring Phone.

Each process measures one kind/shape and one selector count (1/16/128), after
both contexts pass all six functional selector controls. One dedicated warmup
follows earlier preparation/validation activity, then three untraced monotonic-ns
binding calls and one separate Python allocation trace. Candidate construction
and result validation are outside those intervals. Trace peak/current values
include the returned binding, above baseline; no preexisting trace is reset.
These are warm costs, not cold-start latency, native C allocation or RSS.

## Observed results

All 24 selected pairs completed within the unchanged 12-second command
observation limit: 72 timing values and 24 Python allocation samples. For 128
selectors, median complete binding time across three samples was:

| Lineage sessions | Prompt characters per session | Bot Chat | Phone |
|---:|---:|---:|---:|
| 2 | 0 | 6.464 ms | 6.830 ms |
| 2 | 262,144 | 8.950 ms | 8.312 ms |
| 98 | 0 | 83.060 ms | 87.473 ms |
| 98 | 262,144 | 197.305 ms | 162.503 ms |

Maximum traced binding peak above baseline was 26,787,680 bytes. These are
sampled observations, not ceilings or runtime admission criteria. They are not
a controlled causal comparison with the older native/Python/scanner sample.

Each process balanced 40 native acquires/releases, closed its one workload
and original serving database, settled listener/workers and reported scoped
sweep zero. All commands have known outcomes with no settlement-only expiry.
Root checked all 24 closed report/receipt cases and 672 top-level artifact
SHA/size/private-mode bindings. Each report binds 12,185 native and 374 HMP
source files, selected executable, helper and report identities. Python audit
checks disclose synthetic absent-proc probes, own-FD listings and bounded public
OS metadata reads separately from unexpected denials (zero); they are not an OS
sandbox or complete native-library IO attestation.

Independent read-only aggregate review accepted every artifact, source/literal
Git inventory, executable/helper/report binding, all 24 distinct pairs and all
264 known command outcomes. No reviewer execution is claimed. The full preparation at
`891f922` was independently source/artifact accepted before this cost stage.
Root's 235 focused model/guard tests and lint passed; these are not additional
native measurements. Exact revised-source CI is tracked separately.

## Earlier observations retained and remaining work

The first cost layout at `b220085` completed two short-lineage Bot Chat cases.
Its first long-lineage process exceeded 12 seconds; the same original actor was
retained to known exit zero, but the run remains permanently refused. It was
never promoted because of its later child report. The redesigned source uses
one shape and selector per process, preserving the complete matrix and both
proof contexts; earlier partial values do not substitute for any of the 24
current results. No deadline extension, automatic retry or actor replacement
occurred. Earlier setup failures remain in the [preparation record](../../specs/011-local-image-serving/NATIVE_BINDING_REFRESH.md).

Current mint-memory, fresh-process RSS and concurrent-writer/control/refusal/
residual-window/ABA stages remain required; the older 500 phases are historical.
This stage does not close C6b, establish atomic snapshot or ABA detection, resolve
G-M1/G-M2, qualify Linux/physical devices/production Desktop scope, activate a
feature, or authorize release. Existing serving/T12 results remain distinct.

# Actual Link audit cost — November 10, 2026

Diagnostic execution on production source `b35a8be` leaves the original native
contract and 60-second deadline unchanged. It adds local monitoring timestamps
for completed normal calls of the four already-counted functions. It does not
change production code, grant authority, file observations or acceptance checks.
The test still fails its deadline; no image/native/service qualification follows.

At the last retained checkpoint (48.89 seconds, after-phase entry), 44 observed
native operations were typed, one raw capsule retired, and close reservation was
zero. Completed inclusive durations were approximately:

| Category | Calls started | Inclusive seconds |
| --- | ---: | ---: |
| Original artifact owner guard | 5,182 | 31.57 |
| Runtime current | 5,192 | 8.08 |
| Link engine origin | 8,383 | 7.79 |
| Parent origin | 2,872 | 3.20 |

Nested categories overlap and must not be summed or subtracted as an exclusive
profile. Instrumentation perturbs timing. Pending/unwound calls are not included
in completed time; `guard_open_calls` records unmatched starts, including possible
unwinds, rather than a proof of live frames. All four counts were zero at this
checkpoint. This is diagnostic evidence, not a performance acceptance threshold.

The result changes implementation priority: class-member columns alone cannot
be assumed to resolve the full deadline. Their local value-only microbenchmark
was about twice as fast but omitted custody, schema, current-key and size gates.
The direct member-loop experiment had already failed the full deadline and was
reverted. Neither experiment is retained as a production optimization.

Trace the original owner/package/selection/activation chain before implementing
the expected layout. Only remove an audit if an actual original nested checker
performs the complete same fresh check, with original object identity joins and
all later checks preserved. A prior callback return cannot cache authority. A
reviewed design is not permission to skip a security boundary or claim a feature.

The full original character/avatar and local-image delivery requirements remain
open, including full native lifecycle, runtime/service/route integration and
physical device acceptance. No upstream-only blocker has been established.

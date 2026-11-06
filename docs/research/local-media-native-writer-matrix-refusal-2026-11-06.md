## Native writer matrix stopped at observation limit — November 6, 2026

The 768-phase run at `21937dc` completed 174 pairs (348 phases), then stopped
on pair 174: the largest 98-session/full-prompt Bot shape with one selector,
`deactivate:ids0` and `deactivate:page`. Its native process exceeded the unchanged
12-second observation limit. The original retained actor settled to terminal 0;
both checkpoints and final report show balanced 53/53 borrows and closed
DB/listener/workers, but this attempt remains refused. It was not retried or
promoted to a pass, and the remaining 209 pairs were never started.

The accepted paired pilot did not prove sufficient timing margin for the full
matrix. Detailed phase timing was not captured, so the cause is not established.
Independent refusal/prefix artifact review and a reviewed heavy-shape partition
are next. No deadline extension, evidence deletion, deployment or release pass.
The isolated ordinary/delegate follow-up remains source-reviewed with native
execution pending; older statements that this matrix is running are superseded.

Source: HMP `21937dcc50fac8c118843e496c9c1c92eb43856f`; native Hermes
`ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`, Python 3.14.9 / aiohttp 3.14.5.
Exact-source CI passed 7,948 tests with 33 skips, 18 warnings and 190 subtests,
plus Unicode jobs. CI does not override the native observation refusal.

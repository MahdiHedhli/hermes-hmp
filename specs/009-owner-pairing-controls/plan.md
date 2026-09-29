# Plan

1. Add an additive per-device decision table and record schema version 2 on migration. A missing row falls back to the older private config list; an explicit row takes precedence.
2. Prompt after the one-command pairing flow's Bot Chat grant step, and after manual `pair confirm`. Require `GRANT`, with EOF and interruption defaulting to denial.
3. Add host-only `devices grant-controls` and `devices deny-controls` commands for correction and revocation.
4. Read the decision at the shared jobs/model route gate on each request. Preserve bearer, profile authorization, exact-build, and feature-flag checks.
5. Verify positive and negative routes, migration, persistence, and per-device isolation; run the public privacy gate before publishing.

No new network route or Hermes-core import is needed. This branch does not alter the live host's existing device decisions.

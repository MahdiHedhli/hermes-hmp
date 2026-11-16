# Redundant generator-parentheses lint repair

## Problem and bounded change

The exact pinned Ruff 0.16.9 command used by CI reports UP034 findings in six retained presentation/startup files. Remove only redundant parentheses accepted by that rule. Preserve imports, constants, comments, guards, deadlines, test assertions and lint configuration.

The reviewed private preview starts from 183a1189ae639843a256123c224e0301662c41d5. Ruff reports 243 initial UP034 findings and applies 246 fixes because nested cases become visible during rewriting. Full unchanged-configuration lint falls from 530 findings to 287, including zero UP034 findings. This is not a green full lint gate.

## Acceptance

- [x] Review exact six file hash pairs before application.
- [x] Verify location-independent AST, constants and comments remain equal.
- [x] Apply only the reviewed pairs; no rule waiver or unsafe fix.
- [x] Complete the six source-sensitive test files and inspect every failure: 192 passed, two original 60-second child timeouts, and two subtests passed in 724.07 seconds; zero errors/skips. Both timeout identifiers also fail in preserved f4dac584 results. The exact 183a full baseline was not run; no exact-base parity is claimed.
- [x] Verify all 665 frozen server/tools inputs after the terminal run: zero changed.
- [x] Independently review the final six hashes, all 665 frozen inputs and 17 curated evidence entries before publishing; accepted for a bounded draft change with both timeout and full-lint gates open.

AST equality does not establish compiled instruction/layout, tracing, generated class metadata, allocation behavior or runtime qualification. The source-sensitive suite remains required. Existing failures must remain explicit, with no deadline increase or deleted assertion used to make this change pass.

## Feature and architecture boundary

This cleanup concerns retained historical presentation/startup code. It neither enables an optimized rooted graph nor creates a prerequisite for the selected NS1–NS7 native presentation service. The full character and static-image feature remains the intended end state. Retirement of obsolete production files and exclusive tests is a separate proposal requiring complete entry/package closure and a security-responsibility/test disposition crosswalk. Shared authorization, privacy, lifecycle and plugin surface tests must survive.

No live host, device, provider, permission or release changes are included.

## Whitespace amendment after the first terminal run

The UP034 fixer leaves trailing spaces on formerly parenthesized blank lines, caught by `git diff --check`. A six-file trailing-space-only preview preserves line counts, comments, AST including locations, and compiled marshal bytes under the prepared Python 3.11 interpreter. Source fingerprints still change, so the prior 192/2 result is historical evidence for the initial six hashes, not qualification of amended bytes.

- [x] Independently review/apply the exact whitespace-only amendment.
- [x] Repeat source-sensitive tests on the intermediate whitespace fingerprints: 192 passed, two original timeout failures, two passing subtests; 752.018 seconds, zero errors/skips and all 665 inputs unchanged. This run is superseded by final formatted-byte evidence below.
- [x] Recheck pinned lint and whitespace on the final bytes: 287 remaining lint findings, zero UP034; six affected files pass pinned formatting; diff whitespace check passes.

## Final formatter amendment

The initial whitespace-only amendment also failed the pinned formatter check.
That missed check is preserved, and the terminal intermediate suite remains
historical evidence for its own hashes. Apply the independently reviewed six-file
formatter preview only after that run ends. Its AST ignoring locations and comment
tokens remain equal; compiled/tracing/source-location equivalence is not claimed.

- [x] Review/apply the exact formatter pairs; no guard/import/test/config waiver.
- [x] Verify lint/format and source-sensitive results on final bytes: 192 passed, two original 60-second timeout failures, two passing subtests in 754.62 seconds. All 665 frozen inputs remain unchanged; all 194 parent outcomes match the initial UP034 run. This selected-suite comparison is not a full CI, compiled/tracing or exact-183a-full-baseline parity claim.

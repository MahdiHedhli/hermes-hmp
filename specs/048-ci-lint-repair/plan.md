# Plan

Use a focused worktree based on public HMP070f2199, preserving the private deployed
composition and every other source author/worktree. The source CI and local pinned
ruff reproduce1,241 diagnostics in79 unchanged parent paths. A disposable preview
formats74 files (15 production/startup,57 tests,2 tools), changing no AST ignoring
source locations;5 files remain unchanged. Proper-root lint then reports530.

Apply only exact manifest-bound, AST-identical formatted copies after independent
plan review. Copy no configuration, raw evidence or dependency files into source.
The formatter is not `ruff check --fix`. Preserve all typed refusals, helper/import
bindings, literal scripts, original budgets and assertions.

Before a source claim, compare recursive compiled instruction/constant/name/flag
projections and account for source-location/NOP differences explicitly. Run existing
source-location/custody tests chosen with independent review, preserving a matching
base observation if a case fails or an observer no longer arms. Never remove an
assertion, disable an observer or lengthen a deadline to obtain green results.
Full native startup, allocation and runtime integration remain separate gates.

Remaining530 findings are a later stage of the same issue, not accepted debt or
an exclusion. Imports, tuple/local ownership bindings, exception behavior and
adversarial test names/exec need intent review before any semantic treatment.
No suppression or unsafe automatic fix is part of the layout stage. Full CI must
ultimately run all configured gates; current lint failure skips hosted unit tests.

CPython3.14 additionally emits executable class `__firstlineno__` metadata; its
value changes with layout. AST equality is not equality of that generated value
or all compiled constants. The3.14 preview records these differences rather
than treating the source as byte-identical.

## Source-sensitive observer repair

The initial formatted suite introduced four failures before the system under test:
the observer searched for `if ` and `_map(_type, names)` on the same source line.
Formatting separated those tokens. The repaired test resolves the exact enclosing
function by name and first line, finds the unique `_map(_type, names)` call by AST,
and verifies its line exists in `co_lines`. Nested scopes are excluded. The exact
code-object trace filter, mutations, expected refusals and call-count assertions
remain intact. This is an explicit test-only AST change, separate from the original
74 AST-identical formatter pairs; final source is not wholly AST-identical.

The repaired file passes 19 cases. Its four affected cases pass against unchanged
base and formatted source. Removing only the original value-identity guard in a
disposable package causes the intended value case to fail (one failure, no errors
or skips). The final six-file comparison finished with the same outcomes as baseline:
194 collected, 191 passed, the same three failed, plus two passing subtests.
All 665 frozen inputs remained unchanged; keyed XML outcomes have no deltas. The two original 60-second timeouts and foreign-root
observer failure remain unresolved; do not label them harmless or waive them.

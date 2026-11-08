# Original native file machinery — metadata only

The interpreter entry captures the originally observed POSIX C open, read, close,
stat, fstat and readlink objects, their canonical module ownership/name/module
metadata and os aliases, plus original flag values, stat-result type and observed
OS-error class aliases. Currentness rejoins the same operation, flag and class
allocations. Closed types and primitive fences precede metadata equality; no
foreign operation or getter is dispatched to check a replacement.

This capture performs no file operation, accepts no caller path/descriptor/error,
and mints no cache absence, permission refusal, IO receipt or source fallback.
The flag values are original observations, not independently attested kernel ABI
macros. The POSIX API shape is a prerequisite for this already POSIX startup path,
not a qualification of every platform/architecture or a new live feature gate.

A future fixed syscall/effect owner must invoke the held native functions, capture
actual native returns/raised outcomes before callbacks, preserve original partial
resources and byte counts, rejoin current authority, and prove known cleanup
before any permitted source fallback. CacheReadError/CacheProbeError cannot be
relabeled as cache misses. Inventory drift, unexpected appearance, ambiguous IO
or cleanup, stale authority and security-policy refusals remain refusals.

Neither native function identity nor an error class/errno proves that the kernel
was entered: audit hooks or native builtins can raise before kernel execution.
Freeze the exact accepted native-boundary semantics and remaining audit/ABI/
resource policy explicitly; do not claim syscall attestation from this metadata.
Source fallback still requires its independently authorized, freshly verified
source phase and the complete integration contract. No operational factory is
connected by this change.

Independent bounded read-only source review accepted this metadata-only scope.
Seventeen substitution/copy/foreign-metadata cases passed on current Python
and seventeen actual Python 3.11.15 children passed. Exact module/case/worktree/
interpreter/source receipt bindings were independently validated; source hashes
remained unchanged through branch reconciliation. Full Ruff, surface/privacy
and diff checks pass. The repaired configured startup regression passed as
recorded below; native/operational qualification remains pending. No live host/device/settings/grants/provider action occurred.

The combined source1ab9910 suite failed215 cases and passed1,065. Fixture alias
spies conflict with the new continuity checks; initial test-only migration passes
four normal paths and74 operator/link checks. The144-case residual run completed
with125 passes and19 failures, no skips/errors and unchanged source. The separate
reviewed refinement passed164 cases, including all19 prior failure IDs. The
integrated1a49174 candidate passed all1,280 configured startup checks on actual
Python3.14.9, zero failures/errors/skips, with source unchanged. These are source
results, not native outcome/ABI/runtime or image-delivery qualification. Actual
3.11 fixture migration remains under test. Production guards remain intact.

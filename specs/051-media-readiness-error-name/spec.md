# Media readiness exception naming

Pinned lint rejects the readiness projection exception name (N818). Give the class the standard `Error` suffix and retain the existing `MediaReadinessUnavailable` import as an alias of that same class. Keep the ValueError base, fixed error message, input validation, diagnostic projection and all route authorization/readback behavior unchanged.

The class introspection name changes to `MediaReadinessUnavailableError`; this is an internal naming migration, not a claim of cross-version object identity or compiled compatibility. The old import continues to catch the raised class. No diagnostic payload contains the class name and no new request/write or privilege is introduced.

Existing readiness tests exercise closed input vocabulary, feature/access diagnostics, unauthenticated/unauthorized routes and stale application-context handling: 51 pass, with two existing application-state deprecation warnings. Module lint/format pass; full lint remains blocked at286 findings. No tests, guards or lint rules are removed or relaxed. Full CI, installed host, physical/device and release qualification remain separate.

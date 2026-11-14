# Plan

1. Add `setup check` to HMP's existing CLI parser and dispatch.
2. Use the compatibility gate, `identity.resolve_custody`, `load_existing`
   with a read-only store epoch, the checked listener record, and the existing
   TLS-pinned liveness probe. No Hermes imports outside their existing
   allowed module and no subprocess.
3. Report only bounded status text and a pointer to the public deployment
   guide. Leave per-profile route verification to the host guide.
4. Test fresh, ready, stale, unsupported, and wrong-key states in isolated
   homes. Run lint, unit suite, plugin-surface, log, and zero-baseline privacy
   scans before pushing a public branch.

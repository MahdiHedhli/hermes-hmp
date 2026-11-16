# Preserve the frozen registry witness across permission-generation integration

## Exact scope

The original active-batch frozen-registry check expects SHA
b49e6e6205805f38144e769f742f6e3ee918536aa6dd5f66e6c8096d8f77c2b2.
This is exactly local_media_registry.py in e1d88b6f's parent. Current bytes are
exactly e1d88b6f62a99068e8bd5c69de5ca099f2afcfd6, SHA
f0b040c142945eead90befac8df40ffefff89239597ea4c4fb0c2ac9d5682f64.
That commit adds bounded primitive permission-generation tuples to callers and
bindings, validation and equality. This prevents old references surviving an
explicit deny/regrant. It does not authorize changing live permission settings.

Retain the original frozen hash. Add a test-only inverse for the three exact
committed context blocks before the existing cache-layout/R1 witness. Require
unique unchanged blocks; other bytes still reach the old hash. Test changed,
duplicate and relocated sites and unrelated mutations. Exercise real current
registry and permission-store/runtime tests separately. No production fallback,
permission-generation removal, grant, fetch, provider or host/device operation.

## Tasks

- [x] Reproduce the original isolated frozen-registry failure with JUnit.
- [x] Bind exact committed before/after bytes and recover the parent with three hunks.
- [x] Keep old hash/assertions, add projection causals and outside-byte controls.
- [ ] Complete active-batch, registry and current permission store/runtime suites.
- [ ] Independent review, focused publication and current-status synchronization.

## Limits

The projection is not standalone source/runtime validation. Owning current
permission tests, especially deny/regrant and late worker results, remain
necessary. No whole-suite, Linux/native/private/device/release qualification
transfers from these synthetic Darwin tests. The original broad run remains
untouched on its retained immutable source and process handle.

# Declared leaf metadata policy preparation

Uninstalled DATA-only source, November 8, 2026. This is a step toward the full
metadata walker integration, not a replacement for it or a feature acceptance.

The fixed `_declared_leaf_identity` helper preserves `_file`'s initial declared
runtime/cache regular-file identity rules: exact primitive snapshot identity;
regular file, root or actor uid, one link, exact declared byte size, no group/
other write or setuid/setgid bits. The declared size is an exact integer within
the existing `_MAX_FILE` bound. Booleans and coercible/foreign values do not
satisfy primitive guards. The helper returns the original full nine-field tuple.

The 23 synthetic tests cover zero/max size, root/current owner, wrong object
and primitive types, nonregular modes, permissions, ownership, link counts,
size drift and unbounded/coercible policy input. All23 passed on each supported interpreter, with unchanged source and rehashed
source/log/XML evidence; lint passes. No native provenance or dispatch qualification follows from them.

A future actual consumer must retain and bind the actual pending native return,
original declared expected row/size, canonical leaf component and original
opened parent/resource, consumer material/lifecycle and one-use phase. A
constructed snapshot or caller-selected expected size is not that proof.
It must retain the original timestamp conversion/range guard where source
hashing uses mtime, original hash/header/actual EOF checks, full leaf identity
checks before/after reading and final ancestor checks. Anchor/configuration
policies are distinct and must not adopt this helper as a silent substitute.

Do not wire this helper directly into a generic stat dispatcher. Integration
requires separately reviewed role-specific consumers, original result custody,
real ACK history and full plan progress at walker completion. Keep the current
zero-cursor guard until that migration is complete; never bypass it to make
an unwired candidate pass. Wrong actors, stale/revoked lifetimes, foreign
replacements, exceptions and ambiguous native entry retain original denial/
debt semantics, without refunds, retries or foreign writes.

Before integration: execute both-interpreter DATA tests, independently review
policy parity, finish actor-preflight causal qualification, implement actual
leaf/ancestor consumer and ACK roles, and verify the complete walker. Runtime,
service, physical device and release qualification remain separate.

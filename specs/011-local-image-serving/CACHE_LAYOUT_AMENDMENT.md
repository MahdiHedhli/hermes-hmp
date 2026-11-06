# Native generated-image cache layout amendment

Status: independently source-reviewed runtime and witness amendment. Native
cache-helper qualification remains pending; no live activation is claimed.

## Source-backed trigger

Native `ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df` changed the shared
`agent.image_gen_provider.save_b64_image` producer to
`cache/generated/images`. The xAI local-output path still calls that shared
producer and returns a `success_response` with an `image` string. HMP's existing
candidate and file leaf recognized only `cache/images`, so a current native
result was discarded before descriptor minting. A red test against the existing
`raw_tool_candidate` reproduced that refusal.

## Closed amendment to C1

Allow exactly two same-profile native cache layouts: legacy `cache/images` and
current `cache/generated/images`. Each retains exactly one bounded basename.
No arbitrary nested candidate, normalized path, sibling profile, legacy
`image_cache`, documents folder, URL or directory search is admitted.

- Keep the old legacy-only `derive_flat_name` helper and its guards. A separate
  inert lexical selector returns an exact internal CacheLayout member and name.
- The raw `image_generate` row digest already binds the full original result,
  including its cache namespace. No wire field, caller-supplied layout or new
  registry identity is needed. Re-read/digest validation precedes namespace
  selection on every fetch.
- The filesystem leaf accepts only the exact internal enum, selects one literal
  component tuple, and pins every directory with descriptor-relative no-follow
  opens. The added `generated` ancestor is revalidated just like every other
  ancestor. File regularity/link/count/raster/size and lifetime checks remain.
- Missing or refused selected layouts never try another root, even for identical
  basenames. The default leaf call remains legacy-only for existing callers.
- Existing ownership, bot authorization, feature flags, minimum-version/API
  eligibility, TTL, digest CAS, worker and memory limits remain unchanged.

## Required evidence

Positive legacy/current paths, cross-namespace duplicate basename isolation,
missing-current/no-legacy-fallback, raw-digest namespace binding, wrong enum/type
refusal before IO, foreign profiles/traversal/length/alias refusals, symlink and
ancestor replacement refusals, and a real authenticated route over both layouts.
Existing candidate/file/batch/descriptor/fetch and namespace-coherence guards must
continue passing.

Then exercise the pinned native base64 cache materializer and success-response
helper with fixed synthetic PNG bytes and an explicitly scoped scratch profile
home. Restore its ContextVar afterward; no provider generation, credentials,
URL download, user message, host grant, production activation or deployment.
This is cache-helper qualification, not a remote-provider generation claim.

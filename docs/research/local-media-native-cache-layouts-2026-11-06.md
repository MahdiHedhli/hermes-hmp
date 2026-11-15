# Current and legacy native image caches — 2026-11-06

The candidate now supports exactly two same-profile native cache layouts:
`cache/images` and `cache/generated/images`. Native `ed1afb08` uses the latter
through `agent.image_gen_provider.save_b64_image`. The previous HMP selector
recognized only the former and discarded a current native result before minting
its image descriptor. A red test against the existing candidate function
reproduced this gap before implementation.

## Implementation and security scope

A lexical selector returns an exact internal layout enum plus a flat bounded
basename. It does not resolve paths or consult the filesystem. The old legacy
helper retains its original behavior. The raw native tool-result digest includes
the complete image path and is validated before selecting the layout at fetch;
no client-selected layout, new wire field or weaker registry binding is added.

The file leaf chooses one literal component tuple and opens each directory
relative to its pinned parent with no-follow flags. The added `generated`
ancestor receives the same revalidation as every other directory. Identical
basenames cannot alias across layouts. Missing/refused current-layout files
never search legacy or other folders. Ownership, bot authorization, host flags,
minimum-version/API policy, TTL, digest CAS, raster/size and worker limits stay
unchanged. This is layout compatibility, not a version allowlist.

[The C1a amendment](../../specs/011-local-image-serving/CACHE_LAYOUT_AMENDMENT.md)
and runtime implementation were independently source-reviewed. Fifteen exact
inverse chunks preserve the original historical R1/AT1/S5 byte witnesses without
changing their hash constants. Mutated roots, selector calls and layout arguments
are not stripped. This witness amendment was also independently reviewed.

## Observed native cache-helper sample

One fresh Darwin sample completed at HMP
`d6c79d668e11a3b3cd9839afdddfbec7f92c2d43`, native
`ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`, Python 3.14.9 and aiohttp 3.14.5.
It fed fixed synthetic PNG bytes to the actual native base64 cache materializer
three times, under an explicit private profile ContextVar scope, restored each
scope token, and stored the native success-response dictionaries through real
SessionDB. The legacy control was explicitly fixture-written. The native helper
was imported only from the copied native `agent` tree; preloaded/foreign helper
modules refuse before qualification.

A distinct legacy shadow with each generated basename contained different valid
PNG bytes. Generated controls returned the expected original bytes, while the
legacy control also served. Foreign device/profile references, file replacement,
message removal, between-phase bot revocation and final device revocation checks
all completed under the existing two-phase contract.

- Three native cache materializations; home context restored; generated and legacy
  controls passed. No provider generated or downloaded an image. The legacy
  `actual_image_producer: false` classification remains alongside explicit
  `native_cache_materializer: true` and `provider_generation_executed: false`.
- 25/25 borrowed registry acquires/releases; original database closed, scoped
  sweep zero, listener closed and owned workers joined.
- Eleven recorded commands terminal: nine exit 0 and two expected absent-config
  exits; outer controller separately exit 0. No settlement-only path.
- 12,185 native and 370 HMP copied source-file hashes matched literal Git blobs
  and remained unchanged. All 28 top-level artifact hashes/sizes/0600 modes,
  runtime identity and matching marker/report/receipt were independently checked.
  The reviewer performed no test, native call or activation.
- Disclosed OS/runtime premises match the earlier
  [bounded sample](local-media-native-serving-sample-2026-11-06.md): 28 synthetic
  Darwin/Linux probe absences, three real own-descriptor listings, two bounded
  public OS-metadata reads and zero unexpected denials. These are not an OS
  sandbox or platform attestation; the final OS hash trusts OS-root immutability
  for earlier consistency.

The private proof is `hermes-current-native-cache-materializer-proof-20261106.json`.
Earlier legacy-only source and failures remain separately preserved.

## Verification and remaining limits

Sixteen focused causal checks cover both layouts, raw-digest namespace binding,
wrong enum/type before IO, no fallback, directory symlink/replacement refusal,
and moving an already-minted row between namespaces before file IO. The observer
has a positive file-open control, so this refusal is not vacuous.

A separate 800-case candidate/file/batch/descriptor/fetch/layout regression passed
on Python 3.14.9/aiohttp 3.14.5 in 26.92 seconds. The first broader run found seven
historical source-witness mismatches; the exact reviewed inverse repairs them
while retaining old mutation checks. Those failures remain recorded, not relabeled
as a pass.

This qualifies the selected native cache-helper/storage/route path with synthetic
transport/owner/bot authority and compatibility. It does not qualify full provider
or tool generation, deferred/Desktop production scope, cost/T12, Linux, complete
plugin-PM dependency union, phone display, activation or release. No live grant,
flag, provider/model setting, app or host deployment changed. The app binary image
protocol is unchanged; device rendering still needs separate acceptance.

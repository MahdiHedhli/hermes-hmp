# Exact native image_cache compatibility amendment

Status: independently accepted bounded source implementation; focused synthetic
qualification passes. Full native/platform/private/physical qualification remains open. No live cache or phone
is read and no host activation, grant, provider or default changes are included.

## Source and scope

Native ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df hermes_constants.get_hermes_dir
honors a populated profile image_cache directory. gateway.platforms.base passes
cache/images and image_cache to that resolver for get_image_cache_dir. Current
HMP candidate/file leaves explicitly reject that same-profile historic spelling.
The four affected surrounding production inputs equal public183a1189 and private
e985a03f bytes. This is a source compatibility gap, not a claim about the cause of
the owner's earlier cache/images screenshot or a new provider-generation result.

Amend C1 only to admit exact home/image_cache/flat-name as a third internal layout
HISTORIC_IMAGE_CACHE. Existing LEGACY continues to mean cache/images; GENERATED
continues to mean cache/generated/images. Do not rename either old enum value or
change old defaults, wire shapes, handles or client behavior.

## Contract and implementation plan

1. Lexically select only a strict same-profile native image_generate row's exact
   image spelling after existing bounded parsing. Never call the native directory
   resolver, normalize a path or search any cache. Assistant MEDIA text is not
   file authority. Keep the complete raw-result digest binding.
2. Select the literal single-component tuple (image_cache,) from the exact new
   enum. Reuse the original descriptor-relative no-follow directory/file opens,
   file/link/size checks, bounded reads, revalidation and cleanup unchanged.
3. No fallback in either direction: a missing/refused historic file cannot read
   an equal basename from modern/generated caches, and vice versa. Namespace
   changes after mint must refuse through the existing raw-digest check before IO.
4. Preserve current original-operation workers/deadlines/byte budgets, native
   per-bot/device/token-family authority, owner gate, revocation, TTL and raster
   checks. The new path is shorter; it does not increase descriptor-depth bounds.
5. Native path overrides, arbitrary ancestors/nesting, documents/other caches,
   sibling profiles, symlinks/hardlinks and migration remain outside this change.

## Acceptance/checklist

- First demonstrate the positive historic native-row candidate fails on unchanged
  source, then passes with the complete guard chain intact.
- Exercise all three equal-basename namespaces, no-fallback both directions,
  malformed/foreign paths, wrong enum/type, symlink/file/hardlink and ancestor/file
  replacement races. Retain opened/closed descriptor accounting.
- Exercise authenticated descriptor mint/fetch and namespace mutation refusal using
  synthetic media only; unrelated profile/device/bot rights remain refused.
- Run existing candidate/file/layout/fetch tests, causal omission checks, privacy/
  log/plugin-surface checks and focused independent source review before publishing.
- Keep actual native/Linux fixture, private-union composition, physical iOS/Android,
  generated-media and release qualification separate. No installed build or runtime
  availability is implied by source tests.


## Observed evidence and limits

The unchanged-source regression first refused the historic native-row candidate.
After implementation,422 focused cases pass across layout, candidate, filesystem
and authenticated fetch suites. Isolated removal of ancestor no-follow causes one
new historic-layout case to fail; removal of final binding revalidation causes
two replacement-race cases to fail, with zero errors. Original source hashes
remain unchanged during these disposable-copy experiments.

Historical source witnesses first refused the new delta; an explicit test-only
literal inverse now removes exactly this amendment before the existing two-root
inverse and original witnesses run. Independent review recovered both original
183a production files byte-for-byte. Unreviewed root mutations cannot be stripped.
This proves preservation of those old source witnesses, not new allocation/runtime
funding or transfer of native/Linux qualification to changed code.

The expanded913-case selection has912 passes and one pre-existing registry source
witness mismatch. The unchanged183a baseline reproduces the same case, and the
registry file is byte-identical. Its old expected b49e6e62 hash differs from current
f0b040c1 after the earlier permission-generation source addition e1d88b6f. No hash
was waived or test skipped. Full-suite acceptance remains open pending separate
reconciliation of that prior delta. Native/helper generation, actual Linux,
private-host composition and signed-phone/release behavior remain unqualified.

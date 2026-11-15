# Pinned HMP executable-package snapshot

Status: bounded source component accepted. This completes the HMP package
snapshot prerequisite only. It does not complete the gateway runtime inventory,
dependency/loader validation, trusted entry, native/key factory or image delivery.

## Selection and scope

`GatewayPackageOwner.verify` requires the actual retained StartupSelectionOwner,
its original rooted loaded-selection fact and current early activation. A copied
GatewayStartupSelection value is not sufficient. The raw manifest is bounded to
8MiB and must hash to that retained selection's gateway_inventory_sha256 before
parsing. This component currently accepts a package-scoped manifest; the full
factory must still join an independently approved complete gateway recipe and
runtime/dependency/loader coverage. It must never treat this package result as
the entire gateway inventory or as approval of caller-built expectations.

Schema1 uses exactly kind=HMP_GATEWAY_PACKAGE, generation, package and entries.
Generation matches the retained credential generation. Package equals this HMP
module's actual installation directory, separate from the private configuration
directory. The selected private file's trust/approval and actual trusted entry
execution remain separate obligations. No candidate-generation helper approves
its own output, and the synthetic_no_go broker verifier is not promoted.

Native Hermes is a different boundary: retain trusted PM startup/activation and
actual module origins, minimum supported version and required APIs. Do not pin a
whole native checkout against an HMP-tested source digest or inspect its .git,
profiles, .env, credentials, logs or unrelated documents. The native commit is a
diagnostic. HMP-specific Python/crypto/native-extension artifacts and loader roots
still need their own explicitly reviewed coverage/link policy.

## Complete package table and owned traversal

Entries are strictly sorted, unique relative paths with exact keys path/kind/size/
sha256. Every parent directory must be declared before its children. Directories
have integer size0 and null hash; files have bounded exact sizes and lowercase
SHA-256. Paths have bounded depth/length, no absolute/dot/empty components, and
known private data names are refused. Only regular files/directories are allowed;
symlink, device, pipe or socket entries refuse. Bounds include20,000 entries,
1,024 files,128MiB per file and2GiB total through the shared file verifier.

The entry must use -B; caches created during verification are not silently added
to an approved inventory. Any installed pyc/archive/resource files must appear
explicitly in the selected table. No package directory, cache or importable file
is silently excluded. This policy concerns the selected installed HMP package,
not a recursive scan of the native checkout or home directory.

The first descriptor-rooted traversal must match the entire table before any file
body is hashed. Every declared file, including unused code, then passes actual
owned no-follow reads, exact size/EOF/hash, mode/owner/single-link and stable metadata
checks. A second traversal rejoins names/types, original directory/ancestor
identities and each file's stable dev/inode/mode/owner/link/size/mtime/ctime from
the actual hash receipt. Access time and incidental directory timestamps are not
identity. Same-name replacement after hashing refuses even with identical bytes.

Scandir acquisition intent is retained before construction; iterator close intent
is recorded before its one close attempt. Native descriptor/iterator cleanup uses
original process/thread/activation custody after retirement. Ambiguous acquisition,
iteration or close stays attributable/unknown and cannot mint completion. Known
original descriptors retain the reviewed post-open failure cleanup behavior.
This is a bounded filesystem observation, not atomic filesystem snapshotting,
hostile-admin containment or native loader/execution attestation.

## Loaded HMP-origin consistency

Already-loaded modules in this HMP namespace must refer to verified package files.
File/spec-origin strings, module/spec/loader objects and package search-path
references are resealed by identity after currentness callbacks. Comparisons do
not invoke ModuleSpec/custom-loader equality. A fixed empty namespace container
is permitted, but not an arbitrary originless HMP submodule. This is origin
consistency DATA, not approval of a custom loader or future arbitrary imports.
Further imports and dependency/native-extension/OS-loader roots require the
remaining full factory/admission contract before keys or publication authority.

## Verification and limits

19 private synthetic-tree cases plus30 configuration,18 file-I/O,25 activation
and311 layout/import cases passed:403 in6.79s, source unchanged during the run.
Independent read-only review accepted the stable file/root metadata repair;
lint, surface and whitespace checks pass. Reviewer performed no runtime actions.

Cases cover selected digest/schema/generation/root errors, changed and unused
code, missing/unlisted/private files, links and mode errors, actual scanner
retirement, changed module/spec/namespace origins and replacement of an already
hashed unused file with same-name/type/identical bytes. The latter now fails via
the original metadata receipt. Scans/reads cover only private synthetic package
copies; no native checkout, real profile, credentials, keys or host was accessed.
Actual installed-runtime, Linux/Darwin loader/manager and physical/release
qualification remain open, as do the earlier unexplained broker regression cases.

## Historical handoff after native startup

`retained_data()` returns only the originally verified immutable data after native
startup or namespace eviction; it does not repeat file/import/path selection or
relax fresh-load guards. Original owner/scope/fact cells and known-closed custody
are checked before and after actual process/user/thread sampling. Context or fact
replacement refuses without overwriting newer state; wrong-thread reads refuse
without retiring the original snapshot. Package projections retain original raw
manifest, entries, primitive file observations/metadata and origin strings, never
mutable module/spec/loader objects. These historical observations are not current
runtime admission, operator approval, native authority or permission to load keys.
The fixed startup factory must independently establish those remaining joins.

Verification:36 configuration and26 package cases, plus18 artifact,25 activation
and311 import/layout checks:416 passed in8.20s with source hashes unchanged. Cases
cover late startup, namespace eviction, path changes, wrong thread, root fact drift
and drift during context sampling; package publication also preserves a foreign
pre-publication fact. This is isolated source qualification, not installed runtime
or physical device/image-display qualification.

## Schema2 original recipe integration

GatewayPackageOwner.verify_recipe accepts the actual retained GatewayRecipeOwner.
It derives the configuration and plugin expected/raw objects from that owner's
original immutable document fact; no replacement raw argument or optional expected
digest is exposed. Fresh original recipe bindings are checked across callbacks.
The old verify(configuration, raw) still accepts schema1 only. A tuple copied from
the recipe fact is DATA and cannot substitute for its owner or root allocation.

The private verifier retains the actual recipe scope/plan/fact and original
document-count cell in its metadata. Its byte counter starts from that allocation's
known count, then actual file reads advance it. Combined file/byte limits apply to
the five recipe documents plus this plugin package. This is not total startup
accounting: earlier private selection IO and later entry/dependency/interpreter
artifacts still require their original typed handoffs in the complete factory.

The actual final package count cell is frozen immediately after hashing and
rejoined after final tree/origin callbacks, checked against inherited document
count plus actual verified file lengths, and retained in the package fact. The
shared file reader also rejoins its actual count allocation after its guard; the
recipe document reader holds it through extra hash/JSON and publication callbacks.
Equal-valued replacement refuses; no synthesized count, reset or replay is admitted.

Historical accessors use pure original recipe/configuration/closed-custody joins,
with no new module lookup, file read or PM selection. Occupied package acquisition
refuses before fresh callbacks, preserving original data after gateway/path drift.
This remains historical DATA, not admission of current modules or native authority.

14 composed cases plus42 recipe and prior coverage:534 passed in16.45s with source/
fixtures unchanged. Cases cover actual fixed private documents, full plugin tree/
hash verification, wrong/copied source, count drift/substitution, missing/unlisted/
changed code, later namespace/path changes and wrong thread. Other three recipe
children deliberately remain minimal envelopes in this fixture; their executable
tables and all broader runtime/key/physical qualification remain unimplemented.
Independent source review accepted the bounded integration and count repairs.

Original plugin hash/count facts now feed the [entry/wrapper snapshot](ENTRY_FILE_SNAPSHOT.md)
through typed retain_from_package, with combined limits (569 combined checks).
This does not complete remaining startup accounting, runtime or native/key admission.

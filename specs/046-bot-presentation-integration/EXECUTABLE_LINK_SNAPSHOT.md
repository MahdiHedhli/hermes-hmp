# Selected executable leaf-link snapshot

Status: L1 explicit recipe documents and L2 immutable link-plan retention are
source implemented/reviewed. L3 original-owner link/target IO remains unfinished.
Full desktop character delivery remains required; no upstream blocker is established.
No route, key loading, host change or production admission follows this document.

## Need and version choice

Read-only metadata in an isolated candidate fixture environment shows its Python
entry is a single leaf symlink to a regular Python binary. This is not the actual
activated native PM generation or execution proof. The regular-file D1 snapshot
correctly refuses it; silently following the link would weaken custody.

Keep `GatewayRecipeOwner.load` fixed to complete recipe schema1 and interpreter
child schema1. The distinct `load_executable_links` selects recipe schema2 BEFORE
IO and retains that exact integer in its original immutable `_Recipe` inputs.
The complete envelope remains HMP_GATEWAY_RECIPE with the same closed four size/
SHA references, bounds and fixed filenames. Only interpreter advances to schema2;
plugin, entry and dependencies remain schema1. Both versions require the same
independently pinned schema2 private selection and original descriptor/count owner.
No body-driven version detection, automatic migration, fallback or retry.

D1 `retain_runtime_files` refuses recipe2 before retaining an entry-file owner or
acquiring an artifact owner. The explicit `retain_runtime_link_files` path
consumes recipe2/interpreter2 only and retains a plan, never completed custody.
Completion refuses before artifact acquisition and permanently fails that owner;
L3 must use a fresh startup allocation, not resume/upgrade a refused owner. Legacy entry-only DATA remains explicitly
entry-only; it is never substituted for either runtime variant or admission.

## L2 closed interpreter2 plan (source implemented/reviewed)

Retain existing interpreter1 field names/semantics with schema2 and exactly one
additional `executable_link` member. Its closed shape is:

- hops: ordered list of1..8 exact {path, target, destination} rows.
- final: exact {path, size, sha256, uid, mode} object.

The first hop path equals the original captured InterpreterStartupData executable.
Every subsequent path equals the preceding canonical destination; final.path equals
last destination. All selected paths/destinations use D1's canonical absolute path,
length/depth, private-component and forbidden native/configuration-root rules.
Reject cycles, duplicate hop paths, missing/extra hops and a terminal target that is
another symlink. Hardlinks and symlinked ancestors stay refused.

Each target is exact UTF-8 link text,1..4096 bytes, without NUL/control characters.
Absolute or relative text is permitted, but relative text is joined to the selected
hop parent and normalized LEXICALLY; it must equal the independently selected
canonical destination. No resolve(), automatic discovery or followed-path proof.
Raw target components also reject private names, empty components and dot
cancellation. Relative targets may have bounded leading `../` components only;
later `.`/`..` cancellation is refused, and leading parent count cannot exceed
the selected parent's depth. Absolute targets permit no dot cancellation.
This avoids lexical removal of an intermediate private or symlink component.
L3 must still no-follow-walk all actual hop/target parent ancestry: lexical
equality does not establish safe filesystem traversal. Hop paths are loose and
disjoint from all declared package trees and regular artifact declarations;
no package-tree scan exception is introduced.

Final size/SHA obey existing regular-file limits. uid is an exact nonnegative int
permitted by the original startup ownership policy (root or retained startup UID).
mode is exact permission bits0..0777, with at least one execute bit and no
group/other write; existing no-setid,
regular-file and single-link checks remain unchanged. Actual uid/mode must match.
The original executable is admitted through exactly one variant: regular D1 row
or the explicit link chain. Every terminal target must also have its exact regular
file declaration, even when outside stdlib; no undeclared inferred target read.

Full path/size/SHA deduplication retains the separate link-target UID/mode constraint
and original declaration references. Ordinary rows cannot erase stricter target
constraints. Conflicting pins refuse before IO; shared target bytes are hashed once.

## L3 original IO composition (pending)

Retain the link plan/partial owner and descriptor records before effects. Walk each
parent descriptor-relative with the same strict ownership/no-follow checks. Observe
leaf symlinks using no-follow metadata and bounded readlink; never open a symlink
as a regular file or follow an ancestor link. The target is opened/hashed by the
SAME original StartupArtifactOwner that owns the combined plan and inherited counts.
No new artifact allowance, package recapture or completed-owner extension.

Observe the selected link text, leaf inode/metadata and parent relationships before
AND after target hashing, then rejoin the final target receipt/metadata and original
entry/recipe/activation/plan allocations before publication. Both actual readlink
byte counts belong to that same original cumulative allocation, distinct from file
hash bytes. Preflight budgets include twice the selected text size; completion uses
actual observed counts. Include hop declarations in the1024-artifact bound and all
prior selection/recipe/plugin IO; no subtraction or fabricated read credit.

Partial/unknown readlink/open/close outcome latches failure and preserves owned local
cleanup debt. No recapture/retry or cleanup of foreign replacement state. Return
only typed original link-to-target snapshot DATA beside the regular-file receipt.
It proves neither executed image nor OS-loader containment, PM lease, future-import
closure, native/key factory, broker ACK/release or physical image delivery.

## Required acceptance

- Actual temporary absolute/relative/multi-hop executable symlinks through the
  strict combined path, same original IO and shared-target hash deduplication.
- Link/target replacement after hashing, same-byte new inode, wrong selected text,
  cycles/extra hops, symlinked ancestors, private targets and UID/mode conflicts.
- Exact aggregate boundaries including both readlink observations and prior IO;
  partial readlink/open/close, copied original allocations and sticky no-replay.
- Independent review, Python floor/current source-bound checks, affected startup
  regressions, and separately installed runtime and physical qualification.

## L1 source checkpoint

The earlier L1 checkpoint reads canonical recipe2/interpreter2 documents under the
original private IO lifecycle. L1 alone does not decode executable_link, inspect a
symlink or hash its target. Tests cover old/new loader confusion, wrong child/version/
generation, bool/unknown schemas, no recapture and D1 refusal before artifact IO.

Final L1 verification:641 affected startup checks pass with source hashes unchanged,
plus9 actual Python3.11 child fixtures in a separate driver (not the full plugin
suite). Independent bounded source review accepted the version split. Ruff,
closed plugin surface and privacy scans pass. These counts do not qualify links.

## L2 source checkpoint

The new retained runtime plan derives exact interpreter2 link declarations from
the original recipe/entry/plugin bindings. Its target points to the canonical
regular-file row; stricter UID/mode constraints stay in the same immutable plan.
Budget checks reserve both text observations against the original actual plugin
count and pending regular rows, including hop declarations in the file limit.
These are preflight reservations, not measured readlink/hash credit.

Temporary absolute/relative/leading-parent/multi-hop symlink fixtures exercise
planning only. Completion explicitly refuses before artifact ownership/IO and
permanently fails the plan owner; no link metadata or final target hash is
published by this source slice. L3 and installed/native/physical acceptance remain
required. Unknown plans cannot fall back to D1 or an entry-only result.

Final L2 verification:680 affected startup checks pass with source unchanged.48
actual Python3.11 child checks cover9 recipe/refusal and39 link-plan cases; this
is not the full3.11 suite. Independent review accepted the raw-path/immutable-
plan boundaries. Ruff, plugin-surface, privacy and test-log scans pass.

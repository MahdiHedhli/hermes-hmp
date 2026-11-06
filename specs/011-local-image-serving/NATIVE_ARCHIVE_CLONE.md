# Optional native source archive clone: source-review candidate

This fixture-only storage optimization does not change native execution,
authority, phase coverage or the original 12-second process refusal policy.
One fresh tiny synthetic clone completed and passed independent artifact review.
The optional driver integration below is implemented but awaits separate source
review before use.

The local macOS `cp(1)` manual explicitly allows `cp -c` to fall back to an
ordinary copy. Therefore it cannot establish the intended no-fallback storage
property. The local `clonefile(2)` manual documents `fclonefileat` with a retained
source FD and target-directory FD; a pre-existing target fails, and successful
clones have independent attributes and copy-on-write data blocks. Directory
clones are discouraged and are not used. Later writes can still fail ENOSPC;
cloning does not replace capacity admission or establish a disk reservation.

`local_media_native_archive_clone.py` is inert on import. Darwin-only explicit
calls accept one canonical private source archive plus an expected SHA-256 and
an absent `native.tar` under a canonical owned 0700 directory. The retained
source FD must be regular, owned, 0600, single-link and at most 160 MiB. Hash and
size are verified before effects. Descriptor-based `flistxattr` bounds the
attribute-name list at 128 bytes before allocation, requires exact returned
length and complete NUL-terminated unique nonempty ASCII names, and permits only
an empty list or singleton `com.apple.provenance`. Its value stays unread/opaque
and is never authority. Quarantine, resource forks, unknown names, malformed
encoding and query errors refuse. This Python runtime has no `os.listxattr`, so
the documented Darwin FD API is explicit rather than silently skipping guards.

The source FD and target-directory FD stay owned through `fclonefileat` and
postconditions. The current SDK defines NOOWNERCOPY=2 and NOFOLLOW_ANY=8;
only the single fixed basename is passed relative to the pinned directory.
There is no shell/subprocess, directory clone, ordinary-copy fallback, retry,
delete, network or service operation. Any failure leaves uncertain output under
its original owned parent for review. Existing targets are never overwritten.

A destination FD is opened without following links. It must be a distinct inode
on the same device, owned regular 0600/single-link, with exact expected size/hash
and the exact sealed source attribute-name set. Source names are rechecked after
hashing before clone, and source/target names plus stat snapshots are rechecked
through final verification. No claim is made about unread attribute-value bytes. FDs close in reverse order on success/failure.
The caller must still perform normal bounded extraction, literal Git/mode
inventory checks and native source/runtime report binding; a cache path/hash
alone never authorizes executing archive contents.

Root's 31 fake-backend model/query cases and configured lint passed. They create tiny
synthetic files but load no native library and perform no real clone. Independent
source/security review accepted the primitive for a bounded synthetic probe.
Probe artifact review and separate driver integration review remain required
before any native workload use. No storage savings,
platform qualification, archive-cache integration or release pass is claimed.

## Preserved first tiny-probe refusal

The first real probe at `9d57d72` used one new 8 KiB synthetic file and refused
before cloning: the strict zero-attribute guard encountered the OS-provided
`com.apple.provenance` name. The destination was absent and the refusal is
preserved. No attribute was removed, no output promoted and no clone pass claimed.
Independent design review accepted the bounded name-only refinement because this
non-executable archive's data fork alone is consumed by extraction/literal Git
checks. The concrete refinement still requires review before a new tiny probe;
driver integration and native workload use remain unaccepted.

## Fresh opaque-provenance probe

A fresh 8 KiB synthetic file probe at `d7244dc` completed terminal 0 through the
reviewed `fclonefileat` path. Source and destination data-fork hashes/lengths
matched; destination had its own inode, with owned 0600 single-link properties,
and the allowed provenance name was present. Its opaque value was not read.
No ordinary-copy fallback, metadata removal, existing-target overwrite, actual
archive extraction or native Hermes workload occurred. The first strict-guard
refusal remains preserved. Independent artifact review accepted the exact tiny source/artifact bindings. This is not
measured physical-space savings, driver qualification or a release claim.

## Optional driver integration candidate

`run_fixture(native_archive_cache=(canonical_path, exact_sha256))` is explicit
and Darwin-only; malformed cache options refuse before owned filesystem effects.
The default path still creates a fresh native Git archive. Cached mode clones
only `native.tar`; HMP archives remain fresh. Git commit type, custom tar-command
refusal, literal Git tree/mode inventory, bounded archive parsing/extraction and
copied-source hashing remain mandatory. A cache hash/path alone never authorizes
native execution. Wrong archive header commits and wrong content/blob identities
refuse before the native entry.

The receipt records the expected cache digest and clone-helper source hash,
then attempted state before the clone syscall. A clone refusal stops without
falling back to Git archive. The copied HMP clone helper must match the loaded
source hash before native execution. On successful workload completion, the
archive digest and helper hash are checked again before completion publication.
No archive or source evidence is deleted; source/worker lifetime and original
12-second refusal remain unchanged.

Root's 679 combined fixture/model guards and configured lint passed, including
cached/default paths, malformed options, clone refusal, wrong commit/blob,
helper mismatch and post-workload archive drift. These models execute no clone,
Git or native workload. Independent integration source review is pending. No
retained real archive or Hermes workload has used this optional path yet.

## Cached single-phase lineage sample — November 6, 2026

A fresh native sample at `0397803` used the reviewed optional archive-clone path
and independently checked Git/archive/source identities before executing one
largest-shape Bot ordinary-child phase (98 sessions, full prompts, 128 selectors).
It completed under the unchanged process limit: `tip_changed` first, then fresh
`not_eligible`, two public native mutation calls, 39/39 borrows and closed
DB/listener/workers. All ten commands had known outcomes; no expiry/settlement,
ordinary-copy fallback or metadata removal occurred. Independent artifact review
is pending. This is one phase, not a full matrix or a measured storage bound.

The original matrix at `21937dc` remains stopped after 174 completed pairs and
one refused pair; 209 pairs never started. Reusing its verified source archive
neither reruns nor rehabilitates the refused workload. Broader single-phase
partition/remaining execution and independent evidence review remain open.

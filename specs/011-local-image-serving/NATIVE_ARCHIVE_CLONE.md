# Optional native source archive clone: source-review candidate

This fixture-only storage optimization does not change native execution,
authority, phase coverage or the original 12-second process refusal policy.
It is not wired into the serving driver and has not executed a native clone.

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
source/security review and a bounded synthetic real-clone probe are required
before driver integration or any native workload use. No storage savings,
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

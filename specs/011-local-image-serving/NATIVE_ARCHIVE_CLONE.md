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
size are verified before effects. Descriptor-based `flistxattr` reads only the
attribute-list byte count; nonempty attributes and errors refuse. Names/values
are not retrieved. This Python runtime has no `os.listxattr`, so the documented
Darwin FD API is explicit rather than silently skipping that guard.

The source FD and target-directory FD stay owned through `fclonefileat` and
postconditions. The current SDK defines NOOWNERCOPY=2 and NOFOLLOW_ANY=8;
only the single fixed basename is passed relative to the pinned directory.
There is no shell/subprocess, directory clone, ordinary-copy fallback, retry,
delete, network or service operation. Any failure leaves uncertain output under
its original owned parent for review. Existing targets are never overwritten.

A destination FD is opened without following links. It must be a distinct inode
on the same device, owned regular 0600/single-link, with exact expected size/hash
and no extended attributes. Source and destination stat snapshots remain stable
through final verification. FDs close in reverse order on success/failure.
The caller must still perform normal bounded extraction, literal Git/mode
inventory checks and native source/runtime report binding; a cache path/hash
alone never authorizes executing archive contents.

Root's 13 fake-backend model cases and configured lint passed. They create tiny
synthetic files but load no native library and perform no real clone. Independent
source/security review and a bounded synthetic real-clone probe are required
before driver integration or any native workload use. No storage savings,
platform qualification, archive-cache integration or release pass is claimed.

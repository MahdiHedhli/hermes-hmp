# Host-local media file leaf: bounded Linux evidence

Root accepted this **file-leaf-only** platform check on 2026-10-01. It does not qualify an
HMP serving route, native Hermes bridge, process manifest, raster decoder or phone build.

## Source identity and verification

| Input | SHA-256 |
|---|---|
| `server/hmp_plugin/local_media_file_safety.py` | `440c3cfa5c636d5d280f4cf8876f900ab9177b0421d55a8d5503fc398973ef74` |
| `server/tests/unit/test_local_media_file_safety.py` | `eda3d765eb383b28504a771b6b231dfbf3be9b6ad987ad2a91931ae09aa7f59b` |
| Private supplementary real-OS harness | `edde4ae7345d7ec6075471b31ad4c11aa8c71859815abb946ab2ac3e86ea85c6` |

An economical worker ran the byte-identical accepted test file and a supplemental harness.
Root independently reviewed the harness and reran both through a separate isolated runner:
**89 accepted tests passed, no skips; 91 supplemental checks passed**. Source hashes matched
before and after. Root's final run created no bytecode and removed its own scratch directory.
Private receipts retain the counts, outcomes and runner details; no live gateway, bot, grant,
job or Hermes configuration was changed. No dependencies were installed.

The check used CPython 3.14.7, a non-root process, Omarchy Linux x86-64 and a tmpfs scratch
filesystem. Home, Hermes home, XDG directories, working directory and test temporary directories
were isolated. The package initializer was empty; the installed Hermes/plugin was not imported.
The accepted socket test creates and removes its own additional temporary directory. Network
blocking was not enforced; the tests use only local Unix sockets and SSH for transfer.

## Real kernel behavior

- `O_DIRECTORY`, `O_NOFOLLOW`, `O_CLOEXEC`, `O_NONBLOCK` and descriptor-relative operations were
  available. File symlinks returned `ELOOP`; a directory symlink or regular file under directory
  flags returned `ENOTDIR`. Both mapped to the existing closed refusal rules.
- Missing files returned `ENOENT`; denied file/home/cache/images permissions returned `EACCES`.
  Positive controls after restoring permissions distinguished denial from absence.
- A Unix socket returned `ENXIO` on the file open. A FIFO opened nonblocking, then failed the
  regular-file check without reading or hanging; a plain blocking open was the causal control.
- Existing and newly added hardlinks, file/directory replacement, symlink swaps, growth,
  truncation and same-inode rewrites refused at the appropriate existing checks.
- Oversize files refused before reading; an exact-size positive control read its bytes.
  Descriptor counts returned to their starting value.

## Limits and retained evidence quality notes

This does not cover non-tmpfs filesystems, other kernels/distros, device-node files, free-threaded
Python, real-kernel `EIO`/`EMFILE` injection, native database materialization or serving requests.
The project pytest configuration was bypassed for this standalone leaf check. The accepted
monkeypatch cases still cover some faults that were not induced in the kernel.

Early supplementary runs corrected the harness's self-observing read counter; final causal
controls measured a known read exactly and an idle operation as zero. Root used its own runner
rather than the worker's retained transfer wrapper. Root's first run passed all checks but made
two bytecode files inside its disposable tree through a test subprocess; its final run explicitly
inherited the no-bytecode setting and passed with none. These were harness hygiene corrections,
not leaf source changes. All prior private receipts remain retained.

The Linux file-leaf task is accepted for this scope. Native serving, C6 mint cost, T12 memory,
process qualification, device acceptance and release gates remain open.

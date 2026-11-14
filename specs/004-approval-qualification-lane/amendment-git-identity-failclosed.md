# Amendment: a present `.git` never reads as "no git" (fail-closed build identity)

Status: bug fix, runtime file `server/hmp_plugin/compat.py`. Grants no new admission; no shipped
manifest or allowlist entry changes, and there is no environment bypass.

## Resolved bug

`resolve_git_head_sha` decided "no git metadata" with `(root / ".git").exists()`, which follows
symlinks. A dangling `.git` symlink therefore looked absent, and `GitFingerprintReader` returned a
fingerprint-only identity. That is the identity of a genuine git-less archive, so a manifest entry
without `git_sha` could qualify a build whose git metadata was present but broken (research R8
step 5: present-but-unresolvable must be unidentifiable).

## Rule

- "No git" means `lstat(<root>/.git)` raises `FileNotFoundError` (ENOENT) for `.git` itself.
  Nothing else does: a dangling link, a permission error, ENOTDIR or any other `OSError` propagates,
  and the reader returns `None` (unidentifiable).
- A present `.git` that is a malformed `gitdir:` pointer, points at a missing directory, or has an
  unresolvable `HEAD` or ref still raises `ValueError` as before.
- Unchanged and still supported: normal clones, `gitdir:` pointer files, linked worktrees with
  `commondir`, a `.git` symlink to a valid directory, detached, symbolic and packed-ref `HEAD`.
  No ref-parser change. Still no subprocess and no Hermes import.

## Evidence

`server/tests/unit/test_compat.py`: dangling `.git` link (nonexistent file and directory targets),
mocked `PermissionError` on `.git`, malformed pointer, valid symlinked `.git`, genuine git-less
archive unchanged, and a real reader over a fixture whose manifest lists the exact archive
fingerprint returning `None` once `.git` dangles. Five of these fail on the pre-fix code.

## Remaining limits

- `lstat` reports presence, not integrity. A `.git` directory with a valid `HEAD` is trusted as
  identity; objects are not verified, and the SHA is read, not checked against the object store.
- Reads are not atomic with later use (TOCTOU between identity read and route use is covered only
  by the existing re-read and latch checks, not by this change).
- A deliberately stripped `.git` (truly absent) is indistinguishable from a release archive by
  design; it is identified by fingerprint alone. Release archives must ship without `.git`.
- Only `.git` itself is checked: a world-writable tree, or an attacker who can edit bridge files,
  is outside this fix.

## Verification

- Root full run: 1501 passed, 13 existing skips, 1 existing aiohttp warning.
- Root focused run: 152 passed, 6 existing skips. Old pytest garbage-cleanup warnings are unrelated.
- Pinned Ruff, surface and privacy checks are clean.
- Focused Opus review cleared the bounded fix.

## Review note (low, not resolved)

`Path.resolve` on a symlink loop raises `RuntimeError` under supported Python 3.11/3.12. Approval and
compat callers catch it and fail closed; the direct-send path may raise. There is no bypass. This is
an existing availability-only limitation outside this fix and is not resolved here.

## Pending

Two test nits from the focused review are applied after the runs above (the inaccessible-metadata
test now writes a valid `HEAD` before the patched `lstat`, so the read is caught independently;
the dangling-link test asserts the manifest matches the identity before `.git` dangles). Runtime
is unchanged. A root focused rerun is awaited.

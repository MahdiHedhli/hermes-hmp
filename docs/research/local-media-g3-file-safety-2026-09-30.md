# Local generated media: G3 filesystem safety prototype (2026-09-30)

Research evidence for root review. Not a design, wire shape, qualification, public API or product
change. It adds one leaf, `tools/research/local_media_file_safety.py`, and its tests. No media
reference, route, grant, opaque handle, schema, manifest or wire shape is introduced, nothing imports
Hermes or `hmp_plugin`, and the G1 and G2 fixtures were **not** run again. The existing fixture
framework and its scenario list are unchanged.

## What it is

One function, `read_profile_cache_image(profile_home, candidate)`, for a future selected-profile cache
read. `profile_home` is the caller's already-resolved, already-pinned home. The candidate is untrusted.

1. Platform check first: descriptor-relative no-follow open/stat and `O_DIRECTORY`, `O_NOFOLLOW`,
   `O_CLOEXEC`, `O_NONBLOCK` must all exist, else `unsupported_platform` and no path fallback.
2. Candidate grammar (no filesystem access): refuses anything whose exact type is not `str` (a `str` subclass could override the grammar's methods), empty, absolute, `.`/`..`, any `/` or `\`,
   Unicode control/format/surrogate characters (including NUL), and names over 128 UTF-8 bytes.
3. Pin `home`, `cache`, `images` by descriptor (`O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`, each relative to the
   previous descriptor), then open the file relative to `images` with `O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC`.
4. `fstat`: regular, `nlink == 1`, `0 < size <= 8 MiB`; read at most size+1 bytes; compare the length and
   a second `fstat` signature; then `lstat` every path component against the pinned identity, and require the final name's `lstat`
   and a re-`fstat` of the held descriptor to equal the first full signature (dev, ino, mode, nlink, size,
   mtime, ctime).
5. Every descriptor is closed in a `finally`. Any difference returns a closed refusal and drops the buffer.

**Flat only (my research proposal, pending root acceptance; not previously frozen root wording).** The native producer and inbound names are top-level files of `cache/images`
(delivery-paths note, sweep section), so nested names are refused (`candidate_nested`). Nesting, the
legacy `image_cache` directory, `cache/documents`, another profile, or any copy/outside location is never
consulted or used as a fallback. Widening would need a separate reviewed amendment.

## Labels and privacy

The bytes are **unvalidated raster bytes**. Root's 2026-10-01 raster decision assigns structure/codec checks
on the immutable buffer to a separate prototype; this leaf runs no decoder, magic, MIME, dimension or
animation policy and stays `unvalidated_raster_bytes`. The public report says `raster_validated: false` and carries no MIME or format.
The buffer is held in a private field, excluded from `repr`; `unvalidated_raster_bytes()` is an in-process
handoff. Device and inode numbers are compared internally only. The public report holds a closed outcome,
one byte count, the label and booleans. `_hooks` and `_chunk_size` are test seams, not a product contract.

## Observed (one run, macOS, Python 3.14)

Real temp directories (0700) and files (0600). Every refusal test has a positive control in the same
layout. Refused with the outcome shown: foreign profile paths and symlinks (`candidate_absolute`,
`candidate_dot`, `symlink_refused`, `unavailable`); initial missing/swept at file, `images`, `cache`
(`unavailable`) and home (`profile_home_unavailable`); symlink as final component, dangling, to a directory
(`symlink_refused`); symlink as home/`cache`/`images` ancestor even though its target held a valid file
(`profile_home_invalid`, `ancestor_refused`); hardlink, including one created mid-read (`hardlinked`,
`changed_during_read`); directory, FIFO, socket (`not_regular`); empty; oversize (refused before any
`read`); growth, truncation, same-size rewrite mid-read (`changed_during_read`); replacement, unlink,
symlink swap after the descriptor was held, same-inode same-size rewrite with moved timestamps after the
second `fstat` and before the final recheck (`binding_lost`), and rename plus same-name replacement of `images`, `cache`
and home at three timings (`binding_lost`). Unrelated sibling changes do not refuse.

- FIFO: one test runs a blocking `open` of the same FIFO in a subprocess and shows it hits a 2 s deadline,
  then runs the leaf in a separate subprocess under a 15 s deadline and gets `not_regular`.
- Descriptor leak: a tracker over `os.open`/`os.close` shows every opened descriptor closed across ten
  outcome paths and when a hook raises at each seam; the same tracker with `close` disabled reports 4
  leaked, so the clean result is causal. `/dev/fd` counts match before and after.
- Source tests (AST): no `resolve`, `realpath`, `exists`, `isfile`, `access` or builtin `open`; imports
  limited to the standard library; no Hermes, HMP, network or codec import.
- Single-protection mutations (flag removed or check disabled) each fail at least one test for:
  `O_NOFOLLOW`, `O_NONBLOCK`, `nlink`, regular-file, size bound, second `fstat`, binding revalidation and
  descriptor close. Disabling only the read-length comparison did **not** fail any test: the second `fstat`
  signature already catches every case the tests drive, so that comparison is defence in depth.

## Correction (2026-10-01)

Root review found that the final recheck compared the file only by inode/type/nlink, so a same-inode
rewrite between the second `fstat` and the final path recheck returned `ok`. The buffer was still the
older checked read, so this was not arbitrary-file disclosure, but the stated refusal boundary was
inaccurate. Repaired: the final check now requires the path `lstat` and a fresh descriptor `fstat` to
equal the original full signature. New test: rewrite at `before_revalidate`, same inode and size,
mtime moved. Old code: that test failed (returned `ok`). Repaired code: `binding_lost`. Unmutated
control at the same seam: `ok`.

## Known limits

- Not filesystem atomicity. A change after the final recheck, before the caller uses the buffer,
  cannot be excluded; the buffer is bytes read from the held descriptor, not a promise about the name afterward.
- A same-size in-place rewrite within one timestamp tick on a coarse-timestamp filesystem could evade the
  `fstat` signature. The buffer is read in chunks, so such a mutation can yield a **torn, mixed buffer**
  (old and new bytes), not merely stale bytes. Not driven.
- None of this proves content integrity. An immutable-buffer structural check and the phone codec stay
  mandatory, and the same-account writer remains trusted.
- Case-insensitive and Unicode alias candidate names stay confined to `cache/images` but are not a
  canonical identity. A future media reference must bind the selected context, the row and the
  descriptor/byte observations, never the name alone. No raw-inode identity or monotonic restore proof is claimed.
- An `fstat` that raises `OSError` on a held descriptor becomes one closed `read_failed`; descriptors still
  close. Other exceptions (hook or programmer errors) propagate, and cleanup still runs.
- No ownership or mode check on the three directories or the file (umask-002 hosts would break a
  0755-only rule); same-account writers are inside the adopted trust model.
- `profile_home` and its ancestors are a trusted root as given; resolving or pinning the home is the caller's job.
- Only macOS was run. Linux and its `ENOTDIR`/`ELOOP` mapping for `O_DIRECTORY|O_NOFOLLOW` are mapped by
  both errnos but not run. The socket test skips if a unix socket cannot be bound.
- Not covered: raster format and decoder policy, animation, dimensions, polyglots, the database, grants,
  revocation, tip selection, multiplexed profiles, and any real Hermes cache. No byte, auth, native-history
  or network-service qualification is claimed.

## Hardening (2026-10-01, after independent Opus review PASS)

Review of module `29f743dc`, tests `096bbb12`, note `b880d040` passed with nonblocking limits. Two bounded
changes followed; no other behavior changed. Root can accept the flat-only first slice; flat-only is a
research proposal, not a frozen wire shape.

1. `classify_candidate` uses `type(candidate) is str`, not `isinstance`. New test: a synthetic `str`
   subclass overriding `__contains__`/`startswith` carrying `../images/<name>`. The old (isinstance)
   classifier, rebuilt from the current source, accepts it (`None`); the repaired code returns
   `candidate_type` with no descriptor opened. Plain-`str` controls pass. No user files.
2. The `fstat` calls on held descriptors go through one helper; an `OSError` becomes `read_failed`.
   New test injects the failure at each of the five pre-read `fstat` calls: `read_failed`, every opened
   descriptor closed, `/dev/fd` count restored, unfaulted control `ok`. The hook-`RuntimeError` cleanup
   test is unchanged and passes. Not mutation-run against the old code (it simply propagated `OSError`).

## Run (new test file only; G1/G2 not rerun)

```
/private/tmp/hmp-g2-venv314/bin/python -m pytest -c server/pyproject.toml --rootdir=tools/research \
  --confcutdir=tools/research tools/research/tests/test_local_media_file_safety.py
```

Collection is now 89 tests (83 prior + 1 + 5 new). **Rerun after hardening: 12 passed**, selected with `-k`:
the new `str_subclass` and `fstat_oserror` (5) cases plus the affected descriptor/source tests
(`hook_raises`, `leak_detector`, `every_descriptor`, `source_` (2), `unknown_hook`), under a fresh private
`--basetemp`. The earlier full 83-test pass was on the prior module/tests and is cited from that review, not
re-run. Not run: the other tests of this file, G1/G2, native or matrix suites. Linux remains untested,
the post-final-check race remains, and no auth or raster qualification is claimed.
`uvx ruff==0.16.9 format` and `check` with `--config server/pyproject.toml` on the two files: clean.

SHA-256 (after hardening):
- `tools/research/local_media_file_safety.py`: 440c3cfa5c636d5d280f4cf8876f900ab9177b0421d55a8d5503fc398973ef74
- `tools/research/tests/test_local_media_file_safety.py`: 2209d0390bdde220e1525cd8e400084308f5f15cb71832acdb2d987ec4c92076

## Root acceptance (2026-10-01)

Root accepts the hardened filesystem research leaf and the flat-only first image-cache slice.
Opus passed the prior repaired prototype with 83 tests and 17 reviewer probes; its exact hashes
precede the strict string-type and closed-fstat hardening. Sonnet ran 12 targeted tests after
that hardening, and root independently ran eight positive, late-mutation, string-subclass and
fstat-refusal cases with no failures, errors or skips. The remaining earlier tests were not
rerun by root. The hardened file collection contains 89 cases, not a claimed 89-case full run.

Root reviewed the small hardening delta and retains the coarse-timestamp torn-buffer, alias,
trusted-root, Linux-untested and post-final-check limits. This is not a raster, database,
authorization or transport qualification, and no product module or serving route is introduced.

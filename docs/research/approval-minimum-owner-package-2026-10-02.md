# Approval dogfood source package — 2026-10-02

Root prepared an owner-local source export from reviewed candidate
`150bd0f1535b41495e5fc31ded128b9452221052`. The artifact and its full inventory are private.

| Check | Result |
| --- | --- |
| Source worktree | Exact reviewed commit, clean before and after export |
| Package contents | 239 tracked regular files; 32 under `server/hmp_plugin/` |
| Source delta | Zero changed files, bytes or executable modes |
| Independent comparison | Git archive compared with every exported file; all 239 match |
| Custody | Directories 0700; files 0600, tracked executables 0700; no symlinks or hardlinks |
| Plugin surface | Passed on exported runtime directory |
| Source privacy | Passed; no owner evidence added to tracked files |
| Native evidence carried forward | 13 selected cases on each of two prepared samples, zero skips |

The export was made from Git objects and independently compared with Git archive output.
It does not use the removed historical `owner_package.py` manifest editor. No compatibility
manifest, grant, config, credential, dependency or service was changed. The runtime uses the
minimum-version and actual-API policy accepted in spec 034.

This completes T15's packaging step. The artifact is unsigned; it is neither a release nor a
running-process attestation. It has not been installed. A fresh target check, native installer
scan, drain-aware activation and physical card/answer testing remain deployment gates.
The two sampled runs do not establish behavior on every target, and the release-floor
notifier-dependent cases prove negative capability behavior, not operational cards. No
additional `ca705dbf` candidate run is claimed.

The log scanner found no captured logs in its configured source directory; this is not a
live-log scan.

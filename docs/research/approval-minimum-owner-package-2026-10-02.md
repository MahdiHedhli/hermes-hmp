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

## Superseding export and native scanner check

The initial export above is preserved as historical evidence. Root made a fresh private export
from reviewed `c1d3d0b7369847b921b9998422f1437fc8672f49` ([PR #78](https://github.com/MahdiHedhli/hermes-hmp/pull/78)).
Every one of its 239 regular files was compared with its Git blob. The only difference from
`150bd0f` is the synthetic classification target in `tools/compat/session_chat_approval_probe.py`;
all 32 runtime files are byte-identical. Private custody modes, single links and the unchanged
original export were verified. No source or protected native input changed.

The corrected probe passed all 32 required checks on isolated native `8afaab37`, including
classification, offered choices, deny/once behavior, exact-ID refusals, replay and disconnect
cleanup. Its fake executor never executes the synthetic command. This changed-input check
is separate from the earlier 26 selected native cases; it does not enlarge their coverage.

The actual native `plugin-guard-v8` scanned the fresh export read-only inside the protected
sandbox and returned **caution: 121 findings, zero critical** (2 high, 112 medium, 7 low).
All 121 findings match the reviewed corrected-source scan. Both high findings were inspected
individually: a hostile input in a read test and an intentional Unicode vector. The other
finding groups retain the independent review's sampling limit; they are not all individually
certified. The scanner remains enabled. The original dangerous export is not installed.

This new artifact is unsigned and **not installed**. Live target checks, separately authorized
idle/drain-aware activation and physical approval/card-answer testing remain open. No provider,
dependency, configuration, credential, grant or service was changed. The corrected source can
be packaged; no operational approval or push delivery is claimed.

# Public migration privacy gate

Review date: 2026-09-28. Scope: every tracked file in the fresh public `migrate/initial` history.

| Check | Result |
| --- | --- |
| `python3 tools/ci/scan_private.py` | `scan_private: clean.` No baseline or synthetic allowlist files exist. |
| Tracked file inventory | No environment files, private keys, certificates, provisioning profiles, or keystores. |
| Owner identity and paths | No personal name or email, live home path, team ID, or device name. The public GitHub account appears only in intended repository and Gist links. |
| Network and IDs | No live tailnet address or hostname and no real device/user ID. Public CGNAT contract notation, wildcard DNS syntax, and synthetic fixture IDs are retained as reviewed protocol/test literals. |
| Plugin source | `server/hmp_plugin/` is byte-for-byte identical to the private F1 source. The guarded-send build list and its `bridge_files` are unchanged. |
| Git history | New root commit; no private commit ancestry. |
| README icon | PNG has only image and end chunks, with no text or EXIF metadata. |

A supplemental Gitleaks scan reported six generic-key heuristic matches: one Python type-check expression, four labelled deterministic test vectors, and one literal prefix for synthetic fixture keys. Review found no live credential in these findings. No Gitleaks suppression file was added.

Hermes's plugin installer scans the whole checkout, including tests, tools, and documentation. On this full public tree its plugin guard reports **CAUTION (87 heuristic findings)**. The three runtime-code findings in `cli.py` and `identity.py` remain; the remaining findings are principally test/tool subprocess calls, intentionally hostile fixtures, and documentation commands. This is recorded for review rather than altered during the migration. Installer confirmation or an explicit `--force` is required for this unreviewed community plugin.

## Current installation path (2026-09-29)

The paragraph above records the migration-day root scan, not the recommended
installation path. Install `MahdiHedhli/hermes-hmp#server/hmp_plugin` so the
scanner examines only runtime code. After the CLI type-annotation false
positive was removed, the runtime-only scan returned **SAFE** with two medium
subprocess findings; both calls use fixed arguments and no shell. See
[Install and pair](docs/INSTALL.md). Replacing an older root install requires
`--force`, while the scanner stays enabled.

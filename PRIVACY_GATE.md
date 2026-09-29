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

Hermes's plugin installer scans the whole checkout, including tests, tools, and documentation. On this full public tree its plugin guard reports **CAUTION (87 heuristic findings)**. The three runtime-code findings in `cli.py` and `identity.py` remain; the remaining findings are principally test/tool subprocess calls, intentionally hostile fixtures, and documentation commands. A recheck of the integrated feature branch produced the same verdict and count. The current bare `owner/repo` install path has no file-selection step; moving tests to a scanner-excluded directory or disabling the scan would obscure code that ships to users. The [upstream request](NOUS_GATEWAY_OBSERVATIONS.md) asks for a verified install file set scanned as the activated tree. Installer confirmation or an explicit `--force` is required for this unreviewed community plugin.

The runtime findings were reviewed individually:

| Scanner match | Code behavior |
| --- | --- |
| `dump_all_env` on `cli.py`'s `dispatch(..., env: CliEnv)` signature | The scanner matched an injected CLI context parameter. This line does not enumerate or print process environment variables. |
| `python_subprocess` in `cli.py` | A bounded Hermes CLI child call uses fixed argument structure, `shell=False`, a timeout, and an allowlisted environment. |
| `python_subprocess` in `identity.py` | The macOS host-identity read invokes `ioreg` with fixed arguments and a timeout. |

These findings remain visible in Hermes's own install report. This review does not turn a CAUTION verdict into a SAFE verdict.

# HMP migration inventory

Source: private `f1/connect-and-browse` at `885cd0dc515d589c47aa042fd4d9ac8060edcf2b`. The public repository starts from a new commit; no private Git history is copied.

| Source path | Decision | Public destination or reason |
| --- | --- | --- |
| `server/hmp_plugin/**`, `server/tests/**`, `server/pyproject.toml`, `server/README.md`, `server/DEPLOYMENT.md`, `server/HOST_HARDENING.md` | Move | Same `server/` paths. Root manifest and a small registration wrapper enable the bare install command. |
| `tools/compat/**`, `tools/hermes_builds/**`, `tools/fixtures/**`, `tools/vectors/**`, `fixtures/f1/**` | Move | Same paths; the private app consumes them through a pinned HMP checkout. |
| `tools/ci/check_plugin_surface.py`, `scan_logs.py`, `scan_private.py`, and their relevant tests | Move | Same paths. No privacy baseline or synthetic allowlist files are copied. |
| `tools/ci/check_all.sh`, app/network/config/icon/release checks and tests | Stay | These operate on the mobile app or release artifacts. The private CI runner is revised for the split. |
| `tools/acceptance/interceptor.py`, `make_test_ca.py`, `standin_instance.py`, `verify_p256_signature.py`, requirements and matching tests | Copy | Shared protocol and test CA utilities, without physical owner-session data. |
| `tools/acceptance/owner_session.py`, `run_matrix.py`, mobile-driven tests | Stay | Device and app acceptance workflow remains private. |
| `docs/architecture/contracts/HMP_V1.md`, `HMP_V1_CONFORMANCE.md`, vectors | Move | Same paths; public wire contract. |
| `specs/001-connect-and-browse/contracts/server-modules.md`, `fixture-format.md`, server portion of `data-model.md`; `specs/002-send-messages/DESIGN.md` | Sanitize then move | Public server design material. Mobile model and owner rulings are excluded. |
| `docs/FEATURES.md`, `docs/architecture/ROADMAP.md`, `docs/upstream/NOUS_GATEWAY_OBSERVATIONS.md` | Sanitize then move | Concise root `FEATURES.md`, `ROADMAP.md`, and `NOUS_GATEWAY_OBSERVATIONS.md`. Rejected approvals work is labeled as unreleased. |
| `docs/research/f1-acceptance/LIVE_LOCAL_PAIRING.md` | Rewrite | Generic `docs/INSTALL.md` with placeholders and no owner session data. |
| `docs/design/app-icon/candidate-v1-rounded-transparent.png` | Copy | `assets/icon.png` for README branding. Other icon variants remain with the app. |
| `mobile/**`, `analysis_options.yaml`, `.gitignore`, root README/SECURITY | Stay | App source and app-specific root files stay private; public equivalents are newly written. |
| `docs/research/**` except rewritten guide | Stay | Evidence, captures, logs, and owner session records are never published. |
| `docs/architecture/R0_*`, ADRs, other planning/UX docs, app specs | Stay | Owner decisions and app planning remain private. Only a short public constitution is published. |
| `.specify/**`, `.claude/**`, `AGENTS.md` | Stay | Private workflow instructions are not copied. Public Spec Kit constitution is new. |
| `specs/003-approvals/DESIGN.md` and F3 code | Separate draft PR | F3 is rejected by security reviews; it is excluded from this migration. |

## Packaging and compatibility

Hermes's installer resolves `owner/repo` to the repository root and requires `plugin.yaml` plus `__init__.py` there. The root wrapper imports the existing `server/hmp_plugin` implementation. Plugin source files and the guarded-send `bridge_files` list remain in their original paths and retain their behavior. The root manifest duplicates the package dependency declaration so Hermes's plugin manager installs `qrcode`.

## Privacy gate

Run `python3 tools/ci/scan_private.py` from this repository with neither baseline nor synthetic allowlist. Also inspect tracked text for real private addresses, host paths, owner/device identities, team IDs, real HMP IDs, and credential patterns. Synthetic test values are represented with escaped delimiters in source and JSON; they decode to the same fixture values at runtime. No private history is imported.

## Open decisions

The repository uses the MIT license selected by its owner. The [public Gist](https://gist.github.com/MahdiHedhli/c8d01a96bdfc794edaf7c3e1f4cb1502) mirrors the reviewed root observations file; the root file is the canonical version.

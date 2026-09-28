# Migration plan

1. Copy the sanitized F1 server package, tests, vectors, fixtures, and compatibility tools into a fresh public Git history.
2. Add a root `plugin.yaml` and `__init__.py` registration wrapper for Hermes's bare repository installer. Keep `server/hmp_plugin` source bytes and build fingerprints unchanged.
3. Publish concise public docs, a Spec Kit constitution, CI, and a reviewed privacy-gate report.
4. Remove the moved plugin tree from the private app repository and pin the public checkout as the `hmp/` submodule. Preserve app tests through a contract path link, without editing `mobile/`.
5. Validate from the public and private checkouts. Test plugin installation under an isolated `HERMES_HOME` and qualify fixtures against extracted Hermes builds.
6. Open review PRs. Keep F3 approvals in a separate draft PR with explicit security blockers.

The [inventory](../../MIGRATION_INVENTORY.md) lists the disposition of each source area. The [privacy gate](../../PRIVACY_GATE.md) records publication checks.

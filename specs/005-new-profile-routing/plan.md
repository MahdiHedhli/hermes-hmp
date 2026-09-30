# Plan: routing for a bot created after installation

## Modules

- `server/hmp_plugin/routes.py` (new): planning and writing. No Hermes import. `yaml` (PyYAML)
  is imported lazily inside functions, and only in this module.
- `server/hmp_plugin/cli.py`: `routes add <profile>` parser entry, `("routes", "add")` in
  `MUTATING_COMMANDS`, and a dispatch branch that resolves custody with
  `identity.resolve_custody` (named profile and unsafe custody refused), then calls `routes`.
  It does not open the store, does not need an instance identity, and never calls
  `run_hermes_cli`.
- `tools/ci/check_plugin_surface.py`: `yaml` joins `qrcode` as a module-restricted, lazily
  imported third-party package (`routes.py` only). Test added.
- `server/pyproject.toml`, both `plugin.yaml` files, `server/uv.lock`: PyYAML becomes a runtime
  dependency, because the command parses and re-emits config. The floor `>=6,<7` matches the
  existing dev pin. Whether Hermes PM admits it (as it did `qrcode`) is not verified here.

## Trust boundaries

- Only files under the default Hermes root are touched, and only two. A named profile's process
  cannot run the command (ID-2).
- Same-user code can already edit these files (SEC-1). The checks mitigate mistakes, other-user
  symlink swaps, and hostile config shapes; they are not a boundary against same-user code.
  Between the final unchanged-check and the rename there is a small window a concurrent editor
  could hit; there is no cross-process lock with Hermes.
- Authorization is unchanged. The route only lets Hermes resolve the bot. Access still needs the
  phone's request and the host's `pairing approve`.

## Algorithm

1. Validate the name. Resolve the root through custody. Check the directory chain (`root`,
   `profiles`, `profiles/<name>`): real directories, owned by the operator, not group- or
   world-writable. The root itself may be reached through a symlink (the operator's own choice;
   `resolve_custody` compares real paths); nothing below it may be.
2. Read both configs with `O_NOFOLLOW`, `fstat` checks and a size bound; record identity and
   SHA-256. Parse with a strict `SafeLoader` (no duplicate keys, aliases, merge keys).
3. Plan on deep copies. Refuse on any R5/R6 condition, and when the root's
   `gateway.multiplex_profiles` is not already `true` (R2).
4. If nothing changes, print and stop.
5. Emit new YAML for changed files, re-parse it, and require it to equal the expected document.
6. Re-read BOTH originals and require the recorded identity and hash. Write private backups,
   then recheck both again. Write the profile config, then the root config (root rechecked just
   before). On any failure or interrupt after the profile write began, restore the profile file
   only if it is still what was written; report the exact state of each file (status-only).
   Pre-write read/stat/deep-copy/import failures become clean refusals.

## Compatibility assumptions

Route fields are those used by the fixture builder. `multiplex_profiles` is checked at the top
level and under `gateway`; only `gateway.multiplex_profiles` is written. Hermes's route matcher
is not imported or re-implemented. The overlap rule is deliberately broader than any matcher, so
an unfamiliar route refuses instead of being widened.

## Risks

- Re-emitting YAML drops comments and formatting (the backup mitigates; documented).
- Over-refusal on unusual but valid configs. The operator can still edit by hand per
  `DEPLOYMENT.md`.
- PyYAML admission by Hermes PM is unverified here.

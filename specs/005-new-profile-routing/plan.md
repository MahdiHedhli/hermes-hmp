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

- Only one file under the default Hermes root is written: the root `config.yaml`. The profile
  config is read and drift-checked but never written. A named profile's process cannot run the
  command (ID-2).
- Same-user code can already edit these files (SEC-1). The checks mitigate mistakes, other-user
  symlink swaps, and hostile config shapes; they are not a boundary against same-user code.
  Between the final unchanged-check and the rename there is a small window a concurrent same-user
  editor could hit and be overwritten; there is no cross-process lock with Hermes, and none is
  added here without root review.
- Authorization is unchanged. The route only lets Hermes resolve the bot. Access still needs the
  phone's request and the host's `pairing approve`.

## Algorithm

1. Validate the name. Resolve the root through custody. Check the directory chain (`root`,
   `profiles`, `profiles/<name>`): real directories, owned by the operator, not group- or
   world-writable. The root itself may be reached through a symlink (the operator's own choice;
   `resolve_custody` compares real paths); nothing below it may be.
2. Read both configs with `O_NOFOLLOW`, `fstat` checks and a size bound; record identity and
   SHA-256. Parse both with a strict `SafeLoader` (no duplicate keys, aliases, merge keys). The
   profile document is parsed only to prove it is safe, plain YAML; no value in it is used.
3. Plan on a deep copy of the root. Refuse on any R5/R6 condition, and when the root's
   `gateway.multiplex_profiles` is not already `true` (R2). The plan can only change
   `gateway.profile_routes`.
4. If the exact route is already present, print and stop (no write, no backup).
5. Emit new YAML for the root, re-parse it, and require it to equal the expected document.
6. Re-read BOTH originals and require the recorded identity and hash. Write the private backup of
   the root, then recheck both again immediately before the rename. Write the root atomically with
   its original mode. On any failure or interrupt from the write onward, read the root back and
   report one of: holds the new route, not changed by this command, or unconfirmed (backup named).
   Nothing is restored. Pre-write read/stat/deep-copy/import failures become clean refusals.

## Compatibility assumptions

Route fields are those used by the fixture builder. The root `multiplex_profiles` is checked at the
top level and under `gateway`; nothing but `gateway.profile_routes` is written. A profile's own
`multiplex_profiles` is not read. On `ca705dbf7ef86425b381b542712aff310f1ee52c` a multiplexing root
serves profiles without it, and it changes the profile's history namespace; other builds are not
characterized here. Hermes's route matcher is not imported or re-implemented. The overlap rule is
deliberately broader than any matcher, so an unfamiliar route refuses instead of being widened.
The running gateway loads routes once, so the route needs a restart to take effect; the command
promises no hot activation.

## Risks

- Re-emitting YAML drops comments and formatting (the backup mitigates; documented).
- Over-refusal on unusual but valid configs. The operator can still edit by hand per
  `DEPLOYMENT.md`.
- PyYAML admission by Hermes PM is unverified here.

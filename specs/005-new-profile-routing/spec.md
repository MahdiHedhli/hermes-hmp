# Feature specification: routing for a bot created after installation

Status: draft for review. No wire, store, or grant change.

## Problem

HMP can only reach a named profile when the default root `config.yaml` has a matching
`gateway.profile_routes` entry and the profile's own `config.yaml` has
`gateway.multiplex_profiles: true` (see `server/DEPLOYMENT.md`); Hermes serves an eligible profile
only after the root gateway, which already multiplexes profiles, detects it. A profile created
after HMP was installed has neither. The bridge asks Hermes to resolve the synthetic
source (`scope_id = guild_id = <profile>`), gets no match, falls back to the owner profile, and
correctly answers `not_routed`. That refusal is right and stays. What is missing is a safe,
explicit way for the operator to prepare routing for one new bot.

## Behavior

`hermes hmp routes add <profile>` is a host-only operator command. It prepares routing for
exactly one named profile and nothing else.

- **R1 Route.** Adds `{name: "<profile>-route", platform: "hmp", profile: "<profile>",
  guild_id: "<profile>"}` to `gateway.profile_routes` in the default root config.
- **R2 Multiplex.** Sets `gateway.multiplex_profiles: true` in that profile's own config. It
  never changes the root's: the root `gateway.multiplex_profiles` must already be boolean `true`
  (initial setup), otherwise it refuses with a pointer to `server/DEPLOYMENT.md`. It does not
  serve or reload anything. For a profile that already has sessions, the per-profile flag can
  change its session namespace; the docs tell the operator to review sessions first, and nothing
  is migrated.
- **R3 Preserve.** Every other semantic value in both files is preserved. Comments and layout are
  not (a changed file is re-emitted), which is why R9 keeps a backup. A file that needs no change
  is not rewritten.
- **R4 Idempotent.** When everything is already in place the command changes nothing (no write,
  no backup) and exits 0 with the same next-steps text.
- **R5 Refuse, never widen.** It refuses, changing nothing, when any existing HMP-capable route
  could overlap the new one: a route whose platform is absent, `hmp`, or not a plain string, and
  whose `guild_id` is absent, this profile's name, or not a plain literal. That covers broad,
  user-specific, chat-specific, disabled, and differently targeted routes. Only a route that is
  exactly R1, with `enabled` absent or boolean `true`, counts as "already present". Any extra
  key, even with a null value, and `enabled: null`, is a conflict.
- **R6 Multiplex conflicts.** It refuses when a top-level or nested `multiplex_profiles` is
  present with any value other than boolean `true`, in either file, or when a top-level
  `profile_routes` exists (ambiguous location).
- **R7 Input validity.** The name must match Hermes's profile rule (`^[a-z0-9][a-z0-9_-]{0,63}$`)
  and not be `default`. The profile directory, its `config.yaml`, and the root `config.yaml` must
  already exist. The command never creates a profile or a config.
- **R8 Path safety.** No path below the Hermes root may be a symlink. Directories and files must
  be owned by the operator and not group- or world-writable. Files must be regular and at most
  1 MiB. YAML must be a single document holding a mapping, with no duplicate keys, aliases, merge
  keys, or unknown tags.
- **R9 Backups and writes.** Before any write it makes one private (0600) backup per file it will
  change, `config.yaml.hmp-bak` beside the original (one rolling file, replaced on each change;
  a second run replaces the first run's backup, so original comments survive only in a copy the
  operator makes). Writes are atomic per file (same-directory temp file, fsync, rename) and keep
  the original file mode. BOTH config files are re-read and compared before any backup, and again
  before the first config write (backups take time), whichever files will change.
- **R10 Two files are not atomic.** The profile file is written first, then the root (the root
  route is what turns routing on). If the root write fails, or any exception, `KeyboardInterrupt`
  or `SystemExit` arrives after the profile write began, the profile file is restored only when it
  still holds exactly what this command wrote. The command reports each file's final state (an
  interrupt is reported with exit status 130, never swallowed), says "not changed by this
  command" for a file another writer changed, and never claims a rollback it did not confirm. A
  small same-user race between the final check and the rename remains; there is no shared lock.
- **R10a Clean pre-write failures.** A read, stat, deep-copy or missing-PyYAML failure before any
  write is a clean refusal ("nothing was changed"), status-only: no exception or YAML detail is
  ever printed, since it may hold private config.
- **R11 Guards.** It is a mutating command: it refuses without an interactive terminal and when
  any `HERMES_SESSION_*` variable is set, like the other mutating commands. It refuses under a
  named profile (`identity.resolve_custody`).
- **R12 No other side effects.** It does not authorize a user or device, create or approve a
  pairing request, enable an API server, change any grant, restart the gateway, contact Hermes,
  or open the HMP store.
- **R13 Output.** It prints what changed and the required sequence: restart the gateway; on the
  paired phone request access to the bot; then approve that device's pending `hmp` row with
  `hermes -p <profile> pairing approve hmp <request_id>` after checking it belongs to the device.

## Out of scope

Removing routes; several profiles at once; automatic gateway restart; Windows ACL checks (the
owner and mode checks are skipped where `os.geteuid` is absent); any bridge, protocol, or store
change; deciding which bots a device may use.

## Acceptance scenarios

1. Routing was prepared for `alpha` at install (root multiplexing on); `beta` is created later.
   `routes add beta` adds one route and multiplexes `beta`. With root multiplexing absent it
   refuses and writes nothing. `alpha`'s route and config, and all unrelated root values,
   are unchanged.
2. Running it twice reports "already prepared" the second time and rewrites nothing.
3. Unknown profile, invalid name, `default`, missing configs: refused, nothing written.
4. Symlinked profile directory or config, group/world-writable file, oversize file, duplicate
   keys, alias, malformed YAML, non-mapping document: refused, nothing written.
5. Overlapping routes (broad, user-, chat-scoped, disabled, other-profile same guild),
   `multiplex_profiles: false`, string `"true"`, top-level/nested disagreement: refused.
6. A file changed between read and write: refused, nothing written.
7. Root write failure after the profile write: profile restored and reported; if the restore also
   fails, the report says so and names the backup.
8. Non-TTY, `HERMES_SESSION_*`, named-profile process: refused.
9. No subprocess, store open, or approval call happens in any scenario.

## Reference

Inspected upstream reference (public SHA only, not a fixture validation claim):
`ca705dbf7ef86425b381b542712aff310f1ee52c`. Route field names follow
`tools/fixtures/build_fixture.py` and `server/DEPLOYMENT.md`. Unknown route fields are treated as
narrowing, so they refuse rather than pass.

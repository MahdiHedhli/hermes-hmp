# Feature specification: routing for a bot created after installation

Status: reviewed operator-command draft; disposable-host qualification remains open. No wire,
store, or grant change. This revision supersedes the earlier two-file draft (see `REVIEW.md`).

## Problem

HMP can only reach a named profile when the default root `config.yaml` has a matching
`gateway.profile_routes` entry and the root gateway multiplexes profiles (see
`server/DEPLOYMENT.md`). On the inspected build, a multiplexing root serves every live named
profile without consulting that profile's own `gateway.multiplex_profiles` (`profiles_to_serve`).
A profile created after HMP was installed has no route. The bridge asks Hermes to resolve the
synthetic source (`scope_id = guild_id = <profile>`), gets no match, falls back to the owner
profile, and correctly answers `not_routed`. That refusal is right and stays. What is missing is a
safe, explicit way for the operator to put one root route on disk for one new bot.

## Behavior

`hermes hmp routes add <profile>` is a host-only operator command. It writes the root route for
exactly one named profile and nothing else.

- **R1 Route.** Adds `{name: "<profile>-route", platform: "hmp", profile: "<profile>",
  guild_id: "<profile>"}` to `gateway.profile_routes` in the default root config.
- **R2 Root only.** The command writes only the root `config.yaml`. The profile's own
  `config.yaml` is never written, backed up or modified (bytes, mode and mtime stay as they
  were), whatever its `multiplex_profiles` is (absent, `false`, `true`, a string, top-level or
  nested). That flag changes the profile's session namespace, so the command must not set it, and
  it is neither required nor refused. A profile with existing sessions is allowed and its files
  are untouched; there is no zero-history rule and no history warning. The root's own
  `gateway.multiplex_profiles` must already be boolean `true` (initial setup), at the top level
  and nested alike when present, otherwise it refuses with a pointer to `server/DEPLOYMENT.md`.
- **R3 Preserve.** Every other semantic value in the root is preserved. Comments and layout are
  not (a changed file is re-emitted), which is why R9 keeps a backup. A file that needs no change
  is not rewritten.
- **R4 Idempotent.** When the exact route is already present the command changes nothing (no
  write, no backup) and exits 0 with the same next-steps text.
- **R5 Refuse, never widen.** It refuses, changing nothing, when any existing HMP-capable route
  could overlap the new one: a route whose platform is absent, `hmp`, or not a plain string, and
  whose `guild_id` is absent, this profile's name, or not a plain literal. That covers broad,
  user-specific, chat-specific, disabled, and differently targeted routes. Only a route that is
  exactly R1, with `enabled` absent or boolean `true`, counts as "already present". Any extra
  key, even with a null value, and `enabled: null`, is a conflict.
- **R6 Root multiplex conflicts.** It refuses when a top-level or nested root
  `multiplex_profiles` is present with any value other than boolean `true`, or when a top-level
  `profile_routes` exists (ambiguous location).
- **R7 Input validity.** The name must match Hermes's profile rule (`^[a-z0-9][a-z0-9_-]{0,63}$`)
  and not be `default`. The profile directory, its `config.yaml`, and the root `config.yaml` must
  already exist. The command never creates a profile or a config.
- **R8 Path safety.** No path below the Hermes root may be a symlink. Directories and files must
  be owned by the operator and not group- or world-writable. Files must be regular and at most
  1 MiB. YAML must be a single document holding a mapping, with no duplicate keys, aliases, merge
  keys, or unknown tags. The profile config is inspected this way as a prerequisite (path, owner,
  mode, size, strict YAML); none of its values is interpreted.
- **R9 Backup and write.** Before the write it makes one private (0600) backup of the root,
  `config.yaml.hmp-bak` beside the original (one rolling file, replaced on each change; a second
  run replaces the first run's backup, so original comments survive only in a copy the operator
  makes). The write is atomic (same-directory temp file, fsync, rename) and keeps the original
  file mode. BOTH config files are re-read and compared with what was read before the backup, and
  again after it, immediately before the rename; drift in either refuses the run, changing nothing.
  Drift in the profile file is a prerequisite check only: it is never written.
- **R10 Content-free failure state.** If an exception, `KeyboardInterrupt` or `SystemExit` arrives
  once the rename may have happened, the command reports, from the root file's current bytes alone,
  one of: it now holds the new route (on disk; the running gateway is unchanged), it was not changed
  by this command, or its state could not be confirmed (neither original nor new content, with the
  backup named). Nothing is restored, and a file another writer edited is never overwritten. An
  handled interrupt during the root write is reported with exit status 130. An interrupt during
  the backup write changes no config, though the backup may have changed. A second interrupt
  during the final-state read may prevent reporting: the root may already hold the new route and
  must be checked. No configuration content or caught exception text
  is printed. A small same-user race between the final check and the rename remains; there is no
  shared lock, and a concurrent same-user editor of the root can be overwritten.
- **R10a Clean pre-write failures.** A read, stat, deep-copy or missing-PyYAML failure before any
  write is a clean refusal ("nothing was changed"), status-only: no exception or YAML detail is
  ever printed, since it may hold private config.
- **R11 Guards.** It is a mutating command: it refuses without an interactive terminal and when
  any `HERMES_SESSION_*` variable is set, like the other mutating commands. It refuses under a
  named profile (`identity.resolve_custody`).
- **R12 No other side effects.** It does not authorize a user or device, create or approve a
  pairing request, enable an API server, change any grant, restart the gateway, contact Hermes,
  read or write any `.env`, or open the HMP store.
- **R13 Output.** It says the root route is on disk only, that the command did not activate it in the
  running gateway, that reload requires a gateway restart on the inspected build, and that sending
  also needs its separate prerequisites. For an already-present route it says only that the running
  gateway's state was not checked. It prints the manual
  sequence: restart the gateway; on the paired phone request access to the bot; then approve that
  device's pending `hmp` row with `hermes -p <profile> pairing approve hmp <request_id>` after
  checking it belongs to the device. It makes no promise of hot activation.

## Open items

- History readability on `ca705` of a profile without its own `multiplex_profiles` flag
  (`profiles_to_serve` does not consult the flag, which covers serving and routing only). Root-
  reviewed fixture evidence (`C6-EVIDENCE.md`, flag absent or false alike): history the root creates
  for a routed source reads canonically and shows in the Phone list; earlier history of a standalone
  profile gateway (legacy `agent:main` keys) stays intact and resolves by session id, but the
  canonical read is empty and the Phone list omits it. Route-only preparation is not a legacy-history
  migration; a safe fix needs a separate contract decision, and a flag change or history rewrite is
  not an authorized repair. The per-profile flag stays untouched by this command. The disposable-host
  gateway loop and authorization remain unqualified (`tasks.md` C6). This fixture does not qualify
  other read paths or the automatic-preparation/access-card proposal (006); their contracts and
  authorization review remain separate.

## Out of scope

Removing routes; several profiles at once; automatic gateway restart; Windows ACL checks (the
owner and mode checks are skipped where `os.geteuid` is absent); any bridge, protocol, or store
change; deciding which bots a device may use; writing or repairing a profile's own config or
multiplex flag; route hot-activation or any promise that a running gateway loads the route; a
lock shared with Hermes.

## Acceptance scenarios

1. Routing was prepared for `alpha` at install (root multiplexing on); `beta` is created later.
   `routes add beta` adds one root route and touches nothing else. With root multiplexing absent it
   refuses and writes nothing. `alpha`'s route and config, `beta`'s config, and all unrelated root
   values are unchanged.
2. `beta`'s own config holds no flag, `false`, `true`, a string, a top-level flag, or is empty:
   in every case it is byte-for-byte and mtime identical afterwards and has no backup.
3. `beta` already has session files: the command succeeds and they are untouched.
4. Running it twice reports "already in the root config.yaml" the second time and rewrites nothing.
5. Unknown profile, invalid name, `default`, missing configs: refused, nothing written.
6. Symlinked profile directory or config, group/world-writable file, oversize file, duplicate
   keys, alias, malformed YAML, non-mapping document (either file): refused, nothing written.
7. Overlapping routes (broad, user-, chat-scoped, disabled, other-profile same guild) and a root
   `multiplex_profiles: false`, string `"true"`, top-level/nested disagreement: refused.
8. A file (root or profile) changed between read and write, or during the backup write: refused,
   no config file changed.
9. Root write failure before the rename: root confirmed unchanged. Failure or interrupt after the
   rename: reported as on disk. External edit then failure: reported unconfirmed, edit left alone.
10. Non-TTY, `HERMES_SESSION_*`, named-profile process: refused.
11. No subprocess, store open, `.env` access or approval call happens in any scenario.

## Reference

Inspected upstream reference (public SHA only, not a fixture validation claim):
`ca705dbf7ef86425b381b542712aff310f1ee52c`. The per-profile flag facts above are taken from that
exact build (`docs/architecture/NEW_BOT_HMP_ENROLLMENT.md`, section 2). They do not establish how
an older build treats that flag; fixtures and earlier qualification runs wrote the flag into
profiles, and sessions they created may sit under a different namespace. This spec makes no claim
that any older release keeps existing history readable. Route field names follow
`tools/fixtures/build_fixture.py` and `server/DEPLOYMENT.md`. Unknown route fields are treated as
narrowing, so they refuse rather than pass.

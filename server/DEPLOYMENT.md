# Deploying HMP: gateway routing configuration

This note is for the operator installing the HMP (Hermes Mobile Protocol) plugin into a Hermes
gateway. It covers a **real Hermes gateway-configuration requirement**, not an HMP-side default:
without it, HMP's reads (roster, snapshot, history) for a bot cannot resolve to that bot's
profile at all. It is unrelated to `HOST_HARDENING.md`, which covers exposure of *other* Hermes
host surfaces (`api_server`, the dashboard, `/api/status`); this note covers what HMP itself needs
from the gateway config to route correctly.

## The requirement

For every profile HMP is to serve reads for, the Hermes gateway config needs **both**:

1. `gateway.multiplex_profiles: true` in the **root** `config.yaml`. The fixture tooling and the
   earlier qualification runs also wrote it in each profile's own `config.yaml`
   (`<home>/profiles/<name>/config.yaml`); see the version note below. `hermes hmp routes add`
   neither requires nor writes that profile value.
2. A `gateway.profile_routes` entry for that profile, in the root `config.yaml`:

   ```yaml
   gateway:
     multiplex_profiles: true
     profile_routes:
       - name: "<profile>-route"
         platform: "hmp"
         profile: "<profile>"
         guild_id: "<profile>"
   ```

Neither is an HMP default. A fresh Hermes install has no `profile_routes` at all, and
`multiplex_profiles` is unset (single-profile). Without both, HMP is installed and paired
correctly but every read for that bot fails closed (see "What happens if this is missing" below).

## Why this is real Hermes behavior, not a fixture artefact

This was first flagged as a finding while building the fixture tooling
(`tools/fixtures/build_fixture.py`, T060) and has been independently verified against the actual
Hermes gateway source in both compat-matrix builds (`stock-base` `04fa849e70`, `experimental`
`7e8c8f07a1`), not just inferred from fixture behavior:

- **`gateway.profile_routes` / route resolution.** HMP's read bridge (`bridge.py`'s `_source`)
  builds each read as a synthetic inbound source stamped `scope_id=guild_id=<profile>`, exactly
  like a real inbound platform message from that "location," and then asks Hermes's own route
  matcher to resolve it — it does not assume its own answer. Hermes's gateway
  (`gateway/run.py`'s `_profile_name_for_source`) resolves the profile for any inbound source via
  `gateway/profile_routing.py`'s `match_profile_route` against `config.profile_routes`. With no
  matching route, the source's `profile` stays the receiving adapter's own (default) profile, so
  a request naming a different profile does not resolve to it.
- **`gateway.multiplex_profiles` gates routing entirely.** The same `_profile_name_for_source`
  returns `None` immediately when `not getattr(config, "multiplex_profiles", False)` — routing is
  gated on multiplexing being on in the first place; `profile_routes` alone, without
  `multiplex_profiles: true` in the root config, is not read.
  Multiple built runs in `docs/research/r0e/evidence/` (S1–S16, baseline and patched, across
  `04fa849e70`, `7e8c8f07a1`, `82d7ca81a4`, `590c95083d`, `d1561021d7`) confirm the config shape
  this requires (`multiplex_profiles: true` plus a `profile_routes` list) and, separately, single
  profile Hermes installs log `Single-profile install: gateway.multiplex_profiles unset, serving
  the default profile only` when it is absent — i.e. named profiles are unreachable by construction
  without it.
- **A profile's own `multiplex_profiles` is a separate flag with a session-namespace effect, as
  observed on older builds only.** The description below comes from older stock (`04fa849e70`) and
  experimental (`7e8c8f07a1`) source and from fixtures built against them; it is not established
  for `ca705dbf7ef86425b381b542712aff310f1ee52c` (see the version boundary below).
  `gateway/session_recovery.py`'s
  `_resolve_profile_for_key` (which decides a session key's `agent:<profile>` namespace) reads
  `multiplex_profiles` off whatever `load_gateway_config()` sees for the *current* `HERMES_HOME`
  scope — which, when Hermes work is scoped to a profile's own home, is that profile's *own*
  `config.yaml`, not the root one. Without it there, sessions get written under the `agent:main`
  namespace while `bridge.py`'s read path (`gateway.session.build_session_key(source,
  profile=profile)`, which has no config dependency of its own) looks them up under
  `agent:<profile>` — on those builds, a namespace mismatch that makes every snapshot/history read
  come back empty despite real, correctly authorized rows underneath.

  **Version boundary.** The exact-build source fact for routing is Hermes
  `ca705dbf7ef86425b381b542712aff310f1ee52c`: there, `profiles_to_serve(multiplex=True)` serves
  every live named profile of a multiplexing root without consulting the profile's own flag, and
  that flag changes the profile's history namespace. The fixture and the older qualification above
  wrote the flag so fixture-created sessions land under the namespace the bridge reads; that is a
  property of those fixtures and builds, not a claim that an older release keeps existing history
  readable. `routes add` therefore leaves every profile config byte-for-byte as it is, and this
  document makes no claim about other builds' behavior with or without the flag.

  **Open item (not proven).** Whether a profile without its own flag has readable history on
  `ca705` is not established by the Hermes source or the fixtures: `profiles_to_serve` not
  consulting the flag covers serving and routing, not which namespace the bridge reads. Do not read
  route-only as a promise of readable history; this needs an integration check on `ca705`.

This is exactly the deployment shape `tools/fixtures/build_fixture.py` writes for every fixture
instance (`_write_config_yaml`, one root `profile_routes` entry per profile; a per-profile
`config.yaml` stamped `gateway:\n  multiplex_profiles: true\n`), and it is what the T035 real
gateway suite runs against. The root `multiplex_profiles` and route entries are what routing
needs; the per-profile flag in fixtures is for the older builds and fixtures described above, and
is not claimed to be required or sufficient on `ca705`.

## What happens if this is missing (already contract-covered — no change needed here)

This was checked against the existing HMP v1 contract before writing this note, per this task's
instruction to stop and escalate if it needed a new `ERR` `why` or `/ready` field. It does not:
HMP already fails closed with an explicit, documented state rather than a silent empty read.

- `bridge.py`'s `authz_state` calls `served_profiles()` first: a profile Hermes is not serving at
  all (`multiplex_profiles` off, or the profile home doesn't exist) answers
  `AuthzState.NOT_SERVED`.
- A profile that Hermes *is* serving, but that no `profile_routes` entry resolves back to (or
  whose route Hermes's own ingress rejected — `source.profile_route_rejected`, SR-6), answers
  `AuthzState.NOT_ROUTED` (`bridge.py`'s `_not_routed`).
- Both map to the same wire refusal: `ErrorCode.NOT_ROUTED`, HTTP 409, message "bot is not served
  by this instance" (`contract.py`'s `PER_BOT_GATE_REFUSALS`). Every per-bot read
  (`reads.py`'s `_gate`) raises this *before* running any read, and the roster response
  (RO-1) reports each served-but-unrouted bot's `authz` as `"not_routed"` explicitly rather than
  omitting it — a client can tell "this bot needs a route" from "this bot has no data" without
  guessing.
- This is already covered by tests: `server/tests/unit/test_bridge.py` (`test_...not_routed`,
  `test_profile_route_rejected_forces_not_routed`) and `server/tests/unit/test_reads.py`
  (parametrized `NOT_ROUTED`/`NOT_SERVED` cases for both the per-bot gate and the roster).

## A bot created after installation

Three separate things must be true before a phone can use a bot. Do not mistake one for another.

| Layer | What it means | Who sets it |
| --- | --- | --- |
| Serving | Hermes lists the profile as served. An eligible profile is served only once the root gateway, with `multiplex_profiles` already on, detects and reconciles it. | Hermes |
| Routing | HMP can resolve the bot: the exact root route above, in the root `config.yaml` and in the running gateway (which loads routes once, so a restart is needed). | The host operator |
| Authorization | This device may use this bot: a pending request from the phone, approved on the host. | The host operator, per device |

A profile created after HMP was installed is not routed, so its roster entry shows `not_routed`.
That refusal is correct and is not bypassed. New bots are opt-in: HMP never adds routes or grants
on its own. The command below requires the initial setup above to be done already: the root
`gateway.multiplex_profiles` must be boolean `true`, and the command refuses otherwise (it never
turns on multiplexing for the whole gateway). To prepare one bot, run on the host, in an operator
shell:

```sh
hermes hmp routes add <profile>
hermes gateway restart
```

The command writes exactly one file: the default root `config.yaml`. It adds the exact route
shown above. The profile's own `config.yaml` is read and checked (path, owner, mode, size,
strict single-document YAML) but never written, backed up or interpreted: its own
`multiplex_profiles` value, whatever it is, is neither required nor changed, and existing sessions
do not block the command and are not touched. It never authorizes a user or device, approves a
request, enables an API server, serves or reloads anything, or restarts the gateway. Afterwards
the route is **on disk only**. This command did not activate it in the running gateway; reload
requires a gateway restart on the inspected build. Sending also needs its separate prerequisites.
It is safe to run again.

- It refuses, changing nothing, when the root `gateway.multiplex_profiles` is not already boolean
  `true` (finish initial setup first; a top-level or nested value of any other kind also refuses),
  when an existing route could overlap the new one (broad, user-specific, chat-specific, disabled,
  `enabled: null`, carrying any extra key even with a null value, or pointing at another profile),
  when a top-level `profile_routes` exists, when a path is a symlink or is group- or
  world-writable, or when a file is not plain, single-document YAML with no duplicate keys or
  aliases. Only a route that is exactly the one above, with `enabled` absent or `true`, counts as
  already present. Resolve the reported file by hand, then run it again. Error messages are
  status-only and never quote config content.
- It never edits or removes an existing route or value. Comments and layout in the root file are
  not preserved. It keeps one private (mode 0600) backup, `config.yaml.hmp-bak` beside the root
  config, replaced on each change: a second run (for another bot) replaces it with the file as the
  first run left it, so comments from the original file survive only in a copy you make yourself.
  No backup is made for a profile config, which is not changed.
- Both config files are compared with what was read, after planning and again after the backup
  and immediately before the rename; a change to either refuses the run. The root is then written
  atomically (same-directory temp file, fsync, rename) keeping its original mode. If a failure or
  interrupt arrives once the rename may have happened, the command reports what the root file
  holds: the new route (on disk), unchanged by this command, or unconfirmed. It never restores or
  overwrites a file another writer edited as failure recovery. A handled interrupt during the root
  write exits with status 130 after reporting. An interrupt during the backup write changes no
  config, though the backup may have changed. A second interrupt during the final-state read may
  prevent reporting; the root may already contain the new route and must be checked. A small
  same-user race between the final check and the rename remains: there is no lock shared with
  Hermes, so an edit made to the root file at that moment can be overwritten.
- It runs only under the default profile, from an interactive terminal, and not from a Hermes
  session.

After the restart, authorize the device for the new bot: on the paired phone, request access to
it; then on the host run `hermes -p <profile> pairing list`, check the pending `hmp` row belongs to
that device, and run `hermes -p <profile> pairing approve hmp <request_id>`. An empty list means
the phone has not sent its request yet.

## Operator checklist

- [ ] Root `config.yaml`: `gateway.multiplex_profiles: true`.
- [ ] Root `config.yaml`: one `gateway.profile_routes` entry per profile HMP should serve —
      `platform: hmp`, `profile: <name>`, `guild_id: <name>` (leave `bot_profile` unset: HMP is a
      root-level adapter, so routes apply against the default profile's bot, which is correct).
- [ ] Fixture and older-build setups only: each served profile's own
      `<home>/profiles/<name>/config.yaml` also carries `gateway.multiplex_profiles: true` (see the
      version note above). On `ca705` this is not required for serving, it changes the profile's
      history namespace, and `routes add` does not set it.
- [ ] `plugins.enabled` includes `"hmp"`.
- [ ] For a profile created later: `hermes hmp routes add <profile>`, then restart the gateway.

If a bot's roster entry shows `"not_routed"` or `"not_served"` after pairing, re-check this
checklist before assuming a plugin or pairing problem.

# Deploying HMP: gateway routing configuration

This note is for the operator installing the HMP (Hermes Mobile Protocol) plugin into a Hermes
gateway. It covers a **real Hermes gateway-configuration requirement**, not an HMP-side default:
without it, HMP's reads (roster, snapshot, history) for a bot cannot resolve to that bot's
profile at all. It is unrelated to `HOST_HARDENING.md`, which covers exposure of *other* Hermes
host surfaces (`api_server`, the dashboard, `/api/status`); this note covers what HMP itself needs
from the gateway config to route correctly.

## Check the Hermes gateway topology first

The explicit configuration below was tested on the older fixture builds
`04fa849e70` and `7e8c8f07a1`. Do not apply its `multiplex_profiles: true` line
blindly to a different Hermes release. In Hermes `8afaab3703` (2026-09-26),
an **unset** root value lets the gateway run a migration preflight and stay
standalone when another profile gateway or a credential conflict blocks
multiplexing. An explicit `true` takes the direct configuration path instead.
It can also make `/p/<profile>/` reachable on the default API listener and
changes profile secret scoping. These are host-wide effects, not HMP settings.

Before changing the root flag on a multi-profile host, review the output of
`hermes gateway migrate --multiplex --dry-run`, the listener exposure, and each
profile's credentials. Resolve any migration blockers through Hermes's own
workflow. HMP may report `not_served` until the topology is safe; do not force
the flag to make the mobile app connect. The routing checklist below describes
the configuration that the older tested HMP fixtures need once the host is
ready to serve those profiles. Check it against the Hermes build in use before
automating it.

## The requirement

For every profile HMP is to serve reads for, the **root** Hermes gateway config needs **both**:

1. `gateway.multiplex_profiles: true` in the **root** `config.yaml` (a routing prerequisite). A
   profile's own `config.yaml` is not part of this requirement: on Hermes
   `ca705dbf7ef86425b381b542712aff310f1ee52c` a multiplexing root serves every live named profile
   without it, and setting it there changes that profile's history namespace (see the version
   note below). The older fixtures did write it per profile; that does not make it universal.
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

Neither setting is supplied by HMP, and `hermes hmp routes add` never turns on root multiplexing. A fresh Hermes install has no HMP
`profile_routes`; an unset multiplex setting may resolve to standalone or
multiplexed mode after Hermes's own preflight, depending on the build and host.
Without a served and routed profile, HMP reads fail closed (see "What happens
if this is missing" below).

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
- **A profile's own `multiplex_profiles` is a separate flag with a session-namespace effect.**
  `gateway/session_recovery.py`'s `_resolve_profile_for_key` (which decides a session key's
  `agent:<profile>` namespace) returns `None` (legacy `agent:main`) when
  `multiplex_profiles` is falsy in the `load_gateway_config()` result for the *current*
  `HERMES_HOME` scope, which, when Hermes work is scoped to a profile's own home, is that profile's
  *own* `config.yaml`, not the root one. `bridge.py`'s read path
  (`gateway.session.build_session_key(source, profile=profile)`, no config dependency of its own)
  looks rows up under `agent:<profile>`.

  **Dated fixture observation (historical, limited).** On the older stock (`04fa849e70`) and
  experimental (`7e8c8f07a1`) builds, fixtures without the per-profile flag wrote sessions under
  `agent:main` and every snapshot/history read came back empty despite real, correctly authorized
  rows, so the fixtures stamp the flag. That is evidence about those builds and fixtures only; it
  does not show the flag is required on any other build, and it does not show it is harmless to
  add where it is absent.

  **Version boundary.** On Hermes `ca705dbf7ef86425b381b542712aff310f1ee52c`
  (`hermes_cli/profiles.py` `profiles_to_serve(multiplex=True)`), serving a named profile does not
  consult the profile's own flag: the default profile plus every live, non-parked, non-standalone
  named profile directory is served. Because the same flag selects the session-key namespace
  above, changing it changes which namespace that profile's history is written to. `routes add`
  therefore leaves every profile config byte-for-byte as it is, and this document makes no claim
  about other builds with or without the flag.

  **Open item (not proven).** Whether a profile without its own flag has readable history through
  the bridge on `ca705` is not established by the Hermes source or the fixtures. Serving and
  routing are covered; which namespace the bridge reads for existing history is not. Route-only
  preparation does not make an older standalone profile's existing history canonical or readable;
  that needs an integration check on a disposable host. See
  `specs/005-new-profile-routing/spec.md` (Open items) and tasks C6.

This is exactly the deployment shape `tools/fixtures/build_fixture.py` writes for every fixture
instance (`_write_config_yaml`, one root `profile_routes` entry per profile; a per-profile
`config.yaml` stamped `gateway:\n  multiplex_profiles: true\n`), and it is what the T035 real
gateway suite runs against. The root `multiplex_profiles` and the route entries are what routing
needs; the per-profile flag in fixtures belongs to the older builds and fixtures described above and
is not claimed to be required, or sufficient, on `ca705`.

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

Creating a Hermes profile does not route it to HMP or authorize any phone for it. Until the host
operator adds its route the bot is `not_routed`. After the initial setup above, from an operator
terminal on the host:

```sh
hermes hmp routes add <profile>
hermes gateway restart
```

The command writes exactly one file: the default root `config.yaml`. It adds the exact route
shown above. The profile's own `config.yaml` is read and checked (path, owner, mode, size,
strict single-document YAML) but never written, backed up or interpreted: its own
`multiplex_profiles` value, whatever it is, is neither required nor changed (see the
history-namespace note above), and existing sessions do not block the command and are not touched. It never authorizes a user or
device, approves a request, enables an API server, provisions a send key, serves or reloads
anything, or restarts the gateway. Afterwards the route is **on disk only**. This command did not
activate it in the running gateway; reload requires a gateway restart on the inspected build.
Sending also needs its separate prerequisites. It is safe to run again.

- It refuses, changing nothing, when the root `gateway.multiplex_profiles` is not already boolean
  `true` (it never turns multiplexing on), when an existing route could overlap the new one
  (broad, user-specific, chat-specific, disabled, `enabled: null`, carrying any extra key, or
  pointing at another profile), when a top-level `profile_routes` exists, when a path is a symlink
  or is group- or world-writable, or when a file is not plain, single-document YAML with no
  duplicate keys or aliases. Only a route that is exactly the one above, with `enabled` absent or
  `true`, counts as already present. Error messages are status-only and never quote config content.
- It never edits or removes an existing route or value. Comments and layout in the root file are
  not preserved. It keeps one private (mode 0600) backup, `config.yaml.hmp-bak` beside the root
  config, replaced on each change, so keep your own copy if you need the original comments.
- Both config files are compared with what was read, after planning and again before the rename;
  a change to either refuses the run. The root is written atomically keeping its original mode.
  If a failure or interrupt arrives once the rename may have happened, the command reports what
  the root file holds (the new route, unchanged, or unconfirmed) and never overwrites another
  writer's edit as recovery. A small same-user race between the final check and the rename
  remains: there is no lock shared with Hermes.
- It runs only under the default profile, from an interactive terminal, and not from a Hermes
  session.

After the restart, authorize the device for the new bot: on the paired phone, request access to
it; then on the host run `hermes -p <profile> pairing list`, check the pending `hmp` row belongs to
that device, and run `hermes -p <profile> pairing approve hmp <request_id>`. See
`specs/005-new-profile-routing`.

## Operator checklist

- [ ] Confirm Hermes's effective gateway topology. On a multi-profile host,
      review `hermes gateway migrate --multiplex --dry-run` before explicitly
      setting `gateway.multiplex_profiles: true` in the **root** `config.yaml` (the routing
      prerequisite; `routes add` never sets it).
- [ ] Root `config.yaml`: one `gateway.profile_routes` entry per profile HMP should serve —
      `platform: hmp`, `profile: <name>`, `guild_id: <name>` (leave `bot_profile` unset: HMP is a
      root-level adapter, so routes apply against the default profile's bot, which is correct).
- [ ] Do not add `gateway.multiplex_profiles` to a profile's own `config.yaml` as part of this
      setup: it is not required to serve the profile on `ca705`, and changing it changes that
      profile's history namespace. Only the older fixtures wrote it.
- [ ] `plugins.enabled` includes `"hmp"`.
- [ ] For a profile created later: `hermes hmp routes add <profile>` (root route on disk only), then
      restart the gateway.

If a bot's roster entry shows `"not_routed"` or `"not_served"` after pairing, re-check this
checklist before assuming a plugin or pairing problem.

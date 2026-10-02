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

For every profile HMP is to serve reads for, the Hermes gateway config needs **both**:

1. `gateway.multiplex_profiles: true` — in the **root** `config.yaml`, and again in **each served
   profile's own** `config.yaml` (`<home>/profiles/<name>/config.yaml`).
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

Neither setting is supplied by HMP. A fresh Hermes install has no HMP
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
- **Each profile's own `config.yaml` ALSO needs `multiplex_profiles: true`.** This is a second,
  separate requirement from the root config's. `gateway/session_recovery.py`'s
  `_resolve_profile_for_key` (which decides a session key's `agent:<profile>` namespace) reads
  `multiplex_profiles` off whatever `load_gateway_config()` sees for the *current* `HERMES_HOME`
  scope — which, when Hermes work is scoped to a profile's own home, is that profile's *own*
  `config.yaml`, not the root one. Without it there, sessions get written under the `agent:main`
  namespace while `bridge.py`'s read path (`gateway.session.build_session_key(source,
  profile=profile)`, which has no config dependency of its own) looks them up under
  `agent:<profile>` — a namespace mismatch that makes every snapshot/history read come back empty
  despite real, correctly authorized rows underneath.

This is exactly the deployment shape `tools/fixtures/build_fixture.py` writes for every fixture
instance (`_write_config_yaml`, one root `profile_routes` entry per profile; a per-profile
`config.yaml` stamped `gateway:\n  multiplex_profiles: true\n`), and it is what the T035 real
gateway suite runs against. It is not a fixture-only requirement: a hand-run Hermes gateway that
skips either part hits precisely the same rejection paths in stock Hermes source described above.

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

## Operator checklist

- [ ] Confirm Hermes's effective gateway topology. On a multi-profile host,
      review `hermes gateway migrate --multiplex --dry-run` before explicitly
      setting `gateway.multiplex_profiles: true` in the root `config.yaml`.
- [ ] Root `config.yaml`: one `gateway.profile_routes` entry per profile HMP should serve —
      `platform: hmp`, `profile: <name>`, `guild_id: <name>` (leave `bot_profile` unset: HMP is a
      root-level adapter, so routes apply against the default profile's bot, which is correct).
- [ ] Each served profile's own `<home>/profiles/<name>/config.yaml`: also
      `gateway.multiplex_profiles: true`.
- [ ] `plugins.enabled` includes `"hmp"`.

If a bot's roster entry shows `"not_routed"` or `"not_served"` after pairing, re-check this
checklist before assuming a plugin or pairing problem.

## Approvals and Phone chat (owner dogfood, spec 034)

Approvals follow the same minimum-version policy as every other HMP feature: HMP attempts them on
Hermes `0.21.5` or later and closes them only when a Hermes API they need is actually missing.
There is no build list, receipt or restart latch to satisfy. The candidate source and the two
prepared native samples have passed their review gates, and an exact owner-local source package
is prepared. Installation and physical card/answer acceptance remain pending; the feature is
not released. Nothing here changes a grant, a config file or a device.

1. **Check availability.** `hermes hmp compat` lists `approvals` and `phone_chat`. `approvals`
   needs read and send. `phone_chat` also needs the Hermes helpers HMP calls in process. Add
   `--verbose` to see whether this Hermes has the Bot Chat session-stream approval hook. That is a
   neutral fact: without it Bot Chat sends still work and Hermes keeps its own fail-closed
   behavior, and no card is shown. Availability is computed when the listener opens, so after a
   Hermes upgrade restart the gateway in the usual drained way and check again.
2. **Record the controls decision first.** An approval owner is a device listed in
   `gateway.platforms.hmp.extra.owner_device_ids` that the host has not explicitly denied. That
   list is the same legacy allowlist the jobs and default-model controls fall back to, so a listed
   device with **no recorded controls decision also receives jobs and model controls**. Before
   adding a device ID, record an explicit decision for it on the host with
   `hermes hmp devices grant-controls <id>`. Approval ownership requires `grant-controls` (or no
   decision, legacy); `deny-controls` removes approval ownership, so a denied device gets 404 on
   every approval route. This coupling is recorded, not removed (HMP v1 RES-13).
   `hermes hmp setup check` prints a read-only notice when active paired devices have no recorded
   decision. It cannot read the config allowlist, names no device and changes nothing.
3. **Then list the device.** Add its ID to `owner_device_ids` through your normal Hermes config
   workflow. HMP reads the live config on each request. Keep `direct_send.enabled` as it is; the
   routes need it. Removing the ID closes the device's next request.
4. **What changes for the phone.** Only a listed, undenied device's guarded Bot Chat send opens
   the session stream and may answer Hermes's own approval card through Hermes's native route.
   Every other device's send is unchanged and synchronous. Phone chat is a separate hand-off with
   its own prompt-only answer route.

To roll back, remove the device ID from `owner_device_ids`. Nothing on disk besides that list needs
undoing.

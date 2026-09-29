# Deploying HMP: gateway routing configuration

This note is for the operator installing the HMP (Hermes Mobile Protocol) plugin into a Hermes
gateway. It covers a **real Hermes gateway-configuration requirement**, not an HMP-side default:
without it, HMP's reads (roster, snapshot, history) for a bot cannot resolve to that bot's
profile at all. It is unrelated to `HOST_HARDENING.md`, which covers exposure of *other* Hermes
host surfaces (`api_server`, the dashboard, `/api/status`); this note covers what HMP itself needs
from the gateway config to route correctly.

## Check the Hermes gateway topology first

The explicit configuration below was qualified on the older fixture builds
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
the configuration that the older qualified HMP fixtures need once the host is
ready to serve those profiles. Requalify it against the exact Hermes build in
use before automating it.

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

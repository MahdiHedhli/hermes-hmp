# Install and pair

## Requirements

- Hermes Agent `v0.21.5` (`v2026.9.24`) is the earliest public tag with both
  Bot Chat reads and guarded sends verified. `v0.21.4` (`v2026.9.21`) passed
  the read checks, but its send path has not been qualified. Installing HMP
  is not blocked by the Hermes version. Pairing and
  Bot Chat access require a qualified bridge build. The exact Omarchy Y520
  commit is also qualified. Older v0.21.x tags need a bridge adapter; newer
  builds are watched but may need HMP updated before pairing works. See
  [the release matrix](RELEASE_COMPAT_WATCH.md).
- Tailscale on the phone and host. The HMP listener accepts loopback and
  Tailscale address ranges; an arbitrary private VPN address cannot bind it.
- Hermes gateway profile routing configured as described in [Deployment](../server/DEPLOYMENT.md).

On a multi-profile host, read Deployment's topology warning before setting
`gateway.multiplex_profiles: true`. That setting can bypass Hermes's migration
preflight and change API ingress and secret scoping on qualified builds.

Install the runtime plugin directory from its public repository. Hermes scans
the selected directory, so this avoids scanning research documents and test
fixtures as executable plugin content. The current runtime scan has two
medium findings for subprocess calls; both use fixed argument lists, no shell,
and bounded timeouts. Review any scanner warning before accepting it. Never
disable the scanner or use `--allow-removed`.

```sh
hermes plugins install 'MahdiHedhli/hermes-hmp#server/hmp_plugin' --enable
```

If an older root-directory HMP plugin is already installed, replace it with
the runtime-only source using the same command with `--force`. This replaces
the old installation; it does not turn off the scanner. Later releases can be
installed with `hermes plugins update hmp`, followed by a gateway restart.
For a fixed, reproducible version, add `--ref <full-commit-sha>` when installing;
a pinned installation must be explicitly reinstalled to move to another SHA.

## Enable the listener

Installing and enabling the plugin is not enough to start HMP. On the Hermes
host, choose an unused port (18741 is an example) and configure the **top-level**
`platforms.hmp` settings. The `gateway.platforms.hmp` spelling is legacy;
Hermes's config CLI writes the canonical top-level path.

```sh
hermes config set platforms.hmp.enabled true
hermes config set platforms.hmp.extra.bind "$(tailscale ip -4)"
hermes config set platforms.hmp.extra.port 18741
```

Before restarting, configure `gateway.multiplex_profiles` and
`gateway.profile_routes` for every bot the phone should use, following
[Deployment](../server/DEPLOYMENT.md). Pairing can succeed without routes,
but the phone's bot-access requests will be refused as `not_routed`; selecting
"Allow all" on the host cannot approve requests that were never created.
Once routing is configured, continue:

```sh
hermes gateway restart
hermes hmp compat
hermes hmp setup check
hermes hmp instance show
hermes hmp pair offer
```

`hermes hmp compat` checks the Hermes build, not whether the listener ran.
If `pair offer` says there is no current instance identity after a restart,
check the three `platforms.hmp` keys and the gateway start log. A successfully
started listener creates the identity. Do not copy an identity or private key
from another host.

For Bot Chat sends and the scheduled-job and default-model previews, each
named profile needs its own `API_SERVER_KEY` in that profile's private `.env`.
Use a distinct value of at least 16 characters for each profile; the default
profile's key does not authorize a named profile. Keep each API server bound to
loopback, keep keys out of source control and support logs, and use the
profile's Hermes configuration workflow to set and rotate them. A missing or
unusable key leaves that bot's write controls unavailable; pairing and reads
can still work.

After the gateway starts, run `hermes hmp health check` to inspect every served
bot's enabled send, jobs, and model prerequisites. The command uses a fresh
gateway snapshot and the same pinned listener check as `setup check`. A missing
profile-scoped key or loopback route makes that bot's enabled channels
unavailable and returns a nonzero exit code; intentionally disabled channels
are reported as disabled. The private snapshot contains only status codes, no
keys or endpoints. Recheck after changing profile configuration and restarting
the gateway. This is a prerequisite diagnostic: device authorization and the
outcome of a later request are checked separately by HMP's routes.

Scan the offer in the mobile app, compare the short security code on both screens,
and confirm on the host. Selecting `y` at **Allow the phone to use all of these?**
selects the profiles to approve; the phone must still send its bot-access
requests. Tap **Request access to all** on the paired phone. The host then
approves the matching pending requests. If `pair offer` prints manual approval
commands, run `hermes -p <profile> pairing list` for each selected profile,
confirm its pending `hmp` row belongs to the just-paired device, and run
`hermes -p <profile> pairing approve hmp <request_id>` for that row. An empty
pairing list means the phone has not sent that profile's request yet; it is
not a request to approve. Never approve another device's pending row. Keep the
offer and approval codes out of logs, screenshots, and support requests.

Pairing asks separately whether this phone may manage scheduled jobs and bot default models. Type `GRANT` on the host to allow those controls; any other answer leaves them off. This decision applies to that device only, even when two phones share an HMP user.

To change that decision later, use `hermes hmp devices list` on the host to find the active device, then run `hermes hmp devices grant-controls <device-id>` or `hermes hmp devices deny-controls <device-id>`. These commands require an interactive host terminal. Revoking the device also stops its privileged access. Do not put device IDs in support reports.

The plugin belongs to the Hermes instance where it is installed. Do not copy its instance keys or device store between hosts. See [Host hardening](../server/HOST_HARDENING.md) before exposing any Hermes host service.

## Scheduled jobs preview

Scheduled jobs are disabled by default. The host must run an exact Hermes build listed in
`server/hmp_plugin/mobile_cron_supported_builds.json`, with a working profile-scoped
loopback API server and key. Grant the specific phone at pairing or with
`hermes hmp devices grant-controls <device-id>`, then set the HMP gateway platform's
`extra.cron.enabled: true` in private host configuration. Do not commit device IDs or API
server keys to this repository. A new job is always created paused;
review it in the app and choose Resume when ready. A timed-out create may have succeeded,
so refresh the list before creating another job.

For new jobs, the phone defaults to this bot's Bot Chat. Choose “Run history only”
when no chat reply is wanted. Continuity lets each run see this job's previous
output. An existing job's result destination does not change until edited. On
the qualified builds, HMP writes create/edit through Hermes's profile-scoped
cron writer because the profile API does not persist `context_from`. This is
bound to the exact build fingerprint and fails closed after an unqualified
Hermes update.

Build `hermes-ca705dbf-git` is newly qualified for the paused-job writer and
routes only: create, list, edit, and delete of paused jobs, profile isolation,
key and permission gates, and corrupt-store failure. See the
[evidence](compat/ca705dbf-mobile-jobs.md). Actual scheduler delivery and
previous-run continuity are not verified on that build; the earlier qualified
builds keep the delivery and continuity checks recorded in their own evidence.

This preview is qualified only for the listed build bytes. Other builds fail closed.
Installing the plugin does not enable the preview; the operator must grant the device and
enable the cron flag. Existing `extra.owner_device_ids` entries remain a legacy fallback;
an explicit host denial for that device takes precedence.

## Bot default model preview

Model management is disabled by default. The host must run an exact Hermes build listed in
`server/hmp_plugin/mobile_model_supported_builds.json`, with its profile-scoped API server
available locally. Grant the phone at pairing or with
`hermes hmp devices grant-controls <device-id>`, then set
`extra.model_management.enabled: true` in private host configuration. The phone
then offers only models from Hermes's authenticated provider catalog for that bot. A model
change affects new sessions and is never retried automatically; refresh the setting after
an uncertain response. Do not commit device IDs, provider credentials, or API server keys.

The preview fails closed on other Hermes builds. Installing the plugin does not
enable it; the operator must grant the device and enable the model flag. Existing
`extra.owner_device_ids` entries remain a legacy fallback, subject to explicit per-device denial.

## Updating a pinned HMP install

`hermes update` updates Hermes core but does not advance a custom HMP Git-SHA
pin. A pinned plugin's `hermes plugins check-updates` result also does not
compare it with newer HMP revisions. Check the public repository and its
release notes explicitly, keep the current installed SHA for rollback, and
review a candidate commit before reinstalling HMP with `--ref <full-sha>`.
Requalify the new Hermes/HMP combination with `hermes hmp compat` and
`hermes hmp health check` after the gateway restarts, then verify a real
client send separately. Do not infer send readiness from a read-only setup
check. A release-aware check and explicit rollback flow are tracked in
[issue #18](https://github.com/MahdiHedhli/hermes-hmp/issues/18).

## Local compatibility tests

Keep source clones of the public Hermes builds in a sibling `_refs/` directory, or pass an explicit path:

```sh
refs_dir="$PWD/../_refs"
builds_dir="/tmp/hmp-builds"
uv run --project server --extra dev python tools/hermes_builds/extract.py --refs-dir "$refs_dir" --out "$builds_dir" --builds stock-base
uv run --project server --extra dev python tools/compat/run_matrix.py --refs-dir "$refs_dir" --builds-dir "$builds_dir" --out /tmp/hmp-matrix --builds stock-base
```

Fixture gateway data belongs in scratch storage outside this repository. Never point tests at your live Hermes home.

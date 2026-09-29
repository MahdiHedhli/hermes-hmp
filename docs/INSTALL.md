# Install and pair

## Requirements

- A current Hermes Agent installation on the host.
- A private network path between the phone and host, such as Tailscale.
- Hermes gateway profile routing configured as described in [Deployment](../server/DEPLOYMENT.md).

On a multi-profile host, read Deployment's topology warning before setting
`gateway.multiplex_profiles: true`. That setting can bypass Hermes's migration
preflight and change API ingress and secret scoping on qualified builds.

Install the plugin from its public repository. For reproducible deployments, add `--ref <full-commit-sha>`.

```sh
hermes plugins install MahdiHedhli/hermes-hmp
hermes hmp compat
```

Configure profile routing using [Deployment](../server/DEPLOYMENT.md), then
start or restart the Hermes gateway. On a build with the setup check command,
run it before creating a pairing offer:

```sh
hermes hmp setup check
hermes hmp pair offer
```

`setup check` reads HMP's build compatibility, current instance identity, and
TLS-pinned listener readiness without changing files or running another
Hermes command. It reports a served-bot count but cannot prove that every bot
is routed, has a usable profile-scoped API key, or grants this device access.
A nonzero result means Bot Chat is not ready; inspect the gateway and the
deployment checklist. A running listener can still pair a device when only
Hermes read compatibility is missing, but the phone cannot use bots and the
pairing command does not grant bot access or owner controls in that state.
Use `hermes hmp compat` to see the reason, then update to a qualified HMP/Hermes
combination and grant bot access separately. Older HMP releases without this command can still use
`hermes hmp compat` and the checklist.

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

Scan the offer in the mobile app, compare the short security code on both screens, and confirm on the host. Then approve only the profiles this device should access. Pairing asks separately whether this phone may manage scheduled jobs and bot default models. Type `GRANT` on the host to allow those controls; any other answer leaves them off. This decision applies to that device only, even when two phones share an HMP user. Keep the offer and approval codes out of logs, screenshots, and support requests.

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
`hermes hmp update check` is a read-only advisory check against the latest
published stable HMP release. It reports the installed and candidate full SHAs,
Git ancestry, and exact Hermes build matches from the release's read, send,
cron, and model compatibility lists. `listed` means the release manifest names
this build; it is not a runtime health result. `unknown` must not be treated as
supported. As of 2026-09-29, no HMP release has been published, so the check
reports that state instead of suggesting `main` as a release.

After reviewing a published release and its commit, save your current SHA and
use `hermes plugins install MahdiHedhli/hermes-hmp --ref <full-sha> --force`
in an isolated Hermes home first. Run `hermes hmp compat`,
`hermes hmp health check`, and a real client send. To roll back, reinstall the
saved full SHA with the same command and recheck those gates. Only then follow
your normal live gateway change process. Requalify after the gateway restarts;
a read-only setup check cannot prove send readiness. This feature is tracked in
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

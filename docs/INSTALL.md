# Install and pair

## Requirements

- Hermes Agent `v0.21.4` (`v2026.9.21`) or later for pairing, Bot Chat reads and
  session browsing. `v0.21.5` (`v2026.9.24`) or later for guarded sends, scheduled
  jobs and default-model management. Later releases and development builds are
  attempted: a feature is turned off only when this Hermes lacks an API it needs,
  not because the build is unlisted. Older v0.21.x tags need a bridge adapter. See
  [the release matrix](RELEASE_COMPAT_WATCH.md) for the builds that were tested.
- Tailscale on the phone and host. The HMP listener accepts loopback and
  Tailscale address ranges; an arbitrary private VPN address cannot bind it.
- Hermes gateway profile routing configured as described in [Deployment](../server/DEPLOYMENT.md).

On a multi-profile host, read Deployment's topology warning before setting
`gateway.multiplex_profiles: true`. That setting can bypass Hermes's migration
preflight and change API ingress and secret scoping.

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

`hermes hmp compat` shows the Hermes version, HMP's minimum versions and whether each
feature is available. It does not check whether the listener ran. If a feature is
unavailable after a real failure, it prints a warning and a hint. To report a failure you
saw on the phone, run `hermes hmp compat --issue-draft --feature jobs --failure-code
cron_unavailable` (use the feature and the code that failed). It prints a GitHub issue
draft to review and paste; nothing is sent, and only the Hermes and HMP versions, the OS
family, the Python version and fixed feature and error codes can appear. With no failure
to report it says so. A permission or setting code (for example `forbidden`) is explained
rather than drafted, because it is not a version problem.
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

A saved grant is only a permission for that phone. It does not enable scheduled jobs or default models, which also need their host feature flags, a Hermes that provides the APIs they need, the profile API and key, and bot authorization. Use `hermes hmp health check` and the preview sections below to check host prerequisites. Health checks do not verify this phone's permission or its bot authorization.

To change that decision later, use `hermes hmp devices list` on the host to find the active device, then run `hermes hmp devices grant-controls <device-id>` or `hermes hmp devices deny-controls <device-id>`. These commands require an interactive host terminal. Revoking the device also stops its privileged access. Do not put device IDs in support reports.

The plugin belongs to the Hermes instance where it is installed. Do not copy its instance keys or device store between hosts. See [Host hardening](../server/HOST_HARDENING.md) before exposing any Hermes host service.

## Host-local generated images (planned, not implemented)

Image delivery does not exist yet; there is nothing to enable for it. The source-reviewed M2 slice
adds `hermes hmp compat` probe eligibility and offline issue drafting only. When delivery is built
(draft contract: [spec 011](../specs/011-local-image-serving/spec.md)), it will be default off and for
approval-owner devices only. It will need the host switch `platforms.hmp.extra.local_media.enabled`, a
Hermes at or above `v0.21.5` (or a development build) that provides the session lookup APIs it reads, and the
usual per-bot authorization. It will not use a build list, fingerprint or qualification manifest, and a
disabled direct-send switch will not close it. The `local_media` compat line is `available` or
`unavailable (<fixed reason>)`; `available` means required APIs passed inspection, not that an image can
be fetched. Compat does not read the host flag or report `disabled`. The runtime binder remains closed;
listener binding, descriptors, fetching and device acceptance are unfinished. The offline issue draft
labels the failure as operator-reported and cannot attest the requester or flag. Assistant `MEDIA:` text
remains ordinary text. No image-delivery review or release is claimed.

## Scheduled jobs preview

Scheduled jobs are disabled by default. The host must run Hermes `v0.21.5` or later (or a
development build) that provides the scheduler APIs, with a working profile-scoped
loopback API server and key. Grant the specific phone at pairing or with
`hermes hmp devices grant-controls <device-id>`, then set the HMP gateway platform's
`extra.cron.enabled: true` in private host configuration. Do not commit device IDs or API
server keys to this repository. Saving the permission does not
turn the preview on. Enable the host flag with
`hermes config set platforms.hmp.extra.cron.enabled true`, then restart the gateway with
`hermes gateway restart`; if jobs or chats are running, wait for the gateway to drain first
so active work is not interrupted. Run `hermes hmp health check` afterward. A phone that
still gets a service-unavailable answer is missing the flag, a Hermes that provides the APIs, the profile
API and key, or bot authorization. A new job is always created paused;
review it in the app and choose Resume when ready. A timed-out create may have succeeded,
so refresh the list before creating another job.

For new jobs, the phone defaults to this bot's Bot Chat. Choose “Run history only”
when no chat reply is wanted. Continuity lets each run see this job's previous
output. An existing job's result destination does not change until edited. On
the tested builds, HMP writes create/edit through Hermes's profile-scoped
cron writer because the profile API does not persist `context_from`. HMP checks
that the writer exists and names its `paused` parameter; it never creates an active
job, and the jobs feature closes alone if the writer is missing.

Build `hermes-ca705dbf-git` was tested for the paused-job writer and
routes only: create, list, edit, and delete of paused jobs, profile isolation,
key and permission gates, and corrupt-store failure. See the
[evidence](compat/ca705dbf-mobile-jobs.md). Actual scheduler delivery and
previous-run continuity are not verified on that build; the earlier tested
builds keep the delivery and continuity checks recorded in their own evidence.

Those results are evidence about the tested builds. They do not decide which Hermes
builds may use the preview; a later build is attempted, and a failure is reported as above.
Installing the plugin does not enable the preview; the operator must grant the device and
enable the cron flag. Existing `extra.owner_device_ids` entries remain a legacy fallback;
an explicit host denial for that device takes precedence.

## Bot default model preview

Model management is disabled by default. The host must run Hermes `v0.21.5` or later (or a
development build) that provides the model reader and writer, with its profile-scoped API
server available locally. Grant the phone at pairing or with
`hermes hmp devices grant-controls <device-id>`, then set
`extra.model_management.enabled: true` in private host configuration.
This is separate from scheduled jobs: enabling one does not enable the other, and model
management is offered only when this Hermes provides what it needs. The phone
then offers only models from Hermes's authenticated provider catalog for that bot. A model
change affects new sessions and is never retried automatically; refresh the setting after
an uncertain response. Do not commit device IDs, provider credentials, or API server keys.

The preview closes on a Hermes that lacks what it needs. Installing the plugin does not
enable it; the operator must grant the device and enable the model flag. Existing
`extra.owner_device_ids` entries remain a legacy fallback, subject to explicit per-device denial.

## Updating a pinned HMP install

`hermes update` updates Hermes core but does not advance a custom HMP Git-SHA
pin. A pinned plugin's `hermes plugins check-updates` result also does not
compare it with newer HMP revisions. Check the public repository and its
release notes explicitly, keep the current installed SHA for rollback, and
review a candidate commit before reinstalling HMP with `--ref <full-sha>`.
Check the new Hermes/HMP combination with `hermes hmp compat` and
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

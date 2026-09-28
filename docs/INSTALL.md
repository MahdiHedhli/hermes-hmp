# Install and pair

## Requirements

- A current Hermes Agent installation on the host.
- A private network path between the phone and host, such as Tailscale.
- Hermes gateway profile routing configured as described in [Deployment](../server/DEPLOYMENT.md).

Install the plugin from its public repository. For reproducible deployments, add `--ref <full-commit-sha>`.

```sh
hermes plugins install MahdiHedhli/hermes-hmp
hermes hmp compat
hermes hmp pair offer
```

Scan the offer in the mobile app, compare the short security code on both screens, and confirm on the host. Then approve only the profiles this device should access. Keep the offer and approval codes out of logs, screenshots, and support requests.

The plugin belongs to the Hermes instance where it is installed. Do not copy its instance keys or device store between hosts. See [Host hardening](../server/HOST_HARDENING.md) before exposing any Hermes host service.

## Scheduled jobs preview

Scheduled jobs are disabled by default. The host must run an exact Hermes build listed in
`server/hmp_plugin/mobile_cron_supported_builds.json`, with a working profile-scoped
loopback API server and key. To enable a specific phone, use `hermes hmp devices list`
locally to find its device ID, then set the HMP gateway platform's `extra.owner_device_ids`
list and `extra.cron.enabled: true` in the host's private configuration. Do not commit
device IDs or API server keys to this repository. A new job is always created paused;
review it in the app and choose Resume when ready. A timed-out create may have succeeded,
so refresh the list before creating another job.

This preview is qualified only for the listed build bytes. Other builds fail closed.
It is not enabled on the owner's live installation by adding these files.

## Local compatibility tests

Keep source clones of the public Hermes builds in a sibling `_refs/` directory, or pass an explicit path:

```sh
refs_dir="$PWD/../_refs"
builds_dir="/tmp/hmp-builds"
uv run --project server --extra dev python tools/hermes_builds/extract.py --refs-dir "$refs_dir" --out "$builds_dir" --builds stock-base
uv run --project server --extra dev python tools/compat/run_matrix.py --refs-dir "$refs_dir" --builds-dir "$builds_dir" --out /tmp/hmp-matrix --builds stock-base
```

Fixture gateway data belongs in scratch storage outside this repository. Never point tests at your live Hermes home.

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
is routed or that a device has access. A nonzero result means pairing is not
ready; inspect the gateway and the deployment checklist. Older HMP releases
without this command can still use `hermes hmp compat` and the checklist.

Scan the offer in the mobile app, compare the short security code on both screens, and confirm on the host. Then approve only the profiles this device should access. Keep the offer and approval codes out of logs, screenshots, and support requests.

The plugin belongs to the Hermes instance where it is installed. Do not copy its instance keys or device store between hosts. See [Host hardening](../server/HOST_HARDENING.md) before exposing any Hermes host service.

## Local compatibility tests

Keep source clones of the public Hermes builds in a sibling `_refs/` directory, or pass an explicit path:

```sh
refs_dir="$PWD/../_refs"
builds_dir="/tmp/hmp-builds"
uv run --project server --extra dev python tools/hermes_builds/extract.py --refs-dir "$refs_dir" --out "$builds_dir" --builds stock-base
uv run --project server --extra dev python tools/compat/run_matrix.py --refs-dir "$refs_dir" --builds-dir "$builds_dir" --out /tmp/hmp-matrix --builds stock-base
```

Fixture gateway data belongs in scratch storage outside this repository. Never point tests at your live Hermes home.

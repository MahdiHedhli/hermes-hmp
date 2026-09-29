# Install and pair

## Requirements

- A current Hermes Agent installation on the host.
- A private network path between the phone and host, such as Tailscale.
- Hermes gateway listener and profile routing configured as described in
  [Deployment](../server/DEPLOYMENT.md).

Install the plugin directory from its public repository. This limits the
installed code and security scan to the plugin instead of the repository's
tests and development tools. Review the scan before accepting it. For a
reproducible deployment, add `--ref <full-commit-sha>` after reviewing that
commit.

```sh
hermes plugins install MahdiHedhli/hermes-hmp#server/hmp_plugin
hermes plugins list
```

Enabling the plugin makes its CLI available, but does not configure or start
its gateway listener. In the root Hermes `config.yaml`, configure a private
tailnet address and an unused port (replace both example values):

```yaml
gateway:
  platforms:
    hmp:
      enabled: true
      extra:
        bind: "100.x.y.z"
        port: 8443
```

Do not bind HMP or another Hermes service to a public or wildcard address.
For named bot profiles, follow [Deployment](../server/DEPLOYMENT.md) for the
additional routes; check the gateway topology before changing multiplexing.
Then, on the host:

```sh
hermes gateway restart
hermes gateway status
hermes hmp compat
hermes hmp pair offer
```

`compat` must report `supported`. HMP refuses to create a pairing offer for an
unlisted Hermes build; restarting again cannot qualify it. A missing instance
identity after a completed restart means the HMP listener did not start. Check
that `plugins list` shows HMP enabled, that the listener configuration above
is present, and that the chosen port is free. This release has no
`hermes hmp setup check` command; use `hermes hmp --help` for the installed
command list.

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

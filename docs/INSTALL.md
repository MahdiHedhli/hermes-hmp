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
hermes gateway restart
hermes hmp compat
hermes hmp instance show
hermes hmp pair offer
```

`hermes hmp compat` checks the Hermes build, not whether the listener ran.
If `pair offer` says there is no current instance identity after a restart,
check the three `platforms.hmp` keys and the gateway start log. A successfully
started listener creates the identity. Do not copy an identity or private key
from another host.

After pairing, use [Deployment](../server/DEPLOYMENT.md) to add
`gateway.profile_routes` for each bot profile the phone should read. The
listener can pair before those routes exist, but Bot Chat reads will refuse
unrouted profiles.

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

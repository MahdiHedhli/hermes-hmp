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

## Local compatibility tests

Keep source clones of the public Hermes builds in a sibling `_refs/` directory, or pass an explicit path:

```sh
refs_dir="$PWD/../_refs"
builds_dir="/tmp/hmp-builds"
uv run --project server --extra dev python tools/hermes_builds/extract.py --refs-dir "$refs_dir" --out "$builds_dir" --builds stock-base
uv run --project server --extra dev python tools/compat/run_matrix.py --refs-dir "$refs_dir" --builds-dir "$builds_dir" --out /tmp/hmp-matrix --builds stock-base
```

Fixture gateway data belongs in scratch storage outside this repository. Never point tests at your live Hermes home.

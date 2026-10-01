# Hermes release compatibility watch

HMP's current bridge uses Hermes internals. A Hermes version number alone does not
establish that profile routing, authorization, Bot Chat reads, or send outcomes remain
safe. Do not add a tag to `read_compat_builds.json` solely because its files exist.

The [scheduled GitHub workflow](../.github/workflows/hermes-release-compat.yml) runs
daily and can be started manually. It reads every published upstream release since
`v2026.8.31` (Hermes v0.21.0), verifies reviewed tag commits have not moved,
then checks the newest release and every new tag against HMP's committed
bridge fingerprints in a disposable runner. The fixture matrix exercises
profile isolation, authorization, Bot Chat
history and mutations, and refusal of an altered unknown build. The workflow uses
no repository secrets or write token; a new tag fails the run until it is reviewed.
Its report is a source and test result, **not an automatic compatibility grant**.

## Baseline found on 2026-09-29

| Hermes tag | Current bridge source shape | Next action |
| --- | --- | --- |
| `v2026.8.31` (v0.21.0) | 8 of 16 files | Legacy adapter and full fixture tests |
| `v2026.9.7` | 15 of 16 files | Legacy adapter and full fixture tests |
| `v2026.9.11` | 15 of 16 files | Legacy adapter and full fixture tests |
| `v2026.9.14` | 16 of 16 files, but missing `_routed_profile_home` dependency | Adapter and full fixture tests |
| `v2026.9.21` (v0.21.4) | 16 of 16 files | Full read fixture matrix passed in isolation |
| `v2026.9.24` (v0.21.5) | 16 of 16 files | Full read and eight-case guarded-send fixture matrices passed in isolation |

The Omarchy Lenovo Legion Y520 owner's 2026-09-29 Git commit
`ca705dbf7ef86425b381b542712aff310f1ee52c` also passed the same isolated
read matrix and unsupported-build refusal. It is a moving main-branch commit,
4,600 commits beyond `v2026.9.24`, not a new release tag. The exact Git
commit and bridge fingerprint are qualified; a later update is a new build.
Its separate eight-case direct-send fixture suite also passed in isolation;
this result is recorded in `direct_send_supported_builds.json`. The guarded
send route now checks that separate list and the additional dependencies
before the owner-enabled send flag can open it.

The August 31 through September 11 tags cannot work with the current bridge by
loosening the version check. They need an adapter that uses their older gateway and
session APIs, with the same authorization and profile isolation assertions as the
current bridge. Track that work in [issue 22](https://github.com/MahdiHedhli/hermes-hmp/issues/22).

For a newly published tag, inspect the workflow's release table and matrix result.
Investigate any failure, qualify the exact release and install form, and then update
the reviewed-tag inventory in `tools/compat/watch_releases.py` and HMP's compatibility
data together. Retest after an upstream change in any fingerprinted file. Do not
silently admit an untested future source layout or turn off the fail-closed gate.

The earliest public tagged build qualified for the current read bridge is
`v2026.9.21`; `v2026.9.24` is the earliest public tag with guarded sends
qualified. The `v2026.9.21` send fixture could not run because that Hermes
source lacks its deterministic fake LLM test fixture; do not infer send support
from the passing read matrix. Persistent host actions keep their separate
host-side gates.

To run the latest-tag matrix locally, keep the upstream source and fixture homes in
scratch storage outside your real Hermes home. The matrix accepts a separately
extracted build with `--candidate-label` and its full `--candidate-sha`; that SHA
records provenance and does not itself enable a build on a live host.

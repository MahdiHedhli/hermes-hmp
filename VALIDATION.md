# Migration validation

The F1 server package in this repository matches the pre-migration private source byte for byte. Its qualified-send build list, including `bridge_files`, is unchanged.

| Check | Result |
| --- | --- |
| Original F1 unit suite | 1,052 passed, 10 skipped |
| Public HMP unit suite | 1,052 passed, 10 skipped |
| Public unit, CI, fixture-tool, vector, and acceptance-tool suites | 1,159 passed, 10 skipped |
| Ruff, plugin surface, log, and zero-baseline privacy checks | Passed |
| Bare-repository plugin install | Passed in a temporary `HERMES_HOME`; dependency resolution and `plugins doctor --ci hmp` passed there |
| Local fixture integration suite | 65 passed, 8 skipped across the extracted stock-base and experimental builds |
| Compatibility matrix | Stock-base and experimental self-checks and read suites qualified; unsupported-build check passed with zero bridge imports |
| Private app suite with public HMP pinned as a submodule | 1,101 passed, 4 skipped across Dart and Flutter packages; private Python acceptance and CI tests: 127 passed |

The plugin installer reports **CAUTION** for the full repository because it scans test tools and documentation alongside runtime code. The [privacy gate](PRIVACY_GATE.md) records the reviewed findings.

## Scheduled jobs branch validation

The additive `feat/cron-mobile` branch keeps scheduled jobs off by default. The
reviewed stock-base Hermes source at `04fa849e70165336ba73e6750257a1ebd7ff998d`
passed 20 upstream API server jobs tests in an isolated home. HMP's own
`test_mobile_cron_stock.py` passed create-paused, list including paused jobs, edit,
resume, pause, and delete against that extracted build. The new cron fingerprint
is independent of the guarded-send fingerprint. A release candidate still needs
the planned independent security and physical-device review before enabling the flag.
The branch's full CI test selection passed **1,170 tests** with **10 skipped**;
Ruff, the plugin-surface check, and the zero-baseline privacy scan passed.
Gitleaks reported six existing fixture/type-check findings and none in the
new cron implementation or docs.

## Guarded-feature integration validation

On `integration/available-features`, HMP's unit suite passed **1,080 tests** with
**10 skipped**. Against the extracted stock-base Hermes build, the scheduled-job
and default-model adapter tests passed, as did four live gateway fixture cases
covering reads, direct send, ambiguous-send reconciliation, and pairing. Ruff,
plugin-surface, log, zero-baseline privacy, and staged secret scans passed.

At commit `fd48b2e`, an install from this repository succeeded into an isolated
temporary `HERMES_HOME` using the extracted stock-base Hermes CLI. Plugin Doctor
passed runtime discovery, import, manifest parsing, and registration. After
enabling HMP in that isolated home, `hermes hmp setup check` reported the
compatible build and correctly refused with `not initialized` before a gateway
start. No live Hermes home was used. The installed tree's guard returned
**CAUTION, 87 findings**, matching the source-tree scan; see the [privacy gate](PRIVACY_GATE.md).

## Bot channel health branch validation

The additive `feat/bot-health-check` branch reports fixed status codes for the
running gateway's served bots. The unit suite passed **1,085 tests** with **10
skipped**; the focused CLI and adapter suite passed **104 tests**. Ruff, the
plugin surface check, log scan, and zero-baseline privacy scan passed. A stale,
incomplete, or malformed snapshot fails closed. The command does not send a
message, transmit a key, add a network route, or change the guarded-send bridge
file set. Its result does not certify a device's authorization or a later
loopback call.
At `e947a10`, eight stock-base direct-send gateway fixture cases passed. An
isolated `HERMES_HOME` install of that exact commit and Plugin Doctor passed;
the installer still reports the documented repository-wide CAUTION findings.
Live host enablement is a separate operator-controlled step.

## Integrated search, health, and host-grant candidate

The draft `integration/release-candidate` branch combines the authorized Bot
Chat start page with bot channel health and host-granted per-device controls.
The full public CI selection passed **1,202 tests with 10 skipped** locally;
Ruff, plugin surface, log scan, zero-baseline privacy scan, and the branch-diff
secret scan passed. The only merge conflicts were documentation rows and the
spec index. This is source and unit/tooling validation. A fresh isolated
gateway fixture run found that the reference pairing client waited at the new
per-device controls prompt. The fixture now explicitly leaves that privilege
off. The expanded real-PTY matrix passed **18 cases**: 9 stock-base and 9
experimental, with 9 owner-local cases skipped because that build was not
extracted here. The added case pairs two devices for one user. Only the device
whose host prompt received `GRANT` passes the per-device jobs/model gate; its
newly created job stays paused. On experimental Hermes, the model route still
fails closed at its separate exact-build gate, while the qualified cron route
works.
The stock read fixture smoke passed, and the real cron/model adapter tests
passed on each extracted build (**2 per build**). Independent source review
and a release build remain open. The candidate has not been installed into
the owner's live Hermes.

## Local fixture builds

The stock-base and experimental Hermes source clones were copied into the new root's `_refs/` directory and extracted to scratch storage outside the repository. The source revisions are `04fa849e70` and `7e8c8f07a1`, respectively. Pairing fixtures require a real PTY, so they run locally rather than in the current GitHub Actions workflow.

The matrix produced candidate read fingerprints `af86c86844fa99fc79a1c77800db0f2b6b20af8735f658cd7df88d2a3faabf2d` (stock-base) and `bfef558e8947f372e960c088057bc0c0b1360a8cc2275532167b915b7ff21ea7` (experimental). It did not change the committed compatibility list. The guarded-send `bridge_files` list and its owner-build fingerprint remain unchanged in the initial migration.

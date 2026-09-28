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

## Local fixture builds

The stock-base and experimental Hermes source clones were copied into the new root's `_refs/` directory and extracted to scratch storage outside the repository. The source revisions are `04fa849e70` and `7e8c8f07a1`, respectively. Pairing fixtures require a real PTY, so they run locally rather than in the current GitHub Actions workflow.

The matrix produced candidate read fingerprints `af86c86844fa99fc79a1c77800db0f2b6b20af8735f658cd7df88d2a3faabf2d` (stock-base) and `bfef558e8947f372e960c088057bc0c0b1360a8cc2275532167b915b7ff21ea7` (experimental). It did not change the committed compatibility list. The guarded-send `bridge_files` list and its owner-build fingerprint remain unchanged in the initial migration.

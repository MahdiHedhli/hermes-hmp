<p align="center"><img src="assets/icon.png" alt="HermesBot Mobile icon" width="104"></p>

<h1 align="center">Hermes Mobile Plugin</h1>
<p align="center">A self-hosted, device-paired mobile gateway for <a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a>.</p>
<p align="center"><a href="https://hermes-bot.app">hermes-bot.app</a> · <a href="FEATURES.md">Features</a> · <a href="HermesUnifiedGatewayResearch.md">Gateway research</a> · <a href="NOUS_GATEWAY_OBSERVATIONS.md">Requests for Nous</a> · <a href="https://gist.github.com/MahdiHedhli/c8d01a96bdfc794edaf7c3e1f4cb1502">Nous Gist</a></p>
<p align="center"><a href="https://github.com/MahdiHedhli/hermes-hmp/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MahdiHedhli/hermes-hmp/actions/workflows/ci.yml/badge.svg"></a> <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white"> <img alt="Hermes plugin" src="https://img.shields.io/badge/Hermes-platform%20plugin-343A40"> <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/License-MIT-2ea44f"></a></p>

HMP runs inside your own Hermes gateway. It pairs each phone to an instance, serves bot and Bot Chat reads, and supports guarded Bot Chat sends on qualified Hermes builds. The iOS and Android apps live in a separate private repository.

## Install

```sh
hermes plugins install MahdiHedhli/hermes-hmp
hermes hmp pair offer
```

Hermes may ask you to confirm its community-plugin scan findings; the full-tree verdict is recorded in the [privacy gate](PRIVACY_GATE.md). The operator confirms the matching code shown on the phone and host. See the [install and host configuration guide](docs/INSTALL.md) before connecting a device. Use `--ref <full-commit-sha>` to pin a reviewed revision.

| Start here | Purpose |
| --- | --- |
| [Features](FEATURES.md) | Available, preview, and planned capabilities |
| [Roadmap](ROADMAP.md) | Current priorities and gateway adoption gates |
| [Unified gateway research](HermesUnifiedGatewayResearch.md) | Nous's proposed shared session authority and mobile implications |
| [HMP v1 contract](docs/architecture/contracts/HMP_V1.md) | Wire protocol and security boundaries |
| [Deployment](server/DEPLOYMENT.md) | Hermes profile routing requirements |
| [Host hardening](server/HOST_HARDENING.md) | Network exposure guidance |
| [Upstream observations](NOUS_GATEWAY_OBSERVATIONS.md) | Reviewable requests for Nous Research |
| [Contributing](CONTRIBUTING.md) | Development and review workflow |
| [Feature specs](specs/README.md) | Spec Kit workflow and migration plan |
| [Privacy gate](PRIVACY_GATE.md) | Public migration scan and installer verdict |
| [Validation](VALIDATION.md) | Test counts and isolated install result |

## Repository

`plugin.yaml` and `__init__.py` at the root are the install entry point. The unchanged HMP implementation and tests are in `server/`; fixture, vector, and compatibility tools are in `tools/`. Hermes installs the repository root for the bare command above.

HMP registers one platform adapter and one operator CLI. It does not register agent tools or hooks. Unsupported Hermes builds fail closed for guarded operations. See [SECURITY.md](SECURITY.md) for reporting and the threat model.

## Development

```sh
uv run --project server --extra dev pytest server/tests/unit
uvx ruff==0.16.9 check --config server/pyproject.toml server tools
python3 tools/ci/check_plugin_surface.py
python3 tools/ci/scan_private.py
```

Compatibility and fixture tests require extracted Hermes builds; see [CONTRIBUTING.md](CONTRIBUTING.md). The [migration inventory](MIGRATION_INVENTORY.md) records the source disposition.

Licensed under [MIT](LICENSE).

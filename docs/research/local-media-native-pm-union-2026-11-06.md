# Native PM dependency-union sample — 2026-11-06

The shipping root manifest at HMP `4bab0cd68e25019593484604cae6b22c4b8636a7`
declares `aiohttp>=3.14.5,<4`, `qrcode>=7.4.2,<9` and `PyYAML>=6,<7`.
One fresh disposable build resolved and installed that complete declaration
alongside the base native dependency graph for Hermes
`ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`.

## Method and observed result

The version-matched native declaration reader and workspace generator produced
one dependency-only virtual member. Its input directory contained only the
exact shipping `plugin.yaml`, SHA-256
`a904d395310948a7e82ea7a91796a66590fd7981def6d6d408c72e47073f567f`.
No plugin pyproject, build backend or executable code was admitted. The generated
member had only dependency metadata with `tool.uv.package = false`.

Native `pm.build_environment` then built and validated a fresh environment from
that generated workspace. Resolution was permitted only in this writable
snapshot; 12,189 original native source/auxiliary inputs remained unchanged.
The original core project was excluded from installation. No profile discovery,
plugin activation, live environment selection or installed gateway update ran.
Clean homes, runtime, cache and temporary paths were confined to a private
canonical owner-only directory. Normal package-manager index/download and build
behavior is trusted; this is not an OS sandbox or package-code attestation.

The terminal build exited 0. A separate metadata read observed:

| Component | Resolved version |
|---|---|
| Python | 3.14.9 |
| aiohttp | 3.14.5 |
| qrcode | 7.4.2 |
| PyYAML | 6.0.3 |
| cryptography | 50.0.2 |

The generated lock SHA-256 is
`0669d0debf4ae6e1b7f447fb471ac89e1eeb1155071a0af91eb80b5d53751b79`.
Private evidence under `hermes-media-pm-union-attempt2-20261106` preserves the
exact binding, command/terminal status, stdout/stderr, result, versions,
generated manifest/lock and a nine-file SHA/size manifest. Independent read-only
review accepted the harness and all nine artifact hashes/sizes/private modes,
the unchanged 12,189 source hashes, virtual member, resolved lock, installed
package metadata and interpreter metadata. There is no Hermes/HMP distribution
installed in the environment. The reviewer performed no execution.

## Preserved setup refusal and limits

The first attempt exited 1 at its environment allowlist, before native imports
or dependency work: Darwin injected `__CF_USER_TEXT_ENCODING` into the otherwise
explicit environment. A names-only interpreter control identified that sole
extra key. The reviewed correction removes it before the same strict allowlist;
the successful attempt used a separate fresh root. The failed attempt remains
preserved and is not counted as a passing build.

This closes the sampled shipping dependency-union build gap. It does not prove
full plugin installation/loading, all extras or other plugins, the core package
build, any older/newer native revision, Linux, device behavior, activation or
release readiness. It does not replace the separate cache-helper/HTTP sample or
native four-fetch cost/T12 measurement. Actual image-provider generation and
deferred/Desktop production scope remain unqualified. No dependency limit,
runtime eligibility policy, permission, provider or live setting changed.

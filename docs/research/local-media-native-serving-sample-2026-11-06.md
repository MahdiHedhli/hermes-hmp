# Bounded native local-image serving sample — 2026-11-06

One fresh Darwin sample completed on HMP
`3d7d08c94d5321a52bcb6404278d3ac6fe9a44a0` and native Hermes
`ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`. This verifies scratch native
storage/registry with the real descriptor and image-fetch routes. It does not
qualify a running gateway, actual image producer, phone display, Linux, T12,
production activation or release. Routing, owner/bot authorization and
compatibility are explicitly synthetic.

## Observed behavior

The sample seeds `image_generate` assistant/tool rows through native SessionDB's
public methods and creates tiny static PNG files in the private fixture cache.
It uses real HMP descriptor minting and authenticated HTTP image fetches.

| Control | Observed result |
| --- | --- |
| Original eligible device and its image reference | Exact PNG bytes, MIME/length, private no-store and nosniff headers; forbidden headers absent |
| Second eligible device and its own minted reference | Exact PNG bytes; positive control before cross-device rejection |
| Second device using the first device's reference | 404 |
| Authorized alternate profile using the original reference | 404 |
| File replaced after a first successful serve, before the next fetch | 404; replacement cannot change an existing reference's served digest |
| Bot access revoked between phase one and phase two | 404; the mutation callback ran |
| Original message rows cleared before a subsequent fetch | 404 |
| Fresh tool row after the clear | New descriptor and successful fetch |
| Original device revoked before fetch | 401 |

The first phase copies and validates the image. Phase two refreshes authorization,
eligibility and tip; it does not re-read an individual row or file. A late file
edit can therefore leave an in-flight request serving its already copied bytes.
That behavior was measured in a preserved failed fixture expectation and matches
[the established contract](../../specs/011-local-image-serving/ROOT_DECISIONS.md).
No atomic snapshot or late-row/file revocation guarantee is added.

## Resource and source evidence

- 25 native registry acquires and 25 releases; the original scratch native database
  closed, with a scoped post-cleanup sweep of zero.
- The listener and all owned media workers closed/joined. No observation timeout
  or settlement-only path occurred.
- Eleven recorded commands were terminal: nine exit 0 and two expected exit-1
  absent-config probes. The outer controller separately exited 0.
- 12,185 native and 368 HMP/test source-file hashes matched before and after.
  Exports were checked against literal committed Git blob contents and modes;
  replacement objects, lazy fetches and network protocols were disabled.
- The selected PM environment used Python 3.14.9, aiohttp 3.14.5 and pytest 9.1.1.
  Native source/lock inputs stayed unchanged. Each output environment was fresh;
  no existing application environment was modified.

The private `hermes-local-media-native-serving-proof-20261106.json` binds the
receipt, report, source manifest and 28 top-level artifacts by hashes, sizes and
0600 modes. These are selected source/runtime observations, not loaded-code or
platform attestation. Independent read-only artifact review accepted these bindings and observations;
the reviewer executed no test or native command. A separate 320-case
descriptor/fetch/guard regression passed on Python 3.14.9 and aiohttp 3.14.5
in 23.40 seconds. Those synthetic/portable cases are not 320 native runs.

## Disclosed fixture OS allowances

The sample is not an OS sandbox. Selected dependencies/site startup and the OS
remain trusted premises. Its Python audit guards retain the following explicit
exceptions while protecting live homes and unrelated files:

- 28 counted synthetic absences for exact Linux `/proc` probes on Darwin,
  including only the current process's start-time path and its descriptor listing.
  These return file-not-found without opening those outside paths.
- Three real names-only listings of `/dev/fd` for this fresh child's descriptors.
  Native SQLite descriptor ownership and headroom checks remain active. The
  4,096-listing cap is enforced before each listing; no descriptor bytes are
  granted by this exception.
- Two bounded read-only accesses to the canonical root-owned, regular, single-link,
  non-writable public SystemVersion plist. Its observed final SHA-256 was
  `6151cb883e5b48d43a33d4d41956405a1cd502e0c8622319388d943e2cb804a1`.
  Consistent earlier contents rely on OS-root immutability; the final hash alone
  does not prove every earlier read saw those bytes.
- MIME initialization uses built-in tables only, with no host MIME file or registry
  import. Exactly `:memory:` is permitted for native schema comparison; shared
  memory URIs and unrelated database paths remain refused.

There were zero **unexpected** audit denials, not zero outside-path attempts.
Directory hardening was not skipped. No live grant, provider, host flag, gateway
or app deployment changed.

## Preparation failures preserved

The private attempt census keeps 13 terminal attempts, exactly one validated
completion. Earlier failures remain failures: archive framing overhead; missing
ruamel, pytest and aiohttp; host MIME import; native in-memory schema setup;
incorrect synthetic authorization setup; unsupported late-file/row expectations;
and final containment diagnostics. Constructor-stage failure proves process
termination, not explicit native-close success. Later success does not qualify
those older exact sources.

## Remaining work

Native serving/cost and provisional T12 memory/deadline gates, broader Linux
coverage, current producer/cache qualification, full plugin-PM dependency-union
installation, and physical phone rendering remain open. This sample is not a
Hermes version allowlist and does not change minimum-version/API eligibility.

The clean-host attempt also exposed an HMP packaging omission: aiohttp is now
optional in Hermes base. HMP PR126 declares `aiohttp>=3.14.5,<4` in both shipping
manifests and server metadata; only that dependency changed in the server lock.
The native PM declaration reader recognizes both declarations. The sample's
HTTP library was installed through the pinned native library-only `sms` extra;
no SMS service was configured. That setup does not prove complete plugin-union
installation. The source dependency repair also avoids the old 3.14.3 version's
[published advisory range](https://github.com/aio-libs/aiohttp/security/advisories/GHSA-9xw5-w5jj-pvcg).

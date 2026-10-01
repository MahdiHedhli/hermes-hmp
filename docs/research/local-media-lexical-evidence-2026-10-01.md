# Local generated media: lexical image-prefix evidence (2026-10-01)

Root-reviewed research evidence. Not a design, not a wire shape, not a qualification. No media
reference, route, token, manifest, serving path or product code is introduced. The G1 persistence note
(`local-media-g1-persistence-2026-09-30.md`) and the census note are not edited. Root acceptance is limited to the producer-string observation on the exact build below; no serving qualification is granted.

## What is new, and what the older evidence was

| Evidence | Comparison | Scope |
| --- | --- | --- |
| Older (G1 note): `image_in_selected_profile_cache` | `Path(image).parent == <scratch>/cache/images`, where the expected path is built by the fixture from its own layout | Path-object equality. Insensitive only to repeated separators and `.` segments, which `Path` collapses. It does not ignore an equivalent symlink spelling and does not normalize `..`; those compare unequal |
| New: `lexical.*` | the RAW `image` string from the persisted tool row `startswith` `str(GatewayRunner._routed_profile_home(profile)) + "/cache/images/"`, remainder one flat bounded name | Plain string comparison. The expected prefix comes only from the native helper, never from the producer string, `Path.resolve`, `realpath` or any normalization |

The new check reports `old_parent_evidence_agrees` (older boolean equals the lexical verdict) so the two
stay distinguishable in one report. Agreement in the runs below is an observation about one clean
scratch layout; it does not show the two checks are equivalent.

## Binding

| Item | Value |
| --- | --- |
| HMP worktree | `docs/local-media-delivery-discovery`, base `5a688c7`, reviewed bounded research extension |
| Hermes build | independent git checkout at `8afaab3703e336d72a72c812dd2dd249f04f166a`, tree clean before and after, 16 owning files unchanged |
| Helper call path read | `gateway/run_adapters.py` `GatewayRunner._routed_profile_home` (staticmethod) returns `hermes_cli.profiles.get_profile_dir(name)` (a `Path`), or the `UNRESOLVED_PROFILE_HOME` sentinel on any exception |
| HMP mirror | `server/hmp_plugin/bridge.py` `Bridge._profile_home` calls the same helper and accepts only a `str`/`PathLike` whose `Path` is absolute (`_as_path`); anything else is `BridgeError`. The fixture applies the same acceptance (`lexical_prefix`) and records `bridge_shape_equals_native_str`: `str(Path(value))` equals `str(value)` for the helper result |
| Isolation, network, deadline | unchanged from the G1 note: scratch `HOME`/`HERMES_HOME`, allow-list environment, IP and Unix denial in the child, 120 s hard timeout per scenario, no retry |
| Scenarios run | `desktop`, `phone`, `desktop_deferred` only. Failure-injection scenarios and the broad matrix were not run for this fact |

## Observed (one synthetic turn per scenario, one profile pair)

Real `agent.image_gen_provider.save_b64_image` through the synthetic provider; real `AIAgent` and
`SessionDB`; the helper called inside the child under the same scratch home as the turn. Closed booleans
only (no path, prompt, session, device or content in stdout or this note).

| Fact | desktop | phone | desktop_deferred |
| --- | --- | --- | --- |
| scenario completed | yes | yes | yes |
| helper evidence gap | none | none | none |
| helper result type | `PosixPath` | `PosixPath` | `PosixPath` |
| bridge-shaped string equals native string | yes | yes | yes |
| selected and other profile prefixes differ | yes | yes | yes |
| raw image starts with selected-profile prefix | yes | yes | yes |
| raw image starts with other-profile prefix | no | no | no |
| suffix is one flat bounded name (36 chars) | yes | yes | yes |
| lexical verdict accepted | yes | yes | yes |
| older `Path(parent)` boolean agrees | yes | yes | yes |
| IP connects refused (parent denial unchanged) | 4 | 0 | 4 |
| Unix contacts refused | 0 | 0 | 0 |
| scratch removed, stderr mentions scratch | yes, no | yes, no | yes, no |

Per-run raw-value and expected-prefix SHA-256 digests are not retained: the per-run evidence was
deleted, so no digests exist in the private report. They varied with the random scratch root and were
never stable identifiers. The observed run results above are worker observations, not accepted evidence.

## Negative tests (no native build needed)

Explicit unit tests assert refusal for: prefix spelling mismatch (missing, doubled or extra separator,
`.` and `..` segments, case change, relative spelling, an equivalent but different absolute spelling,
empty name); nested suffix, `..`, separators, backslash, NUL, control characters and an over-bound name
(128 encoded bytes, inclusive, matching `MAX_NAME_BYTES` in `local_media_file_safety.py` and spec 011); a foreign profile's prefix; non-string values; and a missing expected
prefix, which is a gap and not a pass. A symlink spelling and a `cache/../cache` spelling that
`os.path.realpath` shows resolve to the same file are both refused, so normalization cannot rescue a
mismatch. A source check asserts the observation function never calls `resolve`, `normpath`,
`realpath`, `abspath` or `Path(`. Helper import failure and a sentinel result are recorded as closed gaps
(`helper_error:<type>`, `helper_result_not_absolute_path`), never defaulted.

## Limits (not claimed)

- Not a live HMP endpoint, not the qualified manifest or contract, and not HmpAdapter or `Bridge`
  exercised: the helper is the native staticmethod called directly; `Bridge._profile_home` was read and
  mirrored, not run. The Phone path is the stand-in adapter described in the G1 note.
- The synthetic provider calls the real `save_b64_image`; its result string is what was compared. Other
  providers or tools that write a path some other way were not observed.
- One build (`8afaab37`), one clean absolute scratch layout, two profiles named `alpha` and `beta`.
  Layouts where `HERMES_HOME` is spelled through a symlink, a trailing separator, `default` profile
  routing, or a profile directory that is later renamed are not characterized: the lexical check might
  refuse them, which is the intended fail-closed direction, but that was exercised only by pure
  string tests, not natively.
- A lexical prefix is not file safety: it says nothing about symlinks, hardlinks, file type, size or
  the file being present at serving time. A later open still needs its own descriptor-level checks.
- Persistence order, failure and history findings of the G1 note are unchanged and were not re-run.
- Network denial is Python-level, not an OS sandbox.

## Root verification (2026-10-01)

Root corrected the candidate filename limit to the frozen 128-byte bound and corrected the older
Path-equality description. The worker’s original native evidence had been deleted, so root repeated
only the three positive native scenarios, retaining the private report and closed metadata. All three
completed with the selected-prefix comparison and single flat name accepted, the foreign prefix
refused, the helper available, the bridge-shaped/native strings equal and native source unchanged.
The exact native pin and clean tree were checked before and after.

Root also passed 34 lexical unit cases and 3 native-helper shape/gap cases; explicit candidate privacy
scanning passed. Pytest emitted cache/old temporary-directory cleanup warnings; no test failed.
The reviewed fixture SHA-256 is `5946c61de495a8ebef49808b4a7f6d03d08ae5d07a8a75ecc41ffe3a2657b759`.
Retained root native report SHA-256: `f2fd2d324507f06f807ccc8b3a6e71af3c5aad3279271bffad6b33fbf1e709f0`.

This closes E1 for the stated exact build, producer and scratch layout. It does not qualify a live
media route, other provider path spellings, Linux file behavior or a phone build.

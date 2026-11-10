## Current upstream revalidation — November 10, 2026

Inspected immutable Hermes main `e0f07847b8f38ac72890cf98e0d344c372ae7ee8`.
`tui_gateway/methods_profiles.py` blob
`5baf116f31e5757f07c6d1aae332aa9c5019e3de` still has no narrow
presentation-only contract in the inspected profile-list path:

- `profiles.list(include_sessions=False)` omits session decoration, but still
  invokes `list_profiles(lazy_skill_count=True)` and `_profile_ui_meta_fields`.
- `hermes_cli/profiles.py` blob `c7d9c6b5f309eabb448d843163c296c22eeb99fc`
  builds each row through `_profile_info`, reading model/provider configuration,
  distribution metadata, wrapper/process state, environment-file existence and
  cached skill count. Filtering its output afterward does not undo those reads.
- `_profile_ui_meta_fields` reads/caches profile YAML and probes avatar files.
  `read_profile_meta` exposes display name/title but not shape/color/character;
  its missing/unreadable fallback conflates failure with empty metadata.

This rules out claiming the broad roster call is the required narrow adapter;
it does not prove an upstream change is necessary. The HMP-owned bounded reader
and existing projection remain candidate mechanisms. Any metadata-first wiring
must explicitly distinguish unavailable presentation from absent avatar, retain
revision/currentness/revocation, and keep full bitmap delivery on the roadmap.
Do not advertise a character capability before the actual native service and
authenticated route are integrated and tested. No profile/config/asset data from
a live home was read; no upstream or installed software was changed.

## Native avatar interface audit — November 7, 2026

Source audit on Hermes `ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`:
Desktop's legacy `profiles.get_asset` returns an avatar data URL. This is not
proof of an HMP-safe reader or a supported canonical asset RPC. Its local Desktop
trust boundary does not establish paired-phone/profile authorization, bounded
pre-read work, revocation, cleanup or image validation. The setter's constraints
are not a substitute for reader qualification. No live asset or private content
was read during this audit.

The canonical roster includes `has_avatar` and presentation metadata, but roster
presence is not an asset-byte delivery contract. Do not import/rebind the legacy
server, expose its general RPC transport to phones, forward phone-selected paths,
or infer authorization from an avatar flag. Retain HMP's authenticated scoped
presentation route and complete its runtime integration; this audit does not
justify waiving the accepted broker/startup/cleanup requirements. Native source
security concerns are recorded privately rather than published as exploit detail.

User-visible status: desktop character/avatar delivery remains unfinished;
source helpers and this audit do not mean an image appears on an installed phone.
Host-local chat images remain a separate feature with deployment and physical
qualification outstanding. The next implementation must complete an actual
original runtime/native acceptance path, not report another DATA helper as BI1.

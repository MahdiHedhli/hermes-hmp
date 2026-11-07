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


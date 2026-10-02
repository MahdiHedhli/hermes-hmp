# Routing command review

## Status

**Root code and documentation review complete; host qualification open.** The current root-only candidate has had an Opus review of the
code (approved; no critical or high finding; `test_routes.py` 138 passed) and an independent root
CI run (1322 passed, 10 existing skips, 1 existing warning; pinned Ruff clean). Its three findings
were addressed in wording only: (1) DEPLOYMENT's per-profile-flag evidence is scoped to older
builds and fixtures, and history readability of a flag-less profile on `ca705` is recorded as an
open item (spec "Open items", tasks C6), not proved; (2) the on-disk-only message no longer says
"served/send-ready until restart"; (3) the interrupt scope is documented as handled during the root
write, with backup-write interrupts changing no config and a second interrupt able to prevent
the final-state report after the root may already have changed. The same-user
editor race stays accepted and documented. Root reviewed the final wording and independently
passed all 138 route tests after the CLI wording repair; pinned Ruff, plugin surface, privacy
and diff checks passed. This is not a release certification. It supersedes the design described
in the historical section below.

Reviewed boundary and remaining integration item:

- The candidate removes every profile write (the earlier design set the profile's own
  `gateway.multiplex_profiles`, which on `ca705dbf7ef86425b381b542712aff310f1ee52c` is not needed
  to serve the profile and changes its history namespace). Root checked that the root write path, its
  unchanged-checks, the content-free final-state report, and the retained refusal rules match
  `spec.md` R1-R13.
- Open: `ca705` history readability without the profile's flag (not proved). The counts in the
  historical section below do not apply to this candidate.

Unchanged limits: same-user races between the final check and the rename remain and no lock is
shared with Hermes; the rolling private backup is replaced on each change and re-emitting YAML
drops comments and layout; Windows owner/mode verification is not validated; the command writes
configuration only (no grant, approval, restart or `.env` access); the route is on disk and needs a
gateway restart, and end-to-end behavior and PyYAML acceptance by the Hermes plugin manager are
untested on a disposable host. Older builds' treatment of the per-profile flag and of existing
history is not established.

## Historical: review of the superseded two-file design

The text below records a review of the earlier implementation. It is superseded, is not evidence for
the current candidate, and its test counts are void for it.

- Root multiplex activation: removed. The command requires existing explicit root multiplexing.
- Disabled/null and narrowed existing routes: refused; no route replacement or widening.
- Both original configs: checked before backups and again before configuration writes.
- Interrupted two-file and root-only writes: final state reported, conditional profile restore,
  exit 130. (Superseded: there is no profile write or restore now.)
- Pre-write emission/read failures: status-only refusal, no configuration content in errors.
- New profile serving: documentation distinguished eligible gateway discovery, HMP routing and
  device authorization, and (superseded) described the per-profile namespace consequence of a flag
  the command then wrote.

Earlier local evidence, for the superseded design only: 1,318 tests passed, 10 skipped; pinned Ruff
0.16.9 lint, the plugin surface check and the public privacy scan were clean. Its upstream source
scan of `ca705dbf7ef86425b381b542712aff310f1ee52c` confirmed an exact HMP guild route selects the
intended profile and an explicitly null `enabled` route does not match.

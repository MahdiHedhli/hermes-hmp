# Routing command review

## Findings and disposition

The implementation received independent Opus review and bounded Sonnet repairs.

- Root multiplex activation: removed. The command requires existing explicit root multiplexing.
- Disabled/null and narrowed existing routes: refused; no route replacement or widening.
- Both original configs: checked before backups and again before configuration writes.
- Interrupted two-file and root-only writes: final state reported, conditional profile restore,
  exit 130. The root-only case identified in follow-up review has dedicated tests.
- Pre-write emission/read failures: status-only refusal, no configuration content in errors.
- New profile serving: documentation distinguishes eligible gateway discovery, HMP routing and
  device authorization, and explains the legacy per-profile namespace consequence.

The root architect checked the final bounded repair against the review's causal findings and
reran the repository's CI-equivalent local suite. This supports a draft code review; it is not
a release or a physical-device acceptance claim.

## Final local evidence

- 1,318 tests passed; 10 skipped. One existing aiohttp subclass deprecation warning.
- Pinned Ruff 0.16.9 lint across `server` and `tools`: passed.
- New routing module and its tests: format check passed. An unrelated existing formatting
  difference elsewhere in the CLI was left unchanged.
- Closed plugin surface check: passed.
- Public privacy scan: clean; diff whitespace check passed.

The inspected upstream reference is `ca705dbf7ef86425b381b542712aff310f1ee52c`.
Its actual route matcher confirmed an exact HMP guild route selects the intended profile and
an explicitly null `enabled` route does not match. A temporary candidate runtime passed that
revision's plugin scanner with a `safe` verdict; this was a source scan, not installation.

## Remaining release gates and limits

- Test dependency admission by Hermes PM in an isolated install.
- Test the command plus gateway restart plus new-profile access end to end on a disposable host.
- Same-user final check/rename races remain documented; no shared lock with Hermes is claimed.
- The private backup is rolling and re-emitting YAML drops comments/layout. Operators must retain
  their own original copy if they need comment history across multiple route additions.
- Windows owner/mode verification is not equivalent to POSIX verification; it is not validated here.
- The command prepares configuration only. Access still requires a phone request and separate
  host approval. It never approves users, restarts a gateway or changes API server settings.

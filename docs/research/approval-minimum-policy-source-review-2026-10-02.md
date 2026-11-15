# Approval minimum-policy source review — 2026-10-02

Root accepted spec 034's converted source after independent Opus review of the merge,
exclusions, runtime gates, native transport selection and failure classification. The candidate
branches from `4d6863e`, merges the earlier approval integration, and excludes its new-bot config
writer, package editor and exact-build admission machinery. Intermediate commits are not deployable.

Bot Chat and Phone chat have separate availability members. Version floors and actual required
APIs govern support; later and unknown builds are attempted. Owner allowlisting, host controls
denial, bearer validation, per-bot authorization and native answer authority remain enforced.
Non-owner sends retain the synchronous path. Missing or malformed native answers cannot become
successful approval receipts. Closing a local Phone generation does not attest native expiry.

The independent reviewer passed 836 focused tests with ten fixture skips and inspected the
security mutations. Root reviewed the subsequent wording/test delta, passed 222 focused tests,
and verified three causal failures: oversized answer body, closed Phone generation and absent
Phone helper availability. Privacy and plugin-surface checks passed on the final source.
These are source checks, not real gateway or device results.

The optional fixed-log omission for an invalid Phone event helper remains a recorded nit; the
operation still closes with an unavailable result. The separate device-list and scoped-key
findings remain unresolved and are not waived by this review.

**Open gates:** T14's real gateway samples and Phone probe; T15's owner-local package; running
host activation; physical cards and answers. A sample must use a supported interpreter and its
locked dependency environment. A prepared floor source on a newer, out-of-range interpreter
does not establish release-floor behavior. No live grant, configuration, plugin or phone was
changed by source acceptance. Priority notifications and broader cross-channel coverage are
separate unfinished work.

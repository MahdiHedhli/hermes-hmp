# Reviewed HMP release check

Status: implementation candidate. GitHub has no published `hermes-hmp` release yet;
the first real comparison must wait for a reviewed release tag.

## Operator outcome

`hermes hmp update check` reports the installed HMP Git pin, the latest
published stable release's exact commit, whether the release is ahead of the
installed pin, and which exact Hermes bridge manifests list the running build.
It does not install, restart, or configure anything. It gives a manual review,
install, verification, and rollback path.

## Requirements

- Use only the fixed public GitHub API repository and bounded unauthenticated
  requests. Never send profile, device, key, chat, or hostname data.
- A tag resolves to an immutable commit SHA, including annotated tags. A
  differing SHA is not automatically called newer: compare ancestry first.
- A 404 from the latest release endpoint says no release; rate limits, network
  failures, malformed data, and unresolvable tags are visible unknown/failure
  states. They never select a candidate silently.
- Evaluate release compatibility manifests as data only. A listed build is an
  advisory match, not a runtime guarantee. Unknown data stays unknown.
- Release data cannot name arbitrary local files, redirect HTTP requests, or
  execute candidate code. The CLI may run without a TTY or gateway and does not
  open the writable HMP store.
- The installed full SHA remains available to the operator for rollback. A
  release must still be reviewed and installed using an explicit full SHA.

## Acceptance

Offline fixtures cover no release, lightweight/annotated tags, exact comparison,
candidate manifest matches, malformed metadata, path traversal, and CLI
read-only behavior. Before promoting a real release, use an isolated Hermes home
to install the full SHA, check `compat` and per-bot `health`, verify a client
send, then reinstall the previous SHA and repeat those checks.

# Public HMP extraction

## User story

As a Hermes operator or contributor, I can review, install, test, and improve the HMP plugin from its own public repository with one bare `hermes plugins install owner/repo` command.

## Acceptance scenarios

1. The repository root is a valid Hermes plugin with one platform and one operator CLI registration.
2. The plugin implementation and qualified-send build fingerprint match the pre-migration F1 source.
3. Unit tests, static surface checks, lint, and zero-baseline privacy scan pass.
4. Fixture tests run against extracted, pinned public Hermes builds in scratch storage.
5. The private app checkout pins this repository by exact commit and does not duplicate plugin source.
6. Features, wire contract, operator setup, security reporting, and upstream proposals are accessible from the root README.
7. Proposed approvals work remains isolated and unreleased until its security blockers are resolved.

## Out of scope

Changing HMP behavior, installing into a live Hermes home, publishing private research evidence, and merging the approvals feature.

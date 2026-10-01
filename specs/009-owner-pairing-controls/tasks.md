# Tasks

- [x] Add additive storage and legacy fallback with explicit-denial precedence.
- [x] Add the host pairing prompt and later grant/deny commands.
- [x] Test `GRANT`, old yes/no input, two-device isolation, revocation, and persistence.
- [x] Test denial and grant on both jobs and model HTTP routes.
- [x] Update install and feature documentation; run unit, lint, plugin surface, privacy, and secret checks.
- [x] Replace the "control granted" wording with the shared informational helper; test it on the pairing and `grant-controls` paths, plus denial and inactive-device paths.
- [x] Update install guidance with the exact `hermes config set` cron command and drain-aware restart; models are separate and only if qualified.
- [ ] Complete independent security review of the exact PR commit before release or live installation.

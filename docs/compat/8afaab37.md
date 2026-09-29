# Hermes `8afaab37` compatibility evidence

This source revision was exported with `git archive` from a clean local clone.
Tests used an isolated Python 3.14 environment and temporary `HERMES_HOME`.
The running Hermes installation was read only. The archived cron bridge files
and the clean git checkout produced the same fingerprint:

`3db5c28b88eca27289e94f405c8645011906fd3ab3d42bd73d2a4b5972f74669`

The upstream Hermes API jobs suite passed 20 tests. The HMP real adapter cron
integration passed 1 test, including create paused, list, edit, resume, pause,
and delete. The allowlist entry requires both this fingerprint and the full
`8afaab3703e336d72a72c812dd2dd249f04f166a` git SHA. No fingerprint-only
entry was added for archive or tarball installations.

This qualifies only the compatibility gate. The preview remains off by default
and needs its separate owner-device, bot-access, and private host-flag checks.

## Default model

The archived model bridge files and clean git checkout produced the same
fingerprint:

`d5d360c9ba6217f3f31843b866a3f88cb5a48f0eac53ea5b2a76ba38b1312b50`

Seven Hermes profile model scope tests passed. The HMP A→B→A integration
passed against the real profile writer using independent temporary homes.
The model entry requires both this fingerprint and the full git SHA above.
No fingerprint-only entry was added. The model preview still requires its
separate owner-device, bot-access, and private host-flag checks.

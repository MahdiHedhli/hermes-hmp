# Plan

1. `hmp_plugin/compat_report.py` (stdlib-only, no import-time I/O): bounded and
   ownership-checked receipt reader; strict format-1 candidate-receipt validation
   bound to this host's identity, the committed list, the installed HMP version
   and the clock; the allowlisted payload and issue body; the read-only login
   lookup; and the single `gh issue create` call with its not-sent versus
   delivery-unconfirmed error split.
2. Register `hermes hmp compat report --matrix` beside the unchanged bare
   `compat` command. Refuse on TTY/session first, resolve identity by file reads
   only, discover the login, print destination, login and the exact body, then
   read one line and accept only `REPORT\n`.
3. Inject identity, committed list, HMP version, clock, `gh` path and runner, and
   temporary directory through `CliEnv`. Never import Hermes or the bridge, and
   never read the CLI host's OS or Python for the report.
4. Test offline: positive, receipt-shape and freshness, ownership, host binding,
   listed builds, consent, preflight failure, and delivery-unconfirmed paths;
   keep the module-layout test.
5. Document the draft, its limits and the open tooling-branch dependency in
   `docs/INSTALL.md` and `FEATURES.md`. The compatibility gate and the source
   tooling are unchanged.

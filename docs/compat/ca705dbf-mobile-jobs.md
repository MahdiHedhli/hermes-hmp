# Hermes `ca705dbf` mobile jobs evidence

Native build: `ca705dbf7ef86425b381b542712aff310f1ee52c`, cron bridge
fingerprint:

`382a68a0ad0a0b65fa8e0cc7f75fa30b7b7b27661694dd62a3c2944464c889d2`

The candidate plugin source was `248784b`. Tests ran on native Python 3.14.7
from a frozen package-manager environment (the unpinned build-time wheel dependency is a
known limitation), using temporary fresh homes and gateways. No live jobs were
read, run, or changed.

## Result

The scoped native fixture suite passed 11 of 11 cases with 0 skipped, plus two
bridge boundary checks and the fingerprint checks. There were no deadline hits
or leftover processes. The suite covers the stock cron writer test, the jobs
fixture (gate closure, A→B→A profile isolation, no cross-profile key borrowing,
and a corrupt store never reporting an unpersisted success), and read and
direct-send regression cases that show chat behavior is preserved.

## Qualification truth

The original wrapper reported FAILED because
of one extra 49-byte file, the native startup `.bytecode-fingerprint`, an inert
checkout-cache stamp written by Hermes at startup. Every other check was
unchanged. An independent review of that delta accepted it, and a manual
supplement qualified the build as a metadata delta.

## Scope

Qualified: paused create, list, edit, and delete through the profile-scoped
writer and routes; profile isolation; key and permission gates; corrupt-store
failure; chat preservation. No model-manifest entry was added.

Not verified: actual scheduler delivery, previous-run continuity, phone UI, and
installation on a physical host. The preview stays off by default and needs an
explicit per-device grant.

The exact Hermes `ca705dbf` plugin-guard-v8 scanner scanned the runtime plugin
subtree at source `248784b`, not an installed live plugin and before the new
admission-only manifest delta. It returned safe with two medium fixed-argument
subprocess findings.

# BR8a launchd crash-containment experiment — observed November 4, 2026

This is a bounded temporary synthetic fixture, not an HMP service install,
production containment receipt or permission to signal an arbitrary process.
Current installed launchd.plist(5), AbandonProcessGroup, states that launchd kills
remaining members of a job's process group when that job dies (unless abandoned).
The existing reader uses start_new_session=True, so its group is different.
Do not assume the manager's job-group cleanup covers that reader.

## Experiment scope

Use current non-root Darwin account and its existing gui/<uid> domain only.
Create a new private /private/tmp fixture directory (0700), random unique job
labels, scripts/plists/logs/receipt (0600), private Unix listener and two one-shot
cases. No file goes into LaunchAgents/LaunchDaemons or a Hermes home. No existing
job, environment, gateway, profile, credential, provider, device or app is changed.
The fixture is removed from launchd with exact-label bootout after each case.
KeepAlive false, RunAtLoad true, no scheduled/persistent startup; program uses
/usr/bin/env -i LANG=C LC_ALL=C and exact Python -I-B-S fixed fixture scripts.

Case A launches an idle synthetic reader with a new session. Case B uses an
inherited broker group. Broker and reader establish separate private connections
with fixed bounded nonce/identity messages. Controller verifies kernel peer UID/
PID and exact job PID/arguments, and records observed groups. It never signals a
peer PID/group. A fixture-only byte on the broker's own authenticated connection
makes that broker call SIGKILL on os.getpid(); no finally cleanup can run. Observe
whether the reader's private connection reaches EOF within two seconds.

Expected diagnostic: the new-session reader socket remains open; the shared-group
reader socket reaches EOF, consistent with the documented launchd policy. Both observations are finite snapshots, not proof of
actual reader code integrity, all descendants, permanent absence or production
hard wall-clock closure. Failure/unknown is recorded, never reclassified as pass.

## Limits and cleanup

Worker socket deadline <=12seconds independently exits on EOF/timeout/explicit
fixture stop. Broker deadline <=15seconds and normal-exit finally cleans only its
own retained synthetic child. For cleanup controller sends explicit
stop through that verified reader connection after recording the observation,
then separately requires EOF within two seconds. Missing/unverified peer or
unknown EOF retains the uncertainty lock even if the job is known absent.
EOF is communication closure only. It does not establish process death. Before
stimulus, require at least nine seconds of the reader deadline remaining, verified
group geometry independent of the controller, broker acknowledgement, and broker
EOF before the separate two-second reader window. Record monotonic timestamps. No arbitrary PID
scan, killpg, SIGCHLD/reaper mutation or real profile content is used.

Each command is a structured subprocess argv, bounded timeout, no shell or retry:
- launchctl print gui/<uid>/<fresh-random-label> before submission: require precise
  absent-service outcome, otherwise stop before mutation.
- launchctl bootstrap gui/<uid> <exact-private-plist> once.
- launchctl print exact service to verify the private program/nonce and PID.
- launchctl bootout exact owned service only, after rechecking its program/nonce;
  no whole-domain bootout or label glob. Known absent is already cleaned. Unknown
  submission/cleanup is retained in private receipt and reported without retry.

Never print/store full launchctl print output, which can include inherited user
environment. Extract only bounded own-job fields and matching booleans. /usr/bin/env
-i prevents that environment reaching Python or its child; logs have no secrets.
Record command stage/return code, exact own-label/paths/hashes and observed result
privately. Preserve receipt/diagnostic logs; remove no unrelated files/services.

## Review / tasks

- [x] Independent safety/causality and implementation review before fixture execution.
- [x] Implement fixed scripts/controller, bounded parser and exact cleanup;19 safety tests
  for refusal/uncertain submission paths without real service mutations.
- [x] Run each owned-label case once; inspect actual receipt and terminal tool
  handle. Do not restart on observation timeout or claim simulated service proof.
- [ ] Independent evidence review; decide production process topology explicitly.
  Current direct ProcessOwner remains unchanged, and character availability closed.

## Actual bounded result

One execution completed with exit0. Each case had more than11.99seconds of the
reader's independent lifetime remaining at stimulus. Broker acknowledgement and
broker socket EOF were observed before the separate reader window.

| Layout | Reader communication during crash window | Separate cleanup |
| --- | --- | --- |
| New session | No EOF over2005.065ms | Explicit stop then EOF; own job absent |
| Shared broker group | EOF within0.644ms | EOF confirmed; own job absent |

Private receipt SHA256:
`1289502d56068d1aad8888b9e7138071d747593552b0768787ddaef6ef3f0ee6`.
Both own-label jobs were known absent, all verified reader connections reached
cleanup EOF, and the uncertainty lock was removed. No installed Hermes, gateway,
profile, device or provider changed.19 focused safety cases and190 composed broker
cases pass; lint and closed-import scanner pass.

This supports rejecting an assumption that launchd job-group cleanup covers a
new-session reader. It is consistent with the documented shared-group behavior.
EOF is not process death, permanent group absence, bounded production syscall
latency or runtime/code integrity. BR8 remains open. A shared-group backend would
need its own reviewed child-only custody/closure contract, audited no-fork worker,
service lifecycle and runtime provenance; it cannot reuse a fictitious old
reader-group-absence receipt. No character route or service is active.

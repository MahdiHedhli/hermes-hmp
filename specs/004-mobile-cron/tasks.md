# Tasks: mobile cron management

1. Confirm the profile-mirrored API contract and create-paused behavior on the
   pinned stock Hermes fixture. Record the exact fingerprint dependency set.
2. Implement the HMP owner-device/host-flag gate and fixed cron route table.
3. Implement bounded loopback calls and minimal job serialization. Add negative
   tests for every trust-boundary and timeout case in `plan.md`.
4. Update the HMP wire contract, feature list, operator guide, and CI checks.
5. Add typed HMP client methods, active-instance-safe state, and the Jobs UI.
6. Verify unit, fixture, app, privacy/log, and compatibility suites. Run the
   zero-baseline public privacy scan before pushing HMP.
7. Leave the feature disabled until a release candidate receives the planned
   independent security and physical-device review.

## Desktop-parity revision (2026-09-29)

8. Extend the bounded wire shape with `deliver`, `continuity`, and `repeat`;
   reject arbitrary destinations and preserve old clients' local default.
9. Qualify Hermes's profile-scoped create/edit writer against exact builds
   because `/api/jobs` does not persist `context_from`; verify Bot Chat
   delivery, finite runs, continuity, and other-context preservation in an
   isolated store. Keep reads, pause/resume, and delete on the scoped API.
10. Add the app's schedule, delivery, repeat, and continuity controls with Bot
    Chat as the new-job UI default, while preserving existing jobs' settings.
11. Recheck the live host's exact installed commit and per-profile health,
    install internal binaries on both iPhones and the Samsung tablet, and
    record owner verification separately from unobserved scheduled runs.
12. Before external release, observe scheduled Bot Chat delivery and continuity
    across runs, finish physical pause/delete checks, and run the exact
    candidate's independent source and signed-artifact reviews.

# Mobile cron management

## Status

Draft owner preview, revised on 2026-09-29 for Desktop-style scheduling. The
host flag remains off by default, and every request requires the selected
bot's access, a separate host-granted device control, and an exact qualified
Hermes build. Installing HMP does not enable remote cron by itself.

## User stories

1. As the owner, I can see scheduled jobs for the selected bot, including their
   schedule, next run, paused state, and last outcome.
2. As the owner, I can create a named scheduled prompt for that bot. The job
   starts paused so I can inspect it before its first execution.
3. As the owner, I can choose run-history or this bot's Bot Chat for results,
   a finite run count, and whether each run sees the previous run's output.
4. As the owner, I can edit a job's name, schedule, prompt, delivery, run count,
   and continuity; pause or resume it; and delete it after confirmation.
5. If a write has an uncertain outcome, the app tells me to refresh the job list
   before I try again. It never retries a create automatically.

## Requirements

- HMP exposes only the selected profile's jobs after device authentication,
  host-configured owner-device authorization, and the existing per-bot access
  check. A separate host flag enables this feature; its default is off.
- HMP uses the resolved loopback API server and the selected profile's scoped
  key for reads, pause/resume, and delete. Create/edit use the qualified
  profile-scoped Hermes cron writer. Neither path gives an API key to the
  device or falls back to another profile, hostname, transport, or public
  route.
- Requests and responses are bounded in size and time. HMP accepts only name,
  schedule, prompt, `deliver` (`local` or `bot-chat`), `continuity` (boolean),
  and `repeat` (1–9999 on create; zero clears a limit on edit). New jobs start
  paused. The app defaults new jobs to `bot-chat`; an older client that omits
  `deliver` gets HMP's conservative `local` default. HMP does not accept
  scripts, workdirs, skills, arbitrary delivery targets, model pins, run-now,
  or an arbitrary API proxy.
- Continuity maps only to Hermes's self-reference for the previous run.
  Editing it preserves other existing context references. Unknown or
  unsupported job types must not be silently rewritten through the phone.
- HMP returns fixed error vocabulary without echoing prompts, API responses,
  tokens, addresses, or exception text into its logs.
- Paired devices without owner authorization, devices without bot access,
  unsupported Hermes builds, disabled feature flag, and missing loopback API
  configuration fail closed.
- Mobile keeps job state scoped to the explicit active instance and bot. Jobs
  are Hermes-owned; mobile does not schedule or execute them locally.

## Acceptance scenarios

- A configured owner device lists jobs for profile A; profile B's jobs do not
  appear. A switch to B clears A's foreground job state before B loads.
- A non-owner device with ordinary bot read access cannot list or mutate jobs.
- A create receives no response after transmission. The app reports an unknown
  outcome and does not send it again; after refresh, the owner can identify the
  paused job or deliberately create a new one.
- A job remains paused after creation and does not execute before the owner
  presses Resume.
- A phone-created Bot Chat job persists `deliver: bot-chat`, a finite run
  count, and `context_from: ["self"]` when continuity is selected; editing a
  Desktop-created supported job preserves its other context references.
- A disabled flag, invalid API key, non-loopback endpoint, unsupported build,
  oversized payload/response, or timeout reveals no job data and makes no
  cross-profile request.

## Out of scope

Immediate run, job scripts, skills, arbitrary working directories, arbitrary
delivery destinations, and cron management by non-owner devices.

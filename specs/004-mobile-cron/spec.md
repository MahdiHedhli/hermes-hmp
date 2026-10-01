# Mobile cron management

## Status

Draft implementation scope. This feature remains off by default until its Hermes
compatibility and authorization checks pass. It does not enable remote cron on a
running installation by itself.

## User stories

1. As the owner, I can see scheduled jobs for the selected bot, including their
   schedule, next run, paused state, and last outcome.
2. As the owner, I can create a named scheduled prompt for that bot. The job
   starts paused so I can inspect it before its first execution.
3. As the owner, I can edit a job's name, schedule, and prompt; pause or resume
   it; and delete it after confirmation.
4. If a write has an uncertain outcome, the app tells me to refresh the job list
   before I try again. It never retries a create automatically.

## Requirements

- HMP exposes only the selected profile's jobs after device authentication,
  host-configured owner-device authorization, and the existing per-bot access
  check. A separate host flag enables this feature; its default is off.
- HMP calls only the resolved loopback API server for that profile, with that
  profile's scoped API key. It never gives the API key to the device and never
  falls back to another profile, hostname, transport, or public route.
- Requests and responses are bounded in size and time. HMP accepts only name,
  schedule, and prompt for create/edit. New jobs use `deliver: local` and
  `paused: true`; no scripts, workdirs, skills, delivery targets, model pins,
  run-now action, or arbitrary API proxying are in this version.
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
- A disabled flag, invalid API key, non-loopback endpoint, unsupported build,
  oversized payload/response, or timeout reveals no job data and makes no
  cross-profile request.

## Out of scope

Results delivery to a chat, immediate run, job scripts, skills, arbitrary
working directories, and cron management by non-owner devices.

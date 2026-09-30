# Plan: mobile cron management

## Source and compatibility

The inspected Hermes checkout is `04fa849e70165336ba73e6750257a1ebd7ff998d`.
Its `gateway/platforms/api_server.py` implements profile-mirrored `/api/jobs`
list/create/get/update/delete/pause/resume routes. `cron/jobs.py` owns the job
store; `cron/scheduler.py` registers created jobs. Confirm these routes and
their profile isolation against the exact qualified build before enabling.

## HMP design

- Add a dedicated cron module, not a general loopback proxy. It builds fixed
  API paths and allowlisted JSON bodies and validates Hermes responses.
- Route table: `GET/POST /bots/{p}/jobs`, `PATCH/DELETE
  /bots/{p}/jobs/{id}`, `POST /bots/{p}/jobs/{id}/pause|resume`.
- Authenticate before any body read, then check owner device, bot access,
  rate limit, host flag, build qualification, and loopback endpoint. The
  device never chooses an API server URL or profile path.
- Read the owner-device set and feature flag from live HMP config on each
  request. An empty or malformed owner set disables the feature.
- Use the existing `ReadBridge.direct_send_endpoint(profile)` for the
  profile-scoped, literal-loopback address and key. Add an independent cron
  compatibility fingerprint for the API and cron files this route depends on.
  Recheck that fingerprint on each job request so a host source update cannot
  inherit a prior qualification without a new review.
- Use an aiohttp client with proxy inheritance disabled, redirects disabled,
  explicit connect/total timeout, response-size bound, and no logging of
  request or response bodies. No automatic retry.
- Normalize job records into a small mobile schema. Do not forward raw Hermes
  job records, which may contain paths, scripts, and internal error text.

## Mobile design

- Add typed methods to the HMP client and a Jobs page under the selected bot.
  Keep the active instance token on every request; discard late responses from
  a prior instance or bot.
- The create/edit form contains name, schedule, and prompt. Create initially
  paused, display confirmation from Hermes, and require a separate Resume.
- Treat network failure after a write as uncertain. Refresh first, with no
  background retry or local job queue.

## Threats and negative tests

Test non-owner access, revoked token, wrong instance, per-bot denial, disabled
flag, malformed IDs/body, unknown profile, path injection, profile-scope mixup,
API key error, redirect, DNS/proxy steering, slow/oversized responses, duplicate
create after timeout, and accidental prompt logging. Test the actual profile
mirroring path with an isolated Hermes home before release.

## Open qualification

Until exact-build qualification and an isolated end-to-end test pass, the host
flag remains off. The owner’s live Hermes is outside this plan.

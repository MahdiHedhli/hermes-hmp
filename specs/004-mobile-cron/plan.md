# Plan: mobile cron management

## Source and compatibility

The initial plan inspected Hermes `04fa849e70165336ba73e6750257a1ebd7ff998d`.
The revised cron writer was qualified against the pinned stock and live-source
builds recorded in `docs/compat/8afaab37.md` and
`server/hmp_plugin/mobile_cron_supported_builds.json`. The profile-mirrored
`/api/jobs` routes handle reads, pause/resume, and delete, but the inspected
create route does not pass `context_from` and the update allowlist excludes it.
HMP therefore uses Hermes's own profile-scoped cron writer for create/edit on
only those exact qualified builds. Requalify after any Hermes source change.

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
- Use an aiohttp client for read, pause/resume, and delete with proxy
  inheritance disabled, redirects disabled, explicit connect/total timeout,
  response-size bound, and no logging of request or response bodies. No
  automatic retry. Use the fixed, profile-scoped Hermes writer for create/edit;
  do not expose a general bridge or arbitrary host path.
- Normalize job records into a small mobile schema. Do not forward raw Hermes
  job records, which may contain paths, scripts, and internal error text.

## Mobile design

- Add typed methods to the HMP client and a Jobs page under the selected bot.
  Keep the active instance token on every request; discard late responses from
  a prior instance or bot.
- The create/edit form contains name, schedule, prompt, result delivery, a
  finite run limit, and previous-run continuity. New phone jobs default to Bot
  Chat delivery, are created paused, and require a separate Resume. Existing
  jobs retain their destination unless edited.
- Treat network failure after a write as uncertain. Refresh first, with no
  background retry or local job queue.

## Threats and negative tests

Test non-owner access, revoked token, wrong instance, per-bot denial, disabled
flag, malformed IDs/body, unknown profile, path injection, profile-scope mixup,
API key error, redirect, DNS/proxy steering, slow/oversized responses, duplicate
create after timeout, accidental prompt logging, arbitrary delivery targets,
unsupported job types, and loss of other context references on edit. Test the
actual profile mirroring and writer paths with an isolated Hermes home before
release.

## Open qualification

Exact-build qualification and isolated writer tests passed for the recorded
candidate; the owner authorized its live installation and verified phone
creation and cross-client edit. A scheduled Bot Chat result and continuity
across real runs still need observation. The host flag remains off by default
for every new installation, and external release still requires independent
security and physical-device review.

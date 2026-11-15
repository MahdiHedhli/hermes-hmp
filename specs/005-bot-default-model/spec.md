# Bot default model on mobile

## Status

Draft feature. It is disabled by default and does not change a live Hermes installation until the operator enables its host flag on a qualified build.

## User story

An owner can inspect a bot's configured provider and default model, choose another model offered by that bot's Hermes profile, and confirm the change. The choice affects new sessions; the phone never claims to switch a running Desktop turn.

## Requirements

- The active instance and exact bot profile remain visible while choosing and confirming a model.
- Only a configured owner device that already has access to that bot can read or change its default model.
- HMP uses the profile that Hermes routed for that bot. The device cannot supply a profile home, API address, credential, custom endpoint, or raw config patch.
- Model options come from Hermes's profile-scoped API server. HMP projects only provider names and model IDs. It does not expose the raw catalog, credentials, endpoint URLs, or pricing internals.
- Model changes use Hermes's existing validated profile-model writer, with an exact-build qualification and a separate host flag that defaults to off. Hermes remains the authority for model and provider validation.
- Writes have no automatic retry. After an uncertain result, the phone reloads the configured model before the owner can decide whether to try again.
- Errors and logs never echo model provider secrets, API responses, config paths, or exception text.

## Acceptance

An authorized owner can read profile A's model and options, change it, and observe the persisted value. The same request against B cannot read or alter A. A non-owner, revoked device, unauthorized bot, disabled flag, unsupported build, invalid selection, or unavailable model catalog fails closed. A late response after switching instances or bots is discarded.

## Out of scope

Mid-chat model switching, configuring providers or API keys, arbitrary model endpoints, changing another bot's model, and changing a model while Hermes cannot validate the selection.

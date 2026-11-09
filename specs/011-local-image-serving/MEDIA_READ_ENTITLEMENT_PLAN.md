# LM-ENT1: independent host-local media read permission

Status: proposed implementation contract, no live grant or API/CLI implemented
by this document. It extends the existing local-image feature; it does not
authorize changing device permissions. The current R3 remains owner-only.

## Observed need

The updated LLY520 has R3 installed but no `local_media.enabled` opt-in and no
configured approval-owner list. Jobs/model controls do not imply that role.
Enabling one flag alone cannot make its images available. Granting approval
answer authority solely to obtain image access would bundle unrelated rights.
No such change was made. Software installation is separate from access.

## Required contract

- Negotiate an explicit independent media-read capability. Older hosts keep
  their existing owner-only behavior; clients explain that limitation instead
  of recommending a silent approval-role grant.
- Keep the host-wide media opt-in, authenticated active device, original token
  scope, per-bot membership, immutable descriptor provenance and bounded image
  checks. A media permission grants none of pairing, bot membership, prompt
  answers, mode changes, jobs, model management or arbitrary host file access.
- Introduce an operator-managed per-device media-read decision. An explicit
  allow can grant that right to a non-approval-owner; an explicit deny closes
  it. Missing decisions preserve existing owner-only behavior and deny other
  devices. Do not migrate absent decisions into new allows.
- Effective precedence is explicit deny, explicit allow, then the unchanged
  missing-decision owner fallback. Bind each decision to the original instance
  and verified stable device identifier, never a label or token string. Persist
  decisions atomically with an authoritative revision/generation shared by
  issuance, fetch and final publication checks. Concurrent writes need a
  reviewed conflict rule and readback; a lost acknowledgement is not a retry.
- Use a separately reviewed local operator command, provisionally
  `hermes hmp devices grant-media-read <verified-device-id>` and its deny/readback
  counterparts. These are proposed syntax, not available commands. Require
  current verified active pairing identity and authoritative stored/effective
  readback. Mobile can request access; it cannot grant itself permission.
- Do not alter approval-owner configuration or job/model controls. An explicit
  media allow remains independent of those decisions. Preserve their own deny
  rules and never reframe a media-only grant as approval authority.
- Recheck the current decision and device/bot authority at descriptor issuance,
  fetch admission and before response publication. Close stale generations and
  late replies on revoke, unpair, entitlement denial or instance/profile change.
  Never treat a cached descriptor or prior successful fetch as renewed access.
  Revocation cannot retract bytes already delivered or guarantee instant worker
  termination. It must prevent late publication, close the corresponding cache
  generation and preserve real worker permit lifetimes and outstanding debt.
- Readiness must separate host opt-in, API/dependency eligibility, operational
  health, per-device entitlement and per-bot authorization. Reveal precise
  reasons only within authenticated authorized scope, with no resource-existence
  leak. Disclose the host-wide impact before enabling a host flag/restart.
  Default masked route denial precedes host-flag, descriptor/reference and file
  lookup. Do not advertise the new capability until its effective-decision path
  exists; supporting one read-only status field is not complete capability.

## Acceptance and tasks

1. Freeze/review the wire capability, store transition and operator authorization
   contract before implementing a mutating command. Keep default-deny migration
   and existing owner behavior explicit.
2. Implement the independent effective decision and read-only readiness with
   current authority/generation binding. Preserve existing owner-only fallback.
3. Implement the reviewed operator grant/deny/readback path. A missing or lost
   acknowledgement requires authoritative inspection, never automatic replay.
4. Apply the decision consistently to issuance, fetching, cancellation and late
   worker completion; preserve image/type/size/path and profile isolation.
5. Verify old-owner behavior, non-owner default denial, media-only allow, explicit
   denial, inactive/revoked/wrong device, wrong bot/instance, concurrent grants,
   stale awaits and lost acknowledgements. Prove every unrelated permission and
   provider/model/job value remains unchanged. No prompt answer or job execution
   is part of these tests.
6. Qualify packaging/runtime and Android/iOS display separately. Only then seek
   the owner's explicit opt-in and exact device grant decisions for deployment.

No upstream Hermes change is established as a prerequisite for this HMP-owned
permission separation. It does not resolve the separate character-reader work.


## Source checkpoint — November 8, media readiness

Focused branch `feat/media-read-entitlement-20261108`, source `701783e`, adds
`GET /bots/{p}/media-readiness` without changing the existing AR1 response.
The new response separates entitlement, host opt-in and runtime API state, with
closed reasons and `contact_host_operator`; it does not advertise an unimplemented
Request access or Fix transport. Image availability is explicitly `not_probed`.
It reuses the existing authenticated per-bot authorization/deadline/worker-budget
fence and rereads rights/settings before disclosure. Unknown authority is refused,
not represented as missing rights. No file/reference lookup or mutation occurs.

The 77-case current-Python readiness suite passes with zero failures/errors/skips;
floor run and broader route-surface/contract coverage are pending at this checkpoint.
Mobile decoding/display and capability negotiation, causal revocation/lost-await
route coverage, independent review and runtime/physical qualification remain open.
The legacy owner-fallback revocation-generation limitation remains open. Nothing
from this schema-4 branch is installed on a live host.

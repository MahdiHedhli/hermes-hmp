# Desktop presentation integration contract — proposed, activation closed

This completes the concrete transport/custody plan for the existing BI1 scope.
It is an implementation contract for review, not a claim of deployed support.
Hermes remains the bot authorization/routing authority. No upstream core edit is
required for the observed version-bound metadata/home interfaces; qualification
of their plugin binding remains required.

## Negotiation and metadata

The authenticated `/hmp/v1/bots` response may add
`capabilities: {bot_presentation: 1}` only after its listener-owned native service,
child supervisor and shutdown drain are bound and healthy. Missing, mistyped or
unknown values mean ordinary letter/local-icon fallback. No capability is an
entitlement or a reason to open unrelated gates.

`GET /hmp/v1/bots/{canonical_profile}/presentation` uses existing bearer and
HMP-Instance checks. The profile is canonical ASCII, 1–64 characters. The native
per-bot authorization gate runs before home resolution or metadata file access.
Jobs/default-model controls, approval ownership and gateway-admin grants are not
required or conferred. All native bot-gate errors retain their existing masking
and status semantics; missing optional routes/resources fall back on mobile.
Authentication failures remain lifecycle failures rather than optional fallback.

Success is one closed JSON DTO of at most4096 decoded bytes:
`version/iid/profile/display_name/name_source/character/metadata_revision/avatar/observed_at`.
The existing pure Python projection and Dart parser define exact scalar limits,
Unicode policy, seven classic shapes, blobatar v2 syntax and digest serialization.
The endpoint reads only fixed profile.yaml presentation fields, never config,
SOUL, prompts, tools, provider secrets or conversations. No raw object graph or
file path leaves the worker. Observation time and avatar revision are excluded
from the canonical metadata digest.

## Fixed image operation

Planned read: `GET /bots/{profile}/presentation/avatar/{revision}`. Revision is a
lowercase SHA-256, never a path, URL or filename. The reader derives the native
home and selects only fixed assets/avatar.png, avatar.jpg or avatar.webp according
to the already frozen preference. A changed or cleared image cannot satisfy an
older requested revision. The response is static PNG/JPEG/WebP, at most2,000,000
bytes, each declared edge at most1024 and at most1,048,576 declared pixels. No
redirect, arbitrary URL/path, SVG, animated fallback or generic asset selection.
Structural scanner admission does not prove decoding; the bounded mobile codec
must decide decode validity and preserve the fallback on failure.

## Parent and child ownership

Reuse ParentAuthorityAdapter and JobOwner. At most16 waiting jobs, six real
processes (four metadata/two avatar), one per canonical profile, with an original
two-second deadline. Admission reserves existing credits before native work.
Original request headers stay in the parent; the child receives no credentials.
A local lease/frame/GO challenge is not native permission.

Native INITIAL, BEFORE, PRE_GO and PRE_EMIT observations reauthenticate original
headers and native bot policy under current listener/store/bridge/identity and
routing-home binding. The accepted native service retains an actual thread ledger
through cancellation and refuses known closure after ambiguous start. A stalled
native call is retained ownership debt, not a magically terminated thread.

The child remains blocked until the reviewed synchronous GO handoff. It receives
bounded, closed source input from the authorized parent, uses the explicit POSIX
backend and fixed-reader no-follow/FD/mode/inode checks, and executes actual YAML
scanner/event reduction and raster inspection under the same deadline and one
nonresetting work ledger. That shared ledger still needs implementation; current
phase-local counters must not be presented as a completed shared owner budget.

The parent bounds stdout/header/body and diagnostics before buffering. Success
requires actual result/diagnostic EOF, observed child wait, process-group closure,
IPC closure, signal-resource closure and all target FDs known closed, in the
existing JobOwner ordering. Unknown cleanup retains UNKNOWN debt. Cancellation,
timeout or HTTP handler completion alone never releases a reservation. Native
and child drains must finish before Store/listener retirement. No forced cleanup
of unrelated processes or guessed ownership.

## Mobile ownership and freshness

Use the original instance/profile/foreground epoch and connection generation.
Fresh authenticated roster authorization/capability is required before metadata.
Recheck current foreground after every asynchronous phase. Saved rows do not fetch.
A new roster object, authorization change, switch, unpair/re-pair or disposal
invalidates retained row data and pending rendering. Do not rebind by friendly name.
Local explicit icons retain priority over a classic character. Unsupported shapes
use fallback; completing classic shapes does not satisfy blobatar or custom-image
parity. Header and details must eventually use the same scope rules as roster.

Metadata/file snapshots and authority observations are not an atomic lock over
all external edits. Document their observation scope; re-read on explicit refresh
and do not claim an instantaneous cross-process edit/clear guarantee without a
native primitive. Separate image revision and current generation prevent a late
older image from replacing an already observed newer revision.

## Required qualification

Remaining causal checks: real child start/GO/EOF/wait/group/IPC/signal ordering;
shared counter exhaustion; timeout/cancel/ambiguous cleanup; wrong/revoked/stale
credentials, native membership and routed home; cross-instance/profile results;
replacement/clear and late responses; bounded pinned binary reads/codec failure;
classic/blobatar/custom-image visual parity; header/details; physical iOS/Android
and exact signed artifact/release review. No source or fixture count substitutes
for these gates. Live route advertisement stays absent until its actual binder
and supervisor pass focused independent review.

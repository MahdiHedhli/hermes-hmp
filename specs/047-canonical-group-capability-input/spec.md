# GR1 native group capability input

Tracking: [HMP issue152](https://github.com/MahdiHedhli/hermes-hmp/issues/152).
Status: first internal source task of the complete group-chat feature; no route,
transport, grant, operator command, phone UI or deployed availability is added.

## User target and scope

A paired phone should eventually discover and operate permitted groups through
Hermes's canonical room authority, preserving instance/bot/device isolation,
native room/event IDs, uncertain outcomes, member controls and native approvals.
A read-only group browser or a capability parser is not completion of that target.

This task only consumes a JSON-decoded `groups.capabilities` result without
promoting native metadata into authorization. It is needed before the bridge can
negotiate native requirements. It neither opens a socket nor imports Hermes.

## Requirements

- GC1: Accept ordinary JSON data matching the pinned native payload's required
  protocol_version, driver, persistent_process, methods, features and max_log_limit.
  Reject wrong scalar/container types, bool-as-int and missing fields with a fixed
  content-free error. No coercion or error interpolation of native input.
- GC2: Preserve exact driver/persistent booleans and independent known method
  advertisements. Method presence must never imply driver state, caller native
  capability, HMP device/bot/room access, approval ownership, operator authority,
  delivery or successful execution. Do not provide a combined ready/authorized bit.
- GC3: Newer positive protocol versions, unknown bounded methods/features and
  extra bounded top-level metadata do not close otherwise understood inputs. Retain only
  the explicitly known method/feature vocabulary. No commit/version allowlist.
- GC4: Bound the top-level key count and key length, and the method/feature lists and each token before normalization. Clamp a
  valid positive native log-page count to the local500-item ceiling. These limits
  are resource rules, not release qualification. The future transport must also
  bound frame size/JSON decoding; this parser does not do that work.
- GC5: Drop authority IDs, seatable profile names, peer URLs/catalogs/grants and
  unknown metadata from the result. Native seatable profiles are not HMP rights.
  Shallow-validate exact String keys before any field lookup; do not traverse or retain ignored values or call their string/repr methods.
- GC6: No runtime call site, socket, ticket, Store/schema/config/grant/model/job
  write, plugin registration, dependency or live state changes in this task.
- GC7: Malformed data remains unavailable to a future caller; no empty/success
  fallback. Source tests, review and native sample pins are not runtime evidence.

## Clarifications

The native gateway owns group execution; HMP must not recreate its scheduler or
room log. Native capabilities list methods even when a principal lacks the
method's capability. `driver:false` also permits native detached metadata paths,
whose per-room ownership filtering differs. This parser describes advertisements
only and cannot make either path safe for a phone. HMP authority, per-room access,
canonical transport and publication fences are separate unfinished tasks.

## Acceptance scenarios

1. Current native-shaped payload parses, preserving observed flags and method
   names, with no retained peer/owner/profile metadata.
2. Future protocol/method/feature additions preserve understood observations.
3. An advertised send with driver false remains an advertisement only; no ready
   or authorization result exists. Native actor privileges remain unknown.
4. Missing, malformed, oversized and hostile Python substitutes are refused with
   the same bounded error; ignored unknown values are never inspected.
5. The parser does not mutate input; later input mutation cannot alter the frozen
   result. It can be imported/tested with no Hermes, networking or Store setup.

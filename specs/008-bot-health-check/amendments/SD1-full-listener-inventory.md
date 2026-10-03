# SD1: complete bounded listener inventory

Status: implementation in progress; independent source review pending. Plan accepted
independently by the coordinator before code on 2026-10-03.

## Requirements

- Preserve all 128 legal profiles with 64 ASCII characters, their full derived
  names and complete three-channel health. This is a record domain, not a native
  global profile maximum. Never truncate or publish a partial fallback.
- Local listener files allow 65,536 bytes; the pinned network ready read remains
  16,384 bytes. Read, write and current-file removal use the file limit.
- Records up to 16,384 bytes retain legacy valid parsing. Larger format-1 records
  require exactly nine keys, no duplicate members, canonical IID, bounded exact
  metadata, unique legal profiles and complete health. Oversized loose legacy
  records must not acquire a larger acceptance budget.
- Large metadata: printable ASCII host/opaque nonce at most 128 characters; host
  must remain an IP literal; exact integer port 1..65535, pid 1..2**31, snapshot
  time 0..2**63-1. Profile/name pairs are unique legal IDs and printable ASCII
  names of at most 64 characters. All three health codes are from the existing set.
- Bound writer projection and default-equivalent JSON encoding before allocating
  an unbounded body. Strict inputs receive the file budget; other small historical
  inputs receive only the legacy budget. Failures are fixed OSError values within
  the adapter's existing fence, before atomic replacement.
- Projection accepts exact built-in lists/tuples and built-in scalar values only;
  arbitrary sequences, generators and subclass hooks are not traversal authority.
  Existing adapter/callers use these built-ins. Deep invalid JSON is refused or
  skipped by removal without changing valid-small semantics.
- Preserve directory/descriptor ownership and mode, NOFOLLOW, expected IID, PID
  and pinned TLS liveness, atomic replacement, exact-current removal and sanitized
  errors. No route, authority, native import or version allowlist changes.

## Envelope proof

Default JSON escaping gives the conservative bound
719 + 128*313 + 508 = **41,291 bytes**, below 65,536. This is not an attained
maximum claim. IP-valid synthetic samples have 41,283 and 41,288 bytes; tests
must retain every field/order/value rather than demand an attained ceiling.
Arbitrary large Unicode/custom names are outside the extended domain; valid
small custom records keep their old budget. No label truncation.

## Plan and tasks

1. Separate the file, legacy and network limits; audit removal's descriptor read.
2. Add strict large validation and bounded writer projection/encoding while
   retaining valid-small semantics and caller interfaces.
3. Add causal fake-only first-start/discovery, roundtrip, refresh, removal,
   descriptor, legacy/large, budget, network and privacy regression controls.
4. Freeze exact source/tests/docs for independent review before integration.

## Checklist

- [ ] Complete 128-profile first-start/discovery and refresh evidence.
- [ ] Strict extended envelope and legacy compatibility controls.
- [ ] File boundary/atomicity/security and unchanged ready network bound.
- [ ] Focused tests, lint/surface/privacy evidence recorded.
- [ ] Independent exact-source acceptance before integration.

## Residuals

Old readers can reject newly large records. Same-OS-user consistent-record
forgery remains SEC-1/SR-7. A failed out-of-domain (>128) refresh preserves an
older snapshot that may remain fresh for 45 seconds; health checks do not prove
equality to the live roster. This amendment does not silently invalidate it or
claim full native/device/provider/release qualification.

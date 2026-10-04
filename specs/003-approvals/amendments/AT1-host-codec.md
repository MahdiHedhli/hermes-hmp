# AT1: pure host-request and framing prerequisite

## Status and requirements

The independently accepted caller/bridge v4 contract defines this inert prerequisite.
Source review and execution remain pending. No operator command, IPC listener, phone
route, factory, native waiter or permission is enabled by this module.

Host selectors are DATA, never authenticated operator or paired-phone authority.
`HostGeneration` carries canonical `wire.require_iid` text, PID 1..2^31-1 and
32 lowercase hex nonce. Decoding requires exact equality with the caller-supplied
current generation; proving that generation's provenance remains the future caller's job.

Requests are nonempty strict UTF-8 JSON objects, at most 2048 bytes and depth four.
Duplicate/unknown fields, invalid scalars, integer bool/float substitutions and malformed
identifiers fail with one context-free `HostCodecError("approval test unavailable")`.
`begin` requires device/profile/session selectors (1..256 UTF-8 bytes, no C0/C1 or DEL),
with optional integer timeout 1..60000 defaulting to 30000. `status` and `cancel` accept
only their 32 lowercase hex host operation ID. They have no phone choice or user ID.

One request frame uses a four-byte unsigned big-endian length followed by exactly that
payload. A bounded incremental decoder accumulates at most 2052 bytes, refuses declared
over-cap lengths before retaining payload, and never returns a request before explicit
EOF confirmation. Invalid input or finish consumes the decoder; there is no reset/retry.
It performs no I/O and cannot prove EOF or enforce the future transport's 2000ms deadlines.

Host responses use the exact accepted/status/cancel-requested/completed/unavailable
schemas and fixed state labels from v4, with a 4096-byte payload cap and depth four.
Completed accepts only terminal states; it is DATA and does not prove a worker joined.
No raw exceptions, private native handle, target selector or phone ID appear in errors
or the fixed unavailable response. The codec generates no IDs and consults no producer.

## Plan

Add one pure module with frozen redacted DTOs, bounded schema/frame readers and closed
response writers. Reuse the existing strict JSON and canonical IID helpers, preserving
all old wire behavior. Add the exact module name to the closed inventory and module
documentation; retain equality, import checks and all scanners without exceptions.
The finite source union uses the published producer lint/inventory base. Caller ordering,
current authorization, peer credentials, connection limits, deadline observation,
producer lifecycle, typed phone projection and real IPC remain separate work.

## Tasks and causal checks

- [ ] AT1-C1 Independently review exact codec, tests and closed inventory additions.
- [ ] AT1-C2 Separately admit and execute fake-only codec tests, lint and inventory gates.
- [ ] AT1-C3 Prove cap/depth refusals before generic JSON decode and no fake admission
  on malformed/schema/stale-generation requests; valid boundaries must reach decoding.
- [ ] AT1-C4 Prove fragmented length/payload handling, missing EOF/truncation/trailing
  refusal, terminal failed decoder, exact fixed errors and separate host-only schemas.
- [ ] AT1-C5 Prove response bounds/shapes, fixed unavailable bytes and redacted DTOs.
- [ ] AT1-C6 Independently freeze/implement remaining caller/IPC/phone layers before
  claiming a runnable command, card, native/device behavior or release qualification.

Test definitions are source only until exact-source review and root execution admission.

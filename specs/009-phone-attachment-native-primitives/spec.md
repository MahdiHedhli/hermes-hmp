# Phone attachments: native primitive discovery fixture

Status: discovery evidence only. No HMP runtime, wire, API, auth, manifest or dependency change, no
attachment UX, and no claim that Phone photo/file upload is feature-ready or that any wire shape is
frozen. Independent root and focused review are pending.

## Problem

The source-only census (private, 2026-09-30) names native primitives a Phone photo/file upload
would rely on, but every statement in it is unexercised. This fixture runs the real native code
under the pinned native interpreter, with synthetic data only, so later design rests on observed
behavior rather than reading.

## Scope

A standalone tool, `tools/fixtures/phone_attachment_primitives.py`, runs one child process under
the native `.venv` interpreter with temporary private HOME / HERMES_HOME / XDG / runtime roots set
before any native import. The child denies IP `connect`, `connect_ex`, `create_connection`,
`sendto`; AF_UNIX stays allowed. This is Python-level instrumentation, not an OS sandbox.

## Subcases (all synthetic)

1. Cache helpers: `cache_document_from_bytes` sanitization/containment into the active profile's
   cache; `cache_image_from_bytes` rejects invalid magic and honors the configured size cap.
2. `MessageEvent` carries path, MIME and caption without the path entering session identity.
3. `GatewayInboundMixin` preparation: `media_text_inlined` None / False / True, real native methods.
4. Busy handling: base fallback versus the runner's `_queue_or_replace_pending_event`
   (PHOTO/TEXT merge, DOCUMENT FIFO, differing security scope as negative control).
5. Durable row: the real native flush helpers write to a real `SessionDB`; read back.

A subcase whose call path needs the full gateway, a model, network or credentials is reported as
`EVIDENCE_GAP`, never replaced by a shadow implementation.

## Non-goals

No full gateway start, pairing, TLS/server, model call, external network, installed CLI, live
home. The native source is read-only; the running approval matrix is neither reused nor disturbed.

## Acceptance

- Source fingerprints of every exercised owning file match before and after.
- Output is a status summary (booleans, counts, status codes): no prompts, transcripts, ids, keys
  or cache paths.
- Synthetic scratch is removed and never exported.

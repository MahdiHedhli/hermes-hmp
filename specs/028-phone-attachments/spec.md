# Spec 028: explicit Phone Photos/Files attachments

Status: D4 normative/interface and bounded pure-source v4 checkpoints independently accepted,
2026-10-03. Root's exact-v4 focused results: Python56, existing contract/module regression115,
Dart71 passed, failures0; four-path Ruff and eight-path Dart analysis clean. This completes only
D4-I and D4-P pure work, not operational/route/storage/native/device/provider/release acceptance.
Normative authority: [revision 1 contract](contracts/HMP_PHONE_ATTACHMENTS_V1.md). Historical Mobile
D1/D2/D3 and September planning inputs remain preserved unchanged; D4 supersedes conflicts.

## User outcome and scope

The complete intended flow is explicit Phone route, OS selection, encrypted review tray, explicit
Send into the existing pending slot before upload, bounded issuer-bound upload, one combined POST,
atomic native no-defer admission, actual own-CMID native row and reopened row-bound bytes. All are
required; upload or a local thumbnail is not completion. Bot Chat retains its draft and unsupported
state; no fallback/second Desktop owner. Attachment-first absent native session is supported only
through native atomic compare/create-or-refuse, never prior dummy text or HMP-created session.

## Requirements

- FR-1: PA-1..PA-7 define authorization, lowering limits, target binding, wire/errors/hash, native
  settlement, lifetime/resource/file/decoder bounds, original documents and ordinary Photos.
- FR-2: product + and all production attachment routes remain closed without actual required native
  no-defer/present-or-absent admission and validator/storage/privacy/device gates. Later/unknown
  builds attempt required APIs, no revision allowlist. Inspected 8afaab37 gap is bounded evidence.
- FR-3: same strict Phone slot for text/combined; same shared host Phone CMID namespace. Unknown
  record kinds block; stale clears cannot overwrite; replay checks current issuer before metadata
  and precedes new expiry/claim. Ambiguity never becomes automatic resend or text substitution.
- FR-4: constructor/string/stamp/reference/row metadata alone confers no authority. Private
  foreground/controller capture and fresh native canonical own user CMID row are mandatory;
  actual futures hold budgets through terminal reader/worker/native settlement despite UI loss.
- FR-5: encrypted draft bytes expire independently of locked ambiguity metadata. Owned-file chunk
  algorithm/key/nonce/AAD/finality/crash format is a separate freeze before adapter source.
- FR-6: complete own-upload history uses retained finite non-evicting metadata, no shadow native
  row/text copy; exact-path suppression never becomes an arbitrary file grant or global regex.
- FR-7: OS-scoped Photos/Files permissions, review/remove/cancel, explicit text-only confirmation;
  no bytes leave before Send, no camera/paste/Folder/URL/host @/audio/video/inline PDF/executable flow.

## Security and open gates

SECURITY.md and constitution apply: pinned per-connection transport; exact issuer/profile/instance;
revocation before/after await; descriptor-safe private custody; bounded data/CPU/memory/copy quotas;
original PDF untrusted, normalized images independently validated; content-free DTO/errors/logs.
No native exception/body/path/ID/hash/reference/label leak. Current native full dispatch/absence
admission gap remains open. Portable closed host decoder and exact encrypted envelope remain open.
Native/OS/model/backend/complete-flow/physical-device/release tests are unexecuted in this slice.

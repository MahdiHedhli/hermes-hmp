# Native reserved file close — coupled implementation tasks

Status: implementation not started. Source baseline `744d75d`; the companion
JSON records exact source hashes and lexical sites, not completed graph proof.
This implements the existing reviewed file-effect contract. It neither replaces
bot-character/local-media delivery nor establishes an upstream prerequisite.

- [ ] NC1: preallocate original open/result/close claims in the original ledger;
  reserve one cleanup attempt before open, under the shared ceiling. Bind the
  actual owner, scope, parent descriptor claim, arguments and original actor/functions.
- [ ] NC2: record actual returned fd before callbacks/allocation; return an immutable
  opened descriptor that retains original claims. Handle post-open allocation failure
  through the held actual fd and preallocated cleanup claim; never guess unknown fd.
- [ ] NC3: consume original reserved close once, after original actor verification,
  independently of failed work/current root/namespace drift. Preserve actual close
  return before postchecks. Unknown close retains debt and must never retry.
- [ ] NC4: migrate every shared descriptor consumer in NATIVE_CLOSE_CONSUMERS.json
  with NC1–NC3 in the same qualified candidate: package, entry, runtime/cache,
  approval/continuation resource facts and history. Read status from independently
  anchored native claims; mutable pending rows cannot manufacture closed credit.
  Use a fixed refusal transition rather than setters on native wrappers.
- [ ] NC5: distinguish legitimate in-flight cleanup from new work; extend ledger
  shape without making general currentness a cleanup gate. Preserve legacy reads.
- [ ] NC6: causal tests: namespace/root/registration drift, forged/copied row,
  wrong actor, revoked work, consumed reservation, reentrancy, reused fd, returned
  open followed by allocation failure, unknown open/close, post-return interruption,
  modified resource/history mirrors and unchanged legacy configuration/approval.
- [ ] NC7: independent exact coupled review and serialized current/floor/combined
  suites; preserve all failures and original progress/debt, no fixture protocol repair.

Open+close metering alone is not six-operation quota completion. Directory iterator
work, loader/factory/key/ABI/transport binding and physical character/local-media
acceptance remain separate incomplete work. Do not deploy a partial NC1–NC4 migration.

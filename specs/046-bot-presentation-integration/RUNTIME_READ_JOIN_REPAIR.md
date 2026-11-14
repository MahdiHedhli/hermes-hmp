# Runtime read plan join and close-status repair

The bounded synthetic normal diagnostic on source9dc2875 recorded its first
refusal at `_new_native_read_file_step`'s initial plan check. `_file` had passed
the entire five-part `_begin_native_declared_walk` result instead of its original
plan at slot0. This successor passes that plan while retaining the complete held
receipt for `_finish_native_declared_walk`; all plan/registry/lifetime gates stay.

The migrated actual close-ACK fault also exposed an optimistic `.closed` mirror:
it reported true after raw None even with unknown acknowledgment and no receipt.
The mirror now requires typed state, unknown/refusedFalse and matching actual
receipt(close, samefd,None). Original raw return and attempted state remain; no
close retry is introduced. The authoritative original-ledger validator is still
required, and constructed mirror DATA alone cannot authorize closure.

Original68 reader38pass/30fail and cleanup diagnostic2pass/2fail remain preserved.
These repairs await source review and focused tests before broader execution.

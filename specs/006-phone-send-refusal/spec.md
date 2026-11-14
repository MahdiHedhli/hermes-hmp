# Phone send: definitive refusal (AP-6)

Status: contract repair. This is HMP's own wire issue, not a `HERMES_API_GAP`. No upstream Hermes
change, no new error code, no shipped manifest entry. The independent approval manifest stays
empty, so nothing here enables approvals.

## Problem

`_phone_turn` treated any falsy delivery result as a refusal and any truthy one as submitted, and
the refusal body lacked `applied:false`. A client could not tell "not sent" from "maybe sent".

## Acceptance scenarios

1. Delivery returns exactly `False`: `503 api_server_unavailable` with top-level `applied:false`,
   stored status `rejected`, no transcript observation.
2. Same-id replay returns the stored body and never calls delivery again.
3. Delivery returns exactly `True`: `202 {"state":"submitted"}`, unchanged.
4. Delivery returns `None`: `200 {"state":"unknown"}`, stored `unknown`, no `applied`.
5. Any other result (`0`, `1`, `""`, `"yes"`, containers, objects) is uncertain: `200 unknown`,
   never admitted and never a definitive refusal.
6. A delivery exception, missing/empty/non-string session key, or non-list approval probe stays
   `503` without `applied`, stored `unknown`.
7. The existing `409 stale` / `applied:false` gates (pending approval, open clarify) are
   unchanged, and a fresh gate reply does not settle an earlier ambiguous attempt.

## Why `False` is definitive

`Bridge.deliver_phone_message` returns `False` only when a reject-policy admission ticket reported
a known refusal (busy, draining, precondition head/expired, lease timeout, unauthorized). None of
those admit a user turn. Background handling may already have been scheduled before a later
admission refusal; this marker proves not admitted, not that no worker ever started.
`refused_other` covers `persist_failed` and `unreported_exit`, whose detail is not on the ticket,
so it returns `None`. A missing ticket, unclassified outcome and the five-second timeout are also
`None`. With a ticket, the initial `_gateway_accepted` flag is never consulted.

### The scheduling flag is not a refusal

Hermes `8afa3703` `BasePlatformAdapter.handle_message` sets `_gateway_accepted = False` first. On a
busy session with `busy_text_mode=queue`, the text-debounce path (`base.py` ~4074-4078) retains the
event and never sets the flag `True`, yet the event runs later. Mapping that `False` to a
definitive refusal made the phone report `applied:false` and invited a duplicate resend. Builds
without a ticket now return `True` only for an exact `True` flag; `False`, missing or non-boolean
is `None` (unknown). AP-6 stores `unknown`; a replay returns it and never redelivers.

Evidence: `server/tests/unit/test_bridge.py` (flag/ticket matrix) and
`server/tests/unit/test_phone_admission_real_hermes.py`, which drives the real 8afa
`handle_message` (busy session, queue mode, isolated `HERMES_HOME`, synthetic profile) in the
build's own interpreter. Limitations: that fixture has no gateway runner, model turn or
reject-policy ticket, and runs only on builds whose `MessageEvent` has no `defer_policy`.

## Out of scope

Route parsing, version policy, idempotency retention.

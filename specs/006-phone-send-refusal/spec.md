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

`Bridge.deliver_phone_message` returns `False` only if `handle_message` returned with the event's
`_gateway_accepted` unset, or the admission ticket reported a known refusal (busy, draining,
precondition head/expired, lease timeout, unauthorized). None of those admit a user turn.
Background handling may already have been scheduled before a later admission refusal; this
marker proves not admitted, not that no worker ever started.
`refused_other` covers `persist_failed` and `unreported_exit`, whose detail is not on the ticket,
so it returns `None`. Missing ticket, unclassified outcome and the five-second timeout are also
`None`. Older builds without a reject-policy ticket use the synchronous flag (`True` or `False`).

## Out of scope

Route parsing, version policy, idempotency retention.

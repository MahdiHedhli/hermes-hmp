# Bot Chat history from the start

Status: draft implementation. This read primitive enables phone-only search of authorized Bot Chats without sending search terms to Hermes.

## User outcome

The phone can page a Bot Chat's active messages from its first available row, then continue with the existing `after=<id>` route. An older HMP release fails clearly because the new route is absent; it cannot silently return a latest snapshot instead.

## Acceptance scenarios

1. For a listed canonical Bot Chat, the first request returns the earliest active page and current head. A subsequent `after=<last-id>` request continues in order.
2. A missing, foreign-user, or foreign-profile session ref returns the same `404 not_found` as SES-2, without revealing session existence.
3. A bot without authorization, a missing bearer, or a disabled session-browsing flag cannot read old rows.
4. A rewritten lineage returns the existing reset shape. A malformed or excessive limit returns `400 bad_request`.
5. The route accepts no search term and invokes no Hermes search method; normal logs contain no message text.

## Constraints

- The route uses the existing `Reads.session_history(..., after=0)` and bridge read path. No new Hermes internal import or compatibility fingerprint is introduced.
- Retain the existing per-device read limiter, per-bot authorization, opaque session ref, and response projection.
- The route returns active history available to HMP, not a promise to recover messages removed by Hermes compaction.

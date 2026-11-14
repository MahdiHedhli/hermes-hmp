# Plan: phone send definitive refusal

1. `prompts._phone_turn`: `accepted is False` returns `_error("api_server_unavailable", ...,
   applied=False)` with status `rejected`; `accepted is not True` (None or malformed) returns
   `200 unknown`; only exact `True` submits. Uses the existing optional `_error(applied=)`.
2. `bridge.deliver_phone_message`: a ticket decides on its reported outcome; without one, only an
   exact `True` flag is accepted and anything else is `None` (see spec: the flag is not a refusal).
3. Contract AP-6 paragraph in `docs/architecture/contracts/HMP_V1.md`.
4. Tests in `server/tests/unit/test_phone_send_refusal.py` and one bridge test.

# Public protocol research note

## R16. Refresh retry grace

A P5 successor is derived from the raw presented refresh token using `transcript("HMP1-GRACE", refresh_raw, family_id, purpose)` and a dedicated HMAC key. This tag is server-internal and is not a V-1 wire tag. The raw token and derivation key must never be logged or stored together.

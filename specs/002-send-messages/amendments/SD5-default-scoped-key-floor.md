# SD5 default scoped key floor defect repair

## Scope and contract

Existing DS-6/bridge length-only rule must apply equally to default inline, named scoped, and default scoped fallback keys. The current default fallback accepts any string, incorrectly reporting a usable endpoint for short/blank scoped values. Native startup separately rejects weak default listener keys; this is gate correctness, not a demonstrated authentication bypass. Base3e676ec; source census retained privately.

## Plan before implementation

1. Replace only default-scoped `isinstance(str)` with existing `_has_usable_secret`, preserving exact raw credential bytes and all precedence/scoping/loopback behavior.
2. Add synthetic fake-Hermes tests for None/non-string/empty/blank/15-char/padded15 rejection, exact16/17/padded16 acceptance, no rejected value logged, existing inline-authoritative rejection and named no-inheritance controls.
3. Independent exact-source/test review before focused fake-only execution. Run configured lint, focused default/named endpoint tests (exclude socket probe), and publish a focused draft PR with exact result.
4. No credentials/config changes, real Hermes/device/provider/network tests or live deployment. Length-only check is not entropy/placeholder/native-auth certification.

## Security and acceptance

Rejected fallback yields no endpoint; accepted fallback retains raw key unchanged and default path prefix. Short present inline remains authoritative and never falls back; named profile never inherits default/inline key. Error/logs contain no key. Native callback/backend admission and full release security review remain separate. All authorization, generation, idempotency and transport rules remain unchanged.

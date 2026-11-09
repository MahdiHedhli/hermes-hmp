# LM-ENT1-N1: native publication contract census — November 8

Status: evidence-backed gap in the exact inspected HMP/native call path; not a
claim that all Hermes APIs lack the capability. No upstream edits or live feature,
authorization, configuration, credential, job or provider reads were performed.

## Pins and scope

Native immutable Git source: `0f0e96fc8e7fd35aba406e4a9fa341fb969d0b41`, freshly
resolved from the existing LLY520 checkout. This is source evidence, not a fresh
running-process byte binding or live latency measurement. HMP bridge path inspected
at `f7f5084`; the publication branch retains that bridge unchanged.

| Native method | Source | Method SHA-256 |
| --- | --- | --- |
| `_is_user_authorized_for_source` | `gateway/run.py:3755` | `cc15a8d1a905353601a4554b4c90e718b92fe955d7110c5f2f92153d66018fd9` |
| `served_profile_names` | `gateway/run_profile_reconcile.py:96` | `fa410670cd802b0a1d05f0f52a0fd68cf55b4d2f6ec932a365c3c0163fd7306f` |
| `build_source` | `gateway/platforms/base.py:4713` | `81948c762ade35d41e5e762719f968fed3ad67e2ddf6f756e16585b84cccb90a` |
| `_authorization_home_for_source` | `gateway/authz_mixin.py:421` | `4324aae77c63ab2d2c784067b329fe1944fd340e73e13f6c41cd01768172a503` |
| `_is_user_authorized` | `gateway/authz_mixin.py:732` | `6e3903a7c6cbb1389b2d3b133904762a26cb850e4a660dac2e359c598daffd0d` |
| `_profile_runtime_scope` | `gateway/run.py:1795` | `d4b77401bfa2d62948656aa0dce3ecb06be9853436896bf8200be6cd6bd786e3` |

## Observed contract

HMP `HermesReadBridge.authz_state` consults the served profile set, source routing,
allow-all refusal and native per-principal authorization. Native served-profile
bookkeeping returns a list; source construction consults live routing. Native
`_is_user_authorized_for_source` returns a Boolean under an authorization-profile
scope. That scope calls `_profile_runtime_scope` with its default credential
hydration behavior; the implementation may perform profile/secret/terminal scope
work. Nothing here was executed against a user's credentials.

Principal authorization consults pairing approval, environment/configuration,
adapter and profile grant sources. The exported calls do not return a monotonic
revision, native-owned read lease, invalidation receipt, or pure final-publication
predicate covering those sources. A bounded gateway source search for
`authorization.*epoch`, `authorization.*revision`, `authorization.*lease` and
`authz.*snapshot` found no matches. This supports the scoped census only; different
names or other interfaces may exist and require separate evidence.

## Consequence and prerequisite

A cached Boolean plus HMP listener generation cannot replace current authority.
Moving the native check to a worker is valid observation collection, but it does
not create a publication lease. Do not use private `hydrate_secrets=False` or
`owner_secret_scope` as an authorization shortcut, and do not infer native policy
currency from a polling interval or file timestamp.

The final pure gate on this call path needs a supported native contract bound to
the original transport/profile/principal and routing scope: either a native-owned
read lease/final claim or an authorization/routing/configuration publication
revision with invalidation before every relevant effect and settlement afterward.
Its coverage must include the actual pairing/configuration/grant writers, including
other processes where supported. Old uncoordinated writers cannot silently become
safe because a newer reader exists. Capability negotiation and actual API support,
not an exact-version allowlist, determine availability.

Independent read-only review confirmed this bounded finding. It did not execute
native methods, inspect private settings or establish whole-SDK absence.

## HMP work that remains implementable

Continue fixed Store observer and listener-actor coordination, typed same-UID
operator mutation/CAS/readback and lifecycle/retirement integration. These remain
necessary but insufficient for native authorization publication. Keep LM-ENT1-N1
explicit and the new pure-gate path undeployed until the native conjunction is
supported. Existing deployed image, jobs, model and approval behavior is unchanged;
this gap does not justify a global feature/version shutdown.

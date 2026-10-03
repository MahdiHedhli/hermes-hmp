# Push-seal conformance source (TEST ONLY)

Status: **SOURCE/PREPARATION ONLY, UNEXECUTED**. This is not a generated or
reviewed known-answer corpus. No dependencies have been installed or imported,
no keys/crypto primitives/corpus have been executed, and no app or server
production source changes. Independent source/preparation review and a new root
execution admission are required before any installation or run.

This isolated test directory implements the accepted 2026-10-03 plan's first
source slice: Node @hpke/core1.8.0 + canonicalize5.1.0 generation; independent
Python PyCryptodome3.23.0 + rfc87850.1.4 opening, JCS, SPKI/DER/signature checks.
Exact common1.9.0 is the only Node transitive dependency. No Python extras,
source distribution builds, dev dependencies or production dependency changes.

`generate.mjs` first pins its source/data/package files, then uses only the
library's public D1 APIs and test-only `ekm`. It compares the single official
D1 entry's 257 encryptions,3 exports, public/private serialized fixture keys,
enc and KEM shared_secret. It states the private/unexposed key schedule/nonce
outputs as such; it does not reproduce HPKE internals. HMP cases use one fresh
context per case, sequence0 and deterministic labelled TEST-ONLY ekm. This
mechanism exists only in this tooling directory and is never a production RNG
option. ECDSA uses Node's vetted builtin crypto and the existing published
TEST-ONLY instance signing fixture, distinct from the official recipient key.
Randomized signature bytes are checked semantically and excluded only from
regeneration byte equality. The checker verifies both S forms using vetted
PyCryptodome DER decode/encode and ECDSA verification.

`check.py` imports neither generator nor production/native code. It opens all
257 official ciphertexts in order, verifies the public recipient bytes, then
independently opens and checks all HMP definitions with an offline reference
pipeline. Its actual opener attempts are counted. It has no provider operation
and reports provider_calls0 only for this reference: it is not instrumentation
of the relay or proof of production zero-provider/error ordering. It does not
implement replay, clock/limit atomicity, allowlist configuration or HTTP. Those
need later actual consumer causal tests. `domain_ok` checks the restricted
plaintext integer domain only;0/u53max expiries are not HTTP eligibility cases.
`eligible` means pre-provider reference checks succeeded, never provider202.

`cases.json` has151 finite unexecuted definitions:16 eligible,2 domain controls,
63 shape400,12 auth401,16 HPKE422,34 plaintext422,8 binding422. Exact IDs/order/count
are checked; no silent skips. `data/rfc9180-test-vectors.json` is the whole original
RFC-cited public data file, SHA256
`61fc662f01996cd06d713dacf5e133167bd309a1f329442d53f1e21a47b3ede6`.
Hex preserves invalid UTF-8. UTF-8 size, full kid/aud grammar, single-shot65byte
enc||taggedct,82..1105 envelope,1024plaintext,4096body, original canonical bytes,
empty FCM environment signature field and raw R/K/C/digests are explicit.
See `SOURCE_PRECISION.md`: unknown outer members are ignored per frozen PR-3;
opened plaintext unknown members are rejected per PN-SEAL-1.

`dependencies.lock.json` pins exact archive/wheel digests and every retained
archive entry's bytes. `data/*` retains official registry/tag/advisory/license
metadata as data. Integrity equality is not a registry-signature/provenance
attestation or safety proof. No archive hooks or source were executed. Private
archives/receipts and existing-runtime hash evidence are supplied separately
for the independent preparation reviewer, not downloaded during execution.

The executable output schema is closed by `TOP_KEYS`/`ROW_KEYS` in the independent
checker and documented in `schema.json`. Generator output remains explicitly
not independently verified; a separate checker receipt is required. Neither
receipt can certify T025 transport,T030 production relay or T043 native sealing.
The optional stdlib regeneration comparison only excludes signature bytes and
requires prior valid checker receipts for both outputs. Future corpus adoption
is a separate gate, after independent results review.

Read `EXECUTION_PLAN.md` for the concrete isolated future steps. It is a plan,
not authorization to install/run. Production HPKE custody/CSPRNG/closed app key
map, native/Dart interoperability, owner O1..O6, provider/platform/device delivery,
replay restart residuals, DesktopT029,A5 and Play remain open. These assets must
not be included in a production plugin/app artifact: public test private keys,
deterministic hooks and test packages require explicit artifact-exclusion checks.

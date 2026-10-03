# Source precision addendum to the accepted vector plan

This is an additive implementation precision for the exact frozen contract,
not an edit to the accepted original plan or a new wire rule.

Frozen HMP_PUSH_RELAY_V1.md SHA256
`7c7cb585b8513cd25122fe532a03d3cefa7b0213bea831c1891c28af5d9720a3`,
PR-3: “Unknown request fields are ignored by the relay and carry no authority,
because the signed transcript covers only the named fields”.

The original plan's negative-case shorthand “unknown/extra/duplicate fields”
400 must be read with that authoritative distinction. `unknown_outer_ignored`
is a positive reference-control: a well-formed, bounded unknown outer string
field leaves all named signature fields unchanged, carries no authority and
advances to eligibility under the synthetic configuration. It is not included
in the signature transcript; removing it gives exactly the same transcript.
Missing required outer members, duplicate names (including escaped-equivalent
names), wrong known-field types/values, invalid I-JSON and bodies over4096 bytes
still refuse at shape400. Unknown outer fields cannot override a known value,
add a new provider action, change the HPKE suite or supply configuration.

PN-SEAL-1's opened plaintext is closed: unknown/extra, missing and duplicate
members are plain422. Outer ignore-unknown is not applied to that plaintext.
`plain_extra` is encrypted valid HPKE and must actually open before rejection.

This correction requires explicit independent source-review attention. The
original plan remains byte-exact as immutable history. The source-only author
and root agreed this precision; it does not claim executed relay behavior.

## Source review amendment: outer pairs and ignored numeric lexemes

Independent source review A1 requires APNs with `apns_token`, or FCM with
`fcm_token`/`fcm_fid`, at shape400 before the reference opener. Three new
negative definitions cover all mismatched pairs and require zero opener calls;
existing valid pairs and valid-outer/different-sealed-platform binding422 remain.
This implements the frozen relay step1; it adds no wire rule.

C1 disposition: the stdlib JSON decoder preserves outer fraction/exponent
tokens as opaque `NumericLexeme` objects rather than coercing them to floats.
Known integer fields still require exact Python `int` and their existing
unsigned53/type limits; fractional/exponent forms are refused for those fields.
Unknown tokens such as `3.14` and `1e400` are ignored without numeric arithmetic,
infinity coercion, signature authority or configuration authority. Literal
`NaN`/`Infinity` remain invalid JSON. Body4096 and recursion limits still apply.

RFC7493 double-precision representability recommendations do not introduce an
additional mandatory range bound on ignored values in this reference model.
The earlier phrase “invalid I-JSON” covers enforced UTF8, duplicate names and
unpaired surrogate prohibitions; it does not certify every numeric precision
recommendation for ignored fields. This is not a general I-JSON oracle. Opened
plaintext keeps the closed schema, numeric-lexeme rejection and exact JCS check.
The two new eligible numeric controls also assert removal leaves the transcript
unchanged. All151 definitions and six pure methods remain unexecuted pending
targeted independent review and separate runtime admission.

## Public registry metadata minimization

The five `npm-*.json` / `pypi-*.json` records are selected-fields provenance
records, not complete registry responses. Each records the official source URL
and SHA256 of its original response. Original responses are preserved privately
for independent comparison; they are not downloaded or read during execution.

Npm retains name/version/license, dependency and engine requirements, distribution
metadata (including declared integrity/signature/attestation references), and
repository metadata. PyPI retains package identity/license, requirements/project
URLs, and each release file's filename, digests, URL, size, type, interpreter
requirements, yanked state/reason, upload timestamp, core-metadata and signature
flag when present. No signature or attestation is verified by this selection.

Author/maintainer/publisher contact, description and unrelated registry fields are
omitted. This removes public contact fields flagged by the repository privacy
gate without adding scanner suppressions or modifying package/archive/license
bytes, source algorithms, case definitions or execution admission. A raw-response
hash binds the original evidence; it does not prove safety or certify provenance.
All151 definitions and six pure methods remain unexecuted.

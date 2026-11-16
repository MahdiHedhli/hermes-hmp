# Registry generation witness reconciliation — November16, 2026

This test-only repair attributes the existing permission-generation additions in
`e1d88b6f62a99068e8bd5c69de5ca099f2afcfd6`. Production registry bytes remain identical
to public183a: SHA256 f0b040c142945eead90befac8df40ffefff89239597ea4c4fb0c2ac9d5682f64.
The earlier frozen witness still expected the pre-addition registry and failed
both on unchanged183a and the image-cache compatibility branch.

The new preservation helper first requires that exact current hash, then reverses
only unique literal e1d additions: Caller/Binding fields, their validation calls,
the bounded primitive validator and caller-generation equality. It finally requires
the original b49e6e6205805f38144e769f742f6e3ee918536aa6dd5f66e6c8096d8f77c2b2 hash.
The original FROZEN value is unchanged. Unknown validator/comparison/source changes
cannot be stripped or silently accepted by replacing the old hash.

249 selected tests pass, including original registry/batch cases and new original-
hash preservation, unknown-delta refusal, all four generation coordinates, malformed
inputs to both constructors and exact accepted-data retention. Independently of
that hash witness, isolated comparison removal causes5 behavioral failures and
validator removal causes24, with zero errors. The original production source stays
byte-identical throughout. Independent bounded review accepts this repair.

This reconciles historical source preservation only. It does not prove new memory/
allocation funding, native acquisition, device authorization or runtime/release
qualification, and transfers none of the old native/platform results to new code.
The expanded selection across nine test files also passes1,048 distinct cases with no failures,
errors or skips. The image-cache feature branch must be tested again after
composition. Repository-
wide lint and all native/Linux/private/physical/release gates remain separate.


The image-cache compatibility composition subsequently passed1,065 distinct cases
across nine selected test files. Its production files remain identical to the
previous image source; this is not an additional native/runtime qualification.

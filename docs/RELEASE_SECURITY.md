# HMP release security gate

Use a `release/*` branch after the feature set is frozen. Every push to it runs the ordinary
plugin CI and a separate read-only source review against that exact commit. The review requires
`OPENAI_API_KEY` in this repository's GitHub Actions secrets; it fails closed if the secret,
review output, commit match, or passing verdict is missing. Never commit the key.

The source reviewer checks pairing, device and profile authorization, owner-only write gates,
replay and ambiguous sends, approvals, compatibility fingerprints, resource limits, and logs.
The verdict gate rejects `REJECT`, `OPEN`, or any blocker or high-severity finding. It prints
only a count of lower-severity findings to public CI logs.

Before enabling a guarded capability or distributing a plugin release, also verify the exact
Hermes build in the isolated gateway/PTY fixture matrix, retain the build's fingerprint and
test report, run the zero-baseline privacy scan, and resolve open security findings. Source
review alone cannot prove runtime behavior. Do not point fixture tests at a live Hermes home.

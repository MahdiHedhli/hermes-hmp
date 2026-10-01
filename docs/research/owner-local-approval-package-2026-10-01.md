# Owner-local approval package derivation

Research tooling and a private local-dogfood candidate only. Nothing is installed or
admitted by this note. Public production approval/direct-send manifests remain empty.

## Derivation

The integrated runtime in draft PR #65 passed all seven fixture stages and exactly
27 required integration cases at `f584b91`; docs head `d2aff3c` has the same runtime.
The packaging tool reads the exact tracked tree from Git objects. It changes only
the two `builds` arrays (approval and direct-send) from empty to one exact-source
fingerprint/Git entry, preserving every other file, mode and manifest field.

Before building or verifying it delegates to the existing full
`validate_approval_receipt(final=True)` for the clean integrated source, using its
approval, read and direct-send lists. That unsigned receipt is deliberately stale
for the package by plugin digest; it is never relabelled or waived. Separate package
digests, byte/mode inventory, the exact manifest-only delta and the package's own
parser/matcher bind the derived package. Fixtures already exercised the same exact
fingerprint/Git match decision with provisional labels. Any code or source change
needs fresh qualification.

Entries describe a Hermes source build, not an owner, host or device. Local custody,
target installation and existing explicit grants impose owner-local scope. An
explicit host denial still closes approvals; controls-only grants do not create an
approval owner. The configured owner list is still required.

## Verification

Independent Opus review passed the tool and actual private candidate conditionally.
The full source validator, exact package delta, inventory and parser checks passed.
Root independently reverified the original package and pinned its whole-tree digest,
plugin digest and both manifest hashes. It was not regenerated. Root passed 39
focused tool tests after lint-only wrapping/import corrections; configured ruff and
the private-data scan passed. No native matrix, live host or device was repeated.

`verify` reports a digest; it does not pin a previously reviewed package by itself.
The operator must compare its returned tree/plugin/manifest digests to the reviewed
record before admission and verify the installed bytes afterward. A differently
labelled entry can still match the same build; its different digest must not be
confused with the reviewed package. This is local evidence, not a signature.

## Remaining admission gates

- Current target disk identity and clean source; same qualifying Python minor.
- Unchanged exact app artifact, source privacy and native crypto evidence.
- Existing owner/device/profile grants and flags, with no host denial.
- Active-work drain, rollback package, install and a fresh gateway process so the
  qualification latch evaluates the new bytes; disk hashes do not attest memory.
- Runtime dependency/compat checks after restart, followed by a real phone approval
  card/answer, expiry, denial and reconnect test.

The public release workflow remains a separate gate. No host keys, grants, profiles,
jobs, messages, app pin, website or store release changes occur in this tooling.

# Fixed private gateway startup selection

Status: bounded source loader accepted; fixed trusted entry/operator approval,
complete inventory/loader validation and native/key factory composition remain
open. This is not an installed configuration, credential generator, activation
command, admission token or authority to serve character images.

## External selection and owned file read

`StartupSelectionOwner.load` accepts the original early activation owner and one
external ExpectedArtifact (absolute path, exact size and SHA-256). The fixed
trusted entry/operator must supply those expectations independently before
listener creation. Computing an expectation from the same file on demand is not
operator approval. Neither an HTTP request, peer transcript nor a caller-built
expectation can supply the future factory's trust root.

The only accepted leaf name is gateway-startup.json,1..65536 bytes. Descriptor-
relative no-follow traversal checks ancestor ownership/write policy, original
relationships and stable metadata. The immediate directory must be owned by the
original effective uid with mode0700; the leaf must be a single-link regular file
owned by that uid with mode0600. Actual size, exact EOF, hash and before/after
metadata are verified through the same retained descriptor owner as artifact
checks. Separate fixed internal owner types/activation slots let config loading
and later artifact observations coexist without resetting either owner.

The loader refuses a late load or gateway/listener startup appearing during its
checks. It calls no PM selection/activation API, creates no files/keys, imports no
provider and makes no host connection. Unknown read/open/close outcomes remain
attributable and cannot be retried as a new selection. Local descriptor cleanup
uses original context/custody even after retirement, not renewed live authority.

## Closed canonical document

JSON must exactly equal its ASCII sort_keys/separators=(comma,colon)/ensure_ascii
canonical encoding, with no extra whitespace, newline, duplicate/unknown/missing
keys or alternate scalar types. Booleans are not integer versions. The exact
schema is:

| Field | Required value or encoding |
| --- | --- |
| schema | Integer1 |
| kind | HMP_GATEWAY_STARTUP_SELECTION |
| iid | Canonical lowercase unpadded Base32 of exactly32 bytes, matching HMP wire semantics |
| protocol | Integer2 |
| algorithm | Ed25519 |
| credential_generation |64 lowercase hexadecimal characters; credential generation, not a Hermes commit allowlist |
| gateway_public |64 lowercase hexadecimal characters encoding32 public-key bytes |
| broker_public |64 lowercase hexadecimal characters encoding32 distinct peer public-key bytes |
| gateway_inventory_sha256 |64 lowercase hexadecimal characters |
| broker_inventory_sha256 |64 lowercase hexadecimal characters |
| loader_policy | darwin-system-loader-trust or linux-system-loader-trust, matching the actual supported platform |

No private seed, bearer, provider credential, command, URL, profile/home path,
arbitrary key path or permission change is accepted as a document field. The
selected installation directory is retained from the original filename; it is
not chosen by parsed data. Later fixed key/inventory path derivation and actual
native instance/generation binding belong to the remaining factory contract.
Minimum native version/API policy remains separate from install integrity; no
Hermes tested-build equality gate is added.

## Result and failure ownership

The parser returns immutable public selection DATA only after file integrity and
canonical validation. The owner retains an independently anchored root fact and
requires all publication slots empty before writing it. The original root/scope/
buffer/fact cells are rejoined after callbacks; a replacement is not overwritten.
Failure withdraws only this owner's exact held published fact, leaves a different
replacement intact, refuses recapture and clears the original accumulation buffer.
Temporary immutable raw references are released; this is not a claim of secure
erasure of every Python heap copy. No raw configuration/error path is logged.

A loaded selection is not evidence of trusted entry execution, operator approval,
complete reachable tree coverage, absence of unexpected files, admitted future
imports/extension libraries/OS-loader roots, original PM lease custody or native
permission. The fixed startup factory must join all required original owners
before loading role keys, accepting terminal closure, ACK, resource release or
fresh native PRE_EMIT/authenticated image publication.

## Bounded verification

30 isolated private-config cases,18 actual selected-file cases,25 activation
cases and310 layout/import checks passed:383 in5.71s. Source hashes did not change
during that run; lint, plugin surface and whitespace pass. Independent read-only
source review accepted the final primitive/canonical IID, late-load, original-cell
and pre/post-publication withdrawal checks. Reviewer performed no runtime actions.

Cases cover modes/links, unsupported/unknown/noncanonical/duplicate/scalar fields,
canonical IID padding bits, wrong expected hash/name/size, changed ownership cells,
lost close acknowledgement, retirement and startup during read, original-buffer
wiping without wiping a replacement, Foreign digest zero callbacks, pre/post-root
fact replacement and no recapture. Children used private synthetic files/minimal
environments; no installed gateway, private host credentials or real keys were
read or changed. Actual Linux/Darwin startup, host/device and release qualification
remain separate. Earlier unexplained broker regression failures remain open.

## Historical handoff after native startup

`retained_data()` returns only the originally verified immutable data after native
startup or namespace eviction; it does not repeat file/import/path selection or
relax fresh-load guards. Original owner/scope/fact cells and known-closed custody
are checked before and after actual process/user/thread sampling. Context or fact
replacement refuses without overwriting newer state; wrong-thread reads refuse
without retiring the original snapshot. Package projections retain original raw
manifest, entries, primitive file observations/metadata and origin strings, never
mutable module/spec/loader objects. These historical observations are not current
runtime admission, operator approval, native authority or permission to load keys.
The fixed startup factory must independently establish those remaining joins.

Verification:36 configuration and26 package cases, plus18 artifact,25 activation
and311 import/layout checks:416 passed in8.20s with source hashes unchanged. Cases
cover late startup, namespace eviction, path changes, wrong thread, root fact drift
and drift during context sampling; package publication also preserves a foreign
pre-publication fact. This is isolated source qualification, not installed runtime
or physical device/image-display qualification.

## Explicit schema versions and remaining complete recipe

`StartupSelectionOwner.load` remains fixed schema1/package-only. The separate
`load_recipe_selection` selects schema2/full-recipe-pin semantics before reading;
there is no document-driven autodetection, downgrade or retry. Both enter the same
original IO/publication lifecycle and return GatewayStartupSelection with an exact
integer schema field retained at the end of the immutable tuple. A matching hash
without this retained version cannot establish recipe type or approval.

The old package verifier refuses schema2 before package acquisition, even with a
package-matching inventory digest. Both fixed loaders refuse alternate recapture
on the original activation and reject subclass dispatch before callbacks. Shared
private-file/canonical-schema/history/custody causals run against each version.
Four cross/unknown-version cases and package-only non-promotion are also covered.

477 combined checks passed in12.63s with source/fixture hashes unchanged. Review
accepted the version separation; this implements only the first GR1 slice of
[GATEWAY_RECIPE.md](GATEWAY_RECIPE.md). The complete recipe and four fixed child
loads, shared aggregate budget, entry/dependency/link/loader validation and actual
native/key factory are still open. A schema2 selection alone approves nothing.

The [GR1 document loader](GATEWAY_RECIPE.md#current-gr1-document-loading-source-checkpoint)
now reads the recipe and four fixed child envelopes under original IO/aggregate
ownership (517 combined checks). Full child-table/runtime/native/key admission
and fixed entry/operator composition remain open.

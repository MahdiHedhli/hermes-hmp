# Gateway factory recipe and pin ownership

Status: GR1 document-loading source implemented/reviewed; GR2 and GR3 remain
open. This is not runtime admission. No installed source, setting, credential or
route changes follow.

## Resolve the existing pin mismatch

The current selection's gateway_inventory_sha256 pins raw HMP_GATEWAY_PACKAGE
bytes. GatewayPackageOwner checks that exact hash before decoding a package-only
table. hmp_startup is a separate wheel package and is not in that table. Calling
this existing result a complete gateway recipe would omit executable entry code
and HMP crypto/dependency coverage. Reinterpreting its fact as approval or loading
keys after that check would violate CREDENTIAL_ADMISSION.md.

The complete factory must use a new explicitly selected configuration version and
a separately implemented recipe owner. Keep the existing schema1 loader/package
components available as source prerequisites; do not silently promote schema1
selection, synthetic_no_go, caller-built tuples or historical retained_data.
Unknown selection versions refuse this presentation startup only, with unrelated
HMP/gateway features left available. No automatic schema migration or key creation.

Schema2 selection retains the eleven schema1 field names, with schema=2. Its
kind remains HMP_GATEWAY_STARTUP_SELECTION. gateway_inventory_sha256 now pins the
canonical complete HMP_GATEWAY_RECIPE bytes, never a package-only table. The
factory selects the exact loader version before reading and cannot retry with
schema1 on failure. The independent installer/operator expectation still pins
the fixed private gateway-startup.json size and SHA. Receipt fields explicitly
record selection version and recipe kind; a bare digest is not a type witness.

## Closed recipe envelope

Use exactly these top-level keys, with no duplicate/unknown keys or coercion:

- schema: exact integer1.
- kind: exact string HMP_GATEWAY_RECIPE.
- generation: the selection's exact credential generation.
- plugin: {size, sha256}, referring to canonical HMP_GATEWAY_PACKAGE child bytes.
- entry: {size, sha256}, referring to a canonical entry-package child table.
- dependencies: {size, sha256}, referring to a canonical HMP-dependency child table.
- interpreter: {size, sha256}, referring to the independently selected interpreter/
  standard-library origin and OS-loader policy record.

All child references are positive exact integer byte lengths and lowercase
SHA256 strings. Each child document is at most8MiB; four child documents plus the
recipe are at most32MiB aggregate. Existing stricter schema/table/file/depth/IO
limits also apply, including an aggregate budget shared across the entire owner;
calling the file verifier separately cannot reset counters. The recipe itself is
bounded64KiB. All documents use exact canonical ASCII JSON and reject trailing
bytes, duplicate fields, booleans as integers and malformed UTF encodings.

References are data commitments, not paths, commands, URLs or sign/approval APIs.
The fixed startup entry reads the documents from fixed names adjacent to its
private selected configuration: gateway-recipe.json, gateway-package.json,
gateway-entry.json, gateway-dependencies.json and gateway-interpreter.json.
No request, broker response, profile or parsed child field selects these paths.
Original descriptor ownership and one-close/unknown handling apply to every read.

## Native baseline versus HMP-owned executable coverage

The trusted administrator/installed-native-runtime premise is unchanged. Native
Hermes startup/PM selection, minimum-version/API support and actual import origins
are required. Hermes commits remain diagnostic; no tested-version equality or
allowlist is added. Do not hash the native checkout/home, configs, credentials,
profiles, chats, logs or unrelated native dependency packages. Do not invent an
original PM lease by making a new selection query or acquiring another lease.

The plugin table retains complete installed hmp_plugin files and unexpected-file
refusal. The entry table independently covers the complete installed hmp_startup
package and the exact fixed external wrapper, if that wrapper is not inside the
package. It joins actual retained main/file/spec/code and loaded module origins;
an equal copied table or matching filename is not original execution evidence.
PM re-exec returns through this same fixed wrapper before the recipe/key factory.

The dependency table covers the HMP-specific reachable Python/crypto/parser/native
extension closure under the actual retained PM generation, including resources,
bytecode/archives and non-system libraries used by those extensions. It must be
complete for HMP's fixed entry/factory/crypto/worker code paths, not the entire
native environment. Unrelated trusted native imports neither need an HMP table
nor become HMP-qualified modules. New files inside a declared HMP-owned package
root refuse; undeclared artifacts cannot be selected by future HMP imports.
This is not a promise that other trusted native code cannot execute.

Interpreter/stdlib roots and system-library loading remain explicit selected
trusted-runtime/OS-loader premises; do not label path membership as measured
loaded-library containment or executable attestation. Actual interpreter/PM import
origins must match the selected record. HMP-owned dependency/extension artifacts
need retained file observations, not only a distribution version or lock hash.

Keep the existing strict regular-file no-follow verifier unchanged. A required
interpreter or library symlink/hardlink needs a distinct reviewed bounded link/
resolved-target owner and an explicit selected link/target chain policy. Until
implemented and observed, refuse that artifact; do not waive single-link/no-follow
checks, use resolve() as custody proof or silently trust a same-named new target.
Windows/loading outside the selected Linux/Darwin policy remains unqualified.

## Original ownership and ordering

1. The independent installed entry retains partial startup ownership before native
   bootstrap. Preserve wrapper argv/orig_argv through any actual PM re-exec.
2. Capture the actual original activation generation/import objects. Retain the
   versioned private configuration owner before IO. Validate its exact independent
   expectation, then the full recipe and every fixed child under shared budgets.
3. Retain one original recipe scope/cell/fact before file/hash/module effects.
   Child package/dependency owners derive expected bytes only from that retained
   recipe fact. No arbitrary optional digest argument, generic verified boolean,
   caller-built qualification or new owner instance substitutes for its root.
4. Rejoin held invocation, activation, configuration, recipe and each child fact
   after effects. Publication checks require all original allocations and known
   closed IO. Preserve foreign replacement state; withdraw only the failing
   owner's exact published fact. Failure is sticky, with no fresh capture/retry.
5. The later native plugin factory joins the original historical handoff to the
   actual current listener/store/identity/bridge/native owner and current minimum/
   API support. Plugin namespace eviction cannot turn newly imported classes into
   the old owners; fixed original entry bindings must bridge this deliberately.
6. Only after all operator/runtime/entry/native checks may the gateway-only key
   owner load its selected private seed. Close its original descriptors before
   any worker launch. Broker admission remains independent. No recipe success
   skips operation/clock/channel/phase, native authorization/DRAIN or ACK/release.

The full factory must not call ParentAuthorityAdapter's unbound default as if it
were live native authority. Bind the actual PresentationNativeService to the
original native owner/context; its drain proves only its own native read worker,
never broker child closure or terminal acceptance. Keep startup/runtime and
per-request device/profile authorization distinct. A selection/manifest/child
snapshot is DATA until these original joins exist, not an authority token.

## Implementation and acceptance order

- GR1: exact version2 selection and closed complete recipe/fixed-child loading,
  shared aggregate budgets and independent original root facts. Existing version1
  components keep their explicit package-only meaning; no key or route changes.
- GR2: derive package/entry/dependency child observations from the actual original
  recipe fact, including entry execution/import-origin joins, future HMP import
  policy and distinct explicit runtime/link/loader coverage. No generic adapter
  may bless caller-supplied expectations. Preserve minimum-version/API policy.
- GR3: current native listener/store/bridge/identity join across plugin reload,
  actual observation/drain service and original role-key FD custody. Review this
  complete conjunct before any native/key publication; broker PS2 remains separate.

Required causals include schema/kind confusion, using a schema1 package as a full
recipe, wrong role/generation, missing/extra/changed child and unexpected code,
aggregate exhaustion across children, same-bytes inode replacement, coherent
root/fact/alias replacement during callbacks, late startup/future import, changed
PM/import origin, namespace eviction, wrong thread/process/listener/profile,
retirement/revocation, partial or uncertain read/hash/close and key FD failure.
Neither fixture re-exec nor source hash testing qualifies actual installed PM
activation/lease, runtime/link/loader, host deployment, physical image delivery
or release. Those actual observations remain separate required evidence.

## Earlier version-selection checkpoint

The fixed schema1 load and schema2 load_recipe_selection paths now share the same
original private-file owner, preserve exact schema in immutable data, and reject
cross-version/unknown input with no fallback. The schema1 package verifier refuses
schema2 before package IO ownership. Both versions cover private-file/canonical/
late/history/refusal causals, alternate-version recapture and subclass callbacks.
Independent read-only review accepted this bounded source slice;477 combined
checks pass in12.63s with unchanged source/fixtures.

GR1 is not complete: full recipe/fixed-child reading and aggregate enforcement
remain to implement. GR2 and GR3 remain open. No schema2 selection, package result
or passing test grants runtime/native/key authority or device qualification.

## Current GR1 document-loading source checkpoint

GatewayRecipeOwner.load accepts the actual schema2 selection owner and a bounded
positive recipe_size candidate. That length is DATA, not approval: actual private
leaf metadata, exact read/EOF and the selection-pinned SHA must agree. The fixed
entry still has to acquire this candidate safely and compose the complete startup;
no request or parsed manifest may select a file path. Unknown or oversized lengths
refuse without document acquisition. There is no fallback/version recapture.

The fixed recipe plus four child files use the original private-file IO lifecycle.
The complete top recipe is canonical/closed and pins each fixed child's size/SHA.
Declared aggregate overflow refuses before child reads; all actual counts share
one original counter. Original root/parent/plan/buffer cells are rejoined across
callbacks. Each child must be canonical JSON with exact integer schema1, the
fixed HMP_GATEWAY_PACKAGE/ENTRY/DEPENDENCIES/INTERPRETER kind and original selected
generation. Child-specific fields/tables and executable closure are GR2, not yet
validated. The positive document fixtures deliberately have no executable tables.

Review found mutable staging rows could replace previously read bytes. The loader
now holds every actual returned expected/raw pair independently and compares exact
object identities after its final guard, publishing only that original immutable
tuple. Both later-child and final-context substitution causals refuse. Foreign
plan/fact state is preserved; original failed/uncertain descriptors receive at
most their owned close attempt. A partial context-capture failure remains attached
to its retained failed owner. A duplicate after native/path drift refuses before
fresh parent callbacks and cannot poison the original activation snapshot.

39 recipe cases and prior startup/import checks passed:517 in14.22s, source/fixture
hashes unchanged. Independent source review accepted the bounded component. No
installed/native bootstrap, keys, providers, host/device traffic or deployment.
GR1 source document IO is implemented; fixed entry/operator composition and GR2/
GR3 runtime/child-table/native/key authority and physical qualification remain open.
The document counter is not a reset allowance for future artifact reads: GR2 must
retain its original known counts and enforce the existing whole-startup file/byte
limits in addition to the32MiB document-phase limit. No new scalar count may serve
as evidence that earlier IO occurred.

## GR2 plugin child integration checkpoint

The actual retained recipe owner can now feed its original plugin document into
GatewayPackageOwner.verify_recipe. The package verifier does not accept caller
replacement raw/digest values for schema2. Recipe facts now retain their actual
original count allocation alongside original immutable document pairs. Pure
historical and fresh early binding checks retain/rejoin parent/root/plan/fact/
closed descriptors and count before/after callbacks. Source binding and exact
count-cell substitutions refuse, even if a replacement has the same numeric value.

Recipe count publication holds the actual last read cell through extra hash/JSON
and the final guard; package publication holds its actual post-hash count through
subsequent scans/origin callbacks. The shared read tail is sealed as well. The
plugin's retained count is ready for a later typed handoff, not reconstructed from
an arbitrary scalar. Occupied startup owners refuse before fresh native callbacks.

This combined limit covers the five recipe documents and plugin files only. Full
startup must still join earlier original selection IO and later entry/dependency/
interpreter artifacts under the existing whole-startup limits. No new allowance
or expected-size sum may replace those original IO observations.

14 composed cases and42 recipe cases plus prior coverage:534 passed in16.45s with
source/fixtures unchanged; source review accepted the integration and count/vacancy
repairs. The composed plugin table is complete, but the other children remain
minimal envelopes. GR2 entry/dependency/interpreter/link/loader closure and GR3
actual native/key factory, broker/ACK/release and physical image delivery stay open.

The [original entry publication](GATEWAY_ENTRY.md#independent-original-entry-publication)
now retains module/function/code and original started facts (548 combined checks).
This is a prerequisite for GR2 entry-artifact consumption, not that qualification
itself. Independent entry/wrapper bytes/control-flow, runtime and GR3 remain open.

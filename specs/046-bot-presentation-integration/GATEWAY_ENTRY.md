# Original invocation through native bootstrap

Status: bounded source entry component, not installed launch or runtime admission.

`hmp_startup.gateway_entry.GatewayEntryOwner.start()` is outside `hmp_plugin`.
The closed plugin import/registration checker is unchanged. No registration path
imports this entry, no console-script target is declared and no listener starts.
The separate package is included in the wheel and needs its own independent
operator-approved executable inventory and origin policy. It is not covered by
GatewayPackageOwner's HMP package table or admitted by its own source hashes.

The one-shot partial entry owner is retained before bootstrap import. It captures
actual main-module/file/spec, argv/orig_argv list allocations and exact values,
process/effective-user/thread and an independent original allocation cell. Bootstrap
must not already be imported, nor may PM/gateway/listener capture have happened.
The fixed lazy native bootstrap import retains its normal PM behavior; the entry
never selects another environment, calls activation directly, rewrites argv or
constructs a replacement lease. The actual post-bootstrap activation owner is
captured before gateway.run. Original invocation scope/cell and held bootstrap/
activation objects are rejoined after context callbacks, not reconstructed from
current matching values. Refusal retains a failed owner and does not retry.

Inspected native ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df / v0.22.7 uses
hermes_cli.venv_sync.relaunch_command to reconstruct a script invocation from
argv[0] after PM interpreter replacement. Therefore the wrapper argv must survive
bootstrap; replacing it with gateway/run.py beforehand could bypass HMP entry
checks on re-exec. This source inspection is not an observed installed re-exec.
The native commit is diagnostic, not a supported-version equality gate.

Tests use actual temporary bootstrap and PM Python files in disposable isolated
interpreters; no installed Hermes/home, keys, provider, host or device traffic.
18 cases cover normal ordering, already/late bootstrap, argument identities and
values, main-module/file drift, bootstrap failure, wrong context, coherent original
cell replacement during bootstrap/after activation, and late aliases/imports.
Combined with retained selection/package/artifact/activation and import checks:
434 passed in9.03s, source unchanged. Review identified original-cell and final
alias gaps; those were repaired and reviewed before this checkpoint.

Still required: actual fixed launcher installation/control flow, independent
entry/runtime/dependency/loader admission and operator approval, configuration and
package ownership joins, native listener/store/bridge identity, gateway-only key
custody, independent broker startup, operation/clock binding and terminal ACK/
release/publication. This class cannot certify any of those. No actual native
bootstrap/re-exec, deployment or physical character display is qualified here.

Earlier packaging snapshot (before the original-publication changes): a temporary
build1.3.0/setuptools80.9.0/wheel0.45.1 environment produced
a wheel containing both startup files byte-for-byte, with no console entrypoints.
The first offline local build failed for missing setuptools, then the pinned-tool
build succeeded. No project dependency or installed Hermes environment changed.

## Pinned native command-builder exec evidence

The native relaunch_command definition was extracted without importing any native
module from ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df, hermes_cli/venv_sync.py
SHA2567688851ccadc994bc3b799a4a25577edaf465b7553b8887892c8b36e1811ffe0.
The source fixture and JSON provenance live in server/tests/unit/data.
This version pin attributes a compatibility experiment; it is not a production
version equality/allowlist gate. Tests call only the pinned command builder in
a disposable bootstrap and perform actual os.execv for script and module launches.
The wrapper is entered again with the same PID/application arguments and a new
interpreter invocation, before fresh original-owner activation capture. No native
bootstrap, PM selection/lease, installed home or gateway listener is executed.

Independent review verified both hashes, source extraction and causal assertions.
Two re-exec cases plus prior startup coverage:436 passed in9.24s with source and
fixture hashes unchanged. This closes command-builder fixture continuity only.
Installed entry origin/inventory, actual PM/native bootstrap/re-exec and full
operator/runtime/key/native factory qualification are still required.

## Independent original entry publication

The module now observes its actual import-time module/namespace/file/spec/loader,
original classmethod/FunctionType/code/global references. Types are checked before
attributes/comparisons; no caller supplies an origin map. This is provenance DATA,
not self-approval of source bytes, executable attestation or proof that a selected
wrapper's code executed. Independently selected artifact/wrapper qualification
and installed control-flow evidence remain required before runtime/key admission.

After actual bootstrap/activation and final original invocation/origin joins, the
entry publishes one independent _STARTED allocation containing original owner/
scope/cell, activation/bootstrap, origin record and immutable EntryStartupData.
The owner mirrors that exact cell; an occupied/foreign publication is not replaced.
A failure withdraws only its own exact publication. Re-exec establishes the new
interpreter's own acquisition; the old image's partial owner is not promoted.

_retained_binding is a pure original-allocation join. retained_data samples and
rejoins the original process/user/thread and returns immutable historical values,
without rereading module registries, files, paths or PM selection. Namespace/argv
changes do not rewrite those values. current_binding adds fresh invocation,
module/class/function/code/spec/loader and actual activation checks. Final pure
invocation/origin fences follow its last native callback; a late callback cannot
leave the entry or query accepting changed provenance. Wrong-process/thread
queries refuse without altering the original ready/failed records.

Queries are not authority tokens, retirement/restore mechanisms or installation
verification. A future typed entry-artifact verifier must accept the actual owner,
join its original activation to the actual recipe/native context and independently
check selected entry/wrapper artifacts. It cannot bless a copied binding tuple or
retain authority after its own startup/runtime liveness contract has failed.
No public route or plugin registration imports the separate entry package; the
closed plugin checker/native import boundary remains unchanged.

32 entry cases plus2 disposable actual script/module exec cases and prior startup
coverage:548 passed in16.57s with unchanged source/fixture hashes. New causals cover
origin file/record/code/loader changes, foreign publication/bootstrap aliases,
namespace and argument changes, wrong thread and actual forked process, final
origin drift before publication and argument drift during fresh activation query.
Independent read-only review accepted the bounded source component. Complete entry
artifact/table and executed-wrapper qualification, runtime/operator/native/key
factory, host/device and image-display/release qualification remain open.

The current original-publication source checkpoint has not been rebuilt into or
qualified as an installed wheel/device candidate. Earlier wheel evidence is
historical and does not certify the changed source bytes.

The [entry/wrapper file snapshot](ENTRY_FILE_SNAPSHOT.md) now binds actual original
recipe/plugin/entry owners to owned file/tree observations (569 combined checks).
It does not attest executed wrapper bytes or complete runtime/operator/native/key
admission; the earlier immutable observation facts remain DATA.

## Current HMP wheel verification — November 7, 2026

Built source `e3148f266cfc13abb3bf4665d2ab8d510bf3cc0a` into a wheel using build1.3.0,
setuptools80.9.0 and wheel0.45.1 in an isolated build environment.
Wheel SHA256: `8c998a4ca4838127b4ec88304bf2493146e8ca23a12a84a61f4ade4db5422e1e`.
All160 packaged code/resource files match the committed source exactly, including
hmp_startup/__init__.py, gateway_entry.py and entry_files.py. The complete ZIP
inventory has no duplicate/missing/unexpected package files, and RECORD hashes
and lengths were independently read back. No console entry point was introduced.

This supersedes the earlier historical wheel evidence only for packaging of this
source commit. It is not an installed gateway startup, runtime admission,
credential/key activation, image route, physical device or release qualification.
The package was neither imported nor installed. Bot-character delivery and
host-local image deployment remain outstanding; the broader goal stays active.

## Original interpreter continuity and Python-floor repair — November 7, 2026

The original entry now captures interpreter paths, version/flags, implementation
metadata and platform before native bootstrap. Current entry checks rejoin the
original implementation/version/flags objects and primitive snapshots; historical
handoff retains immutable redacted DATA. No environment selector, file read,
Hermes version allowlist, key load or runtime authority is introduced.

Actual Python 3.11 child testing exposed an existing activation defect: stdlib
typing.io/re are opaque aliases rather than ordinary modules. Only those original
stdlib namespace/registry identities now receive distinct alias records, with no
alias attribute access, equality, iteration or execution. Replaced/missing bindings
still refuse; unrelated nonmodule registry values remain rejected. This is an
HMP compatibility repair, not an upstream blocker or global type relaxation.

Independent source reviews accepted both bounded changes. 595 affected startup
checks passed in 27.04s with unchanged source; 49 actual Python 3.11.15 child entry/
synthetic reexec cases passed separately (not a full 3.11 plugin suite). Current
mobile source `56d517c` additionally passed 28 character/readiness widget/pure tests;
these are not physical devices or host image delivery.

Isolated metadata census found 412 listed files across installed reachable fixture
distributions, native extensions including a standalone cffi backend, and missing
qrcode. That incomplete metadata environment is not admitted closure. Distribution
metadata cannot approve roots, bound file IO or prove current/future import and
loader containment. Combined dependency/interpreter wire and plan integration,
link/loader policy, operator/native/key factory, broker acceptance and physical
character delivery remain open. Existing native lifecycle regressions remain unresolved.

## Executable-link candidate packaging verified — November 7, 2026

Built exact HMP source `bd39d95b2c057e759df4582095ca5d6d1e942de2` using the cached pinned build tools.
Wheel SHA256: `8e292af8c8e0b07c997424d77b750620af34a507e509994f5dca472f673b9c05`. All 162 package code/resource files
match the committed source; complete ZIP inventory and RECORD digests/sizes were
verified. The wheel was neither imported nor installed. Packaging does not qualify
actual interpreter execution, loader/native/key/broker composition or phone images.
Independent review accepted the final original-owner guard and closed lazy-import
delta. Linux exact-source CI is pending; local 706 startup / 74 actual Python 3.11
child fixtures and 89 surface checks are distinct evidence, not installed acceptance.

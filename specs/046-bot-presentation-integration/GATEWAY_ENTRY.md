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

Packaging: a temporary build1.3.0/setuptools80.9.0/wheel0.45.1 environment produced
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

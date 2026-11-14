# BR8b fixed-install synthetic broker bootstrap

Status: composed source harness implemented and independently reviewed; no
production service, runtime admission or capability is activated. This slice must compose verification
with the namespace-only bootstrap and retained registry, rather than presenting
a standalone hashfile utility as runtime attestation. Full metadata/custom-image
scope is preserved; the initial no-GO harness is a qualification step only.

## Expected installation versus observed files

An operator or reviewed release process supplies an expected manifest digest
from outside the selected installation. A generator may inventory candidate
bytes; it cannot authorize its own output. The bootstrap verifier and selected
interpreter require an explicitly trusted installation origin. Neither a broker
handshake nor a hash reported by the selected tree independently supplies that
trust. The trusted verifier origin includes its pre-verification standard-library
and native dependencies: later inventory comparison cannot retroactively attest
the code computing that comparison. Original phone credentials never enter this
mechanism.

One startup generation binds the exact bootstrap, broker/worker code, parser
closure, interpreter, runtime search roots and executable-code policy. Freeze
that selection and the fixed launch recipe for the broker lifetime. Under the
existing trusted root/same-UID administrator model, installation mutation must
not run concurrently with this generation. Before/after hashes cannot eliminate
execution races. An update selects a new installation and broker boot, invalidates
old operations, and never replays BEGIN/GO.

## Complete executable closure

- Plugin/parser: exact files and closed import roots, including transitive
  SafeLoader composer/constructor/resolver code even when graph construction is
  unused. Do not execute package initializers or activate site paths.
- Bytecode: `-B` prevents writes, not reads. Reject plugin/parser `__pycache__`,
  legacy `.pyc` and other unapproved executable forms, or admit their exact bytes
  explicitly. Do not call a source-only scan complete bytecode qualification.
- Standard library: account for source, frozen modules, cached bytecode, ZIP
  search locations and native extensions. Unexpected import roots or writable
  locations able to supply a missing module refuse.
- Native runtime: explicitly qualify interpreter, extensions and dependent
  system-library trust. Python-file hashes alone are insufficient. Platform
  runtime policies and evidence must remain explicit rather than invented from
  an interpreter version string.

Preserve `presentation_child_launch.py` fixed `-I -B -S` selection and immutable
recipe. Preserve `presentation_child.py` namespace-only loading. Verify the
selected generation before importing broker modules; no Hermes/gateway/provider
initialization is permitted. Construct and strongly retain the actual registry.
The independently OS-supervised entry is the sole exact-child reaper, installs
no auto-reaper and exposes no process handles to another reaper.

## First actual harness and acceptance

Use only new synthetic empty-input/no-GO readers. No native roots, real profile
content, network message or permission change. Retain partial owners and UNKNOWN
on crash; local endpoint/EOF/reap observations do not authorize terminal release.

- [x] Implement verifier and standalone namespace-only synthetic bootstrap together.
- [x] Demonstrate substituted source/cache/import-root refusal in isolated fixtures.
- [x] Demonstrate observed generation drift refusal before launch and before final
  diagnostics; original deadline expiry prevents start without renewal.
- [ ] Integrate new-boot invalidation/reconnect semantics with the future service.
- [ ] Demonstrate no plugin/parser package initializer or site activation and
  exclusive exact-child reap. Admitted standard-library initialization is part
  of the qualified runtime closure.
- [ ] Audit full worker/runtime closure for spawn, regroup and FD transfer;
  Python instrumentation alone is not an OS sandbox.
- [ ] Demonstrate retained partial startup/cleanup and no release on broker crash.
- [x] Independently review the composed source and actual bounded harness: root
  and independent Python 3.13 runs pass the 34-case composed suite; two added
  same-source/symlink trust-alias tests also pass independently.

Production service-manager containment, current endpoint-to-kernel-peer/boot
binding, bounded transport, native original-authorization pre-GO/pre-emit,
started terminal release, authenticated routes and physical parity remain
separate gates. This contract supplies no service or connection authority.

## Source harness observations and limits

`presentation_broker_bootstrap.py` accepts only canonical bounded synthetic-no-GO
manifests with an independently supplied expected digest. It inventories exact
runtime files (including admitted bytecode/archives/extensions/bundled libraries),
source-only plugin/parser files, ordered running import roots and absent ZIP
locations, implementation/version/cache tag, actual selected executable and
prefix. Runtime symlinks must resolve inside the selected runtime; source trees
refuse symlinks/caches/extra executable forms. Counts are charged while enumerating
before sorting, and file/aggregate reads are bounded. The expected native policy
names only fixed OS-managed locations and distinguishes inventoried installation
libraries; it is an explicit trusted-OS/loader premise, not measurement or runtime
enforcement of every loaded-library origin, nor an OS sandbox. Root ownership
alone is not evidence for administrator-installed `/usr/local` libraries.
Production platform loaded-image/origin qualification remains open.

The candidate inventory tool executes its fixed trusted verifier implementation;
it treats inspected candidate trees as data. Its observed digest never blesses
itself. Test-created expected manifests are fixture oracles only and cannot
establish production trust. Real release/install origin review remains required.

The harness imports the broker through a private namespace without plugin package
initialization, strongly retains the actual registry before constructor effects,
starts one fixed reader without input or GO, and cancels through the existing
managed owner. Local drain observation leaves the reservation PENDING. Partial or
uncertain outcomes do not return normally or drop retained registry ownership;
the external synthetic supervisor must inspect/retire the harness. Diagnostic
write failure cannot unwind that retained owner. This does not qualify actual
service-manager crash/orphan containment or started terminal release.

Full re-verification occurs before the original operation deadline is issued.
Bounded metadata/identity fences run before start with checks on both sides of
that same deadline, and before final diagnostic reporting. These detect observed
drift but do not eliminate mutation races. No concurrent installation mutation
remains an explicit premise. Failed/late checks never extend work or cleanup.

The launch environment is fixed C locale without provider/home/loader variables.
Darwin may inject `__CF_USER_TEXT_ENCODING`; only a bounded canonical numeric
three-field form with matching effective UID is accepted, only on Darwin. This
is a platform encoding exception, not an import-path or permission exception.

Causal fixtures include private relocated-runtime ZIP/source mutation, legacy
source cache/archive/symlink refusal, expected-versus-running configuration and
manifest mismatch, generation change and deadline crossing before any Popen,
postcleanup drift suppressing diagnostics, candidate bootstrap non-execution,
bounded directory enumeration and malformed/wrong-UID platform encoding. No
real native root/profile, message, tool action, grant or service is used.

# BR8b fixed-install synthetic broker bootstrap

Status: independently reviewed next implementation contract; not implemented,
qualified or activated by this document. This slice must compose verification
with the namespace-only bootstrap and retained registry, rather than presenting
a standalone hashfile utility as runtime attestation. Full metadata/custom-image
scope is preserved; the initial no-GO harness is a qualification step only.

## Expected installation versus observed files

An operator or reviewed release process supplies an expected manifest digest
from outside the selected installation. A generator may inventory candidate
bytes; it cannot authorize its own output. The bootstrap verifier and selected
interpreter require an explicitly trusted installation origin. Neither a broker
handshake nor a hash reported by the selected tree independently supplies that
trust. Original phone credentials never enter this mechanism.

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

- [ ] Implement verifier and standalone namespace-only bootstrap together.
- [ ] Demonstrate substituted source/cache/import-root refusal.
- [ ] Demonstrate generation-change refusal and no replay after a new boot.
- [ ] Demonstrate no plugin/parser package initializer or site activation and
  exclusive exact-child reap. Admitted standard-library initialization is part
  of the qualified runtime closure.
- [ ] Audit full worker/runtime closure for spawn, regroup and FD transfer;
  Python instrumentation alone is not an OS sandbox.
- [ ] Demonstrate retained partial startup/cleanup and no release on broker crash.
- [ ] Independently review the composed source and actual bounded harness.

Production service-manager containment, current endpoint-to-kernel-peer/boot
binding, bounded transport, native original-authorization pre-GO/pre-emit,
started terminal release, authenticated routes and physical parity remain
separate gates. This contract supplies no service or connection authority.

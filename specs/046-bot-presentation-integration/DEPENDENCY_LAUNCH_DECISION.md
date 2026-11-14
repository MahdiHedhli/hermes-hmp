# BI1 explicit parser-package child launch

Status: independently accepted source-only runtime repair. This does not qualify a live listener,
exclusive process custody, installed code integrity or the native Kanban reaper.

## Specify / clarify

A listener's parent-only PM site-packages activation must not be assumed to reach
an isolated worker. Preserve the fixed no-provider/no-plugin-initializer worker,
no inherited environment/PYTHONPATH, and no request-selected executable/module.
Do not activate an entire dependency environment (including .pth/sitecustomize)
just to import the worker's one parser dependency.

Proposed trusted startup input: the exact absolute PyYAML package directory from
the listener's already selected runtime. It is not obtained from phone input,
IPC profile content, os.environ, sys.path copying or a mutable PM selector on each
job. Keep the default recipe dependency-free/refusal-only until startup binds it.
The new explicit recipe is captured once by its process owner before any launch;
it cannot be replaced/retried after claim/start. All launches add -S to -I -B.

The child receives only that fixed package directory as a bounded process argument,
not a code string or user-selected module name. It binds the exact package name
`yaml` as a namespace with ModuleSpec and a closed submodule search path. It does
not execute the package initializer, load the optional C extension, insert site
paths or activate `.pth`/sitecustomize. The adapter statically imports only
`yaml.error/events/tokens` and `SafeLoader` from `yaml.loader`, inside functions.
The scanner permits only those exact adapter-local lazy imports; dynamic package
code execution remains rejected by S2. Its earlier rejection of the generic
importlib loader is preserved as a repaired pre-convergence finding.

The adapter preserves PyYAML's own SafeLoader token/event check/get/dispose loops.
SafeLoader initialization and its transitive pure-Python reader/scanner/parser/
composer/constructor/resolver code are part of the trusted dependency closure.
No claim excludes constructor code or initialization; the application never calls
graph retrieval or construction methods. Both token and event generators dispose
in finally, including reducer refusal and explicit outer generator close. Complete
interpreter/stdlib/parser/submodule/bytecode provenance remains a startup gate;
these fixed import names are not an integrity attestation.

The provided path is an absolute, bounded, canonical directory named yaml, with
__init__.py a regular file. Reject relative paths, symlink package/entry, traversal,
NUL/control characters and extra arguments. The runtime/source attestation and
filesystem-mutation premise remain a separate mandatory startup gate, including
interpreter/stdlib, own module closure, parser submodules/extensions and generation
identity. Path checks and a caller-provided path are not that attestation. No live
route/capability may infer readiness from this recipe.

## Plan / checklist / tasks

- [x] Independently review this closed dependency launch contract and narrower static-parser amendment.
- [x] Implement explicit immutable process-owner recipe and -S bootstrap; default
  recipe still starts only the fixed child, with no dependency exposure.
- [x] Causal actual-process tests: explicit selected parser works under a bare
  interpreter lacking yaml; no .pth/sitecustomize/unrelated package activation;
  relative/symlink/malformed/extra-arg refusal; fixed environment and no sys.path
  inheritance; retain exact child wait/group/pipes behavior and no retry.
- [x] Regression test supervisor/worker/YAML and closed-import scanners; review.
- [ ] Bind actual listener-selected generation/code attestation before activation.
- [ ] Resolve reaper/broker custody and physical presentation separately.

This is a source repair for one runtime blocker, not a replacement for desktop
name/classic/blobatar/custom-image parity or the larger BI1 activation goal.

## Convergence / remaining gate

The initial generic importlib implementation was rejected by S2; it was replaced,
not exempted. A separate review found mutable Supervisor startup selection after
native awaits. Its immutable snapshot/current-binding check now refuses changed
configuration before process creation; the pending-INITIAL causal test proves no
launch or emission. The process owner captures a deep-immutable recipe before
claim/start and refuses replacement or repeated/failed launch replay.

Independent final parser/adapter/scanner review: 123 tests and mandatory closed
surface scanner pass. Root Python3.14.9 presentation/skeleton/surface run: 790 tests
and190 subtests pass; the subsequent20-case parser launch run includes three added
missing-isolation-flag cases. Counts overlap and are not summed. Final Python3.11 run passes793 tests+190 subtests. The floor run includes all
three additional flag cases. These are source/fixture qualifications, not live
runtime attestations.

The already reviewed Supervisor was missing from the exact source-module test
inventory; its explicit addition repairs that stale inventory. No new gateway
route, manifest dependency, global import exemption or production capability was
introduced. Installed listener-selected generation/interpreter/stdlib/dependency/
bytecode attestation, reaper ownership and physical parity remain required.

# Bounded broker/worker source audit — November 4, 2026

Inspected own-code source: `9ef3bf434d673c1cb02f72722b9e7fe2c15ef180`.
The independent reviewer inspected source only: no imports, fixtures or live-host
actions. This supports bounded synthetic containment experiments, not an OS
sandbox, complete runtime proof or production started-operation release.

## Actual call paths

- `presentation_broker_bootstrap.py` creates a private namespace without executing
  plugin initialization, retains the registry before construction, then runs only
  start, abort and cleanup polling. This harness never stages input or relays GO.
- `presentation_broker_child.py` starts the fixed reader through `Popen` with three
  pipes, `close_fds=True`, no passed descriptors, inherited group and no shell.
  Its native observations use exact-child `waitpid`, and it attempts at most one
  SIGKILL for its retained unreaped child. There is no worker-group signal API.
- `presentation_child.py` binds own-code and parser namespaces without package
  initialization, then selects the fixed filesystem backend and worker.
- `presentation_worker_control.py` requires bounded input3, the original deadline,
  exact challenge GO and input EOF before processing. `presentation_worker.py`
  revalidates primitive scope and emits bounded output2 chunks.
- `presentation_files.py` limits the read transaction to fixed profile/avatar
  leaves with held-directory checks and descriptor cleanup. The filesystem
  backend exposes only open/stat/fstat/read/lseek/close operations.
- `presentation_raster.py` performs in-process structural checks, hashing and CRC;
  it invokes no external image decoder program.

No new own-code worker call path was found that spawns/executes another program,
changes group/session, or sends socket/SCM_RIGHTS descriptors. This is a statement
about the inspected fixed call path, not absence of those capabilities from the
interpreter or its imported libraries.

## Exact parser source distinction

The fixture source is PyYAML 6.0.3. The coordinator's read-only comparison
matched all 16 non-initializer Python files to the selected vendor package by
SHA-256; the independent reviewer inspected that source without repeating those
hashes. Fixture `__init__.py` was a deliberate tripwire. Its source namespace does not activate that initializer or `_yaml`.

`yaml/loader.py` imports reader/scanner/parser/composer/constructor/resolver, and
SafeLoader initialization initializes all six. All belong to the trusted closure.
The fixed adapter invokes token/event check/get loops and disposes in finally;
exact byte input uses the reader's in-memory branch. It does not invoke graph
construction, `get_data`, `get_node` or unsafe object constructors.

`yaml/constructor.py` contains unsafe dynamic-import definitions. They are imported
as definitions; the fixed token/event path does not call them. Do not describe
those definitions as absent from the admitted source or general SafeLoader/module
imports as a complete confinement guarantee.

## Remaining qualification conditions

Exclusive child custody must include `subprocess.Popen` behavior, not only our
explicit waitpid call. Popen has constructor-error, destructor and `_active`
cleanup paths. The current synthetic process is fresh, has no prior abandoned
foreign Popen objects, strongly retains its registry/known children and admits
one operation only. It performs no later spawn after ambiguous construction;
this is not a newly demonstrated blocker for that harness. Unknown construction
never supplies closure.

Before a multi-operation service is admitted, qualify partial-Popen retention and
future-start behavior: failed construction must not silently introduce an alternate
reaper whose observations are mistaken for this owner's exact wait. Retaining a
partial Popen before constructor effects or quarantining subsequent starts needs
an exact-source contract and causal tests. No monkeypatch of native reapers,
SIGCHLD policy or ECHILD-to-success conversion is permitted.

Interpreter/import machinery, codecs, hashing, CRC/native extensions and the OS
loader remain inside the explicit trusted-runtime/OS premises. Text/AST tracing
cannot establish confinement against vulnerabilities there. Actual loaded-image
qualification, service crash/orphan/descendant containment, authenticated peer/boot
binding, original native authorization and started-operation release remain open.

## Post-audit source repair — November 5, 2026

Source `e056102` now retains native Popen allocations before initialization and
checks the same exact empty stdlib cleanup list around allocation. Independent
120-case focused convergence and floor/current regressions passed; hosted
CI41971597711 passes on that exact source. This improves the partial-constructor
condition identified above, without converting constructor-internal cleanup to
closure or excluding arbitrary concurrent foreign reapers. Fresh standalone and
strong-retention premises remain mandatory. Next is the separately reviewed
[bounded service-containment fixture](BROKER_SERVICE_CONTAINMENT_FIXTURE.md);
its implementation and actual observations remain open.

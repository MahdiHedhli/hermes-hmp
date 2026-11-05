# Reader runtime findings — November 4, 2026

## Source repair after the observations below

The isolated worker now accepts a fixed, validated startup parser-package path
under `-I -B -S`, without executing its package initializer or activating site
paths. The namespace/adapter only uses closed pure-Python SafeLoader token/event
imports, including its transitive composer/constructor/resolver initialization
code but no graph-construction calls. The supervisor/process owner freeze that
selection before launch and reject rebinding across native awaits. No automatic
PM selector lookup or parent sys.path copy is introduced. See the reviewed
[dependency launch decision](DEPENDENCY_LAUNCH_DECISION.md).

This fixes the source mechanism for exposing the dependency. Binding and attesting
the actual listener's selected generation, interpreter/stdlib/own code/parser
closure and bytecode remains open. The original observed failure below describes
the preceding launch recipe, not an active version allowlist. The independent
Kanban reaper/custody gap is unchanged; no live route or capability is activated.

## Original runtime observations

The composed reader is source-reviewed, but two actual integration assumptions
need repair before activation. These are capability/ownership issues, not an
exact Hermes version allowlist or a Linux restriction. Source hashes are in
[runtime-source-pins-20261104.json](runtime-source-pins-20261104.json).

## PM dependency activation does not propagate to the isolated child

The inspected native checkout is ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df.
Its current launcher boots tools Python 3.14.9; this is **not** proof of the
interpreter used by an already-running gateway. A read-only bare interpreter
probe with -I -B finds no yaml module. This does **not** mean PyYAML is absent
from the PM-selected environment: hermes_bootstrap.py calls activate_dependencies,
and pm/environments.py adds that environment's site-packages to the parent
sys.path without changing sys.prefix. Our current child recipe uses sys.executable
with -I, so it does not inherit that parent-only activation.

Native PM already offers venv_command(root, selected_venv(root), options=("-I",
"-B")), including sealed-payload handling. The repair must freeze and validate
the selected generation actually used by the listener and qualify interpreter,
dependency/.pth/code origins. It must not copy the parent's entire sys.path,
inherit PYTHONPATH or silently switch an already-running listener to a newer
selection. No dependency, runtime, launcher or host setting was changed here.

## Native Kanban may consume a direct child's exit status

When the embedded Kanban dispatcher runs, gateway/kanban_watchers.py invokes
reap_worker_zombies through asyncio.to_thread. This is a thread in the same
process, not a separate reaper service. The POSIX implementation in
hermes_cli/kanban_db_dispatch.py uses waitpid(-1, WNOHANG), which may consume any
direct child's status before PresentationProcessOwner observes it. Current
source has no ownership exclusion/registered status-delivery hook on this path.
Actual configured/running dispatcher state was not inspected; the conflict is
conditional on that path running, not a claim that every host is affected.

A new actual-kernel test reproduces the consequence using only its exact own
synthetic child PID as the competing wait. ECHILD remains UNKNOWN, retires signal
authority and does not invent terminal/group closure. The test never calls a
process-wide reaper or touches another process's children.

Setsid, an HMP-only lock, asyncio subprocesses, PID handles or changed SIGCHLD
policy cannot exclude another thread's waitpid(-1). Do not disable Kanban or
replace the native reaper to activate characters. The smallest direct-child
prerequisite is native registered child ownership with exact status delivery or
exclusion and race-safe registration. An external independently supervised
reader broker is a possible no-upstream-change design, but needs its own reviewed
IPC/authentication/custody/lifecycle architecture; it is not implemented or
qualified by the current in-gateway supervisor.

Native profiles.list now exposes ui_meta, but its actor authorization, full-profile
reads and data scope are not the HMP phone contract. It is not an automatic safe
fallback for this worker or permission to read sibling bot configuration.

## Next implementation priorities

Keep direct-reader activation closed until the two assumptions are resolved.
Preserve local selectable icons and letter fallback. Continue host-local image
qualification independently; its existing authenticated media route has a
separate authority model and does not require this presentation reader. Do not
mark desktop parity complete or permanently upstream-impossible: choose and
review the direct-owner integration or external-broker path, and preserve the
full presentation scope, runtime/route/physical tasks and active broader goal.

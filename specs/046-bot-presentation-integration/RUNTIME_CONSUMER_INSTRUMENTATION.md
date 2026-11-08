# Causal fixture instrumentation scope

This descendant leaves production source identical to 9dc2875. The original
68-case run remains frozen and active, with reported failures pending terminal
diagnostics; no cause or pass is inferred from this fixture change.

The consumer fixture previously installed a global C profiler even for cases
that used no profile observation, and its interruption tracer enabled line
events for every Python frame. The tracer now returns None for non-target code.
Reentry observation is armed at the exact original consumer buffer-extend line,
observes its actual C return, then disables profiling before the nested refusal.
EOF-failure metadata observation starts at the actual failure marker and remains
active through cleanup. Other cases need no profiler.

All target code/line, actual event, reentry, ownership, buffer/history, EOF and
metadata assertions remain, as does the 60-second child deadline. This is an
instrumentation correction, not a production fix or a runtime performance pass.
No new execution result is claimed; original failure evidence remains intact.

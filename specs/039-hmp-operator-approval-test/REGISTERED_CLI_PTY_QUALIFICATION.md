# AT1-REGISTERED-CLI-PTY-01 — November 11, 2026 UTC

The genuine HMP command descriptor registered by the native PluginManager now
passes an isolated macOS parser/handler/real-terminal integration. This advances
the earlier observer-function-only result without changing product/runtime code.

The descriptor's actual setup_fn builds the hmp argument tree; ordinary argparse
passes its result to the actual handler_fn for begin/cancel/status dispatch. Fixture wiring attaches
that descriptor to ordinary argparse; it does not copy HMP argument definitions
or replace its handlers. Native main is deliberately NOT imported or called:
module-level interrupted-update recovery and main's update/discovery/startup
hooks are outside this test. This is not stock shell/launcher qualification.

## What actually ran

The native server lifecycle owns a non-daemon background thread, while parsed
commands run on the Python main thread with real PTY stdin/stdout descriptors.
The fixture context substitutes only the existing synthetic host-ID port and
supplies a controlled environment snapshot; it does not fake isatty, permissions,
native helpers, the Store, listener record, socket peer UID or HTTP authentication.
Both streams report true from their actual native isatty method. The counterpart
noninteractive refusal uses actual pipes, not a fake TTY stream.

- Parsed begin acknowledges, denies and expires through actual native helpers;
  parsed status reads the final state after each joined outcome.
- Parsed cancel controls a pending operation begun by the already-qualified
  observer. That auxiliary observer runs on the server thread with its supported
  install_signals=False setting. Parsed handlers remain on main with normal
  signal-scope installation; no received-signal behavior is qualified.
- Missing --session returns2; noninteractive pipes and an injected agent-session
  marker return1. Each refuses with zero Unix connects and no producer admission.
- Each positive outcome observes actual joined CLI output/code, an empty native
  queue, released producer slot, withdrawn HTTP card and unchanged empty chat.
- The real server thread joins; CLI resource debt is zero; listener, database,
  task/worker capacity and loader registrations settle. Native status generation
  persists and its daemon is idle; that idle daemon is not claimed as joined.

`REGISTERED_CLI_PTY_SAMPLE_20261111.json` records exact source/interpreter/scripts,
report/log/result hashes, per-case coverage and limitations. All12,577 native/HMP
exported source files match before and after. Independent read-only review
rehashed the sources and final evidence with no mismatch. The unchanged default
observer mode also passes on the same final script. Matching five admission
refusals pass on Python3.14.9 and3.11.15; these do not qualify native ed1 under3.11.

## Fixture failures preserved

Two earlier runs failed the stdout witness despite native acknowledgement and
clean teardown. A fresh own-PTY probe confirmed Darwin can discard unread output
at last-slave close. An attempted tcdrain fix then blocked; a read-only sample
identified that call in the actual owned child. One SIGINT to that verified child
interrupted it gracefully, and its real thread/listener/store/registry cleanup
was observed. That run is failed and perturbed, NOT successful cancellation or
signal-handling evidence. No force termination or old begin retry occurred.

The final collector flushes and observes bounded native readiness/read output
while its slave stays open (absolute2s, max4096bytes,50ms quiet after data).
It never substitutes expected text for actual output and retains the original
joined-output/code assertion. Unknown fdopen/close ownership is retained rather
than retrying a possibly reused descriptor. Every new trial used a new private
instance after the old process was terminal; no ambiguous operation was resent.

## Reproduce and remaining gates

Use the same reviewed export/environment invocation documented in
NATIVE_IPC_QUALIFICATION.md, adding --registered-cli-pty. The controller requires
the requested mode and its per-case witnesses, not only a complete phase string.
No dependency install, host update, grant/mode/provider/model/job change or
physical device action follows from the test.

- [x] **AT1-REGISTERED-CLI-PTY-01** Actual registered parser/handler + real PTY,
  native producer, kernel-authenticated IPC and authenticated HTTP controls.
- [ ] **AT1-CLI-ENTRY** Stock native launcher/discovery/startup and shell path.
- [ ] Actual received signals, native adversarial/fault expansion and Linux.
- [ ] Android/iOS physical card/display/answer, native storage and release.
- [ ] Independent avatar startup53/full04660s gate; this result does not close it.

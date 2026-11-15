# Canonical Bot Chat title rotation: bounded native evidence

Root ran a private disposable-home fixture against clean Hermes
`8afaab3703e336d72a72c812dd2dd249f04f166a`, with its isolated copied CPython 3.14.7
runtime. This is session-metadata research for C6b; no serving, grant, manifest entry,
gateway, Agent turn or device qualification is implied.

## Observed flow

The fixture used native public SessionDB methods, including `publish_compression_child`.
It replayed the title-transfer public calls in the order read from the actual Agent source.
It did not call the Agent's compression functions or exercise their lease/model path.

| Phase | Title holder | Root hidden | Child hidden |
| --- | --- | --- | --- |
| Initial canonical session | Root | Exact integer 1 | No child |
| First child published, before title transfer | Root | 1 | Exact integer 0 |
| First title transfer | Child | 1, untitled | 0, titled |
| Second child published, before title transfer | Middle ancestor | 1, untitled | 0, untitled |
| Second title transfer | Latest child | 1, untitled | 0, titled |

The native root-first compression lineage equaled the independently walked parent chain.
Old bound references resolved to the current tip. Requiring the titled row itself to be hidden
would refuse the real compressed Bot Chat after either title transfer.

## Results and scope

All **15 cases and 51 proposed eligibility checks** met their expectations: 23 accepted,
28 refused. Controls refused ordinary visible canonical titles, unrelated sessions, explicit
forks, resume-walker children outside the compression lineage, stale tips, native unhide/pin,
deleted or retired titles and archived lineages.

One accepted case deliberately demonstrates a retained limitation: a trusted host can retitle
the visible tip of an ordinary hidden compressed lineage to the canonical title, producing
the same metadata as a real moved Bot Chat title. The proof trusts native-written metadata,
including model-generated or operator-set titles and automatic titling if it can create this
state while the canonical title is free. This case demonstrates deliberate retitling only;
it does not exclude other native title writers. It grants no file-read authority by itself.

Both before/after strict isolation checks passed: zero live-home module, path or runtime-prefix
matches; zero attempted Python network operations; no product package initializer executed.
Child stdout/stderr were empty, no deadline fired, all 248 imported native source files and
accepted HMP pins were unchanged, and the owned scratch directory was removed. Root separately
compared the copied runtime/venv's 7,963 non-cache file/symlink entries with its approved snapshot.

The first run was retained as INCOMPLETE because its preflight incorrectly expected
`agent.conversation_compression` not to be imported. Native SessionDB startup imports that module
through `hermes_state_common`, `agent.context_compressor` and `agent.turn_context`. The repaired
fixture checked its exact checkout origin, unchanged module object and source hash instead;
it still required no `run_agent` or gateway import. Import executes module-level code.

Private final receipt SHA-256:
`0843d0c1828ed0bcac1bfcd9b94ba0d2da75d6659dbfe82cc3d4de3f4ead307d`.
Runner SHA-256: `8cab886dc51d4ab031445a36e173de8cab12dd4e230a7979a96a65a542022d4d`.

Limits: sequential fixtures, at most three chain rows, no concurrent/ABA snapshot proof,
deep-chain or prompt-allocation cost, Phone-session proof, production bridge binding,
media file access or physical acceptance. Compression leases were explicitly disabled in
the disposable publication fixture. C6b and serving admission remain open.

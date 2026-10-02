# Approval minimum-policy native samples — October 2, 2026

Root accepted the corrected, isolated native sample runs for runtime candidate
`150bd0f1535b41495e5fc31ded128b9452221052`, with fixture-tool correction
`2c153e209c8a7d64bf12fa9369a88d8180dc52c4`. The bound candidate contained 239 source files.
No installed gateway or phone was used as a fixture.

| Sample | Interpreter and dependencies | Selected cases | Result |
| --- | --- | --- | --- |
| `8afaab3703e336d72a72c812dd2dd249f04f166a` | Python 3.14.7; sample lock, messaging extra | 13 | All passed; zero skips or failures |
| `f97608f178d1ffeca59860195ab7da295f7c8e5f` (`v2026.9.24`) | Python 3.11.15 within its declared range; sample lock, messaging extra | 13 | All passed; zero skips or failures |

The first sample has the session-stream approval notifier. The release-floor sample lacks it:
its notifier-dependent cases exercise negative availability behavior, rather than proving that
Bot Chat cards operate on that sample. Phone-chat helper availability remains separate. These
are sampled implementation results, not a runtime commit allowlist or blanket qualification.

Each sample passed sandbox preflight, parent/import isolation, an actual offline fixture `uv`
call that changed no dependencies, and native smoke. The preflight included 19 explicit sandbox
canaries. The harness used its declared dependency lock. Both approval processes exited normally
with no remaining child processes, and candidate and protected-tree digests remained unchanged.
Root's final preparation verification reported intact inputs.

The selected cases cover unavailable-fixture behavior, manifest mutation, ordinary non-owner
sends, Bot Chat allow/deny and timeout behavior, Desktop-held prompts, replay without a second
stream, Phone approvals and clarification, cross-profile refusal, text/slash non-resolution,
and restart during a pending wait. Case names do not imply that missing native capabilities
were present; each case's declared negative branch is retained.

Earlier failures remain in private evidence: the obsolete fingerprint bootstrap failed before
case bodies, and the first corrected preflight failed when invoked from the wrong working
directory. Neither is counted as a successful native case. The preparation review's limitation
on independently reconstructing transient build-tool archive execution is also retained; lock
and installed-file evidence do not erase that provenance limitation.

## Remaining gates

- No candidate `ca705dbf` run is claimed by this two-sample result.
- Owner-local package and drain-aware deployment remain pending.
- The installed `4d6863e` baseline remains unchanged and has no approval lane.
- Physical phone card/answer behavior, priority push and provider delivery are unverified.
- These results do not supply the separate Bot Chat caller-message identity needed to correlate
  an ambiguous send with its canonical history row.

Spec 034 T14 has evidence for its two declared prepared samples. Packaging (T15) and the
optional additional sample are separate work; this document grants no phone or owner privilege.

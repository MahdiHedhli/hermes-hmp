# Bounded approval-key validation result — November16, 2026

Executable source:17694b2be31157aa349908ef0d2408818cfc0639; basef6b845eee893fa493e78fa315d89d9b59ab41acd. Only gateway_approval.py changes among199 production files;198 are byte-identical. No live action, permission/config write, source cache or removed seal.

- All86 selected cases pass26.629s: complete API metadata and import-order files plus all44 original fixed-operator cases. No failures/errors/skips.
- The complete20-case metadata file also passes on the original parent production with all six new controls. The initial private runner description incorrectly said23; authoritative JUnit and the explicit private correction show20.
- Three collision-bearing str-subclass keys are refused before hash/equality hooks, covering registry/module/spec. Three actual isolated operator mutations between retained-binding and closed-custody seals are also refused; restoration preserves original bindings.
- Exclusive scratch scan omission produces exactly three intended foreign-key-comparison failures. Exclusive scratch second-seal omission produces exactly three intended late-key-accepted failures, with the original trace fragment retained as a comment at the omitted-call position. No errors/skips; source checkout unchanged. These broken controls were never deployed or published as production.
- Independent source/final review accepts the bounded change and terminal evidence. Plugin-surface and changed-source private-value checks pass. Three parent Ruff findings (late-cycle E402, existing import I001, test exec S102) remain unchanged and unwaived; this is not a clean whole-project lint claim.
- An isolated Python3.14.4 metadata microbenchmark uses five interleaved parent/current rounds of10,000 calls. Median times54,533,583ns versus37,594,875ns (ratio0.689). No native root API executes. This measures only the helper, not startup, throughput, end-to-end behavior or another platform.

## Still failing / unqualified

The original normal cache-input scenario was rechecked on an exclusive17694b2b scratch composition with the reviewed962b38ca native readlink test observer and the original-code trace helper. It still times out at the unchanged60-second child deadline (one failure, no errors/skips; total60.158s). This optimization does NOT resolve that timeout. Other cache variants were not selected. The observer changes only that private scratch test file; it is not part of this production branch.

Prior native Linux passes bind their original sources, not this new production change. Full operator/cache, native Linux/private composition, Darwin scanner, signed physical startup/image behavior, full attachments, groups and release qualification remain open. The original broad regression run remains separately owned; no replacement or kill was performed.

Published as [draft PR184](https://github.com/MahdiHedhli/hermes-hmp/pull/184); no merge/deployment.

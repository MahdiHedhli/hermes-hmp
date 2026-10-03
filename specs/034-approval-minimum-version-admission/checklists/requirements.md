# Requirements quality checklist (reviewer-owned)

- [ ] Every requirement names its failure behavior (R1-R16).
- [ ] No requirement uses a commit, fingerprint or manifest as a runtime gate (R5).
- [ ] Floors are taken from source evidence, not from a sampled development build (R2, D4).
- [ ] The Bot Chat notifier is described as attempted with a neutral diagnostic, never as a floor (R4).
- [ ] Authority checks are listed in route order and match HMP v1 §7b (R6).
- [ ] Fences cover instance, user, profile, request ID, run or session key, generation and binding (R7-R10).
- [ ] Transport selection is decided before the send and never falls back (R11).
- [ ] Failure reporting is user-reviewed and offline (R16).
- [ ] Out-of-scope items, including SD3/SD5, are explicit.

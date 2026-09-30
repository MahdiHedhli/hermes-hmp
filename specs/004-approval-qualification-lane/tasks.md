# Tasks: approval qualification lane

- [x] Write spec, plan and tasks.
- [x] Add empty `approval_supported_builds.json` with the bounded `bridge_files` list.
- [x] Add `APPROVAL_DEPENDENCIES`, `probe_approval_dependencies` and `approval_build_qualified`.
- [x] Leave `DIRECT_SEND_DEPENDENCIES` and `direct_send_build_qualified` unchanged.
- [x] Add the read-only `Approval qualification:` line to `hermes hmp compat`.
- [x] Package the new list in the wheel.
- [x] Unit tests: empty list, malformed list, missing list, missing source file, SHA mismatch, probe
      failure, independence from guarded-send qualification, CLI output.
- [x] Update `FEATURES.md` and `ROADMAP.md` as draft groundwork.
- [x] Run the focused tests and lint. Full local suite: 1197 passed, 10 skipped;
      Ruff lint, plugin surface, privacy, and diff checks passed. Formatter differences in
      preexisting lines remain outside this slice.
- [ ] Later, separate slices: behavioral approval qualification evidence, then any build entry.

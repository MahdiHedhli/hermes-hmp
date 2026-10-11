# Root architecture decisions

Read the owner policy in this directory. The independent architecture review is source-only advice.

Accepted: R1b per-feature floors; R2 no native requires_hermes; R3 separate session
browsing; R4 Python major.minor in report metadata; R6 runtime availability names.
Phone copy R5 is assigned separately and does not change the wire.

Required corrections to the architecture advice:

- A failed dependency probe does not prove a version incompatibility. Do not say
  “HMP has not been validated on Hermes …” unconditionally: the same sampled build
  may previously have passed. Say the feature compatibility check failed and show
  a fixed reason. Describe a version as unvalidated only when sampled evidence says
  so and only after failure. Do not warn merely for an unlisted build.
- Offline issue drafts must also accept explicit operator-reported runtime failure
  context (`--feature` plus `--failure-code`), as frozen in the source task. Probe
  success does not mean every live upstream operation works. Drafts clearly label
  operator-reported versus probe-observed failure; neither asserts the cause.
- The process/source qualification on the separate approvals branch is superseded
  as a version gate. Actual approval owner, profile binding, native notifier and
  request authority requirements remain. Do not merge a hidden exact gate later.
- No merge to main or native job test on the owner host is required just to install the
  reviewed focused commit. Install the exact reviewed commit after the existing
  scanner/doctor checks; preserve configuration and controls. A real send or job
  creation remains a separate owner test and is not automatically invoked.

The automatic runtime failure ledger and richer phone issue handoff are follow-on
work, explicitly not done by this deployment slice. The offline draft is usable
for both a probe failure and an owner-reported live feature failure.

Final review accepted the repaired source: issue drafts revalidate fixed metadata at the helper boundary, send probes include SessionDB.get_session, and a valid install stamp is authoritative before literal version evidence. Deployment is verified separately.

# Plan

A new internal `hmp_plugin.group_capabilities` module contains frozen DATA and a
pure parser. It has no importer in runtime code in this slice. Known method and
feature vocabularies come from source at Hermes4162ecf11f611400fa6e5c42d2f360188ce50b39
(`gateway/session_group_controls.py`); this pin is evidence only, never a gate.
The group protocol value is retained, not used as a release/version allowlist.

Boundary: already-decoded plain JSON dict -> bounded normalized observation.
Shallow exact-String key validation precedes any dict lookup, with at most64 keys
and128 characters per key; ignored values are not traversed. This prevents a
foreign key equality callback during a required-key lookup. Exact built-in
containers/scalars avoid custom mappings, booleans masquerading
as numbers and coercion callbacks. Known-only frozen sets prevent native profile,
endpoint, grant or unknown diagnostic data escaping through this result. Native
log count is positive integer DATA and is capped locally at500.

Before integrating a caller, GR1-AUTH02 must qualify the existing same-UID
explicit-endpoint canonical client/control ticket path, distinguish a native
owner from a paired device, and converge on device/room/bot authority and current
revocation/publication fencing. Current public client default can start a gateway;
explicit-endpoint branch omits restart-wait ticket policy. Do not wire around
those limitations through private AuthorityConnection objects or forged subjects.
The constitution's closed outbound surface is unchanged.

Independent review first checks this spec/checklist/analyze, then the exact code,
tests and causal failures. Run focused parser tests, repository privacy/log/plugin
surface checks and pinned ruff. Full native/device/release evidence stays open.

Caller prerequisite: exclusively own stable decoded built-in containers for the
whole synchronous parse. No concurrent input mutation is supported or fenced
here. Freezing the returned DATA does not establish original-input custody,
transport authority or a bounded JSON decoder/frame.

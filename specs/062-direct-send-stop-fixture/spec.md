# Keep the direct-send stop fixture aligned with the listener context

## Scope and plan

The current direct-send stop test constructs an unstarted listener with a reduced
SimpleNamespace context. It omits the readiness_reads field required by the real
ServerContext, so stop fails before reaching the pending-send cancellation check.
The real context declares this field and defaults it to None.

Supply the explicit absent-readiness-service value in this fixture only. Preserve
the existing real PendingSendTasks, waiting background coroutine, cancellation
spy, listener stop and assertions about cancellation and exact shutdown bound.
No production fallback, bypass, route, cleanup ordering or authority change.

## Tasks

- [x] Reproduce the exact isolated AttributeError with normal JUnit.
- [x] Add the explicit absent optional readiness service to the reduced fixture.
- [x] Run the complete direct-send file and related listener lifecycle tests.
- [x] Independent review and focused publication; keep broad failures separate.

## Qualification limits

Synthetic Darwin source tests do not establish full-suite, Linux CI, native/private
integration, actual listener traffic, device, host-update or release qualification.
The separate retained broad run uses its original immutable source and is not
modified or restarted by this fixture repair.

## Observed verification

The original test fails with AttributeError for readiness_reads before reaching
pending-send cancellation. After the explicit fixture field, complete
`test_direct_send.py` and `test_server.py` produce normal JUnit: 148 cases,
147 passes, zero failures/errors and one wheel-build skip because uv is absent
from the isolated test PATH. This is not wheel-build qualification or a claim
that the whole broader suite passes. Exact CI Ruff 0.16.9 accepts the one changed
Python file. Actual tests use Darwin/Python 3.14.4, temporary synthetic homes and
existing fake bridges; no production source is changed.

Independently accepted and published as [Draft PR177](https://github.com/MahdiHedhli/hermes-hmp/pull/177),
stacked on PR176. Publication does not install this source.

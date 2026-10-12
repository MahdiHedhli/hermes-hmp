from dataclasses import replace

from hmp_plugin.approval_test_producer import TestNotice as Notice
from hmp_plugin.approval_test_projection import TestProjection as Projection
from hmp_plugin.prompts import PromptStore


def test_projection_is_target_scoped_and_cleanup_identity_bound() -> None:
    store = PromptStore(clock=lambda: 100)
    projection = Projection(store, wall_clock=lambda: 100, monotonic=lambda: 10)
    notice = Notice("synthetic-instance", "synthetic-user", "default", "synthetic-session",
                    "synthetic-device", "synthetic-request", deadline_monotonic=20)
    assert projection.publish(notice)
    assert not projection.publish(notice)
    assert not store.list_visible(notice.instance_id, notice.user_id, notice.profile)
    rows = store.list_visible(notice.instance_id, notice.user_id, notice.profile,
                              device_id=notice.device_id)
    assert len(rows) == 1 and rows[0].choices == ("once", "deny")
    assert rows[0].session_key is None
    assert not projection.remove(replace(notice))
    assert projection.remove(notice)
    assert not store.list_visible(notice.instance_id, notice.user_id, notice.profile,
                                  device_id=notice.device_id)
    assert projection.remove(notice)


def test_closed_store_and_elapsed_deadline_refuse_publication() -> None:
    store = PromptStore(clock=lambda: 100)
    projection = Projection(store, wall_clock=lambda: 100, monotonic=lambda: 10)
    notice = Notice("synthetic-instance", "synthetic-user", "default", "synthetic-session",
                    "synthetic-device", "synthetic-request", deadline_monotonic=10)
    assert not projection.publish(notice)
    store.close(100)
    assert not projection.publish(replace(notice, deadline_monotonic=20))


def test_projection_never_rounds_deadline_beyond_native_waiter() -> None:
    store = PromptStore(clock=lambda: 100.25)
    projection = Projection(store, wall_clock=lambda: 100.25, monotonic=lambda: 10)
    notice = Notice("synthetic-instance", "synthetic-user", "default", "synthetic-session",
                    "synthetic-device", "synthetic-request", deadline_monotonic=11)
    assert projection.publish(notice)
    row = store.get((notice.instance_id, notice.user_id, notice.profile, notice.request_id))
    assert row is not None and row.expires_at == 101
    assert row.expires_at <= 101.25
    assert projection.remove(notice)
    assert not projection.publish(replace(notice, deadline_monotonic=10.1))


def test_answer_lookup_requires_owned_row_device_and_live_deadline() -> None:
    clock = [10.0]
    store = PromptStore(clock=lambda: 100)
    projection = Projection(store, wall_clock=lambda: 100, monotonic=lambda: clock[0])
    notice = Notice("synthetic-instance", "synthetic-user", "default", "synthetic-session",
                    "synthetic-device", "synthetic-request", deadline_monotonic=20)
    assert projection.publish(notice)
    row = store.get((notice.instance_id, notice.user_id, notice.profile, notice.request_id))
    assert row is not None
    assert projection.notice_for_answer(row, notice.device_id) is notice
    assert projection.notice_for_answer(row, "synthetic-other-device") is None
    assert projection.notice_for_answer(replace(row), notice.device_id) is None
    clock[0] = 20
    assert projection.notice_for_answer(row, notice.device_id) is None
    assert projection.remove(notice)


def test_pending_cleanup_or_other_choice_never_acknowledges_answer() -> None:
    from hmp_plugin.approval_test_producer import TestOutcome as Outcome
    from hmp_plugin.approval_test_producer import TestStatus as Status
    from hmp_plugin.approval_test_projection import settled_answer_verdict

    for status in (Status.PENDING, Status.CLEANUP_PENDING, Status.UNAVAILABLE):
        assert settled_answer_verdict(Outcome(status), "once") == "unavailable"
        assert settled_answer_verdict(Outcome(status), "deny") == "unavailable"
    assert settled_answer_verdict(Outcome(Status.ONCE_ACKNOWLEDGED), "once") == "accepted"
    assert settled_answer_verdict(Outcome(Status.DENIED), "deny") == "accepted"
    assert settled_answer_verdict(Outcome(Status.DENIED), "once") == "unavailable"
    assert settled_answer_verdict(Outcome(Status.ONCE_ACKNOWLEDGED), "always") == "unavailable"
    for status in (Status.CANCELLED, Status.EXPIRED):
        assert settled_answer_verdict(Outcome(status), "once") == "stale"

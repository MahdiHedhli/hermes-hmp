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

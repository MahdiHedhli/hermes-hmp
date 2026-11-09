"""Real Store SQL boundary, with a local currency observer; no daemon/IPC coverage."""
import pytest
from hmp_plugin.store import Store
from hmp_plugin.media_publication import MediaPublication, PublicationUnavailable

SCOPE = ('a' * 52, 'device', 'default', 1)


class Observer:
    def __init__(self):
        self.publisher = MediaPublication()
        self.events = []
        self.begin_lost = False
        self.settle_lost = False
    def begin(self):
        receipt = self.publisher.begin_mutation()
        self.events.append(('begin', receipt))
        if self.begin_lost: raise KeyboardInterrupt('synthetic begin return loss')
        return receipt
    def settle(self, receipt, *, certain):
        assert receipt is self.events[0][1]
        self.events.append(('settle', certain))
        self.publisher.settle_mutation(receipt, certain=certain)
        if self.settle_lost: raise KeyboardInterrupt('synthetic settlement return loss')


def setup(tmp_path):
    observer = Observer()
    store = Store(tmp_path / 'store.sqlite3', mutation_observer=observer)
    store.migrate()
    assert observer.events == []  # startup migration is explicitly NOT coordinated
    return store, observer


def count(store):
    return store._conn.execute('SELECT count(*) FROM users').fetchone()[0]


@pytest.mark.parametrize('rollback', (False, True))
def test_actual_sql_commit_or_rollback_is_one_original_observation(tmp_path, rollback):
    store, observer = setup(tmp_path)
    cohort = (object(), object(), object())
    old = observer.publisher.candidate(SCOPE, cohort)
    try:
        with store.transaction():
            assert not observer.publisher.claim_once(old, SCOPE, cohort)
            store.insert_user('synthetic', 'owner', 1)  # joins, never double-begins
            with pytest.raises(PublicationUnavailable): observer.publisher.candidate(SCOPE, cohort)
            if rollback: raise ValueError('synthetic body failure')
    except ValueError:
        assert rollback
    assert [x[0] for x in observer.events] == ['begin', 'settle']
    assert observer.events[-1] == ('settle', True)
    assert store._transaction_owner is None
    assert count(store) == (0 if rollback else 1)
    assert observer.publisher.claim_once(observer.publisher.candidate(SCOPE, cohort), SCOPE, cohort)
    store.close()


def test_begin_ack_loss_starts_no_sql_and_retains_closed_barrier(tmp_path):
    store, observer = setup(tmp_path); observer.begin_lost = True
    with pytest.raises(KeyboardInterrupt): store.insert_user('synthetic', 'owner', 1)
    assert count(store) == 0
    assert [x[0] for x in observer.events] == ['begin']
    with pytest.raises(PublicationUnavailable): observer.publisher.candidate(SCOPE, (1, 2, 3))
    store.close()


def test_settlement_ack_loss_preserves_committed_sql_without_replay(tmp_path):
    store, observer = setup(tmp_path); observer.settle_lost = True
    with pytest.raises(RuntimeError, match='settlement outcome unavailable'):
        store.insert_user('synthetic', 'owner', 1)
    assert count(store) == 1 and observer.events[-1] == ('settle', True)
    assert not store._poisoned and store._transaction_owner is None
    store.close()


def test_post_receipt_lock_interruption_settles_uncertain_before_sql(tmp_path):
    store, observer = setup(tmp_path)
    original = store._write_lock
    class InterruptedLock:
        def __enter__(self): raise KeyboardInterrupt('synthetic lock interruption')
        def __exit__(self, *args): raise AssertionError('not entered')
    store._write_lock = InterruptedLock()
    with pytest.raises(KeyboardInterrupt): store.insert_user('synthetic', 'owner', 1)
    store._write_lock = original
    assert count(store) == 0 and observer.events[-1] == ('settle', False)
    with pytest.raises(PublicationUnavailable): observer.publisher.candidate(SCOPE, (1, 2, 3))
    store.close()


def test_nested_refusal_acquires_no_second_receipt(tmp_path):
    store, observer = setup(tmp_path)
    with store.transaction():
        with pytest.raises(RuntimeError, match='nested'):
            with store.transaction(): pass
    assert len(observer.events) == 2
    store.close()


@pytest.mark.parametrize('lost', ('COMMIT', 'ROLLBACK'))
def test_sql_settlement_ack_loss_is_uncertain_and_poisoned(tmp_path, lost):
    import sqlite3
    store, observer = setup(tmp_path)
    original = store._conn
    class LostSqlAck:
        def execute(self, sql, *args):
            result = original.execute(sql, *args)
            if sql == lost: raise KeyboardInterrupt('synthetic SQL acknowledgement loss')
            return result
        def __getattr__(self, name): return getattr(original, name)
    store._conn = LostSqlAck()
    with pytest.raises(BaseException):
        with store.transaction():
            store.insert_user('synthetic', 'owner', 1)
            if lost == 'ROLLBACK': raise ValueError('synthetic body failure')
    assert store._poisoned
    assert observer.events[-1] == ('settle', False)
    with pytest.raises(PublicationUnavailable): observer.publisher.candidate(SCOPE, (1, 2, 3))
    # Observe the actual persisted SQL outcome independently, never replay it.
    with sqlite3.connect(str(store._path)) as readback:
        actual = readback.execute('SELECT count(*) FROM users').fetchone()[0]
    assert actual == (1 if lost == 'COMMIT' else 0)
    store._conn = original
    store.close()


def test_none_begin_receipt_starts_no_sql_and_never_settles_foreign_ownership(tmp_path):
    store, observer = setup(tmp_path)
    def no_receipt():
        observer.publisher.begin_mutation()  # orphan belongs to observer, not caller
        observer.events.append(('begin_none', None))
        return None
    observer.begin = no_receipt
    with pytest.raises(RuntimeError, match='mutation receipt unavailable'):
        store.insert_user('synthetic', 'owner', 1)
    assert count(store) == 0
    assert observer.events == [('begin_none', None)]
    with pytest.raises(PublicationUnavailable): observer.publisher.candidate(SCOPE, (1, 2, 3))
    store.close()

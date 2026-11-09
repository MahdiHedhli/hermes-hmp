"""Currency primitive only: no test result supplies real authorization coverage."""
import threading
import pytest
from hmp_plugin import media_publication as m

SCOPE = ('a' * 52, 'device', 'default', 1)


def test_claim_is_original_scoped_and_single_use():
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    assert not owner.claim_once(m.PublicationTicket(), SCOPE, cohort)
    assert owner.claim_once(ticket, SCOPE, cohort)
    assert not owner.claim_once(ticket, SCOPE, cohort)


@pytest.mark.parametrize('field', range(4))
def test_wrong_scope_consumes_only_original_ticket(field):
    owner = m.MediaPublication(); cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    changed = list(SCOPE); changed[field] = ('b' * 51 + 'a', 'other', 'named', 2)[field]
    assert not owner.claim_once(ticket, tuple(changed), cohort)
    assert not owner.claim_once(ticket, SCOPE, cohort)


def test_pending_nested_mutations_and_rollback_never_revive_candidate():
    owner = m.MediaPublication(); cohort = (object(), object(), object())
    old = owner.candidate(SCOPE, cohort)
    first = owner.begin_mutation(); second = owner.begin_mutation()
    assert not owner.claim_once(old, SCOPE, cohort)
    with pytest.raises(m.PublicationUnavailable): owner.candidate(SCOPE, cohort)
    owner.settle_mutation(first, certain=True)
    with pytest.raises(m.PublicationUnavailable): owner.candidate(SCOPE, cohort)
    owner.settle_mutation(second, certain=True)
    assert owner.claim_once(owner.candidate(SCOPE, cohort), SCOPE, cohort)
    assert not owner.claim_once(old, SCOPE, cohort)


def test_lost_ack_is_sticky_and_foreign_settlement_cannot_clear_it():
    owner = m.MediaPublication(); other = m.MediaPublication()
    ticket = owner.begin_mutation()
    with pytest.raises(m.PublicationUnavailable): other.settle_mutation(ticket, certain=True)
    owner.settle_mutation(ticket, certain=False)
    with pytest.raises(m.PublicationUnavailable): owner.candidate(SCOPE, (1, 2, 3))
    with pytest.raises(m.PublicationUnavailable): owner.begin_mutation()


def test_replaced_dependency_uses_identity_not_foreign_equality():
    class Foreign:
        def __eq__(self, other): raise AssertionError('foreign equality')
    owner = m.MediaPublication(); cohort = (Foreign(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    assert not owner.claim_once(ticket, SCOPE, (Foreign(), cohort[1], cohort[2]))


def test_expiry_close_and_foreign_thread_fail_closed(monkeypatch):
    owner = m.MediaPublication(); cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    errors = []
    def foreign():
        try: owner.close()
        except m.PublicationUnavailable: errors.append(True)
    thread = threading.Thread(target=foreign); thread.start(); thread.join()
    assert errors == [True]
    monkeypatch.setattr(m.time, 'monotonic_ns', lambda: 10 ** 30)
    assert not owner.claim_once(ticket, SCOPE, cohort)
    owner.close()
    with pytest.raises(m.PublicationUnavailable): owner.candidate(SCOPE, cohort)


def test_capacity_and_epoch_overflow_are_bounded_and_refuse():
    owner = m.MediaPublication(); cohort = (object(), object(), object())
    for _ in range(32): owner.candidate(SCOPE, cohort)
    with pytest.raises(m.PublicationUnavailable): owner.candidate(SCOPE, cohort)
    mutation = owner.begin_mutation()  # also clears every retained candidate
    owner.settle_mutation(mutation, certain=True)
    owner._epoch = m._MAX_EPOCH
    with pytest.raises(m.PublicationUnavailable): owner.begin_mutation()
    with pytest.raises(m.PublicationUnavailable): owner.candidate(SCOPE, cohort)


def test_foreign_scope_fields_do_not_dispatch_equality_or_length_hooks():
    class Foreign:
        def __eq__(self, other): raise AssertionError('foreign equality')
        def __len__(self): raise AssertionError('foreign length')
    owner = m.MediaPublication(); cohort = (object(), object(), object())
    for field in range(4):
        bad = list(SCOPE); bad[field] = Foreign()
        with pytest.raises(m.PublicationUnavailable): owner.candidate(tuple(bad), cohort)


def test_invalidation_releases_retained_dependency_cohort():
    import gc
    import weakref
    class Dependency: pass
    owner = m.MediaPublication()
    dependency = Dependency(); ref = weakref.ref(dependency)
    ticket = owner.candidate(SCOPE, (dependency, object(), object()))
    del dependency
    gc.collect(); assert ref() is not None
    mutation = owner.begin_mutation()
    gc.collect(); assert ref() is None
    assert not owner.claim_once(ticket, SCOPE, (object(), object(), object()))
    owner.settle_mutation(mutation, certain=True)


@pytest.mark.parametrize('certain', (True, False))
def test_interrupted_settlement_retains_pending_barrier(monkeypatch, certain):
    owner = m.MediaPublication(); cohort = (object(), object(), object())
    mutation = owner.begin_mutation()
    original = owner._advance
    def interrupted():
        original()
        raise KeyboardInterrupt('synthetic settlement interruption')
    monkeypatch.setattr(owner, '_advance', interrupted)
    with pytest.raises(KeyboardInterrupt): owner.settle_mutation(mutation, certain=certain)
    with pytest.raises(m.PublicationUnavailable): owner.candidate(SCOPE, cohort)
    assert mutation in owner._pending
    if not certain: assert owner._poisoned

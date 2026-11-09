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

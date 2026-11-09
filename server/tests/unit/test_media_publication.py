"""Currency primitive only: no test result supplies real authorization coverage."""

import threading

import pytest

from hmp_plugin import media_publication as m

SCOPE = ("a" * 52, "device", "default", 1)


def test_claim_is_original_scoped_and_single_use():
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    assert not owner.claim_once(m.PublicationTicket(), SCOPE, cohort)
    assert owner.claim_once(ticket, SCOPE, cohort)
    assert not owner.claim_once(ticket, SCOPE, cohort)


@pytest.mark.parametrize("field", range(4))
def test_wrong_scope_consumes_only_original_ticket(field):
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    changed = list(SCOPE)
    changed[field] = ("b" * 51 + "a", "other", "named", 2)[field]
    assert not owner.claim_once(ticket, tuple(changed), cohort)
    assert not owner.claim_once(ticket, SCOPE, cohort)


def test_pending_nested_mutations_and_rollback_never_revive_candidate():
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    old = owner.candidate(SCOPE, cohort)
    first = owner.begin_mutation()
    second = owner.begin_mutation()
    assert not owner.claim_once(old, SCOPE, cohort)
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, cohort)
    owner.settle_mutation(first, certain=True)
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, cohort)
    owner.settle_mutation(second, certain=True)
    assert owner.claim_once(owner.candidate(SCOPE, cohort), SCOPE, cohort)
    assert not owner.claim_once(old, SCOPE, cohort)


def test_lost_ack_is_sticky_and_foreign_settlement_cannot_clear_it():
    owner = m.MediaPublication()
    other = m.MediaPublication()
    ticket = owner.begin_mutation()
    with pytest.raises(m.PublicationUnavailableError):
        other.settle_mutation(ticket, certain=True)
    owner.settle_mutation(ticket, certain=False)
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, (1, 2, 3))
    with pytest.raises(m.PublicationUnavailableError):
        owner.begin_mutation()


def test_replaced_dependency_uses_identity_not_foreign_equality():
    class Foreign:
        def __eq__(self, other):
            raise AssertionError("foreign equality")

    owner = m.MediaPublication()
    cohort = (Foreign(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    assert not owner.claim_once(ticket, SCOPE, (Foreign(), cohort[1], cohort[2]))


def test_expiry_close_and_foreign_thread_fail_closed(monkeypatch):
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    errors = []

    def foreign():
        try:
            owner.close()
        except m.PublicationUnavailableError:
            errors.append(True)

    thread = threading.Thread(target=foreign)
    thread.start()
    thread.join()
    assert errors == [True]
    monkeypatch.setattr(m.time, "monotonic_ns", lambda: 10**30)
    assert not owner.claim_once(ticket, SCOPE, cohort)
    owner.close()
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, cohort)


def test_capacity_and_epoch_overflow_are_bounded_and_refuse():
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    for _ in range(32):
        owner.candidate(SCOPE, cohort)
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, cohort)
    mutation = owner.begin_mutation()  # also clears every retained candidate
    owner.settle_mutation(mutation, certain=True)
    owner._epoch = m._MAX_EPOCH
    with pytest.raises(m.PublicationUnavailableError):
        owner.begin_mutation()
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, cohort)


def test_foreign_scope_fields_do_not_dispatch_equality_or_length_hooks():
    class Foreign:
        def __eq__(self, other):
            raise AssertionError("foreign equality")

        def __len__(self):
            raise AssertionError("foreign length")

    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    for field in range(4):
        bad = list(SCOPE)
        bad[field] = Foreign()
        with pytest.raises(m.PublicationUnavailableError):
            owner.candidate(tuple(bad), cohort)


def test_invalidation_releases_retained_dependency_cohort():
    import gc
    import weakref

    class Dependency:
        pass

    owner = m.MediaPublication()
    dependency = Dependency()
    ref = weakref.ref(dependency)
    ticket = owner.candidate(SCOPE, (dependency, object(), object()))
    del dependency
    gc.collect()
    assert ref() is not None
    mutation = owner.begin_mutation()
    gc.collect()
    assert ref() is None
    assert not owner.claim_once(ticket, SCOPE, (object(), object(), object()))
    owner.settle_mutation(mutation, certain=True)


@pytest.mark.parametrize("certain", (True, False))
def test_interrupted_settlement_retains_pending_barrier(monkeypatch, certain):
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    mutation = owner.begin_mutation()
    original = owner._advance

    def interrupted():
        original()
        raise KeyboardInterrupt("synthetic settlement interruption")

    monkeypatch.setattr(owner, "_advance", interrupted)
    with pytest.raises(KeyboardInterrupt):
        owner.settle_mutation(mutation, certain=certain)
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, cohort)
    assert mutation in owner._pending
    if not certain:
        assert owner._poisoned


def _interrupt_at(function, operation, *, marker=None):
    """Interrupt the actual Python line/return boundary, without production hooks."""
    import inspect
    import sys

    code = function.__func__.__code__
    source, first = inspect.getsourcelines(function)
    matches = [] if marker is None else [i for i, text in enumerate(source) if marker in text]
    if marker is not None:
        assert len(matches) == 1, "handoff marker must identify exactly one source line"
    line = None if marker is None else first + matches[0]
    reached = []

    def trace(frame, event, arg):
        if frame.f_code is code and (
            (marker is None and event == "return")
            or (marker is not None and event == "line" and frame.f_lineno == line)
        ):
            reached.append(True)
            raise KeyboardInterrupt("synthetic handoff loss")
        return trace

    previous = sys.gettrace()
    try:
        sys.settrace(trace)
        with pytest.raises(KeyboardInterrupt):
            operation()
    finally:
        sys.settrace(previous)
    assert reached == [True]


@pytest.mark.parametrize("marker", ("self._pending[ticket] = None", None))
def test_begin_handoff_loss_never_authorizes_outer_write(marker):
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    old = owner.candidate(SCOPE, cohort)
    writes = []

    def outer():
        receipt = owner.begin_mutation()
        writes.append(receipt)  # never reached without receiving original receipt

    _interrupt_at(owner.begin_mutation, outer, marker=marker)
    assert writes == []
    assert not owner.claim_once(old, SCOPE, cohort)
    if marker is None:
        with pytest.raises(m.PublicationUnavailableError):
            owner.candidate(SCOPE, cohort)
    else:
        # Invalidation completed but the writer never received permission to start.
        assert owner.claim_once(owner.candidate(SCOPE, cohort), SCOPE, cohort)


@pytest.mark.parametrize("certain", (True, False))
@pytest.mark.parametrize("marker", ("del self._pending[ticket]", None))
def test_settlement_line_or_return_loss_has_no_automatic_replay(certain, marker):
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    mutation = owner.begin_mutation()
    writes = ["one completed synthetic mutation"]

    def outer():
        owner.settle_mutation(mutation, certain=certain)
        writes.append("acknowledged")

    _interrupt_at(owner.settle_mutation, outer, marker=marker)
    assert writes == ["one completed synthetic mutation"]
    if not certain or marker is not None:
        with pytest.raises(m.PublicationUnavailableError):
            owner.candidate(SCOPE, cohort)
    else:
        # Settlement really completed. A missing caller acknowledgement is NOT a
        # reason to repeat the mutation or manufacture a second settlement receipt.
        assert owner.claim_once(owner.candidate(SCOPE, cohort), SCOPE, cohort)
        with pytest.raises(m.PublicationUnavailableError):
            owner.settle_mutation(mutation, certain=True)


@pytest.mark.parametrize("marker", ("self._candidates.clear()", None))
def test_close_line_and_return_loss_stay_closed(marker):
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    _interrupt_at(owner.close, owner.close, marker=marker)
    assert not owner.claim_once(ticket, SCOPE, cohort)
    with pytest.raises(m.PublicationUnavailableError):
        owner.candidate(SCOPE, cohort)


def test_lost_candidate_return_cannot_start_sampling_and_retention_expires(monkeypatch):
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    samples = []

    def outer():
        ticket = owner.candidate(SCOPE, cohort)
        samples.append(ticket)

    _interrupt_at(owner.candidate, outer)
    assert samples == [] and len(owner._candidates) == 1
    monkeypatch.setattr(m.time, "monotonic_ns", lambda: 10**30)
    owner.candidate(SCOPE, cohort)
    assert len(owner._candidates) == 1  # expired orphan replaced, never accumulated


def test_lost_claim_return_cannot_publish_or_reuse_receipt():
    owner = m.MediaPublication()
    cohort = (object(), object(), object())
    ticket = owner.candidate(SCOPE, cohort)
    sent = []

    def outer():
        if owner.claim_once(ticket, SCOPE, cohort):
            sent.append("publish")

    _interrupt_at(owner.claim_once, outer)
    assert sent == []
    assert not owner.claim_once(ticket, SCOPE, cohort)

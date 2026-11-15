"""Real SHA state and explicit lost-boundary causals; DATA, not native authority."""
import hashlib

import pytest

from hmp_plugin import presentation_credential_payload_digest as module
from hmp_plugin.presentation_credential_payload_digest import PayloadDigest
from hmp_plugin.presentation_jobs import FrameError


def test_seeded_copy_hashes_result2_body_and_does_not_change_original():
    seed = hashlib.sha256(b"original-prefix")
    before = seed.hexdigest()
    digest = PayloadDigest(source=seed, seed_count=15, seed_sha256=before)
    digest.feed(b"-body-rest")
    fact = digest.finish(25)
    assert seed.hexdigest() == before
    assert fact.sha256 == hashlib.sha256(b"original-prefix-body-rest").hexdigest()
    assert fact.count == 25 and fact.hasher is not seed
    assert digest.current_fact(25) is fact
    for action in (lambda: digest.feed(b"x"), lambda: digest.finish(25)):
        with pytest.raises(FrameError):
            action()


def test_fresh_result2_body_hash_has_no_buffer():
    digest = PayloadDigest()
    for part in (b"header", b"-metadata", b"-image"):
        digest.feed(part)
    assert digest.finish(21).sha256 == hashlib.sha256(b"header-metadata-image").hexdigest()
    assert not any(type(v) in (bytes, bytearray, memoryview) for v in vars(digest).values())


@pytest.mark.parametrize("fault", ["mismatch", "same", "lost"])
def test_bad_or_uncertain_seed_copy_cannot_retry(monkeypatch, fault):
    source = hashlib.sha256(b"seed")
    original = module._COPY
    def copy(value):
        result = original(value)
        if fault == "lost":
            raise OSError("synthetic hash copy acknowledgement lost")
        return value if fault == "same" else result
    monkeypatch.setattr(module, "_COPY", copy)
    digest = PayloadDigest.__new__(PayloadDigest)
    with pytest.raises(FrameError):
        PayloadDigest.__init__(digest, source=source, seed_count=4,
                               seed_sha256="0" * 64 if fault == "mismatch" else source.hexdigest())
    assert digest._failed
    with pytest.raises(FrameError):
        PayloadDigest.__init__(digest)
    assert source.hexdigest() == hashlib.sha256(b"seed").hexdigest()


@pytest.mark.parametrize("fault", ["lost", "skipped", "prior_corrupt"])
def test_update_boundary_is_unknown_without_replay(monkeypatch, fault):
    digest = PayloadDigest()
    hasher = digest._hasher_origin
    original = module._UPDATE
    def update(value, chunk):
        if value is hasher and fault == "skipped":
            return None
        original(value, chunk)
        if value is hasher and fault == "lost":
            raise OSError("synthetic hash update acknowledgement lost")
    monkeypatch.setattr(module, "_UPDATE", update)
    if fault == "prior_corrupt":
        original(hasher, b"uncredited")
    with pytest.raises(FrameError) as raised:
        digest.feed(b"actual")
    assert raised.value.__context__ is None
    cursor = raised.value.__traceback__
    while cursor is not None:
        if cursor.tb_frame.f_code.co_name != "test_update_boundary_is_unknown_without_replay":
            assert not any(type(v) is bytes and v == b"actual"
                           for v in cursor.tb_frame.f_locals.values())
        cursor = cursor.tb_next
    assert digest._failed
    assert not digest._update.complete
    assert digest._update.attempted is (fault != "prior_corrupt")
    with pytest.raises(FrameError):
        digest.feed(b"actual")
    with pytest.raises(FrameError):
        digest.finish(6)


def test_foreign_hash_return_does_not_run_equality(monkeypatch):
    digest = PayloadDigest()
    called = []
    class Foreign:
        def __eq__(self, other):
            called.append(True)
            raise AssertionError("foreign digest")
    monkeypatch.setattr(module, "_HEX", lambda value: Foreign())
    with pytest.raises(FrameError):
        digest.finish(0)
    assert digest._failed and called == []


def test_post_hash_fact_copy_refuses_original_return(monkeypatch):
    digest = PayloadDigest()
    current = PayloadDigest._current
    def changed(value):
        result = current(value)
        if value._fact is not None:
            copied = value._fact._replace()
            value._fact, value._fact_cell = copied, (value, copied)
        return result
    monkeypatch.setattr(PayloadDigest, "_current", changed)
    with pytest.raises(FrameError):
        digest.finish(0)
    assert digest._failed and digest._finish_attempted


@pytest.mark.parametrize("state", ["failed", "finished", "uninitialized", "foreign_self"])
def test_early_feed_refusal_drops_body_alias(state):
    digest = PayloadDigest()
    if state == "failed":
        digest._failed = True
    elif state == "finished":
        digest.finish(0)
    elif state == "uninitialized":
        digest = PayloadDigest.__new__(PayloadDigest)
    else:
        digest = object()
    with pytest.raises(FrameError) as raised:
        PayloadDigest.feed(digest, b"early-private-body")
    assert raised.value.__context__ is None
    cursor = raised.value.__traceback__
    while cursor is not None:
        if cursor.tb_frame.f_code.co_name == "feed":
            assert cursor.tb_frame.f_locals["chunk"] is None
        cursor = cursor.tb_next


def test_native_feed_wrapper_drops_body_alias_on_preflight_refusal():
    from hmp_plugin.presentation_credential_cleanup_payload import feed
    with pytest.raises(FrameError) as raised:
        feed(object(), b"early-private-body", 18)
    assert raised.value.__context__ is None
    cursor = raised.value.__traceback__
    while cursor is not None:
        if cursor.tb_frame.f_code.co_name == "feed":
            assert cursor.tb_frame.f_locals["chunk"] is None
        cursor = cursor.tb_next

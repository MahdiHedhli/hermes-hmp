"""Registry causals; no service/native input or live Hermes profile content."""

import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from hmp_plugin import presentation_broker_child as child_module
from hmp_plugin import presentation_broker_registry as module
from hmp_plugin.presentation_broker_codec import BrokerBinding
from hmp_plugin.presentation_broker_lifecycle import operation_id
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_pipes import OwnedPresentationPipes


def binding(serial=1):
    return BrokerBinding("a" * 52, "b" * 32, "c" * 64, "d" * 64, operation_id(serial))


def reserve(registry, serial=1, profile=None, kind="METADATA"):
    b = binding(serial)
    return b, registry.reserve(
        b, profile or f"p{serial}", kind, time.monotonic_ns() + 1_900_000_000
    )


@pytest.fixture
def fake_children(monkeypatch):
    children = []

    def spawn():
        child = SimpleNamespace(
            pid=400000 + len(children),
            returncode=None,
            stdin=object(),
            stdout=object(),
            stderr=object(),
        )
        children.append(child)
        return child

    monkeypatch.setattr(child_module, "_POPEN_TYPE", SimpleNamespace)
    monkeypatch.setattr(child_module, "_allocate_popen", spawn)
    monkeypatch.setattr(child_module, "_initialize_popen", lambda *a, **k: None)
    monkeypatch.setattr(child_module.os, "getpgid", lambda pid: module.os.getpgrp())
    monkeypatch.setattr(child_module.os, "killpg", lambda *a: pytest.fail("group signal"))
    return children


def test_fixed_owner_retained_before_any_observable_start(monkeypatch, fake_children):
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    record = registry._records[ticket]
    original = record.owner.start

    def start():
        assert registry._records[ticket] is record
        assert record.owner is record.owner_snapshot
        assert record.start_attempted and registry._counts().active == 1
        original()

    monkeypatch.setattr(record.owner, "start", start)
    streams = registry.start(ticket)
    assert streams.control is fake_children[0].stdin
    assert registry.status(b) is RegistryStatus.PENDING
    with pytest.raises(FrameError):
        registry.seal_unlaunched(ticket)
    with pytest.raises(FrameError):
        registry.acknowledge(b)
    assert registry.counts.active == 1


def test_unlaunched_terminal_global_ack_replay_and_fresh_status_channel():
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    registry.seal_unlaunched(ticket)
    changed_channel = replace(b, channel="e" * 64)
    assert registry.status(changed_channel) is RegistryStatus.CLOSED
    assert registry.acknowledge(changed_channel)
    assert not registry.acknowledge(b)
    assert registry.status(b) is RegistryStatus.UNKNOWN
    assert registry.counts.terminal == 0
    with pytest.raises(FrameError):
        registry.reserve(b, "p1", "METADATA", time.monotonic_ns() + 1_000_000_000)


def test_queued_limit_and_refused_serial_is_burned():
    registry = BrokerRegistry(binding())
    tickets = [reserve(registry, i)[1] for i in range(1, 17)]
    b = binding(17)
    with pytest.raises(FrameError):
        registry.reserve(b, "later", "METADATA", time.monotonic_ns() + 1_000_000_000)
    registry.seal_unlaunched(tickets[0])
    registry.acknowledge(binding(1))  # different random operation is NOT a matching ACK
    with pytest.raises(FrameError):
        registry.reserve(b, "later", "METADATA", time.monotonic_ns() + 1_000_000_000)
    assert registry.counts.waiting == 15


def test_reserved_journal_capacity_no_eviction():
    registry = BrokerRegistry(binding())
    bindings = []
    for i in range(1, 65):
        b, t = reserve(registry, i)
        bindings.append(b)
        registry.seal_unlaunched(t)
    assert registry.counts.terminal == 64
    b = binding(65)
    with pytest.raises(FrameError):
        registry.reserve(b, "full", "AVATAR", time.monotonic_ns() + 1_000_000_000)
    assert registry.status(bindings[0]) is RegistryStatus.CLOSED
    registry.acknowledge(bindings[0])
    with pytest.raises(FrameError):
        registry.reserve(b, "full", "AVATAR", time.monotonic_ns() + 1_000_000_000)
    reserve(registry, 66)
    assert registry.counts.terminal == 63 and registry.counts.waiting == 1


def test_type_total_and_per_profile_caps_across_kinds(fake_children):
    registry = BrokerRegistry(binding())
    for i in range(1, 5):
        registry.start(reserve(registry, i)[1])
    _, meta = reserve(registry, 5)
    with pytest.raises(FrameError):
        registry.start(meta)
    _, sameprofile = reserve(registry, 6, profile="p1", kind="AVATAR")
    with pytest.raises(FrameError):
        registry.start(sameprofile)
    registry.start(reserve(registry, 7, kind="AVATAR")[1])
    registry.start(reserve(registry, 8, kind="AVATAR")[1])
    _, extra = reserve(registry, 9, kind="AVATAR")
    with pytest.raises(FrameError):
        registry.start(extra)
    assert registry.counts.active == 6 and len(fake_children) == 6


@pytest.mark.parametrize(
    "field,value", [("iid", "b" * 51 + "a"), ("listener", "f" * 32), ("broker", "f" * 64)]
)
def test_cross_scope_never_looks_up_or_releases(field, value):
    registry = BrokerRegistry(binding())
    b, t = reserve(registry)
    registry.seal_unlaunched(t)
    other = replace(b, **{field: value})
    with pytest.raises(FrameError):
        registry.status(other)
    with pytest.raises(FrameError):
        registry.acknowledge(other)
    assert registry.status(b) is RegistryStatus.CLOSED


@pytest.mark.parametrize(
    "profile,kind,deadline",
    [
        (True, "METADATA", 100),
        ("../private", "METADATA", 100),
        ("p", "other", 100),
        ("p", "METADATA", True),
        ("p", "METADATA", float("inf")),
    ],
)
def test_invalid_shapes_refuse_before_hash_or_spawn(profile, kind, deadline, fake_children):
    registry = BrokerRegistry(binding())
    with pytest.raises(FrameError):
        registry.reserve(binding(), profile, kind, deadline)
    assert registry.counts.waiting == 0 and fake_children == []


def test_foreign_ticket_hash_never_runs():
    registry = BrokerRegistry(binding())
    calls = []

    class Foreign:
        def __hash__(self):
            calls.append("hash")
            return 1

    with pytest.raises(FrameError):
        registry.start(Foreign())
    assert calls == []


def test_unknown_constructor_retains_reserved_record(monkeypatch):
    registry = BrokerRegistry(binding())

    class FailOwner:
        def __init__(self, *a, **k):
            assert registry._counts().waiting == 1
            raise RuntimeError("synthetic construction ambiguity")

    monkeypatch.setattr(module, "BrokerChildOwner", FailOwner)
    with pytest.raises(FrameError):
        reserve(registry)
    # Restore exact type before validating the retained, ownerless unknown record.
    monkeypatch.setattr(module, "BrokerChildOwner", child_module.BrokerChildOwner)
    assert registry.counts.waiting == 1 and registry.counts.unknown == 1
    assert len(registry._records) == 1


def test_start_failure_keeps_active_owner_no_seal_ack_or_replay(monkeypatch):
    registry = BrokerRegistry(binding())
    b, t = reserve(registry)
    owner = registry._records[t].owner

    def fail(*a, **k):
        raise OSError("synthetic launch")

    monkeypatch.setattr(child_module, "_initialize_popen", fail)
    with pytest.raises(FrameError):
        registry.start(t)
    assert registry._records[t].owner is owner
    assert registry.counts.active == 1 and registry.counts.unknown == 1
    assert registry.status(b) is RegistryStatus.PENDING
    with pytest.raises(FrameError):
        registry.seal_unlaunched(t)
    with pytest.raises(FrameError):
        registry.acknowledge(b)


def test_atomic_competing_original_and_status_ack_release_once():
    registry = BrokerRegistry(binding())
    b, t = reserve(registry)
    registry.seal_unlaunched(t)
    outcomes = []
    barrier = threading.Barrier(2)

    def ack(channel):
        barrier.wait()
        try:
            outcomes.append(registry.acknowledge(replace(b, channel=channel)))
        except FrameError:
            outcomes.append("refused")

    a = threading.Thread(target=ack, args=("e" * 64,))
    c = threading.Thread(target=ack, args=("f" * 64,))
    a.start()
    c.start()
    a.join(timeout=2)
    c.join(timeout=2)
    assert not a.is_alive() and not c.is_alive()
    assert outcomes.count(True) <= 1
    # Reentry may poison conservatively; no second capacity removal is possible.
    assert len(registry._records) <= 1


def test_rebound_sealed_fact_poisoned_never_closed_or_ack():
    registry = BrokerRegistry(binding())
    b, t = reserve(registry)
    registry.seal_unlaunched(t)
    owner = registry._records[t].owner
    owner._binding = object()
    with pytest.raises(FrameError):
        registry.status(b)
    owner._binding = owner._binding_snapshot
    with pytest.raises(FrameError):
        registry.acknowledge(b)
    assert len(registry._records) == 1


def test_registry_start_deadline_does_not_extend_queue(fake_children, monkeypatch):
    registry = BrokerRegistry(binding())
    _, t = reserve(registry)
    deadline = registry._records[t].deadline_ns
    monkeypatch.setattr(module.time, "monotonic_ns", lambda: deadline)
    with pytest.raises(FrameError):
        registry.start(t)
    assert registry.counts.waiting == 1 and fake_children == []


def test_actual_fixed_reader_exact_reap_and_pipe_eof_do_not_release_reservation():
    registry = BrokerRegistry(binding())
    b, t = reserve(registry)
    streams = registry.start(t)
    streams.control.close()
    pipes = OwnedPresentationPipes(streams.result, streams.diagnostic)
    deadline = time.monotonic() + 3
    while not pipes.drained:
        pipes.poll(deadline=deadline)
    while not registry.poll_wait(t):
        assert time.monotonic() < deadline
        time.sleep(0.005)
    assert pipes.drained and pipes.output == b""
    assert registry.status(b) is RegistryStatus.PENDING
    assert registry.counts.active == 1
    with pytest.raises(FrameError):
        registry.acknowledge(b)


def test_malformed_retained_operation_key_refuses_before_equality_callback():
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    callbacks = []

    class ForeignKey:
        def __hash__(self):
            return hash(b.operation)

        def __eq__(self, other):
            callbacks.append("eq")
            return True

    # Construct this separate malformed table without comparing against a valid key.
    foreign = ForeignKey()
    registry._operations = {foreign: ticket}
    with pytest.raises(FrameError):
        registry.status(b)
    assert callbacks == [] and len(registry._records) == 1


def test_reentry_retains_all_owners_and_never_emits_closed():
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    registry.seal_unlaunched(ticket)
    registry._lock.acquire()
    try:
        with pytest.raises(FrameError):
            registry.status(b)
    finally:
        registry._lock.release()
    with pytest.raises(FrameError):
        registry.status(b)
    with pytest.raises(FrameError):
        registry.acknowledge(b)
    assert len(registry._records) == 1


def test_changed_retained_metadata_poison_is_sticky_after_restoration():
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    record = registry._records[ticket]
    original = record.profile
    record.profile = "other"
    with pytest.raises(FrameError):
        registry.status(b)
    record.profile = original
    with pytest.raises(FrameError):
        registry.seal_unlaunched(ticket)
    assert len(registry._records) == 1


def test_startup_recipe_drift_does_not_launch_or_choose_new_executable(monkeypatch):
    registry = BrokerRegistry(binding())
    _, ticket = reserve(registry)
    callbacks = []

    class ForeignExecutable:
        def __eq__(self, other):
            callbacks.append("eq")
            return True

        def __fspath__(self):
            callbacks.append("path")
            return "/untrusted"

    object.__setattr__(registry._recipe, "argv", (ForeignExecutable(),))
    monkeypatch.setattr(
        child_module, "_initialize_popen", lambda *a, **k: pytest.fail("recipe drift spawn")
    )
    with pytest.raises(FrameError):
        registry.start(ticket)
    assert callbacks == [] and len(registry._records) == 1


def test_constructed_owner_recipe_must_match_original_startup(monkeypatch):
    registry = BrokerRegistry(binding())
    original = child_module.child_launch

    def changed(parser):
        recipe = original(parser)
        return replace(recipe, argv=("/untrusted", *recipe.argv[1:]))

    monkeypatch.setattr(child_module, "child_launch", changed)
    monkeypatch.setattr(
        child_module, "_initialize_popen", lambda *a, **k: pytest.fail("changed recipe spawn")
    )
    with pytest.raises(FrameError):
        reserve(registry)
    record = next(iter(registry._records.values()))
    assert record.owner is not None and record.unknown


def test_reap_unknown_retained_owner_can_still_attempt_safe_exact_cleanup(
    monkeypatch, fake_children
):
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    registry.start(ticket)
    registry._records[ticket].unknown = True
    calls = []
    monkeypatch.setattr(
        child_module.os, "waitpid", lambda pid, flags: calls.append(pid) or (pid, 0)
    )
    assert registry.poll_wait(ticket)
    assert calls == [fake_children[0].pid]
    assert registry.counts.active == 1 and registry.counts.unknown == 1
    assert registry.status(b) is RegistryStatus.PENDING
    with pytest.raises(FrameError):
        registry.acknowledge(b)


def test_ownership_check_crossing_deadline_does_not_spawn(monkeypatch, fake_children):
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    record = registry._records[ticket]
    original = record.owner.owns

    def delayed(binding):
        accepted = original(binding)
        monkeypatch.setattr(module.time, "monotonic_ns", lambda: record.deadline_ns)
        return accepted

    monkeypatch.setattr(record.owner, "owns", delayed)
    with pytest.raises(FrameError):
        registry.start(ticket)
    assert fake_children == []
    assert registry.counts.active == 1 and registry.counts.unknown == 1
    assert registry.status(b) is RegistryStatus.PENDING


def test_deadline_crossing_inside_spawn_keeps_owner_and_refuses_normal_return(
    monkeypatch, fake_children
):
    registry = BrokerRegistry(binding())
    b, ticket = reserve(registry)
    record = registry._records[ticket]
    spawn = child_module._initialize_popen

    def delayed(*a, **k):
        child = spawn(*a, **k)
        monkeypatch.setattr(module.time, "monotonic_ns", lambda: record.deadline_ns)
        return child

    monkeypatch.setattr(child_module, "_initialize_popen", delayed)
    with pytest.raises(FrameError):
        registry.start(ticket)
    assert len(fake_children) == 1
    assert record.owner._child_snapshot is fake_children[0]
    assert registry.counts.active == 1 and registry.counts.unknown == 1
    assert registry.status(b) is RegistryStatus.PENDING

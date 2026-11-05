"""Full fixed reader on NEW synthetic roots; no live host/native authority."""

import hashlib
import os
import stat
import struct
import tempfile
import time
import zlib
from pathlib import Path

import pytest
import yaml

from hmp_plugin import presentation_broker_resources as module
from hmp_plugin.presentation_broker_codec import BrokerBinding
from hmp_plugin.presentation_broker_lifecycle import operation_id
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_broker_resources import BrokerLocalDrainObservation
from hmp_plugin.presentation_budget import PresentationWorkLedger
from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from hmp_plugin.presentation_input_v3 import encode_input_v3
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_output_v2 import decode_output_v2
from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner
from hmp_plugin.presentation_posix import PosixFileOps


def image():
    def chunk(kind, body):
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x8b\x5c\xf6\xff"))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def synthetic():
    parent = Path.cwd()
    if any(
        stat.S_IMODE(p.stat().st_mode) not in (0o700, 0o750, 0o755)
        for p in (parent, *parent.parents)
    ):
        pytest.skip("synthetic fixed-reader roots require safe ancestors")
    with tempfile.TemporaryDirectory(prefix="hmp-broker-resources-synthetic-", dir=parent) as raw:
        home = Path(raw)
        (home / "profile.yaml").write_text(
            "display_name: Synthetic Resource\n"
            "ui_meta: {hermes-bots: {shape: hexagon, color: '#8b5cf6'}}\n"
        )
        (home / "profile.yaml").chmod(0o600)
        (home / "assets").mkdir(mode=0o700)
        (home / "assets" / "avatar.png").write_bytes(image())
        (home / "assets" / "avatar.png").chmod(0o600)
        made = []

        def make(kind="METADATA", asset=None, profile="default"):
            target = home if profile == "default" else home / "profiles" / profile
            if profile != "default":
                target.mkdir(mode=0o700, parents=True)
                (target / "profile.yaml").write_text("display_name: Other Synthetic\n")
                (target / "profile.yaml").chmod(0o600)
                (target / "assets").mkdir(mode=0o700)
                (target / "assets" / "avatar.png").write_bytes(image())
                (target / "assets" / "avatar.png").chmod(0o600)
            if asset is not None:
                (target / "assets" / "avatar.png").write_bytes(asset)
            asset_sha = hashlib.sha256((target / "assets" / "avatar.png").read_bytes()).hexdigest()
            deadline = time.monotonic_ns() + 1_900_000_000
            ledger = PresentationWorkLedger(clock=time.monotonic, deadline=deadline / 1e9)
            parent_owner = ParentPolicyReadOwner(
                root=str(home),
                home=str(target),
                profile=profile,
                uid=os.geteuid(),
                gid=os.getegid(),
                ledger=ledger,
                fs=PosixFileOps(),
                current=lambda: True,
            )
            snapshot = parent_owner.run()
            assert parent_owner.descriptors_closed
            b = BrokerBinding("a" * 52, "b" * 32, "c" * 64, "d" * 64, operation_id(len(made) + 1))
            registry = BrokerRegistry(b, parser_package=str(Path(yaml.__file__).resolve().parent))
            ticket = registry.reserve(b, profile, kind, deadline)
            row = {
                "schema": 3,
                "challenge": "e" * 64,
                "epoch": 1,
                "profile": profile,
                "root": str(home),
                "home": str(target),
                "operation": kind,
                "expected_avatar_sha": asset_sha if kind == "AVATAR" else None,
                "uid": os.geteuid(),
                "gid": os.getegid(),
                "dir_modes": [0o700, 0o750, 0o755],
                "leaf_modes": [0o600, 0o640, 0o644],
                "source_manifest_sha": "f" * 64,
                "deadline_ns": deadline,
                "directory_policy": [[r.uid, r.gid, r.modes[0]] for r in snapshot.rules],
                "iid": b.iid,
                "canonical_fallback": "Hermes",
                "observed_at": 100,
                "parent_work_counts": dict(snapshot.counts),
            }
            made.append((registry, ticket))
            return registry, ticket, b, row

        yield make
        # Tests never infer protocol success during fixture teardown. Each actual
        # own child is reaped; only exact known fixture streams/selectors close.
        from io import FileIO

        for registry, ticket in made:
            record = registry._records[ticket]
            owner = record.owner
            if not owner._launch_attempted:
                continue
            resources = record.resources
            if owner._wait is None and not owner.uncertain:
                if not owner.signals_retired:
                    owner.terminate_once()
                until = time.monotonic() + 3
                while not owner.poll_wait():
                    assert time.monotonic() < until
                    time.sleep(0.005)
            if owner._child is not None:
                for stream in (owner._child.stdin, owner._child.stdout, owner._child.stderr):
                    if type(stream) is FileIO and not FileIO.closed.__get__(stream, FileIO):
                        FileIO.close(stream)
            if resources is not None and getattr(resources, "_pipes", None) is not None:
                selector = resources._pipes._selector
                if selector is not None:
                    type(selector).close(selector)


def complete(registry, ticket, row):
    registry.start_resources(ticket)
    registry.stage_resource_input(ticket, encode_input_v3(row))
    registry.relay_resource_go(ticket)
    while not registry.poll_resource_result(ticket):
        assert time.monotonic_ns() < row["deadline_ns"]
        time.sleep(0.002)
    return registry._records[ticket].resources


def cleanup(registry, ticket):
    registry.abort_resources(ticket)
    resources = registry._records[ticket].resources
    frozen = resources._cleanup_end_ns
    while not registry.poll_resource_cleanup(ticket):
        if time.monotonic_ns() >= frozen:
            return False
        time.sleep(0.001)
    assert resources._cleanup_end_ns == frozen
    return True


@pytest.mark.parametrize("kind", ["METADATA", "AVATAR"])
def test_actual_fixed_processing_candidate_and_local_observation_stay_pending(synthetic, kind):
    registry, ticket, b, row = synthetic(kind)
    resources = complete(registry, ticket, row)
    fact = registry.resource_local_observation(ticket)
    assert resources.validates_local(registry._records[ticket], fact)
    assert not resources.validates_local(
        registry._records[ticket], BrokerLocalDrainObservation(fact.scope, fact.exit_code)
    )
    assert registry.poll_resource_result(ticket)  # no duplicate reap or decoder/pipe replay
    wire = registry.take_resource_candidate(ticket)
    header, avatar = decode_output_v2(wire, row["challenge"], row["epoch"])
    assert header["fields"]["display_name"] == "Synthetic Resource"
    assert avatar == image()  # metadata also carries bounded asset/revision processing proof
    assert not resources._candidate and resources._pipes.output == b""
    assert registry.status(b) is RegistryStatus.PENDING and registry.counts.active == 1
    with pytest.raises(FrameError):
        registry.acknowledge(b)
    with pytest.raises(FrameError):
        registry.take_resource_candidate(ticket)


@pytest.mark.parametrize("stage", ["preinput", "input", "go"])
def test_actual_cancelled_local_drain_never_restores_work_or_releases_slot(synthetic, stage):
    registry, ticket, b, row = synthetic()
    registry.start_resources(ticket)
    if stage in ("input", "go"):
        registry.stage_resource_input(ticket, encode_input_v3(row))
    if stage == "go":
        registry.relay_resource_go(ticket)
    assert cleanup(registry, ticket)
    resources = registry._records[ticket].resources
    fact = registry.resource_local_observation(ticket)
    assert resources.validates_local(registry._records[ticket], fact)
    assert registry.status(b) is RegistryStatus.PENDING
    with pytest.raises(FrameError):
        registry.take_resource_candidate(ticket)


def test_cancel_after_success_wipes_buffer_and_preserves_only_local_fact(synthetic):
    registry, ticket, _b, row = synthetic()
    resources = complete(registry, ticket, row)
    assert resources._candidate
    assert cleanup(registry, ticket)
    assert not resources._candidate and resources._input_context is None
    assert registry.resource_local_observation(ticket)
    with pytest.raises(FrameError):
        registry.take_resource_candidate(ticket)


@pytest.mark.parametrize(
    "field,value",
    [("iid", "b" * 51 + "a"), ("profile", "other"), ("operation", "AVATAR"), ("deadline_ns", 123)],
)
def test_mismatched_input_scope_never_goes_and_can_cleanup(synthetic, field, value):
    registry, ticket, b, row = synthetic()
    registry.start_resources(ticket)
    row[field] = value
    with pytest.raises(FrameError):
        registry.stage_resource_input(ticket, encode_input_v3(row))
    assert not registry._records[ticket].resources._go_attempted
    assert cleanup(registry, ticket)
    assert registry.status(b) is RegistryStatus.PENDING


def test_managed_child_cannot_use_unmanaged_wait_signal_or_start(synthetic):
    registry, ticket, _, _ = synthetic()
    registry.start_resources(ticket)
    for method in (
        registry.start,
        registry.poll_wait,
        registry.terminate_once,
        registry.seal_unlaunched,
    ):
        with pytest.raises(FrameError):
            method(ticket)
    assert cleanup(registry, ticket)


def test_managed_object_retained_before_constructor_and_child_start(synthetic, monkeypatch):
    registry, ticket, _, _row = synthetic()
    record = registry._records[ticket]
    original_init = module.BrokerReaderResources.__init__
    original_start = record.owner.start

    def init(self, *a, **k):
        assert record.managed and record.resources is self and record.resources_snapshot is self
        original_init(self, *a, **k)

    def start():
        assert record.resources_ready and record.start_attempted and registry._counts().active == 1
        original_start()

    monkeypatch.setattr(module.BrokerReaderResources, "__init__", init)
    monkeypatch.setattr(record.owner, "start", start)
    registry.start_resources(ticket)
    assert cleanup(registry, ticket)


def test_constructor_failure_retains_partial_managed_object_without_unmanaged_fallback(
    synthetic, monkeypatch
):
    registry, ticket, b, _ = synthetic()

    def fail(self, *a, **k):
        assert registry._records[ticket].resources is self
        raise RuntimeError("synthetic constructor failure")

    monkeypatch.setattr(module.BrokerReaderResources, "__init__", fail)
    with pytest.raises(FrameError):
        registry.start_resources(ticket)
    record = registry._records[ticket]
    assert record.resources is not None and record.unknown and record.managed
    assert not record.owner._launch_attempted and registry.status(b) is RegistryStatus.PENDING
    with pytest.raises(FrameError):
        registry.start(ticket)


def test_cleanup_end_cannot_be_renewed_or_rebound(synthetic):
    registry, ticket, _, _ = synthetic()
    registry.start_resources(ticket)
    registry.abort_resources(ticket)
    resources = registry._records[ticket].resources
    end = resources._cleanup_end_ns
    registry.abort_resources(ticket)
    assert resources._cleanup_end_ns == end
    assert cleanup(registry, ticket)
    resources._cleanup_end_ns = end + 1
    with pytest.raises(FrameError):
        registry.resource_local_observation(ticket)


def test_take_candidate_swallowed_reentry_during_close_validation_never_returns_bytes(
    synthetic, monkeypatch
):
    registry, ticket, _, row = synthetic()
    resources = complete(registry, ticket, row)
    original = resources._control.validates_close

    def reenter(*a):
        result = original(*a)
        with pytest.raises(FrameError):
            resources.abort()
        return result

    monkeypatch.setattr(resources._control, "validates_close", reenter)
    with pytest.raises(FrameError):
        registry.take_resource_candidate(ticket)
    assert resources._invalidated and not resources._candidate


def test_normal_result_poll_after_abort_is_not_normal_completion(synthetic):
    registry, ticket, _, row = synthetic()
    complete(registry, ticket, row)
    registry.abort_resources(ticket)
    with pytest.raises(FrameError):
        registry.poll_resource_result(ticket)
    assert registry.resource_local_observation(ticket)  # physical local fact is distinct


def test_cleanup_wait_expiry_prevents_late_signal_and_close(synthetic, monkeypatch):
    registry, ticket, _, _ = synthetic()
    registry.start_resources(ticket)
    registry.abort_resources(ticket)
    resources = registry._records[ticket].resources
    end = resources._cleanup_end_ns
    now = [end - 100_000_000]

    def delayed():
        now[0] = end
        return False

    monkeypatch.setattr(module.time, "monotonic_ns", lambda: now[0])
    monkeypatch.setattr(resources._process, "poll_wait", delayed)
    monkeypatch.setattr(resources._process, "terminate_once", lambda: pytest.fail("late signal"))
    monkeypatch.setattr(resources._control, "close_for_drain", lambda: pytest.fail("late close"))
    assert not registry.poll_resource_cleanup(ticket)
    assert resources._cleanup_end_ns == end


def test_cleanup_close_expiry_prevents_another_wait(synthetic, monkeypatch):
    registry, ticket, _, _ = synthetic()
    registry.start_resources(ticket)
    registry.abort_resources(ticket)
    resources = registry._records[ticket].resources
    end = resources._cleanup_end_ns
    now = [end - 100_000_000]
    calls = []
    poll = resources._process.poll_wait
    close = resources._control.close_for_drain

    def first_wait():
        calls.append(1)
        assert len(calls) == 1
        return poll()

    def delayed_close():
        close()
        now[0] = end

    monkeypatch.setattr(module.time, "monotonic_ns", lambda: now[0])
    monkeypatch.setattr(resources._process, "poll_wait", first_wait)
    monkeypatch.setattr(resources._control, "close_for_drain", delayed_close)
    assert not registry.poll_resource_cleanup(ticket)
    assert len(calls) == 1


def test_buffer_retarget_never_wipes_or_returns_other_operation_candidate(synthetic):
    a, ta, _, ra = synthetic()
    first = complete(a, ta, ra)
    b, tb, _, rb = synthetic()
    second = complete(b, tb, rb)
    before = bytes(second._candidate)
    first._candidate = second._candidate
    with pytest.raises(FrameError):
        a.take_resource_candidate(ta)
    assert bytes(second._candidate) == before
    assert b.take_resource_candidate(tb) == before


@pytest.mark.parametrize(
    "field,value", [("scope", ("foreign",)), ("exit_code", False), ("exit_code", 999)]
)
def test_local_observation_drift_is_sticky_and_wipes_owned_candidate(synthetic, field, value):
    registry, ticket, _, row = synthetic()
    resources = complete(registry, ticket, row)
    observed = registry.resource_local_observation(ticket)
    object.__setattr__(observed, field, value)
    with pytest.raises(FrameError):
        registry.take_resource_candidate(ticket)
    assert resources._poisoned and not resources._candidate_snapshot


def test_partial_control_owner_retained_after_actual_acquisition_failure(synthetic, monkeypatch):
    from hmp_plugin import presentation_control_pipe as control_module

    registry, ticket, b, _ = synthetic()

    def fail(**k):
        raise OSError("synthetic GO control acquisition")

    monkeypatch.setattr(control_module, "GoHandoff", fail)
    with pytest.raises(FrameError):
        registry.start_resources(ticket)
    resources = registry._records[ticket].resources
    assert resources._control is resources._control_snapshot
    assert resources._control.resource_uncertain and not resources._control._acquired
    assert not cleanup(registry, ticket)
    assert registry._records[ticket].owner._wait is not None
    assert registry.status(b) is RegistryStatus.PENDING


def test_partial_pipe_owner_retained_after_actual_selector_registration_failure(
    synthetic, monkeypatch
):
    from hmp_plugin import presentation_pipes as pipes_module

    registry, ticket, b, _ = synthetic()
    factory = pipes_module.selectors.DefaultSelector

    def make_selector():
        selector = factory()

        def fail(*a, **k):
            raise OSError("synthetic register failure")

        selector.register = fail
        return selector

    monkeypatch.setattr(pipes_module.selectors, "DefaultSelector", make_selector)
    with pytest.raises(FrameError):
        registry.start_resources(ticket)
    resources = registry._records[ticket].resources
    assert resources._pipes is resources._pipes_snapshot and resources._pipes.uncertain
    assert resources._control is None
    assert not cleanup(registry, ticket)
    assert registry._records[ticket].owner._wait is not None
    assert registry.status(b) is RegistryStatus.PENDING


def test_decode_refusal_keeps_only_local_drain_and_cannot_report_normal_success(
    synthetic, monkeypatch
):
    registry, ticket, b, row = synthetic()
    registry.start_resources(ticket)
    registry.stage_resource_input(ticket, encode_input_v3(row))
    registry.relay_resource_go(ticket)

    def refuse(*a):
        raise FrameError("synthetic result refusal")

    monkeypatch.setattr(module, "decode_output_v2", refuse)
    with pytest.raises(FrameError):
        while not registry.poll_resource_result(ticket):
            time.sleep(0.001)
    resources = registry._records[ticket].resources
    assert not resources._normal_complete and not resources._candidate
    assert registry.resource_local_observation(ticket)
    assert registry.status(b) is RegistryStatus.PENDING


def test_go_written_then_reentry_cannot_publish_candidate(synthetic, monkeypatch):
    from hmp_plugin import presentation_control_pipe as control_module

    registry, ticket, b, row = synthetic()
    registry.start_resources(ticket)
    registry.stage_resource_input(ticket, encode_input_v3(row))
    resources = registry._records[ticket].resources
    actual = control_module.os.write
    fd = resources._control._identity[0]

    def write(target, body):
        result = actual(target, body)
        if target == fd and len(body) == 65:
            with pytest.raises(FrameError):
                resources.abort()
        return result

    monkeypatch.setattr(control_module.os, "write", write)
    with pytest.raises(FrameError):
        registry.relay_resource_go(ticket)
    assert resources._invalidated and not resources._candidate
    assert cleanup(registry, ticket)
    assert registry.status(b) is RegistryStatus.PENDING


def test_candidate_copy_crossing_original_deadline_never_returns_bytes(synthetic, monkeypatch):
    import builtins

    registry, ticket, _, row = synthetic()
    resources = complete(registry, ticket, row)

    def delayed(value):
        result = builtins.bytes(value)
        monkeypatch.setattr(module.time, "monotonic_ns", lambda: row["deadline_ns"])
        return result

    monkeypatch.setattr(module, "bytes", delayed, raising=False)
    with pytest.raises(FrameError):
        registry.take_resource_candidate(ticket)
    assert resources._result_taken and not resources._candidate


def test_resource_cannot_rebind_a_different_original_child_deadline(synthetic):
    registry, ticket, b, row = synthetic()
    record = registry._records[ticket]
    with pytest.raises(FrameError):
        module.BrokerReaderResources(
            record,
            record.owner,
            binding=b,
            profile="default",
            kind="METADATA",
            deadline_ns=row["deadline_ns"] + 1,
            cleanup_budget=record.cleanup_budget,
        )
    assert not record.owner._launch_attempted


def test_registry_and_resources_share_original_budget_and_shortening(synthetic):
    registry, ticket, _, row = synthetic()
    record = registry._records[ticket]
    budget = record.cleanup_budget
    assert budget is record.cleanup_budget_snapshot
    assert CancellationBudget.inspect(budget) == (row["deadline_ns"], None, None, False)
    registry.start_resources(ticket)
    resources = record.resources
    assert resources._cleanup_budget is resources._cleanup_budget_snapshot is budget
    first = CancellationBudget.local(budget, time.monotonic_ns())
    registry.abort_resources(ticket)
    assert resources._cleanup_end_ns == first.end_ns
    earlier = CancellationWindow(first.start_ns - 1_000_000, first.end_ns - 1_000_000)
    CancellationBudget.inherit(budget, earlier, time.monotonic_ns())
    registry.abort_resources(ticket)
    assert resources._cleanup_end_ns == earlier.end_ns
    assert cleanup(registry, ticket)
    assert resources._cleanup_end_ns == earlier.end_ns


def test_original_cleanup_before_resource_start_prevents_launch(synthetic):
    registry, ticket, _, _ = synthetic()
    record = registry._records[ticket]
    CancellationBudget.local(record.cleanup_budget, time.monotonic_ns())
    with pytest.raises(FrameError):
        registry.start_resources(ticket)
    assert not record.owner._launch_attempted


def test_different_budget_cannot_attach_even_with_identical_deadline(synthetic):
    registry, ticket, b, row = synthetic()
    record = registry._records[ticket]
    with pytest.raises(FrameError):
        module.BrokerReaderResources(record, record.owner, binding=b, profile="default",
            kind="METADATA", deadline_ns=row["deadline_ns"],
            cleanup_budget=CancellationBudget(row["deadline_ns"]))
    assert not record.owner._launch_attempted


def test_late_abort_is_capped_by_original_end_not_a_fresh_interval(synthetic, monkeypatch):
    registry, ticket, _, row = synthetic()
    registry.start_resources(ticket)
    resources = registry._records[ticket].resources
    monkeypatch.setattr(module.time, "monotonic_ns", lambda: row["deadline_ns"] + 1_000_000_000)
    registry.abort_resources(ticket)
    assert resources._cleanup_end_ns == row["deadline_ns"] + CLEANUP_NS
    monkeypatch.setattr(resources._process, "terminate_once", lambda: pytest.fail("late signal"))
    assert not registry.poll_resource_cleanup(ticket)


@pytest.mark.parametrize("action", ["duplicate_input", "duplicate_go", "go_before_input"])
def test_invalid_one_use_work_transitions_never_enable_another_go(synthetic, action):
    registry, ticket, b, row = synthetic()
    registry.start_resources(ticket)
    if action != "go_before_input":
        registry.stage_resource_input(ticket, encode_input_v3(row))
    if action == "duplicate_go":
        registry.relay_resource_go(ticket)
    with pytest.raises(FrameError):
        if action == "duplicate_input":
            registry.stage_resource_input(ticket, encode_input_v3(row))
        else:
            registry.relay_resource_go(ticket)
    resources = registry._records[ticket].resources
    assert resources._invalidated and not resources._candidate
    assert cleanup(registry, ticket)
    assert registry.status(b) is RegistryStatus.PENDING


def large_image():
    raw = image()
    body = b"synthetic\x00" + b"x" * 300_000
    extra = (
        struct.pack(">I", len(body))
        + b"tEXt"
        + body
        + struct.pack(">I", zlib.crc32(b"tEXt" + body))
    )
    return raw[:33] + extra + raw[33:]


def test_large_actual_avatar_buffer_moves_once_and_temporary_decode_is_not_retained(synthetic):
    data = large_image()
    registry, ticket, _, row = synthetic("AVATAR", asset=data)
    resources = complete(registry, ticket, row)
    assert resources._pipes.output == b"" and len(resources._candidate) > len(data)
    wire = registry.take_resource_candidate(ticket)
    header, avatar = decode_output_v2(wire, row["challenge"], row["epoch"])
    assert avatar == data and header["avatar_sha"] == hashlib.sha256(data).hexdigest()
    assert not resources._candidate and resources._pipes.output == b""


def test_large_post_go_cancel_discards_locally_without_started_release(synthetic):
    import select

    registry, ticket, b, row = synthetic("AVATAR", asset=large_image())
    registry.start_resources(ticket)
    registry.stage_resource_input(ticket, encode_input_v3(row))
    registry.relay_resource_go(ticket)
    resources = registry._records[ticket].resources
    assert select.select([resources._streams.result], [], [], 1)[
        0
    ]  # actual output ready, not consumed
    assert cleanup(registry, ticket)
    assert resources._pipes.output == b"" and not resources._candidate
    assert registry.status(b) is RegistryStatus.PENDING


def test_cancel_one_managed_reader_leaves_another_reader_and_controller_working(synthetic):
    a, ta, _, _ = synthetic()
    a.start_resources(ta)
    b, tb, _, row = synthetic()
    b.start_resources(tb)
    assert cleanup(a, ta)
    b.stage_resource_input(tb, encode_input_v3(row))
    b.relay_resource_go(tb)
    while not b.poll_resource_result(tb):
        time.sleep(0.001)
    assert b.take_resource_candidate(tb)


def test_snapshot_retarget_never_wipes_other_operation_or_guesses_which_buffer_is_owned(synthetic):
    a, ta, _, ra = synthetic()
    first = complete(a, ta, ra)
    b, tb, _, rb = synthetic()
    second = complete(b, tb, rb)
    own_before = bytes(first._candidate)
    other_before = bytes(second._candidate)
    first._candidate_snapshot = second._candidate
    with pytest.raises(FrameError):
        a.take_resource_candidate(ta)
    assert bytes(first._candidate) == own_before and bytes(second._candidate) == other_before
    assert first._poisoned
    assert b.take_resource_candidate(tb) == other_before


@pytest.mark.parametrize("field", ["_candidate", "_candidate_snapshot"])
def test_candidate_copy_boundary_retarget_does_not_wipe_another_operation(
    synthetic, monkeypatch, field
):
    import builtins

    a, ta, _, ra = synthetic()
    first = complete(a, ta, ra)
    b, tb, _, rb = synthetic()
    second = complete(b, tb, rb)
    held = first._candidate
    before = builtins.bytes(second._candidate)

    def copy(value):
        result = builtins.bytes(value)
        if value is held:
            setattr(first, field, second._candidate)
        return result

    monkeypatch.setattr(module, "bytes", copy, raising=False)
    with pytest.raises(FrameError):
        a.take_resource_candidate(ta)
    assert not held and builtins.bytes(second._candidate) == before
    assert b.take_resource_candidate(tb) == before


def test_valid_other_profile_input_is_rejected_before_control_transfer(synthetic, monkeypatch):
    registry, ticket, _, row = synthetic()
    registry.start_resources(ticket)
    _, _, _, other = synthetic(profile="other")
    other["deadline_ns"] = row["deadline_ns"]  # isolate profile mismatch, not a deadline mismatch
    packet = encode_input_v3(
        other
    )  # fully valid closed codec including actual other-home policy/counts
    writes = []
    monkeypatch.setattr(
        registry._records[ticket].resources._control,
        "write_input",
        lambda data: writes.append(data),
    )
    with pytest.raises(FrameError):
        registry.stage_resource_input(ticket, packet)
    assert writes == []
    assert cleanup(registry, ticket)

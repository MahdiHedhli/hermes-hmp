"""Real temporary POSIX files, unit-issued claims; no host auth/HTTP/UI proof.

Image bytes here deliberately exercise raw source custody, not raster admission.
"""

import os

import pytest

from hmp_plugin.presentation_budget import PresentationWorkLedger
from hmp_plugin.presentation_memory import OPERATION_PAYLOAD_LIMIT, PresentationMemoryBudget
from hmp_plugin.presentation_native_claim import NativeReadRegistry, NativeSourceError
from hmp_plugin.presentation_native_files import NativePresentationFileReader, PosixPresentationOps


class RecordingOps(PosixPresentationOps):
    def __init__(self):
        super().__init__()
        self.opened, self.closed, self.reads = [], [], []
        self.live = set()
        self.after_read = None
        actual_open, actual_close, actual_read = self.open, self.close, self.read

        def opening(name, flags, *, dir_fd):
            fd = actual_open(name, flags, dir_fd=dir_fd)
            self.opened.append((fd, name))
            assert fd not in self.live
            self.live.add(fd)
            return fd

        def closing(fd):
            self.closed.append(fd)
            self.live.remove(fd)
            return actual_close(fd)

        def reading(fd, count):
            self.reads.append((fd, count))
            data = actual_read(fd, count)
            if self.after_read is not None:
                self.after_read(fd, data)
            return data

        self.open, self.close, self.read = opening, closing, reading


@pytest.fixture
def source(tmp_path):
    # resolve() only on the test fixture path (macOS /var -> /private/var).
    home = tmp_path.resolve() / "profile"
    home.mkdir(mode=0o700)
    metadata = home / "profile.yaml"
    metadata.write_bytes(b"display_name: Unit fixture\n")
    metadata.chmod(0o600)
    assets = home / "assets"
    assets.mkdir(mode=0o700)
    avatar = assets / "avatar.png"
    avatar.write_bytes(b"RAW_UNIT_RASTER_NOT_QUALIFIED")
    avatar.chmod(0o600)
    # macOS temporary directories may inherit wheel rather than effective group.
    # Match the explicit claim ownership policy without weakening the reader.
    for path in (home, metadata, assets, avatar):
        os.chown(path, os.geteuid(), os.getegid())
    return home, metadata, assets, avatar


def setup_read(home, ops=None):
    now = [1.0]
    issuer, operation = object(), object()

    def clock():
        return now[0]

    registry = NativeReadRegistry(issuer, object(), clock)
    registry._begin(issuer, operation, "belac", 3.0)
    claim = registry._issue(
        issuer, operation, home=str(home), uid=os.geteuid(), gid=os.getegid(), authority=object()
    )
    work = PresentationWorkLedger(clock=clock, deadline=3.0)
    memory = PresentationMemoryBudget()
    ops = RecordingOps() if ops is None else ops
    return (
        NativePresentationFileReader(registry, ops),
        claim,
        work,
        memory,
        ops,
        now,
        issuer,
        operation,
    )


def test_actual_fixed_reads_double_observation_and_explicit_buffer_release(source):
    home, metadata, _, avatar = source
    reader, claim, work, memory, ops, *_ = setup_read(home)
    result = reader.read(claim, work, memory)
    assert result.metadata == metadata.read_bytes()
    assert result.avatar == avatar.read_bytes()
    assert result.avatar_name == "avatar.png"
    assert memory.snapshot()[:2] == (len(result.metadata) + len(result.avatar), 2)
    assert work.snapshot()["read_bytes"] == 2 * (
        metadata.stat().st_size + avatar.stat().st_size + 2
    )
    assert not ops.live and len(ops.closed) == len(ops.opened)
    assert {name for _, name in ops.opened} >= {"profile.yaml", "avatar.png", "assets"}
    result.discard()
    assert result.metadata is None and result.avatar is None
    assert memory.snapshot()[:2] == (0, 0)
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)


def test_true_absence_is_distinct_from_unsafe_source(source):
    home, metadata, assets, avatar = source
    avatar.unlink()
    assets.rmdir()
    metadata.unlink()
    reader, claim, work, memory, ops, *_ = setup_read(home)
    result = reader.read(claim, work, memory)
    assert result.metadata is result.avatar is result.avatar_name is None
    assert memory.snapshot()[:2] == (0, 0) and not ops.live
    result.discard()


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "fifo", "mode", "ambiguous", "empty"])
def test_unsafe_avatar_is_refused_before_payload_read(source, unsafe):
    home, _, assets, avatar = source
    if unsafe == "symlink":
        avatar.unlink()
        avatar.symlink_to(home / "profile.yaml")
    elif unsafe == "hardlink":
        os.link(avatar, assets / "alias")
    elif unsafe == "fifo":
        avatar.unlink()
        os.mkfifo(avatar, 0o600)
    elif unsafe == "mode":
        avatar.chmod(0o666)
    elif unsafe == "ambiguous":
        (assets / "avatar.jpg").write_bytes(b"another")
    else:
        avatar.write_bytes(b"")
    reader, claim, work, memory, ops, *_ = setup_read(home)
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.reads and not ops.live
    assert memory.snapshot()[:2] == (0, 0)


@pytest.mark.parametrize("mutation", ["overwrite", "replace", "new_avatar", "retire", "expire"])
def test_source_or_authority_change_during_read_cannot_return_result(source, mutation):
    home, metadata, assets, _ = source
    reader, claim, work, memory, ops, now, issuer, operation = setup_read(home)

    def mutate(fd, data):
        if not data:
            return
        ops.after_read = None
        if mutation == "overwrite":
            metadata.write_bytes(b"display_name: Mutated text\n")
        elif mutation == "replace":
            new = home / "unit-new.yaml"
            new.write_bytes(metadata.read_bytes())
            new.chmod(0o600)
            new.replace(metadata)
        elif mutation == "new_avatar":
            (assets / "avatar.jpg").write_bytes(b"new")
        elif mutation == "retire":
            claim._owner._retire(issuer, operation)
        else:
            now[0] = 3.0

    ops.after_read = mutate
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.live and memory.snapshot()[:2] == (0, 0)


def test_unknown_close_is_not_retried_and_retains_registry_debt(source):
    home, *_ = source
    reader, claim, work, memory, ops, _, issuer, operation = setup_read(home)
    actual_close = ops.close
    failed = []

    def ambiguous_close(fd):
        actual_close(fd)  # simulate close succeeded but acknowledgement was lost
        if not failed:
            failed.append(fd)
            raise OSError("unit ambiguous acknowledgement")

    ops.close = ambiguous_close
    with pytest.raises(NativeSourceError, match="native_source_close_unknown"):
        reader.read(claim, work, memory)
    assert not ops.live and memory.snapshot()[:2] == (0, 0)
    assert len(ops.reads) == 2  # metadata payload and EOF; no avatar/repeated read
    assert ops.closed.count(failed[0]) == 1
    claim._owner._retire(issuer, operation)
    with pytest.raises(NativeSourceError):
        claim._owner._forget_closed(issuer, operation)


def test_exhausted_work_is_not_reset_by_reader(source):
    home, *_ = source
    reader, claim, work, memory, ops, *_ = setup_read(home)
    work.charge_read_bytes(4_131_076)
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.reads and not ops.live and memory.snapshot()[:2] == (0, 0)


def test_exhausted_buffer_budget_still_closes_all_descriptors(source):
    home, *_ = source
    reader, claim, work, memory, ops, *_ = setup_read(home)
    held = memory.reserve("result", OPERATION_PAYLOAD_LIMIT)
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.reads and not ops.live
    assert memory.snapshot()[:2] == (OPERATION_PAYLOAD_LIMIT, 1)
    memory.release(held)


def test_maximum_fixed_source_fits_original_work_and_buffer_envelopes(source):
    home, metadata, _, avatar = source
    metadata.write_bytes(b"x" * 65_536)
    avatar.write_bytes(b"y" * 2_000_000)
    reader, claim, work, memory, ops, *_ = setup_read(home)
    result = reader.read(claim, work, memory)
    assert len(result.metadata) == 65_536 and len(result.avatar) == 2_000_000
    assert work.snapshot()["read_bytes"] == 4_131_076
    assert memory.snapshot()[0] == 2_065_536
    assert memory.snapshot()[2] <= OPERATION_PAYLOAD_LIMIT
    assert not ops.live
    result.discard()
    assert memory.snapshot()[:2] == (0, 0)


def test_unreadable_metadata_is_not_reported_as_absence(source):
    home, *_ = source
    reader, claim, work, memory, ops, *_ = setup_read(home)
    actual_stat = ops.stat

    def denied(name, **kwargs):
        if name == "profile.yaml":
            raise PermissionError("unit access refused")
        return actual_stat(name, **kwargs)

    ops.stat = denied
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.reads and not ops.live and memory.snapshot()[:2] == (0, 0)


def test_assets_directory_link_cannot_reach_other_profile(source):
    home, _, assets, avatar = source
    avatar.unlink()
    assets.rmdir()
    other = home.parent / "other"
    other.mkdir(mode=0o700)
    (other / "avatar.png").write_bytes(b"OTHER_PROFILE_MUST_NOT_READ")
    assets.symlink_to(other, target_is_directory=True)
    reader, claim, work, memory, ops, *_ = setup_read(home)
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.reads and not ops.live and memory.snapshot()[:2] == (0, 0)


def test_short_read_failure_releases_buffers_and_settles_known_handles(source):
    home, *_ = source
    reader, claim, work, memory, ops, *_ = setup_read(home)
    ops.read = lambda fd, count: b""
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.live and memory.snapshot()[:2] == (0, 0)
    assert not claim._in_progress and not claim._unknown


def test_foreign_clock_cannot_reset_original_deadline(source):
    home, *_ = source
    reader, claim, _, memory, ops, *_ = setup_read(home)
    work = PresentationWorkLedger(clock=lambda: 1.0, deadline=3.0)
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.opened and not ops.reads and memory.snapshot()[:2] == (0, 0)


def test_reader_rejects_foreign_owner_without_running_object_hooks(source):
    home, *_ = source
    reader, claim, work, memory, ops, *_ = setup_read(home)

    class Foreign:
        def __getattribute__(self, name):
            raise AssertionError("foreign registry inspected")

    claim._owner = Foreign()
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert not ops.opened and not ops.reads and memory.snapshot()[:2] == (0, 0)


def test_reader_cannot_adopt_valid_claim_from_another_registry(source):
    home, *_ = source
    reader, _, _, memory, ops, *_ = setup_read(home)
    _, foreign, work, _, _, *_ = setup_read(home)
    with pytest.raises(NativeSourceError):
        reader.read(foreign, work, memory)
    assert not ops.opened and not ops.reads and memory.snapshot()[:2] == (0, 0)


def test_growth_byte_has_buffer_credit_before_eof_probe_and_is_discarded(source):
    home, metadata, *_ = source
    reader, claim, work, memory, ops, *_ = setup_read(home)
    actual_read = ops.read
    observed = []

    def growing(fd, count):
        if count == 1 and not observed:
            # The EOF probe must already own its independent one-byte credit.
            assert any(size == 1 and kind == "file" for _, size, kind in memory._live.values())
            with metadata.open("ab") as stream:
                stream.write(b"x")
            data = actual_read(fd, count)
            assert data == b"x"
            observed.append(memory.snapshot()[:2])
            return data
        return actual_read(fd, count)

    ops.read = growing
    with pytest.raises(NativeSourceError):
        reader.read(claim, work, memory)
    assert len(observed) == 1 and observed[0][0] == len(b"display_name: Unit fixture\n") + 1
    assert not ops.live and memory.snapshot()[:2] == (0, 0)

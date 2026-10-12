"""Whole fixed-reader transaction on synthetic files and real kernel descriptors.

The optional test parent controls fixture placement only. No live Hermes directory
is opened; unsafe ancestor policy causes a skip rather than relaxing the reader.
"""

import os
import stat
import tempfile
import time
from pathlib import Path

import pytest

from hmp_plugin.presentation_files import (
    DirectoryRule,
    PresentationReadError,
    bind_owned_worker_read,
    read_fixed_presentation_files,
)
from hmp_plugin.presentation_posix import PosixFileOps
from hmp_plugin.presentation_yaml import PresentationYamlError
from hmp_plugin.presentation_yaml_adapter import parse_presentation_yaml


@pytest.fixture
def scope():
    parent = Path(os.environ.get("HMP_PRESENTATION_TEST_PARENT", str(Path.cwd()))).resolve()
    # Refuse before fixture creation if a real ancestor violates the frozen policy.
    for p in (parent, *parent.parents):
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode not in (0o700, 0o750, 0o755):
            pytest.skip("synthetic fixture requires secure ancestor modes")
    with tempfile.TemporaryDirectory(prefix="hmp-bi1-synthetic-", dir=parent) as raw:
        home = Path(raw)
        (home / "profile.yaml").write_bytes(
            b"display_name: Synthetic\n"
            b"ui_meta: {hermes-bots: {shape: hexagon, color: '#8b5cf6', custom: true}}\n"
        )
        (home / "profile.yaml").chmod(0o600)
        parts = [home, *home.parents][::-1]
        rules = tuple(
            DirectoryRule(
                str(p), p.stat().st_uid, p.stat().st_gid, (stat.S_IMODE(p.stat().st_mode),)
            )
            for p in parts
        )
        bound = bind_owned_worker_read(
            root_path=str(home),
            home_path=str(home),
            profile=None,
            service_uid=os.getuid(),
            service_gid=os.getgid(),
            directory_rules=rules,
            deadline=time.monotonic() + 2.0,
            challenge="a" * 64,
            source_manifest_sha256="b" * 64,
            worker_go_challenge="a" * 64,
        )
        yield home, bound


class TrackedOS(PosixFileOps):
    def __init__(self):
        self.opened = set()
        self.open_attempts = 0

    def open(self, *args, **kwargs):
        self.open_attempts += 1
        fd = super().open(*args, **kwargs)
        self.opened.add(fd)
        return fd

    def close(self, fd):
        super().close(fd)
        self.opened.remove(fd)


def test_actual_transaction_then_closed_yaml_projection(scope):
    _, bound = scope
    fs = TrackedOS()
    result = read_fixed_presentation_files(bound, fs=fs, clock=time.monotonic)
    fields = parse_presentation_yaml(result.metadata, clock=time.monotonic, deadline=bound.deadline)
    assert fields.display_name == "Synthetic"
    assert fields.shape == "hexagon" and fields.custom is True
    assert result.avatar is None
    assert fs.opened == set()
    assert result.budget["readBytesCharged"] <= 4_131_076


def test_actual_symlink_metadata_refused_with_all_owned_fds_closed(scope):
    home, bound = scope
    (home / "other").write_bytes(b"display_name: Never read\n")
    (home / "profile.yaml").unlink()
    (home / "profile.yaml").symlink_to("other")
    fs = TrackedOS()
    with pytest.raises(PresentationReadError):
        read_fixed_presentation_files(bound, fs=fs, clock=time.monotonic)
    assert fs.opened == set()


def test_actual_metadata_replacement_during_read_is_refused(scope):
    home, bound = scope

    class ReplacingOS(TrackedOS):
        replaced = False

        def read(self, fd, size):
            body = super().read(fd, size)
            if not self.replaced:
                self.replaced = True
                replacement = home / "replacement"
                replacement.write_bytes(b"display_name: Changed\n")
                replacement.chmod(0o600)
                os.replace(replacement, home / "profile.yaml")
            return body

    fs = ReplacingOS()
    with pytest.raises(PresentationReadError):
        read_fixed_presentation_files(bound, fs=fs, clock=time.monotonic)
    assert fs.replaced and fs.opened == set()


class RasterLedger:
    def __init__(self):
        self.scans = 0
        self.hash_bytes = 0
        self.units = 0

    def charge_scan(self):
        assert self.scans == 0
        self.scans += 1

    def charge_hash_bytes(self, count):
        self.hash_bytes += count
        assert self.hash_bytes <= 2_000_000

    def charge_unit(self):
        self.units += 1
        assert self.units <= 10_000


def process(result, bound, expected=None):
    from hmp_plugin.presentation_pipeline import reduce_fixed_result
    from hmp_plugin.presentation_raster import RasterBudget

    ledger = RasterLedger()
    processed = reduce_fixed_result(
        result,
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
        deadline=bound.deadline,
        raster_budget=RasterBudget(deadline=bound.deadline, clock=time.monotonic, ledger=ledger),
        expected_avatar_revision=expected,
    )
    return processed, ledger


def test_actual_metadata_pipeline_returns_closed_scoped_character(scope):
    _, bound = scope
    result = read_fixed_presentation_files(bound, fs=PosixFileOps(), clock=time.monotonic)
    output, ledger = process(result, bound)
    assert output.metadata["iid"] == "a" * 52 and output.metadata["profile"] == "default"
    assert output.metadata["character"] == {
        "version": 1,
        "shape": "hexagon",
        "color": "#8b5cf6",
        "custom": None,
    }
    assert output.metadata["display_name"] == "Synthetic"
    assert output.avatar_bytes is None and ledger.scans == 0
    assert "profile.yaml" not in repr(output)


def test_actual_avatar_pipeline_binds_binary_to_content_revision(scope):
    import hashlib
    import struct
    import zlib

    home, bound = scope

    def chunk(kind, body):
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        )

    image = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x8b\x5c\xf6\xff"))
        + chunk(b"IEND", b"")
    )
    (home / "assets").mkdir(mode=0o700)
    (home / "assets" / "avatar.png").write_bytes(image)
    (home / "assets" / "avatar.png").chmod(0o600)
    result = read_fixed_presentation_files(bound, fs=PosixFileOps(), clock=time.monotonic)
    output, ledger = process(result, bound, hashlib.sha256(image).hexdigest())
    assert output.avatar_bytes == image
    assert output.metadata["avatar"] == {
        "revision": hashlib.sha256(image).hexdigest(),
        "mime": "image/png",
        "bytes": len(image),
        "width": 1,
        "height": 1,
    }
    assert ledger.scans == 1 and ledger.hash_bytes == len(image)
    with pytest.raises(PresentationYamlError, match="AVATAR_CHANGED"):
        process(result, bound, "0" * 64)


def test_cleared_avatar_cannot_satisfy_previous_revision(scope):
    from hmp_plugin.presentation_yaml import PresentationYamlError

    _, bound = scope
    result = read_fixed_presentation_files(bound, fs=PosixFileOps(), clock=time.monotonic)
    with pytest.raises(PresentationYamlError, match="AVATAR_CHANGED"):
        process(result, bound, "0" * 64)


def test_pipeline_rejects_raster_budget_with_extended_deadline(scope):
    from hmp_plugin.presentation_pipeline import reduce_fixed_result
    from hmp_plugin.presentation_raster import RasterBudget

    _, bound = scope
    result = read_fixed_presentation_files(bound, fs=PosixFileOps(), clock=time.monotonic)
    with pytest.raises(PresentationYamlError, match="BUDGET_SCOPE"):
        reduce_fixed_result(
            result,
            iid="a" * 52,
            profile="default",
            canonical_fallback="Hermes",
            observed_at=100,
            clock=time.monotonic,
            deadline=bound.deadline,
            raster_budget=RasterBudget(
                deadline=bound.deadline + 10.0, clock=time.monotonic, ledger=RasterLedger()
            ),
        )


def test_pipeline_rechecks_deadline_after_metadata_projection(scope):
    from hmp_plugin.presentation_pipeline import reduce_fixed_result
    from hmp_plugin.presentation_raster import RasterBudget

    home, bound = scope
    (home / "profile.yaml").unlink()
    result = read_fixed_presentation_files(bound, fs=PosixFileOps(), clock=time.monotonic)
    ticks = iter([1.0, 2.0])

    def clock():
        return next(ticks)

    with pytest.raises(PresentationYamlError, match="DEADLINE"):
        reduce_fixed_result(
            result,
            iid="a" * 52,
            profile="default",
            canonical_fallback="Hermes",
            observed_at=100,
            clock=clock,
            deadline=2.0,
            raster_budget=RasterBudget(deadline=2.0, clock=clock, ledger=RasterLedger()),
        )


def test_shared_ledger_is_charged_by_real_file_and_yaml_pipeline(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_pipeline import reduce_fixed_result
    from hmp_plugin.presentation_raster import RasterBudget

    _, bound = scope
    work = PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline)
    result = read_fixed_presentation_files(
        bound, fs=PosixFileOps(), clock=time.monotonic, ledger=work
    )
    before = work.snapshot()
    assert result.work_ledger is work
    assert before["read_bytes"] == result.budget["readBytesCharged"]
    assert before["opens"] == result.budget["opensCharged"]
    assert before["yaml_nodes"] == 0
    output = reduce_fixed_result(
        result,
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
        deadline=bound.deadline,
        raster_budget=RasterBudget(deadline=bound.deadline, clock=time.monotonic, ledger=work),
    )
    after = work.snapshot()
    assert after["read_bytes"] == before["read_bytes"]
    assert after["yaml_nodes"] > 0 and after["yaml_tokens"] > 0
    assert output.metadata["character"]["shape"] == "hexagon"


def test_shared_scope_rejects_replacement_processing_ledger(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_pipeline import reduce_fixed_result
    from hmp_plugin.presentation_raster import RasterBudget

    _, bound = scope
    work = PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline)
    result = read_fixed_presentation_files(
        bound, fs=PosixFileOps(), clock=time.monotonic, ledger=work
    )
    replacement = PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline)
    with pytest.raises(PresentationYamlError, match="WORK_SCOPE"):
        reduce_fixed_result(
            result,
            iid="a" * 52,
            profile="default",
            canonical_fallback="Hermes",
            observed_at=100,
            clock=time.monotonic,
            deadline=bound.deadline,
            raster_budget=RasterBudget(
                deadline=bound.deadline, clock=time.monotonic, ledger=replacement
            ),
        )
    assert replacement.snapshot()["yaml_nodes"] == 0


def test_one_ledger_covers_real_metadata_and_avatar_processing(scope):
    import struct
    import zlib

    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_pipeline import reduce_fixed_result
    from hmp_plugin.presentation_raster import RasterBudget

    home, bound = scope

    def chunk(kind, body):
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        )

    image = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x8b\x5c\xf6\xff"))
        + chunk(b"IEND", b"")
    )
    (home / "assets").mkdir(mode=0o700)
    (home / "assets" / "avatar.png").write_bytes(image)
    (home / "assets" / "avatar.png").chmod(0o600)
    work = PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline)
    result = read_fixed_presentation_files(
        bound, fs=PosixFileOps(), clock=time.monotonic, ledger=work
    )
    output = reduce_fixed_result(
        result,
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
        deadline=bound.deadline,
        raster_budget=RasterBudget(deadline=bound.deadline, clock=time.monotonic, ledger=work),
    )
    totals = work.snapshot()
    assert totals["read_bytes"] == result.budget["readBytesCharged"]
    assert totals["yaml_nodes"] > 0 and totals["raster_units"] > 0
    assert totals["hash_bytes"] == len(image)
    assert output.avatar_bytes == image


def test_worker_entry_owns_one_ledger_and_refuses_wrong_profile_before_io(scope):
    from hmp_plugin.presentation_pipeline import run_fixed_worker

    _, bound = scope
    fs = TrackedOS()
    with pytest.raises(PresentationYamlError, match="WORK_SCOPE"):
        run_fixed_worker(
            bound,
            fs=fs,
            iid="a" * 52,
            profile="other",
            canonical_fallback="Other",
            observed_at=100,
            clock=time.monotonic,
        )
    assert fs.opened == set() and fs.open_attempts == 0
    completed = run_fixed_worker(
        bound,
        fs=fs,
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
    )
    assert completed.result.metadata["profile"] == "default"
    assert completed.charges["read_bytes"] > 0 and completed.charges["yaml_nodes"] > 0
    assert fs.opened == set()


def test_actual_completed_worker_frame_excludes_paths_and_raw_profile(scope):
    from hmp_plugin.presentation_jobs import FrameError, decode_output
    from hmp_plugin.presentation_pipeline import encode_completed_worker, run_fixed_worker

    home, bound = scope
    with (home / "profile.yaml").open("ab") as out:
        out.write(b"private: synthetic-private-not-projected\n")
    completed = run_fixed_worker(
        bound,
        fs=PosixFileOps(),
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
    )
    framed = encode_completed_worker(completed, challenge="a" * 64, epoch=1)
    header, body = decode_output(framed, "a" * 64, 1)
    assert header["fields"]["display_name"] == "Synthetic"
    assert header["fields"]["shape"] == "hexagon"
    assert header["cleanup"] == {"known_fds_closed": True, "unknown_close": False}
    assert header["absence_bitmap"] == 14 and body == b""
    assert str(home).encode() not in framed
    assert b"synthetic-private-not-projected" not in framed
    with pytest.raises(FrameError):
        decode_output(framed, "b" * 64, 1)


def test_default_profile_blobatar_frame_reprojects_same_character(scope):
    from hmp_plugin.presentation import project_presentation
    from hmp_plugin.presentation_jobs import decode_output
    from hmp_plugin.presentation_pipeline import encode_completed_worker, run_fixed_worker

    home, bound = scope
    (home / "profile.yaml").write_bytes(
        b'ui_meta: {hermes-bots: {shape: "blobatar:abc:hexagon", custom: true}}\n'
    )
    completed = run_fixed_worker(
        bound,
        fs=PosixFileOps(),
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
    )
    header, _ = decode_output(
        encode_completed_worker(completed, challenge="a" * 64, epoch=1), "a" * 64, 1
    )
    fields = header["fields"]
    rebuilt = project_presentation(
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        bot_title=fields.get("title"),
        profile_display_name=fields.get("display_name"),
        shape=fields.get("shape"),
        color=fields.get("color"),
        custom=fields.get("custom"),
        avatar=None,
        observed_at=100,
    )
    assert rebuilt == completed.result.metadata


@pytest.mark.parametrize(
    "raw",
    [
        b"ui_meta: {hermes-bots: {custom: true}}\n",
        b"ui_meta: {hermes-bots: {shape: circle, color: invalid, custom: true}}\n",
    ],
)
def test_null_character_frame_preserves_fallback_and_metadata_revision(scope, raw):
    from hmp_plugin.presentation import project_presentation
    from hmp_plugin.presentation_jobs import decode_output
    from hmp_plugin.presentation_pipeline import encode_completed_worker, run_fixed_worker

    home, bound = scope
    (home / "profile.yaml").write_bytes(raw)
    completed = run_fixed_worker(
        bound,
        fs=PosixFileOps(),
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
    )
    assert completed.result.metadata["character"] is None
    header, _ = decode_output(
        encode_completed_worker(completed, challenge="a" * 64, epoch=1), "a" * 64, 1
    )
    fields = header["fields"]
    rebuilt = project_presentation(
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        bot_title=fields.get("title"),
        profile_display_name=fields.get("display_name"),
        shape=fields.get("shape"),
        color=fields.get("color"),
        custom=fields.get("custom"),
        avatar=None,
        observed_at=100,
    )
    assert rebuilt == completed.result.metadata


def test_complete_child_stream_requires_go_then_emits_only_bounded_projection(scope):
    import io
    from dataclasses import replace

    from hmp_plugin.presentation_jobs import FrameError, decode_output, encode_input
    from hmp_plugin.presentation_worker import process_child_stream

    _, bound = scope
    ns = int(bound.deadline * 1_000_000_000)
    row = {
        "schema": 1,
        "challenge": bound.challenge,
        "epoch": 1,
        "profile": "default",
        "root": bound.root_path,
        "home": bound.home_path,
        "operation": "METADATA",
        "expected_avatar_sha": None,
        "uid": bound.service_uid,
        "gid": bound.service_gid,
        "dir_modes": [448, 488, 493],
        "leaf_modes": [384, 416, 420],
        "source_manifest_sha": bound.source_manifest_sha256,
        "deadline_ns": ns,
    }
    calls = []

    def factory(value):
        calls.append(value)
        return replace(bound, deadline=ns / 1_000_000_000)

    fs = TrackedOS()
    sink = io.BytesIO()
    process_child_stream(
        io.BytesIO(encode_input(row) + bound.challenge.encode() + b"\n"),
        sink,
        scope_factory=factory,
        fs=fs,
        clock=time.monotonic,
        deadline=bound.deadline + 0.1,
        iid="a" * 52,
        canonical_fallback="Hermes",
        observed_at=100,
    )
    header, body = decode_output(sink.getvalue(), bound.challenge, 1)
    assert header["fields"]["display_name"] == "Synthetic" and body == b""
    assert len(calls) == 1 and fs.opened == set()
    attempts = fs.open_attempts
    with pytest.raises(FrameError):
        process_child_stream(
            io.BytesIO(encode_input(row) + b"0" * 64 + b"\n"),
            io.BytesIO(),
            scope_factory=factory,
            fs=fs,
            clock=time.monotonic,
            deadline=bound.deadline + 0.1,
            iid="a" * 52,
            canonical_fallback="Hermes",
            observed_at=100,
        )
    assert len(calls) == 1 and fs.open_attempts == attempts


def test_factory_cannot_substitute_original_deadline_hash_or_epoch(scope):
    import io
    from dataclasses import replace

    from hmp_plugin.presentation_jobs import FrameError, encode_input
    from hmp_plugin.presentation_worker import process_child_stream

    _, bound = scope
    ns = int(bound.deadline * 1_000_000_000)
    row = {
        "schema": 1,
        "challenge": bound.challenge,
        "epoch": 1,
        "profile": "default",
        "root": bound.root_path,
        "home": bound.home_path,
        "operation": "METADATA",
        "expected_avatar_sha": None,
        "uid": bound.service_uid,
        "gid": bound.service_gid,
        "dir_modes": [448, 488, 493],
        "leaf_modes": [384, 416, 420],
        "source_manifest_sha": bound.source_manifest_sha256,
        "deadline_ns": ns,
    }

    def substitute(value):
        value["deadline_ns"] += 2_000_000_000
        value["source_manifest_sha"] = "c" * 64
        value["epoch"] = 2
        return replace(
            bound,
            deadline=value["deadline_ns"] / 1_000_000_000,
            source_manifest_sha256=value["source_manifest_sha"],
        )

    fs = TrackedOS()
    sink = io.BytesIO()
    with pytest.raises(FrameError, match="BI1_CHILD_SCOPE_REFUSED"):
        process_child_stream(
            io.BytesIO(encode_input(row) + bound.challenge.encode() + b"\n"),
            sink,
            scope_factory=substitute,
            fs=fs,
            clock=time.monotonic,
            deadline=bound.deadline + 0.1,
            iid="a" * 52,
            canonical_fallback="Hermes",
            observed_at=100,
        )
    assert fs.open_attempts == 0 and sink.getvalue() == b""


def test_factory_private_copy_cannot_change_emitted_epoch(scope):
    import io
    from dataclasses import replace
    from hmp_plugin.presentation_jobs import decode_output, encode_input
    from hmp_plugin.presentation_worker import process_child_stream

    _, bound = scope
    ns = int(bound.deadline * 1_000_000_000)
    row = {
        "schema": 1,
        "challenge": bound.challenge,
        "epoch": 1,
        "profile": "default",
        "root": bound.root_path,
        "home": bound.home_path,
        "operation": "METADATA",
        "expected_avatar_sha": None,
        "uid": bound.service_uid,
        "gid": bound.service_gid,
        "dir_modes": [448, 488, 493],
        "leaf_modes": [384, 416, 420],
        "source_manifest_sha": bound.source_manifest_sha256,
        "deadline_ns": ns,
    }

    def mutate_copy(value):
        value["epoch"] = 2
        value["dir_modes"][0] = 0
        return replace(bound, deadline=ns / 1_000_000_000)

    sink = io.BytesIO()
    process_child_stream(
        io.BytesIO(encode_input(row) + bound.challenge.encode() + b"\n"),
        sink,
        scope_factory=mutate_copy,
        fs=PosixFileOps(),
        clock=time.monotonic,
        deadline=bound.deadline + 0.1,
        iid="a" * 52,
        canonical_fallback="Hermes",
        observed_at=100,
    )
    header, _ = decode_output(sink.getvalue(), bound.challenge, 1)
    assert header["epoch"] == 1 and row["dir_modes"] == [448, 488, 493]

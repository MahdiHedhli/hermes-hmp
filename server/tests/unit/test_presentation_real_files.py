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


def test_late_scope_factory_returns_without_opening_profile_files(scope):
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
    now = [time.monotonic()]

    def late(value):
        now[0] = ns / 1_000_000_000
        return replace(bound, deadline=ns / 1_000_000_000)

    fs = TrackedOS()
    sink = io.BytesIO()
    with pytest.raises(FrameError, match="BI1_CHILD_DEADLINE"):
        process_child_stream(
            io.BytesIO(encode_input(row) + bound.challenge.encode() + b"\n"),
            sink,
            scope_factory=late,
            fs=fs,
            clock=lambda: now[0],
            deadline=bound.deadline + 0.1,
            iid="a" * 52,
            canonical_fallback="Hermes",
            observed_at=100,
        )
    assert fs.open_attempts == 0 and sink.getvalue() == b""


def test_schema2_real_child_processing_preserves_projection_and_closes_files(scope):
    import io

    from hmp_plugin.presentation_input_v2 import encode_input_v2
    from hmp_plugin.presentation_jobs import decode_output
    from hmp_plugin.presentation_worker import process_child_stream_v2

    _, bound = scope
    row = {
        "schema": 2,
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
        "deadline_ns": int(bound.deadline * 1_000_000_000),
        "directory_policy": [[r.uid, r.gid, r.modes[0]] for r in bound.directory_rules],
        "iid": "a" * 52,
        "canonical_fallback": "Hermes",
        "observed_at": 100,
    }
    fs = TrackedOS()
    sink = io.BytesIO()
    process_child_stream_v2(
        io.BytesIO(encode_input_v2(row) + bound.challenge.encode() + b"\n"),
        sink,
        fs=fs,
        clock=time.monotonic,
        deadline=bound.deadline + 0.1,
        effective_uid=os.geteuid(),
        effective_gid=os.getegid(),
    )
    header, body = decode_output(sink.getvalue(), bound.challenge, 1)
    assert header["fields"]["display_name"] == "Synthetic"
    assert header["fields"]["shape"] == "hexagon"
    assert body == b"" and fs.opened == set()


@pytest.mark.parametrize("bounded_pipes", [False, True, "control", "retained"])
def test_fixed_isolated_child_script_processes_only_synthetic_profile(scope, bounded_pipes):
    import subprocess
    import sys

    from hmp_plugin.presentation_input_v3 import encode_input_v3
    from hmp_plugin.presentation_output_v2 import decode_output_v2

    _, bound = scope
    row = {
        "schema": 3,
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
        "deadline_ns": int(bound.deadline * 1_000_000_000),
        "directory_policy": [[r.uid, r.gid, r.modes[0]] for r in bound.directory_rules],
        "iid": "a" * 52,
        "canonical_fallback": "Hermes",
        "observed_at": 100,
        "parent_work_counts": {
            "read_bytes": 0,
            "hash_bytes": 0,
            "opens": len(bound.directory_rules),
            "metadata": 4 * len(bound.directory_rules),
            "path_bytes": 3 * (1 + sum(len(p.encode()) for p in bound.home_path[1:].split("/"))),
            "yaml_nodes": 0,
            "yaml_tokens": 0,
            "raster_units": 0,
        },
    }
    script = Path(__file__).parents[2] / "hmp_plugin" / "presentation_child.py"
    argv = [sys.executable, "-I", "-B", str(script)]
    payload = encode_input_v3(row) + bound.challenge.encode() + b"\n"
    if bounded_pipes:
        from hmp_plugin.presentation_pipes import OwnedPresentationPipes

        lifetime = None
        if bounded_pipes == "retained":
            from hmp_plugin.presentation_process import PresentationProcessOwner

            lifetime = PresentationProcessOwner()
            lifetime.start()
            child = lifetime.child
        else:
            child = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={"LANG": "C", "LC_ALL": "C"},
                close_fds=True,
                start_new_session=True,
            )
        try:
            owner = OwnedPresentationPipes(child.stdout, child.stderr)
            if bounded_pipes in ("control", "retained"):
                from hmp_plugin.presentation_control_pipe import OwnedControlPipe

                handle = object()
                control = OwnedControlPipe(
                    child.stdin, handle=handle, child=child, current=lambda: True
                )
                control.write_input(encode_input_v3(row))
                control.send_go(handle, child, bound.challenge)
                assert control.closed
            else:
                child.stdin.write(payload)
                child.stdin.close()
            while not owner.drained:
                owner.poll(deadline=bound.deadline)
            if lifetime is None:
                assert child.wait(timeout=1) == 0
            else:
                while not lifetime.poll_wait():
                    assert time.monotonic() < bound.deadline
                    time.sleep(0.005)
                assert lifetime.exit_code == 0 and lifetime.signals_retired
                assert lifetime.probe_group_absence()
            assert owner.diagnostic_bytes == 0
            assert child.stdout.closed and child.stderr.closed
            output = owner.output
        finally:
            # Cleanup only this synthetic test's exact Popen-owned process.
            if lifetime is not None and lifetime.reaped:
                pass
            elif lifetime is not None:
                # Preserve unknown lifetime debt rather than use another reaper.
                raise AssertionError("retained synthetic process did not settle")
            elif child.poll() is None:
                child.kill()
                child.wait(timeout=1)
            for stream in (child.stdin, child.stdout, child.stderr):
                if not stream.closed:
                    stream.close()
    else:
        result = subprocess.run(
            argv,
            input=payload,
            capture_output=True,
            timeout=3,
            check=False,
            env={"LANG": "C", "LC_ALL": "C"},
            close_fds=True,
            start_new_session=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stderr == b""
        output = result.stdout
    header, body = decode_output_v2(output, bound.challenge, 1)
    assert header["fields"]["display_name"] == "Synthetic"
    assert header["fields"]["shape"] == "hexagon" and body == b""


def test_input3_processing_carries_parent_credits_into_complete_result2(scope):
    import io

    from hmp_plugin.presentation_input_v3 import encode_input_v3
    from hmp_plugin.presentation_output_v2 import compare_parent_totals, decode_output_v2
    from hmp_plugin.presentation_pipeline import run_fixed_worker
    from hmp_plugin.presentation_worker import process_child_stream_v3

    _, bound = scope
    n = len(bound.directory_rules)
    s = 1 + sum(len(part.encode()) for part in bound.home_path[1:].split("/"))
    counts = {
        "read_bytes": 0,
        "hash_bytes": 0,
        "opens": n,
        "metadata": 4 * n,
        "path_bytes": 3 * s,
        "yaml_nodes": 0,
        "yaml_tokens": 0,
        "raster_units": 0,
    }
    row = {
        "schema": 3,
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
        "deadline_ns": int(bound.deadline * 1_000_000_000),
        "directory_policy": [[r.uid, r.gid, r.modes[0]] for r in bound.directory_rules],
        "iid": "a" * 52,
        "canonical_fallback": "Hermes",
        "observed_at": 100,
        "parent_work_counts": counts,
    }
    # The parent credits are synthetic declarations here, not native IO proof.
    baseline = run_fixed_worker(
        bound,
        fs=TrackedOS(),
        iid="a" * 52,
        profile="default",
        canonical_fallback="Hermes",
        observed_at=100,
        clock=time.monotonic,
    )
    output = io.BytesIO()
    process_child_stream_v3(
        io.BytesIO(encode_input_v3(row) + bound.challenge.encode() + b"\n"),
        output,
        fs=TrackedOS(),
        clock=time.monotonic,
        deadline=bound.deadline + 0.1,
        effective_uid=os.geteuid(),
        effective_gid=os.getegid(),
    )
    header, body = decode_output_v2(output.getvalue(), bound.challenge, 1)
    totals = compare_parent_totals(header, parent_home=bound.home_path, parent_counts=counts)
    assert header["fields"]["display_name"] == "Synthetic" and body == b""
    assert totals == {key: baseline.charges[key] + counts[key] for key in counts}
    assert totals["yaml_tokens"] > 0


def test_parent_policy_is_directory_only_and_charges_exact_success_schedule(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    _, bound = scope

    class DirectoryOnly(TrackedOS):
        def read(self, fd, size):
            raise AssertionError("parent must never read a body")

        def open(self, path, flags, **kwargs):
            assert flags & os.O_DIRECTORY and flags & os.O_NOFOLLOW
            assert path not in ("profile.yaml", "config.yaml", "assets")
            return super().open(path, flags, **kwargs)

    fs = DirectoryOnly()
    ledger = PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline)
    owner = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=ledger,
        fs=fs,
        current=lambda: True,
    )
    result = owner.run()
    n = len(bound.directory_rules)
    s = 1 + sum(len(p.encode()) for p in bound.home_path[1:].split("/"))
    assert result.rules == bound.directory_rules
    assert result.counts["opens"] == n
    assert result.counts["metadata"] == 4 * n
    assert result.counts["path_bytes"] == 3 * s
    assert result.counts["read_bytes"] == 0
    assert owner.descriptors_closed and fs.opened == set()
    assert len(result.chain) == n


def test_parent_current_refusal_has_zero_filesystem_effects(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    _, bound = scope
    fs = TrackedOS()
    owner = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=fs,
        current=lambda: False,
    )
    with pytest.raises(FrameError):
        owner.run()
    assert fs.open_attempts == 0 and owner.descriptors_closed


def test_parent_unsafe_home_refuses_and_closes_prior_ancestors(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    home, bound = scope
    home.chmod(0o777)
    fs = TrackedOS()
    owner = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=fs,
        current=lambda: True,
    )
    with pytest.raises(FrameError):
        owner.run()
    assert owner.descriptors_closed and fs.opened == set()


def test_parent_unknown_close_retains_attempt_and_cannot_replay(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    _, bound = scope

    class LostClose(TrackedOS):
        def __init__(self):
            super().__init__()
            self.calls = []

        def close(self, fd):
            self.calls.append(fd)
            super().close(fd)
            if len(self.calls) == 1:
                raise OSError("synthetic lost close acknowledgement")

    fs = LostClose()
    owner = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=fs,
        current=lambda: True,
    )
    with pytest.raises(FrameError):
        owner.run()
    attempts = tuple(fs.calls)
    original_failure = owner._failure
    assert owner.uncertain and not owner.descriptors_closed
    assert owner._cleanup_errors and fs.opened == set()
    with pytest.raises(FrameError):
        owner.run()
    assert tuple(fs.calls) == attempts
    assert owner._failure is original_failure


def test_parent_stat_failure_is_closed_and_retains_original_privately(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    _, bound = scope

    class Refused(TrackedOS):
        def stat(self, *args, **kwargs):
            raise OSError("synthetic private path must not enter public error")

    owner = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=Refused(),
        current=lambda: True,
    )
    with pytest.raises(FrameError) as captured:
        owner.run()
    assert str(captured.value) == "BI1_PARENT_READ_REFUSED"
    assert isinstance(owner._failure, OSError)
    assert owner.descriptors_closed


def test_actual_parent_policy_and_child_result_preserve_counts_and_directory_chain(scope):
    import io

    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_input_v3 import encode_input_v3
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_output_v2 import BoundedResultBufferV2, compare_parent_snapshot
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner
    from hmp_plugin.presentation_worker import process_child_stream_v3

    _, bound = scope
    parent = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=TrackedOS(),
        current=lambda: True,
    )
    snapshot = parent.run()
    assert parent.descriptors_closed
    row = {
        "schema": 3,
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
        "deadline_ns": int(bound.deadline * 1_000_000_000),
        "directory_policy": [[r.uid, r.gid, r.modes[0]] for r in snapshot.rules],
        "iid": "a" * 52,
        "canonical_fallback": "Hermes",
        "observed_at": 100,
        "parent_work_counts": dict(snapshot.counts),
    }
    output = io.BytesIO()
    process_child_stream_v3(
        io.BytesIO(encode_input_v3(row) + bound.challenge.encode() + b"\n"),
        output,
        fs=TrackedOS(),
        clock=time.monotonic,
        deadline=bound.deadline + 0.1,
        effective_uid=os.geteuid(),
        effective_gid=os.getegid(),
    )
    buffer = BoundedResultBufferV2()
    data = output.getvalue()
    for offset in range(0, len(data), 17):
        buffer.feed(data[offset : offset + 17])
    header, body = buffer.finish(bound.challenge, 1)
    totals = compare_parent_snapshot(header, snapshot=snapshot, parent_home=bound.home_path)
    assert totals["opens"] > snapshot.counts["opens"] and body == b""
    assert header["fields"]["display_name"] == "Synthetic"
    header["chain"][-1][1] += 1
    with pytest.raises(FrameError):
        compare_parent_snapshot(header, snapshot=snapshot, parent_home=bound.home_path)
    # Synthetic IO composition only: no native grant, thread join or live route proof.


def test_parent_pending_fd_survives_record_allocation_failure(scope, monkeypatch):
    from hmp_plugin import presentation_parent_policy as module
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError

    _, bound = scope
    fs = TrackedOS()
    owner = module.ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=fs,
        current=lambda: True,
    )

    def fail(*args, **kwargs):
        raise MemoryError("synthetic record allocation failure")

    monkeypatch.setattr(module, "_HeldDirectory", fail)
    with pytest.raises(FrameError):
        owner.run()
    assert fs.open_attempts == 1 and fs.opened == set()
    assert owner.descriptors_closed and owner._pending_fd is None
    assert owner._pending_close_attempted
    assert isinstance(owner._failure, MemoryError)


def test_parent_exhausted_open_credit_refuses_before_kernel_open(scope):
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    _, bound = scope
    fs = TrackedOS()
    work = PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline)
    for _ in range(80):
        work.charge_open()
    owner = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=work,
        fs=fs,
        current=lambda: True,
    )
    with pytest.raises(FrameError):
        owner.run()
    assert fs.open_attempts == 0 and owner.descriptors_closed


def test_policy_thread_result_waits_for_actual_worker_and_known_closes(scope):
    import threading

    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner
    from hmp_plugin.presentation_policy_thread import PolicyThreadOwner

    _, bound = scope
    entered, release = threading.Event(), threading.Event()

    class HeldStat(TrackedOS):
        first = True

        def stat(self, *args, **kwargs):
            if self.first:
                self.first = False
                entered.set()
                assert release.wait(timeout=1)
            return super().stat(*args, **kwargs)

    fs = HeldStat()
    policy = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=fs,
        current=lambda: True,
    )
    owner = PolicyThreadOwner(policy)
    owner.start()
    try:
        assert entered.wait(timeout=1)
        assert not owner.poll_join() and not owner.joined
        with pytest.raises(FrameError):
            owner.observed_snapshot()
    finally:
        release.set()
        while not owner.poll_join():
            assert time.monotonic() < bound.deadline
            time.sleep(0.005)
    snapshot = owner.observed_snapshot()
    assert snapshot.counts["opens"] == len(bound.directory_rules)
    assert policy.descriptors_closed and fs.opened == set()
    assert owner._worker is not None and not owner._worker.is_alive()


def test_policy_thread_start_failure_retains_owner_without_replay(scope, monkeypatch):
    from hmp_plugin import presentation_policy_thread as module
    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    _, bound = scope
    policy = ParentPolicyReadOwner(
        root=bound.root_path,
        home=bound.home_path,
        profile="default",
        uid=os.geteuid(),
        gid=os.getegid(),
        ledger=PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline),
        fs=TrackedOS(),
        current=lambda: True,
    )

    class FailedThread:
        calls = 0

        def __init__(self, **kwargs):
            pass

        def start(self):
            self.calls += 1
            raise OSError("synthetic unknown thread start")

    monkeypatch.setattr(module.threading, "Thread", FailedThread)
    owner = module.PolicyThreadOwner(policy)
    with pytest.raises(module.PolicyThreadStartError) as captured:
        owner.start()
    assert captured.value.failed_owner is owner and owner.uncertain
    assert owner._worker is not None and owner._worker.calls == 1
    with pytest.raises(FrameError):
        owner.start()
    with pytest.raises(FrameError):
        owner.poll_join()
    with pytest.raises(FrameError):
        owner.observed_snapshot()
    assert owner._worker.calls == 1 and not owner.joined


def test_parent_constructor_bounds_paths_before_large_allocation(scope):
    import tracemalloc

    from hmp_plugin.presentation_budget import PresentationWorkLedger
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    _, bound = scope
    work = PresentationWorkLedger(clock=time.monotonic, deadline=bound.deadline)
    huge = "/" + "x" * 2_000_000
    for root, home in ((huge, bound.home_path), (bound.root_path, huge)):
        tracemalloc.start()
        try:
            with pytest.raises(FrameError):
                ParentPolicyReadOwner(
                    root=root,
                    home=home,
                    profile="default",
                    uid=os.geteuid(),
                    gid=os.getegid(),
                    ledger=work,
                    fs=TrackedOS(),
                    current=lambda: True,
                )
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert peak < 500_000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "attack",
    [
        "none",
        "reentrant_postcheck",
        "retired_listener",
        "transfer",
        "transfer_retired",
        "abort_before_start",
        "abort_after_join",
        "abort_unjoined",
        "abort_uncertain",
        "construction_retired",
    ],
)
async def test_native_policy_binding_requires_admitted_operation_and_fresh_postcheck(scope, attack):
    from hmp_plugin.presentation_authority import (
        AuthorityRefusalError,
        ListenerFence,
        NativeObservation,
        OriginalHeaders,
        ParentAuthorityAdapter,
    )
    from hmp_plugin.presentation_jobs import CapturedLease
    from hmp_plugin.presentation_policy_binding import NativePolicyWork

    _, bound = scope

    class Headers:
        def getall(self, key, default):
            return {"Authorization": ["Bearer " + "A" * 43], "HMP-Instance": ["a" * 52]}.get(
                key, default
            )

    class Request:
        headers = Headers()

    class NativeFake:
        def __init__(self):
            self.allowed = True
            self.calls = []

        async def observe(self, record, phase):
            self.calls.append(phase)
            if not self.allowed:
                return None
            lease = record.lease
            return NativeObservation(
                lease.iid,
                lease.device_id,
                lease.user_id,
                lease.family_id,
                lease.profile,
                bound.home_path,
                record.listener,
                record.store,
                record.bridge,
                record.identity,
                record.native_owner,
                True,
            )

        async def drain(self, record):
            return True

    native = NativeFake()
    authority = ParentAuthorityAdapter("a" * 52, service=native)
    lease = CapturedLease("a" * 52, "device", "user", "family", "default", "b" * 64, "binding", 1)
    operation = authority.reserve(
        lease,
        "METADATA",
        OriginalHeaders.from_request(Request()),
        listener=object(),
        fence=ListenerFence(1),
        store=object(),
        bridge=object(),
        identity=object(),
        native_owner=object(),
    )
    with pytest.raises(AuthorityRefusalError):
        NativePolicyWork(authority, operation)
    assert await authority.initialize(operation)
    with pytest.raises(AuthorityRefusalError):
        NativePolicyWork(authority, operation)
    authority.start(operation)
    if attack == "construction_retired":
        original = authority._clock
        record = authority._record(operation)

        def clock():
            authority._clock = original
            # In-flight construction is not an abort receipt.
            assert not authority.refuse_policy_prelaunch(operation)
            record.fence.retire()
            return original()

        authority._clock = clock
        with pytest.raises(AuthorityRefusalError):
            NativePolicyWork(authority, operation)
        work = record.policy_work
        assert work._thread is None and work._policy is None
        assert authority.refuse_policy_prelaunch(operation)
        assert work.resources_closed
        assert await authority.retire_known(operation)
        return
    work = NativePolicyWork(authority, operation)
    with pytest.raises(AuthorityRefusalError):
        NativePolicyWork(authority, operation)
    if attack == "abort_before_start":
        assert authority.refuse_policy_prelaunch(operation)
        assert work.resources_closed
        with pytest.raises(AuthorityRefusalError):
            work.start()
        assert await authority.retire_known(operation)
        return
    work.start()
    if attack == "abort_unjoined":
        assert not authority.refuse_policy_prelaunch(operation)
        assert (
            authority._record(operation).owner.inspect(authority._record(operation).handle)[2]
            is False
        )
    while not work.poll_join():
        assert time.monotonic() < bound.deadline
        await __import__("asyncio").sleep(0.005)
    if attack in ("abort_after_join", "abort_unjoined", "abort_uncertain"):
        if attack == "abort_uncertain":
            work._policy.uncertain = True
            assert not authority.refuse_policy_prelaunch(operation)
            assert not await authority.retire_known(operation)
            return
        authority.cancel(operation)
        assert authority.refuse_policy_prelaunch(operation)
        assert work.resources_closed
        assert await authority.retire_known(operation)
        return
    with pytest.raises(AuthorityRefusalError):
        work.observed_snapshot()
    original_clock = authority._clock
    if attack == "reentrant_postcheck":

        def clock():
            authority._clock = original_clock
            nested = work.postcheck()
            with pytest.raises(AuthorityRefusalError):
                nested.send(None)
            return original_clock()

        authority._clock = clock
        with pytest.raises(AuthorityRefusalError):
            await work.postcheck()
        with pytest.raises(AuthorityRefusalError):
            work.observed_snapshot()
        assert native.calls == ["INITIAL", "BEFORE"]
        return
    assert await work.postcheck()
    if attack == "retired_listener":

        def clock():
            authority._clock = original_clock
            authority._record(operation).fence.retire()
            return original_clock()

        authority._clock = clock
        with pytest.raises(AuthorityRefusalError):
            work.observed_snapshot()
        return
    assert work.observed_snapshot().counts["opens"] == len(bound.directory_rules)
    assert native.calls == ["INITIAL", "BEFORE", "PRE_GO"]
    if attack in ("transfer", "transfer_retired"):
        from hmp_plugin.presentation_input_v3 import decode_input_v3

        if attack == "transfer_retired":

            def clock():
                authority._record(operation).fence.retire()
                return original_clock()

            authority._record(operation).owner._clock = clock
            with pytest.raises(AuthorityRefusalError):
                work.worker_input(
                    source_manifest_sha="b" * 64, canonical_fallback="Hermes", observed_at=1
                )
            return
        packet = work.worker_input(
            source_manifest_sha="b" * 64, canonical_fallback="Hermes", observed_at=1
        )
        assert not authority.refuse_policy_prelaunch(operation)
        row = decode_input_v3(packet)
        assert row["home"] == bound.home_path
        assert row["iid"] == "a" * 52
        assert row["profile"] == "default" and row["operation"] == "METADATA"
        assert row["challenge"] == authority._record(operation).owner.challenge(
            authority._record(operation).handle
        )
        assert row["parent_work_counts"]["opens"] == len(bound.directory_rules)
        assert row["deadline_ns"] == int(authority._record(operation).deadline * 1_000_000_000)
        assert "Authorization" not in packet.decode()
        with pytest.raises(AuthorityRefusalError):
            work.worker_input(
                source_manifest_sha="b" * 64, canonical_fallback="Hermes", observed_at=1
            )
        return
    with pytest.raises(AuthorityRefusalError):
        await work.postcheck()
    # Native service is synthetic; no actual bearer/native gateway qualification.

"""Private in-memory BI1 raster fork checks; no reader, decoder, or authority."""

from __future__ import annotations

import ast
import hashlib
import struct
import sys
import unittest
import zlib
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from hmp_plugin import local_media_raster_structure as g3
from hmp_plugin import presentation_raster as bi1


def chunk(kind: bytes, payload: bytes = b"") -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def png(width: int = 2, height: int = 2, extra: bytes = b"") -> bytes:
    head = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    return (
        bi1.PNG_SIGNATURE
        + head
        + extra
        + chunk(b"IDAT", zlib.compress(b"\x00" * 4))
        + chunk(b"IEND")
    )


def segment(marker: int, payload: bytes = b"") -> bytes:
    return bytes((255, marker)) + struct.pack(">H", len(payload) + 2) + payload


def jpeg(width: int = 2, height: int = 2, entropy: bytes = b"\x12\x34") -> bytes:
    dqt = segment(0xDB, b"\x00" + bytes(range(1, 65)))
    sof = segment(0xC0, struct.pack(">BHHB", 8, height, width, 1) + b"\x01\x11\x00")
    dc = segment(0xC4, b"\x00\x01" + bytes(15) + b"\x00")
    ac = segment(0xC4, b"\x10\x01" + bytes(15) + b"\x00")
    sos = segment(0xDA, b"\x01\x01\x00\x00\x3f\x00")
    return b"\xff\xd8" + dqt + sof + dc + ac + sos + entropy + b"\xff\xd9"


def webp(width: int = 2, height: int = 2) -> bytes:
    tag = b"\x50\x00\x00\x9d\x01\x2a" + struct.pack("<HH", width, height) + bytes(6)
    body = b"WEBP" + b"VP8 " + struct.pack("<I", len(tag)) + tag
    return b"RIFF" + struct.pack("<I", len(body)) + body


class Clock:
    def __init__(self, fail_at: int | None = None) -> None:
        self.calls = 0
        self.fail_at = fail_at

    def __call__(self) -> float:
        self.calls += 1
        return 2.0 if self.fail_at is not None and self.calls >= self.fail_at else 1.0


class Shared:
    def __init__(self) -> None:
        self.units = 0
        self.scans = 0
        self.hash_bytes = 0
        self.hash_slices = 0

    def charge_scan(self) -> None:
        if self.scans:
            raise RuntimeError("scan already claimed")
        self.scans += 1

    def charge_unit(self) -> None:
        self.units += 1

    def charge_hash_bytes(self, count: int) -> None:
        if type(count) is not int or not 1 <= count <= 65_536:
            raise RuntimeError("hash slice")
        if count > 2_000_000 - self.hash_bytes:
            raise RuntimeError("hash credit")
        self.hash_bytes += count
        self.hash_slices += 1


def inspect(data: bytes, suffix: str, clock: Clock | None = None, ledger: Shared | None = None):
    budget = bi1.RasterBudget(2.0, clock or Clock(), ledger or Shared())
    return bi1.inspect_fixed_avatar(data, suffix, hashlib.sha256(data).hexdigest(), budget), budget


class RasterFork(unittest.TestCase):
    def test_closed_loop_and_whole_body_call_inventory(self) -> None:
        tree = ast.parse(Path(bi1.__file__).read_text())
        loops = (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        found = Counter(
            (definition.name, type(child).__name__)
            for definition in tree.body
            if isinstance(definition, ast.FunctionDef)
            for child in ast.walk(definition)
            if isinstance(child, loops)
        )
        self.assertEqual(
            found,
            Counter(
                {
                    ("_check_png", "While"): 1,
                    ("_check_png", "For"): 1,
                    ("_next_jpeg_marker", "While"): 2,
                    ("_check_jpeg", "While"): 1,
                    ("_check_jpeg", "GeneratorExp"): 1,
                    ("_jpeg_sof", "For"): 1,
                    ("_jpeg_sof", "DictComp"): 1,
                    ("_jpeg_dqt", "While"): 1,
                    ("_jpeg_dht", "While"): 1,
                    ("_jpeg_scan", "For"): 2,
                    ("_jpeg_scan", "While"): 1,
                    ("_jpeg_scan", "GeneratorExp"): 1,
                    ("_check_webp", "While"): 1,
                    ("inspect_fixed_avatar", "For"): 1,
                    ("inspect_fixed_avatar", "GeneratorExp"): 1,
                }
            ),
        )
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        finds = [
            node
            for node in calls
            if isinstance(node.func, ast.Attribute) and node.func.attr == "find"
        ]
        self.assertEqual(len(finds), 1)
        self.assertEqual(len(finds[0].args), 3)  # bounded explicit end argument
        self.assertEqual(
            len(
                [
                    node
                    for node in calls
                    if isinstance(node.func, ast.Name) and node.func.id == "open"
                ]
            ),
            0,
        )
        self.assertNotIn("import re", Path(bi1.__file__).read_text())

    def refusal(self, data: bytes, suffix: str, reason: bi1.Reason, detail: str) -> None:
        with self.assertRaises(bi1.RasterRefused) as found:
            inspect(data, suffix)
        self.assertEqual((found.exception.reason, found.exception.detail), (reason, detail))

    def test_static_controls_and_exact_1024_square(self) -> None:
        for suffix, data, mime in (
            ("png", png(), "image/png"),
            ("jpg", jpeg(), "image/jpeg"),
            ("webp", webp(), "image/webp"),
        ):
            with self.subTest(suffix=suffix):
                descriptor, budget = inspect(data, suffix)
                self.assertEqual(
                    (descriptor.mime, descriptor.width, descriptor.height), (mime, 2, 2)
                )
                self.assertEqual(descriptor.sha256, hashlib.sha256(data).hexdigest())
                self.assertEqual(descriptor.length, len(data))
                self.assertEqual(descriptor.decodability, "unvalidated")
                self.assertGreater(budget.units, 0)
        for suffix, data in (
            ("png", png(1024, 1024)),
            ("jpg", jpeg(1024, 1024)),
            ("webp", webp(1024, 1024)),
        ):
            with self.subTest(suffix=suffix):
                descriptor, _ = inspect(data, suffix)
                self.assertEqual(descriptor.width * descriptor.height, 1_048_576)

    def test_dimension_refusal_at_parsed_header(self) -> None:
        for suffix, data in (
            ("png", png(1025, 1)),
            ("jpg", jpeg(1025, 1)),
            ("webp", webp(1025, 1)),
        ):
            with self.subTest(suffix=suffix):
                self.refusal(data, suffix, bi1.Reason.DIMENSIONS, "dims.over_limit")

    def test_suffix_digest_bounds_animation_and_one_use(self) -> None:
        data = png()
        for suffix in ("jpg", "webp"):
            self.refusal(data, suffix, bi1.Reason.MALFORMED, "input.structure_mismatch")
        budget = bi1.RasterBudget(2.0, Clock(), Shared())
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1.inspect_fixed_avatar(data, "png", "0" * 64, budget)
        self.assertEqual(found.exception.detail, "input.sha256_mismatch")
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), budget)
        self.assertEqual(found.exception.detail, "budget.reused")
        self.refusal(data + bytes(2_000_001), "png", bi1.Reason.TOO_LARGE, "input.bi1_size")
        self.refusal(
            png(extra=chunk(b"acTL", bytes(8))), "png", bi1.Reason.ANIMATED, "png.animation_chunk"
        )
        self.refusal(data + b"x", "png", bi1.Reason.TRAILING_DATA, "png.after_iend")

    def test_differential_selected_g3_corpus(self) -> None:
        controls = (
            png(),
            png(1024, 1024),
            jpeg(),
            jpeg(1024, 1024),
            webp(),
            webp(1024, 1024),
            png(extra=chunk(b"tEXt", b"abc")),
            jpeg(entropy=b"\xff\x00\x12"),
            png(extra=chunk(b"acTL", bytes(8))),
            png() + b"x",
            jpeg() + b"x",
            webp() + b"x",
            b"GIF89a" + bytes(20),
        )
        for data in controls:
            with self.subTest(length=len(data), prefix=data[:8]):
                try:
                    old = g3.check_raster_structure(data)
                    old_result = (old.kind, old.width, old.height)
                except g3.RasterRefused as error:
                    old_result = (error.reason.value, error.detail)
                suffix = (
                    "png"
                    if data.startswith(bi1.PNG_SIGNATURE)
                    else "jpg"
                    if data.startswith(b"\xff\xd8")
                    else "webp"
                    if data.startswith(b"RIFF")
                    else "png"
                )
                try:
                    new, _ = inspect(data, suffix)
                    new_result = (
                        {"image/png": "png", "image/jpeg": "jpeg", "image/webp": "webp"}[new.mime],
                        new.width,
                        new.height,
                    )
                except bi1.RasterRefused as error:
                    new_result = (error.reason.value, error.detail)
                self.assertEqual(new_result, old_result)

    def test_differential_generated_structural_cases(self) -> None:
        cases: list[bytes] = []
        for color, depth in ((0, 1), (0, 16), (2, 8), (2, 16), (4, 8), (6, 8), (6, 16)):
            for interlace in (0, 1):
                head = chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, depth, color, 0, 0, interlace))
                body = [head]
                if color == 3:
                    body.append(chunk(b"PLTE", b"\x01\x02\x03" * 2))
                body += [chunk(b"IDAT", zlib.compress(bytes(4))), chunk(b"IEND")]
                cases.append(bi1.PNG_SIGNATURE + b"".join(body))
        cases.extend(
            (
                png(extra=chunk(b"tEXt", b"abc")),
                png(extra=chunk(b"acTL", bytes(8))),
                png(extra=chunk(b"ABCD", b"x")),
                png() + b"x",
                jpeg(entropy=b"\xff\x00\x12"),
                jpeg(entropy=b"\xff\xff\x12"),
                jpeg() + b"x",
                webp(),
                webp(1024, 1024),
                webp() + b"x",
                webp(0, 2),
                b"GIF89a" + bytes(20),
                b"<svg/>",
            )
        )
        self.assertGreaterEqual(len(cases), 27)
        for data in cases:
            with self.subTest(length=len(data), prefix=data[:12]):
                try:
                    old = g3.check_raster_structure(data)
                    old_result = (old.kind, old.width, old.height)
                except g3.RasterRefused as error:
                    old_result = (error.reason.value, error.detail)
                if data.startswith(bi1.PNG_SIGNATURE):
                    suffix = "png"
                elif data.startswith(b"\xff\xd8"):
                    suffix = "jpg"
                elif data.startswith(b"RIFF"):
                    suffix = "webp"
                else:
                    suffix = "png"
                try:
                    new, _ = inspect(data, suffix)
                    kind = {"image/png": "png", "image/jpeg": "jpeg", "image/webp": "webp"}[
                        new.mime
                    ]
                    new_result = (kind, new.width, new.height)
                except bi1.RasterRefused as error:
                    new_result = (error.reason.value, error.detail)
                self.assertEqual(new_result, old_result)

    def test_differential_single_byte_mutations(self) -> None:
        cases = (("png", png()), ("jpg", jpeg()), ("webp", webp()))
        checked = 0
        for suffix, control in cases:
            for position in range(len(control)):
                for value in (0, 128, 255):
                    changed = control[:position] + bytes([value]) + control[position + 1 :]
                    if changed == control:
                        continue
                    try:
                        old = g3.check_raster_structure(changed)
                        old_result = (old.kind, old.width, old.height)
                    except g3.RasterRefused as error:
                        old_result = (error.reason.value, error.detail)
                    try:
                        new, _ = inspect(changed, suffix)
                        kind = {"image/png": "png", "image/jpeg": "jpeg", "image/webp": "webp"}[
                            new.mime
                        ]
                        new_result = (kind, new.width, new.height)
                    except bi1.RasterRefused as error:
                        new_result = (error.reason.value, error.detail)
                    self.assertEqual(new_result, old_result)
                    checked += 1
        self.assertGreater(checked, 500)

    def test_png_crc_second_slice_deadline(self) -> None:
        data = png(extra=chunk(b"tEXt", bytes(131_073)))
        real_crc = zlib.crc32
        seen = 0

        def counted_crc(*args, **kwargs):
            nonlocal seen
            seen += 1
            return real_crc(*args, **kwargs)

        def clock() -> float:
            return 2.0 if seen >= 2 else 1.0

        budget = bi1.RasterBudget(2.0, clock, Shared())
        with (
            patch.object(bi1.zlib, "crc32", side_effect=counted_crc),
            self.assertRaises(bi1.RasterRefused) as found,
        ):
            bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), budget)
        self.assertEqual(found.exception.detail, "budget.deadline")
        self.assertEqual(seen, 2)  # IHDR CRC and the first large tEXt CRC slice

    def test_hash_second_slice_deadline_before_scan(self) -> None:
        data = png(extra=chunk(b"tEXt", bytes(131_073)))
        clock = Clock(fail_at=3)
        with self.assertRaises(bi1.RasterRefused) as found:
            inspect(data, "png", clock)
        self.assertEqual(found.exception.detail, "budget.deadline")
        self.assertEqual(clock.calls, 3)

    def test_clock_rejects_nonfinite_negative_and_wrong_type(self) -> None:
        for value in (-1.0, float("-inf"), float("nan"), float("inf"), True, 0):
            with self.subTest(value=value):
                shared = Shared()
                budget = bi1.RasterBudget(2.0, lambda value=value: value, shared)
                with self.assertRaises(bi1.RasterRefused) as found:
                    budget.begin()
                self.assertEqual(found.exception.detail, "budget.deadline")
                self.assertEqual(shared.scans, 0)
                self.assertEqual(shared.hash_bytes, 0)
        zero = bi1.RasterBudget(2.0, lambda: 0.0, Shared())
        zero.begin()

        data = png()
        for value in (-1.0, float("-inf"), float("nan"), float("inf")):
            with self.subTest(later=value):
                calls = 0

                def later_clock(value: float = value) -> float:
                    nonlocal calls
                    calls += 1
                    return value if calls == 3 else 1.0

                shared = Shared()
                with self.assertRaises(bi1.RasterRefused) as found:
                    inspect(data, "png", later_clock, shared)
                self.assertEqual(found.exception.detail, "budget.deadline")
                self.assertEqual(shared.hash_bytes, len(data))
                self.assertEqual(shared.units, 0)

    def test_hash_credit_precedes_each_digest_update_and_preserves_units(self) -> None:
        data = b"x" * 65_537

        class StopSecondHash(Shared):
            def charge_hash_bytes(self, count: int) -> None:
                if self.hash_slices == 1:
                    raise RuntimeError("shared hash credit exhausted")
                super().charge_hash_bytes(count)

        class DigestSpy:
            def __init__(self) -> None:
                self.updates: list[int] = []

            def update(self, part: memoryview) -> None:
                self.updates.append(len(part))

            def hexdigest(self) -> str:
                return "0" * 64

        spy = DigestSpy()
        shared = StopSecondHash()
        budget = bi1.RasterBudget(2.0, Clock(), shared)
        with (
            patch.object(bi1.hashlib, "sha256", return_value=spy),
            self.assertRaises(bi1.RasterRefused) as found,
        ):
            bi1.inspect_fixed_avatar(data, "png", "0" * 64, budget)
        self.assertEqual(found.exception.detail, "budget.hash_charge")
        self.assertEqual(spy.updates, [65_536])
        self.assertEqual(shared.hash_bytes, 65_536)
        self.assertEqual(shared.hash_slices, 1)
        self.assertEqual(shared.units, 0)
        self.assertEqual(budget.units, 0)
        self.assertEqual(budget.hash_bytes, 65_536)

        successful = Shared()
        descriptor, normal = inspect(png(), "png", ledger=successful)
        self.assertEqual(descriptor.mime, "image/png")
        self.assertEqual(successful.hash_bytes, descriptor.length)
        self.assertEqual(normal.hash_bytes, descriptor.length)
        self.assertEqual(normal.units, successful.units)

        class StopFirstHash(Shared):
            def charge_hash_bytes(self, count: int) -> None:
                raise RuntimeError("first hash credit exhausted")

        first_spy = DigestSpy()
        first = bi1.RasterBudget(2.0, Clock(), StopFirstHash())
        with (
            patch.object(bi1.hashlib, "sha256", return_value=first_spy),
            self.assertRaises(bi1.RasterRefused) as first_refusal,
        ):
            bi1.inspect_fixed_avatar(data, "png", "0" * 64, first)
        self.assertEqual(first_refusal.exception.detail, "budget.hash_charge")
        self.assertEqual(first_spy.updates, [])

        class FalseReturn(Shared):
            def charge_hash_bytes(self, count: int) -> None:
                return False

        malformed = bi1.RasterBudget(2.0, Clock(), FalseReturn())
        with self.assertRaises(bi1.RasterRefused) as bad_return:
            bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), malformed)
        self.assertEqual(bad_return.exception.detail, "budget.hash_charge_result")

        exact = b"x" * 131_154
        exact_spy = DigestSpy()
        exact_shared = Shared()
        with (
            patch.object(bi1.hashlib, "sha256", return_value=exact_spy),
            self.assertRaises(bi1.RasterRefused) as unsupported,
        ):
            bi1.inspect_fixed_avatar(
                exact, "png", "0" * 64, bi1.RasterBudget(2.0, Clock(), exact_shared)
            )
        self.assertEqual(unsupported.exception.detail, "input.signature")
        self.assertEqual(exact_spy.updates, [65_536, 65_536, 82])
        self.assertEqual(exact_shared.hash_bytes, len(exact))

        second_budget = bi1.RasterBudget(2.0, Clock(), exact_shared)
        with self.assertRaises(bi1.RasterRefused) as reused_shared:
            bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), second_budget)
        self.assertEqual(reused_shared.exception.detail, "budget.scan_charge")
        self.assertEqual(exact_shared.hash_bytes, len(exact))

    def test_webp_and_jpeg_deadline_inside_scans(self) -> None:
        for suffix, data in (("webp", webp()), ("jpg", jpeg(entropy=b"\x12" * 131_072))):
            with self.subTest(suffix=suffix):
                with self.assertRaises(bi1.RasterRefused) as found:
                    inspect(data, suffix, Clock(fail_at=5))
                self.assertEqual(found.exception.detail, "budget.deadline")

    def test_jpeg_entropy_second_window_and_pre_return_deadline(self) -> None:
        data = b"\x12" * 131_072 + b"\xff\xd9"
        budget = bi1.RasterBudget(2.0, Clock(fail_at=3), Shared())
        budget.begin()
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1._next_jpeg_marker(data, 0, budget)
        self.assertEqual(found.exception.detail, "budget.deadline")
        for suffix, body in (("png", png()), ("jpg", jpeg()), ("webp", webp())):
            with self.subTest(suffix=suffix):
                good_clock = Clock()
                inspect(body, suffix, good_clock)
                with self.assertRaises(bi1.RasterRefused) as late:
                    inspect(body, suffix, Clock(fail_at=good_clock.calls))
                self.assertEqual(late.exception.detail, "budget.deadline")

    def test_table_restart_and_webp_chunk_checkpoints(self) -> None:
        examples = (("jpg", jpeg(), "_jpeg_dqt"), ("jpg", jpeg(), "_jpeg_dht"))
        for suffix, data, caller in examples:
            with self.subTest(caller=caller):
                state = {"expired": False}

                def clock(state: dict[str, bool] = state) -> float:
                    return 2.0 if state["expired"] else 1.0

                budget = bi1.RasterBudget(2.0, clock, Shared())
                real_tick = budget.tick

                def expire_at_caller(
                    expected: str = caller,
                    state: dict[str, bool] = state,
                    tick=real_tick,
                ) -> None:
                    if sys._getframe(1).f_code.co_name == expected:
                        state["expired"] = True
                    tick()

                budget.tick = expire_at_caller
                with self.assertRaises(bi1.RasterRefused) as found:
                    bi1.inspect_fixed_avatar(data, suffix, hashlib.sha256(data).hexdigest(), budget)
                self.assertEqual(found.exception.detail, "budget.deadline")
        data = webp()
        expired = False

        def clock() -> float:
            return 2.0 if expired else 1.0

        budget = bi1.RasterBudget(2.0, clock, Shared())
        real_unit = budget.unit

        def expire_at_chunk(detail: str) -> None:
            nonlocal expired
            if sys._getframe(1).f_code.co_name == "_check_webp":
                expired = True
            real_unit(detail)

        budget.unit = expire_at_chunk
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1.inspect_fixed_avatar(data, "webp", hashlib.sha256(data).hexdigest(), budget)
        self.assertEqual(found.exception.detail, "budget.deadline")

    def test_shared_ledger_and_failed_credit(self) -> None:
        data = png()
        shared = Shared()
        budget = bi1.RasterBudget(2.0, Clock(), shared)
        result = bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), budget)
        self.assertEqual(result.mime, "image/png")
        self.assertEqual(budget.units, shared.units)
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), budget)
        self.assertEqual(found.exception.detail, "budget.reused")

        class Full(Shared):
            def charge_unit(self) -> None:
                raise RuntimeError("cap")

        full = bi1.RasterBudget(2.0, Clock(), Full())
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), full)
        self.assertEqual(found.exception.detail, "budget.charge")
        second = bi1.RasterBudget(2.0, Clock(), shared)
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1.inspect_fixed_avatar(data, "png", hashlib.sha256(data).hexdigest(), second)
        self.assertEqual(found.exception.detail, "budget.scan_charge")

    def test_closed_unbound_ledger_and_structural_cap(self) -> None:
        body = png()
        unbound = bi1.RasterBudget(2.0, Clock(), object())
        with self.assertRaises(bi1.RasterRefused) as found:
            bi1.inspect_fixed_avatar(body, "png", hashlib.sha256(body).hexdigest(), unbound)
        self.assertEqual(found.exception.detail, "budget.scan_charge")
        spam = png(extra=chunk(b"tEXt") * 10_000)
        self.refusal(spam, "png", bi1.Reason.TOO_MANY_UNITS, "png.chunk_count")
        segments = b"\xff\xd8" + segment(0xFE) * 10_000
        self.refusal(segments, "jpg", bi1.Reason.TOO_MANY_UNITS, "jpeg.segment_count")


if __name__ == "__main__":
    unittest.main()

"""Tests for tools/research/local_media_raster_structure.py (G3 structural checks, not decoding).

Every fixture is synthetic and built here from fixed constants. Each negative flips exactly one
property of an accepted control so the refusal is attributable to that property. Admission means
"structure of an allowed static raster" only; the corrupt-payload tests pin that limit.
"""

from __future__ import annotations

import ast
import inspect
import struct
import subprocess
import sys
import time
import tracemalloc
import zlib
from pathlib import Path

import pytest

from hmp_plugin import local_media_raster_structure as rs
from hmp_plugin.local_media_raster_structure import MAX_BYTES, Reason, check_raster_structure

SOURCE = Path(rs.__file__)


def refused(data: bytes, reason: Reason, detail: str) -> None:
    with pytest.raises(rs.RasterRefused) as info:
        check_raster_structure(data)
    assert (info.value.reason, info.value.detail) == (reason, detail)


def malformed(data: bytes, detail: str) -> None:
    refused(data, Reason.MALFORMED, detail)


# --- PNG builders --------------------------------------------------------------------------------


def chunk(ctype: bytes, payload: bytes = b"", crc: int | None = None) -> bytes:
    if crc is None:
        crc = zlib.crc32(ctype + payload)
    return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", crc)


def ihdr(w=2, h=2, depth=8, color=6, comp=0, filt=0, interlace=0) -> bytes:
    return chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, color, comp, filt, interlace))


IDAT_OK = zlib.compress(b"\x00" * 4)


def png(chunks: list[bytes]) -> bytes:
    return rs.PNG_SIGNATURE + b"".join(chunks)


def png_chunks(color=6, depth=8, w=2, h=2, interlace=0) -> list[bytes]:
    out = [ihdr(w, h, depth, color, interlace=interlace)]
    if color == 3:
        out.append(chunk(b"PLTE", b"\x01\x02\x03" * 2))
    out += [chunk(b"IDAT", IDAT_OK), chunk(b"IEND")]
    return out


def png_insert(index: int, extra: bytes, **kw) -> bytes:
    chunks = png_chunks(**kw)
    chunks.insert(index, extra)
    return png(chunks)


VALID_PNG = png(png_chunks())

# --- JPEG builders -------------------------------------------------------------------------------

SOI, EOI = b"\xff\xd8", b"\xff\xd9"


def seg(marker: int, payload: bytes = b"") -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


DQT = seg(0xDB, b"\x00" + bytes(range(1, 65)))


def dht(tc: int, th: int, n: int = 1) -> bytes:
    return seg(0xC4, bytes([tc << 4 | th, n]) + bytes(15) + bytes(n))


DHT_DC, DHT_AC = dht(0, 0), dht(1, 0)


def sof(marker=0xC0, comps=((1, 0x11, 0),), w=2, h=2, precision=8) -> bytes:
    payload = struct.pack(">BHHB", precision, h, w, len(comps))
    return seg(marker, payload + b"".join(bytes(c) for c in comps))


def sos(comps=((1, 0x00),), ss=0, se=63, ah=0, al=0) -> bytes:
    payload = bytes([len(comps)]) + b"".join(bytes(c) for c in comps)
    return seg(0xDA, payload + bytes([ss, se, ah << 4 | al]))


ENTROPY = b"\x12\x34"


def jpeg(parts: list[bytes]) -> bytes:
    return b"".join(parts)


def baseline_parts(entropy: bytes = ENTROPY) -> list[bytes]:
    return [SOI, DQT, sof(), DHT_DC, DHT_AC, sos(), entropy, EOI]


VALID_JPEG = jpeg(baseline_parts())
RGB = ((1, 0x22, 0), (2, 0x11, 0), (3, 0x11, 0))


def progressive_parts() -> list[bytes]:
    return [
        SOI,
        DQT,
        sof(0xC2),
        DHT_DC,
        DHT_AC,
        sos(ss=0, se=0, ah=0, al=1),
        ENTROPY,
        sos(ss=1, se=63, ah=0, al=1),
        ENTROPY,
        sos(ss=1, se=63, ah=1, al=0),
        ENTROPY,
        sos(ss=0, se=0, ah=1, al=0),
        ENTROPY,
        EOI,
    ]


# --- WebP builders -------------------------------------------------------------------------------


def wchunk(fourcc: bytes, payload: bytes) -> bytes:
    return fourcc + struct.pack("<I", len(payload)) + payload + b"\0" * (len(payload) & 1)


def riff(*chunks: bytes) -> bytes:
    body = b"WEBP" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def vp8(w=2, h=2, tag=0x50, start=b"\x9d\x01\x2a", scale=0) -> bytes:
    header = tag.to_bytes(3, "little") + start + struct.pack("<HH", w | scale << 14, h)
    return wchunk(b"VP8 ", header + bytes(6))


def vp8l(w=2, h=2, alpha=0, version=0, sig=0x2F) -> bytes:
    bits = (w - 1) | (h - 1) << 14 | alpha << 28 | version << 29
    return wchunk(b"VP8L", bytes([sig]) + struct.pack("<I", bits) + bytes(4))


def vp8x(flags=0, w=2, h=2, reserved=b"\0\0\0") -> bytes:
    canvas = (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")
    return wchunk(b"VP8X", bytes([flags]) + reserved + canvas)


ALPH_COMPRESSED = wchunk(b"ALPH", b"\x01\x00\x00")
VALID_VP8, VALID_VP8L = riff(vp8()), riff(vp8l())
VALID_VP8X = riff(vp8x(), vp8())

# --- accepted structures -------------------------------------------------------------------------


@pytest.mark.parametrize("color,depth", [(0, 1), (0, 16), (2, 8), (2, 16), (4, 8), (6, 8), (6, 16)])
@pytest.mark.parametrize("interlace", [0, 1])
def test_png_accepts_legal_color_depth_interlace(color, depth, interlace):
    result = check_raster_structure(png(png_chunks(color, depth, interlace=interlace)))
    assert (result.kind, result.width, result.height) == ("png", 2, 2)
    assert result.decodability == "unvalidated"


@pytest.mark.parametrize("depth", [1, 2, 4, 8])
def test_png_accepts_indexed_with_palette(depth):
    assert check_raster_structure(png(png_chunks(3, depth))).kind == "png"


def test_png_admits_split_idat_and_zlib_header_split_across_chunks():
    chunks = [ihdr(), chunk(b"IDAT", IDAT_OK[:1]), chunk(b"IDAT", IDAT_OK[1:]), chunk(b"IEND")]
    assert check_raster_structure(png(chunks)).kind == "png"


def test_jpeg_accepts_baseline_gray_and_rgb_interleaved_and_separate_scans():
    assert check_raster_structure(VALID_JPEG).kind == "jpeg"
    shared = [SOI, DQT, sof(comps=RGB), DHT_DC, DHT_AC]
    one = [*shared, sos(((1, 0), (2, 0), (3, 0))), ENTROPY, EOI]
    assert check_raster_structure(jpeg(one)).kind == "jpeg"
    three: list[bytes] = list(shared)
    for cid in (1, 2, 3):
        three += [sos(((cid, 0),)), ENTROPY]
    assert check_raster_structure(jpeg([*three, EOI])).kind == "jpeg"


def test_jpeg_accepts_progressive_gray_and_rgb():
    assert check_raster_structure(jpeg(progressive_parts())).kind == "jpeg"
    parts = progressive_parts()
    parts[2] = sof(0xC2, comps=RGB)
    dc = [sos(((1, 0), (2, 0), (3, 0)), 0, 0, 0, 1), ENTROPY]
    ac = [p for c in (1, 2, 3) for p in (sos(((c, 0),), 1, 63, 0, 1), ENTROPY)]
    assert check_raster_structure(jpeg([*parts[:5], *dc, *ac, EOI])).kind == "jpeg"


def test_jpeg_accepts_stuffed_bytes_and_ordered_restarts():
    stuffed = baseline_parts(b"\xff\x00\x12\xff\x00")
    assert check_raster_structure(jpeg(stuffed)).kind == "jpeg"
    parts = baseline_parts(b"\x01\xff\xd0\x02\xff\xd1\x03")
    parts.insert(5, seg(0xDD, b"\x00\x01"))
    assert check_raster_structure(jpeg(parts)).kind == "jpeg"


def test_jpeg_metadata_segments_pass_without_interpretation():
    parts = baseline_parts()
    parts[1:1] = [seg(0xE1, b"Exif\0\0junk"), seg(0xFE, b"comment"), seg(0xEE, b"Adobe")]
    assert check_raster_structure(jpeg(parts)).kind == "jpeg"


@pytest.mark.parametrize(
    "data,kind",
    [
        (VALID_VP8, "webp"),
        (VALID_VP8L, "webp"),
        (VALID_VP8X, "webp"),
        (riff(vp8x(0x10), ALPH_COMPRESSED, vp8()), "webp"),
        (riff(vp8x(0x10), vp8l(alpha=1)), "webp"),
        (
            riff(
                vp8x(0x20 | 0x08 | 0x04),
                wchunk(b"ICCP", b"icc"),
                vp8(),
                wchunk(b"EXIF", b"e"),
                wchunk(b"XMP ", b"xy"),
            ),
            "webp",
        ),
    ],
)
def test_webp_accepts_lossy_lossless_extended_alpha_and_metadata(data, kind):
    assert check_raster_structure(data).kind == kind


def test_webp_odd_payload_requires_and_accepts_zero_pad():
    data = riff(vp8x(0x08), vp8(), wchunk(b"EXIF", b"odd"))
    assert len(data) % 2 == 0
    assert check_raster_structure(data).kind == "webp"


# --- limits --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "w,h,ok",
    [
        (8192, 2441, True),
        (8192, 2442, False),
        (8193, 1, False),
        (1, 8193, False),
        (5000, 5000, False),
        (8192, 8192, False),
        (1, 1, True),
        (8192, 1, True),
    ],
)
def test_dimension_caps_apply_to_every_format(w, h, ok):
    cases = {
        "png": png(png_chunks(w=w, h=h)),
        "jpeg": jpeg([SOI, DQT, sof(w=w, h=h), DHT_DC, DHT_AC, sos(), ENTROPY, EOI]),
        "webp-vp8l": riff(vp8l(w, h)),
        "webp-vp8x": riff(vp8x(0, w, h), vp8(w, h)) if max(w, h) < 16384 else b"",
    }
    for name, data in cases.items():
        if ok:
            assert check_raster_structure(data).width == w, name
        else:
            refused(data, Reason.DIMENSIONS, "dims.over_limit")


@pytest.mark.parametrize("w,h", [(0, 2), (2, 0)])
def test_zero_dimensions_are_malformed(w, h):
    malformed(png(png_chunks(w=w, h=h)), "dims.zero")
    malformed(
        jpeg([SOI, DQT, sof(w=w, h=h), DHT_DC, DHT_AC, sos(), ENTROPY, EOI]),
        "dims.zero" if w == 0 else "jpeg.height_zero",
    )


def test_byte_size_cap_exact_boundary_and_empty():
    filler = MAX_BYTES - len(VALID_PNG) - 12
    exact = png([ihdr(), chunk(b"tEXt", b"\0" * filler), chunk(b"IDAT", IDAT_OK), chunk(b"IEND")])
    assert len(exact) == MAX_BYTES
    assert check_raster_structure(exact).kind == "png"
    refused(exact + b"\0", Reason.TOO_LARGE, "input.over_8_mib")
    refused(b"", Reason.EMPTY, "input.empty")


def test_png_chunk_count_cap_is_exactly_10000():
    def build(total: int) -> bytes:
        filler = [chunk(b"tEXt", b"k")] * (total - 3)
        return png([ihdr(), chunk(b"IDAT", IDAT_OK), *filler, chunk(b"IEND")])

    assert check_raster_structure(build(rs.MAX_UNITS)).kind == "png"
    refused(build(rs.MAX_UNITS + 1), Reason.TOO_MANY_UNITS, "png.chunk_count")


def test_jpeg_segment_count_cap_counts_segments_and_restarts():
    def build(extra: int) -> bytes:
        parts = baseline_parts()
        parts[1:1] = [seg(0xFE, b"c")] * extra
        return jpeg(parts)

    base = 6  # DQT, SOF, DHT, DHT, SOS, EOI
    assert check_raster_structure(build(rs.MAX_UNITS - base)).kind == "jpeg"
    refused(build(rs.MAX_UNITS - base + 1), Reason.TOO_MANY_UNITS, "jpeg.segment_count")
    parts = baseline_parts(b"\x01" + b"\xff\xd0\xff\xd1" * 1 + b"\x02")
    parts.insert(5, seg(0xDD, b"\x00\x01"))
    assert check_raster_structure(jpeg(parts)).kind == "jpeg"
    restarts = b"".join(bytes([0xFF, 0xD0 + i % 8, 0x01]) for i in range(rs.MAX_UNITS))
    parts = baseline_parts(b"\x01" + restarts)
    parts.insert(5, seg(0xDD, b"\x00\x01"))
    refused(jpeg(parts), Reason.TOO_MANY_UNITS, "jpeg.segment_count")


# --- PNG refusals --------------------------------------------------------------------------------


def test_png_signature_prefix_truncation_always_refuses():
    for i in range(len(VALID_PNG)):
        with pytest.raises(rs.RasterRefused):
            check_raster_structure(VALID_PNG[:i] if i else b"\x89")


def test_png_truncated_and_overflowing_lengths():
    malformed(VALID_PNG[:-12], "png.no_iend")
    malformed(VALID_PNG[:-5], "png.truncated_chunk")
    for length in (0x7FFFFFFF, 0xFFFFFFFF, len(VALID_PNG)):
        bad = bytearray(VALID_PNG)
        bad[8:12] = struct.pack(">I", length)
        malformed(bytes(bad), "png.length_overflow")


@pytest.mark.parametrize("index", [0, 1, 2])
def test_png_bad_crc_in_any_chunk_refuses_and_good_crc_admits(index):
    chunks = png_chunks()
    good = chunks[index]
    chunks[index] = good[:-1] + bytes([good[-1] ^ 1])
    malformed(png(chunks), "png.crc")
    chunks[index] = good
    assert check_raster_structure(png(chunks)).kind == "png"


def test_png_corrupt_payload_byte_fails_crc():
    bad = bytearray(VALID_PNG)
    bad[8 + 8 + 3] ^= 1  # inside IHDR
    malformed(bytes(bad), "png.crc")


@pytest.mark.parametrize(
    "bad,detail",
    [
        (ihdr(depth=4, color=2), "png.ihdr_depth_color"),
        (ihdr(depth=16, color=3), "png.ihdr_depth_color"),
        (ihdr(comp=1), "png.ihdr_method"),
        (ihdr(filt=1), "png.ihdr_method"),
        (ihdr(interlace=2), "png.ihdr_method"),
        (chunk(b"IHDR", b"\0" * 12), "png.ihdr_length"),
    ],
)
def test_png_invalid_ihdr(bad, detail):
    malformed(png([bad, chunk(b"IDAT", IDAT_OK), chunk(b"IEND")]), detail)


def test_png_ihdr_must_be_first_and_unique():
    malformed(png([chunk(b"tEXt", b"k"), *png_chunks()]), "png.ihdr_order")
    malformed(png_insert(1, ihdr()), "png.ihdr_order")


def test_png_critical_chunk_rules():
    refused(png_insert(1, chunk(b"ABCD")), Reason.UNSUPPORTED_VARIANT, "png.unknown_critical")
    refused(png_insert(1, chunk(b"CgBI")), Reason.UNSUPPORTED_VARIANT, "png.unknown_critical")
    malformed(png_insert(1, chunk(b"tEst")), "png.chunk_type")  # reserved bit set
    malformed(png_insert(1, chunk(b"t3xt")), "png.chunk_type")
    assert check_raster_structure(png_insert(1, chunk(b"teXt", b"x"))).kind == "png"  # metadata
    assert check_raster_structure(png_insert(1, chunk(b"zzZz", b"\xff" * 9))).kind == "png"


def test_png_chunk_order_and_duplicates():
    idat = chunk(b"IDAT", IDAT_OK)
    malformed(png([ihdr(), chunk(b"IEND")]), "png.no_idat")
    malformed(
        png([ihdr(), idat, chunk(b"tEXt", b"k"), idat, chunk(b"IEND")]), "png.idat_not_contiguous"
    )
    malformed(png([ihdr(), idat]), "png.no_iend")
    malformed(png([ihdr(), idat, chunk(b"IEND", b"x")]), "png.iend_length")
    two = png([ihdr(), chunk(b"gAMA", b"\0" * 4), chunk(b"gAMA", b"\0" * 4), idat, chunk(b"IEND")])
    malformed(two, "png.duplicate_chunk")
    late = png([ihdr(), idat, chunk(b"gAMA", b"\0" * 4), chunk(b"IEND")])
    malformed(late, "png.ancillary_order")
    ok = png([ihdr(), chunk(b"gAMA", b"\0" * 4), chunk(b"pHYs", bytes(9)), idat, chunk(b"IEND")])
    assert check_raster_structure(ok).kind == "png"


def test_png_palette_rules():
    plte = chunk(b"PLTE", b"\0\0\0" * 2)
    idat = chunk(b"IDAT", IDAT_OK)
    base = [ihdr(depth=8, color=3), plte, idat, chunk(b"IEND")]
    assert check_raster_structure(png(base)).kind == "png"
    malformed(png([base[0], idat, chunk(b"IEND")]), "png.indexed_without_plte")
    malformed(png([base[0], idat, plte, chunk(b"IEND")]), "png.indexed_without_plte")
    malformed(png([base[0], plte, plte, idat, chunk(b"IEND")]), "png.plte_order")
    malformed(png([base[0], plte, idat, plte, chunk(b"IEND")]), "png.plte_order")
    malformed(png([ihdr(color=0), plte, idat, chunk(b"IEND")]), "png.plte_order")
    malformed(png([ihdr(color=4), plte, idat, chunk(b"IEND")]), "png.plte_order")
    assert check_raster_structure(png([ihdr(color=2), plte, idat, chunk(b"IEND")])).kind == "png"
    for payload, detail in ((b"\0\0", "png.plte_length"), (b"", "png.plte_length")):
        malformed(png([base[0], chunk(b"PLTE", payload), idat, chunk(b"IEND")]), detail)
    three = chunk(b"PLTE", b"\0\0\0" * 3)
    malformed(png([ihdr(depth=1, color=3), three, idat, chunk(b"IEND")]), "png.plte_too_large")
    assert check_raster_structure(png([ihdr(depth=2, color=3), three, idat, chunk(b"IEND")]))
    bkgd = chunk(b"bKGD", b"\0")
    malformed(png([base[0], bkgd, plte, idat, chunk(b"IEND")]), "png.plte_order")
    assert check_raster_structure(png([base[0], plte, bkgd, idat, chunk(b"IEND")])).kind == "png"
    malformed(
        png([base[0], plte, chunk(b"gAMA", bytes(4)), idat, chunk(b"IEND")]), "png.ancillary_order"
    )


def test_png_trns_and_hist_rules():
    plte = chunk(b"PLTE", b"\0\0\0" * 2)
    idat, iend = chunk(b"IDAT", IDAT_OK), chunk(b"IEND")
    ok = [ihdr(color=3), plte, chunk(b"tRNS", b"\xff\xff"), idat, iend]
    assert check_raster_structure(png(ok)).kind == "png"
    malformed(
        png([ihdr(color=3), plte, chunk(b"tRNS", b"\xff" * 3), idat, iend]), "png.trns_length"
    )
    malformed(png([ihdr(color=6), chunk(b"tRNS", b"\0" * 6), idat, iend]), "png.trns_invalid")
    malformed(png([ihdr(color=3), chunk(b"tRNS", b"\xff"), plte, idat, iend]), "png.trns_invalid")
    assert check_raster_structure(png([ihdr(color=0), chunk(b"tRNS", b"\0\0"), idat, iend]))
    malformed(png([ihdr(color=0), chunk(b"tRNS", b"\0"), idat, iend]), "png.trns_length")
    malformed(png([ihdr(color=2), chunk(b"hIST", b"\0\0"), idat, iend]), "png.hist_without_plte")


@pytest.mark.parametrize("ctype", [b"acTL", b"fcTL", b"fdAT"])
@pytest.mark.parametrize("where", ["before_idat", "after_idat"])
def test_png_apng_refused_anywhere(ctype, where):
    payload = bytes(8) if ctype == b"acTL" else bytes(26 if ctype == b"fcTL" else 4)
    index = 1 if where == "before_idat" else 2
    refused(png_insert(index, chunk(ctype, payload)), Reason.ANIMATED, "png.animation_chunk")
    assert check_raster_structure(VALID_PNG).kind == "png"  # control: same PNG without it


@pytest.mark.parametrize(
    "head",
    [b"\x00\x00", b"\x78\x00", b"\x78\xbb", b"\x88\x1c", b"\x78\x20"[:2], b"\x78"],
)
def test_png_idat_zlib_header_sanity(head):
    bad = png([ihdr(), chunk(b"IDAT", head + b"\0\0"), chunk(b"IEND")])
    malformed(bad, "png.zlib_header")


def test_png_trailing_payload_refused():
    for tail in (b"PK\x03\x04", b"\0", b"\x89PNG\r\n\x1a\n"):
        refused(VALID_PNG + tail, Reason.TRAILING_DATA, "png.after_iend")
    refused(VALID_PNG + VALID_PNG, Reason.TRAILING_DATA, "png.after_iend")


# --- JPEG refusals -------------------------------------------------------------------------------


def test_jpeg_prefix_truncation_always_refuses():
    for data in (VALID_JPEG, jpeg(progressive_parts())):
        for i in range(3, len(data)):
            with pytest.raises(rs.RasterRefused):
                check_raster_structure(data[:i])


def test_jpeg_trailing_payload_and_missing_eoi():
    for tail in (b"<html>", b"\0", EOI, b"\xff"):
        refused(VALID_JPEG + tail, Reason.TRAILING_DATA, "jpeg.after_eoi")
    malformed(VALID_JPEG[:-2], "jpeg.no_eoi")


@pytest.mark.parametrize("marker", [0xC1, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCF])
def test_jpeg_unsupported_sof_refused(marker):
    parts = baseline_parts()
    parts[2] = sof(marker)
    refused(jpeg(parts), Reason.UNSUPPORTED_VARIANT, "jpeg.unsupported_sof")
    assert check_raster_structure(VALID_JPEG).kind == "jpeg"


def test_jpeg_cmyk_two_component_and_12_bit_refused():
    cmyk = tuple((i, 0x11, 0) for i in range(1, 5))
    for comps, precision in ((cmyk, 8), (((1, 0x11, 0), (2, 0x11, 0)), 8), (((1, 0x11, 0),), 12)):
        parts = baseline_parts()
        parts[2] = sof(comps=comps, precision=precision)
        refused(
            jpeg(parts),
            Reason.UNSUPPORTED_VARIANT,
            "jpeg.precision" if precision == 12 else "jpeg.components",
        )


def test_jpeg_exactly_one_sof():
    parts = baseline_parts()
    malformed(jpeg([*parts[:3], sof(194), *parts[3:]]), "jpeg.second_sof")
    malformed(jpeg([*parts[:3], sof(), *parts[3:]]), "jpeg.second_sof")
    malformed(jpeg(parts[:2] + parts[3:]), "jpeg.scan_before_sof")
    malformed(jpeg([*parts[:7], sof(), *parts[7:]]), "jpeg.second_sof")
    malformed(jpeg([SOI, DQT, DHT_DC, DHT_AC, EOI]), "jpeg.eoi_without_scan")


def test_jpeg_empty_sos_segment_at_end_of_buffer_is_a_closed_refusal():
    control = jpeg([*baseline_parts()[:5], b"\xff\xda\x00\x02", EOI])
    malformed(control, "jpeg.sos_length")  # same bytes with a following marker
    malformed(jpeg([*baseline_parts()[:5], b"\xff\xda\x00\x02"]), "jpeg.sos_length")


@pytest.mark.parametrize(
    "comps",
    [
        ((1, 0x22, 0), (1, 0x11, 0), (3, 0x11, 0)),
        ((1, 0x02, 0),),
        ((1, 0x20, 0),),
        ((1, 0x52, 0),),
        ((1, 0x25, 0),),
        ((1, 0x11, 4),),
    ],
    ids=["duplicate_id", "v0", "h0", "h5", "v5", "tq4"],
)
def test_jpeg_sof_component_rules(comps):
    parts = baseline_parts()
    assert check_raster_structure(jpeg(parts)).kind == "jpeg"
    parts[2] = sof(comps=comps)
    malformed(jpeg(parts), "jpeg.component")


def test_jpeg_scan_count_cap_is_exactly_64():
    def build(total: int) -> bytes:
        parts = progressive_parts()[:5]
        parts += [sos(ss=0, se=0, ah=0, al=1), ENTROPY, sos(ss=1, se=63, ah=0, al=1), ENTROPY]
        parts += [sos(ss=1, se=63, ah=1, al=0), ENTROPY] * (total - 2)
        return jpeg([*parts, EOI])

    assert rs.MAX_JPEG_SCANS == 64
    assert check_raster_structure(build(64)).kind == "jpeg"
    refused(build(65), Reason.TOO_MANY_UNITS, "jpeg.scan_count")


def test_jpeg_unknown_or_unlisted_markers_refuse():
    for marker in (0xC8, 0xCC, 0xDC, 0xDE, 0xDF, 0xF0, 0xFD, 0x02, 0xD8):
        parts = baseline_parts()
        parts.insert(1, seg(marker, b"\0\0"))
        refused(jpeg(parts), Reason.UNSUPPORTED_VARIANT, "jpeg.unsupported_marker")
    parts = baseline_parts()
    parts.insert(1, b"\xff\xd0")
    refused(jpeg(parts), Reason.UNSUPPORTED_VARIANT, "jpeg.unsupported_marker")
    refused(b"\xff\xd8\xff\xff", Reason.UNSUPPORTED_VARIANT, "jpeg.unsupported_marker")  # fill
    malformed(jpeg([SOI, seg(0xFE), b"\x00\x00"]), "jpeg.marker_expected")


def test_jpeg_segment_length_bounds():
    parts = baseline_parts()
    parts.insert(1, b"\xff\xe0\x00\x01")
    malformed(jpeg(parts), "jpeg.segment_length")
    parts[1] = b"\xff\xe0\xff\xff" + b"\0" * 10
    malformed(jpeg(parts), "jpeg.segment_length")
    malformed(SOI + b"\xff\xe0\x00", "jpeg.truncated_segment")


def test_jpeg_table_requirements():
    parts = baseline_parts()
    malformed(jpeg(parts[:1] + parts[2:]), "jpeg.missing_dqt")
    malformed(jpeg(parts[:3] + parts[4:]), "jpeg.missing_dht")
    malformed(jpeg(parts[:4] + parts[5:]), "jpeg.missing_dht")
    malformed(jpeg([*parts[:1], seg(0xDB, b"\x00" + bytes(10)), *parts[2:]]), "jpeg.dqt_length")
    malformed(jpeg([*parts[:3], seg(0xC4, b"\x00" + bytes(16)), *parts[4:]]), "jpeg.dht")
    malformed(
        jpeg([*parts[:3], seg(0xC4, bytes([0, 5]) + bytes(15)), *parts[4:]]), "jpeg.dht_length"
    )
    malformed(jpeg([*parts[:3], seg(0xDD, b"\0"), *parts[3:]]), "jpeg.dri_length")


def test_jpeg_baseline_scan_parameters_and_component_coverage():
    parts = baseline_parts()
    parts[5] = sos(ss=1)
    malformed(jpeg(parts), "jpeg.baseline_scan_params")
    parts[5] = sos(((9, 0),))
    malformed(jpeg(parts), "jpeg.sos_component")
    parts[5] = sos(((1, 0x22),))
    malformed(jpeg(parts), "jpeg.sos_component")
    rgb = [SOI, DQT, sof(comps=RGB), DHT_DC, DHT_AC]
    malformed(jpeg([*rgb, sos(((1, 0),)), ENTROPY, EOI]), "jpeg.component_incomplete")
    twice = [*rgb, sos(((1, 0),)), ENTROPY, sos(((1, 0),)), ENTROPY]
    malformed(jpeg([*twice, EOI]), "jpeg.component_rescanned")
    big = [SOI, DQT, sof(comps=((1, 0x44, 0), (2, 0x11, 0), (3, 0x11, 0))), DHT_DC, DHT_AC]
    malformed(jpeg([*big, sos(((1, 0), (2, 0), (3, 0))), ENTROPY, EOI]), "jpeg.mcu_too_large")


def test_jpeg_progressive_scan_rules():
    def with_scan(index: int, scan: bytes) -> bytes:
        parts = progressive_parts()
        parts[index] = scan
        return jpeg(parts)

    assert check_raster_structure(jpeg(progressive_parts())).kind == "jpeg"
    malformed(with_scan(5, sos(ss=0, se=5, ah=0, al=1)), "jpeg.progressive_scan_params")
    malformed(with_scan(7, sos(ss=5, se=2, ah=0, al=1)), "jpeg.progressive_scan_params")
    malformed(with_scan(7, sos(ss=1, se=64, ah=0, al=1)), "jpeg.progressive_scan_params")
    malformed(with_scan(9, sos(ss=1, se=63, ah=3, al=0)), "jpeg.progressive_scan_params")
    malformed(with_scan(5, sos(ss=0, se=0, ah=0, al=14)), "jpeg.progressive_scan_params")
    rgb = progressive_parts()
    rgb[2] = sof(0xC2, comps=RGB)
    malformed(
        jpeg([*rgb[:5], sos(((1, 0), (2, 0)), 1, 63, 0, 1), ENTROPY, EOI]),
        "jpeg.progressive_scan_params",
    )
    dc_only = [*progressive_parts()[:7], EOI]
    malformed(jpeg(dc_only), "jpeg.component_incomplete")
    ac_only = progressive_parts()[:5] + progressive_parts()[7:9] + [EOI]
    malformed(jpeg(ac_only), "jpeg.component_incomplete")
    no_ac_table = progressive_parts()
    del no_ac_table[4]
    malformed(jpeg(no_ac_table), "jpeg.missing_dht")
    no_dc_table = progressive_parts()
    del no_dc_table[3]
    malformed(jpeg(no_dc_table), "jpeg.missing_dht")


def test_jpeg_entropy_stuffing_fill_and_restart_rules():
    def build(entropy: bytes, dri: int | None = None) -> bytes:
        parts = baseline_parts(entropy)
        if dri is not None:
            parts.insert(5, seg(0xDD, struct.pack(">H", dri)))
        return jpeg(parts)

    assert check_raster_structure(build(b"\x01\xff\x00\xff\x00\x02")).kind == "jpeg"
    malformed(build(b""), "jpeg.empty_scan")
    malformed(build(b"\x01\xff\xff\x02"), "jpeg.fill_bytes")
    malformed(build(b"\x01\xff\xd0\x02"), "jpeg.restart")  # restart without DRI
    malformed(build(b"\x01\xff\xd1\x02", 1), "jpeg.restart")  # wrong index
    malformed(build(b"\x01\xff\xd0\x02\xff\xd0\x03", 1), "jpeg.restart")  # repeated index
    assert check_raster_structure(build(b"\x01\xff\xd0\x02", 1)).kind == "jpeg"
    wrap = b"\x01" + b"".join(bytes([0xFF, 0xD0 + i % 8, 1]) for i in range(9))
    assert check_raster_structure(build(wrap, 1)).kind == "jpeg"
    # an unescaped marker inside entropy data ends the scan; a second SOF is then refused
    malformed(build(b"\x01" + sof()), "jpeg.second_sof")
    assert check_raster_structure(build(b"\x01\xff\xfe\x00\x02")).kind == "jpeg"  # COM ends scan


# --- WebP refusals -------------------------------------------------------------------------------


def test_webp_prefix_truncation_always_refuses():
    for data in (VALID_VP8, VALID_VP8L, VALID_VP8X, riff(vp8x(0x10), ALPH_COMPRESSED, vp8())):
        for i in range(12, len(data)):
            with pytest.raises(rs.RasterRefused):
                check_raster_structure(data[:i])


def test_webp_riff_size_and_trailing_payload():
    bigger = bytearray(VALID_VP8)
    bigger[4:8] = struct.pack("<I", len(VALID_VP8) - 7)
    malformed(bytes(bigger), "webp.riff_size")
    smaller = bytearray(VALID_VP8)
    smaller[4:8] = struct.pack("<I", len(VALID_VP8) - 9)
    malformed(bytes(smaller), "webp.riff_size")
    malformed(VALID_VP8 + b"\0\0", "webp.riff_size")
    malformed(VALID_VP8 + wchunk(b"EXIF", b"x"), "webp.riff_size")
    # trailing chunk with a consistent RIFF size is still refused after a simple image
    sized = riff(vp8(), wchunk(b"EXIF", b"x"))
    malformed(sized, "webp.unexpected_chunk")
    malformed(riff(vp8())[:19], "webp.truncated")


def test_webp_chunk_length_overflow_and_padding():
    inflated = bytearray(VALID_VP8)
    inflated[16:20] = struct.pack("<I", 0x7FFFFFFF)
    malformed(bytes(inflated), "webp.length_overflow")
    inflated[16:20] = struct.pack("<I", 0xFFFFFFFF)
    malformed(bytes(inflated), "webp.length_overflow")
    good = riff(vp8x(0x08), vp8(), wchunk(b"EXIF", b"odd"))
    bad_pad = good[:-1] + b"\x01"
    malformed(bad_pad, "webp.padding")
    no_pad = good[:-1]
    malformed(no_pad, "webp.riff_size")
    fixed = bytearray(no_pad)
    fixed[4:8] = struct.pack("<I", len(no_pad) - 8)
    malformed(bytes(fixed), "webp.length_overflow")


def test_webp_animation_flag_and_chunks_refused():
    refused(riff(vp8x(0x02), vp8()), Reason.ANIMATED, "webp.animation_flag")
    assert check_raster_structure(riff(vp8x(0x00), vp8())).kind == "webp"
    anim = wchunk(b"ANIM", bytes(6))
    anmf = wchunk(b"ANMF", bytes(16))
    refused(riff(vp8x(0), anim, vp8()), Reason.ANIMATED, "webp.animation_chunk")
    refused(riff(vp8x(0), vp8(), anmf), Reason.ANIMATED, "webp.animation_chunk")
    refused(riff(vp8x(0x02), anim, anmf), Reason.ANIMATED, "webp.animation_flag")
    refused(riff(anim, vp8()), Reason.ANIMATED, "webp.animation_chunk")
    refused(riff(vp8(), anmf), Reason.ANIMATED, "webp.animation_chunk")


def test_webp_canvas_and_bitstream_must_agree():
    assert check_raster_structure(riff(vp8x(0, 5, 7), vp8(5, 7))).width == 5
    malformed(riff(vp8x(0, 5, 7), vp8(5, 8)), "webp.canvas_mismatch")
    malformed(riff(vp8x(0, 6, 7), vp8(5, 7)), "webp.canvas_mismatch")
    malformed(riff(vp8x(0, 5, 7), vp8l(4, 7)), "webp.canvas_mismatch")


def test_webp_vp8x_layout_rules():
    malformed(riff(vp8x(), vp8x(), vp8()), "webp.unexpected_chunk")
    malformed(riff(vp8(), vp8x()), "webp.unexpected_chunk")
    malformed(riff(wchunk(b"VP8X", bytes(11)), vp8()), "webp.vp8x_length")
    malformed(riff(vp8x(0x01), vp8()), "webp.vp8x_reserved")
    malformed(riff(vp8x(0x80), vp8()), "webp.vp8x_reserved")
    malformed(riff(vp8x(reserved=b"\0\0\1"), vp8()), "webp.vp8x_reserved")
    malformed(riff(vp8x()), "webp.no_image")
    malformed(riff(vp8x(), vp8(), vp8()), "webp.second_image")
    malformed(riff(vp8x(), vp8(), vp8l()), "webp.second_image")
    refused(
        riff(vp8x(), wchunk(b"JUNK", b"x"), vp8()), Reason.UNSUPPORTED_VARIANT, "webp.unknown_chunk"
    )
    refused(riff(wchunk(b"JUNK", b"x"), vp8()), Reason.UNSUPPORTED_VARIANT, "webp.first_chunk")


def test_webp_alpha_rules():
    flag = 0x10
    assert check_raster_structure(riff(vp8x(flag), ALPH_COMPRESSED, vp8())).kind == "webp"
    malformed(riff(vp8x(0), ALPH_COMPRESSED, vp8()), "webp.chunk_without_flag")
    malformed(riff(vp8x(flag), ALPH_COMPRESSED, vp8l()), "webp.alph_with_vp8l")
    malformed(riff(vp8x(flag), vp8(), ALPH_COMPRESSED), "webp.chunk_order")
    malformed(riff(vp8x(flag), ALPH_COMPRESSED, ALPH_COMPRESSED, vp8()), "webp.duplicate_chunk")
    malformed(riff(vp8x(flag), wchunk(b"ALPH", b""), vp8()), "webp.alph_empty")
    malformed(riff(vp8x(flag), wchunk(b"ALPH", b"\x40"), vp8()), "webp.alph_header")
    malformed(riff(vp8x(flag), wchunk(b"ALPH", b"\x02"), vp8()), "webp.alph_header")
    malformed(riff(vp8x(flag), wchunk(b"ALPH", b"\x20"), vp8()), "webp.alph_header")
    raw_ok = wchunk(b"ALPH", b"\x00" + bytes(4))
    assert check_raster_structure(riff(vp8x(flag), raw_ok, vp8())).kind == "webp"
    malformed(riff(vp8x(flag), wchunk(b"ALPH", b"\x00" + bytes(3)), vp8()), "webp.alph_raw_length")
    malformed(riff(vp8(), ALPH_COMPRESSED), "webp.unexpected_chunk")


def test_webp_metadata_chunk_order_and_flags():
    icc, exif, xmp = wchunk(b"ICCP", b"i"), wchunk(b"EXIF", b"e"), wchunk(b"XMP ", b"x")
    assert check_raster_structure(riff(vp8x(0x20), icc, vp8())).kind == "webp"
    malformed(riff(vp8x(0), icc, vp8()), "webp.chunk_without_flag")
    malformed(riff(vp8x(0x20), vp8(), icc), "webp.chunk_order")
    malformed(riff(vp8x(0x08), exif, vp8()), "webp.chunk_order")
    malformed(riff(vp8x(0x04), xmp, vp8()), "webp.chunk_order")
    malformed(riff(vp8x(0x08), vp8(), exif, exif), "webp.duplicate_chunk")
    malformed(riff(vp8x(0x20 | 0x10), ALPH_COMPRESSED, icc, vp8()), "webp.chunk_order")
    assert check_raster_structure(riff(vp8x(0x20 | 0x10), icc, ALPH_COMPRESSED, vp8()))


def test_webp_bitstream_header_rules():
    assert check_raster_structure(VALID_VP8).kind == "webp"
    malformed(riff(vp8(start=b"\x9d\x01\x2b")), "webp.vp8_header")
    malformed(riff(vp8(tag=0x51)), "webp.vp8_frame_tag")  # inter frame
    malformed(riff(vp8(tag=0x40)), "webp.vp8_frame_tag")  # not shown
    malformed(riff(vp8(tag=0x50 | 4 << 1)), "webp.vp8_frame_tag")  # version 4
    malformed(riff(vp8(tag=(900 << 5) | 0x10)), "webp.vp8_frame_tag")  # partition overruns
    refused(riff(vp8(scale=1)), Reason.UNSUPPORTED_VARIANT, "webp.vp8_scaling")
    malformed(riff(wchunk(b"VP8 ", bytes(9))), "webp.vp8_header")
    malformed(riff(vp8l(sig=0x2E)), "webp.vp8l_header")
    refused(riff(vp8l(version=1)), Reason.UNSUPPORTED_VARIANT, "webp.vp8l_version")
    malformed(riff(wchunk(b"VP8L", bytes(4))), "webp.vp8l_header")
    malformed(riff(vp8(0, 2)), "dims.zero")


# --- format identity, suffix and non-raster inputs -----------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00",
        b"GIF87a" + bytes(20),
        b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        b"<?xml version='1.0'?><svg/>",
        b"<!doctype html><html></html>",
        b"plain text pretending to be a picture",
        b"BM" + bytes(60),
        b"II*\x00" + bytes(20),
        b"MM\x00*" + bytes(20),
        b"\x00\x00\x00\x18ftypheic" + bytes(20),
        b"\x00\x00\x00\x1cftypavif" + bytes(20),
        b"\x00\x00\x01\x00\x01\x00" + bytes(20),
        b"RIFF\x04\x00\x00\x00WAVE",
        b"\x89PNG",
        b"\xff\xd8",
        b"\xff",
    ],
)
def test_non_admitted_signatures_refused(data):
    with pytest.raises(rs.RasterRefused) as info:
        check_raster_structure(data)
    assert info.value.reason in (Reason.UNSUPPORTED_FORMAT, Reason.MALFORMED)


def test_gif_svg_html_text_have_the_unsupported_reason():
    for data in (b"GIF89a" + bytes(20), b"<svg/>", b"<html>", b"hello"):
        refused(data, Reason.UNSUPPORTED_FORMAT, "input.signature")


def test_result_depends_on_bytes_only_never_on_a_name():
    assert list(inspect.signature(check_raster_structure).parameters) == ["data"]
    # JPEG bytes are admitted as JPEG whatever a caller might have called them
    assert check_raster_structure(VALID_JPEG).kind == "jpeg"
    # text that merely starts like a name or extension is refused on content
    refused(b".png image.png", Reason.UNSUPPORTED_FORMAT, "input.signature")


@pytest.mark.parametrize("wrapper", [bytearray, memoryview])
def test_only_immutable_bytes_accepted(wrapper):
    refused(wrapper(VALID_PNG), Reason.NOT_BYTES, "input.not_bytes")
    refused("not bytes", Reason.NOT_BYTES, "input.not_bytes")


# --- structural-only limit -----------------------------------------------------------------------


def test_png_with_corrupt_deflate_body_is_structurally_admitted_but_unvalidated():
    corrupt = IDAT_OK[:2] + b"\xff" * 10  # valid zlib header, invalid deflate stream
    with pytest.raises(zlib.error):
        zlib.decompress(corrupt)
    data = png([ihdr(), chunk(b"IDAT", corrupt), chunk(b"IEND")])
    result = check_raster_structure(data)
    assert (result.kind, result.decodability) == ("png", "unvalidated")
    # the guard is the zlib header only, not the body
    malformed(
        png([ihdr(), chunk(b"IDAT", b"\x00\x00" + corrupt[2:]), chunk(b"IEND")]), "png.zlib_header"
    )


def test_png_size_mismatch_between_header_and_data_is_not_detected():
    big = png([ihdr(8192, 2441), chunk(b"IDAT", IDAT_OK), chunk(b"IEND")])
    result = check_raster_structure(big)
    assert (result.width, result.height, result.decodability) == (8192, 2441, "unvalidated")


def test_jpeg_and_webp_with_arbitrary_compressed_payload_are_admitted_unvalidated():
    junk = bytes(range(256)).replace(b"\xff", b"\x00") * 3
    assert check_raster_structure(jpeg(baseline_parts(junk))).decodability == "unvalidated"
    arbitrary = riff(wchunk(b"VP8L", b"\x2f" + struct.pack("<I", 1 | 1 << 14) + junk))
    assert check_raster_structure(arbitrary).decodability == "unvalidated"


def test_structure_is_frozen_and_refusal_messages_carry_no_input():
    result = check_raster_structure(VALID_PNG)
    with pytest.raises(AttributeError):
        result.width = 1  # type: ignore[misc]
    with pytest.raises(rs.RasterRefused) as info:
        check_raster_structure(b"SECRET-LOOKING-CONTENT")
    assert "SECRET" not in str(info.value)
    assert str(info.value) == "unsupported_format:input.signature"


# --- robustness and bounded work -----------------------------------------------------------------


def _flip_everywhere(data: bytes):
    for i in range(len(data)):
        for mask in (0x01, 0x80, 0xFF):
            yield data[:i] + bytes([data[i] ^ mask]) + data[i + 1 :]


def test_every_single_byte_mutation_returns_structure_or_closed_refusal():
    samples = [
        VALID_PNG,
        png(png_chunks(3, 8)),
        VALID_JPEG,
        jpeg(progressive_parts()),
        jpeg(
            [
                *baseline_parts(b"\x01\xff\x00\xff\xd0\x02")[:5],
                seg(221, b"\x00\x01"),
                sos(),
                b"\x01\xff\xd0\x02",
                EOI,
            ]
        ),
        VALID_VP8,
        VALID_VP8L,
        riff(vp8x(0x30), ALPH_COMPRESSED, vp8()),
    ]
    count = 0
    for sample in samples:
        for mutated in _flip_everywhere(sample):
            try:
                result = check_raster_structure(mutated)
            except rs.RasterRefused as exc:
                assert isinstance(exc.reason, Reason)
            else:
                assert result.decodability == "unvalidated"
            count += 1
    assert count > 1000


def test_large_stuffed_jpeg_scan_is_linear_and_copy_free():
    entropy = b"\xff\x00" * ((MAX_BYTES - 200) // 2)
    data = jpeg(baseline_parts(entropy))
    assert len(data) <= MAX_BYTES
    tracemalloc.start()
    start = time.perf_counter()
    try:
        assert check_raster_structure(data).kind == "jpeg"
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert time.perf_counter() - start < 5
    assert peak < 256 * 1024


def test_large_png_chunk_is_checked_without_copying_it():
    filler = MAX_BYTES - len(VALID_PNG) - 12
    data = png([ihdr(), chunk(b"IDAT", IDAT_OK), chunk(b"tEXt", b"\0" * filler), chunk(b"IEND")])
    tracemalloc.start()
    try:
        assert check_raster_structure(data).kind == "png"
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 256 * 1024


def test_adversarial_marker_dense_input_stays_within_unit_cap():
    spam = SOI + seg(0xFE, b"") * 20_000
    refused(spam, Reason.TOO_MANY_UNITS, "jpeg.segment_count")
    chunks = png([ihdr(), *[chunk(b"tEXt")] * 50_000])
    refused(chunks, Reason.TOO_MANY_UNITS, "png.chunk_count")


# --- dependency boundary -------------------------------------------------------------------------

ALLOWED_IMPORTS = {"__future__", "re", "struct", "zlib", "dataclasses", "enum"}


def test_module_imports_only_the_standard_library_subset_and_no_decoder():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= ALLOWED_IMPORTS
    assert not any(
        isinstance(n, ast.Call) and getattr(n.func, "id", "") == "open" for n in ast.walk(tree)
    )
    code = "\n".join(ast.unparse(n) for n in tree.body if not isinstance(n, ast.Expr))
    for forbidden in ("PIL", "hermes", "decompress", "pathlib", "os."):
        assert forbidden not in code


def test_fresh_interpreter_check_loads_no_imaging_module():
    script = (
        f"import sys; sys.path.insert(0, {str(SOURCE.parent)!r})\n"
        "import local_media_raster_structure as m\n"
        f"m.check_raster_structure({VALID_PNG!r}); m.check_raster_structure({VALID_JPEG!r})\n"
        f"m.check_raster_structure({VALID_VP8X!r})\n"
        "names = {'PIL', 'pillow_heif', 'hermes_cli', 'agent'}\n"
        "bad = [n for n in sys.modules if n.split('.')[0] in names]\n"
        "print(len(bad))\n"
    )
    out = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert out.stdout.strip() == "0"


# Byte-exact copies of the three synthetic 1x1 assets in the app test support file
# mobile/app/test/media/media_test_support.dart (onePixelPng / onePixelJpeg / onePixelWebp).
# No real user image. The Flutter codec accepting these was prior app evidence
# (image_media_loader_test.dart); this test only checks the host structural check admits them,
# not a cross-layer run.
APP_ONE_PIXEL_ASSETS = {
    "png": (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
        "2mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    ),
    "jpeg": (
        "/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAAB"
        "AAEAAKACAAQAAAABAAAAAaADAAQAAAABAAAAAQAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklN"
        "BCUAAAAAABDUHYzZjwCyBOmACZjs+EJ+/8AAEQgAAQABAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAAB"
        "AgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNi"
        "coIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SV"
        "lpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8B"
        "AAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXET"
        "IjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpz"
        "dHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm"
        "5+jp6vLz9PX29/j5+v/bAEMAAgICAgICAwICAwUDAwMFBgUFBQUGCAYGBgYGCAoICAgICAgKCgoKCgoKCgwMDAwM"
        "DA4ODg4ODw8PDw8PDw8PD//bAEMBAgICBAQEBwQEBxALCQsQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQ"
        "EBAQEBAQEBAQEBAQEBAQEBAQEP/dAAQAAf/aAAwDAQACEQMRAD8A7iiiiv8AQA+XP//Z"
    ),
    "webp": "UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==",
}


@pytest.mark.parametrize("kind", ["png", "jpeg", "webp"])
def test_app_synthetic_one_pixel_assets_are_admitted(kind):
    import base64

    result = check_raster_structure(base64.b64decode(APP_ONE_PIXEL_ASSETS[kind]))
    assert (result.kind, result.width, result.height) == (kind, 1, 1)
    assert result.decodability == "unvalidated"

#!/usr/bin/env python3
"""G3 raster structure prototype for host-local generated images (research, not product).

Test tooling: `server/hmp_plugin` never imports it. `check_raster_structure(data)` runs standard-
library structural checks on one bounded immutable `bytes` buffer. It never decompresses, never
decodes, never opens a path, and takes no file name or suffix, so a name cannot affect the result.

A pass means only "this buffer has the structure of an admitted static PNG/JPEG/WebP". It is NOT
proof the image decodes: entropy, zlib, Huffman and VP8/VP8L payloads are never inspected, so a
structurally valid file with corrupt compressed data is admitted and `Structure.decodability` stays
"unvalidated". The phone's bounded Flutter codec is the decoder and alone decides validity. It is
also not a claim that polyglot or ambiguous files are rejected in general; only the listed
trailing-byte, marker and chunk rules are enforced. Metadata chunks and segments pass through
unchanged and are not interpreted.

Policy (mirrors the accepted phone render policy): PNG/JPEG/WebP only, 1..8 MiB, each edge <= 8192,
<= 20,000,000 pixels, one static frame, at most 10,000 PNG chunks or JPEG segments/restart markers
(admitted WebP layouts have at most six chunks, so it needs no counter). A JPEG may also have at
most 64 scans: a conservative availability limit on decode cost, separate from the unit cap, not a
complete CPU or decompression-bomb guard. Header dimensions are declared, not decoded. Every refusal
is a closed `Reason` plus a fixed `detail` tag; neither ever contains input bytes. Work is linear in
the buffer: no byte slice larger than a PNG palette is copied and no loop revisits earlier bytes.
Concurrency is not part of this pure function.
"""

from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass, field
from enum import StrEnum

MAX_BYTES = 8 * 1024 * 1024
MAX_EDGE = 8192
MAX_PIXELS = 20_000_000
MAX_UNITS = 10_000
MAX_JPEG_SCANS = 64

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class Reason(StrEnum):
    NOT_BYTES = "not_bytes"
    EMPTY = "empty"
    TOO_LARGE = "too_large"
    UNSUPPORTED_FORMAT = "unsupported_format"
    UNSUPPORTED_VARIANT = "unsupported_variant"
    MALFORMED = "malformed"
    TRAILING_DATA = "trailing_data"
    DIMENSIONS = "dimensions"
    TOO_MANY_UNITS = "too_many_units"
    ANIMATED = "animated"


class RasterRefused(Exception):  # noqa: N818 - closed refusal, not an error class hierarchy
    def __init__(self, reason: Reason, detail: str) -> None:
        super().__init__(f"{reason.value}:{detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class Structure:
    kind: str
    width: int
    height: int
    decodability: str = "unvalidated"


def _refuse(reason: Reason, detail: str) -> RasterRefused:
    return RasterRefused(reason, detail)


def _bad(detail: str) -> RasterRefused:
    return RasterRefused(Reason.MALFORMED, detail)


def _check_dims(width: int, height: int) -> None:
    if width < 1 or height < 1:
        raise _bad("dims.zero")
    if width > MAX_EDGE or height > MAX_EDGE or width * height > MAX_PIXELS:
        raise _refuse(Reason.DIMENSIONS, "dims.over_limit")


# --- PNG -----------------------------------------------------------------------------------------

_PNG_DEPTHS = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
_PNG_ANIMATION = frozenset({b"acTL", b"fcTL", b"fdAT"})
_PNG_BEFORE_PLTE = frozenset(
    {b"cHRM", b"gAMA", b"iCCP", b"sBIT", b"sRGB", b"cICP", b"mDCV", b"cLLI"}
)
_PNG_AFTER_PLTE = frozenset({b"bKGD", b"hIST", b"tRNS"})
_PNG_BEFORE_IDAT = frozenset({b"pHYs", b"sPLT"})
_PNG_SINGLE = _PNG_BEFORE_PLTE | _PNG_AFTER_PLTE | frozenset({b"pHYs", b"tIME", b"eXIf"})


def _check_png(data: bytes) -> Structure:
    n = len(data)
    mv = memoryview(data)
    pos = len(PNG_SIGNATURE)
    units = 0
    width = height = color = depth = 0
    seen: set[bytes] = set()
    palette_entries = 0
    have_plte = have_idat = idat_over = False
    head = b""  # first two IDAT payload bytes, for the zlib header sanity check
    while True:
        if pos == n:
            raise _bad("png.no_iend")
        if n - pos < 12:
            raise _bad("png.truncated_chunk")
        units += 1
        if units > MAX_UNITS:
            raise _refuse(Reason.TOO_MANY_UNITS, "png.chunk_count")
        (length,) = struct.unpack_from(">I", data, pos)
        ctype = data[pos + 4 : pos + 8]
        if length > 0x7FFFFFFF or length > n - pos - 12:
            raise _bad("png.length_overflow")
        (crc,) = struct.unpack_from(">I", data, pos + 8 + length)
        if zlib.crc32(mv[pos + 4 : pos + 8 + length]) != crc:
            raise _bad("png.crc")
        if not ctype.isalpha() or ctype[2] & 0x20:
            raise _bad("png.chunk_type")
        body = pos + 8
        first = units == 1
        if first != (ctype == b"IHDR"):
            raise _bad("png.ihdr_order")
        if ctype in _PNG_ANIMATION:
            raise _refuse(Reason.ANIMATED, "png.animation_chunk")
        if ctype in _PNG_SINGLE:
            if ctype in seen:
                raise _bad("png.duplicate_chunk")
            seen.add(ctype)
        if ctype != b"IDAT" and have_idat:
            idat_over = True

        if ctype == b"IHDR":
            if length != 13:
                raise _bad("png.ihdr_length")
            width, height, depth, color, comp, filt, interlace = struct.unpack_from(
                ">IIBBBBB", data, body
            )
            if depth not in _PNG_DEPTHS.get(color, ()):
                raise _bad("png.ihdr_depth_color")
            if comp != 0 or filt != 0 or interlace not in (0, 1):
                raise _bad("png.ihdr_method")
            _check_dims(width, height)
        elif ctype == b"PLTE":
            if have_plte or have_idat or color in (0, 4) or (seen & _PNG_AFTER_PLTE):
                raise _bad("png.plte_order")
            if length == 0 or length % 3 or length > 768:
                raise _bad("png.plte_length")
            palette_entries = length // 3
            if color == 3 and palette_entries > 1 << depth:
                raise _bad("png.plte_too_large")
            have_plte = True
        elif ctype == b"IDAT":
            if idat_over:
                raise _bad("png.idat_not_contiguous")
            if color == 3 and not have_plte:
                raise _bad("png.indexed_without_plte")
            have_idat = True
            if len(head) < 2:
                head += data[body : body + min(2 - len(head), length)]
        elif ctype == b"IEND":
            if length != 0:
                raise _bad("png.iend_length")
            if not have_idat:
                raise _bad("png.no_idat")
            if pos + 12 != n:
                raise _refuse(Reason.TRAILING_DATA, "png.after_iend")
            break
        elif not ctype[0] & 0x20:
            raise _refuse(Reason.UNSUPPORTED_VARIANT, "png.unknown_critical")
        else:
            _check_png_ancillary(ctype, length, color, palette_entries, have_plte, have_idat)
        pos += 12 + length

    if len(head) < 2 or head[0] & 0x0F != 8 or head[0] >> 4 > 7 or head[1] & 0x20:
        raise _bad("png.zlib_header")
    if (head[0] << 8 | head[1]) % 31:
        raise _bad("png.zlib_header")
    return Structure("png", width, height)


def _check_png_ancillary(
    ctype: bytes,
    length: int,
    color: int,
    palette_entries: int,
    have_plte: bool,
    have_idat: bool,
) -> None:
    if have_idat and ctype in _PNG_BEFORE_PLTE | _PNG_AFTER_PLTE | _PNG_BEFORE_IDAT:
        raise _bad("png.ancillary_order")
    if have_plte and ctype in _PNG_BEFORE_PLTE:
        raise _bad("png.ancillary_order")
    if ctype == b"hIST" and not have_plte:
        raise _bad("png.hist_without_plte")
    if ctype == b"tRNS":
        expected = {0: 2, 2: 6}
        if color in (4, 6) or (color == 3 and not have_plte):
            raise _bad("png.trns_invalid")
        if color == 3:
            if not 1 <= length <= palette_entries:
                raise _bad("png.trns_length")
        elif length != expected[color]:
            raise _bad("png.trns_length")


# --- JPEG ----------------------------------------------------------------------------------------

# An 0xFF followed by a non-zero byte inside entropy data is a marker (or refused fill); 0xFF 0x00
# is a stuffed byte. One C-speed search per marker keeps the traversal linear.
_JPEG_MARKER = re.compile(rb"\xff[\x01-\xff]")
_SOF_ADMITTED = {0xC0: "baseline", 0xC2: "progressive"}
_JPEG_SEGMENTS = frozenset({0xC4, 0xDB, 0xDD, 0xDA, 0xFE, *_SOF_ADMITTED, *range(0xE0, 0xF0)})


@dataclass
class _Jpeg:
    mode: str = ""
    width: int = 0
    height: int = 0
    comps: dict[int, tuple[int, int, int]] = field(default_factory=dict)  # id -> (h, v, tq)
    quant: set[int] = field(default_factory=set)
    huff: set[tuple[int, int]] = field(default_factory=set)
    restart: int = 0
    scans: int = 0
    scanned: dict[int, set[str]] = field(default_factory=dict)


def _check_jpeg(data: bytes) -> Structure:
    n = len(data)
    st = _Jpeg()
    pos = 2
    units = 0
    while True:
        if pos + 2 > n or data[pos] != 0xFF:
            raise _bad("jpeg.marker_expected")
        marker = data[pos + 1]
        units += 1
        if units > MAX_UNITS:
            raise _refuse(Reason.TOO_MANY_UNITS, "jpeg.segment_count")
        if marker == 0xD9:
            if not st.mode or st.scans == 0:
                raise _bad("jpeg.eoi_without_scan")
            if pos + 2 != n:
                raise _refuse(Reason.TRAILING_DATA, "jpeg.after_eoi")
            break
        if marker not in _JPEG_SEGMENTS:
            if 0xC1 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                raise _refuse(Reason.UNSUPPORTED_VARIANT, "jpeg.unsupported_sof")
            raise _refuse(Reason.UNSUPPORTED_VARIANT, "jpeg.unsupported_marker")
        if pos + 4 > n:
            raise _bad("jpeg.truncated_segment")
        (length,) = struct.unpack_from(">H", data, pos + 2)
        end = pos + 2 + length
        if length < 2 or end > n:
            raise _bad("jpeg.segment_length")
        body = pos + 4
        if marker in _SOF_ADMITTED:
            _jpeg_sof(data, st, marker, body, end)
        elif marker == 0xDB:
            _jpeg_dqt(data, st, body, end)
        elif marker == 0xC4:
            _jpeg_dht(data, st, body, end)
        elif marker == 0xDD:
            if length != 4:
                raise _bad("jpeg.dri_length")
            (st.restart,) = struct.unpack_from(">H", data, body)
        elif marker == 0xDA:
            pos, units = _jpeg_scan(data, st, body, end, units)
            continue
        pos = end

    if any(marks != {"dc", "ac"} for marks in st.scanned.values()):
        raise _bad("jpeg.component_incomplete")
    return Structure("jpeg", st.width, st.height)


def _jpeg_sof(data: bytes, st: _Jpeg, marker: int, body: int, end: int) -> None:
    if st.mode:
        raise _bad("jpeg.second_sof")
    if st.scans:
        raise _bad("jpeg.sof_after_scan")
    if end - body < 6:
        raise _bad("jpeg.sof_length")
    precision, height, width, nf = struct.unpack_from(">BHHB", data, body)
    if precision != 8:
        raise _refuse(Reason.UNSUPPORTED_VARIANT, "jpeg.precision")
    if nf not in (1, 3):
        raise _refuse(Reason.UNSUPPORTED_VARIANT, "jpeg.components")  # includes CMYK (4)
    if end - body != 6 + 3 * nf:
        raise _bad("jpeg.sof_length")
    if height == 0:
        raise _bad("jpeg.height_zero")  # DNL-defined height is refused
    _check_dims(width, height)
    comps: dict[int, tuple[int, int, int]] = {}
    for i in range(nf):
        cid, hv, tq = struct.unpack_from(">BBB", data, body + 6 + 3 * i)
        h, v = hv >> 4, hv & 15
        if cid in comps or not (1 <= h <= 4 and 1 <= v <= 4) or tq > 3:
            raise _bad("jpeg.component")
        comps[cid] = (h, v, tq)
    st.mode = _SOF_ADMITTED[marker]
    st.width, st.height = width, height
    st.comps = comps
    st.scanned = {cid: set() for cid in comps}


def _jpeg_dqt(data: bytes, st: _Jpeg, pos: int, end: int) -> None:
    while pos < end:
        pq_tq = data[pos]
        pq, tq = pq_tq >> 4, pq_tq & 15
        if pq > 1 or tq > 3:
            raise _bad("jpeg.dqt")
        pos += 1 + 64 * (pq + 1)
        if pos > end:
            raise _bad("jpeg.dqt_length")
        st.quant.add(tq)
    if pos != end:
        raise _bad("jpeg.dqt_length")


def _jpeg_dht(data: bytes, st: _Jpeg, pos: int, end: int) -> None:
    while pos < end:
        if pos + 17 > end:
            raise _bad("jpeg.dht_length")
        tc_th = data[pos]
        tc, th = tc_th >> 4, tc_th & 15
        total = sum(data[pos + 1 : pos + 17])
        if tc > 1 or th > 3 or total > 256 or total == 0:
            raise _bad("jpeg.dht")
        pos += 17 + total
        if pos > end:
            raise _bad("jpeg.dht_length")
        st.huff.add((tc, th))
    if pos != end:
        raise _bad("jpeg.dht_length")


def _jpeg_scan(data: bytes, st: _Jpeg, body: int, end: int, units: int) -> tuple[int, int]:
    """Validate an SOS header, then walk its entropy data. Returns (next marker pos, units)."""
    if not st.mode:
        raise _bad("jpeg.scan_before_sof")
    if st.scans >= MAX_JPEG_SCANS:
        raise _refuse(Reason.TOO_MANY_UNITS, "jpeg.scan_count")
    if end == body:
        raise _bad("jpeg.sos_length")
    ns = data[body]
    if ns < 1 or ns > len(st.comps) or end - body != 4 + 2 * ns:
        raise _bad("jpeg.sos_length")
    ss, se, ahl = struct.unpack_from(">BBB", data, end - 3)
    ah, al = ahl >> 4, ahl & 15
    baseline = st.mode == "baseline"
    ids: list[int] = []
    tables: list[tuple[int, int]] = []
    for i in range(ns):
        cid, tdta = struct.unpack_from(">BB", data, body + 1 + 2 * i)
        td, ta = tdta >> 4, tdta & 15
        if cid not in st.comps or cid in ids or max(td, ta) > (1 if baseline else 3):
            raise _bad("jpeg.sos_component")
        ids.append(cid)
        tables.append((td, ta))
    if ns > 1 and sum(st.comps[c][0] * st.comps[c][1] for c in ids) > 10:
        raise _bad("jpeg.mcu_too_large")
    if baseline:
        if (ss, se, ah, al) != (0, 63, 0, 0):
            raise _bad("jpeg.baseline_scan_params")
        kinds, need_dc, need_ac = "dc+ac", True, True
    else:
        if ah > 13 or al > 13 or se > 63 or (ah and ah != al + 1):
            raise _bad("jpeg.progressive_scan_params")
        if ss == 0:
            if se != 0:
                raise _bad("jpeg.progressive_scan_params")
            kinds, need_dc, need_ac = "dc", ah == 0, False
        else:
            if se < ss or ns != 1:
                raise _bad("jpeg.progressive_scan_params")
            kinds, need_dc, need_ac = "ac", False, True
    for cid, (td, ta) in zip(ids, tables, strict=True):
        if st.comps[cid][2] not in st.quant:
            raise _bad("jpeg.missing_dqt")
        if (need_dc and (0, td) not in st.huff) or (need_ac and (1, ta) not in st.huff):
            raise _bad("jpeg.missing_dht")
        marks = st.scanned[cid]
        if baseline and marks:
            raise _bad("jpeg.component_rescanned")
        if ah == 0:
            marks.update(kinds.split("+"))
    st.scans += 1

    pos = end
    expected_rst = 0
    first = True
    while True:
        m = _JPEG_MARKER.search(data, pos)
        if m is None:
            raise _bad("jpeg.no_eoi")
        if first and m.start() == pos:
            raise _bad("jpeg.empty_scan")
        first = False
        marker = data[m.start() + 1]
        if marker == 0xFF:
            raise _bad("jpeg.fill_bytes")
        if 0xD0 <= marker <= 0xD7:
            if not st.restart or marker != 0xD0 + expected_rst % 8:
                raise _bad("jpeg.restart")
            expected_rst += 1
            units += 1
            if units > MAX_UNITS:
                raise _refuse(Reason.TOO_MANY_UNITS, "jpeg.segment_count")
            pos = m.end()
            continue
        return m.start(), units


# --- WebP ----------------------------------------------------------------------------------------

_WEBP_ANIMATION = frozenset({b"ANIM", b"ANMF"})


def _webp_vp8(data: bytes, body: int, size: int) -> tuple[int, int]:
    if size < 10 or data[body + 3 : body + 6] != b"\x9d\x01\x2a":
        raise _bad("webp.vp8_header")
    tag = data[body] | data[body + 1] << 8 | data[body + 2] << 16
    if tag & 1 or (tag >> 1) & 7 > 3 or not tag & 0x10 or tag >> 5 > size - 10:
        raise _bad("webp.vp8_frame_tag")  # not a shown key frame, or partition overruns payload
    (w, h) = struct.unpack_from("<HH", data, body + 6)
    if w >> 14 or h >> 14:
        raise _refuse(Reason.UNSUPPORTED_VARIANT, "webp.vp8_scaling")
    return w, h


def _webp_vp8l(data: bytes, body: int, size: int) -> tuple[int, int]:
    if size < 5 or data[body] != 0x2F:
        raise _bad("webp.vp8l_header")
    (bits,) = struct.unpack_from("<I", data, body + 1)
    if bits >> 29:
        raise _refuse(Reason.UNSUPPORTED_VARIANT, "webp.vp8l_version")
    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1


def _webp_alph(data: bytes, body: int, size: int, width: int, height: int) -> None:
    if size < 1:
        raise _bad("webp.alph_empty")
    flags = data[body]
    if flags & 0xC0 or (flags >> 4) & 3 > 1 or flags & 3 > 1:
        raise _bad("webp.alph_header")
    if flags & 3 == 0 and size != 1 + width * height:
        raise _bad("webp.alph_raw_length")


def _check_webp(data: bytes) -> Structure:
    n = len(data)
    if n < 20:
        raise _bad("webp.truncated")
    (riff_size,) = struct.unpack_from("<I", data, 4)
    if riff_size != n - 8:
        raise _bad("webp.riff_size")
    pos = 12
    units = 0
    extended = False
    flags = 0
    canvas: tuple[int, int] | None = None
    image: tuple[int, int] | None = None
    seen: set[bytes] = set()
    alpha_seen = False
    while pos < n:
        if n - pos < 8:
            raise _bad("webp.truncated_chunk")
        units += 1
        fourcc = data[pos : pos + 4]
        (size,) = struct.unpack_from("<I", data, pos + 4)
        body = pos + 8
        end = body + size + (size & 1)
        if end > n:
            raise _bad("webp.length_overflow")
        if size & 1 and data[end - 1] != 0:
            raise _bad("webp.padding")
        if fourcc in _WEBP_ANIMATION:
            raise _refuse(Reason.ANIMATED, "webp.animation_chunk")
        if units == 1:
            extended = fourcc == b"VP8X"
            if extended:
                flags, canvas = _webp_vp8x(data, body, size)
            elif fourcc not in (b"VP8 ", b"VP8L"):
                raise _refuse(Reason.UNSUPPORTED_VARIANT, "webp.first_chunk")
        if fourcc in (b"VP8 ", b"VP8L"):
            if image:
                raise _bad("webp.second_image")
            image = (_webp_vp8 if fourcc == b"VP8 " else _webp_vp8l)(data, body, size)
            if fourcc == b"VP8L" and alpha_seen:
                raise _bad("webp.alph_with_vp8l")
        elif not extended or fourcc == b"VP8X":
            if units != 1:
                raise _bad("webp.unexpected_chunk")
        elif fourcc in (b"ICCP", b"ALPH", b"EXIF", b"XMP "):
            _webp_extended_chunk(data, fourcc, body, size, flags, canvas, image, seen)
            alpha_seen = alpha_seen or fourcc == b"ALPH"
        else:
            raise _refuse(Reason.UNSUPPORTED_VARIANT, "webp.unknown_chunk")
        pos = end
    if image is None:
        raise _bad("webp.no_image")
    if not extended and units != 1:
        raise _bad("webp.unexpected_chunk")
    if extended and canvas != image:
        raise _bad("webp.canvas_mismatch")
    _check_dims(*image)
    return Structure("webp", *image)


def _webp_vp8x(data: bytes, body: int, size: int) -> tuple[int, tuple[int, int]]:
    if size != 10:
        raise _bad("webp.vp8x_length")
    flags = data[body]
    if flags & 0x02:
        raise _refuse(Reason.ANIMATED, "webp.animation_flag")
    if flags & 0xC1 or data[body + 1 : body + 4] != b"\0\0\0":
        raise _bad("webp.vp8x_reserved")
    w = int.from_bytes(data[body + 4 : body + 7], "little") + 1
    h = int.from_bytes(data[body + 7 : body + 10], "little") + 1
    _check_dims(w, h)
    return flags, (w, h)


def _webp_extended_chunk(
    data: bytes,
    fourcc: bytes,
    body: int,
    size: int,
    flags: int,
    canvas: tuple[int, int] | None,
    image: tuple[int, int] | None,
    seen: set[bytes],
) -> None:
    if fourcc in seen:
        raise _bad("webp.duplicate_chunk")
    seen.add(fourcc)
    needed_flag = {b"ICCP": 0x20, b"ALPH": 0x10, b"EXIF": 0x08, b"XMP ": 0x04}[fourcc]
    if not flags & needed_flag:
        raise _bad("webp.chunk_without_flag")
    if fourcc in (b"ICCP", b"ALPH") and image is not None:
        raise _bad("webp.chunk_order")
    if fourcc in (b"EXIF", b"XMP ") and image is None:
        raise _bad("webp.chunk_order")
    if fourcc == b"ALPH":
        if canvas is None:
            raise _bad("webp.chunk_order")
        _webp_alph(data, body, size, *canvas)
    if fourcc == b"ICCP" and b"ALPH" in seen:
        raise _bad("webp.chunk_order")


# --- entry point ---------------------------------------------------------------------------------


def check_raster_structure(data: bytes) -> Structure:
    """Return the admitted structure of `data` or raise `RasterRefused` (closed reason, detail)."""
    if type(data) is not bytes:
        raise _refuse(Reason.NOT_BYTES, "input.not_bytes")
    if not data:
        raise _refuse(Reason.EMPTY, "input.empty")
    if len(data) > MAX_BYTES:
        raise _refuse(Reason.TOO_LARGE, "input.over_8_mib")
    if data.startswith(PNG_SIGNATURE):
        return _check_png(data)
    if data.startswith(b"\xff\xd8\xff"):
        return _check_jpeg(data)
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return _check_webp(data)
    raise _refuse(Reason.UNSUPPORTED_FORMAT, "input.signature")

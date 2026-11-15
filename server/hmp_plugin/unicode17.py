"""Pure, pinned Unicode 17 NFC and extended grapheme operations for BI1.

Generated tables have no runtime file dependencies. Unicode data notice is in
UNICODE_LICENSE.txt. This module has no process-global mutable cache.
"""

from __future__ import annotations

from bisect import bisect_right
from types import MappingProxyType

from . import unicode17_data as _data

_DECOMP = MappingProxyType(dict(_data.CANONICAL_DECOMP))
_CCC = MappingProxyType(dict(_data.CCC))
_COMPOSE = MappingProxyType(dict(_data.COMPOSE))
_DROP = _data.DROP_RANGES
_WHITE = _data.WHITE_SPACE_RANGES
_GCB = _data.GCB
_INCB = _data.INCB
_EP = _data.EP
_DROP_STARTS = tuple(row[0] for row in _DROP)
_WHITE_STARTS = tuple(row[0] for row in _WHITE)
_GCB_STARTS = tuple(row[0] for row in _GCB)
_INCB_STARTS = tuple(row[0] for row in _INCB)
_EP_STARTS = tuple(row[0] for row in _EP)
_MAX_RAW = 4096
_MAX_NFC = 16384


def _limit(text: str, max_scalars: int, absolute: int) -> None:
    if type(text) is not str or type(max_scalars) is not int or not 1 <= max_scalars <= _MAX_RAW:
        raise ValueError("Unicode 17 input contract")
    if len(text) > min(max_scalars, absolute):
        raise ValueError("Unicode 17 scalar cap")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
        raise ValueError("Unicode 17 scalar required")


def _lookup(rows: tuple[tuple[int, ...], ...], starts: tuple[int, ...], cp: int) -> int:
    i = bisect_right(starts, cp) - 1
    if i >= 0 and cp <= rows[i][1]:
        return rows[i][2]
    return 0


def _member(rows: tuple[tuple[int, int], ...], starts: tuple[int, ...], cp: int) -> bool:
    i = bisect_right(starts, cp) - 1
    return i >= 0 and cp <= rows[i][1]


def category_drop17(cp: int) -> bool:
    if type(cp) is not int or not 0 <= cp <= 0x10FFFF:
        raise ValueError("Unicode 17 code point")
    return _member(_DROP, _DROP_STARTS, cp)


def white_space17(cp: int) -> bool:
    if type(cp) is not int or not 0 <= cp <= 0x10FFFF:
        raise ValueError("Unicode 17 code point")
    return _member(_WHITE, _WHITE_STARTS, cp)


def _canonical(cp: int) -> tuple[int, ...]:
    # Algorithmic Hangul decomposition, inclusive through U+D7A3 only.
    if 0xAC00 <= cp <= 0xD7A3:
        syllable = cp - 0xAC00
        if syllable % 28:
            return (
                0x1100 + syllable // 588,
                0x1161 + (syllable % 588) // 28,
                0x11A7 + syllable % 28,
            )
        return (0x1100 + syllable // 588, 0x1161 + (syllable % 588) // 28)
    return _DECOMP.get(cp, (cp,))


def _composite(a: int, b: int) -> int | None:
    if 0x1100 <= a <= 0x1112 and 0x1161 <= b <= 0x1175:
        return 0xAC00 + ((a - 0x1100) * 21 + b - 0x1161) * 28
    if 0xAC00 <= a <= 0xD7A3 and (a - 0xAC00) % 28 == 0 and 0x11A8 <= b <= 0x11C2:
        return a + b - 0x11A7
    return _COMPOSE.get((a << 21) | b)


def nfc17(text: str, *, max_scalars: int) -> str:
    """NFC under the pinned Unicode 17 data; input <=4096, output <=16384."""
    _limit(text, max_scalars, _MAX_RAW)
    ordered: list[int] = []
    segment: list[int] = []

    def flush() -> None:
        if not segment:
            return
        if _CCC.get(segment[0], 0) == 0:
            ordered.append(segment[0])
            ordered.extend(sorted(segment[1:], key=lambda cp: _CCC.get(cp, 0)))
        else:
            ordered.extend(sorted(segment, key=lambda cp: _CCC.get(cp, 0)))
        segment.clear()

    count = 0
    for ch in text:
        for cp in _canonical(ord(ch)):
            count += 1
            if count > _MAX_NFC:
                raise ValueError("Unicode 17 normalization output cap")
            if _CCC.get(cp, 0) == 0:
                flush()
            segment.append(cp)
    flush()
    result: list[int] = []
    starter = -1
    last_cc = 0
    for cp in ordered:
        cc = _CCC.get(cp, 0)
        composed = _composite(result[starter], cp) if starter >= 0 else None
        if composed is not None and (last_cc < cc or last_cc == 0):
            result[starter] = composed
            continue
        if cc == 0:
            starter = len(result)
        result.append(cp)
        last_cc = cc
    return "".join(chr(cp) for cp in result)


def grapheme_boundaries17(text: str, *, max_scalars: int) -> tuple[int, ...]:
    """Extended-grapheme boundaries as Python code-point offsets."""
    _limit(text, max_scalars, _MAX_RAW)
    out = [0]
    previous = 0
    regional_run = 0
    indic_state = 0
    ep_suffix = False
    zwj_ep = False
    for pos, ch in enumerate(text):
        cp = ord(ch)
        current = _lookup(_GCB, _GCB_STARTS, cp)
        indic = _lookup(_INCB, _INCB_STARTS, cp)
        pictographic = _lookup(_EP, _EP_STARTS, cp) == 1
        if pos:
            if previous == 1 and current == 2:  # GB3
                breaks = False
            elif previous in (1, 2, 3) or current in (1, 2, 3):  # GB4/5
                breaks = True
            elif (
                (previous == 9 and current in (9, 10, 12, 13))  # GB6
                or (previous in (12, 10) and current in (10, 11))  # GB7
                or (previous in (13, 11) and current == 11)  # GB8
                or current in (4, 5, 8)  # GB9/GB9a
                or previous == 7  # GB9b
                or (indic == 1 and indic_state == 2)  # GB9c
                or (previous == 5 and zwj_ep and pictographic)  # GB11
                or (previous == 6 and current == 6 and regional_run % 2)  # GB12/GB13
            ):  # GB6..GB13, in normative order
                breaks = False
            else:
                breaks = True
            if breaks:
                out.append(pos)
        regional_run = regional_run + 1 if current == 6 else 0
        if indic == 1:
            indic_state = 1
        elif indic == 2:
            if indic_state:
                indic_state = 2
        elif indic != 3:
            indic_state = 0
        zwj_ep = current == 5 and ep_suffix
        ep_suffix = pictographic or (current == 4 and ep_suffix)
        previous = current
    if text:
        out.append(len(text))
    return tuple(out)

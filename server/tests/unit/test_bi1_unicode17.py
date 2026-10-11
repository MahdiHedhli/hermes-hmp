"""Pinned Unicode 17 BI1 provider vectors; capability and routes remain off."""

import hashlib
import os
import stat
from pathlib import Path

import pytest

from hmp_plugin import presentation, unicode17

DATA = Path(__file__).resolve().parents[1] / "data"
NORM_SIZE = 2_827_429
NORM_SHA = "5019ffd530751a741900c849c0e010332f142a3612234639bd200b82138a87db"
BREAK_SIZE = 126_570
BREAK_SHA = "e2d134d2c52919bace503ebb6a551c1855fe1a1faec18478c78fff254a1793ec"


def _official_rows(name: str, size: int, digest: str) -> list[str]:
    assert name in {"NormalizationTest-17.0.0.txt", "GraphemeBreakTest-17.0.0.txt"}
    fd = os.open(DATA / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        stream = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with stream:
        metadata = os.fstat(stream.fileno())
        assert stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
        assert metadata.st_size == size
        body = stream.read(size + 1)
        assert len(body) == size and hashlib.sha256(body).hexdigest() == digest
    return body.decode("utf-8").splitlines()


def _scalars(field: str) -> str:
    return "".join(chr(int(value, 16)) for value in field.split())


def test_normalization_official_20034_by_five():
    count = 0
    for row in _official_rows("NormalizationTest-17.0.0.txt", NORM_SIZE, NORM_SHA):
        raw = row.split("#", 1)[0].strip()
        if not raw or raw.startswith("@"):
            continue
        fields = raw.split(";")
        assert len(fields) == 6 and fields[-1] == ""
        columns = tuple(_scalars(field) for field in fields[:5])
        for original, expected in zip(columns, (columns[1],) * 3 + (columns[3],) * 2, strict=True):
            assert unicode17.nfc17(original, max_scalars=4096) == expected
        count += 1
    assert count == 20_034


def test_extended_grapheme_official_766():
    count = 0
    for row in _official_rows("GraphemeBreakTest-17.0.0.txt", BREAK_SIZE, BREAK_SHA):
        raw = row.split("#", 1)[0].strip()
        if not raw:
            continue
        tokens = raw.split()
        points = []
        expected = []
        for index, token in enumerate(tokens):
            if index % 2:
                points.append(int(token, 16))
            elif token == "÷":
                expected.append(len(points))
            else:
                assert token == "\u00d7"
        text = "".join(chr(cp) for cp in points)
        assert unicode17.grapheme_boundaries17(text, max_scalars=4096) == tuple(expected)
        count += 1
    assert count == 766


@pytest.mark.parametrize("bad", (0, -1, 4097, True, 1.5, "4096"))
def test_scalar_limit_type_and_range_refuses(bad):
    with pytest.raises(ValueError):
        unicode17.nfc17("a", max_scalars=bad)
    with pytest.raises(ValueError):
        unicode17.grapheme_boundaries17("a", max_scalars=bad)


def test_input_output_bounds_and_scalar_validation():
    assert len(unicode17.nfc17("a" * 4096, max_scalars=4096)) == 4096
    with pytest.raises(ValueError):
        unicode17.nfc17("a" * 4097, max_scalars=4096)
    with pytest.raises(ValueError):
        unicode17.grapheme_boundaries17("a" * 4097, max_scalars=4096)
    with pytest.raises(ValueError):
        unicode17.nfc17("\ud800", max_scalars=1)
    with pytest.raises(ValueError):
        unicode17.grapheme_boundaries17("\udfff", max_scalars=1)


def test_hangul_boundary_and_equal_class_blocking():
    assert unicode17.nfc17("\u1100\u1161", max_scalars=2) == "\uac00"
    assert unicode17.nfc17("\uac00\u11a8", max_scalars=2) == "\uac01"
    for cp in (0xD7A3, 0xD7A4, 0xD7A5):
        text = chr(cp)
        assert unicode17.nfc17(text, max_scalars=1) == text
    assert unicode17.nfc17("\u0308\u0301", max_scalars=2) == "\u0308\u0301"


def test_unassigned_and_formatting_policy_for_host_titles():
    assert presentation._name(" A\u0301 ") == "Á"
    assert presentation._name("\u0600س") == "\u0600س"
    assert presentation._name("می\u200cروم") == "می\u200cروم"
    assert presentation._name("👩‍👩‍👧‍👦") == "👩‍👩‍👧‍👦"
    assert presentation._name("a\u202e") == "a"
    assert presentation._name("a\u00ad") == "a"
    assert presentation._name("\ud800A") == "A"
    assert presentation._name("a" * 257) is None


def test_tables_have_no_mutable_global_cache():
    with pytest.raises(TypeError):
        unicode17._CCC[0x301] = 0
    assert isinstance(unicode17._GCB, tuple)
    assert isinstance(unicode17._INCB, tuple)
    assert isinstance(unicode17._EP, tuple)


def test_presentation_revision_excludes_observation_and_avatar():
    common = {
        "iid": "a" * 52,
        "profile": "default",
        "bot_title": " A\u0301 ",
        "profile_display_name": None,
        "canonical_fallback": "Fallback",
        "shape": None,
        "color": None,
        "custom": None,
    }
    first = presentation.project_presentation(**common, avatar=None, observed_at=1)
    second = presentation.project_presentation(
        **common,
        avatar={"revision": "0" * 64, "mime": "image/png", "bytes": 42, "width": 1, "height": 1},
        observed_at=2,
    )
    assert first["display_name"] == second["display_name"] == "Á"
    assert first["metadata_revision"] == second["metadata_revision"]
    assert first["avatar"] is None and second["avatar"] is not None
    changed = presentation.project_presentation(
        **{**common, "bot_title": "Different"}, avatar=None, observed_at=1
    )
    assert changed["metadata_revision"] != first["metadata_revision"]

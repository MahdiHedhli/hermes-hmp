"""BI1 pure presentation projection. No route, filesystem read, or feature enablement.

The caller must separately prove current authorization and supply scalar values from
an independently bounded profile reader. The avatar descriptor must come from the
fixed-file reader; validating its shape here does not grant that authority.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from .unicode17 import category_drop17, grapheme_boundaries17, nfc17, white_space17

DOMAIN = b"HMP-BI1-META-V1\0"
MAX_SOURCE_CODEPOINTS = 4096
MAX_NAME_GRAPHEMES = 80
MAX_NAME_BYTES = 256
MAX_RESPONSE_BYTES = 4096
CLASSIC_SHAPES = frozenset({"circle", "squircle", "pill", "triangle", "hexagon", "cloud", "drop"})
BLOB_KINDS = frozenset(
    {"round", "organic", "boxy", "capsule", "nub", "cloud", "droplet", "hexagon", "sun", "triangle"}
)
MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})
PROFILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)
IID = re.compile(r"[a-z2-7]{52}\Z", re.ASCII)
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z", re.ASCII)
BLOB = re.compile(r"blobatar(?::([a-z0-9]{0,32})(?::([a-z]+))?)?\Z", re.ASCII)
# Unicode 17 PropList.txt Bidi_Control, exactly twelve code points. These
# change bidirectional display order without appearing in the title itself.
BIDI_CONTROLS = frozenset(
    "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
)
# Individual zero-width display commands. Soft hyphen and zero-width space
# can make distinct titles look the same; word joiner/BOM have no visible
# glyph, and the invisible math operators/language tag are not title text.
# This is an explicit UI policy, not a decision about every Cf character.
DISPLAY_CONTROLS = frozenset("\u00ad\u200b\u2060\u2061\u2062\u2063\u2064\ufeff\U000e0001")
JOINERS = frozenset({"\u200c", "\u200d"})
TAG_START = 0xE0020
TAG_END = 0xE007F
EMOJI_TAG = re.compile(r"\U0001f3f4[\U000e0061-\U000e007a]{1,32}\U000e007f\Z")


class PresentationUnavailableError(ValueError):
    """This optional read projection cannot be represented safely."""


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise PresentationUnavailableError(reason)


def _clusters(text: str) -> list[str]:
    """Exact Unicode 17 clusters; this input already passed the 256-byte cap."""
    try:
        boundaries = grapheme_boundaries17(text, max_scalars=256)
    except ValueError as exc:
        raise PresentationUnavailableError("grapheme input contract") from exc
    clusters = [text[boundaries[i] : boundaries[i + 1]] for i in range(len(boundaries) - 1)]
    _need("".join(clusters) == text, "grapheme segmentation incomplete")
    return clusters


def _strip_white17(text: str) -> str:
    start = 0
    end = len(text)
    while start < end and white_space17(ord(text[start])):
        start += 1
    while end > start and white_space17(ord(text[end - 1])):
        end -= 1
    return text[start:end]


def _name(value: object) -> str | None:
    if type(value) is not str or len(value) > MAX_SOURCE_CODEPOINTS:
        return None
    # Remove only the declared bidi and invisible-display controls. Other
    # format characters, including Arabic signs, joiners and emoji tags,
    # survive for contextual validation below. Cn is retained under the
    # exact Unicode 17 table and is never reclassified by host stdlib data.
    kept = "".join(
        ch
        for ch in value
        if not category_drop17(ord(ch)) and ch not in BIDI_CONTROLS and ch not in DISPLAY_CONTROLS
    )
    try:
        text = _strip_white17(nfc17(kept, max_scalars=MAX_SOURCE_CODEPOINTS))
    except ValueError:
        return None
    if not text or len(text.encode("utf-8")) > MAX_NAME_BYTES:
        return None
    clusters = _clusters(text)
    for index, ch in enumerate(text):
        if ch in JOINERS and (
            index == 0
            or index + 1 == len(text)
            or white_space17(ord(text[index - 1]))
            or white_space17(ord(text[index + 1]))
            or text[index - 1] in JOINERS
            or text[index + 1] in JOINERS
        ):
            return None
    for cluster in clusters:
        if (
            any(TAG_START <= ord(ch) <= TAG_END for ch in cluster)
            and EMOJI_TAG.fullmatch(cluster) is None
        ):
            return None
    return text if len(clusters) <= MAX_NAME_GRAPHEMES else None


def _iid(value: object) -> str:
    _need(type(value) is str and IID.fullmatch(value) is not None, "invalid iid")
    try:
        raw = base64.b32decode(value.upper() + "====")
    except binascii.Error as exc:
        raise PresentationUnavailableError("noncanonical iid") from exc
    _need(
        len(raw) == 32 and base64.b32encode(raw).decode("ascii").rstrip("=").lower() == value,
        "noncanonical iid",
    )
    return value


def _profile(value: object) -> str:
    _need(type(value) is str and PROFILE.fullmatch(value) is not None, "invalid profile")
    return value


def _character(
    profile: str, shape: object, color: object, custom: object
) -> dict[str, object] | None:
    if custom is not None and type(custom) is not bool:
        return None
    if shape is not None and (type(shape) is not str or len(shape) > 128):
        return None
    if color is not None and (type(color) is not str or len(color) > 64):
        return None
    if profile == "default" and custom is not True:
        return {"version": 1, "shape": "squircle", "color": "#8b5cf6", "custom": None}
    if type(shape) is str and shape in CLASSIC_SHAPES and type(color) is str:
        if COLOR.fullmatch(color) is not None:
            return {"version": 1, "shape": shape, "color": color.lower(), "custom": None}
        return None
    if type(shape) is str:
        match = BLOB.fullmatch(shape)
        if match is not None and (match[2] is None or match[2] in BLOB_KINDS):
            return {
                "version": 2,
                "shape": "blobatar",
                "color": None,
                "custom": {"seed": match[1] or "", "kind": match[2]},
            }
    return None


def _avatar(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    _need(
        type(value) is dict and set(value) == {"revision", "mime", "bytes", "width", "height"},
        "avatar schema",
    )
    revision = value["revision"]
    _need(type(revision) is str and HEX64.fullmatch(revision) is not None, "avatar revision")
    _need(type(value["mime"]) is str and value["mime"] in MIMES, "avatar mime")
    for key in ("bytes", "width", "height"):
        _need(type(value[key]) is int, "avatar numeric type")
    _need(0 < value["bytes"] <= 2_000_000, "avatar byte cap")
    _need(0 < value["width"] <= 1024 and 0 < value["height"] <= 1024, "avatar dimension cap")
    _need(value["width"] * value["height"] <= 1_048_576, "avatar pixel cap")
    return dict(value)


def _canonical_metadata(fields: Mapping[str, object]) -> bytes:
    _need(
        set(fields) == {"version", "iid", "profile", "display_name", "name_source", "character"},
        "metadata revision field set",
    )
    _need(type(fields["version"]) is int and fields["version"] == 1, "metadata version")
    _iid(fields["iid"])
    _profile(fields["profile"])
    name = fields["display_name"]
    _need(type(name) is str and _name(name) == name, "metadata display name")
    _need(
        type(fields["name_source"]) is str
        and fields["name_source"] in {"bot_title", "profile_display_name", "canonical_fallback"},
        "metadata name source",
    )
    character = fields["character"]
    if character is not None:
        _need(
            type(character) is dict and set(character) == {"version", "shape", "color", "custom"},
            "metadata character schema",
        )
        version = character["version"]
        if type(version) is int and version == 1:
            _need(
                type(character["shape"]) is str
                and character["shape"] in CLASSIC_SHAPES
                and type(character["color"]) is str
                and COLOR.fullmatch(character["color"]) is not None
                and character["color"] == character["color"].lower()
                and character["custom"] is None,
                "metadata classic character",
            )
        elif type(version) is int and version == 2:
            custom = character["custom"]
            _need(
                type(character["shape"]) is str
                and character["shape"] == "blobatar"
                and character["color"] is None
                and type(custom) is dict
                and set(custom) == {"seed", "kind"},
                "metadata blobatar schema",
            )
            seed = custom["seed"]
            kind = custom["kind"]
            _need(
                type(seed) is str
                and len(seed) <= 32
                and re.fullmatch(r"[a-z0-9]*", seed, re.ASCII) is not None
                and (kind is None or (type(kind) is str and kind in BLOB_KINDS)),
                "metadata blobatar fields",
            )
        else:
            raise PresentationUnavailableError("metadata character version")
    return json.dumps(
        fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def metadata_revision(fields: Mapping[str, object]) -> str:
    """Hash only the six closed fields; avatar and observation time never enter."""
    return hashlib.sha256(DOMAIN + _canonical_metadata(fields)).hexdigest()


def project_presentation(
    *,
    iid: object,
    profile: object,
    bot_title: object,
    profile_display_name: object,
    canonical_fallback: object,
    shape: object,
    color: object,
    custom: object,
    avatar: object,
    observed_at: object,
) -> dict[str, Any]:
    """Project reviewed scalar inputs; does not read YAML or authenticate a caller."""
    instance = _iid(iid)
    canonical_profile = _profile(profile)
    _need(type(observed_at) is int and 0 <= observed_at <= 2**53 - 1, "observation time")
    display_name = None
    name_source = None
    for source, raw in (
        ("bot_title", bot_title),
        ("profile_display_name", profile_display_name),
        ("canonical_fallback", canonical_fallback),
    ):
        normalized = _name(raw)
        if normalized is not None:
            display_name = normalized
            name_source = source
            break
    _need(display_name is not None and name_source is not None, "no admissible name")
    fields: dict[str, object] = {
        "version": 1,
        "iid": instance,
        "profile": canonical_profile,
        "display_name": display_name,
        "name_source": name_source,
        "character": _character(canonical_profile, shape, color, custom),
    }
    result = dict(fields)
    result["metadata_revision"] = metadata_revision(fields)
    result["avatar"] = _avatar(avatar)
    result["observed_at"] = observed_at
    encoded = json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    _need(len(encoded) <= MAX_RESPONSE_BYTES, "presentation response cap")
    return result

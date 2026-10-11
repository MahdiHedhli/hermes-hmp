"""Pure BI1 projection tests. Filesystem, auth, route, decoder and native gates are separate."""

import hashlib
from decimal import Decimal

import pytest

from hmp_plugin import presentation

IID = "a" * 52
BASE = {
    "iid": IID,
    "profile": "default",
    "bot_title": None,
    "profile_display_name": None,
    "canonical_fallback": "Hermes",
    "shape": None,
    "color": None,
    "custom": None,
    "avatar": None,
    "observed_at": 100,
}


def project(**changes):
    return presentation.project_presentation(**dict(BASE, **changes))


def test_primary_closed_character_and_frozen_revision():
    row = project()
    assert row["name_source"] == "canonical_fallback"
    assert row["character"] == {
        "version": 1,
        "shape": "squircle",
        "color": "#8b5cf6",
        "custom": None,
    }
    assert row["metadata_revision"] == (
        "a4181cb9f55a6ce50a8a34ebc1ce8130ab96ed81533b93652c386924c877cb93"
    )
    assert set(row) == {
        "version",
        "iid",
        "profile",
        "display_name",
        "name_source",
        "character",
        "metadata_revision",
        "avatar",
        "observed_at",
    }


def test_title_then_profile_name_then_canonical_fallback():
    assert project(bot_title="Aster", profile_display_name="Given")["name_source"] == "bot_title"
    assert project(bot_title="\u202e", profile_display_name="Given")["display_name"] == "Given"
    assert project(bot_title=None, profile_display_name=None)["display_name"] == "Hermes"


def test_metadata_revision_is_independent_of_avatar_and_time():
    a = project()
    b = project(
        observed_at=200,
        avatar={
            "revision": "b" * 64,
            "mime": "image/png",
            "bytes": 12,
            "width": 1,
            "height": 1,
        },
    )
    assert a["metadata_revision"] == b["metadata_revision"]
    assert a["avatar"] is None and b["avatar"] is not None
    assert project(bot_title="Hermes Two")["metadata_revision"] != a["metadata_revision"]
    assert hashlib.sha256(b"").hexdigest() != a["metadata_revision"]


@pytest.mark.parametrize(
    "shape", ["circle", "squircle", "pill", "triangle", "hexagon", "cloud", "drop"]
)
def test_all_closed_classic_shapes(shape):
    row = project(profile="alpha", shape=shape, color="#Aa33Ff", custom=True)
    assert row["character"] == {
        "version": 1,
        "shape": shape,
        "color": "#aa33ff",
        "custom": None,
    }


@pytest.mark.parametrize(
    "shape,custom",
    [
        ("blobatar", {"seed": "", "kind": None}),
        ("blobatar:abc123:hexagon", {"seed": "abc123", "kind": "hexagon"}),
        ("blobatar::droplet", {"seed": "", "kind": "droplet"}),
    ],
)
def test_closed_blobatar_projection(shape, custom):
    row = project(profile="alpha", bot_title="Aster", shape=shape, color=None, custom=True)
    assert row["character"] == {"version": 2, "shape": "blobatar", "color": None, "custom": custom}
    if shape == "blobatar:abc123:hexagon":
        assert row["metadata_revision"] == (
            "887eb42671a14c879b1df0de6740070f5956cf8d01cc3330f50542f0d6f99df8"
        )


@pytest.mark.parametrize(
    "shape,color,custom",
    [
        ("<svg>", "#123456", True),
        ("blobatar:a:unknown", None, True),
        ("blobatar:ABC", None, True),
        ("circle", "url(evil)", True),
        ("circle", "#123456", "true"),
    ],
)
def test_unrepresentable_character_falls_back_without_raw_passthrough(shape, color, custom):
    row = project(profile="alpha", shape=shape, color=color, custom=custom)
    assert row["character"] is None
    assert "<svg>" not in str(row) and "url(evil)" not in str(row)


def test_current_primary_default_overrides_unpersisted_seed():
    row = project(shape="circle", color="#000000", custom=False)
    assert row["character"]["shape"] == "squircle"
    assert row["character"]["color"] == "#8b5cf6"


def test_exact_unicode_grapheme_boundary_requires_generated_unicode17_provider():
    # The generated Unicode 17 provider must be present; no skip or stdlib fallback.
    assert presentation._name("e\u0301" * 80) == "é" * 80
    assert presentation._name("e\u0301" * 81) is None
    assert presentation._name("\U0001f1fa\U0001f1f8" * 80) is None  # 640 UTF-8 bytes >256
    assert presentation._name("\U0001f1fa\U0001f1f8" * 32) == "\U0001f1fa\U0001f1f8" * 32


def test_joiners_survive_before_exact_grapheme_count_and_digest():
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466"
    persian = "\u0645\u06cc\u200c\u0631\u0648\u0645"
    assert presentation._name(family * 10) == family * 10
    assert presentation._name(family * 11) is None  # 275 UTF-8 bytes
    assert presentation._name(persian) == persian
    row = project(bot_title=family)
    assert row["display_name"] == family
    without_joiners = project(bot_title=family.replace("\u200d", ""))
    assert row["metadata_revision"] != without_joiners["metadata_revision"]


def test_supported_emoji_tag_sequence_retained_and_stray_tag_refused():
    tag_flag = "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f"
    assert presentation._name(tag_flag * 9) == tag_flag * 9
    assert presentation._name(tag_flag * 10) is None  # 280 UTF-8 bytes
    assert presentation._name("A\U000e0067") is None
    assert project(bot_title="A\U000e0067", profile_display_name="Valid")["display_name"] == "Valid"


def test_explicit_bidi_and_display_controls_neutralized():
    assert presentation._name("A\u202e\u2066\u2069\u061c\u200e\u200fB") == "AB"
    assert presentation._name("A\x00\u2060\ufeffB") == "AB"
    fallback = project(bot_title="\u202e", profile_display_name="Valid")
    assert fallback["name_source"] == "profile_display_name"
    assert presentation._name("\u200dA") is None
    assert presentation._name("A\u200c") is None


@pytest.mark.parametrize(
    "control",
    [
        "\u061c",
        "\u200e",
        "\u200f",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
        "\u00ad",
        "\u200b",
        "\u2060",
        "\u2061",
        "\u2062",
        "\u2063",
        "\u2064",
        "\ufeff",
        "\U000e0001",
    ],
)
def test_declared_controls_only_are_removed_before_clustering(monkeypatch, control):
    seen = []

    def observe(text):
        seen.append(text)
        return list(text)

    monkeypatch.setattr(presentation, "_clusters", observe)
    assert presentation._name("A" + control + "B") == "AB"
    assert seen == ["AB"]


@pytest.mark.parametrize("mark", ["\u0600", "\u0601", "\u06dd"])
def test_arabic_formatting_marks_survive_before_clustering(monkeypatch, mark):
    seen = []

    def observe(text):
        seen.append(text)
        return list(text)

    monkeypatch.setattr(presentation, "_clusters", observe)
    expected = mark + "123"
    assert presentation._name(expected) == expected
    assert seen == [expected]


def test_other_format_and_joiner_characters_are_not_category_erased(monkeypatch):
    seen = []

    def observe(text):
        seen.append(text)
        return list(text)

    monkeypatch.setattr(presentation, "_clusters", observe)
    sample = "A\u180e\u200c\u200d\U000e0067B"
    # The tag is rejected by the existing contextual grammar, after it is
    # passed to the grapheme seam. Joiners and the Mongolian separator survive.
    assert presentation._name(sample) is None
    assert seen == [sample]


def test_name_keeps_newer_assigned_character_when_stdlib_reports_cn(monkeypatch):
    import unicodedata

    newer = "\U0001fae8"
    original = unicodedata.category
    with monkeypatch.context() as patcher:
        patcher.setattr(
            unicodedata,
            "category",
            lambda ch: "Cn" if ch == newer else original(ch),
        )
        patcher.setattr(
            unicodedata,
            "normalize",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("stdlib Unicode normalization fallback")
            ),
        )
        assert unicodedata.category(newer) == "Cn"
        assert presentation.category_drop17(ord(newer)) is False
        assert presentation._name("A" + newer) == "A" + newer


@pytest.mark.parametrize(
    "changes",
    [
        {"iid": "A" * 52},
        {"iid": "a" * 51 + "b"},
        {"profile": "../alpha"},
        {"profile": "Alpha"},
        {"observed_at": True},
        {
            "avatar": {
                "revision": "b" * 64,
                "mime": "image/png",
                "bytes": True,
                "width": 1,
                "height": 1,
            }
        },
        {
            "avatar": {
                "revision": "b" * 64,
                "mime": "image/svg+xml",
                "bytes": 1,
                "width": 1,
                "height": 1,
            }
        },
        {
            "avatar": {
                "revision": "b" * 64,
                "mime": "image/png",
                "bytes": 2_000_001,
                "width": 1,
                "height": 1,
            }
        },
        {
            "avatar": {
                "revision": "b" * 64,
                "mime": "image/png",
                "bytes": 1,
                "width": 1025,
                "height": 1,
            }
        },
        {
            "avatar": {
                "revision": "b" * 64,
                "mime": "image/png",
                "bytes": 1,
                "width": 1,
                "height": 1,
                "url": "https://example.test",
            }
        },
    ],
)
def test_closed_identity_time_and_avatar_schema(changes):
    with pytest.raises(presentation.PresentationUnavailableError):
        project(**changes)


def test_metadata_revision_rejects_self_or_avatar_field_cycle():
    fields = {
        k: project()[k]
        for k in (
            "version",
            "iid",
            "profile",
            "display_name",
            "name_source",
            "character",
        )
    }
    with pytest.raises(presentation.PresentationUnavailableError):
        presentation.metadata_revision(dict(fields, metadata_revision="a" * 64))
    with pytest.raises(presentation.PresentationUnavailableError):
        presentation.metadata_revision(dict(fields, avatar=None))


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", True),
        ("iid", "A" * 52),
        ("profile", "../default"),
        ("display_name", "\u202e"),
        ("name_source", "private_config"),
        ("character", {"version": True, "shape": "circle", "color": "#123456", "custom": None}),
        ("character", {"version": 1, "shape": "circle", "color": "#123456", "custom": False}),
        (
            "character",
            {
                "version": 2,
                "shape": "blobatar",
                "color": None,
                "custom": {"seed": "ABC", "kind": "round"},
            },
        ),
        (
            "character",
            {
                "version": 2,
                "shape": "blobatar",
                "color": None,
                "custom": {"seed": "ok", "kind": "round", "svg": "<svg>"},
            },
        ),
    ],
)
def test_revision_helper_rejects_noncanonical_direct_fields(field, value):
    fields = {
        k: project()[k]
        for k in (
            "version",
            "iid",
            "profile",
            "display_name",
            "name_source",
            "character",
        )
    }
    fields[field] = value
    with pytest.raises(presentation.PresentationUnavailableError):
        presentation.metadata_revision(fields)


@pytest.mark.parametrize("observed_at", [0, 2**53 - 1])
def test_observation_time_i_json_inclusive_bound(observed_at):
    row = project(observed_at=observed_at)
    assert type(row["observed_at"]) is int
    assert row["observed_at"] == observed_at
    assert row["metadata_revision"] == project(observed_at=100)["metadata_revision"]


@pytest.mark.parametrize(
    "observed_at",
    [
        -1,
        2**53,
        2**63 - 1,
        True,
        False,
        0.0,
        1.5,
        float("inf"),
        float("nan"),
        Decimal("1"),
        "0",
        None,
    ],
)
def test_observation_time_rejects_outside_i_json_integer_domain(observed_at):
    with pytest.raises(presentation.PresentationUnavailableError, match="observation time"):
        project(observed_at=observed_at)

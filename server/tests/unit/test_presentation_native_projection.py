"""Temporary fixed FS -> real bounded YAML/raster -> full DTO.

Claims are unit fixtures, not native authentication. Raster cases are structural,
not Flutter decoding/device/native gateway qualification.
"""

import builtins
import hashlib
import json

import pytest

from hmp_plugin.presentation import CLASSIC_SHAPES
from hmp_plugin.presentation_native_claim import NativeSourceError
from hmp_plugin.presentation_native_projection import NativePresentationProjector
from hmp_plugin.presentation_native_yaml import NativePresentationYaml

from .test_presentation_native_files import setup_read
from .test_presentation_native_files import source as source
from .test_presentation_raster import chunk, jpeg, png, webp

IID = "a" * 52


def configured(source, *, raw=None, image=None, name="avatar.png"):
    home, metadata, assets, avatar = source
    if raw is not None:
        metadata.write_bytes(raw)
    if image is None:
        avatar.unlink()
    else:
        avatar.write_bytes(image)
        if name != "avatar.png":
            avatar.rename(assets / name)
    reader, claim, work, memory, ops, now, issuer, operation = setup_read(home)
    projector = NativePresentationProjector(claim._owner, reader)
    return projector, claim, work, memory, ops, now, issuer, operation


def run(args, **kwargs):
    projector, claim, work, memory, *_ = args
    return projector.run(claim, work, memory, iid=IID, observed_at=123, **kwargs)


@pytest.mark.parametrize("shape", sorted(CLASSIC_SHAPES))
def test_all_classic_characters_and_desktop_name_reach_closed_dto(source, shape):
    raw = f"""display_name: Profile name
ui_meta:
  hermes-bots:
    title: Desktop name
    shape: {shape}
    color: '#AABBCC'
    custom: true
private: {{secret: SYNTHETIC_PRIVATE_NOT_OUTPUT}}
""".encode()
    args = configured(source, raw=raw)
    result = run(args)
    dto = json.loads(result.metadata)
    assert dto["display_name"] == "Desktop name" and dto["name_source"] == "bot_title"
    assert dto["character"] == {"version": 1, "shape": shape, "color": "#aabbcc", "custom": None}
    assert dto["avatar"] is None and dto["profile"] == "belac" and dto["iid"] == IID
    assert set(dto) == {
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
    assert b"SYNTHETIC_PRIVATE" not in result.metadata and len(result.metadata) <= 4096
    assert args[2].snapshot()["yaml_tokens"] > 0 and args[2].snapshot()["yaml_nodes"] > 0
    assert not args[4].live
    result.discard()
    assert args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize(
    "shape,seed,kind",
    [
        ("blobatar", "", None),
        ("blobatar:abc123", "abc123", None),
        ("blobatar:abc123:droplet", "abc123", "droplet"),
    ],
)
def test_blobatar_versions_keep_exact_seed_and_kind(source, shape, seed, kind):
    args = configured(
        source, raw=f"ui_meta: {{hermes-bots: {{shape: '{shape}', custom: true}}}}".encode()
    )
    result = run(args)
    assert json.loads(result.metadata)["character"] == {
        "version": 2,
        "shape": "blobatar",
        "color": None,
        "custom": {"seed": seed, "kind": kind},
    }
    result.discard()
    assert args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize(
    "name,factory,mime",
    [
        ("avatar.png", png, "image/png"),
        ("avatar.jpg", jpeg, "image/jpeg"),
        ("avatar.webp", webp, "image/webp"),
    ],
)
def test_static_formats_single_hash_exact_body_and_revision(source, name, factory, mime):
    image = factory()
    args = configured(source, image=image, name=name)
    digest = hashlib.sha256(image).hexdigest()
    result = run(args, expected_avatar_revision=digest)
    assert result.avatar == image
    assert json.loads(result.metadata)["avatar"] == {
        "revision": digest,
        "mime": mime,
        "bytes": len(image),
        "width": 2,
        "height": 2,
    }
    assert args[2].snapshot()["hash_bytes"] == len(image)
    assert args[3].snapshot()[0] > len(image)
    result.discard()
    assert result.avatar is None and result.metadata is None and args[3].snapshot()[:2] == (0, 0)


def test_missing_metadata_uses_canonical_fallback_and_image_still_renders_descriptor(source):
    args = configured(source, image=png())
    source[1].unlink()
    result = run(args)
    dto = json.loads(result.metadata)
    assert dto["display_name"] == "Belac" and dto["name_source"] == "canonical_fallback"
    assert dto["avatar"]["mime"] == "image/png"
    result.discard()
    assert args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize(
    "raw",
    [
        b"display_name: &a Name\nother: *a\n",
        b"%FOO synthetic\n---\ndisplay_name: Name\n",
        b"display_name: One\ndisplay_name: Two\n",
        b"display_name: !!str Name\n",
        b"display_name: [wrong]\n",
        b'display_name: "unterminated\n',
        b"display_name: \xff\n",
    ],
)
def test_bad_yaml_has_closed_error_no_retained_context_and_no_payload_debt(source, raw):
    args = configured(source, raw=raw)
    with pytest.raises(NativeSourceError) as error:
        run(args)
    assert str(error.value) == "native_source_unavailable"
    assert error.value.__context__ is None
    assert not args[4].live and args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize(
    "image,name",
    [
        (png(extra=b"") + b"trailing", "avatar.png"),
        (png(), "avatar.jpg"),
        (png(width=1025), "avatar.png"),
        (b"<svg/>", "avatar.png"),
    ],
)
def test_refused_image_does_not_return_descriptor_or_payload(source, image, name):
    args = configured(source, image=image, name=name)
    with pytest.raises(NativeSourceError) as error:
        run(args)
    assert error.value.__context__ is None
    assert not args[4].live and args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize("image", [None, png()])
def test_missing_or_stale_avatar_revision_refuses_without_result(source, image):
    args = configured(source, image=image)
    with pytest.raises(NativeSourceError) as error:
        run(args, expected_avatar_revision="0" * 64)
    assert error.value.reason == "native_avatar_revision_changed"
    assert error.value.__context__ is None
    assert not args[4].live and args[3].snapshot()[:2] == (0, 0)


def test_invalid_requested_revision_refuses_before_any_source_open(source):
    args = configured(source)
    with pytest.raises(NativeSourceError):
        run(args, expected_avatar_revision="../unsafe")
    assert not args[4].opened and args[3].snapshot()[:2] == (0, 0)


def test_yaml_uses_startup_bound_dependency_without_graph_construction_or_request_import(
    source, monkeypatch
):
    from yaml.loader import SafeLoader

    args = configured(source)
    original_import = builtins.__import__

    def import_guard(name, *args, **kwargs):
        if name == "yaml" or name.startswith("yaml."):
            raise AssertionError("request imported parser")
        return original_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail("YAML graph construction")

    for name in (
        "get_data",
        "get_single_data",
        "get_node",
        "construct_object",
        "construct_document",
    ):
        monkeypatch.setattr(SafeLoader, name, forbidden)
    monkeypatch.setattr(builtins, "__import__", import_guard)
    result = run(args)
    assert json.loads(result.metadata)["display_name"] == "Unit fixture"
    result.discard()
    assert args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize("stop", ["expire", "retire"])
def test_late_projection_cannot_outlive_original_claim(source, monkeypatch, stop):
    args = configured(source)
    original_parse = NativePresentationYaml.parse

    def changed(parser, raw, work):
        fields = original_parse(parser, raw, work)
        if stop == "expire":
            args[5][0] = 3.0
        else:
            args[1]._owner._retire(args[6], args[7])
        return fields

    monkeypatch.setattr(NativePresentationYaml, "parse", changed)
    with pytest.raises(NativeSourceError):
        run(args)
    assert not args[4].live and args[3].snapshot()[:2] == (0, 0)


def test_original_yaml_work_cannot_be_reset_between_read_and_parse(source):
    args = configured(source)
    for _ in range(2048):
        args[2].charge_yaml_token()
    with pytest.raises(NativeSourceError):
        run(args)
    assert not args[4].live and args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize(
    "raw,expected_disposed",
    [
        (b"display_name: Name\n", 2),
        (b"%FOO synthetic\n---\ndisplay_name: Name", 1),
        (b"display_name: One\ndisplay_name: Two", 2),
    ],
)
def test_bound_parser_disposes_sequential_loaders_on_success_and_refusal(
    source, monkeypatch, raw, expected_disposed
):
    from yaml.loader import SafeLoader

    args = configured(source, raw=raw)
    original_init, original_dispose = SafeLoader.__init__, SafeLoader.dispose
    live, disposed = set(), []

    def initialize(loader, stream):
        assert not live  # scan pass must settle before the event pass starts
        assert any(kind == "yaml" for _, _, kind in args[3]._live.values())
        original_init(loader, stream)
        live.add(id(loader))

    def dispose(loader):
        live.remove(id(loader))
        disposed.append(True)
        original_dispose(loader)

    monkeypatch.setattr(SafeLoader, "__init__", initialize)
    monkeypatch.setattr(SafeLoader, "dispose", dispose)
    result = None
    try:
        result = run(args)
    except NativeSourceError:
        assert expected_disposed != 2 or b"Two" in raw
    finally:
        if result is not None:
            result.discard()
    assert len(disposed) == expected_disposed and not live
    assert args[3].snapshot()[:2] == (0, 0)


def test_name_rename_and_static_image_clear_have_independent_revision_semantics(source):
    args = configured(source, raw=b"display_name: First\n", image=png())
    result = run(args)
    original = json.loads(result.metadata)
    result.discard()
    source[1].write_bytes(b"display_name: Second\n")
    # New explicit operation; claims/read work are never reused or renewed.
    reader, claim, work, memory, *_ = setup_read(source[0])
    projector = NativePresentationProjector(claim._owner, reader)
    renamed = projector.run(claim, work, memory, iid=IID, observed_at=124)
    current = json.loads(renamed.metadata)
    assert current["metadata_revision"] != original["metadata_revision"]
    assert current["avatar"] == original["avatar"]
    renamed.discard()
    source[3].unlink()
    reader, claim, work, memory, *_ = setup_read(source[0])
    projector = NativePresentationProjector(claim._owner, reader)
    cleared = projector.run(claim, work, memory, iid=IID, observed_at=125)
    dto = json.loads(cleared.metadata)
    assert dto["avatar"] is None and dto["metadata_revision"] == current["metadata_revision"]
    cleared.discard()
    assert memory.snapshot()[:2] == (0, 0)


def test_full_metadata_and_avatar_limits_are_not_reduced_by_composition(source):
    prefix = b"display_name: Maximum fixture\n#"
    raw = prefix + b"x" * (65_536 - len(prefix))
    base = png()
    image = png(extra=chunk(b"tEXt", b"x" * (2_000_000 - len(base) - 12)))
    assert len(raw) == 65_536 and len(image) == 2_000_000
    args = configured(source, raw=raw, image=image)
    result = run(args)
    assert result.avatar == image
    dto = json.loads(result.metadata)
    assert dto["display_name"] == "Maximum fixture" and dto["avatar"]["bytes"] == 2_000_000
    charges = args[2].snapshot()
    assert charges["read_bytes"] == 4_131_076 and charges["hash_bytes"] == 2_000_000
    assert args[3].snapshot()[2] <= 16 * 1024 * 1024
    result.discard()
    assert args[3].snapshot()[:2] == (0, 0)


def test_image_hash_credit_cannot_be_reset_by_projection(source):
    args = configured(source, image=png())
    remaining = 2_000_000
    while remaining:
        count = min(remaining, 65_536)
        args[2].charge_hash_bytes(count)
        remaining -= count
    with pytest.raises(NativeSourceError) as error:
        run(args)
    assert error.value.reason == "native_source_unavailable" and error.value.__context__ is None
    assert not args[4].live and args[3].snapshot()[:2] == (0, 0)


@pytest.mark.parametrize("profile,expected", [("default", "Hermes"), ("school-bot", "School Bot")])
def test_unnamed_profile_uses_same_native_roster_fallback(source, profile, expected):
    source[1].unlink()
    source[3].unlink()
    reader, claim, work, memory, *_ = setup_read(source[0], profile=profile)
    projector = NativePresentationProjector(claim._owner, reader)
    result = projector.run(claim, work, memory, iid=IID, observed_at=123)
    dto = json.loads(result.metadata)
    assert dto["display_name"] == expected and dto["name_source"] == "canonical_fallback"
    if profile == "default":
        assert dto["character"] == {
            "version": 1,
            "shape": "squircle",
            "color": "#8b5cf6",
            "custom": None,
        }
    result.discard()
    assert memory.snapshot()[:2] == (0, 0)

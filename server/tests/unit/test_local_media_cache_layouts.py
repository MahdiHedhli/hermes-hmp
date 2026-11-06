"""Closed native cache layouts: current producer support without path fallback."""

import json

import pytest

from hmp_plugin import local_media_candidate as candidate
from hmp_plugin import local_media_file_safety as files


def test_current_generated_cache_path_is_a_candidate():
    home = "/fixture/profile-alpha"
    assert candidate.derive_cache_location(home + "/cache/generated/images/native.png", home) == (
        files.CacheLayout.GENERATED,
        "native.png",
    )
    assert candidate.derive_cache_location(home + "/cache/images/native.png", home) == (
        files.CacheLayout.LEGACY,
        "native.png",
    )


def test_current_native_result_remains_eligible_for_descriptor_minting():
    home = "/fixture/profile-alpha"
    row = {
        "id": 2,
        "role": "tool",
        "tool_name": "image_generate",
        "tool_call_id": "fixture-call",
        "content": json.dumps(
            {"success": True, "image": home + "/cache/generated/images/native.png"}
        ),
    }
    assert candidate.raw_tool_candidate(row, home) is not None


def test_same_name_layouts_do_not_alias_and_missing_generated_has_no_fallback(
    tmp_path, monkeypatch
):
    import os

    home = tmp_path / "alpha"
    legacy = home / "cache/images"
    generated = home / "cache/generated/images"
    legacy.mkdir(parents=True)
    generated.mkdir(parents=True)
    (legacy / "same.png").write_bytes(b"legacy-data")
    (generated / "same.png").write_bytes(b"generated-data")
    read = files.read_profile_cache_image(
        home, "same.png", cache_layout=files.CacheLayout.GENERATED
    )
    assert read.unvalidated_raster_bytes() == b"generated-data"
    read = files.read_profile_cache_image(home, "same.png")
    assert read.unvalidated_raster_bytes() == b"legacy-data"
    (generated / "same.png").unlink()
    generated.rmdir()
    generated.parent.rmdir()
    opened = []
    original = os.open

    def observe(name, *args, **kwargs):
        opened.append(name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(os, "open", observe)
    missing = files.read_profile_cache_image(
        home, "same.png", cache_layout=files.CacheLayout.GENERATED
    )
    assert missing.outcome is files.Outcome.UNAVAILABLE
    assert opened == [str(home), "cache", "generated"]


def test_untrusted_layout_values_refuse_before_any_file_open(tmp_path, monkeypatch):
    import enum
    import os

    class ForeignLayout(enum.Enum):
        GENERATED = "generated_images"

    def unexpected_open(*args, **kwargs):
        raise AssertionError("invalid layout must not open a path")

    monkeypatch.setattr(os, "open", unexpected_open)
    for value in (
        None,
        "generated_images",
        ("cache", "generated", "images"),
        ForeignLayout.GENERATED,
    ):
        result = files.read_profile_cache_image(tmp_path, "same.png", cache_layout=value)
        assert result.outcome is files.Outcome.CACHE_LAYOUT_INVALID


def test_generated_path_grammar_and_foreign_profile_remain_closed():
    home = "/fixture/alpha"
    for value in (
        home + "/cache/generated/images/../secret.png",
        home + "/cache/generated/images/nested/image.png",
        home + "/cache/generated/images/",
        home + "/cache/generated/images/a\\b.png",
        home + "/cache/generated/images/" + "x" * 129,
        home + "-other/cache/generated/images/image.png",
        home + "/cache/documents/image.png",
        home + "/image_cache/image.png",
    ):
        assert candidate.derive_cache_location(value, home) is None


def test_raw_digest_binds_cache_namespace_for_the_same_tool_row():
    home = "/fixture/alpha"
    row = {"id": 2, "role": "tool", "tool_name": "image_generate", "tool_call_id": "fixture-call"}
    row["content"] = json.dumps({"success": True, "image": home + "/cache/images/same.png"})
    old = candidate.raw_tool_candidate(row, home)
    row["content"] = json.dumps(
        {"success": True, "image": home + "/cache/generated/images/same.png"}
    )
    new = candidate.raw_tool_candidate(row, home)
    assert old is not None and new is not None
    assert old.raw_digest != new.raw_digest


@pytest.mark.parametrize("level", ["generated", "images"])
def test_generated_cache_ancestor_symlinks_are_refused(tmp_path, level):
    home = tmp_path / "alpha"
    cache = home / "cache"
    cache.mkdir(parents=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    if level == "generated":
        (foreign / "images").mkdir()
        (foreign / "images/same.png").write_bytes(b"foreign")
        (cache / "generated").symlink_to(foreign, target_is_directory=True)
    else:
        (cache / "generated").mkdir()
        (foreign / "same.png").write_bytes(b"foreign")
        (cache / "generated/images").symlink_to(foreign, target_is_directory=True)
    result = files.read_profile_cache_image(
        home, "same.png", cache_layout=files.CacheLayout.GENERATED
    )
    assert result.outcome is files.Outcome.ANCESTOR_REFUSED


@pytest.mark.parametrize("level", ["generated", "images"])
def test_every_added_directory_is_revalidated_after_read(tmp_path, level):
    home = tmp_path / "alpha"
    images = home / "cache/generated/images"
    images.mkdir(parents=True)
    (images / "same.png").write_bytes(b"original")
    target = images.parent if level == "generated" else images

    def replace_directory():
        target.rename(target.with_name(target.name + "-old"))
        target.mkdir()

    result = files.read_profile_cache_image(
        home,
        "same.png",
        cache_layout=files.CacheLayout.GENERATED,
        _hooks={"before_revalidate": replace_directory},
    )
    assert result.outcome is files.Outcome.BINDING_LOST


def test_authenticated_route_uses_generated_namespace_and_preserves_legacy(tmp_path, monkeypatch):
    from .test_s5_media_fetch import VALID_PNG, VALID_PNG_B, Fx

    fx = Fx(tmp_path, monkeypatch)
    legacy = fx.image_path(6)
    generated = fx.native.home_path / "cache/generated/images" / legacy.name
    generated.parent.mkdir(parents=True)
    generated.write_bytes(VALID_PNG)
    legacy.write_bytes(VALID_PNG_B)
    row = next(item for item in fx.native.db.messages[fx.rig.tip] if item["id"] == 6)
    row["content"] = json.dumps({"success": True, "image": str(generated)})

    async def scenario(client):
        owner = await fx.rig.pair(client)
        refs = await fx.mint(client, owner)
        assert await fx.served(client, refs[6], dev=owner) == VALID_PNG
        assert await fx.served(client, refs[4], dev=owner) == VALID_PNG
        generated.unlink()
        await fx.refused(client, refs[6], dev=owner)

    fx.run(scenario)


def test_minted_reference_cannot_move_between_namespaces_before_file_io(tmp_path, monkeypatch):
    import os

    from .test_s5_media_fetch import VALID_PNG, Fx

    fx = Fx(tmp_path, monkeypatch)
    legacy = fx.image_path(6)
    generated = fx.native.home_path / "cache/generated/images" / legacy.name
    generated.parent.mkdir(parents=True)
    generated.write_bytes(VALID_PNG)
    row = next(item for item in fx.native.db.messages[fx.rig.tip] if item["id"] == 6)
    row["content"] = json.dumps({"success": True, "image": str(generated)})
    opens = []
    original = os.open

    def observe(name, *args, **kwargs):
        opens.append(name)
        return original(name, *args, **kwargs)

    async def scenario(client):
        owner = await fx.rig.pair(client)
        refs = await fx.mint(client, owner)
        monkeypatch.setattr(os, "open", observe)
        monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd | {observe})
        assert await fx.served(client, refs[6], dev=owner) == VALID_PNG
        assert opens
        opens.clear()
        before = fx.p1_in
        row["content"] = json.dumps({"success": True, "image": str(legacy)})
        await fx.refused(client, refs[6], dev=owner)
        assert fx.p1_in == before + 1 and opens == []

    fx.run(scenario)


@pytest.mark.parametrize(
    "name,old,new",
    [
        (
            "local_media_file_safety.py",
            '("cache", "generated", "images")',
            '("cache", "documents")',
        ),
        (
            "local_media_candidate.py",
            'prefix = home + "/cache/generated/images/"',
            'prefix = home + "/cache/documents/"',
        ),
        (
            "local_media_active_batch.py",
            "_candidate.derive_cache_location(claim.image, home)",
            "_candidate.derive_flat_name(claim.image, home)",
        ),
        ("bridge.py", "cache_layout=layout", "cache_layout=None"),
    ],
)
def test_source_witness_cannot_strip_an_unreviewed_layout_change(name, old, new):
    from pathlib import Path

    from .media_cache_layout_witness import reverse_cache_layout_additions

    text = (Path(candidate.__file__).parent / name).read_bytes().decode("utf-8")
    assert text.count(old) == 1
    reverse_cache_layout_additions(text, name)
    mutant = text.replace(old, new, 1)
    with pytest.raises(AssertionError):
        reverse_cache_layout_additions(mutant, name)

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


def test_historic_native_cache_result_is_not_discarded():
    home = "/fixture/profile-alpha"
    row = {
        "id": 2,
        "role": "tool",
        "tool_name": "image_generate",
        "tool_call_id": "fixture-call",
        "content": json.dumps({"success": True, "image": home + "/image_cache/native.png"}),
    }
    assert candidate.raw_tool_candidate(row, home) is not None


@pytest.mark.parametrize(
    "suffix", ["", "nested/a.png", "../a.png", "a\\b.png", "a" * 129, "/a.png", "a\x00b.png"]
)
def test_historic_native_path_grammar_and_foreign_profile_stay_closed(suffix):
    home = "/fixture/alpha"
    assert candidate.derive_cache_location(home + "/image_cache/" + suffix, home) is None
    assert candidate.derive_cache_location(home + "-other/image_cache/valid.png", home) is None
    assert candidate.derive_cache_location(home + "/cache/image_cache/valid.png", home) is None


def test_three_same_name_roots_are_isolated_without_any_fallback(tmp_path):
    home = tmp_path / "alpha"
    layouts = [
        ("cache/images", files.CacheLayout.LEGACY, b"modern"),
        ("cache/generated/images", files.CacheLayout.GENERATED, b"generated"),
        ("image_cache", files.CacheLayout.HISTORIC_IMAGE_CACHE, b"historic"),
    ]
    for relative, _layout, payload in layouts:
        folder = home / relative
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = folder / "same.png"
        path.write_bytes(payload)
        path.chmod(0o600)
    for relative, layout, payload in layouts:
        result = files.read_profile_cache_image(home, "same.png", cache_layout=layout)
        assert result.unvalidated_raster_bytes() == payload
        path = home / relative / "same.png"
        path.unlink()
        missing = files.read_profile_cache_image(home, "same.png", cache_layout=layout)
        assert missing.outcome is files.Outcome.UNAVAILABLE and missing.byte_count == 0
        path.write_bytes(payload)
        path.chmod(0o600)


@pytest.mark.parametrize(
    "attack",
    ["ancestor_symlink", "file_symlink", "hardlink", "ancestor_replacement", "file_replacement"],
)
def test_historic_file_safety_and_cleanup(tmp_path, monkeypatch, attack):
    import os

    from .test_local_media_file_safety import FdTracker

    home = tmp_path / "alpha"
    folder = home / "image_cache"
    folder.mkdir(parents=True, mode=0o700)
    path = folder / "same.png"
    path.write_bytes(b"synthetic-original")
    path.chmod(0o600)

    def read(**kw):
        return files.read_profile_cache_image(
            home, "same.png", cache_layout=files.CacheLayout.HISTORIC_IMAGE_CACHE, **kw
        )

    assert read().unvalidated_raster_bytes() == b"synthetic-original"
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    other_file = other / "same.png"
    other_file.write_bytes(b"synthetic-foreign")
    other_file.chmod(0o600)
    hook = None
    if attack == "ancestor_symlink":
        path.unlink()
        folder.rmdir()
        folder.symlink_to(other, target_is_directory=True)
        expected = files.Outcome.ANCESTOR_REFUSED
    elif attack == "file_symlink":
        path.unlink()
        path.symlink_to(other_file)
        expected = files.Outcome.SYMLINK_REFUSED
    elif attack == "hardlink":
        path.unlink()
        os.link(other_file, path)
        expected = files.Outcome.HARDLINKED
    elif attack == "ancestor_replacement":

        def hook():
            folder.rename(home / "old-image-cache")
            folder.mkdir(mode=0o700)

        expected = files.Outcome.BINDING_LOST
    else:

        def hook():
            path.rename(folder / "old.png")
            path.write_bytes(b"replacement")
            path.chmod(0o600)

        expected = files.Outcome.BINDING_LOST
    tracker = FdTracker(monkeypatch)
    try:
        result = read(_hooks={"before_revalidate": hook} if hook else None)
        assert result.outcome is expected and result.byte_count == 0
        assert not tracker.leaked
        with pytest.raises(ValueError):
            result.unvalidated_raster_bytes()
    finally:
        tracker.cleanup()


def test_authenticated_historic_image_fetch_and_namespace_change_refusal(tmp_path, monkeypatch):
    import os

    from .test_s5_media_fetch import VALID_PNG, VALID_PNG_B, Fx

    fx = Fx(tmp_path, monkeypatch)
    modern = fx.image_path(6)
    historic = fx.native.home_path / "image_cache" / modern.name
    historic.parent.mkdir(mode=0o700)
    historic.write_bytes(VALID_PNG)
    historic.chmod(0o600)
    modern.write_bytes(VALID_PNG_B)
    row = next(item for item in fx.native.db.messages[fx.rig.tip] if item["id"] == 6)
    row["content"] = json.dumps({"success": True, "image": str(historic)})
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
        row["content"] = json.dumps({"success": True, "image": str(modern)})
        await fx.refused(client, refs[6], dev=owner)
        assert opens == []

    fx.run(scenario)


@pytest.mark.parametrize(
    "name,old,new",
    [
        (
            "local_media_candidate.py",
            'historic_prefix = home + "/image_cache/"',
            'historic_prefix = home + "/cache/documents/"',
        ),
        (
            "local_media_file_safety.py",
            'HISTORIC_CACHE_COMPONENTS = ("image_cache",)',
            'HISTORIC_CACHE_COMPONENTS = ("cache", "documents")',
        ),
    ],
)
def test_historic_inverse_never_strips_an_unreviewed_root(name, old, new):
    from pathlib import Path

    from .media_cache_layout_witness import reverse_cache_layout_additions

    text = (Path(candidate.__file__).parent / name).read_text()
    reverse_cache_layout_additions(text, name)
    assert text.count(old) == 1
    with pytest.raises(AssertionError):
        reverse_cache_layout_additions(text.replace(old, new), name)

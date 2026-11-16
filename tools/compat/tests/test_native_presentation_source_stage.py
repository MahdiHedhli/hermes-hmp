"""Closed source-copy refusal cases; no native core/bootstrap/provider executes."""

import hashlib
import importlib.util
import io
import os
import tarfile
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "presentation_source_stage", Path(__file__).parents[1] / "native_presentation_source_stage.py"
)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)
COMMIT = "1" * 40
DATA = b"synthetic-only\n"
OID = hashlib.sha1(
    b"blob " + str(len(DATA)).encode() + b"\0" + DATA, usedforsecurity=False
).hexdigest()


def archive(tmp_path, names, *, kind=None, comment=COMMIT, mode=0o600):
    path = tmp_path / "source.tar"
    with tarfile.open(
        path, "w", format=tarfile.PAX_FORMAT, pax_headers={"comment": comment}
    ) as out:
        for name in names:
            item = tarfile.TarInfo(name)
            item.mode = mode
            item.size = len(DATA)
            if kind is not None:
                item.type = kind
                item.linkname = "outside"
            out.addfile(item, io.BytesIO(DATA) if kind is None else None)
    path.chmod(0o600)
    return path


def test_copy_exact_literal_bytes_and_manifest_hashes_without_native_execution(tmp_path):
    path = archive(tmp_path, ["sample.py"])
    output = tmp_path / "copy"
    result = module.extract_snapshot(path, output, COMMIT, {"sample.py": ("100644", OID)})
    assert result == {"sample.py": hashlib.sha256(DATA).hexdigest()}
    assert (output / "sample.py").read_bytes() == DATA
    assert (output / "sample.py").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("name", ["../outside.py", "/outside.py", "a/../sample.py", "a//sample.py"])
def test_noncanonical_or_escaping_archive_path_refuses(tmp_path, name):
    path = archive(tmp_path, [name])
    with pytest.raises(module.PresentationSourceStageError):
        module.extract_snapshot(path, tmp_path / "copy", COMMIT, {"sample.py": ("100644", OID)})


@pytest.mark.parametrize("fault", ["duplicate", "extra", "missing", "blob", "mode", "commit"])
def test_incomplete_or_mutated_literal_snapshot_refuses(tmp_path, fault):
    names = ["sample.py"]
    if fault == "duplicate":
        names *= 2
    elif fault == "extra":
        names.append("extra.py")
    path = archive(
        tmp_path,
        names,
        comment="2" * 40 if fault == "commit" else COMMIT,
        mode=0o644 if fault == "mode" else 0o600,
    )
    oid = "0" * 40 if fault == "blob" else OID
    literal = {"sample.py": ("100644", oid)}
    if fault == "missing":
        literal["missing.py"] = ("100644", OID)
    with pytest.raises(module.PresentationSourceStageError):
        module.extract_snapshot(path, tmp_path / "copy", COMMIT, literal)


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE])
def test_archive_link_or_special_file_refuses(tmp_path, kind):
    path = archive(tmp_path, ["sample.py"], kind=kind)
    with pytest.raises(module.PresentationSourceStageError):
        module.extract_snapshot(path, tmp_path / "copy", COMMIT, {"sample.py": ("100644", OID)})


def test_existing_or_symlink_destination_and_nonprivate_archive_refuse(tmp_path):
    path = archive(tmp_path, ["sample.py"])
    target = tmp_path / "copy"
    target.symlink_to(tmp_path / "absent", target_is_directory=True)
    with pytest.raises(module.PresentationSourceStageError):
        module.extract_snapshot(path, target, COMMIT, {"sample.py": ("100644", OID)})
    target.unlink()
    path.chmod(0o644)
    with pytest.raises(module.PresentationSourceStageError):
        module.extract_snapshot(path, target, COMMIT, {"sample.py": ("100644", OID)})


def test_literal_tree_filters_only_native_extensions_and_refuses_selected_links():
    raw = (
        b"100644 blob "
        + OID.encode()
        + b"\tsample.py\0"
        + b"100644 blob "
        + OID.encode()
        + b"\tREADME.md\0"
    )
    assert set(module.literal_tree(raw, module._EXTENSIONS)) == {"sample.py"}
    assert set(module.literal_tree(raw, None)) == {"sample.py", "README.md"}
    with pytest.raises(module.PresentationSourceStageError):
        module.literal_tree(raw.replace(b"100644", b"120000", 1), module._EXTENSIONS)


def test_private_parent_is_required_before_destination_creation(tmp_path):
    path = archive(tmp_path, ["sample.py"])
    tmp_path.chmod(0o755)
    try:
        with pytest.raises(module.PresentationSourceStageError):
            module.extract_snapshot(path, tmp_path / "copy", COMMIT, {"sample.py": ("100644", OID)})
        assert not os.path.lexists(tmp_path / "copy")
    finally:
        tmp_path.chmod(0o700)


def test_malformed_archive_is_normalized_to_source_refusal(tmp_path):
    path = tmp_path / "bad.tar"
    path.write_bytes(b"not-a-tar")
    path.chmod(0o600)
    with pytest.raises(module.PresentationSourceStageError):
        module.extract_snapshot(path, tmp_path / "copy", COMMIT, {"sample.py": ("100644", OID)})


def test_foreign_repository_object_refuses_before_hooks_or_setup_writes(tmp_path):
    calls = []

    class Foreign:
        def __str__(self):
            calls.append(True)
            raise AssertionError("foreign path hook ran")

    with pytest.raises(module.PresentationSourceStageError):
        module.stage_sources(tmp_path.resolve(), Foreign(), tmp_path.resolve())
    assert calls == [] and list(tmp_path.iterdir()) == []


def test_complete_new_native_snapshot_size_exception_is_exact_commit_scoped():
    assert module.snapshot_byte_limit("f8acc26834bf1275c34d09ccc3e51250bcd1e26b") == 149236948
    assert module.snapshot_byte_limit("ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df") == 128 * 1024**2
    assert module.snapshot_byte_limit(COMMIT) == 128 * 1024**2

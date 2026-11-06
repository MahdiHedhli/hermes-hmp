"""Disposable synthetic credential files only; never installed host keys."""

import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from hmp_plugin.presentation_credential_files import (
    CredentialAcquisitionError,
    RoleKeySelection,
    StartupRoleKeyFiles,
)


def selection(tmp_path):
    directory = tmp_path / "role"
    directory.mkdir(mode=0o700)
    own, peer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()

    def public(key):
        return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    values = {
        "own.seed": own.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
        "own.pub": public(own),
        "peer.pub": public(peer),
    }
    for name, data in values.items():
        fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
    return RoleKeySelection(str(directory), "gateway", "a" * 64, public(own), public(peer))


def refused(value):
    with pytest.raises(CredentialAcquisitionError) as error:
        StartupRoleKeyFiles(value)
    owner = error.value.failed_owner
    assert owner._refused and not owner._ready and owner._private_key is None
    assert all(item.fd is None or item.closed or item.unknown for item in owner._records)
    return owner


def test_success_closes_all_descriptors_and_retirement_is_irreversible(tmp_path):
    value = selection(tmp_path)
    owner = StartupRoleKeyFiles(value)
    assert owner._ready and not owner._refused
    assert owner._private_key is not None
    assert all(item.closed for item in owner._records)
    assert owner.close_local()
    assert not hasattr(owner, "sign") and not hasattr(owner, "authorized")
    assert repr(owner) == "<StartupRoleKeyFiles credentials-redacted>"
    owner.retire()
    assert owner._refused and not owner._ready and owner._private_key is None


@pytest.mark.parametrize("name", ["own.seed", "own.pub", "peer.pub"])
@pytest.mark.parametrize(
    "mutation", ["missing", "short", "long", "mode", "link", "symlink", "fifo"]
)
def test_invalid_key_files_refuse_and_close_partial_owners(tmp_path, name, mutation):
    value = selection(tmp_path)
    path = Path(value.directory) / name
    if mutation == "missing":
        path.unlink()
    elif mutation == "short":
        path.write_bytes(b"x" * 31)
    elif mutation == "long":
        path.write_bytes(b"x" * 33)
    elif mutation == "mode":
        path.chmod(0o644)
    elif mutation == "link":
        os.link(path, Path(value.directory) / "alias")
    elif mutation == "symlink":
        backup = Path(value.directory) / "original"
        path.rename(backup)
        path.symlink_to(backup)
    elif mutation == "fifo":
        path.unlink()
        os.mkfifo(path, 0o600)
    refused(value)


def test_seed_public_pin_and_peer_pin_must_match(tmp_path):
    value = selection(tmp_path)
    for field in ("own_public", "peer_public"):
        fields = {
            "directory": value.directory,
            "role": value.role,
            "generation": value.generation,
            "own_public": value.own_public,
            "peer_public": value.peer_public,
        }
        fields[field] = b"x" * 32
        refused(RoleKeySelection(**fields))
    Path(value.directory, "own.seed").write_bytes(b"x" * 32)
    refused(value)


def test_private_directory_and_nofollow_ancestry(tmp_path):
    value = selection(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(value.directory, target_is_directory=True)
    refused(
        RoleKeySelection(
            str(alias), value.role, value.generation, value.own_public, value.peer_public
        )
    )
    Path(value.directory).chmod(0o755)
    refused(value)


def test_close_uncertainty_is_retained_and_never_retried(tmp_path, monkeypatch):
    value = selection(tmp_path)
    close = os.close
    calls = []

    def uncertain_once(fd):
        calls.append(fd)
        close(fd)
        if len(calls) == 1:
            raise OSError("synthetic ambiguous close")

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", uncertain_once)
        owner = refused(value)
        before = list(calls)
        assert owner.close_local() is False
        assert calls == before
    assert sum(item.unknown for item in owner._records) == 1


def test_input_error_does_not_embed_keys_or_paths(tmp_path):
    value = selection(tmp_path)
    Path(value.directory, "peer.pub").unlink()
    with pytest.raises(CredentialAcquisitionError) as error:
        StartupRoleKeyFiles(value)
    assert str(error.value) == "BI1_CREDENTIAL_FILES_REFUSED"
    assert value.directory not in repr(error.value.failed_owner)


def test_reinitialization_cannot_revive_retired_owner_or_discard_records(tmp_path):
    value = selection(tmp_path)
    owner = StartupRoleKeyFiles(value)
    original_records = owner._records
    original_refs = tuple(original_records)
    owner.retire()
    with pytest.raises(CredentialAcquisitionError):
        StartupRoleKeyFiles.__init__(owner, value)
    assert owner._records is original_records and tuple(owner._records) == original_refs
    assert owner._refused and not owner._ready and owner._private_key is None


def test_key_aliases_cleared_before_failure_traceback_leaves_loader(tmp_path, monkeypatch):
    value = selection(tmp_path)
    close = os.close
    count = 0

    def uncertain(fd):
        nonlocal count
        count += 1
        close(fd)
        if count == 1:
            raise OSError("synthetic close uncertainty after derivation")

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", uncertain)
        with pytest.raises(CredentialAcquisitionError) as caught:
            StartupRoleKeyFiles(value)
    assert caught.value.__context__ is None
    traceback = caught.value.__traceback__
    checked = False
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_code.co_name == "__init__" and frame.f_code.co_filename.endswith(
            "presentation_credential_files.py"
        ):
            checked = True
            assert frame.f_locals["values"] == []
            for name in ("seed", "data", "key", "own_public", "peer_public", "derived"):
                assert frame.f_locals[name] is None
        traceback = traceback.tb_next
    assert checked


def test_retirement_during_final_close_cannot_publish_ready_key(tmp_path, monkeypatch):
    value = selection(tmp_path)
    owner = StartupRoleKeyFiles.__new__(StartupRoleKeyFiles)
    close = os.close
    retired = False

    def retire_during_close(fd):
        nonlocal retired
        close(fd)
        if not retired:
            retired = True
            owner.retire()

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", retire_during_close)
        with pytest.raises(CredentialAcquisitionError):
            StartupRoleKeyFiles.__init__(owner, value)
    assert retired and owner._refused and not owner._ready and owner._private_key is None
    assert all(item.closed for item in owner._records)


def test_foreign_process_context_refuses_before_descriptor_effects(tmp_path, monkeypatch):
    value = selection(tmp_path)
    owner = StartupRoleKeyFiles(value)
    # Retain one real disposable descriptor so this case would cause a native
    # close without the original-process guard; closed records alone prove none.
    fd = os.open(Path(value.directory) / "own.pub", os.O_RDONLY | os.O_CLOEXEC)
    held = type(owner._records[0])(fd=fd)
    owner._records.append(held)
    original = owner._process
    owner._process = (-1, os.geteuid())

    def forbidden(fd):
        raise AssertionError("foreign context must not touch original descriptors")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "close", forbidden)
            assert owner.close_local() is False
        assert owner._refused and not held.close_attempted
        assert os.fstat(fd).st_size == 32
    finally:
        owner._process = original
        assert owner.close_local()

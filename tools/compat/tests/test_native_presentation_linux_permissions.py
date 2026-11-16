"""Actual owned synthetic filesystem hardening; no live home or software execution."""

import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "fresh_permissions", Path(__file__).parents[1] / "native_presentation_linux_permissions.py"
)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)


@pytest.fixture
def trees(tmp_path):
    root = tmp_path / "owned-fresh"
    root.mkdir(mode=0o700)
    (root / "python-package").mkdir(mode=0o700)
    prefix = root / "python-package/python"
    prefix.mkdir(mode=0o700)
    venv = root / "venv"
    venv.mkdir(mode=0o700)
    return root, prefix, venv


def test_complete_inventory_precedes_strict_mode_drop_and_bytes_are_unchanged(trees, monkeypatch):
    root, prefix, venv = trees
    directory = prefix / "lib"
    directory.mkdir(mode=0o700)
    directory.chmod(0o777)
    paths = [directory / "sample.py", venv / "sample.py"]
    for path in paths:
        path.write_bytes(b"synthetic-unmodified")
        path.chmod(0o666)
    alias = venv / "alias"
    alias.symlink_to(paths[0])
    before = {str(p): (p.stat().st_ino, p.read_bytes()) for p in paths}
    original = module.os.fchmod
    observed = []

    def checked_fchmod(fd, mode):
        receipt = json.loads((root / "permission-normalization.json").read_text())
        assert receipt["completeOffenderInventory"] is True
        assert len(receipt["offenders"]) == 3
        assert receipt["stage"] == "hardening"
        observed.append(mode)
        return original(fd, mode)

    monkeypatch.setattr(module.os, "fchmod", checked_fchmod)
    result = module.harden(root, prefix, venv)
    assert result["stage"] == "complete" and observed == [0o755, 0o644, 0o644]
    assert alias.is_symlink() and alias.resolve() == paths[0]
    for path in paths:
        assert (path.stat().st_ino, path.read_bytes()) == before[str(path)]
        row = next(x for x in result["changes"] if x.get("inode") == path.stat().st_ino)
        assert row["beforeMode"] == 0o666 and row["afterMode"] == 0o644
        assert row["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert row["unchangedBytes"] is True


@pytest.mark.parametrize("fault", ["hardlink", "outside-symlink", "fifo", "setid"])
def test_bad_full_inventory_refuses_before_any_permission_change(trees, fault):
    root, prefix, venv = trees
    early = prefix / "a-early"
    early.write_bytes(b"synthetic-first")
    early.chmod(0o666)
    bad = venv / "bad"
    outside = root.parent / "outside"
    outside.write_bytes(b"synthetic-outside")
    outside.chmod(0o666)
    if fault == "hardlink":
        os.link(early, bad)
    elif fault == "outside-symlink":
        bad.symlink_to(outside)
    elif fault == "fifo":
        os.mkfifo(bad, 0o600)
    else:
        bad.write_bytes(b"synthetic")
        bad.chmod(0o4644)
    with pytest.raises(module.SoftwarePermissionError):
        module.harden(root, prefix, venv)
    assert early.stat().st_mode & 0o777 == 0o666
    assert outside.stat().st_mode & 0o777 == 0o666
    receipt = json.loads((root / "permission-normalization.json").read_text())
    assert receipt["stage"] == "quarantined" and receipt["changes"] == []
    assert receipt["completeOffenderInventory"] is False


def test_effect_followed_by_lost_result_quarantines_and_cannot_replay(trees, monkeypatch):
    root, prefix, venv = trees
    path = venv / "sample"
    path.write_bytes(b"synthetic")
    path.chmod(0o666)
    original = module.os.fchmod

    def lost_result(fd, mode):
        original(fd, mode)
        raise OSError("synthetic lost fchmod return")

    monkeypatch.setattr(module.os, "fchmod", lost_result)
    with pytest.raises(OSError, match="synthetic lost"):
        module.harden(root, prefix, venv)
    assert path.stat().st_mode & 0o777 == 0o644
    receipt = json.loads((root / "permission-normalization.json").read_text())
    assert receipt["stage"] == "quarantined" and receipt["retryAllowed"] is False
    assert receipt["changes"] == [] and receipt["completeOffenderInventory"] is True
    with pytest.raises(module.SoftwarePermissionError):
        module.harden(root, prefix, venv)


def test_inode_replacement_after_inventory_is_refused(trees, monkeypatch):
    root, prefix, venv = trees
    path = venv / "sample"
    path.write_bytes(b"first")
    path.chmod(0o666)
    replacement = root / "replacement"
    replacement.write_bytes(b"second")
    replacement.chmod(0o666)
    original = module.write_receipt

    def replace_once(destination, receipt):
        original(destination, receipt)
        if receipt["stage"] == "inventory-complete":
            os.replace(replacement, path)

    monkeypatch.setattr(module, "write_receipt", replace_once)
    with pytest.raises(module.SoftwarePermissionError):
        module.harden(root, prefix, venv)
    assert path.read_bytes() == b"second" and path.stat().st_mode & 0o777 == 0o666


def test_byte_mutation_during_mode_change_cannot_be_admitted(trees, monkeypatch):
    root, prefix, venv = trees
    path = venv / "sample"
    path.write_bytes(b"first")
    path.chmod(0o666)
    original = module.os.fchmod

    def mutate(fd, mode):
        original(fd, mode)
        path.write_bytes(b"other")

    monkeypatch.setattr(module.os, "fchmod", mutate)
    with pytest.raises(module.SoftwarePermissionError):
        module.harden(root, prefix, venv)
    receipt = json.loads((root / "permission-normalization.json").read_text())
    assert receipt["stage"] == "quarantined" and receipt["changes"] == []


def test_private_root_and_fixed_software_scope_required(trees):
    root, prefix, venv = trees
    with pytest.raises(module.SoftwarePermissionError):
        module.harden(root, prefix, root.parent)
    assert not (root / "permission-normalization.json").exists()
    root.chmod(0o755)
    with pytest.raises(module.SoftwarePermissionError):
        module.harden(root, prefix, venv)
    assert not (root / "permission-normalization.json").exists()


@pytest.mark.parametrize("failure_phase", ["file", "parent"])
def test_inventory_sync_failure_blocks_every_mode_change_and_replay(
    trees, monkeypatch, failure_phase
):
    root, prefix, venv = trees
    path = venv / "sample"
    path.write_bytes(b"synthetic")
    path.chmod(0o666)
    original = module.os.fsync
    failures, effects = [], []

    def fail_inventory_sync(fd):
        directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        ledger = root / (
            "permission-normalization.json"
            if directory
            else "permission-normalization.json.pending"
        )
        phase = "parent" if directory else "file"
        if not failures and phase == failure_phase and ledger.exists():
            body = json.loads(ledger.read_text())
            if body["stage"] == "inventory-complete":
                failures.append(phase)
                raise OSError("synthetic inventory fsync failure")
        return original(fd)

    def forbidden_effect(fd, mode):
        effects.append(mode)
        raise AssertionError("fchmod must not precede successful inventory sync")

    monkeypatch.setattr(module.os, "fsync", fail_inventory_sync)
    monkeypatch.setattr(module.os, "fchmod", forbidden_effect)
    with pytest.raises(OSError, match="synthetic inventory fsync failure"):
        module.harden(root, prefix, venv)
    assert failures == [failure_phase] and effects == []
    assert path.stat().st_mode & 0o777 == 0o666
    with pytest.raises(module.SoftwarePermissionError):
        module.harden(root, prefix, venv)

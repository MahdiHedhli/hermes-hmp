"""Real kernel boundary checks using exclusively synthetic temporary files."""

import os
import stat
import tempfile
from pathlib import Path

import pytest

from hmp_plugin.presentation_files import DIR_FLAGS, LEAF_FLAGS
from hmp_plugin.presentation_posix import PosixFileOps


def test_fixed_leaf_flags_refuse_symlink_and_preserve_target():
    fs = PosixFileOps()
    with tempfile.TemporaryDirectory() as root:
        p = Path(root)
        (p / "target").write_bytes(b"synthetic-private-target")
        (p / "avatar.png").symlink_to("target")
        parent = fs.open(root, DIR_FLAGS)
        try:
            with pytest.raises(OSError):
                fs.open("avatar.png", LEAF_FLAGS, dir_fd=parent)
            assert (p / "target").read_bytes() == b"synthetic-private-target"
            assert stat.S_ISLNK(fs.stat("avatar.png", dir_fd=parent).st_mode)
        finally:
            fs.close(parent)


def test_held_descriptor_stays_bound_when_name_replaced():
    fs = PosixFileOps()
    with tempfile.TemporaryDirectory() as root:
        p = Path(root)
        (p / "profile.yaml").write_bytes(b"synthetic-original")
        parent = fs.open(root, DIR_FLAGS)
        leaf = fs.open("profile.yaml", LEAF_FLAGS, dir_fd=parent)
        try:
            held = fs.fstat(leaf)
            (p / "replacement").write_bytes(b"synthetic-replacement")
            os.replace(p / "replacement", p / "profile.yaml")
            assert fs.stat("profile.yaml", dir_fd=parent).st_ino != held.st_ino
            assert fs.read(leaf, 64) == b"synthetic-original"
            assert fs.fstat(leaf).st_ino == held.st_ino
        finally:
            fs.close(leaf)
            fs.close(parent)


def test_directory_flags_refuse_symlink():
    fs = PosixFileOps()
    with tempfile.TemporaryDirectory() as root:
        p = Path(root)
        (p / "real").mkdir()
        (p / "assets").symlink_to("real", target_is_directory=True)
        parent = fs.open(root, DIR_FLAGS)
        try:
            with pytest.raises(OSError):
                fs.open("assets", DIR_FLAGS, dir_fd=parent)
        finally:
            fs.close(parent)

"""Whole fixed-reader transaction on synthetic files and real kernel descriptors.

The optional test parent controls fixture placement only. No live Hermes directory
is opened; unsafe ancestor policy causes a skip rather than relaxing the reader.
"""
import os
import stat
import tempfile
import time
from pathlib import Path

import pytest

from hmp_plugin.presentation_files import (
    DirectoryRule, PresentationReadError, bind_owned_worker_read,
    read_fixed_presentation_files,
)
from hmp_plugin.presentation_posix import PosixFileOps
from hmp_plugin.presentation_yaml_adapter import parse_presentation_yaml


@pytest.fixture
def scope():
    parent = Path(os.environ.get('HMP_PRESENTATION_TEST_PARENT', str(Path.cwd()))).resolve()
    # Refuse before fixture creation if a real ancestor violates the frozen policy.
    for p in (parent, *parent.parents):
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode not in (0o700, 0o750, 0o755):
            pytest.skip('synthetic fixture requires secure ancestor modes')
    with tempfile.TemporaryDirectory(prefix='hmp-bi1-synthetic-', dir=parent) as raw:
        home = Path(raw)
        (home / 'profile.yaml').write_bytes(b"display_name: Synthetic\nui_meta: {hermes-bots: {shape: hexagon, color: '#8b5cf6', custom: true}}\n")
        (home / 'profile.yaml').chmod(0o600)
        parts = [home, *home.parents][::-1]
        rules = tuple(DirectoryRule(str(p), p.stat().st_uid, p.stat().st_gid,
                                   (stat.S_IMODE(p.stat().st_mode),)) for p in parts)
        bound = bind_owned_worker_read(
            root_path=str(home), home_path=str(home), profile=None,
            service_uid=os.getuid(), service_gid=os.getgid(), directory_rules=rules,
            deadline=time.monotonic()+2., challenge='a'*64,
            source_manifest_sha256='b'*64, worker_go_challenge='a'*64,
        )
        yield home, bound


class TrackedOS(PosixFileOps):
    def __init__(self):
        self.opened = set()
    def open(self, *args, **kwargs):
        fd = super().open(*args, **kwargs)
        self.opened.add(fd)
        return fd
    def close(self, fd):
        super().close(fd)
        self.opened.remove(fd)


def test_actual_transaction_then_closed_yaml_projection(scope):
    _, bound = scope
    fs = TrackedOS()
    result = read_fixed_presentation_files(bound, fs=fs, clock=time.monotonic)
    fields = parse_presentation_yaml(result.metadata, clock=time.monotonic, deadline=bound.deadline)
    assert fields.display_name == 'Synthetic'
    assert fields.shape == 'hexagon' and fields.custom is True
    assert result.avatar is None
    assert fs.opened == set()
    assert result.budget['readBytesCharged'] <= 4_131_076


def test_actual_symlink_metadata_refused_with_all_owned_fds_closed(scope):
    home, bound = scope
    (home / 'other').write_bytes(b'display_name: Never read\n')
    (home / 'profile.yaml').unlink()
    (home / 'profile.yaml').symlink_to('other')
    fs = TrackedOS()
    with pytest.raises(PresentationReadError):
        read_fixed_presentation_files(bound, fs=fs, clock=time.monotonic)
    assert fs.opened == set()


def test_actual_metadata_replacement_during_read_is_refused(scope):
    home, bound = scope
    class ReplacingOS(TrackedOS):
        replaced = False
        def read(self, fd, size):
            body = super().read(fd, size)
            if not self.replaced:
                self.replaced = True
                replacement = home / 'replacement'
                replacement.write_bytes(b'display_name: Changed\n')
                replacement.chmod(0o600)
                os.replace(replacement, home / 'profile.yaml')
            return body
    fs = ReplacingOS()
    with pytest.raises(PresentationReadError):
        read_fixed_presentation_files(bound, fs=fs, clock=time.monotonic)
    assert fs.replaced and fs.opened == set()

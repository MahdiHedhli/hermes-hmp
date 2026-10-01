"""Tests for tools/research/local_media_file_safety.py (G3 filesystem safety prototype).

Real OS temp directories (0700) and private files (0600); no Hermes, network, database or real
media. Every refusal test has a positive control in the same layout, so a refusal is attributable
to the property under test rather than to a broken fixture. Only closed metadata is asserted.
"""

from __future__ import annotations

import ast
import contextlib
import errno
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import local_media_file_safety as fs
import pytest

Out = fs.Outcome
NAME = "gen_20260930_120000_abcd1234.png"
PAYLOAD = b"SYNTHETIC-RASTER-MARKER-" + bytes(range(256)) * 3  # not an image on purpose
TOOLS_RESEARCH_DIR = Path(fs.__file__).resolve().parent


def make_profile(root: Path, name: str = "alpha", *, payload: bytes | None = PAYLOAD) -> Path:
    home = root / name
    images = home / "cache" / "images"
    images.mkdir(parents=True, mode=0o700)
    for directory in (home, home / "cache", images):
        directory.chmod(0o700)
    if payload is not None:
        write_private(images / NAME, payload)
    return home


def write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.utime(path, ns=(10**18, 10**18))  # fixed old mtime: a later write must move it


def images_of(home: Path) -> Path:
    return home / "cache" / "images"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    base = tmp_path / "root"
    base.mkdir(mode=0o700)
    return base


@pytest.fixture
def home(root: Path) -> Path:
    return make_profile(root)


class FdTracker:
    """Records descriptors opened and closed through `os`, so leaks are measurable."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, skip_close: bool = False) -> None:
        self.opened: set[int] = set()
        self.closed: set[int] = set()
        self.reads = 0
        real_open, real_close, real_read = os.open, os.close, os.read

        def tracked_open(*args: object, **kwargs: object) -> int:
            fd = real_open(*args, **kwargs)  # type: ignore[arg-type]
            self.opened.add(fd)
            return fd

        def tracked_close(fd: int) -> None:
            if skip_close:
                return
            self.closed.add(fd)
            real_close(fd)

        def tracked_read(fd: int, n: int) -> bytes:
            self.reads += 1
            return real_read(fd, n)

        monkeypatch.setattr(os, "open", tracked_open)
        monkeypatch.setattr(os, "close", tracked_close)
        monkeypatch.setattr(os, "read", tracked_read)
        self._real_close = real_close

    @property
    def leaked(self) -> set[int]:
        return self.opened - self.closed

    def cleanup(self) -> None:
        for fd in self.leaked:
            with contextlib.suppress(OSError):
                self._real_close(fd)


def read(home: Path, candidate: str = NAME, **kwargs: object) -> fs.ReadResult:
    return fs.read_profile_cache_image(home, candidate, **kwargs)  # type: ignore[arg-type]


def assert_refused(result: fs.ReadResult, outcome: fs.Outcome) -> None:
    assert result.outcome is outcome
    assert result.byte_count == 0
    with pytest.raises(ValueError, match="no bytes"):
        result.unvalidated_raster_bytes()


# ---- positive control and public surface -------------------------------------------------


def test_valid_regular_bounded_file(home: Path) -> None:
    result = read(home)
    assert result.outcome is Out.OK
    assert result.byte_count == len(PAYLOAD)
    assert result.unvalidated_raster_bytes() == PAYLOAD


def test_size_bounds_exact_and_over(root: Path) -> None:
    home = make_profile(root, payload=None)
    path = images_of(home) / NAME
    write_private(path, b"x" * fs.MAX_BYTES)
    assert read(home).byte_count == fs.MAX_BYTES
    path.unlink()
    write_private(path, b"x" * (fs.MAX_BYTES + 1))
    assert_refused(read(home), Out.OVERSIZE)


def test_oversize_refused_before_any_read(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_private(images_of(home) / "big.bin", b"x" * 100)
    tracker = FdTracker(monkeypatch)
    try:
        assert_refused(read(home, "big.bin", max_bytes=99), Out.OVERSIZE)
        assert tracker.reads == 0
        assert read(home, "big.bin", max_bytes=100).outcome is Out.OK  # control: bound is the cause
        assert tracker.reads > 0
    finally:
        tracker.cleanup()


def test_empty_file_refused(home: Path) -> None:
    write_private(images_of(home) / "empty.png", b"")
    assert_refused(read(home, "empty.png"), Out.EMPTY)


def test_bytes_are_never_qualified_as_raster(home: Path) -> None:
    png_like = b"\x89PNG\r\n\x1a\n" + b"junk"
    write_private(images_of(home) / "a.png", png_like)
    write_private(images_of(home) / "b.txt", b"not an image at all")
    for name in ("a.png", "b.txt", NAME):
        result = read(home, name)
        assert result.outcome is Out.OK  # no codec, magic or extension policy runs here
        report = result.public_report()
        assert report["bytes_label"] == "unvalidated_raster_bytes"
        assert report["raster_validated"] is False
        assert not {"mime", "format", "width", "height", "frames", "animated"} & report.keys()


def test_public_report_and_repr_leak_nothing(home: Path) -> None:
    result = read(home)
    dumped = json.dumps(result.public_report()) + repr(result) + str(result)
    for secret in (str(home), NAME, "SYNTHETIC-RASTER-MARKER", "alpha"):
        assert secret not in dumped
    assert set(result.public_report()) == {
        "outcome",
        "byte_count",
        "bytes_label",
        "raster_validated",
        "binding_held",
    }
    st = os.stat(images_of(home) / NAME)
    for number in (st.st_ino, st.st_dev):
        assert f'"{number}"' not in dumped
    refused = read(home, "missing.png")
    assert refused.public_report()["binding_held"] is False
    assert str(home) not in json.dumps(refused.public_report())


def test_public_reports_for_every_outcome_use_closed_keys(root: Path) -> None:
    keys = None
    for outcome in fs.Outcome:
        report = fs.ReadResult(outcome).public_report()
        keys = keys or set(report)
        assert set(report) == keys
        assert report["binding_held"] is False or outcome is Out.OK


# ---- candidate grammar -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("candidate", "outcome"),
    [
        ("/etc/passwd", Out.CANDIDATE_ABSOLUTE),
        ("", Out.CANDIDATE_EMPTY),
        (".", Out.CANDIDATE_DOT),
        ("..", Out.CANDIDATE_DOT),
        ("../alpha/cache/images/x.png", Out.CANDIDATE_DOT),
        ("sub/../x.png", Out.CANDIDATE_DOT),
        ("./x.png", Out.CANDIDATE_DOT),
        ("sub/x.png", Out.CANDIDATE_NESTED),
        ("x.png/", Out.CANDIDATE_NESTED),
        ("sub\\x.png", Out.CANDIDATE_NESTED),
        ("a\x00b.png", Out.CANDIDATE_CONTROL),
        ("a\nb.png", Out.CANDIDATE_CONTROL),
        ("a\x1bb.png", Out.CANDIDATE_CONTROL),
        ("a\x7fb.png", Out.CANDIDATE_CONTROL),
        ("a\x85b.png", Out.CANDIDATE_CONTROL),
        ("a‮b.png", Out.CANDIDATE_CONTROL),
        ("a\ud800b.png", Out.CANDIDATE_CONTROL),
        ("a" * (fs.MAX_NAME_BYTES + 1), Out.CANDIDATE_TOO_LONG),
        ("é" * (fs.MAX_NAME_BYTES // 2 + 1), Out.CANDIDATE_TOO_LONG),
        (b"x.png", Out.CANDIDATE_TYPE),
        (None, Out.CANDIDATE_TYPE),
    ],
)
def test_candidate_grammar_refused_without_filesystem_access(
    home: Path, monkeypatch: pytest.MonkeyPatch, candidate: object, outcome: fs.Outcome
) -> None:
    tracker = FdTracker(monkeypatch)
    try:
        assert_refused(read(home, candidate), outcome)  # type: ignore[arg-type]
        assert not tracker.opened  # refused before touching the filesystem
    finally:
        tracker.cleanup()


class _GrammarOverride(str):
    """Hostile in-process str subclass whose methods hide the separators from the grammar."""

    def __contains__(self, item: object) -> bool:
        return False

    def startswith(self, *args: object, **kwargs: object) -> bool:  # type: ignore[override]
        return False


def test_str_subclass_cannot_override_the_candidate_grammar(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evil = _GrammarOverride("../images/" + NAME)
    assert isinstance(evil, str)
    # Old classifier (isinstance check, rebuilt from the current source): accepts the traversal.
    source = Path(fs.__file__).read_text(encoding="utf-8")
    assert "type(candidate) is not str" in source
    legacy: dict[str, object] = {}
    exec(  # noqa: S102 - synthetic mutation of this module's own source, test only
        compile(
            source.replace("type(candidate) is not str", "not isinstance(candidate, str)"),
            "legacy",
            "exec",
        ),
        legacy,
    )
    assert legacy["classify_candidate"](evil) is None  # type: ignore[operator]
    plain = legacy["classify_candidate"]("../images/" + NAME)  # control: plain str is refused
    assert plain.value == Out.CANDIDATE_DOT.value  # type: ignore[attr-defined]
    # Repaired code refuses before any filesystem access.
    tracker = FdTracker(monkeypatch)
    try:
        assert_refused(read(home, evil), Out.CANDIDATE_TYPE)
        assert not tracker.opened
    finally:
        tracker.cleanup()
    assert read(home, str(NAME)).outcome is Out.OK  # control: a plain str is fine


def test_candidate_grammar_accepts_native_shapes(home: Path) -> None:
    for name in (
        "openai_20260930_120000_abcd1234.png",
        "inbound_0123456789ab.jpg",
        ".hid",
        "...",
    ):
        write_private(images_of(home) / name, PAYLOAD)
        assert read(home, name).outcome is Out.OK
    long_ok = "a" * fs.MAX_NAME_BYTES
    write_private(images_of(home) / long_ok, PAYLOAD)
    assert read(home, long_ok).outcome is Out.OK


def test_nested_is_refused_even_when_the_file_exists(home: Path) -> None:
    nested = images_of(home) / "sub"
    nested.mkdir(mode=0o700)
    write_private(nested / "x.png", PAYLOAD)
    write_private(images_of(home) / "x.png", PAYLOAD)
    assert_refused(read(home, "sub/x.png"), Out.CANDIDATE_NESTED)
    assert read(home, "x.png").outcome is Out.OK  # flat control


def test_absolute_path_to_a_real_file_is_refused(home: Path) -> None:
    absolute = str(images_of(home) / NAME)
    assert_refused(read(home, absolute), Out.CANDIDATE_ABSOLUTE)
    assert read(home).outcome is Out.OK


@pytest.mark.parametrize("bad_home", ["relative/home", "", "has\0nul"])
def test_profile_home_must_be_absolute(bad_home: str) -> None:
    assert_refused(fs.read_profile_cache_image(bad_home, NAME), Out.PROFILE_HOME_INVALID)


# ---- profile and root confinement --------------------------------------------------------


def test_selected_profile_a_and_b_are_isolated(root: Path) -> None:
    alpha = make_profile(root, "alpha", payload=b"alpha-bytes")
    beta = make_profile(root, "beta", payload=b"beta-bytes")
    assert read(alpha).unvalidated_raster_bytes() == b"alpha-bytes"
    assert read(beta).unvalidated_raster_bytes() == b"beta-bytes"
    # B's file by absolute or relative traversal from A: refused, never served.
    assert_refused(read(alpha, str(images_of(beta) / NAME)), Out.CANDIDATE_ABSOLUTE)
    assert_refused(read(alpha, f"../../../beta/cache/images/{NAME}"), Out.CANDIDATE_DOT)
    # A file that exists only in B is unavailable for A: no cross-profile fallback.
    write_private(images_of(beta) / "only_beta.png", b"beta-only")
    assert_refused(read(alpha, "only_beta.png"), Out.UNAVAILABLE)
    assert read(beta, "only_beta.png").outcome is Out.OK


def test_symlink_to_foreign_profile_file_refused(root: Path) -> None:
    alpha = make_profile(root, "alpha", payload=None)
    beta = make_profile(root, "beta", payload=b"beta-bytes")
    (images_of(alpha) / "link.png").symlink_to(images_of(beta) / NAME)
    assert_refused(read(alpha, "link.png"), Out.SYMLINK_REFUSED)
    assert read(beta).outcome is Out.OK


def test_sibling_cache_roots_are_never_consulted(home: Path) -> None:
    for sibling in ("documents", "videos"):
        (home / "cache" / sibling).mkdir(mode=0o700)
        write_private(home / "cache" / sibling / "only.png", PAYLOAD)
    legacy = home / "image_cache"
    legacy.mkdir(mode=0o700)
    write_private(legacy / "only.png", PAYLOAD)
    assert_refused(read(home, "only.png"), Out.UNAVAILABLE)


# ---- missing / swept ---------------------------------------------------------------------


def test_initial_missing_file_cache_images_and_home(root: Path) -> None:
    home = make_profile(root, payload=None)
    assert_refused(read(home), Out.UNAVAILABLE)  # swept or never written
    shutil.rmtree(images_of(home))
    assert_refused(read(home), Out.UNAVAILABLE)
    shutil.rmtree(home / "cache")
    assert_refused(read(home), Out.UNAVAILABLE)
    shutil.rmtree(home)
    assert_refused(read(home), Out.PROFILE_HOME_UNAVAILABLE)
    # Control: recreating the layout and file makes the same call succeed.
    assert read(make_profile(root)).outcome is Out.OK


def test_file_swept_while_open_is_refused_not_served(home: Path) -> None:
    path = images_of(home) / NAME
    assert_refused(read(home, _hooks={"before_revalidate": path.unlink}), Out.BINDING_LOST)
    write_private(path, PAYLOAD)
    assert_refused(read(home, _hooks={"after_chunk": path.unlink}), Out.CHANGED_DURING_READ)
    write_private(path, PAYLOAD)
    assert read(home, _hooks={"after_chunk": lambda: None}).outcome is Out.OK  # control


def test_no_fallback_copy_or_outside_location(home: Path, root: Path) -> None:
    before = sorted(p.name for p in root.rglob("*"))
    (images_of(home) / NAME).unlink()
    stray = root / NAME
    write_private(stray, PAYLOAD)  # same name beside the profile; must never be used
    assert_refused(read(home), Out.UNAVAILABLE)
    stray.unlink()
    assert sorted(p.name for p in root.rglob("*")) == sorted(n for n in before if n != NAME)


# ---- symlinks, hardlinks, special files --------------------------------------------------


def test_symlink_final_component_refused(home: Path) -> None:
    (images_of(home) / "link.png").symlink_to(NAME)
    assert_refused(read(home, "link.png"), Out.SYMLINK_REFUSED)
    assert read(home).outcome is Out.OK


def test_dangling_symlink_final_component_refused(home: Path) -> None:
    (images_of(home) / "dangling.png").symlink_to("nowhere.png")
    assert_refused(read(home, "dangling.png"), Out.SYMLINK_REFUSED)


def test_symlink_to_directory_final_component_refused(home: Path) -> None:
    (images_of(home) / "dirlink").symlink_to(".")
    assert_refused(read(home, "dirlink"), Out.SYMLINK_REFUSED)


@pytest.mark.parametrize("which", ["home", "cache", "images"])
def test_symlink_ancestor_refused_though_target_holds_a_valid_file(root: Path, which: str) -> None:
    real = make_profile(root, "real")
    assert read(real).outcome is Out.OK  # control: the target layout is valid
    home = root / "via"
    if which == "home":
        home.symlink_to(real)
    else:
        home.mkdir(mode=0o700)
        if which == "cache":
            (home / "cache").symlink_to(real / "cache")
        else:
            (home / "cache").mkdir(mode=0o700)
            (home / "cache" / "images").symlink_to(images_of(real))
    expected = Out.PROFILE_HOME_INVALID if which == "home" else Out.ANCESTOR_REFUSED
    assert_refused(read(home), expected)


def test_cache_that_is_a_regular_file_is_refused(root: Path) -> None:
    home = root / "odd"
    home.mkdir(mode=0o700)
    write_private(home / "cache", b"not a directory")
    assert_refused(read(home), Out.ANCESTOR_REFUSED)


def test_hardlink_refused_including_created_after_open(home: Path, root: Path) -> None:
    path = images_of(home) / NAME
    outside = root / "outside_link"
    os.link(path, outside)
    assert_refused(read(home), Out.HARDLINKED)
    outside.unlink()
    assert read(home).outcome is Out.OK  # control: same file, one link

    def add_link() -> None:
        os.link(path, outside)

    assert_refused(read(home, _hooks={"after_chunk": add_link}), Out.CHANGED_DURING_READ)


def test_directory_final_component_refused(home: Path) -> None:
    (images_of(home) / "adir").mkdir(mode=0o700)
    assert_refused(read(home, "adir"), Out.NOT_REGULAR)


def test_socket_final_component_refused_if_available(root: Path) -> None:
    short = Path(tempfile.mkdtemp(prefix="hs", dir="/tmp")).resolve()  # AF_UNIX path limit
    try:
        home = make_profile(short, "p")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            try:
                sock.bind(str(images_of(home) / "s"))
            except OSError:
                pytest.skip("cannot bind a unix socket here")
            assert_refused(read(home, "s"), Out.NOT_REGULAR)
            assert read(home).outcome is Out.OK
        finally:
            sock.close()
    finally:
        shutil.rmtree(short, ignore_errors=True)


FIFO_SCRIPT = """
import sys
sys.path.insert(0, {tools!r})
import local_media_file_safety as fs
r = fs.read_profile_cache_image({home!r}, "pipe")
print(r.outcome.value)
"""

BLOCKING_OPEN_SCRIPT = """
import os
os.open({fifo!r}, os.O_RDONLY)
"""


def test_fifo_refused_without_hanging(home: Path) -> None:
    fifo = images_of(home) / "pipe"
    os.mkfifo(fifo, 0o600)
    # Causal guard: a plain blocking open of this FIFO does hang, so the deadline is meaningful.
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            [sys.executable, "-c", BLOCKING_OPEN_SCRIPT.format(fifo=str(fifo))],
            timeout=2,
            check=False,
            capture_output=True,
        )
    started = time.monotonic()
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            FIFO_SCRIPT.format(tools=str(TOOLS_RESEARCH_DIR), home=str(home)),
        ],
        timeout=15,
        check=False,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr[-200:]
    assert done.stdout.strip() == "not_regular"
    assert time.monotonic() - started < 15


def test_fifo_with_idle_writer_refused_before_read(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fifo = images_of(home) / "pipe"
    os.mkfifo(fifo, 0o600)
    writer = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)  # a peer that never writes
    tracker = FdTracker(monkeypatch)
    try:
        assert_refused(read(home, "pipe"), Out.NOT_REGULAR)
        assert tracker.reads == 0
    finally:
        tracker.cleanup()
        os.close(writer)


# ---- mutation during the read ------------------------------------------------------------


def test_growth_during_read_refused(home: Path) -> None:
    path = images_of(home) / NAME

    grown = []

    def grow() -> None:
        if not grown:
            grown.append(True)
            with open(path, "ab") as handle:
                handle.write(b"more")

    assert_refused(read(home, _hooks={"after_chunk": grow}), Out.CHANGED_DURING_READ)
    assert read(home).byte_count == len(PAYLOAD) + 4  # control: the grown file reads cleanly


def test_growth_across_the_bound_never_buffers_past_bound_plus_one(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = images_of(home) / "g.bin"
    write_private(path, b"x" * 10)
    total = 0
    real_read = os.read

    def counting_read(fd: int, n: int) -> bytes:
        nonlocal total
        data = real_read(fd, n)
        total += len(data)
        return data

    def grow() -> None:
        with open(path, "ab") as handle:
            handle.write(b"y" * 1000)

    monkeypatch.setattr(os, "read", counting_read)
    result = read(home, "g.bin", max_bytes=20, _hooks={"after_chunk": grow}, _chunk_size=4)
    assert_refused(result, Out.CHANGED_DURING_READ)
    assert total <= 21


def test_truncation_during_read_refused(home: Path) -> None:
    path = images_of(home) / NAME
    result = read(home, _hooks={"after_chunk": lambda: os.truncate(path, 5)}, _chunk_size=64)
    assert_refused(result, Out.CHANGED_DURING_READ)


def test_same_size_content_change_during_read_refused(home: Path) -> None:
    path = images_of(home) / NAME

    def rewrite() -> None:
        fd = os.open(path, os.O_WRONLY)
        try:
            os.pwrite(fd, b"Z" * len(PAYLOAD), 0)
        finally:
            os.close(fd)

    assert_refused(read(home, _hooks={"before_second_fstat": rewrite}), Out.CHANGED_DURING_READ)
    assert read(home).outcome is Out.OK  # control: no mutation, no refusal


def test_same_inode_rewrite_after_second_fstat_refused_by_final_recheck(
    home: Path,
) -> None:
    path = images_of(home) / NAME

    def rewrite() -> None:
        fd = os.open(path, os.O_WRONLY)
        try:
            os.pwrite(fd, b"Z" * len(PAYLOAD), 0)  # same inode, same size
        finally:
            os.close(fd)
        os.utime(path, ns=(2 * 10**18, 2 * 10**18))  # deterministic timestamp movement

    before = path.stat()
    assert_refused(read(home, _hooks={"before_revalidate": rewrite}), Out.BINDING_LOST)
    after = path.stat()
    assert (after.st_ino, after.st_size) == (
        before.st_ino,
        before.st_size,
    )  # truly in place
    assert after.st_mtime_ns != before.st_mtime_ns
    assert read(home).outcome is Out.OK  # control: no mutation at the same seam, no refusal
    write_private(images_of(home) / "other.png", PAYLOAD)
    assert read(home, "other.png", _hooks={"before_revalidate": lambda: None}).outcome is Out.OK


def test_replacement_by_rename_while_fd_held_refused(home: Path, root: Path) -> None:
    path = images_of(home) / NAME
    other = root / "replacement"
    write_private(other, b"attacker-bytes")

    def replace() -> None:
        os.rename(other, path)

    # Late replacement: the held descriptor's stat is unchanged, only the name moved.
    assert_refused(read(home, _hooks={"before_revalidate": replace}), Out.BINDING_LOST)
    assert read(home).unvalidated_raster_bytes() == b"attacker-bytes"  # new file valid on its own


def test_replacement_by_rename_mid_read_refused(home: Path, root: Path) -> None:
    other = root / "replacement"
    write_private(other, b"attacker-bytes")
    result = read(home, _hooks={"after_chunk": lambda: os.rename(other, images_of(home) / NAME)})
    # The displaced inode loses its last link, so its own ctime/nlink already differ.
    assert_refused(result, Out.CHANGED_DURING_READ)


def test_replacement_by_symlink_while_fd_held_refused(home: Path) -> None:
    path = images_of(home) / NAME
    decoy = images_of(home) / "decoy.png"
    write_private(decoy, b"decoy-bytes")

    def swap() -> None:
        path.unlink()
        path.symlink_to(decoy)

    assert_refused(read(home, _hooks={"before_revalidate": swap}), Out.BINDING_LOST)


@pytest.mark.parametrize("level", ["images", "cache", "home"])
@pytest.mark.parametrize("moment", ["after_dirs_pinned", "after_chunk", "before_revalidate"])
def test_ancestor_rename_and_replacement_while_fd_held_refused(
    root: Path, level: str, moment: str
) -> None:
    home = make_profile(root, "alpha", payload=b"old-bytes")
    target = {"images": images_of(home), "cache": home / "cache", "home": home}[level]
    moved = root / f"{level}_moved"

    def rename_and_replace() -> None:
        os.rename(target, moved)
        # Same-name replacement with a plausible valid layout and file.
        if level == "home":
            make_profile(root, "alpha", payload=b"new-bytes")
        elif level == "cache":
            images = home / "cache" / "images"
            images.mkdir(parents=True, mode=0o700)
            write_private(images / NAME, b"new-bytes")
        else:
            images_of(home).mkdir(mode=0o700)
            write_private(images_of(home) / NAME, b"new-bytes")

    result = read(home, _hooks={moment: rename_and_replace})
    assert_refused(result, Out.BINDING_LOST)
    # Control: the replacement layout is itself valid for a fresh call.
    assert read(home).unvalidated_raster_bytes() == b"new-bytes"


def test_ancestor_renamed_away_without_replacement_refused(home: Path, root: Path) -> None:
    moved = root / "gone"
    result = read(home, _hooks={"after_chunk": lambda: os.rename(images_of(home), moved)})
    assert_refused(result, Out.BINDING_LOST)


def test_ancestor_replaced_by_symlink_after_pin_refused(home: Path, root: Path) -> None:
    other = make_profile(root, "other", payload=b"other-bytes")
    moved = root / "images_moved"

    def swap() -> None:
        os.rename(images_of(home), moved)
        images_of(home).symlink_to(images_of(other))

    assert_refused(read(home, _hooks={"before_revalidate": swap}), Out.BINDING_LOST)


def test_unrelated_mutation_does_not_refuse(home: Path, root: Path) -> None:
    def touch_neighbour() -> None:
        write_private(images_of(home) / "neighbour.png", b"n")
        (root / "alpha_other").mkdir()

    assert read(home, _hooks={"after_chunk": touch_neighbour}).outcome is Out.OK


# ---- platform ----------------------------------------------------------------------------


def test_unsupported_platform_refuses_without_fallback(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert fs.platform_supported()  # control
    monkeypatch.setattr(os, "supports_dir_fd", set())
    assert not fs.platform_supported()
    tracker = FdTracker(monkeypatch)
    try:
        assert_refused(read(home), Out.UNSUPPORTED_PLATFORM)
        assert not tracker.opened
    finally:
        tracker.cleanup()


@pytest.mark.parametrize("missing", ["O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "O_NONBLOCK"])
def test_missing_open_flag_is_unsupported(
    home: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.delattr(os, missing)
    assert_refused(read(home), Out.UNSUPPORTED_PLATFORM)


# ---- descriptor hygiene ------------------------------------------------------------------


def open_fd_count() -> int:
    return len(os.listdir("/dev/fd"))


def _scenarios(home: Path, root: Path) -> Iterator[Callable[[], fs.ReadResult]]:
    (images_of(home) / "empty.png").write_bytes(b"")
    (images_of(home) / "link.png").symlink_to(NAME)
    os.mkfifo(images_of(home) / "pipe", 0o600)
    (images_of(home) / "adir").mkdir()
    yield lambda: read(home)
    yield lambda: read(home, "missing.png")
    yield lambda: read(home, "empty.png")
    yield lambda: read(home, "link.png")
    yield lambda: read(home, "pipe")
    yield lambda: read(home, "adir")
    yield lambda: read(home, "../x")
    yield lambda: read(root / "no_such_home")
    yield lambda: read(home, max_bytes=5)
    yield lambda: read(home, _hooks={"after_chunk": lambda: os.truncate(images_of(home) / NAME, 3)})


def test_every_descriptor_is_closed_on_every_path(
    home: Path, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = open_fd_count()
    tracker = FdTracker(monkeypatch)
    try:
        for run in _scenarios(home, root):
            run()
        assert tracker.opened  # the scenarios did open descriptors
        assert not tracker.leaked
    finally:
        tracker.cleanup()
    monkeypatch.undo()
    assert open_fd_count() == baseline


def test_descriptors_closed_when_a_hook_raises(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class BoomError(RuntimeError):
        pass

    def boom() -> None:
        raise BoomError

    baseline = open_fd_count()
    tracker = FdTracker(monkeypatch)
    try:
        for moment in sorted(fs.HOOK_NAMES):
            with pytest.raises(BoomError):
                read(home, _hooks={moment: boom})
        assert tracker.opened
        assert not tracker.leaked
    finally:
        tracker.cleanup()
    monkeypatch.undo()
    assert open_fd_count() == baseline


@pytest.mark.parametrize("failing_call", [1, 2, 3, 4, 5])
def test_fstat_oserror_is_one_closed_refusal_and_descriptors_close(
    home: Path, monkeypatch: pytest.MonkeyPatch, failing_call: int
) -> None:
    # Calls 1-3 pin home/cache/images, 4 is the first file fstat, 5 the second.
    real_fstat = os.fstat
    calls = 0

    def flaky(fd: int) -> os.stat_result:
        nonlocal calls
        calls += 1
        if calls == failing_call:
            raise OSError(errno.EIO, "injected")
        return real_fstat(fd)

    baseline = open_fd_count()
    tracker = FdTracker(monkeypatch)
    try:
        monkeypatch.setattr(os, "fstat", flaky)
        assert_refused(read(home), Out.READ_FAILED)
        assert calls == failing_call  # stopped at the injected failure
        assert tracker.opened
        assert not tracker.leaked
        monkeypatch.setattr(os, "fstat", real_fstat)
        assert read(home).outcome is Out.OK  # control: the injection is the cause
    finally:
        tracker.cleanup()
    monkeypatch.undo()
    assert open_fd_count() == baseline


def test_leak_detector_is_causal(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With close disabled the same tracker must report leaks, so the clean runs mean something."""
    tracker = FdTracker(monkeypatch, skip_close=True)
    try:
        read(home)
        assert len(tracker.leaked) == 4  # home, cache, images, file
    finally:
        tracker.cleanup()


def test_unknown_hook_and_bad_bounds_rejected(home: Path) -> None:
    with pytest.raises(ValueError, match="hook"):
        read(home, _hooks={"nope": lambda: None})
    for bad in (0, -1, fs.MAX_BYTES + 1):
        with pytest.raises(ValueError, match="bounds"):
            read(home, max_bytes=bad)


# ---- source hygiene ----------------------------------------------------------------------


def _module_tree() -> ast.Module:
    return ast.parse(Path(fs.__file__).read_text(encoding="utf-8"))


def test_source_has_no_path_authority_or_check_then_open_calls() -> None:
    banned_attrs = {
        "resolve",
        "realpath",
        "exists",
        "isfile",
        "isdir",
        "islink",
        "access",
        "open",
    }
    allowed_open_receivers = {"os"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Attribute) and node.attr in banned_attrs:
            if node.attr == "open":
                assert isinstance(node.value, ast.Name)
                assert node.value.id in allowed_open_receivers
            else:
                raise AssertionError(f"banned call surface: {node.attr}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "eval", "exec"}


def test_source_imports_no_hermes_hmp_network_or_codec() -> None:
    allowed = {
        "contextlib",
        "enum",
        "errno",
        "os",
        "stat",
        "sys",
        "unicodedata",
        "collections",
        "dataclasses",
        "typing",
        "__future__",
    }
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            assert {a.name.split(".")[0] for a in node.names} <= allowed
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed

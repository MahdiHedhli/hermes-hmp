"""In-memory causal tests; never opens a real presentation or profile path."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import unittest
from dataclasses import dataclass, field
from types import SimpleNamespace

from hmp_plugin import presentation_files as reader


@dataclass
class Node:
    name: str
    ino: int
    mode: int
    uid: int
    gid: int
    body: bytes = b""
    children: dict[str, Node] = field(default_factory=dict)
    dev: int = 7
    nlink: int = 1
    mtime_ns: int = 100
    ctime_ns: int = 100
    atime_ns: int = 100

    @property
    def size(self) -> int:
        return len(self.body) if stat.S_ISREG(self.mode) else 0

    def row(self) -> SimpleNamespace:
        return SimpleNamespace(
            st_dev=self.dev,
            st_ino=self.ino,
            st_mode=self.mode,
            st_uid=self.uid,
            st_gid=self.gid,
            st_nlink=self.nlink,
            st_size=self.size,
            st_mtime_ns=self.mtime_ns,
            st_ctime_ns=self.ctime_ns,
            st_atime_ns=self.atime_ns,
        )


class FakeOS:
    def __init__(self):
        self.root = Node("/", 1, stat.S_IFDIR | 0o755, 0, 0, nlink=2)
        self.srv = Node("srv", 2, stat.S_IFDIR | 0o755, 0, 0, nlink=2)
        self.home = Node("hermes", 3, stat.S_IFDIR | 0o700, 501, 20, nlink=2)
        self.assets = Node("assets", 4, stat.S_IFDIR | 0o700, 501, 20, nlink=2)
        self.meta = Node("profile.yaml", 5, stat.S_IFREG | 0o600, 501, 20, b"name: Ada\n")
        self.avatar = Node("avatar.png", 6, stat.S_IFREG | 0o600, 501, 20, b"PNG")
        self.root.children["srv"] = self.srv
        self.srv.children["hermes"] = self.home
        self.home.children["assets"] = self.assets
        self.home.children["profile.yaml"] = self.meta
        self.assets.children["avatar.png"] = self.avatar
        self.handles: dict[int, list[object]] = {}
        self.next_fd = 10
        self.call_count: dict[str, int] = {}
        self.hook = None
        self.fail_close_at = None
        self.close_calls: list[int] = []
        self.before_calls: list[tuple[str, object]] = []

    def _event(self, kind: str, arg: object):
        n = self.call_count.get(kind, 0) + 1
        self.call_count[kind] = n
        self.before_calls.append((kind, arg))
        if self.hook is not None:
            self.hook(self, kind, arg, n)

    def _node(self, path: str, dir_fd: int | None) -> Node:
        if dir_fd is None and path == "/":
            return self.root
        if dir_fd is None:
            raise AssertionError("absolute non-root lookup is prohibited")
        parent = self.handles[dir_fd][0]
        assert isinstance(parent, Node)
        try:
            return parent.children[path]
        except KeyError as exc:
            raise FileNotFoundError(errno.ENOENT, "missing") from exc

    def stat(self, path, *, dir_fd=None, follow_symlinks=False):
        self._event("stat", path)
        assert follow_symlinks is False
        return self._node(path, dir_fd).row()

    def open(self, path, flags, *, dir_fd=None):
        self._event("open", path)
        node = self._node(path, dir_fd)
        if stat.S_ISLNK(node.mode) and flags & os.O_NOFOLLOW:
            raise OSError(errno.ELOOP, "link")
        if flags & os.O_DIRECTORY and not stat.S_ISDIR(node.mode):
            raise OSError(errno.ENOTDIR, "not directory")
        if not flags & os.O_DIRECTORY and not stat.S_ISREG(node.mode):
            raise OSError(errno.ENXIO, "not regular")
        fd = self.next_fd
        self.next_fd += 1
        self.handles[fd] = [node, 0]
        return fd

    def fstat(self, fd):
        self._event("fstat", fd)
        return self.handles[fd][0].row()

    def read(self, fd, size):
        self._event("read", size)
        node, offset = self.handles[fd]
        assert isinstance(node, Node) and isinstance(offset, int)
        data = node.body[offset : offset + size]
        self.handles[fd][1] = offset + len(data)
        return data

    def lseek(self, fd, offset, whence):
        self._event("lseek", fd)
        if whence != os.SEEK_SET or offset != 0:
            raise AssertionError("unexpected seek")
        self.handles[fd][1] = 0
        return 0

    def close(self, fd):
        self._event("close", fd)
        self.close_calls.append(fd)
        self.handles.pop(fd)
        if self.fail_close_at == len(self.close_calls):
            raise OSError(errno.EIO, "may already be closed")


def bound_scope(now=1.0):
    rules = (
        reader.DirectoryRule("/", 0, 0, (0o755,)),
        reader.DirectoryRule("/srv", 0, 0, (0o755,)),
        reader.DirectoryRule("/srv/hermes", 501, 20, (0o700,)),
    )
    return reader.bind_owned_worker_read(
        root_path="/srv/hermes",
        home_path="/srv/hermes",
        profile=None,
        service_uid=501,
        service_gid=20,
        directory_rules=rules,
        deadline=now + 2.0,
        challenge="a" * 32,
        source_manifest_sha256="b" * 64,
        worker_go_challenge="a" * 32,
    )


class FixedReaderFakeTests(unittest.TestCase):
    def run_reader(self, fs, clock=lambda: 1.0):
        return reader.read_fixed_presentation_files(bound_scope(), fs=fs, clock=clock)

    def assert_refused(self, fs, label, clock=lambda: 1.0):
        with self.assertRaises(reader.PresentationReadError) as raised:
            self.run_reader(fs, clock)
        self.assertEqual(raised.exception.label, label)
        self.assertEqual(fs.handles, {})
        self.assertEqual(len(fs.close_calls), len(set(fs.close_calls)))

    def test_complete_fixed_files_and_budget(self):
        fs = FakeOS()
        result = self.run_reader(fs)
        self.assertEqual(result.metadata, b"name: Ada\n")
        self.assertEqual(result.metadata_sha256, hashlib.sha256(fs.meta.body).hexdigest())
        self.assertEqual(result.avatar_name, "avatar.png")
        self.assertEqual(result.avatar, b"PNG")
        self.assertEqual(result.avatar_sha256, hashlib.sha256(fs.avatar.body).hexdigest())
        self.assertTrue(result.raster_and_yaml_unvalidated)
        self.assertEqual(
            result.budget["readBytesCharged"],
            2 * (len(fs.meta.body) + len(fs.avatar.body) + 2),
        )
        self.assertLessEqual(result.budget["peakTargetFDs"], 34)
        self.assertEqual(fs.handles, {})

    def test_unbound_scope_refuses_before_any_lookup(self):
        fs = FakeOS()
        with self.assertRaises(reader.PresentationReadError):
            reader.read_fixed_presentation_files(object(), fs=fs, clock=lambda: 1.0)
        self.assertEqual(fs.before_calls, [])
        with self.assertRaises(reader.PresentationReadError):
            reader.bind_owned_worker_read(
                root_path="/srv/hermes",
                home_path="/srv/hermes",
                profile=None,
                service_uid=501,
                service_gid=20,
                directory_rules=(),
                deadline=3.0,
                challenge="a" * 32,
                source_manifest_sha256="b" * 64,
                worker_go_challenge="z" * 32,
            )

    def test_fixed_absence_and_no_scan(self):
        fs = FakeOS()
        fs.home.children.pop("profile.yaml")
        fs.home.children.pop("assets")
        result = self.run_reader(fs)
        self.assertIsNone(result.metadata)
        self.assertIsNone(result.avatar)
        self.assertTrue(all(kind != "scandir" for kind, _ in fs.before_calls))
        self.assertEqual(fs.handles, {})

    def test_duplicate_avatar_refused(self):
        fs = FakeOS()
        fs.assets.children["avatar.jpg"] = Node(
            "avatar.jpg", 7, stat.S_IFREG | 0o600, 501, 20, b"JPG"
        )
        self.assert_refused(fs, "MULTIPLE_AVATARS")

    def test_ancestor_link_and_named_swap(self):
        fs = FakeOS()
        fs.srv.mode = stat.S_IFLNK | 0o777
        self.assert_refused(fs, "DIRECTORY_TYPE")
        fs = FakeOS()

        def swap(fake, kind, arg, n):
            if kind == "open" and arg == "hermes":
                fake.srv.children["hermes"] = Node(
                    "hermes", 33, stat.S_IFDIR | 0o700, 501, 20, nlink=2
                )
                fake.hook = None

        fs.hook = swap
        self.assert_refused(fs, "DIRECTORY_BINDING")

    def test_fifo_link_hardlink_and_owner(self):
        for mutation, label in (
            (lambda f: setattr(f.meta, "mode", stat.S_IFIFO | 0o600), "LEAF_TYPE"),
            (lambda f: setattr(f.meta, "mode", stat.S_IFLNK | 0o600), "LEAF_TYPE"),
            (lambda f: setattr(f.meta, "nlink", 2), "LEAF_TYPE"),
            (lambda f: setattr(f.meta, "uid", 502), "LEAF_OWNER"),
            (lambda f: setattr(f.meta, "gid", 80), "LEAF_OWNER"),
            (lambda f: setattr(f.meta, "mode", stat.S_IFREG | 0o666), "LEAF_MODE"),
        ):
            with self.subTest(label=label, mutation=mutation):
                fs = FakeOS()
                mutation(fs)
                self.assert_refused(fs, label)

    def test_cap_plus_one_before_body_read(self):
        fs = FakeOS()
        fs.meta.body = b"x" * (reader.PROFILE_MAX + 1)
        self.assert_refused(fs, "LEAF_SIZE")
        self.assertFalse(any(kind == "read" for kind, _ in fs.before_calls))
        fs = FakeOS()
        fs.avatar.body = b"x" * (reader.AVATAR_MAX + 1)
        self.assert_refused(fs, "LEAF_SIZE")

    def test_atime_only_drift_is_not_identity(self):
        fs = FakeOS()

        def atime(fake, kind, arg, n):
            if kind == "read":
                fake.meta.atime_ns += 1
                fake.avatar.atime_ns += 1

        fs.hook = atime
        self.assertEqual(self.run_reader(fs).avatar, b"PNG")

    def test_one_ns_held_and_named_drift(self):
        for attribute in ("mtime_ns", "ctime_ns"):
            fs = FakeOS()

            def drift(fake, kind, arg, n, attribute=attribute):
                if kind == "read" and n == 1:
                    setattr(fake.meta, attribute, getattr(fake.meta, attribute) + 1)
                    fake.hook = None

            fs.hook = drift
            self.assert_refused(fs, "LEAF_CHANGED")

    def test_body_change_same_metadata_refuses(self):
        fs = FakeOS()

        def mutate(fake, kind, arg, n):
            if kind == "close" and len(fake.close_calls) == 1:
                fake.meta.body = b"name: Eve\n"  # Same size and timestamps.
                fake.hook = None

        fs.hook = mutate
        self.assert_refused(fs, "METADATA_BODY_CHANGED")

    def test_persistent_leaf_name_swap_same_bytes_refuses(self):
        fs = FakeOS()

        def swap(fake, kind, arg, n):
            if kind == "close" and len(fake.close_calls) == 1:
                fake.home.children["profile.yaml"] = Node(
                    "profile.yaml",
                    55,
                    stat.S_IFREG | 0o600,
                    501,
                    20,
                    fake.meta.body,
                )
                fake.hook = None

        fs.hook = swap
        self.assert_refused(fs, "PRESENCE_CHANGED")

    def test_truncated_body_and_partial_request_credit(self):
        fs = FakeOS()

        def truncate(fake, kind, arg, n):
            if kind == "read" and n == 1:
                fake.meta.body = b""
                fake.hook = None

        fs.hook = truncate
        self.assert_refused(fs, "BODY_TRUNCATED")

        fs = FakeOS()
        fs.meta.body = b"x" * 5000
        original_read = fs.read

        def short_read(fd, size):
            return original_read(fd, min(size, 1))

        fs.read = short_read
        self.assert_refused(fs, "READ_CREDIT")
        self.assertLessEqual(fs.call_count.get("read", 0), reader.READ_CREDIT)

    def test_directory_mode_drift_after_read(self):
        fs = FakeOS()

        def drift(fake, kind, arg, n):
            if kind == "read" and n == 1:
                fake.home.mode = stat.S_IFDIR | 0o755
                fake.hook = None

        fs.hook = drift
        self.assert_refused(fs, "DIRECTORY_CHANGED")

    def test_absence_becomes_present(self):
        fs = FakeOS()
        fs.home.children.pop("profile.yaml")

        def appear(fake, kind, arg, n):
            if kind == "read" and n == 1:
                fake.home.children["profile.yaml"] = fake.meta
                fake.hook = None

        fs.hook = appear
        self.assert_refused(fs, "PRESENCE_CHANGED")

    def test_final_absence_after_body_reread(self):
        for absent_name, parent_name in (
            ("profile.yaml", "home"),
            ("avatar.png", "assets"),
        ):
            with self.subTest(absent_name=absent_name):
                fs = FakeOS()
                parent = getattr(fs, parent_name)
                missing = parent.children.pop(absent_name)

                def appear(
                    fake, kind, arg, n, parent=parent, absent_name=absent_name, missing=missing
                ):
                    if kind == "close" and n == 2:
                        parent.children[absent_name] = missing
                        fake.hook = None

                fs.hook = appear
                self.assert_refused(fs, "PRESENCE_CHANGED")
                self.assertEqual(parent.mtime_ns, 100)
                self.assertEqual(parent.ctime_ns, 100)

    def test_final_extra_avatar_disappearance_and_replacement(self):
        for mutation, label in (
            (
                lambda fake: fake.assets.children.__setitem__(
                    "avatar.jpg",
                    Node("avatar.jpg", 70, stat.S_IFREG | 0o600, 501, 20, b"JPG"),
                ),
                "MULTIPLE_AVATARS",
            ),
            (lambda fake: fake.home.children.pop("profile.yaml"), "PRESENCE_CHANGED"),
            (
                lambda fake: fake.assets.children.__setitem__(
                    "avatar.png",
                    Node("avatar.png", 71, stat.S_IFREG | 0o600, 501, 20, b"PNG"),
                ),
                "PRESENCE_CHANGED",
            ),
        ):
            with self.subTest(label=label, mutation=mutation):
                fs = FakeOS()

                def change(fake, kind, arg, n, mutation=mutation):
                    if kind == "close" and n == 4:
                        mutation(fake)
                        fake.hook = None

                fs.hook = change
                self.assert_refused(fs, label)
                self.assertEqual(fs.home.mtime_ns, 100)
                self.assertEqual(fs.assets.mtime_ns, 100)

    def test_final_presence_does_not_outlive_directory_bindings(self):
        for mutate, kind, name, occurrence, label in (
            (
                lambda fake: setattr(fake.root, "mtime_ns", 101),
                "stat",
                "profile.yaml",
                7,
                "DIRECTORY_CHANGED",
            ),
            (
                lambda fake: setattr(fake.home, "ctime_ns", 101),
                "stat",
                "profile.yaml",
                7,
                "DIRECTORY_CHANGED",
            ),
            (
                lambda fake: setattr(fake.assets, "mtime_ns", 101),
                "stat",
                "avatar.webp",
                3,
                "ASSETS_CHANGED",
            ),
            (
                lambda fake: fake.srv.children.__setitem__(
                    "hermes",
                    Node("hermes", 78, stat.S_IFDIR | 0o700, 501, 20, nlink=2),
                ),
                "stat",
                "profile.yaml",
                7,
                "DIRECTORY_CHANGED",
            ),
        ):
            with self.subTest(mutate=mutate):
                fs = FakeOS()
                seen = [0]

                def drift(
                    fake,
                    observed_kind,
                    observed_name,
                    n,
                    mutate=mutate,
                    kind=kind,
                    name=name,
                    seen=seen,
                    occurrence=occurrence,
                ):
                    if observed_kind == kind and observed_name == name:
                        seen[0] += 1
                        if seen[0] == occurrence:
                            mutate(fake)
                            fake.hook = None

                fs.hook = drift
                self.assert_refused(fs, label)
                self.assertEqual(seen[0], occurrence)

    def test_read_error_and_close_error_original_retained(self):
        fs = FakeOS()

        def fail_read(fake, kind, arg, n):
            if kind == "read" and n == 1:
                raise OSError(errno.EIO, "synthetic read failure")

        fs.hook = fail_read
        self.assert_refused(fs, "BODY_READ")
        fs = FakeOS()
        fs.hook = fail_read
        fs.fail_close_at = 1
        with self.assertRaises(reader.UnknownCloseError) as raised:
            self.run_reader(fs)
        self.assertIsInstance(raised.exception.original, reader.PresentationReadError)
        self.assertEqual(raised.exception.original.label, "BODY_READ")
        self.assertEqual(fs.handles, {})
        self.assertEqual(len(fs.close_calls), len(set(fs.close_calls)))

    def test_newly_opened_fd_is_owned_before_fstat_failure(self):
        fs = FakeOS()

        def fail_first_fstat(fake, kind, arg, n):
            if kind == "fstat" and n == 1:
                raise OSError(errno.EIO, "synthetic held-stat failure")

        fs.hook = fail_first_fstat
        self.assert_refused(fs, "HELD_STAT")
        self.assertEqual(fs.call_count.get("open"), 1)
        self.assertEqual(fs.call_count.get("close"), 1)

    def test_deadline_during_body_preserves_owned_close(self):
        fs = FakeOS()
        moment = [1.0]

        def expire_on_body(fake, kind, arg, n):
            if kind == "read" and n == 1:
                moment[0] = 4.0

        fs.hook = expire_on_body
        self.assert_refused(fs, "DEADLINE", clock=lambda: moment[0])

    def test_deadline_before_io_and_close_remaining(self):
        fs = FakeOS()
        self.assert_refused(fs, "DEADLINE", clock=lambda: 4.0)
        fs = FakeOS()
        moment = [1.0]

        def expire_on_final_close(fake, kind, arg, n):
            if kind == "close" and n == 5:
                moment[0] = 4.0

        fs.hook = expire_on_final_close
        self.assert_refused(fs, "DEADLINE", clock=lambda: moment[0])
        fs = FakeOS()
        fs.fail_close_at = 1
        with self.assertRaises(reader.UnknownCloseError) as raised:
            self.run_reader(fs)
        self.assertIsInstance(raised.exception.original, OSError)
        self.assertEqual(fs.handles, {})
        self.assertEqual(len(fs.close_calls), len(set(fs.close_calls)))


if __name__ == "__main__":
    unittest.main()

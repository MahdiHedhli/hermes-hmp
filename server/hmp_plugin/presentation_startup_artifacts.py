"""Owned bounded startup artifact observations, not runtime admission.

Only the future fixed startup/configuration loader supplies external expectations.
No route imports this module. Matching selected files is not complete reachable
inventory/loader qualification or permission to load keys or publish images.
"""
from __future__ import annotations

import hashlib
import os
import stat
import threading
from dataclasses import dataclass
from typing import NamedTuple

from .presentation_gateway_activation import GatewayActivationOwner

_MAX_FILES = 1024
_MAX_FILE = 128 * 1024 * 1024
_MAX_TOTAL = 2 * 1024 * 1024 * 1024


class ArtifactObservationError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_STARTUP_ARTIFACTS_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise ArtifactObservationError


class ExpectedArtifact(NamedTuple):
    path: str
    size: int
    sha256: str

    def __repr__(self):
        return "<ExternalArtifactExpectation DATA not-approval redacted>"


class _HashedArtifact(NamedTuple):
    owner: object
    scope: object
    expected: ExpectedArtifact
    identity: tuple
    sha256: str

    def __repr__(self):
        return "<HashedArtifact original-descriptor DATA redacted>"


@dataclass(repr=False)
class _Descriptor:
    fd: int | None = None
    attempted: bool = False
    close_attempted: bool = False
    closed: bool = False
    unknown: bool = False


class _Scope(NamedTuple):
    activation: GatewayActivationOwner
    activation_scope: object
    expected: tuple
    context: tuple
    records: list
    parent: object = None

    def __repr__(self):
        return "<StartupArtifactScope redacted>"


class _PackageSource(NamedTuple):
    owner: object
    binding: tuple
    count_cell: tuple
    expected: tuple

    def __repr__(self):
        return "<OriginalPackageCountSource DATA redacted>"


def _package_source(package):
    from .presentation_gateway_package import GatewayPackageOwner
    _require(type(package) is GatewayPackageOwner)
    binding = GatewayPackageOwner._retained_binding(package)
    _require(GatewayPackageOwner._guard(package) is binding[0])
    after = GatewayPackageOwner._retained_binding(package)
    _require(all(a is b for a, b in zip(binding[:4], after[:4], strict=True))
             and all(a is b for a, b in zip(binding[4], after[4], strict=True)))
    meta = binding[0].expected
    _require(meta.recipe is not None and type(meta.recipe_binding) is tuple)
    previous = tuple(row[0] for row in meta.recipe_binding[4][3]) + meta.files
    return _PackageSource(package, binding, binding[3][2][7], previous)


def _source_current(source):
    _require(type(source) is _PackageSource)
    actual = _package_source(source.owner)
    _require(source.count_cell is actual.count_cell
             and all(a is b for a, b in zip(source.binding[:4], actual.binding[:4], strict=True))
             and all(a is b for a, b in zip(source.binding[4], actual.binding[4], strict=True))
             and type(source.expected) is tuple and len(source.expected) == len(actual.expected)
             and all(a is b for a, b in zip(source.expected, actual.expected, strict=True)))


def _identity(row, directory=False):
    _require(type(row) is os.stat_result)
    result = (row.st_dev, row.st_ino, row.st_mode, row.st_uid, row.st_gid)
    if not directory:
        result += (row.st_nlink, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
    _require(all(type(v) is int for v in result))
    return result


def _expected(rows):
    _require(type(rows) is tuple and 1 <= len(rows) <= _MAX_FILES)
    seen, total = set(), 0
    for row in rows:
        _require(type(row) is ExpectedArtifact and type(row.path) is str
                 and 1 < len(row.path.encode("utf-8")) <= 4096
                 and row.path.startswith("/")
                 and all(32 <= ord(c) != 127 for c in row.path))
        parts = row.path[1:].split("/")
        _require(1 <= len(parts) <= 64 and all(p not in ("", ".", "..") for p in parts)
                 and row.path not in seen and type(row.size) is int
                 and 0 <= row.size <= _MAX_FILE and type(row.sha256) is str
                 and len(row.sha256) == 64 and all(c in "0123456789abcdef" for c in row.sha256))
        seen.add(row.path)
        total += row.size
        _require(total <= _MAX_TOTAL)


def _configuration(owner):
    if type(owner) is StartupArtifactOwner:
        return False
    from .presentation_startup_selection import StartupSelectionOwner
    if type(owner) is StartupSelectionOwner:
        return True
    from .presentation_gateway_package import GatewayPackageOwner
    if type(owner) is GatewayPackageOwner:
        return False
    from .presentation_gateway_recipe import GatewayRecipeOwner
    _require(type(owner) is GatewayRecipeOwner)
    return True


def _owner_guard(owner):
    if type(owner) is StartupArtifactOwner:
        return StartupArtifactOwner._guard(owner)
    from .presentation_startup_selection import StartupSelectionOwner
    if type(owner) is StartupSelectionOwner:
        return StartupSelectionOwner._guard(owner)
    from .presentation_gateway_package import GatewayPackageOwner
    if type(owner) is GatewayPackageOwner:
        return GatewayPackageOwner._guard(owner)
    from .presentation_gateway_recipe import GatewayRecipeOwner
    _require(type(owner) is GatewayRecipeOwner)
    return GatewayRecipeOwner._guard(owner)


def _root(owner, activation):
    if type(owner) is StartupArtifactOwner:
        return activation._artifact_cell
    from .presentation_startup_selection import StartupSelectionOwner
    if type(owner) is StartupSelectionOwner:
        return activation._selection_cell
    from .presentation_gateway_package import GatewayPackageOwner
    if type(owner) is GatewayPackageOwner:
        return activation._package_cell
    from .presentation_gateway_recipe import GatewayRecipeOwner
    _require(type(owner) is GatewayRecipeOwner)
    return activation._recipe_cell


def _append_configuration(owner, data):
    if _configuration(owner):
        from .presentation_startup_selection import StartupSelectionOwner
        if type(owner) is StartupSelectionOwner:
            StartupSelectionOwner._append(owner, data)
        else:
            from .presentation_gateway_recipe import GatewayRecipeOwner
            _require(type(owner) is GatewayRecipeOwner)
            GatewayRecipeOwner._append(owner, data)


class StartupArtifactOwner:
    @classmethod
    def observe(cls, activation, expected):
        _require(cls is StartupArtifactOwner)
        return StartupArtifactOwner.complete(StartupArtifactOwner.retain(activation, expected))

    @classmethod
    def retain(cls, activation, expected):
        _require(cls is StartupArtifactOwner)
        return StartupArtifactOwner._retain(activation, expected, None)

    @classmethod
    def retain_from_package(cls, package, expected):
        _require(cls is StartupArtifactOwner)
        source = _package_source(package)
        return StartupArtifactOwner._retain(source.binding[0].activation, expected, source)

    @classmethod
    def _retain(cls, activation, expected, source):
        _require(cls is StartupArtifactOwner and type(activation) is GatewayActivationOwner
                 and activation._artifact_owner is None and activation._artifact_cell is None
                 and activation._artifact_attempt_cell is None
                 and activation._artifact_fact_cell is None)
        GatewayActivationOwner.current(activation)
        _require(activation._artifact_owner is None and activation._artifact_cell is None)
        owner = cls.__new__(cls)
        activation._artifact_owner = owner
        activation._artifact_cell = (activation, owner)
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._facts = owner._hashes = owner._attempt_cell = owner._fact_cell = None
        owner._scope = owner._origin = owner._cell = owner._root_cell = None
        owner._count_cell = owner._initial_count_cell = None
        owner._bytes_read = 0
        try:
            if source is not None:
                _require(type(source) is _PackageSource)
                owner._bytes_read = source.count_cell[2]
            s = _Scope(activation, activation._scope, expected,
                       (os.getpid(), os.geteuid(), threading.get_ident()), [], source)
            owner._scope = owner._origin = s
            owner._cell = (owner, s)
            owner._root_cell = (activation, owner, s)
            activation._artifact_cell = owner._root_cell
            owner._count_cell = owner._initial_count_cell = (owner, s, owner._bytes_read)
            _expected(expected)
            if source is not None:
                _source_current(source)
                _expected(source.expected + expected)
            StartupArtifactOwner._guard(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise ArtifactObservationError(owner) from None

    @classmethod
    def complete(cls, owner):
        _require(cls is StartupArtifactOwner and type(owner) is StartupArtifactOwner
                 and type(owner._origin) is _Scope)
        s, root = owner._origin, owner._root_cell
        activation = s.activation
        _require(owner._ready is False and owner._failed is False and owner._unknown is False
                 and owner._attempt_cell is None and activation._artifact_attempt_cell is None)
        _require(owner._scope is s and owner._origin is s and owner._root_cell is root
                 and activation._artifact_owner is owner and activation._artifact_cell is root)
        attempt = (owner, s, root)
        owner._attempt_cell = activation._artifact_attempt_cell = attempt
        fact = None
        try:
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(v) is int for v in context) and context == s.context)
            _require(StartupArtifactOwner._guard(owner) is s
                     and owner._count_cell is owner._initial_count_cell
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.unknown is False and row.close_attempted is True
                             for row in s.records))
            hashes = tuple(StartupArtifactOwner._file(owner, row) for row in s.expected)
            count = owner._count_cell
            _require(StartupArtifactOwner._guard(owner) is s
                     and owner._root_cell is root and owner._attempt_cell is attempt
                     and activation._artifact_attempt_cell is attempt
                     and type(count) is tuple and len(count) == 3
                     and count[0] is owner and count[1] is s and type(count[2]) is int
                     and owner._count_cell is count and owner._bytes_read is count[2]
                     and count[2] == owner._initial_count_cell[2]
                     + sum(row.size for row in s.expected)
                     and all(type(row) is _HashedArtifact and row.owner is owner
                             and row.scope is s and row.expected is expected
                             for row, expected in zip(hashes, s.expected, strict=True))
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.unknown is False and row.close_attempted is True
                             for row in s.records)
                     and owner._facts is None and owner._hashes is None
                     and owner._fact_cell is None and activation._artifact_fact_cell is None)
            fact = (owner, s, hashes, count)
            owner._facts = tuple(row.expected for row in hashes)
            owner._hashes = hashes
            owner._fact_cell = activation._artifact_fact_cell = fact
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = True
            if fact is not None and activation._artifact_fact_cell is fact:
                activation._artifact_fact_cell = None
            raise ArtifactObservationError(owner) from None

    def __repr__(self):
        return "<StartupArtifactOwner historical-files-not-admission redacted>"

    def _guard(self):
        _require(type(self) is StartupArtifactOwner and type(self._origin) is _Scope
                 and self._scope is self._origin and type(self._cell) is tuple
                 and len(self._cell) == 2 and self._cell[0] is self
                 and self._cell[1] is self._origin)
        s, cell, root_cell = self._origin, self._cell, self._root_cell
        _require(type(s.activation) is GatewayActivationOwner
                 and s.activation._artifact_owner is self
                 and type(root_cell) is tuple and len(root_cell) == 3
                 and s.activation._artifact_cell is root_cell
                 and root_cell[0] is s.activation and root_cell[1] is self
                 and root_cell[2] is s
                 and s.activation._scope is s.activation_scope
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context)
                 and self._failed is False and self._unknown is False
                 and type(s.records) is list and self._reading is False)
        attempt, fact = self._attempt_cell, self._fact_cell
        _require(s.activation._artifact_attempt_cell is attempt
                 and s.activation._artifact_fact_cell is fact)
        actual = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in actual) and actual == s.context)
        GatewayActivationOwner.current(s.activation)
        if s.parent is not None:
            _source_current(s.parent)
        _require(self._scope is s and self._origin is s and self._cell is cell
                 and s.activation._scope is s.activation_scope
                 and s.activation._artifact_owner is self
                 and self._root_cell is root_cell and s.activation._artifact_cell is root_cell
                 and self._failed is False
                 and self._unknown is False and self._attempt_cell is attempt
                 and self._fact_cell is fact and s.activation._artifact_attempt_cell is attempt
                 and s.activation._artifact_fact_cell is fact)
        return s

    def _open(self, name, parent, directory):
        s = _owner_guard(self)
        row = _Descriptor()
        s.records.append(row)  # original descriptor allocation before open
        root_cell, fd = self._root_cell, None
        row.attempted = True
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
        if directory:
            flags |= os.O_DIRECTORY
        try:
            fd = os.open(name, flags, dir_fd=parent)
            _require(type(fd) is int and fd >= 0)
            row.fd = fd
            _require(_owner_guard(self) is s)
            return row, fd
        except BaseException:
            row.unknown = self._unknown = True
            if type(fd) is int and row.fd is fd and row.close_attempted is False:
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root_cell)
                except BaseException:
                    row.unknown = self._unknown = True
            raise

    def _close(self, row, fd, s, root_cell):
        # Cleanup may run after a failed guard, but only on the original context.
        _require(type(s) is _Scope and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context))
        actual = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(
            all(type(v) is int for v in actual)
            and actual == s.context
            and type(row) is _Descriptor
            and row.fd is fd
            and type(fd) is int
            and row.close_attempted is False
            and type(s.records) is list
            and any(original is row for original in s.records)
            and type(root_cell) is tuple
            and len(root_cell) == (4 if _configuration(self) else 3)
            and root_cell[0] is s.activation
            and root_cell[1] is self
            and root_cell[2] is s
            and self._root_cell is root_cell
            and _root(self, s.activation) is root_cell
            and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope
        )
        row.close_attempted = True
        try:
            os.close(fd)
            row.closed = True
            _require(self._root_cell is root_cell and _root(self, s.activation) is root_cell
                     and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope)
        except BaseException:
            row.unknown = self._unknown = True
            raise

    def _read(self, fd, count, s):
        if type(self) is StartupArtifactOwner:
            _require(self._ready is False and self._attempt_cell is not None)
        _require(_owner_guard(self) is s and type(count) is int
                 and 0 < count <= 65536 and type(self._bytes_read) is int)
        before, cell = self._bytes_read, self._count_cell
        _require(type(cell) is tuple and len(cell) == 3 and cell[0] is self
                 and cell[1] is s and type(cell[2]) is int and cell[2] == before)
        self._reading = True
        data = None
        try:
            data = os.read(fd, count)
            _require(type(data) is bytes)
            same = (self._scope is s and self._origin is s and self._bytes_read is before
                    and self._count_cell is cell and self._reading is True)
            after = before + len(data)  # actual count before any post-read check
            after_cell = (self, s, after)
            self._bytes_read = after
            self._count_cell = after_cell
            self._reading = False
            _require(same and len(data) <= count and _owner_guard(self) is s
                     and self._bytes_read is after and self._count_cell is after_cell)
            return data
        except BaseException:
            self._unknown = True
            raise
        finally:
            data = None

    def _stat(self, name, parent, s):
        _require(_owner_guard(self) is s)
        value = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _require(type(value) is os.stat_result and _owner_guard(self) is s)
        return value

    def _fstat(self, fd, s):
        _require(_owner_guard(self) is s)
        value = os.fstat(fd)
        _require(type(value) is os.stat_result and _owner_guard(self) is s)
        return value

    def _file(self, expected):
        s = _owner_guard(self)
        root_cell = self._root_cell
        held, directories = [], []
        data = digest = None
        result = None
        failed = False
        try:
            parent = None
            for name in ("/", *expected.path[1:].split("/")[:-1]):
                row, fd = StartupArtifactOwner._open(self, name, parent, True)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(self, fd, s)
                signature = _identity(info, True)
                mode = stat.S_IMODE(info.st_mode)
                _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                directories.append((name, parent, fd, signature))
                parent = fd
            if _configuration(self):
                _require(info.st_uid == s.context[1] and stat.S_IMODE(info.st_mode) == 0o700)
            name = expected.path.rsplit("/", 1)[1]
            before = StartupArtifactOwner._stat(self, name, parent, s)
            original = _identity(before)
            _require(stat.S_ISREG(before.st_mode) and before.st_uid in (0, s.context[1])
                     and before.st_nlink == 1 and before.st_size == expected.size
                     and not before.st_mode & (0o022 | stat.S_ISUID | stat.S_ISGID))
            if _configuration(self):
                _require(before.st_uid == s.context[1] and stat.S_IMODE(before.st_mode) == 0o600)
            row, fd = StartupArtifactOwner._open(self, name, parent, False)
            held.append((row, fd))
            _require(_identity(StartupArtifactOwner._fstat(self, fd, s)) == original)
            digest = hashlib.sha256()
            remaining = expected.size
            while remaining:
                _require(_owner_guard(self) is s)
                data = StartupArtifactOwner._read(self, fd, min(remaining, 65536), s)
                _require(0 < len(data) <= remaining)
                remaining -= len(data)
                _require(_owner_guard(self) is s)
                _append_configuration(self, data)
                digest.update(data)
                data = None
                _require(_owner_guard(self) is s)
            data = StartupArtifactOwner._read(self, fd, 1, s)
            count_cell, counted = self._count_cell, self._bytes_read
            _require(data == b"" and _identity(StartupArtifactOwner._fstat(self, fd, s)) == original
                     and _identity(StartupArtifactOwner._stat(self, name, parent, s)) == original)
            _require(_owner_guard(self) is s)
            actual_hash = digest.hexdigest()
            _require(_owner_guard(self) is s
                     and type(actual_hash) is str and actual_hash == expected.sha256)
            for name, parent, directory, signature in directories:
                _require(
                    _identity(StartupArtifactOwner._fstat(self, directory, s), True) == signature
                    and _identity(StartupArtifactOwner._stat(self, name, parent, s), True)
                    == signature
                )
            _require(_owner_guard(self) is s)
            result = expected
            if not _configuration(self):
                result = _HashedArtifact(self, s, expected, original, actual_hash)
        except BaseException:
            failed = True
        finally:
            data = digest = None
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root_cell)
                except BaseException:
                    row.unknown = self._unknown = True
                    failed = True
        if failed:
            raise ArtifactObservationError(self) from None
        _require(_owner_guard(self) is s and self._count_cell is count_cell
                 and self._bytes_read is counted)
        return result

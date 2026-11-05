"""Held private endpoint snapshots, never connection/code/custody authority.

Exclusive synchronous FD ownership is required. Root and the same-UID host
administrator are trusted. The future connection owner must independently join
endpoint checks with kernel peer and broker boot qualification around connect.
Nothing here creates, binds, connects, repairs or unlinks an endpoint.
"""

from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass

from .presentation_jobs import FrameError

_SOCKET = "presentation.sock"
_UNAVAILABLE = "BI1_BROKER_ENDPOINT_UNAVAILABLE"
_MISSING = "BI1_BROKER_ENDPOINT_MISSING"
Identity = tuple[int, int, int, int, int]


def _identity(row: os.stat_result) -> Identity:
    return row.st_dev, row.st_ino, row.st_mode, row.st_uid, row.st_gid


@dataclass
class _Directory:
    name: str
    fd: int | None = None
    original_fd: int | None = None
    identity: Identity | None = None
    close_attempted: bool = False
    closed: bool = False
    unknown: bool = False


@dataclass(frozen=True)
class EndpointObservation:
    """One owner's snapshot; not reusable permission for a later connection."""

    directory: Identity
    socket: Identity


class _MissingEndpointError(Exception):
    pass


class EndpointAcquisitionError(FrameError):
    def __init__(self, owner: BrokerEndpointOwner, code: str):
        super().__init__(code)
        self.failed_owner = owner


class BrokerEndpointOwner:
    def __init__(self, directory: str, *, expected_uid: int):
        self._directory = self._directory_snapshot = directory
        self._uid = self._uid_snapshot = expected_uid
        self._records: list[_Directory] = []
        self._records_snapshot = self._records
        self._record_refs: tuple[_Directory, ...] = ()
        self._seals: tuple[tuple[_Directory, str, int, Identity], ...] = ()
        self._seals_snapshot = self._seals
        self._components: tuple[str, ...] = ()
        self._components_snapshot = self._components
        self._socket: Identity | None = None
        self._socket_snapshot: Identity | None = None
        self._observation: EndpointObservation | None = None
        self._observation_value: tuple[Identity, Identity] | None = None
        self._refused = False
        self._closing = False
        try:
            if (
                os.name != "posix"
                or type(directory) is not str
                or not directory.startswith("/")
                or directory == "/"
                or any(ord(c) < 32 or ord(c) == 127 for c in directory)
                or type(expected_uid) is not int
                or not 1 <= expected_uid <= (1 << 32) - 2
            ):
                raise FrameError(_UNAVAILABLE)
            parts = tuple(directory[1:].split("/"))
            if (
                any(p in ("", ".", "..") for p in parts)
                or len(parts) > 64
                or len((directory + "/" + _SOCKET).encode("utf-8")) > 102
            ):
                raise FrameError(_UNAVAILABLE)
            self._components = self._components_snapshot = parts
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            for name in ("/", *parts):
                # Retain each partial record before open/fstat or the next open.
                record = _Directory(name)
                self._records.append(record)
                self._record_refs = tuple(self._records)
                parent = self._records[-2].fd if len(self._records) > 1 else None
                record.fd = record.original_fd = os.open(name, flags, dir_fd=parent)
                if type(record.fd) is not int or record.fd < 0:
                    raise FrameError(_UNAVAILABLE)
                row = os.fstat(record.fd)
                record.identity = _identity(row)
                self._seals = self._seals_snapshot = (
                    *self._seals, (record, name, record.fd, record.identity)
                )
                self._directory_policy(row, final=len(self._records) == len(parts) + 1)
                if os.get_inheritable(record.fd) is not False:
                    raise FrameError(_UNAVAILABLE)
            self._socket = self._socket_snapshot = self._socket_row()
            self._current()
        except BaseException as error:
            self._refused = True
            code = _MISSING if isinstance(error, _MissingEndpointError) else _UNAVAILABLE
            raise EndpointAcquisitionError(self, code) from None

    def _directory_policy(self, row: os.stat_result, *, final: bool) -> None:
        mode = stat.S_IMODE(row.st_mode)
        if not stat.S_ISDIR(row.st_mode) or row.st_nlink < 1:
            raise FrameError(_UNAVAILABLE)
        if final:
            if row.st_uid != self._uid_snapshot or mode != 0o700:
                raise FrameError(_UNAVAILABLE)
        elif (
            row.st_uid not in (0, self._uid_snapshot)
            or mode & (stat.S_ISUID | stat.S_ISGID)
            or (mode & 0o022 and not (row.st_uid == 0 and mode & stat.S_ISVTX))
        ):
            raise FrameError(_UNAVAILABLE)

    def _bindings(self) -> None:
        if (
            type(self._directory) is not str
            or type(self._directory_snapshot) is not str
            or type(self._uid) is not int
            or type(self._uid_snapshot) is not int
            or type(self._components) is not tuple
            or type(self._components_snapshot) is not tuple
            or type(self._records) is not list
            or type(self._records_snapshot) is not list
            or type(self._record_refs) is not tuple
            or type(self._seals) is not tuple
            or type(self._seals_snapshot) is not tuple
            or self._directory is not self._directory_snapshot
            or self._uid is not self._uid_snapshot
            or self._components is not self._components_snapshot
            or self._records is not self._records_snapshot
            or len(self._records) != len(self._record_refs)
            or any(a is not b for a, b in zip(self._records, self._record_refs, strict=True))
            or self._seals is not self._seals_snapshot
            or self._socket is not self._socket_snapshot
        ):
            raise FrameError(_UNAVAILABLE)
        if any(type(r) is not _Directory for r in self._record_refs) or any(
            type(s) is not tuple
            or len(s) != 4
            or type(s[0]) is not _Directory
            or type(s[1]) is not str
            or type(s[2]) is not int
            or s[2] < 0
            or type(s[3]) is not tuple
            or len(s[3]) != 5
            or any(type(v) is not int or v < 0 for v in s[3])
            for s in self._seals_snapshot
        ):
            raise FrameError(_UNAVAILABLE)

    def _held(self, record: _Directory) -> Identity:
        self._bindings()
        if (
            type(record) is not _Directory
            or type(record.fd) is not int
            or type(record.original_fd) is not int
            or record.fd is not record.original_fd
            or record.closed is not False
            or record.unknown is not False
            or type(record.identity) is not tuple
            or len(record.identity) != 5
            or any(type(v) is not int or v < 0 for v in record.identity)
        ):
            raise FrameError(_UNAVAILABLE)
        seal = next((s for s in self._seals_snapshot if s[0] is record), None)
        if (
            seal is None
            or record.name is not seal[1]
            or record.fd is not seal[2]
            or record.original_fd is not seal[2]
            or record.identity is not seal[3]
        ):
            raise FrameError(_UNAVAILABLE)
        row = os.fstat(seal[2])
        if _identity(row) != record.identity or os.get_inheritable(record.fd) is not False:
            raise FrameError(_UNAVAILABLE)
        return record.identity

    def _lineage(self) -> None:
        self._bindings()
        for index, record in enumerate(self._record_refs):
            held = self._held(record)
            row = os.stat(
                record.name,
                dir_fd=None if index == 0 else self._record_refs[index - 1].fd,
                follow_symlinks=False,
            )
            if _identity(row) != held:
                raise FrameError(_UNAVAILABLE)
            self._directory_policy(row, final=index == len(self._record_refs) - 1)

    def _socket_row(self) -> Identity:
        try:
            row = os.stat(_SOCKET, dir_fd=self._record_refs[-1].fd, follow_symlinks=False)
        except FileNotFoundError:
            raise _MissingEndpointError from None
        if (
            not stat.S_ISSOCK(row.st_mode)
            or row.st_uid != self._uid_snapshot
            or stat.S_IMODE(row.st_mode) != 0o600
            or row.st_nlink != 1
        ):
            raise FrameError(_UNAVAILABLE)
        return _identity(row)

    def _current(self) -> tuple[Identity, Identity]:
        if self._refused is not False or self._closing is not False:
            raise FrameError(_UNAVAILABLE)
        try:
            self._lineage()
            current = self._socket_row()
            if current != self._socket_snapshot:
                raise FrameError(_UNAVAILABLE)
            self._lineage()
            if self._socket_row() != current:
                raise FrameError(_UNAVAILABLE)
            return self._record_refs[-1].identity, current
        except BaseException:
            self._refused = True
            raise FrameError(_UNAVAILABLE) from None

    def observe(self) -> EndpointObservation:
        directory, endpoint = self._current()
        observation = EndpointObservation(directory, endpoint)
        self._observation = observation
        self._observation_value = directory, endpoint
        return observation

    def validates(self, observation: EndpointObservation) -> bool:
        current = self._current()
        if (
            type(observation) is not EndpointObservation
            or observation is not self._observation
            or (observation.directory, observation.socket) != self._observation_value
            or current != self._observation_value
        ):
            self._refused = True
            raise FrameError(_UNAVAILABLE)
        return True

    def close(self) -> bool:
        """Attempt each known owned FD once. Ambiguous closure never retries."""
        self._refused = True
        self._closing = True
        try:
            self._bindings()
        except BaseException:
            return False
        for record in reversed(self._record_refs):
            if record.close_attempted is not False:
                continue
            record.close_attempted = True
            if record.fd is None:
                record.unknown = True
                continue
            try:
                self._bindings()
                self._held(record)
                descriptor = record.fd
                os.close(descriptor)
                # A no-op/reused descriptor cannot become a local close fact.
                try:
                    os.fstat(descriptor)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        raise
                else:
                    raise FrameError(_UNAVAILABLE)
                self._bindings()
                record.closed = True
            except BaseException:
                record.unknown = True
        return bool(self._record_refs) and all(
            r.closed is True and r.close_attempted is True and r.unknown is False
            for r in self._record_refs
        )

"""Explicit POSIX worker backend for the bounded fixed presentation reader.

Import performs no I/O. This backend conveys no authority and is never selected
implicitly; only an authorized disposable worker may supply it to the reader.
The reader owns flags, budgets, descriptor custody and close outcomes.
"""
from __future__ import annotations

import os


class PosixFileOps:
    def open(self, path: str, flags: int, *, dir_fd: int | None = None) -> int:
        return os.open(path, flags, dir_fd=dir_fd)

    def stat(self, path: str, *, dir_fd: int | None = None, follow_symlinks: bool = False):
        return os.stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    def fstat(self, fd: int):
        return os.fstat(fd)

    def read(self, fd: int, size: int) -> bytes:
        return os.read(fd, size)

    def lseek(self, fd: int, offset: int, whence: int) -> int:
        return os.lseek(fd, offset, whence)

    def close(self, fd: int) -> None:
        # Never retry: an error may mean the descriptor was already closed.
        os.close(fd)

"""CPython source-loader input-attempt semantics; never code/runtime admission."""
from __future__ import annotations

from typing import NamedTuple


class CacheSelectionError(Exception):
    def __init__(self):
        super().__init__('BI1_CACHE_SELECTION_REFUSED')


def _require(value):
    if value is not True:
        raise CacheSelectionError


class CacheInputAttempt(NamedTuple):
    input: str
    validation: str
    flags: int | None

    def __repr__(self):
        return '<SourceLoaderInputAttempt DATA not-admission>'


def source_loader_input(header, magic, mtime, size, source_hash, mode, cache_state):
    """Model a known input observation, not a later read or successful import."""
    _require(type(magic) is bytes and len(magic) == 4
             and type(source_hash) is bytes and len(source_hash) == 8
             and type(mode) is str and mode in ('default', 'always', 'never')
             and type(cache_state) is str
             and cache_state in ('absent', 'nonfile', 'unreadable', 'declared')
             and (header is None or (type(header) is bytes and len(header) <= 16)))
    _require((mtime is None and size is None)
             or (type(mtime) is int and -2 ** 64 < mtime < 2 ** 64
                 and type(size) is int and 0 <= size < 2 ** 64))
    if mtime is None:
        return CacheInputAttempt('source', 'source_stat_unavailable', None)
    if cache_state != 'declared':
        _require(header is None)
        return CacheInputAttempt('source', 'cache_' + cache_state, None)
    _require(type(header) is bytes)
    if len(header) < 16 or header[:4] != magic:
        return CacheInputAttempt('source', 'cache_header_invalid', None)
    flags = int.from_bytes(header[4:8], 'little')
    if flags & ~3:
        return CacheInputAttempt('source', 'cache_header_invalid', flags)
    if not flags & 1:  # includes flags2, as the actual SourceLoader does
        timestamp = int.from_bytes(header[8:12], 'little')
        stored_size = int.from_bytes(header[12:16], 'little')
        if timestamp != mtime & 0xffffffff or stored_size != size & 0xffffffff:
            return CacheInputAttempt('source', 'timestamp_mismatch', flags)
        return CacheInputAttempt('cache', 'timestamp', flags)
    checked = mode != 'never' and (bool(flags & 2) or mode == 'always')
    if checked and header[8:16] != source_hash:
        return CacheInputAttempt('source', 'hash_mismatch', flags)
    return CacheInputAttempt('cache', 'hash_checked' if checked else 'hash_unchecked', flags)

"""Closed diagnostic classification DATA, never a native receipt or permission.

Only a future fixed stat-boundary handler may attach this category to its actual
original operation/result/consumer claim. Calling this helper with a constructed
exception proves nothing about an operation, kernel state, authority or fallback.
No caller/route imports it, and it performs no IO.
"""
from __future__ import annotations

import errno
from enum import Enum

_FILE_NOT_FOUND = FileNotFoundError
_ERRNO_MEMBER = OSError.errno
_FILENAME_MEMBER = OSError.filename
_ENOENT = errno.ENOENT


class _StatReport(Enum):
    REFUSED = 0
    REPORTED_MISSING_FOR_ORIGINAL_ARGUMENT = 1


def _reported_stat_condition(error, original_name):
    """Inspect only exact native exception slots; retain none of their values."""
    if type(error) is not _FILE_NOT_FOUND or type(original_name) is not str:
        return _StatReport.REFUSED
    # Native member descriptors bypass instance dictionaries and Python getters.
    number = _ERRNO_MEMBER.__get__(error, _FILE_NOT_FOUND)
    filename = _FILENAME_MEMBER.__get__(error, _FILE_NOT_FOUND)
    if (type(number) is int and number == _ENOENT
            and type(filename) is str and filename == original_name):
        return _StatReport.REPORTED_MISSING_FOR_ORIGINAL_ARGUMENT
    return _StatReport.REFUSED

"""POSIX CPython cache-path planning DATA, never filesystem or import authority."""
from __future__ import annotations

from typing import NamedTuple

from .runtime_files import RuntimeFilesError, _path


class CacheCandidateError(Exception):
    def __init__(self):
        super().__init__("BI1_CACHE_CANDIDATE_REFUSED")


def _require(value):
    if value is not True:
        raise CacheCandidateError


def _location(value):
    _require(type(value) is str and 0 < len(value) <= 4096 and value.startswith("/")
             and all(32 <= ord(c) != 127 and not 0xD800 <= ord(c) <= 0xDFFF for c in value)
             and len(value.encode("utf-8")) <= 4096
             and (value == "/" or all(part not in ("", ".", "..")
                                      for part in value[1:].split("/"))))
    return value


class PlannedCachePath(NamedTuple):
    path: str
    cwd_dependent: bool

    def __repr__(self):
        return "<PlannedSourceCachePath DATA not-observation redacted>"


def planned_cache_path(source, tag, optimize, prefix, cwd):
    """Plan all supported POSIX source-cache forms without calling a loader or OS.

    Inputs are DATA, not approved observations. The future original startup owner
    must bind these values before IO and observe every possible artifact/absence.
    """
    _location(source)
    _require(source.endswith(".py") and type(tag) is str and 0 < len(tag) <= 128
             and all(32 <= ord(c) != 127 and c != "/"
                     and not 0xD800 <= ord(c) <= 0xDFFF for c in tag)
             and len(tag.encode("utf-8")) <= 512
             and type(optimize) is int and 0 <= optimize <= 2147483647
             and (prefix is None or type(prefix) is str)
             and (cwd is None or type(cwd) is str))
    if prefix is not None:
        _location(prefix)
    head, tail = source.rsplit("/", 1)
    dependent = not head
    if dependent:
        head = _location(cwd)
    stem = tail[:-3] or "py"  # CPython's empty-base '.py' uses the remainder 'py'.
    filename = stem + "." + tag
    if optimize:
        filename += ".opt-" + str(optimize)
    filename += ".pyc"
    if prefix is None:
        result = head.rstrip("/") + "/__pycache__/" + filename
    else:
        relative = head.lstrip("/")
        result = prefix.rstrip("/") + "/" + (relative + "/" if relative else "") + filename
    try:
        _path(source)
        _path(result)
    except RuntimeFilesError:
        raise CacheCandidateError from None
    return PlannedCachePath(result, dependent)

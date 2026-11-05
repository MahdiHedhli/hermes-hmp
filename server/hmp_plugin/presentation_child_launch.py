"""Fixed disposable-worker launch configuration; no process or authority here.

The supervisor must verify the worker source and own every child/pipe before use.
A launch configuration is neither a source attestation nor native permission.
"""

from __future__ import annotations

import os
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .presentation_jobs import FrameError


@dataclass(frozen=True)
class ChildLaunch:
    argv: tuple[str, ...]
    environment: Mapping[str, str]
    close_fds: bool = True
    pass_fds: tuple[int, ...] = ()
    start_new_session: bool = True


def worker_environment() -> dict[str, str]:
    # No os.environ copy, HOME change, provider/credential, PYTHONPATH or loader
    # injection variables. Exact executable is used; no shell/PATH lookup needed.
    return {"LANG": "C", "LC_ALL": "C"}


def parser_package_path(value: str) -> str:
    """Validate fixed startup configuration, not code integrity or phone authority."""
    if type(value) is not str:
        raise FrameError("BI1_PARSER_PATH_REFUSED")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        raise FrameError("BI1_PARSER_PATH_REFUSED") from None
    if not 1 <= len(encoded) <= 4096:
        raise FrameError("BI1_PARSER_PATH_REFUSED")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise FrameError("BI1_PARSER_PATH_REFUSED")
    path = Path(value)
    try:
        if (
            not path.is_absolute()
            or str(path) != value
            or path.name != "yaml"
            or str(path.resolve(strict=True)) != value
            or not stat.S_ISDIR(path.lstat().st_mode)
        ):
            raise FrameError("BI1_PARSER_PATH_REFUSED")
        entry = path / "__init__.py"
        if not stat.S_ISREG(entry.lstat().st_mode):
            raise FrameError("BI1_PARSER_PATH_REFUSED")
    except (OSError, RuntimeError, ValueError):
        raise FrameError("BI1_PARSER_PATH_REFUSED") from None
    return value


def child_launch(parser_package: str | None = None) -> ChildLaunch:
    if os.name != "posix" or not Path(sys.executable).is_absolute():
        raise FrameError("BI1_CHILD_UNAVAILABLE")
    script = Path(__file__).parent / "presentation_child.py"
    arguments = (
        () if parser_package is None else ("--parser-package", parser_package_path(parser_package))
    )
    return ChildLaunch(
        (sys.executable, "-I", "-B", "-S", str(script), *arguments),
        MappingProxyType(worker_environment()),
    )

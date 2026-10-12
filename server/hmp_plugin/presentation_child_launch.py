"""Fixed disposable-worker launch configuration; no process or authority here.

The supervisor must verify the worker source and own every child/pipe before use.
A launch configuration is neither a source attestation nor native permission.
"""

from __future__ import annotations

import os
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


def child_launch() -> ChildLaunch:
    if os.name != "posix" or not Path(sys.executable).is_absolute():
        raise FrameError("BI1_CHILD_UNAVAILABLE")
    script = Path(__file__).parent / "presentation_child.py"
    return ChildLaunch(
        (sys.executable, "-I", "-B", str(script)),
        MappingProxyType(worker_environment()),
    )

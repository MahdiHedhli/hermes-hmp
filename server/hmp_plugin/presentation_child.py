"""Fixed isolated presentation child; never import the gateway initializer.

The parent must attest code/runtime origins, enforce its original hard deadline,
and own/reap this process and every pipe. This bootstrap is not an OS sandbox.
"""

from __future__ import annotations

import importlib.machinery
import os
import sys
import time
import types
from pathlib import Path

_NAMESPACE = "_hmp_presentation_child"


def bootstrap() -> None:
    global __package__
    if any(name == _NAMESPACE or name.startswith(_NAMESPACE + ".") for name in sys.modules):
        raise RuntimeError("BI1_CHILD_NAMESPACE_REFUSED")
    root = str(Path(__file__).parent)
    package = types.ModuleType(_NAMESPACE)
    package.__package__ = _NAMESPACE
    package.__path__ = [root]
    package.__spec__ = importlib.machinery.ModuleSpec(_NAMESPACE, loader=None, is_package=True)
    package.__spec__.submodule_search_locations = [root]
    sys.modules[_NAMESPACE] = package
    __package__ = _NAMESPACE


def main() -> int:
    try:
        if os.name != "posix" or os.geteuid() <= 0:
            raise RuntimeError("BI1_CHILD_IDENTITY_REFUSED")
        bootstrap()
        # Fixed own-code relative closure. No plugin initializer, sys.path edit,
        # environment/config lookup or input-selected module is involved.
        from .presentation_posix import PosixFileOps
        from .presentation_worker import process_child_stream_v2

        process_child_stream_v2(
            sys.stdin.buffer,
            sys.stdout.buffer,
            fs=PosixFileOps(),
            clock=time.monotonic,
            # Before input reveals the ORIGINAL parent deadline, only the
            # parent's hard timeout bounds imports/blocked reads. No new work
            # deadline is issued here; processing adopts the exact input value.
            deadline=sys.float_info.max,
            effective_uid=os.geteuid(),
            effective_gid=os.getegid(),
        )
        return 0
    except BaseException:
        # No paths, payload values or exception tracebacks on the diagnostic pipe.
        try:
            sys.stderr.buffer.write(b"BI1_CHILD_REFUSED\n")
            sys.stderr.buffer.flush()
        except BaseException:
            return 1
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

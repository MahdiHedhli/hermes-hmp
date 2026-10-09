"""Fresh-interpreter import probe that proves WHICH `hmp_plugin` tree it loaded.

A "no local_media module is loaded" assertion is only meaningful for the package under test. An
editable finder in a reused environment can resolve `hmp_plugin` (or one of its submodules) from an
unrelated checkout, so the probe first requires every loaded `hmp_plugin` package/submodule file to
live inside the exact PACKAGE tree, and only then inspects the loaded local_media modules.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"


def foreign_hmp_modules(modules: Mapping[str, Any], package: str) -> list[str]:
    """Loaded `hmp_plugin` modules whose file or package path is not inside `package`.

    Self-contained (stdlib only, no module globals) so the probe can embed its exact source.
    """
    import os

    root = os.path.realpath(package)

    def inside(path: object) -> bool:
        if not isinstance(path, str):
            return False
        real = os.path.realpath(path)
        return real == root or real.startswith(root + os.sep)

    bad = []
    for name, mod in sorted(modules.items()):
        if name != "hmp_plugin" and not name.startswith("hmp_plugin."):
            continue
        file = getattr(mod, "__file__", None)
        paths = list(getattr(mod, "__path__", None) or [])
        ok = inside(file) if file is not None else bool(paths)
        if ok and paths:
            ok = all(inside(p) for p in paths)
        if not ok:
            bad.append(name)
    return bad


def run_no_local_media_probe(
    imports: Sequence[str], *, marker: str = "local_media", search_root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Import `imports` fresh, then require PACKAGE provenance and no loaded media module."""
    code = (
        "from __future__ import annotations\n"
        "import sys\n"
        f"{inspect.getsource(foreign_hmp_modules)}\n"
        + "".join(f"import {name}\n" for name in imports)
        + f"foreign = foreign_hmp_modules(sys.modules, {str(PACKAGE)!r})\n"
        "assert 'hmp_plugin' in sys.modules and not foreign, ('foreign hmp_plugin', foreign)\n"
        f"bad = sorted(m for m in sys.modules if {marker!r} in m)\n"
        "assert not bad, bad\n"
    )
    env = {**os.environ, "PYTHONPATH": str(search_root or PACKAGE.parent)}
    return subprocess.run(
        [sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, check=False
    )

"""Source-only worker causals; no gateway, socket or native runtime."""

import runpy
from pathlib import Path


def test_native_media_worker_source_causals():
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "native_media_worker_source_checks.py"),
        run_name="_source_checks",
    )

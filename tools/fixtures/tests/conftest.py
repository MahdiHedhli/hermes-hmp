"""Make tools/fixtures/manifest.py importable as `manifest` from the tests
directory without turning tools/fixtures into an installed package."""

import sys
from pathlib import Path

TOOLS_FIXTURES_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_FIXTURES_DIR))

"""Make tools/acceptance/{interceptor,make_test_ca}.py importable as top-level modules from the
tests directory without turning tools/acceptance into an installed package."""

import sys
from pathlib import Path

TOOLS_ACCEPTANCE_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_ACCEPTANCE_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_ACCEPTANCE_DIR))

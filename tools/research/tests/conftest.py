"""Make tools/research/local_media_persistence_fixture.py importable from the tests directory."""

import sys
from pathlib import Path

TOOLS_RESEARCH_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_RESEARCH_DIR))

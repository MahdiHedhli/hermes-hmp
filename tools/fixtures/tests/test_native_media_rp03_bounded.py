"""One collected wrapper runs 56 pinned source methods and 206 inert causals.

The child interpreter is a source test driver with an inert socket module,
not an admitted native worker, gateway or transport process.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_native_media_rp03_source_causals():
    driver = Path(__file__).resolve().parents[1] / "native_media_rp03_source_checks.py"
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-S", str(driver)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stderr == ""
    # These are deterministic output expectations for pinned source tests,
    # not a transport/c018 preallocation or streaming custody proof.
    assert len(result.stdout.encode("utf-8")) <= 512
    summary = json.loads(result.stdout)
    assert summary == {
        "legacyMethods": 42,
        "authorityMethods": 14,
        "authorityCausalRows": 206,
        "sourceOnly": True,
        "runtimeQualified": False,
        "parserTag": "CPython3.14.6 selected source AST",
        "hostParserEquivalent": False,
        "legacyReplayIsAuthorityEvidence": False,
    }
    assert result.stdout == json.dumps(summary, sort_keys=True) + "\n"

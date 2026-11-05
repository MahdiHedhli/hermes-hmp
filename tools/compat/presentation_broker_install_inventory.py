"""Write a candidate inventory for separate review; never approve or launch it.

Run with the selected interpreter's -I -B -S and the fixed minimal environment.
The printed digest is observed inventory, not an independently trusted expected
manifest digest. Fixture oracles are not production qualification.
"""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import sys
from pathlib import Path


def _main() -> int:
    if len(sys.argv) != 5:
        return 1
    plugin, parser, generation, output = sys.argv[1:]
    # Execute the fixed independently trusted inventory implementation, NOT
    # the inspected candidate's bootstrap. Candidate trees are data only here.
    bootstrap = (Path(__file__).resolve().parents[2] / "server" / "hmp_plugin"
                 / "presentation_broker_bootstrap.py").resolve(strict=True)
    for candidate in (Path(plugin).resolve(strict=True), Path(parser).resolve(strict=True)):
        if bootstrap.is_relative_to(candidate):
            raise ValueError("trusted inventory source must be outside candidate data trees")
    namespace = runpy.run_path(str(bootstrap), run_name="_inventory_only")
    raw = namespace["candidate_manifest"](plugin, parser, generation)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        remaining = memoryview(raw)
        while remaining:
            count = os.write(descriptor, remaining)
            if count <= 0:
                raise OSError("inventory write refused")
            remaining = remaining[count:]
    finally:
        os.close(descriptor)
    print(json.dumps({"candidate_only": True, "production_qualified": False,
                      "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
                     sort_keys=True))
    return 0


def main() -> int:
    try:
        return _main()
    except BaseException:
        sys.stderr.write("BI1_CANDIDATE_INVENTORY_REFUSED\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

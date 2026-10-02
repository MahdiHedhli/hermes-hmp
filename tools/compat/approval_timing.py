#!/usr/bin/env python3
"""Approval qualifier timing at the real pinned source (local evidence, not a guarantee).

Run in the build's interpreter as a FRESH process (the probe imports Hermes modules and the plugin
holds a module-level latch), with a synthetic HERMES_HOME and XDG_STATE_HOME inside --work. It
measures, with `time.perf_counter`, the listener factory (baseline capture, no probe), the first
callback (manifest + fingerprint + import probe: the cold cost) and N later callbacks (manifest +
fingerprint re-read with the cached probe: the steady cost). One JSON line is printed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from approval_harness_common import PluginCopy


def _ms(seconds: float) -> float:
    return round(seconds * 1000.0, 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--hermes-src", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--cached-calls", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.cached_calls <= 5000:
        parser.error("--cached-calls must be between 1 and 5000")

    copy = PluginCopy(args.work, args.receipt, args.hermes_src)
    copy.set_entry(True)
    compat = copy.compat

    started = time.perf_counter()
    qualified = compat.approval_listener_qualifier(copy.read_identity)
    factory = time.perf_counter() - started

    started = time.perf_counter()
    first = qualified()
    cold = time.perf_counter() - started

    cached: list[float] = []
    results = [first]
    for _ in range(args.cached_calls):
        started = time.perf_counter()
        results.append(qualified())
        cached.append(time.perf_counter() - started)
    ordered = sorted(cached)
    report = {
        "python": sys.version.split()[0],
        "all_open": all(result is True for result in results),
        "factory_ms": _ms(factory),
        "cold_first_call_ms": _ms(cold),
        "cached": {
            "n": len(cached),
            "median_ms": _ms(statistics.median(cached)),
            "p95_ms": _ms(ordered[max(0, int(len(ordered) * 0.95) - 1)]),
            "max_ms": _ms(ordered[-1]),
        },
    }
    print(json.dumps(report))
    return 0 if report["all_open"] else 1


if __name__ == "__main__":
    sys.exit(main())

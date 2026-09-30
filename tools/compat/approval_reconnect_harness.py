#!/usr/bin/env python3
"""Listener-reconnect harness: real `adapter.open_components` called repeatedly in ONE process.

The gateway daemon has no public listener-only restart, so a full gateway restart cannot prove
what a listener reconnect does. `HmpAdapter.connect` builds its context with exactly this call, so
driving it again in the same process, between manifest edits, exercises the real factory,
process latch and probe cache. Run in the build's interpreter with a synthetic HERMES_HOME and
XDG_STATE_HOME inside --work. Prints one JSON object; the caller asserts the expected shape.

Scenarios:
  closed_start_stays_closed  first connect sees the EMPTY manifest, later connects see an entry.
  admitted_start_close_and_restore  first connect admitted; entry removed, wrong-fingerprint
      entry, then the same startup entry restored.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

from approval_harness_common import PluginCopy

SCENARIOS = ("closed_start_stays_closed", "admitted_start_close_and_restore")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--hermes-src", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    args = parser.parse_args()

    copy = PluginCopy(args.work, args.receipt, args.hermes_src)
    from hmp_plugin import adapter

    steps: list[dict[str, object]] = []
    callbacks = []
    contexts = []

    def connect(name: str) -> None:
        ctx = adapter.open_components(SimpleNamespace(config=SimpleNamespace(extra={})))
        try:
            callbacks.append(ctx.approval_qualification_open)
            contexts.append(ctx)
            steps.append({"step": name, "supported": ctx.compat.supported is True,
                          "open": ctx.approval_qualification_open()})
        finally:
            ctx.store.close()

    def recheck(name: str) -> None:
        # The callback belongs to the FIRST live context; report that context's own support.
        steps.append({"step": name, "supported": contexts[0].compat.supported is True,
                      "open": callbacks[0]()})

    if args.scenario == "closed_start_stays_closed":
        copy.set_entry(False)
        connect("connect-empty-manifest")
        copy.set_entry(True)
        recheck("first-callback-after-entry-installed")
        connect("reconnect-with-entry")
        copy.set_entry(False)
        connect("reconnect-empty-again")
        copy.set_entry(True)
        connect("reconnect-entry-restored")
    else:
        copy.set_entry(True)
        connect("connect-with-entry")
        recheck("callback-again-cached-probe")
        copy.set_entry(False)
        recheck("first-callback-after-removal")
        connect("reconnect-empty-manifest")
        copy.set_entry(True, fingerprint="0" * 64)
        connect("reconnect-wrong-fingerprint")
        recheck("first-callback-wrong-fingerprint")
        copy.set_entry(True)
        connect("reconnect-same-entry-restored")
        recheck("first-callback-after-restore")
    print(json.dumps({"scenario": args.scenario, "pid": os.getpid(), "steps": steps}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

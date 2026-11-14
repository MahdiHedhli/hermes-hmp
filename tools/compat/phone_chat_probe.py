#!/usr/bin/env python3
"""Evidence-only probe of the `phone_chat` capability check against a REAL Hermes tree.

Run it with the Hermes build's own interpreter:

    <hermes-venv>/bin/python tools/compat/phone_chat_probe.py --hermes-src <tree>

It uses HMP's real `compat.probe_dependencies` over the real `PHONE_CHAT_DEPENDENCIES`, in an
isolated temporary `HERMES_HOME`. It calls no helper, opens no socket and starts no gateway.

1. Baseline: on the build as shipped, nothing in the table may be missing. (A build that already
   lacks a helper is reported as such; that is a fact about the sample, not an admission list.)
2. Mutants, applied IN MEMORY to the imported real objects and undone afterwards, never to the
   files on disk: the `MessageEvent` dataclass loses `allow_gateway_control`; the approval
   resolver's signature loses its named `request_id`; the signature becomes `**kwargs`-only. Each
   must be detected, with exactly its own HMP label.
3. The neutral session-stream hook fact for the same tree.

This is sampled evidence for one tree. It is not a runtime allowlist and it never gates a build.
Exit 0 only when the baseline is clean and every mutant is detected with its own label.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from bridge_files import _isolate_hermes_home, _refuse_real_home

SERVER_DIR = Path(__file__).resolve().parents[2] / "server"


def _missing(compat: Any, root: Path) -> list[str]:
    return sorted(compat.probe_dependencies(hermes_root=root, specs=compat.PHONE_CHAT_DEPENDENCIES))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--hermes-src", type=Path, required=True)
    args = parser.parse_args()
    _refuse_real_home(args.hermes_src)
    src = args.hermes_src.resolve()
    sys.path.insert(0, str(SERVER_DIR))
    sys.path.insert(0, str(src))
    with _isolate_hermes_home():
        from hmp_plugin import compat

        baseline = _missing(compat, src)
        event = importlib.import_module("gateway.platforms.event")
        approval = importlib.import_module("tools.approval")
        mutants: dict[str, list[str]] = {}

        # Mutant 1: the dataclass has no `allow_gateway_control` field.
        cls = event.MessageEvent
        saved_fields = cls.__dataclass_fields__
        cls.__dataclass_fields__ = {
            k: v for k, v in saved_fields.items() if k != "allow_gateway_control"
        }
        try:
            mutants["no_allow_gateway_control"] = _missing(compat, src)
        finally:
            cls.__dataclass_fields__ = saved_fields

        # Mutants 2 and 3: the resolver's signature without a named `request_id`, then
        # `**kwargs`-only. Only `__signature__` of the real function object changes, so its source
        # file and wrapper chain stay inside the Hermes tree and the probe has to notice the
        # missing parameter itself (a containment failure would not explain a detection).
        resolver = approval.resolve_gateway_approval
        had_signature = "__signature__" in vars(resolver)
        saved_signature = vars(resolver).get("__signature__")
        param = inspect.Parameter
        base = list(inspect.signature(resolver).parameters.values())
        variants = {
            "resolver_without_request_id": [p for p in base if p.name != "request_id"],
            "resolver_kwargs_only": [
                param("args", param.VAR_POSITIONAL),
                param("kwargs", param.VAR_KEYWORD),
            ],
        }
        for name, params in variants.items():
            resolver.__signature__ = inspect.Signature(params)
            try:
                mutants[name] = _missing(compat, src)
            finally:
                if had_signature:
                    resolver.__signature__ = saved_signature
                else:
                    del resolver.__signature__

        restored = _missing(compat, src)
        hook = compat.stream_hook_present(src)

    expected = {
        "no_allow_gateway_control": ["gateway.platforms.event.MessageEvent.allow_gateway_control"],
        "resolver_without_request_id": ["tools.approval.resolve_gateway_approval"],
        "resolver_kwargs_only": ["tools.approval.resolve_gateway_approval"],
    }
    detected = {name: mutants[name] == labels for name, labels in expected.items()}
    report = {
        "baseline_missing": baseline,
        "restored_missing": restored,
        "mutants": mutants,
        "detected": detected,
        "stream_hook": hook,
        "ok": baseline == [] and restored == baseline and all(detected.values()),
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

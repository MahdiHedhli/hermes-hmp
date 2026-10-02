"""Shared setup for the approval reconnect and timing harnesses (test-only, fixture tooling).

Both harnesses run in the BUILD's own interpreter as a fresh process, so the plugin's module-level
approval latch starts unset. They import a scratch COPY of `server/hmp_plugin` (never the tracked
package), with fixture-only manifests, against a synthetic HERMES_HOME and XDG root. Nothing here
is read by the plugin runtime and nothing writes to the tracked manifests.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

SERVER_DIR = Path(__file__).resolve().parents[2] / "server"


class HarnessError(RuntimeError):
    pass


def _refuse_real_home(path: Path, what: str) -> None:
    home = Path.home().resolve()
    resolved = path.resolve()
    if resolved == home or home in resolved.parents:
        raise HarnessError(f"refusing {what} inside the real user home: {resolved}")


class PluginCopy:
    """A scratch plugin copy with a bootstrapped read entry and a togglable approval entry."""

    def __init__(self, work: Path, receipt: Path, hermes_src: Path) -> None:
        work = work.resolve()
        _refuse_real_home(work, "harness work directory")
        for name in ("HERMES_HOME", "XDG_STATE_HOME"):
            value = os.environ.get(name, "")
            if not value or not Path(value).resolve().is_relative_to(work):
                raise HarnessError(f"{name} must be a synthetic path inside the work directory")
        self.root = hermes_src.resolve()
        pkg_root = work / "pkg"
        self.dest = pkg_root / "hmp_plugin"
        if self.dest.exists():
            raise HarnessError("harness plugin copy already exists")
        shutil.copytree(
            SERVER_DIR / "hmp_plugin", self.dest, ignore=shutil.ignore_patterns("__pycache__")
        )
        sys.path.insert(0, str(pkg_root))  # the copy wins over any other hmp_plugin on the path
        from hmp_plugin import compat

        self.compat: ModuleType = compat
        if Path(compat.__file__).resolve().parent != self.dest.resolve():
            raise HarnessError("hmp_plugin did not import from the scratch copy")
        self.approval_path = self.dest / compat.APPROVAL_COMPAT_FILE
        approval = json.loads(self.approval_path.read_text(encoding="utf-8"))
        if approval.get("builds") != []:
            raise HarnessError("the copied approval manifest must start empty")
        self.approval_files: list[str] = approval["bridge_files"]
        raw = json.loads(receipt.read_text(encoding="utf-8"))
        if raw.get("bridge_files") != self.approval_files or len(raw.get("builds", [])) != 1:
            raise HarnessError("receipt boundary differs from the copied approval manifest")
        self.entry: dict[str, Any] = dict(raw["builds"][0])
        actual = compat.compute_read_bridge_fingerprint(self.root, self.approval_files)
        if actual != self.entry.get("fingerprint"):
            raise HarnessError("receipt fingerprint is stale for this Hermes source")
        read_path = self.dest / compat.READ_COMPAT_FILE
        read = json.loads(read_path.read_text(encoding="utf-8"))
        self.read_files: list[str] = read["bridge_files"]
        identity = compat.GitFingerprintReader(self.read_files).read(self.root)
        if identity is None:
            raise HarnessError("cannot identify the Hermes source over the read files")
        self.read_identity = identity
        read["builds"] = [{
            "fingerprint": identity.fingerprint, "git_sha": identity.git_sha,
            "label": "harness", "qualified_by": "harness fixture-only bootstrap",
            "qualified_at": datetime.now(UTC).isoformat(),
        }]
        read_path.write_text(json.dumps(read, indent=2) + "\n", encoding="utf-8")

    def set_entry(self, present: bool, *, fingerprint: str | None = None) -> None:
        entry = dict(self.entry)
        if fingerprint is not None:
            entry["fingerprint"] = fingerprint
        data = {"format": 1, "bridge_files": self.approval_files,
                "builds": [entry] if present else []}
        self.approval_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

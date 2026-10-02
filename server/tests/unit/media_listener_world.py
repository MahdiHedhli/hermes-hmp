"""Synthetic worlds for the S6b local-media listener binding tests.

Each `Synth` is an isolated byte copy of the whole `hmp_plugin` package (optionally with source
edits, used only to build MUTANTS that a guard test must catch) loaded under a unique package name,
next to a synthetic "native" tree that holds only invented files. The copy's
`read_compat_builds.json` and `local_media_supported_builds.json` are rewritten so the copy's REAL
`compat.default_gate()` and REAL `local_media_gate.media_listener_qualifier` see a matching entry.
Nothing imports Hermes, no shipped manifest changes, and the private `sys` anchor is snapshotted
and restored only by the test module's autouse fixture (test-only; the product has no such path).
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import sys
import types
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import compat as real_compat

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
KEY = "_hermes_hmp_local_media_process_state"
FORMAT = "hmp-local-media-1"
SHA = "0123456789abcdef0123456789abcdef01234567"
NATIVE = {
    "hermes_constants.py": (
        b"import os\n\n\ndef get_default_hermes_root():\n    return os.environ['HMP_SYNTH_HOME']\n"
    ),
    "a.py": b"A = 1\n",
    "b/c.py": b"C = 2\n",
}
READ_FILES = ["a.py", "hermes_constants.py"]
MARKER = "hermes_constants"


class _BaseAdapter:
    def __init__(self, config: Any, platform: Any) -> None:
        self.config = config
        self.platform = platform

    def _mark_connected(self, *, listener_base: str | None = None) -> None:
        pass

    def _mark_disconnected(self) -> None:
        pass

    def _set_fatal_error(self, code: str, message: str, *, retryable: bool) -> None:
        pass


class _SendResult:
    def __init__(self, success: bool, message_id: str | None = None, error: str | None = None):
        self.success, self.message_id, self.error = success, message_id, error


class Config:
    def __init__(self, extra: dict[str, Any]) -> None:
        self.extra = extra


def install_gateway_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = types.ModuleType("gateway")
    config = types.ModuleType("gateway.config")
    platforms = types.ModuleType("gateway.platforms")
    base = types.ModuleType("gateway.platforms.base")
    config.Platform = lambda name: ("platform", name)  # type: ignore[attr-defined]
    base.BasePlatformAdapter = _BaseAdapter  # type: ignore[attr-defined]
    base.SendResult = _SendResult  # type: ignore[attr-defined]
    for name, mod in (
        ("gateway", gateway),
        ("gateway.config", config),
        ("gateway.platforms", platforms),
        ("gateway.platforms.base", base),
    ):
        monkeypatch.setitem(sys.modules, name, mod)


def evict(name: str) -> None:
    """What the Hermes loader's `_evict_modules` does: the package and every submodule."""
    for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
        del sys.modules[key]


def load_package(plugin: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, plugin / "__init__.py", submodule_search_locations=[str(plugin)]
    )
    assert spec is not None and spec.loader is not None
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return package


def fingerprint(root: Path, files: list[str]) -> str:
    fp = real_compat.compute_read_bridge_fingerprint(root, files)
    assert fp is not None
    return fp


def isolated_anchor() -> Iterator[None]:
    """A generator for the test module's autouse fixture. Test-only: no anchor at the start of
    each test; the original is put back afterwards."""
    missing = object()
    old = sys.__dict__.get(KEY, missing)
    sys.__dict__.pop(KEY, None)
    had_marker = MARKER in sys.modules
    try:
        yield
    finally:
        for name in [n for n in sys.modules if n.startswith("hmpsix_")]:
            del sys.modules[name]
        if not had_marker:  # the synthetic `hermes_constants` a world's identity code imported
            sys.modules.pop(MARKER, None)
        if old is missing:
            sys.__dict__.pop(KEY, None)
        else:
            sys.__dict__[KEY] = old


class Synth:
    """One synthetic package copy plus a synthetic native tree.

    `edits` maps a plugin file name to `(old, new)` source replacements (mutants only). `share`
    reuses
    another world's native tree and home (a second package directory over the same native root).
    """

    def __init__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        label: str = "w",
        *,
        edits: dict[str, list[tuple[str, str]]] | None = None,
        share: Synth | None = None,
        manifest_entry: bool = True,
        load: bool = True,
        supported_listing: bool = True,
    ) -> None:
        self.monkeypatch = monkeypatch
        base = (tmp_path / f"synthetic_{label}").resolve()
        base.mkdir()
        self.base = base
        self.plugin = base / "plugin"
        shutil.copytree(PACKAGE, self.plugin, ignore=shutil.ignore_patterns("__pycache__"))
        for name, pairs in (edits or {}).items():
            path = self.plugin / name
            text = path.read_text(encoding="utf-8")
            for old, new in pairs:
                assert text.count(old) >= 1, f"mutation anchor missing in {name}: {old[:50]!r}"
                text = text.replace(old, new, 1)
            path.write_text(text, encoding="utf-8")
        if share is None:
            self.root = base / "native"
            for rel, data in NATIVE.items():
                path = self.root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (self.root / ".git").mkdir()
            (self.root / ".git" / "HEAD").write_text(SHA + "\n", encoding="utf-8")
        else:
            self.root = share.root
        self.home = base / "home"
        self.home.mkdir()
        self.pkg = f"hmpsix_{uuid.uuid4().hex[:10]}"
        self.supported_listing = supported_listing
        self.manifest_entry = manifest_entry
        self.write_lists()
        self.package: types.ModuleType | None = None
        if load:
            self.load()

    # --- identity oracles (independent of the gate's own digest code) ---
    def native_files(self) -> list[str]:
        return sorted(NATIVE)

    def hmp_files(self) -> list[str]:
        return sorted(p.name for p in self.plugin.glob("*.py"))

    def write_lists(self) -> None:
        read_fp = fingerprint(self.root, READ_FILES)
        builds = (
            [
                {
                    "git_sha": SHA,
                    "fingerprint": read_fp,
                    "label": "synthetic",
                    "qualified_by": "synthetic test",
                    "qualified_at": "2026-10-01",
                }
            ]
            if self.supported_listing
            else []
        )
        (self.plugin / "read_compat_builds.json").write_text(
            json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": builds}),
            encoding="utf-8",
        )
        entry = {
            "label": "synthetic",
            "git_sha": SHA,
            "native_fingerprint": fingerprint(self.root, self.native_files()),
            "hmp_fingerprint": fingerprint(self.plugin, self.hmp_files()),
            "source_sha": None,
            "qualified_by": "synthetic test",
            "qualified_at": "2026-10-01",
        }
        doc = {
            "format": FORMAT,
            "native_files": self.native_files(),
            "hmp_files": self.hmp_files(),
            "builds": [entry] if self.manifest_entry else [],
        }
        (self.plugin / "local_media_supported_builds.json").write_text(
            json.dumps(doc), encoding="utf-8"
        )

    # --- loading ---
    def load(self) -> None:
        """Load (or reload, after an eviction) the copy exactly as Hermes's loader would, with the
        synthetic native root made findable through the REAL `compat.locate_hermes_root`."""
        present = sys.modules.get(MARKER)
        assert present is None or Path(present.__file__).parent == self.root, (
            "a foreign marker module is loaded in this process"
        )
        self.monkeypatch.syspath_prepend(str(self.root))
        importlib.invalidate_caches()
        evict(self.pkg)
        install_gateway_stubs(self.monkeypatch)
        self.package = load_package(self.plugin, self.pkg)
        compat = self.mod("compat")
        compat.probe_read_dependencies = lambda **_kw: ()  # no Hermes here; probe tested elsewhere

    def mod(self, name: str) -> Any:
        return importlib.import_module(f"{self.pkg}.{name}")

    def reload(self) -> None:
        """A later load of the same directory: evicts every copy module, loads afresh."""
        self.load()

    # --- identity / home (no real identity or key material outside the temp dir) ---
    def env(self) -> dict[str, str]:
        return {
            "HOME": str(self.home),
            "HERMES_HOME": "",
            "XDG_STATE_HOME": "",
            "HMP_SYNTH_HOME": str(self.home / "hermes"),
        }

    def apply_env(self) -> None:
        for key, value in self.env().items():
            self.monkeypatch.setenv(key, value)

    def adapter(self, extra: dict[str, Any] | None = None) -> Any:
        return self.mod("adapter").HmpAdapter(Config({"port": 1, **(extra or {})}))

    def open(self, adapter: Any | None = None) -> tuple[Any, Any]:
        """`(adapter, ctx)` from the copy's REAL `open_components`."""
        self.apply_env()
        adapter = adapter if adapter is not None else self.adapter()
        ctx = self.mod("adapter").open_components(adapter)
        return adapter, ctx


def call_count(box: list[Any]) -> Callable[..., None]:
    def record(*args: Any, **kwargs: Any) -> None:
        box.append((args, kwargs))

    return record

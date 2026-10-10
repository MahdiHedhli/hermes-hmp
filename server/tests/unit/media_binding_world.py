"""Synthetic worlds for the M3 local-media availability binding tests.

Each `World` is an isolated byte copy of the whole `hmp_plugin` package (optionally with source
edits, used only to build MUTANTS that a guard test must catch) loaded under a unique package name.
Its `compat.default_gate` is replaced by a stub that returns a chosen result, so the copy's REAL
`adapter.open_components` runs against a SUPPORTED result with `identity is None` (the converted
base) and whatever `local_media` eligibility the test wants. The copy's `identity` custody root is
pointed at a temporary home. Nothing imports Hermes, reads a build list, or touches a live home.
"""

from __future__ import annotations

import importlib
import importlib.util
import shutil
import sys
import types
import uuid
from pathlib import Path
from typing import Any

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
LEGACY_ANCHOR = "_hermes_hmp_local_media_process_state"
MEDIA_STEMS = (
    "local_media_sidecar",
    "local_media_candidate",
    "local_media_active_scan",
    "local_media_result",
    "local_media_file_safety",
    "local_media_active_batch",
    "local_media_batch_binding",
)


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


class World:
    """One isolated package copy. `features` names the eligibility members reported available (the
    default is read plus local media); `supported=False` makes the stub report an unsupported build;
    `eligibility=False` makes the result carry no eligibility at all (a test double)."""

    def __init__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        label: str = "w",
        *,
        edits: dict[str, list[tuple[str, str]]] | None = None,
        features: tuple[str, ...] = ("read", "local_media"),
        supported: bool = True,
        eligibility: bool = True,
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
                assert text.count(old) >= 1, f"mutation anchor missing in {name}: {old[:60]!r}"
                text = text.replace(old, new, 1)
            path.write_text(text, encoding="utf-8")
        self.home = base / "home"
        self.home.mkdir()
        self.pkg = f"hmpm3_{uuid.uuid4().hex[:10]}"
        self.features = features
        self.supported = supported
        self.eligibility = eligibility
        self.package: types.ModuleType | None = None
        self.load()

    # --- loading ---
    def load(self) -> None:
        """Load (or reload, after an eviction) the copy exactly as Hermes's loader would."""
        importlib.invalidate_caches()
        evict(self.pkg)
        install_gateway_stubs(self.monkeypatch)
        self.package = load_package(self.plugin, self.pkg)
        compat = self.mod("compat")
        result = self._result(compat)

        class _Gate:
            def evaluate(self_inner) -> Any:  # noqa: N805
                return result

        self.monkeypatch.setattr(compat, "default_gate", lambda **_kw: _Gate())
        self.monkeypatch.setattr(
            self.mod("identity"), "_default_hermes_root", lambda: self.home / "hermes"
        )

    def _result(self, compat: Any) -> Any:
        statuses = compat.CompatStatus
        status = statuses.SUPPORTED if self.supported else statuses.UNSUPPORTED
        why = None if self.supported else self.mod("contract").OtherWhy.HERMES_BUILD_UNSUPPORTED
        eligibility = None
        if self.eligibility:
            version = compat.hermes_version.HermesVersion(
                compat.hermes_version.Scheme.SEMVER,
                (0, 21, 5),
                compat.hermes_version.VersionSource.LITERAL,
            )
            features = {
                compat.Feature(name): compat.FeatureStatus(available=True)
                for name in self.features
            }
            for feature in compat.Feature:
                features.setdefault(
                    feature,
                    compat.FeatureStatus(available=False, reason=compat.Unavailable.REQUIRES_READ),
                )
            eligibility = compat.Eligibility(version=version, git_sha=None, features=features)
        return compat.CompatResult(status, why, None, None, eligibility)

    def mod(self, name: str) -> Any:
        return importlib.import_module(f"{self.pkg}.{name}")

    def reload(self) -> None:
        self.load()

    def media_modules_loaded(self) -> list[str]:
        return sorted(
            n.rsplit(".", 1)[-1]
            for n in sys.modules
            if n.startswith(self.pkg + ".") and "local_media_" in n
        )

    # --- identity / home (no real identity or key material outside the temp dir) ---
    def apply_env(self) -> None:
        for key, value in {
            "HOME": str(self.home),
            "HERMES_HOME": "",
            "XDG_STATE_HOME": "",
        }.items():
            self.monkeypatch.setenv(key, value)

    def adapter(self, extra: dict[str, Any] | None = None) -> Any:
        return self.mod("adapter").HmpAdapter(Config({"port": 1, **(extra or {})}))

    def open(self, adapter: Any | None = None) -> tuple[Any, Any]:
        """`(adapter, ctx)` from the copy's REAL `open_components`."""
        self.apply_env()
        adapter = adapter if adapter is not None else self.adapter()
        ctx = self.mod("adapter").open_components(adapter)
        return adapter, ctx

    def fill_caches(self) -> tuple[Any, Any]:
        """Fill the copy's per-load media caches (as an inert media twin would) without opening a
        listener, so a test can damage one cross-reference before the binding proves it."""
        chain = self.mod("bridge")._local_media_modules()
        reads_media = self.mod("reads")._local_media_modules()
        return chain, reads_media

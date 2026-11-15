"""Real Hermes profile writer through HMP in isolated A→B→A homes."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

_PROVIDER_CONFIG = (
    "custom_providers:\n"
    "  - name: acme\n"
    "    base_url: https://api.acme.test/v1\n"
    "    key_env: ACME_RELAY_KEY\n"
    "    models: [acme/mini]\n"
)


def test_profile_model_write_and_scope_a_b_a(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("hermes_cli.web_routers.profiles")
    from hermes_cli import models_validate
    from hermes_cli.config import invalidate_env_cache

    from hmp_plugin.bridge import HermesReadBridge

    home = tmp_path / "root"
    profiles = {name: home / "profiles" / name for name in ("a", "b")}
    for name, path in profiles.items():
        path.mkdir(parents=True)
        (path / "config.yaml").write_text(_PROVIDER_CONFIG, encoding="utf-8")
        (path / ".env").write_text(f"ACME_RELAY_KEY={name}-key\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("ACME_RELAY_KEY", "wrong-root-key")
    invalidate_env_cache()
    keys: list[str] = []

    def validate(_model, _provider, api_key=None, **_kwargs):
        keys.append(api_key)
        return {"accepted": True, "persist": True, "recognized": True, "message": ""}

    monkeypatch.setattr(models_validate, "validate_requested_model", validate)
    runner = SimpleNamespace(
        _routed_profile_home=lambda name: profiles[name],
        served_profile_names=lambda: ["default", "a", "b"],
    )
    bridge = HermesReadBridge(SimpleNamespace(gateway_runner=runner), SimpleNamespace())

    assert bridge.profile_default_model("a")["model"] != "acme/mini"
    assert bridge.profile_default_model("b")["model"] != "acme/mini"
    assert bridge.set_profile_default_model("a", "acme", "acme/mini") == {
        "provider": "custom:acme", "model": "acme/mini",
    }
    assert bridge.profile_default_model("b")["model"] != "acme/mini"
    assert bridge.set_profile_default_model("b", "acme", "acme/mini") == {
        "provider": "custom:acme", "model": "acme/mini",
    }
    assert bridge.profile_default_model("a") == {
        "provider": "custom:acme", "model": "acme/mini",
    }
    assert keys == ["a-key", "b-key"]

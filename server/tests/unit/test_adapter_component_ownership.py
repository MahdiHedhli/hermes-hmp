"""Component setup ownership, with all builders inert and no listener/Store I/O."""

from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace

import pytest

from .test_adapter import adapter_module as adapter_module


class StopSetup(BaseException):
    pass


class Harness:
    def __init__(
        self,
        *,
        supported=True,
        fail=None,
        error_type=RuntimeError,
        cleanup_type=None,
        extra=None,
        features=True,
    ):
        self.events = []
        self.fail = fail
        self.failure = error_type("synthetic setup failure")
        self.cleanup_failure = cleanup_type("synthetic cleanup failure") if cleanup_type else None
        self.closes = 0
        self.constructed = 0
        self.returned = None
        self.caught = None
        h = self

        class TracedMap(dict):
            def get(self, key, default=None):
                h.step("config.get:" + key)
                return super().get(key, default)

        class Adapter:
            def __init__(self):
                object.__setattr__(self, "config", SimpleNamespace(extra=TracedMap(extra or {})))

            def __getattribute__(self, name):
                if name in ("config", "_read_worker_budget", "_observe_served_profiles"):
                    h.step("adapter.get:" + name)
                return object.__getattribute__(self, name)

            def __setattr__(self, name, value):
                h.step("adapter.set:" + name)
                object.__setattr__(self, name, value)

        self.adapter = Adapter()

        class FakeStore:
            def __init__(self, path):
                h.step("Store")
                h.constructed += 1
                h.store = self

            def migrate(self):
                h.step("migrate")

            def close(self):
                h.closes += 1
                h.events.append("close")
                if h.cleanup_failure:
                    raise h.cleanup_failure

        class Context:
            def __init__(self, **kwargs):
                h.step("ServerContext")
                self.__dict__.update(kwargs)
                self.__dict__.update(
                    now=lambda: 123,
                    guarantees=object(),
                    reported_write_gate=lambda: None,
                    reported_send_gate=lambda: None,
                    is_phone_chat_available=lambda: self.phone_chat_available(),
                )

            def __setattr__(self, name, value):
                h.step("context.set:" + name)
                object.__setattr__(self, name, value)

        class Eligibility:
            def available(self, feature):
                h.step("available:" + feature)
                return features

        def make_result(is_supported):
            return SimpleNamespace(
                supported=is_supported,
                eligibility=Eligibility(),
                status=SimpleNamespace(value="SUPPORTED" if is_supported else "UNSUPPORTED"),
            )

        def bridge(*args):
            h.step("Bridge")
            return SimpleNamespace(
                bind_phone_chat_helpers=h.callback("bind_phone", True),
                approval_timeout_s=lambda profile: 300,
            )

        feature_names = (
            "SEND",
            "APPROVALS",
            "PHONE_CHAT",
            "SESSION_BROWSING",
            "LOCAL_MEDIA",
            "JOBS",
            "MODEL",
        )
        self.ns = {
            "Mapping": Mapping,
            "Store": FakeStore,
            "compat": SimpleNamespace(
                default_gate=h.callback(
                    "default_gate",
                    SimpleNamespace(evaluate=h.callback("evaluate", make_result(supported))),
                ),
                CompatResult=lambda *_: make_result(False),
                CompatStatus=SimpleNamespace(UNSUPPORTED=False),
                Feature=SimpleNamespace(**{name: name for name in feature_names}),
            ),
            "OtherWhy": SimpleNamespace(HERMES_BUILD_UNSUPPORTED="unsupported"),
            "identity": SimpleNamespace(
                resolve_custody=h.callback("resolve_custody", SimpleNamespace(anchor_dir="inert")),
                load_or_create=h.callback("identity", SimpleNamespace(iid="synthetic-iid")),
            ),
            "server": SimpleNamespace(
                store_path=h.callback("store_path", "inert"),
                ServerContext=Context,
                ReadWorkerBudget=h.callback("ReadWorkerBudget", object()),
            ),
            "_log_unavailable_features": h.callback("log_unavailable"),
            "_bridge_published": h.callback(
                "bridge_published", (object(), bridge, h.callback("Directory", object()))
            ),
            "prompts": SimpleNamespace(
                PromptStore=h.callback(
                    "PromptStore", SimpleNamespace(close_phone_chat=lambda _: None)
                ),
                AdapterHooks=h.callback("AdapterHooks", object()),
            ),
            "Reads": h.callback("Reads", object()),
            "Authorize": h.callback("Authorize", object()),
            "direct_send": SimpleNamespace(
                ProfileLocks=h.callback("ProfileLocks", object()),
                DirectSendDeps=h.callback("DirectSendDeps", object()),
            ),
            "_media_bind": h.callback("media_bind", object()),
            "reads": object(),
            "log_event": h.callback("log_event"),
            "_readiness_owner_device_ids_from_adapter": lambda _: frozenset(),
            "_readiness_settings_from_adapter": lambda _: {},
        }

    def step(self, name):
        self.events.append(name)
        if len(self.events) - 1 == self.fail:
            raise self.failure

    def callback(self, name, value=None):
        def callback(*args, **kwargs):
            self.step(name)
            return value

        return callback

    def run(self, adapter_module, monkeypatch):
        for name, value in self.ns.items():
            monkeypatch.setattr(adapter_module, name, value)
        try:
            self.returned = adapter_module.open_components(self.adapter)
        except BaseException as error:
            self.caught = error
        return self


@pytest.mark.parametrize("supported", [False, True])
@pytest.mark.parametrize("error_type", [RuntimeError, StopSetup])
def test_component_setup_failures_close_known_store_once(
    adapter_module, monkeypatch, supported, error_type
):
    baseline = Harness(supported=supported).run(adapter_module, monkeypatch)
    assert baseline.caught is None and baseline.closes == 0
    for index, event in enumerate(list(baseline.events)):
        h = Harness(supported=supported, fail=index, error_type=error_type).run(
            adapter_module, monkeypatch
        )
        if event in ("default_gate", "evaluate") and error_type is RuntimeError:
            assert h.caught is None and h.returned is not None and h.closes == 0
            assert h.returned.compat.supported is False
            continue
        assert h.returned is None
        assert h.caught is h.failure, event
        assert h.closes == h.constructed, event


@pytest.mark.parametrize("supported", [False, True])
@pytest.mark.parametrize("error_type", [RuntimeError, StopSetup])
@pytest.mark.parametrize("cleanup_type", [RuntimeError, StopSetup])
def test_component_setup_cleanup_failure_retains_causes_and_custody(
    adapter_module, monkeypatch, supported, error_type, cleanup_type
):
    baseline = Harness(supported=supported).run(adapter_module, monkeypatch)
    assert baseline.caught is None
    for index, event in enumerate(list(baseline.events)):
        # No caller-owned store exists until the constructor returns.
        if index <= baseline.events.index("Store"):
            continue
        h = Harness(
            supported=supported, fail=index, error_type=error_type, cleanup_type=cleanup_type
        ).run(adapter_module, monkeypatch)
        error = h.caught
        assert isinstance(error, adapter_module._ComponentSetupCleanupError), event
        assert error.setup_failure is h.failure and error.__cause__ is h.failure
        assert error.cleanup_failure is h.cleanup_failure
        assert error.store is h.store and error.store_close_unknown is True
        assert h.closes == 1 and h.returned is None
        assert str(error) == "HMP component setup failed with unresolved store cleanup"


@pytest.mark.parametrize("supported", [False, True])
def test_component_setup_success_transfers_store_ownership(adapter_module, monkeypatch, supported):
    h = Harness(supported=supported).run(adapter_module, monkeypatch)
    assert h.caught is None and h.closes == 0
    assert h.returned.store is h.store
    h.returned.store.close()
    assert h.closes == 1

"""Private binding only: inert helper authority/registry, no components or listener I/O."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace

import pytest

from .test_adapter import adapter_module as adapter_module

HELPER_PATH = (
    Path(__file__).resolve().parents[3] / "tools/fixtures/native_media_listener_factory.py"
)


@pytest.fixture
def fixture_helper(monkeypatch):
    spec = importlib.util.spec_from_file_location("native_media_listener_factory", HELPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@dataclass
class Entry:
    adapter_factory: object
    metadata: object


class Registry:
    def __init__(self, entry):
        self.state = (entry, None)
        self.scope = "inert-scope"

    def current_scope_key(self):
        return self.scope

    def snapshot_registration(self, name, *, scope):
        assert name == "hmp" and scope == self.scope
        return self.state

    def get(self, name):
        assert name == "hmp"
        return self.state[0]

    def restore_registration(self, name, current, previous, *, scope):
        assert name == "hmp" and scope == self.scope
        if any(left is not right for left, right in zip(self.state, current, strict=True)):
            return False
        self.state = previous
        return True


class InertAuthority:
    """Single-state test checkpoint only; never a root/runtime qualification."""

    def __init__(self, binding):
        self.binding = binding
        self.identities = tuple(
            getattr(binding, name)
            for name in ("source_generation", "worker_generation", "listener_owner")
        )

    def checkpoint(self, _stage, binding):
        if binding is not self.binding or any(
            getattr(binding, name) is not saved
            for name, saved in zip(
                ("source_generation", "worker_generation", "listener_owner"),
                self.identities,
                strict=True,
            )
        ):
            raise RuntimeError("INERT_CONTEXT_CHANGED")
        return 1.0


class Scenario:
    def __init__(self, adapter_module, helper):
        self.module = adapter_module
        self.helper = helper
        self.config = SimpleNamespace(extra={})
        self.runner = SimpleNamespace(session_store=object())
        self.calls = 0

        def factory(config):
            self.calls += 1
            assert config is self.config
            self.adapter = adapter_module.HmpAdapter(config)
            return self.adapter

        entry = Entry(factory, object())
        self.registry = Registry(entry)
        self.binding = helper.StartupBinding(
            registry=self.registry,
            scope=self.registry.scope,
            role="A",
            ordinal=1,
            config=self.config,
            runner=self.runner,
            original_entry=entry,
            original_factory=factory,
            adapter_type=adapter_module.HmpAdapter,
            source_module=helper,
            source_origin=helper.__file__,
            source_sha256="0" * 64,
            source_generation=object(),
            worker_generation=object(),
            listener_owner=object(),
            deadline=100.0,
        )
        self.owner = helper.FixtureScopeOwner(self.binding, authority=InertAuthority(self.binding))
        self.slot = self.owner.issue_slot()
        self.delegate = helper.ScopedFactoryDelegate(self.owner)
        self.delegate.install(self.slot)

    def prepare_direct(self):
        """Model the delegate's pre-bind state for isolated adapter-negative causals."""
        self.adapter = self.module.HmpAdapter(self.config)
        self.owner.adapter_debt = self.adapter
        self.slot.claimed = True
        self.owner.state = "FACTORY_CLAIMED"
        self.owner.binding_attempted = True

    def direct_bind(self, slot=None):
        with self.owner.flight():
            self.owner._callback(
                self.adapter._bind_fixture_listener,
                self.slot if slot is None else slot,
                binding_hook=True,
            )


def run_connect(adapter):
    """The binding-only refusal occurs before any await; never create an event loop."""
    coroutine = adapter.connect()
    try:
        return coroutine.send(None)
    finally:
        coroutine.close()


def test_real_delegate_retains_exact_binding_before_native_wiring(adapter_module, fixture_helper):
    scenario = Scenario(adapter_module, fixture_helper)
    adapter = scenario.delegate.factory(scenario.config)
    assert scenario.calls == 1 and scenario.owner.bound_adapter is adapter
    assert scenario.owner.state == "ADAPTER_BOUND"
    slot, owner, binding, context = adapter._fixture_listener_binding
    assert slot is scenario.slot and owner is scenario.owner and binding is scenario.binding
    assert context == tuple(vars(binding)[name] for name in adapter_module._FIXTURE_CONTEXT_FIELDS)
    assert getattr(adapter, "gateway_runner", None) is None


@pytest.mark.parametrize("field", ["source_generation", "worker_generation", "listener_owner"])
def test_delegate_checkpoint_refuses_stale_opaque_context_before_factory(
    adapter_module, fixture_helper, field
):
    scenario = Scenario(adapter_module, fixture_helper)
    object.__setattr__(scenario.binding, field, object())
    with pytest.raises(fixture_helper.ScopeRefusedError, match="FACTORY_UNCERTAIN"):
        scenario.delegate.factory(scenario.config)
    assert scenario.calls == 0 and scenario.owner.bound_adapter is None
    assert str(scenario.owner.first_failure) == "INERT_CONTEXT_CHANGED"


@pytest.mark.parametrize(
    "damage",
    [
        "missing_module",
        "foreign_module",
        "foreign_spec",
        "foreign_class",
        "wrong_slot",
        "wrong_owner",
        "wrong_binding",
        "wrong_config",
        "wrong_adapter_type",
        "wrong_runner",
        "slot_unclaimed",
        "slot_changed",
        "owner_stale",
        "first_failure",
        "debt_changed",
        "source_module",
        "source_origin",
        "missing_generation",
        "constructor_namespace",
        "constructor_filename",
        "hook_namespace",
        "hook_filename",
        "hook_shadow",
    ],
)
def test_foreign_or_stale_private_bind_refuses(adapter_module, fixture_helper, monkeypatch, damage):
    scenario = Scenario(adapter_module, fixture_helper)
    scenario.prepare_direct()
    owner, slot, binding = scenario.owner, scenario.slot, scenario.binding
    supplied_slot = slot
    if damage == "missing_module":
        monkeypatch.delitem(sys.modules, "native_media_listener_factory")
    elif damage == "foreign_module":
        monkeypatch.setitem(sys.modules, "native_media_listener_factory", ModuleType("foreign"))
    elif damage == "foreign_spec":
        monkeypatch.setattr(fixture_helper, "__spec__", object())
    elif damage == "foreign_class":
        monkeypatch.setattr(fixture_helper, "_StartupSlot", object)
    elif damage == "wrong_slot":
        supplied_slot = object()
    elif damage == "wrong_owner":
        slot.owner = object()
    elif damage == "wrong_binding":
        slot.binding = object()
    elif damage == "wrong_config":
        scenario.adapter.config = SimpleNamespace(extra={})
    elif damage == "wrong_adapter_type":
        object.__setattr__(binding, "adapter_type", object)
    elif damage == "wrong_runner":
        scenario.adapter.gateway_runner = object()
    elif damage == "slot_unclaimed":
        slot.claimed = False
    elif damage == "slot_changed":
        owner.slot = object()
    elif damage == "owner_stale":
        owner.state = "POISONED"
    elif damage == "first_failure":
        owner.first_failure = RuntimeError("synthetic")
    elif damage == "debt_changed":
        owner.adapter_debt = object()
    elif damage == "source_module":
        object.__setattr__(binding, "source_module", object())
    elif damage == "source_origin":
        object.__setattr__(binding, "source_origin", "foreign")
    elif damage == "missing_generation":
        object.__setattr__(binding, "worker_generation", None)
    elif damage.startswith("constructor_"):
        old = fixture_helper.StartupBinding.__init__
        replacement = FunctionType(
            old.__code__.replace(co_filename="foreign")
            if damage.endswith("filename")
            else old.__code__,
            vars(fixture_helper) if damage.endswith("filename") else {},
        )
        monkeypatch.setattr(fixture_helper.StartupBinding, "__init__", replacement)
    elif damage.startswith("hook_") and damage != "hook_shadow":
        old = fixture_helper.FixtureScopeOwner.accept_adapter_binding
        replacement = FunctionType(
            old.__code__.replace(co_filename="foreign")
            if damage.endswith("filename")
            else old.__code__,
            vars(fixture_helper) if damage.endswith("filename") else {},
        )
        monkeypatch.setattr(fixture_helper.FixtureScopeOwner, "accept_adapter_binding", replacement)
    elif damage == "hook_shadow":
        owner.accept_adapter_binding = lambda *_args: None
    with pytest.raises((RuntimeError, fixture_helper.ScopeRefusedError)):
        scenario.direct_bind(supplied_slot)
    assert scenario.adapter._fixture_listener_binding is None
    assert owner.bound_adapter is None
    if scenario.adapter._fixture_binding_attempted:
        calls = []

        def forbidden(*_args, **_kwargs):
            calls.append("forbidden")
            raise AssertionError("Failed binding must not enter production setup")

        monkeypatch.setattr(adapter_module.server, "listener_settings", forbidden)
        monkeypatch.setattr(adapter_module, "open_components", forbidden)
        with pytest.raises(RuntimeError, match="FIXTURE_BINDING_UNAVAILABLE"):
            run_connect(scenario.adapter)
        assert calls == []


def test_direct_outside_guard_and_repeated_binding_refuse(adapter_module, fixture_helper):
    scenario = Scenario(adapter_module, fixture_helper)
    scenario.prepare_direct()
    with pytest.raises(RuntimeError, match="FIXTURE_BINDING_PHASE_CHANGED"):
        scenario.adapter._bind_fixture_listener(scenario.slot)
    assert scenario.adapter._fixture_binding_failed
    with pytest.raises(RuntimeError, match="FIXTURE_BINDING_CONSUMED"):
        scenario.adapter._bind_fixture_listener(scenario.slot)


def test_repeat_after_success_poisoned_without_second_hook(adapter_module, fixture_helper):
    scenario = Scenario(adapter_module, fixture_helper)
    adapter = scenario.delegate.factory(scenario.config)
    retained = adapter._fixture_listener_binding
    with pytest.raises(RuntimeError, match="FIXTURE_BINDING_CONSUMED"):
        adapter._bind_fixture_listener(scenario.slot)
    assert adapter._fixture_listener_binding is retained and adapter._fixture_binding_failed


def test_caught_reentry_cannot_publish_a_binding(adapter_module, fixture_helper, monkeypatch):
    scenario = Scenario(adapter_module, fixture_helper)
    scenario.prepare_direct()

    def reentrant(owner, slot, adapter):
        try:
            adapter._bind_fixture_listener(slot)
        except RuntimeError as error:
            globals()["_test_reentry_errors"].append(error)
        globals()["_test_original_accept"](owner, slot, adapter)

    # Source mutation for a causal test, not a qualified helper. A genuine source authority
    # would refuse mutated bytes; constructor/filename shape is never that authority.
    original = fixture_helper.FixtureScopeOwner.accept_adapter_binding
    monkeypatch.setattr(fixture_helper, "_test_original_accept", original, raising=False)
    monkeypatch.setattr(fixture_helper, "_test_reentry_errors", [], raising=False)
    replacement = FunctionType(
        reentrant.__code__.replace(co_filename=fixture_helper.__file__), vars(fixture_helper)
    )
    monkeypatch.setattr(fixture_helper.FixtureScopeOwner, "accept_adapter_binding", replacement)
    with pytest.raises((RuntimeError, fixture_helper.ScopeRefusedError)):
        scenario.direct_bind()
    assert scenario.adapter._fixture_listener_binding is None
    assert scenario.adapter._fixture_binding_failed
    assert len(fixture_helper._test_reentry_errors) == 1
    assert str(fixture_helper._test_reentry_errors[0]) == "FIXTURE_BINDING_CONSUMED"


@pytest.mark.parametrize(
    "wiring", ["none", "wrong_runner", "no_session", "wrong_session", "matched"]
)
def test_bound_connect_refuses_before_components_or_listener(
    adapter_module, fixture_helper, monkeypatch, wiring
):
    scenario = Scenario(adapter_module, fixture_helper)
    adapter = scenario.delegate.factory(scenario.config)
    calls = []

    def forbidden(*_args, **_kwargs):
        calls.append("forbidden")
        raise AssertionError("No component, thread, settings or listener entry is allowed")

    monkeypatch.setattr(adapter_module.server, "listener_settings", forbidden)
    monkeypatch.setattr(adapter_module.server, "HmpServer", forbidden)
    monkeypatch.setattr(adapter_module, "open_components", forbidden)
    monkeypatch.setattr(adapter_module, "asyncio", SimpleNamespace(to_thread=forbidden))
    if wiring != "none":
        adapter.gateway_runner = object() if wiring == "wrong_runner" else scenario.runner
    if wiring in ("wrong_session", "matched"):
        adapter._session_store = (
            object() if wiring == "wrong_session" else scenario.runner.session_store
        )
    with pytest.raises(RuntimeError) as failure:
        run_connect(adapter)
    assert calls == []
    if wiring == "matched":
        assert str(failure.value) == "FIXTURE_LISTENER_OWNERSHIP_UNBOUND"


def test_failed_bind_cannot_fall_back_to_production(adapter_module, fixture_helper):
    scenario = Scenario(adapter_module, fixture_helper)
    scenario.prepare_direct()
    with pytest.raises(RuntimeError):
        scenario.adapter._bind_fixture_listener(object())
    with pytest.raises(RuntimeError, match="FIXTURE_BINDING_UNAVAILABLE"):
        run_connect(scenario.adapter)


@pytest.mark.parametrize("field", ["worker_generation", "source_generation", "runner", "config"])
def test_changed_retained_context_refuses_at_connect(adapter_module, fixture_helper, field):
    scenario = Scenario(adapter_module, fixture_helper)
    adapter = scenario.delegate.factory(scenario.config)
    object.__setattr__(scenario.binding, field, object())
    with pytest.raises(RuntimeError, match="FIXTURE_CONTEXT_CHANGED"):
        run_connect(adapter)


def test_conflicting_class_refuses_and_already_expected_runner_can_bind(
    adapter_module, fixture_helper, monkeypatch
):
    scenario = Scenario(adapter_module, fixture_helper)
    scenario.prepare_direct()
    scenario.adapter.gateway_runner = scenario.runner
    scenario.direct_bind()
    assert scenario.owner.bound_adapter is scenario.adapter

    class ForeignAdapter(adapter_module.HmpAdapter):
        pass

    foreign = ForeignAdapter(scenario.config)
    calls = []

    def forbidden(*_args, **_kwargs):
        calls.append("forbidden")
        raise AssertionError("Rejected subclass must not enter production setup")

    monkeypatch.setattr(adapter_module.server, "listener_settings", forbidden)
    monkeypatch.setattr(adapter_module.server, "HmpServer", forbidden)
    monkeypatch.setattr(adapter_module, "open_components", forbidden)
    monkeypatch.setattr(adapter_module, "asyncio", SimpleNamespace(to_thread=forbidden))
    with pytest.raises(RuntimeError, match="FIXTURE_ADAPTER_TYPE_CHANGED"):
        foreign._bind_fixture_listener(scenario.slot)
    assert foreign._fixture_binding_attempted and foreign._fixture_binding_failed
    with pytest.raises(RuntimeError, match="FIXTURE_BINDING_UNAVAILABLE"):
        run_connect(foreign)
    assert calls == []


def test_unbound_production_connect_reaches_original_settings(adapter_module, monkeypatch):
    calls = []

    class ProductionReached(BaseException):
        pass

    def settings(extra):
        calls.append(extra)
        raise ProductionReached

    monkeypatch.delitem(sys.modules, "native_media_listener_factory", raising=False)
    config = SimpleNamespace(extra={})
    adapter = adapter_module.HmpAdapter(config)
    monkeypatch.setattr(adapter_module.server, "listener_settings", settings)
    with pytest.raises(ProductionReached):
        run_connect(adapter)
    assert calls == [config.extra] and adapter._fixture_listener_binding is None

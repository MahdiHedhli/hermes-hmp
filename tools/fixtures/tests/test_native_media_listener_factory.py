"""Inert scoped-owner causals; no native imports, descriptors or listener calls.

ModelAuthority validates one builtin state after fault hooks. Its restore-stage
debt counter is synthetic and never certifies actual native lifecycle custody.
"""

import sys
import traceback
import unittest
from contextlib import suppress
from dataclasses import dataclass, fields, replace
from types import ModuleType

import native_media_listener_factory as helper_module
from native_media_listener_factory import (
    FixtureScopeOwner,
    ScopedFactoryDelegate,
    ScopeRefusedError,
    StartupBinding,
)

CAUSALS = []


@dataclass
class ModelEntry:
    name: str
    adapter_factory: object
    check_fn: object
    validate_config: object
    ensure_deps_fn: object
    auth_metadata: object
    required_env: object
    source: object
    plugin_name: object
    future_metadata_field: object


class ModelAdapter:
    def __init__(self, config):
        self.config = config
        self.model_binding = None

    def _bind_fixture_listener(self, slot):
        if self.model_binding is None:
            raise ScopeRefusedError("ADAPTER_BINDING_UNBOUND")
        self.model_binding.bind(self, slot)
        slot.owner.accept_adapter_binding(slot, self)


class ModelRegistry:
    """Pure model of the pinned public identity-CAS tuple operations."""

    def __init__(self, entry):
        self.scope = "inert-home-A"
        self.state = (entry, None)
        self.hook = None
        self.cas_calls = 0
        self.policy_calls = []

    def before(self, operation):
        if self.hook is not None:
            self.hook(operation)

    def current_scope_key(self):
        self.before("scope")
        return self.scope

    def snapshot_registration(self, name, *, scope):
        self.before("snapshot")
        assert name == "hmp" and scope == "inert-home-A"
        return self.state

    def get(self, name):
        self.before("get")
        assert name == "hmp"
        return self.state[0]

    def restore_registration(self, name, current, previous, *, scope):
        self.before("cas")
        assert name == "hmp" and scope == "inert-home-A"
        self.cas_calls += 1
        if self.state[0] is not current[0] or self.state[1] is not current[1]:
            return False
        self.state = previous
        return True

    def create_adapter(self, config):
        entry = self.get("hmp")
        self.policy_calls.append("check")
        if not entry.check_fn() and (entry.ensure_deps_fn is None or not entry.ensure_deps_fn()):
            return None
        if entry.validate_config is not None:
            self.policy_calls.append("validate")
            if not entry.validate_config(config):
                return None
        try:
            return entry.adapter_factory(config)
        except ScopeRefusedError:
            return None


class ModelAuthority:
    """Inert coherent checkpoint; default real authority remains unbound."""

    def __init__(self, binding):
        self.expected = binding
        self.source_generation = binding.source_generation
        self.worker_generation = binding.worker_generation
        self.listener_owner = binding.listener_owner
        self.cancelled = False
        self.now = 1.0
        self.native_debt = 0
        self.hook = None

    def checkpoint(self, stage, binding):
        if self.hook is not None:
            self.hook(stage)
        # All foreign hooks are before this builtin-state commit.
        if binding is not self.expected:
            raise ScopeRefusedError("OWNER_BINDING_CHANGED")
        if binding.registry.scope != binding.scope:
            raise ScopeRefusedError("SCOPE_CHANGED")
        if self.cancelled:
            raise ScopeRefusedError("CANCELLED")
        if (
            self.source_generation is not binding.source_generation
            or self.worker_generation is not binding.worker_generation
            or self.listener_owner is not binding.listener_owner
        ):
            raise ScopeRefusedError("GENERATION_CHANGED")
        if stage in ("restore_ready", "restore") and self.native_debt != 0:
            raise ScopeRefusedError("LIFECYCLE_DEBT")
        return self.now


class ModelBinding:
    def __init__(self):
        self.calls = []
        self.hook = None

    def bind(self, adapter, slot):
        self.calls.append((adapter, slot))
        if self.hook is not None:
            self.hook()
        assert type(adapter) is ModelAdapter and slot.claimed
        assert adapter.config is slot.binding.config


class Scenario:
    def __init__(self, *, authority_bound=True, backend_bound=True):
        self.config = object()
        self.factory_calls = []
        self.factory_hook = None

        def original(config):
            self.factory_calls.append(config)
            adapter = ModelAdapter(config)
            adapter.model_binding = self.backend if backend_bound else None
            self.last_adapter = adapter
            self.authority.native_debt = 1
            if self.factory_hook is not None:
                self.factory_hook()
            return adapter

        self.original_factory = original
        self.entry = ModelEntry(
            "hmp",
            original,
            lambda: True,
            lambda _config: True,
            None,
            object(),
            [],
            object(),
            object(),
            object(),
        )
        self.registry = ModelRegistry(self.entry)
        self.binding = StartupBinding(
            self.registry,
            self.registry.scope,
            "A",
            1,
            self.config,
            object(),
            self.entry,
            original,
            ModelAdapter,
            helper_module,
            helper_module.__spec__.origin,
            "0" * 64,
            object(),
            object(),
            object(),
            30.0,
        )
        self.authority = ModelAuthority(self.binding)
        self.owner = FixtureScopeOwner(
            self.binding, authority=self.authority if authority_bound else None
        )
        self.backend = ModelBinding()
        self.delegate = ScopedFactoryDelegate(self.owner)

    def install(self):
        self.slot = self.owner.issue_slot()
        self.delegate.install(self.slot)


class ScopeTests(unittest.TestCase):
    def terminal(self, scenario):
        first = scenario.owner.first_failure
        self.assertIsNotNone(first)
        self.assertEqual(scenario.owner.state, "POISONED")
        before = (
            len(scenario.factory_calls),
            scenario.registry.cas_calls,
            len(scenario.backend.calls),
        )
        for action in (
            lambda: scenario.delegate.factory(scenario.config),
            scenario.owner.issue_slot,
            scenario.owner.issue_restore_permit,
            lambda: scenario.delegate.restore(object()),
        ):
            with self.assertRaises(ScopeRefusedError):
                action()
            self.assertIs(scenario.owner.first_failure, first)
        self.assertEqual(
            before,
            (len(scenario.factory_calls), scenario.registry.cas_calls, len(scenario.backend.calls)),
        )

    def record(self, case):
        CAUSALS.append(case)

    def test_default_authority_refuses_before_registration(self):
        s = Scenario(authority_bound=False)
        with self.assertRaisesRegex(ScopeRefusedError, "STARTUP_AUTHORITY_UNBOUND"):
            s.owner.issue_slot()
        self.assertEqual((s.registry.cas_calls, len(s.factory_calls)), (0, 0))
        self.terminal(s)
        self.record("default-authority-unbound")

    def test_default_binding_refuses_and_retains_constructed_adapter(self):
        s = Scenario(backend_bound=False)
        s.install()
        with self.assertRaisesRegex(ScopeRefusedError, "FACTORY_UNCERTAIN"):
            s.delegate.factory(s.config)
        self.assertEqual(s.owner.first_failure.code, "ADAPTER_BINDING_UNBOUND")
        self.assertIs(s.owner.adapter_debt, s.last_adapter)
        self.assertIs(s.registry.state[0], s.delegate.delegated_state[0])
        self.assertEqual(len(s.factory_calls), 1)
        self.terminal(s)
        self.record("default-binding-unbound-retains-debt-and-barrier")

    def test_full_field_preservation_and_normal_policy_path(self):
        s = Scenario()
        s.install()
        delegated = s.registry.state[0]
        for member in fields(s.entry):
            if member.name != "adapter_factory":
                self.assertIs(getattr(delegated, member.name), getattr(s.entry, member.name))
        adapter = s.registry.create_adapter(s.config)
        self.assertIs(adapter, s.last_adapter)
        self.assertEqual(s.registry.policy_calls, ["check", "validate"])
        self.assertEqual(s.factory_calls, [s.config])
        self.assertEqual(s.backend.calls, [(adapter, s.slot)])
        self.assertEqual(s.owner.state, "ADAPTER_BOUND")
        self.record("preserve-all-dataclass-fields-and-policy-factory-path")

    def test_dependency_and_config_failures_do_not_call_factory(self):
        for policy in ("dependency", "config", "installer"):
            s = Scenario()
            if policy in ("dependency", "installer"):
                s.entry.check_fn = lambda: False
            if policy == "config":
                s.entry.validate_config = lambda _config: False
            if policy == "installer":
                s.entry.ensure_deps_fn = lambda: False
            s.install()
            self.assertIsNone(s.registry.create_adapter(s.config))
            self.assertEqual(s.factory_calls, [])
            self.assertFalse(s.slot.claimed)
            self.record("policy-refusal:" + policy)

    def test_cas_install_refuses_foreign_entry_or_loader(self):
        for field in (0, 1):
            s = Scenario()
            slot = s.owner.issue_slot()
            foreign = object()

            def race(operation, *, scenario=s, changed=foreign, key=field):
                if operation == "cas":
                    scenario.registry.state = (
                        (changed, None) if key == 0 else (scenario.entry, changed)
                    )

            s.registry.hook = race
            with self.assertRaisesRegex(ScopeRefusedError, "INSTALL_CAS_FAILED"):
                s.delegate.install(slot)
            self.assertIs(s.registry.state[field], foreign)
            self.assertEqual((len(s.factory_calls), len(s.backend.calls)), (0, 0))
            self.terminal(s)
            self.record("install-cas-foreign:" + str(field))

    def test_global_fallback_without_scoped_snapshot_refuses(self):
        s = Scenario()
        s.registry.state = (None, None)
        s.registry.get = lambda _name: s.entry
        slot = s.owner.issue_slot()
        with self.assertRaisesRegex(ScopeRefusedError, "REGISTRATION_CHANGED"):
            s.delegate.install(slot)
        self.assertEqual(s.registry.cas_calls, 0)
        self.terminal(s)
        self.record("global-fallback-is-not-scoped-ownership")

    def test_unissued_wrong_slot_config_scope_and_foreign_factory(self):
        for fault in ("unissued", "wrong_slot", "config", "scope", "entry", "loader"):
            s = Scenario()
            if fault == "unissued":
                action, argument = s.delegate.factory, s.config
            elif fault == "wrong_slot":
                s.owner.issue_slot()
                action, argument = s.delegate.install, object()
            else:
                s.install()
                if fault == "scope":
                    s.registry.scope = "inert-home-B"
                if fault == "entry":
                    s.registry.state = (object(), None)
                if fault == "loader":
                    s.registry.state = (s.registry.state[0], object())
                action = s.delegate.factory
                argument = object() if fault == "config" else s.config
            with self.assertRaises(ScopeRefusedError):
                action(argument)
            self.assertEqual((len(s.factory_calls), len(s.backend.calls)), (0, 0))
            self.terminal(s)
            self.record("factory-refusal:" + fault)

    def test_consumed_delegate_refuses_all_retry_invocations(self):
        s = Scenario()
        s.install()
        s.delegate.factory(s.config)
        with self.assertRaisesRegex(ScopeRefusedError, "FACTORY_UNCERTAIN"):
            s.delegate.factory(s.config)
        self.assertEqual(s.owner.first_failure.code, "FACTORY_CONSUMED")
        self.assertIs(s.registry.state[0], s.delegate.delegated_state[0])
        self.terminal(s)
        self.record("consumed-retry-barrier-no-production-fallback")

    def test_original_factory_throw_retains_unknown_construction_debt(self):
        class Cancel(BaseException):
            pass

        for failure in (RuntimeError(), Cancel()):
            s = Scenario()
            s.install()

            def throw(error=failure):
                raise error

            s.factory_hook = throw
            if isinstance(failure, Exception):
                with self.assertRaisesRegex(ScopeRefusedError, "FACTORY_UNCERTAIN"):
                    s.delegate.factory(s.config)
            else:
                with self.assertRaises(type(failure)):
                    s.delegate.factory(s.config)
            self.assertTrue(s.owner.factory_attempted)
            self.assertTrue(s.slot.claimed)
            self.assertIsNone(s.owner.adapter_debt)
            self.assertIs(s.owner.first_failure, failure)
            self.assertEqual(len(s.factory_calls), 1)
            self.terminal(s)
            self.record("factory-throw:" + type(failure).__name__)

    def test_foreign_helper_errors_notes_causes_and_subclasses_are_redacted(self):
        class ForeignRefusalError(ScopeRefusedError):
            pass

        marker = "SYNTHETIC_PRIVATE_CALLBACK_DETAIL"
        for site in ("factory", "bind", "registry", "checkpoint"):
            for payload in ("message", "cause_and_note", "subclass"):
                s = Scenario()
                s.install()
                error_type = ForeignRefusalError if payload == "subclass" else ScopeRefusedError
                original = error_type(marker if payload == "message" else "FACTORY_CONSUMED")
                if payload != "message":
                    original.__cause__ = ValueError(marker)
                    original.add_note(marker)

                def fail(*_args, error=original, **_kwargs):
                    raise error

                if site == "factory":
                    s.factory_hook = fail
                elif site == "bind":
                    s.backend.hook = fail
                elif site == "registry":
                    s.registry.hook = fail
                else:
                    s.authority.hook = fail
                with self.assertRaises(ScopeRefusedError) as caught:
                    s.delegate.factory(s.config)
                public = caught.exception
                self.assertIsNot(public, original)
                self.assertEqual(str(public), "FACTORY_UNCERTAIN")
                self.assertIsNone(public.__cause__)
                self.assertIsNone(public.__context__)
                self.assertFalse(getattr(public, "__notes__", ()))
                self.assertNotIn(marker, "".join(traceback.format_exception(public)))
                self.assertIs(s.owner.first_failure, original)
                self.assertIs(s.registry.state[0], s.delegate.delegated_state[0])
                self.assertTrue(
                    s.slot.claimed if site in ("factory", "bind") else not s.slot.claimed
                )
                if site == "bind":
                    self.assertIs(s.owner.adapter_debt, s.last_adapter)
                elif site == "factory":
                    self.assertTrue(s.owner.factory_attempted)
                    self.assertIsNone(s.owner.adapter_debt)
                else:
                    self.assertEqual(s.factory_calls, [])
                self.terminal(s)
                self.record("redacted-foreign-helper-error:" + site + ":" + payload)

    def test_returned_adapter_retained_after_normal_return_generation_change(self):
        for fault in (
            "source_generation",
            "worker_generation",
            "listener_owner",
            "cancel",
            "deadline",
        ):
            s = Scenario()
            s.install()

            def change(*, scenario=s, change_kind=fault):
                if change_kind == "cancel":
                    scenario.authority.cancelled = True
                elif change_kind == "deadline":
                    scenario.authority.now = 30.0
                else:
                    setattr(scenario.authority, change_kind, object())

            s.factory_hook = change
            with self.assertRaises(ScopeRefusedError):
                s.delegate.factory(s.config)
            self.assertIs(s.owner.adapter_debt, s.last_adapter)
            self.assertEqual(s.backend.calls, [])
            self.terminal(s)
            self.record("late-factory-return:" + fault)

    def test_wrong_adapter_type_or_config_refuses_before_binding(self):
        for fault in ("type", "config"):
            s = Scenario()
            original = s.binding.original_factory

            def replacement(config, *, factory=original, change_kind=fault):
                adapter = factory(config)
                if change_kind == "config":
                    adapter.config = object()
                    return adapter
                return object()

            # Fresh scenario binds this exact factory before installation;
            # changing a live factory identity is a separate refusal.
            s.entry.adapter_factory = replacement
            s.binding = replace(s.binding, original_factory=replacement)
            s.authority = ModelAuthority(s.binding)
            s.owner = FixtureScopeOwner(s.binding, authority=s.authority)
            s.delegate = ScopedFactoryDelegate(s.owner)
            s.install()
            with self.assertRaises(ScopeRefusedError):
                s.delegate.factory(s.config)
            self.assertEqual(s.backend.calls, [])
            self.assertEqual(len(s.factory_calls), 1)
            self.terminal(s)
            self.record("wrong-adapter:" + fault)

    def test_auxiliary_callback_reentry_poison_is_sticky_when_caught(self):
        s = Scenario()
        s.install()

        def caught_auxiliary():
            with suppress(ScopeRefusedError):
                s.owner.checkpoint("factory")

        s.factory_hook = caught_auxiliary
        with self.assertRaises(ScopeRefusedError):
            s.delegate.factory(s.config)
        self.assertIs(s.owner.adapter_debt, s.last_adapter)
        self.assertEqual(s.backend.calls, [])
        self.terminal(s)
        self.record("caught-auxiliary-checkpoint-reentry-terminal")

    def test_canonical_module_class_constructor_namespace_replacement_refuses(self):
        for fault in (
            "module",
            "spec_origin",
            "owner_class",
            "slot_class",
            "binding_class",
            "constructor",
            "accept_method",
        ):
            s = Scenario()
            s.install()
            original_spec_origin = helper_module.__spec__.origin
            original_owner = helper_module.FixtureScopeOwner
            original_slot = helper_module._StartupSlot
            original_binding = helper_module.StartupBinding
            original_constructor = original_owner.__init__
            original_accept = original_owner.accept_adapter_binding

            def foreign(*_args):
                return None

            try:
                if fault == "module":
                    sys.modules["native_media_listener_factory"] = ModuleType(
                        "native_media_listener_factory"
                    )
                elif fault == "spec_origin":
                    helper_module.__spec__.origin = "/inert/foreign.py"
                elif fault == "owner_class":
                    helper_module.FixtureScopeOwner = type("ForeignOwner", (), {})
                elif fault == "slot_class":
                    helper_module._StartupSlot = type("ForeignSlot", (), {})
                elif fault == "binding_class":
                    helper_module.StartupBinding = type("ForeignBinding", (), {})
                elif fault == "constructor":
                    original_owner.__init__ = foreign
                else:
                    original_owner.accept_adapter_binding = foreign
                with self.assertRaises(ScopeRefusedError):
                    s.delegate.factory(s.config)
                self.assertEqual(s.factory_calls, [])
            finally:
                # Test-only restoration of collector-owned Python metadata;
                # no scope revival or runtime/registry custody claim.
                sys.modules["native_media_listener_factory"] = helper_module
                helper_module.__spec__.origin = original_spec_origin
                helper_module.FixtureScopeOwner = original_owner
                helper_module._StartupSlot = original_slot
                helper_module.StartupBinding = original_binding
                original_owner.__init__ = original_constructor
                original_owner.accept_adapter_binding = original_accept
            self.terminal(s)
            self.record("helper-provenance-replacement:" + fault)

    def test_caught_and_propagated_reentry_at_all_external_sites(self):
        for site in ("checkpoint", "scope", "snapshot", "get", "cas", "factory", "bind"):
            for caught in (False, True):
                s = Scenario()
                s.install()

                def reenter(*, scenario=s, swallow=caught):
                    try:
                        scenario.owner.issue_slot()
                    except ScopeRefusedError:
                        if not swallow:
                            raise

                if site == "checkpoint":
                    s.authority.hook = lambda _stage: reenter()
                elif site == "factory":
                    s.factory_hook = reenter
                elif site == "bind":
                    s.backend.hook = reenter
                elif site == "cas":
                    # The CAS callback is reached on restoration, after debt
                    # settlement in this inert model; never auto restoration.
                    s.delegate.factory(s.config)
                    s.authority.native_debt = 0
                    permit = s.owner.issue_restore_permit()
                    s.registry.hook = lambda operation, reenter=reenter, site=site: (
                        reenter() if operation == site else None
                    )
                else:
                    s.registry.hook = lambda operation, reenter=reenter, site=site: (
                        reenter() if operation == site else None
                    )
                with self.assertRaises(ScopeRefusedError):
                    if site == "cas":
                        s.delegate.restore(permit)
                    else:
                        s.delegate.factory(s.config)
                if site == "factory" and caught:
                    self.assertIs(s.owner.adapter_debt, s.last_adapter)
                self.terminal(s)
                self.record(f"reentry:{site}:{caught}")

    def test_cancel_or_expiry_during_install_keeps_cas_effect_honest(self):
        for fault in ("cancel", "deadline"):
            s = Scenario()
            slot = s.owner.issue_slot()

            def change(operation, *, scenario=s, change_kind=fault):
                if operation == "cas":
                    if change_kind == "cancel":
                        scenario.authority.cancelled = True
                    else:
                        scenario.authority.now = 30.0

            s.registry.hook = change
            with self.assertRaises(ScopeRefusedError):
                s.delegate.install(slot)
            self.assertIs(s.registry.state[0], s.delegate.delegated_state[0])
            self.assertEqual(s.factory_calls, [])
            self.terminal(s)
            self.record("install-cas-return-then:" + fault)

    def test_restore_requires_explicit_zero_debt_permit(self):
        s = Scenario()
        s.install()
        s.delegate.factory(s.config)
        with self.assertRaisesRegex(ScopeRefusedError, "LIFECYCLE_DEBT"):
            s.owner.issue_restore_permit()
        self.assertIs(s.registry.state[0], s.delegate.delegated_state[0])
        self.terminal(s)
        self.record("restore-debt-not-caller-boolean")

    def test_known_restore_once_and_no_automatic_finally_restore(self):
        s = Scenario()
        s.install()
        s.delegate.factory(s.config)
        self.assertIs(s.registry.state[0], s.delegate.delegated_state[0])
        s.authority.native_debt = 0
        permit = s.owner.issue_restore_permit()
        s.delegate.restore(permit)
        self.assertIs(s.registry.state[0], s.entry)
        self.assertEqual(s.owner.state, "RESTORED")
        self.assertTrue(permit.used)
        with self.assertRaises(ScopeRefusedError):
            s.delegate.restore(permit)
        self.assertEqual(s.registry.cas_calls, 2)
        self.terminal(s)
        self.record("explicit-known-zero-debt-restore-once")

    def test_restore_foreign_entry_loader_and_debt_return(self):
        for fault in ("entry", "loader", "debt"):
            s = Scenario()
            s.install()
            s.delegate.factory(s.config)
            s.authority.native_debt = 0
            permit = s.owner.issue_restore_permit()
            foreign = object()

            def change(operation, *, scenario=s, change_kind=fault, changed=foreign):
                if operation == "cas":
                    if change_kind == "entry":
                        scenario.registry.state = (changed, None)
                    elif change_kind == "loader":
                        scenario.registry.state = (scenario.registry.state[0], changed)
                    else:
                        scenario.authority.native_debt = 1

            s.registry.hook = change
            with self.assertRaises(ScopeRefusedError):
                s.delegate.restore(permit)
            if fault in ("entry", "loader"):
                self.assertIs(s.registry.state[0 if fault == "entry" else 1], foreign)
            else:
                # Actual CAS effect retained, never lied about or rolled back.
                self.assertIs(s.registry.state[0], s.entry)
            self.assertTrue(permit.used)
            self.terminal(s)
            self.record("restore-cas:" + fault)

    def test_restore_arbitrary_boolean_or_foreign_permit_refuses(self):
        for value in (True, object()):
            s = Scenario()
            s.install()
            s.delegate.factory(s.config)
            with self.assertRaisesRegex(ScopeRefusedError, "RESTORE_PERMIT"):
                s.delegate.restore(value)
            self.assertEqual(s.registry.cas_calls, 1)
            self.terminal(s)
            self.record("restore-unissued-permit:" + type(value).__name__)

    def test_invalid_and_regressed_checkpoint_samples_refuse(self):
        for value in (True, -1, float("nan"), float("inf"), 30.0, 0.5):
            s = Scenario()
            s.install()
            s.authority.now = value
            with self.assertRaises(ScopeRefusedError):
                s.delegate.factory(s.config)
            self.assertEqual(s.factory_calls, [])
            self.terminal(s)
            self.record("sample-refusal:" + repr(value))

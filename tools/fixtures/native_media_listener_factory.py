"""Source-only scoped HMP factory delegation; default authority/binder refuse.

This helper imports no native module and opens/adopts/closes no descriptor.
An injected protocol-shaped object is not proof of root authority. A separately
reviewed root checkpoint must bind the immutable startup context and verify
actual zero lifecycle debt for restore stages. The adapter/socket backend is
also unbound until its source and custody are independently qualified.
"""

import math
import sys
from contextlib import contextmanager, suppress
from dataclasses import dataclass, fields, is_dataclass, replace
from importlib.machinery import ModuleSpec
from types import FunctionType, ModuleType


class ScopeRefusedError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(condition, code):
    if not condition:
        raise ScopeRefusedError(code)


class UnboundStartupAuthority:
    def checkpoint(self, stage, binding):
        raise ScopeRefusedError("STARTUP_AUTHORITY_UNBOUND")


@dataclass(frozen=True, init=False)
class StartupBinding:
    """Context data, not a permit; root checkpoint supplies actual authority.

    Source/worker/listener generations are opaque root-owned identities.
    ``config`` is the exact object passed through normal native preparation.
    No schedule, actor credential, socket FD or future media row is fabricated.
    """

    registry: object
    scope: str
    role: str
    ordinal: int
    config: object
    runner: object
    original_entry: object
    original_factory: object
    adapter_type: type
    source_module: object
    source_origin: str
    source_sha256: str
    source_generation: object
    worker_generation: object
    listener_owner: object
    deadline: float

    def __init__(
        self,
        registry,
        scope,
        role,
        ordinal,
        config,
        runner,
        original_entry,
        original_factory,
        adapter_type,
        source_module,
        source_origin,
        source_sha256,
        source_generation,
        worker_generation,
        listener_owner,
        deadline,
    ):
        # Explicit source-defined constructor: provenance checks must not
        # silently treat a generated dataclass '<string>' initializer as source.
        for name, value in (
            ("registry", registry),
            ("scope", scope),
            ("role", role),
            ("ordinal", ordinal),
            ("config", config),
            ("runner", runner),
            ("original_entry", original_entry),
            ("original_factory", original_factory),
            ("adapter_type", adapter_type),
            ("source_module", source_module),
            ("source_origin", source_origin),
            ("source_sha256", source_sha256),
            ("source_generation", source_generation),
            ("worker_generation", worker_generation),
            ("listener_owner", listener_owner),
            ("deadline", deadline),
        ):
            object.__setattr__(self, name, value)


_ISSUER = object()


class _StartupSlot:
    def __init__(self, issuer, owner):
        require(issuer is _ISSUER, "SLOT_ISSUER")
        self.owner = owner
        self.binding = owner.binding
        self.claimed = False


class _RestorePermit:
    def __init__(self, issuer, owner):
        require(issuer is _ISSUER, "RESTORE_ISSUER")
        self.owner = owner
        self.slot = owner.slot
        self.used = False


class FixtureScopeOwner:
    """One fail-stop logical startup owner; never a runtime custody receipt."""

    def __init__(self, binding, *, authority=None):
        require(type(binding) is StartupBinding, "BINDING_SCHEMA")
        require(type(binding.scope) is str and 0 < len(binding.scope) <= 4096, "SCOPE_SCHEMA")
        require(type(binding.role) is str and binding.role in ("A", "B"), "ROLE_SCHEMA")
        require(
            type(binding.ordinal) is int
            and 1 <= binding.ordinal <= (3 if binding.role == "A" else 2),
            "ORDINAL_SCHEMA",
        )
        require(
            type(binding.deadline) in (int, float)
            and math.isfinite(binding.deadline)
            and binding.deadline > 0,
            "DEADLINE_SCHEMA",
        )
        require(type(binding.adapter_type) is type, "ADAPTER_TYPE_SCHEMA")
        require(type(binding.source_module) is ModuleType, "SOURCE_MODULE_SCHEMA")
        require(
            type(binding.source_origin) is str and 0 < len(binding.source_origin) <= 4096,
            "SOURCE_ORIGIN_SCHEMA",
        )
        require(
            type(binding.source_sha256) is str
            and len(binding.source_sha256) == 64
            and all(char in "0123456789abcdef" for char in binding.source_sha256),
            "SOURCE_HASH_SCHEMA",
        )
        require(
            is_dataclass(binding.original_entry) and not isinstance(binding.original_entry, type),
            "ENTRY_SCHEMA",
        )
        require(callable(binding.original_factory), "FACTORY_SCHEMA")
        self.binding = binding
        self.authority = UnboundStartupAuthority() if authority is None else authority
        self.state = "UNISSUED"
        self.slot = None
        self.restore_permit = None
        self.first_failure = None
        self.operation = None
        self.in_callback = False
        self.last_now = None
        self.factory_attempted = False
        self.adapter_debt = None
        self.binding_attempted = False
        self.binding_hook_active = False
        self.bound_adapter = None
        self._helper_types = (type(self), type(binding), _StartupSlot, _RestorePermit)
        self._accept_function = vars(type(self))["accept_adapter_binding"]

    def _source_identity(self):
        binding = self.binding
        module = sys.modules.get("native_media_listener_factory")
        require(
            type(module) is ModuleType and module is binding.source_module, "HELPER_MODULE_CHANGED"
        )
        space = vars(module)
        spec = space.get("__spec__")
        require(
            type(spec) is ModuleSpec
            and spec.name == "native_media_listener_factory"
            and space.get("__name__") == "native_media_listener_factory"
            and spec.loader is not None
            and spec.origin == binding.source_origin
            and space.get("__file__") == binding.source_origin,
            "HELPER_SPEC_CHANGED",
        )
        for name, expected in zip(
            ("FixtureScopeOwner", "StartupBinding", "_StartupSlot", "_RestorePermit"),
            self._helper_types,
            strict=True,
        ):
            require(space.get(name) is expected, "HELPER_TYPE_CHANGED")
            constructor = vars(expected)["__init__"]
            require(
                type(constructor) is FunctionType
                and constructor.__globals__ is space
                and constructor.__code__.co_filename == binding.source_origin,
                "HELPER_CONSTRUCTOR_CHANGED",
            )
        method = vars(type(self))["accept_adapter_binding"]
        require(
            method is self._accept_function
            and type(method) is FunctionType
            and method.__globals__ is space
            and method.__code__.co_filename == binding.source_origin,
            "HELPER_FUNCTION_CHANGED",
        )

    def poison(self, error):
        if self.first_failure is None:
            self.first_failure = error
        self.state = "POISONED"

    def assert_live(self):
        require(self.first_failure is None, "SCOPE_TERMINAL")

    @contextmanager
    def flight(self):
        self.assert_live()
        if self.operation is not None or self.in_callback:
            error = ScopeRefusedError("SCOPE_REENTRY")
            self.poison(error)
            raise error
        token = object()
        self.operation = token
        try:
            yield
            self.assert_live()
            require(self.operation is token, "OPERATION_REPLACED")
        except BaseException as error:
            self.poison(error)
            raise
        finally:
            self.operation = None

    def _callback(self, function, *args, retain_adapter=False, binding_hook=False, **kwargs):
        self.assert_live()
        if self.operation is None or self.in_callback:
            error = ScopeRefusedError("CALLBACK_REENTRY")
            self.poison(error)
            raise error
        token = self.operation
        self.in_callback = True
        self.binding_hook_active = binding_hook
        try:
            value = function(*args, **kwargs)
            # Retain a constructed result before checking a caught reentry or
            # changed authority. An invalid result is debt, never output.
            if retain_adapter:
                self.adapter_debt = value
        finally:
            self.in_callback = False
            self.binding_hook_active = False
        self.assert_live()
        require(self.operation is token, "OPERATION_REPLACED")
        return value

    def checkpoint(self, stage):
        self._source_identity()
        now = self._callback(self.authority.checkpoint, stage, self.binding)
        self._source_identity()
        require(
            type(now) in (int, float) and math.isfinite(now) and 0 <= now < self.binding.deadline,
            "DEADLINE",
        )
        require(self.last_now is None or now >= self.last_now, "CLOCK_REGRESSION")
        self.last_now = now

    def accept_adapter_binding(self, slot, adapter):
        """Private parser-like hook for the direct HMP bind callback, no IO.

        This hook records only exact in-memory binding ownership. It performs
        no new authority callback and supplies no socket/runtime certificate.
        """
        try:
            self.assert_live()
            self._source_identity()
            require(
                self.operation is not None and self.in_callback and self.binding_hook_active,
                "BIND_HOOK_PHASE",
            )
            require(
                type(slot) is _StartupSlot
                and slot is self.slot
                and slot.owner is self
                and slot.binding is self.binding
                and slot.claimed,
                "SLOT_BINDING",
            )
            require(
                self.state == "FACTORY_CLAIMED"
                and self.adapter_debt is adapter
                and type(adapter) is self.binding.adapter_type,
                "ADAPTER_BINDING",
            )
            require(adapter.config is self.binding.config, "ADAPTER_CONFIG_CHANGED")
            require(self.bound_adapter is None, "ADAPTER_ALREADY_BOUND")
            self.bound_adapter = adapter
        except BaseException as error:
            self.poison(error)
            raise

    def invoke(self, stage, function, *args, **kwargs):
        self.checkpoint(stage)
        value = self._callback(function, *args, **kwargs)
        self.checkpoint(stage)
        return value

    def issue_slot(self):
        with self.flight():
            require(self.state == "UNISSUED", "SLOT_ALREADY_ISSUED")
            self.checkpoint("issue")
            self.slot = _StartupSlot(_ISSUER, self)
            self.state = "ROOT_ISSUED"
            return self.slot

    def issue_restore_permit(self):
        with self.flight():
            require(self.state == "ADAPTER_BOUND", "RESTORE_STATE")
            require(self.restore_permit is None, "RESTORE_ALREADY_ISSUED")
            # Trusted restore_ready must observe actual native/adapter/thread/
            # task/server/connection/FD zero debt coherently. It cannot accept
            # a caller Boolean or this helper's logical fields as that proof.
            self.checkpoint("restore_ready")
            self.restore_permit = _RestorePermit(_ISSUER, self)
            return self.restore_permit


class ScopedFactoryDelegate:
    """Public scoped CAS around exactly one original factory invocation."""

    def __init__(self, owner):
        require(type(owner) is FixtureScopeOwner, "OWNER_SCHEMA")
        self.owner = owner
        self.original_state = None
        self.delegated_state = None

    def _registry_state(self, expected, stage):
        owner, binding = self.owner, self.owner.binding
        scope = owner.invoke(stage, binding.registry.current_scope_key)
        require(type(scope) is str and scope == binding.scope, "SCOPE_CHANGED")
        snapshot = owner.invoke(
            stage, binding.registry.snapshot_registration, "hmp", scope=binding.scope
        )
        require(
            type(snapshot) is tuple
            and len(snapshot) == 2
            and snapshot[0] is expected[0]
            and snapshot[1] is expected[1],
            "REGISTRATION_CHANGED",
        )
        entry = owner.invoke(stage, binding.registry.get, "hmp")
        require(entry is expected[0], "SCOPED_ENTRY_CHANGED")

    def install(self, slot):
        with self.owner.flight():
            owner, binding = self.owner, self.owner.binding
            require(
                type(slot) is _StartupSlot and slot is owner.slot and slot.owner is owner,
                "SLOT_BINDING",
            )
            require(owner.state == "ROOT_ISSUED" and not slot.claimed, "INSTALL_STATE")
            require(
                binding.original_entry.adapter_factory is binding.original_factory,
                "ORIGINAL_FACTORY_CHANGED",
            )
            self.original_state = (binding.original_entry, None)
            self._registry_state(self.original_state, "install")
            delegated = owner.invoke(
                "install", replace, binding.original_entry, adapter_factory=self.factory
            )
            require(type(delegated) is type(binding.original_entry), "ENTRY_TYPE_CHANGED")
            for member in fields(binding.original_entry):
                if member.name != "adapter_factory":
                    require(
                        getattr(delegated, member.name)
                        is getattr(binding.original_entry, member.name),
                        "ENTRY_FIELD_CHANGED",
                    )
            self.delegated_state = (delegated, None)
            installed = owner.invoke(
                "install",
                binding.registry.restore_registration,
                "hmp",
                self.original_state,
                self.delegated_state,
                scope=binding.scope,
            )
            require(installed is True, "INSTALL_CAS_FAILED")
            self._registry_state(self.delegated_state, "install")
            owner.checkpoint("install")
            owner.state = "REGISTRY_INSTALLED"

    def factory(self, config):
        # Native public create_adapter logs Exception text/traceback. Keep
        # ALL ordinary failures privately, including our error type/subclasses.
        # Leave the handled exception context before raising the fresh public
        # error so it has no copied cause/context/notes. BaseException still
        # propagates with its original fail-stop debt.
        with suppress(Exception):
            return self._factory(config)
        raise ScopeRefusedError("FACTORY_UNCERTAIN") from None

    def _factory(self, config):
        with self.owner.flight():
            owner, binding = self.owner, self.owner.binding
            slot = owner.slot
            require(
                owner.state == "REGISTRY_INSTALLED" and slot is not None and not slot.claimed,
                "FACTORY_CONSUMED",
            )
            require(config is binding.config, "CONFIG_CHANGED")
            self._registry_state(self.delegated_state, "factory")
            owner.checkpoint("factory")
            slot.claimed = True
            owner.factory_attempted = True
            owner.state = "FACTORY_CLAIMED"
            adapter = owner.invoke("factory", binding.original_factory, config, retain_adapter=True)
            require(type(adapter) is binding.adapter_type, "ADAPTER_TYPE_CHANGED")
            self._registry_state(self.delegated_state, "factory")
            require(getattr(adapter, "config", None) is config, "ADAPTER_CONFIG_CHANGED")
            bind = getattr(adapter, "_bind_fixture_listener", None)
            require(callable(bind), "ADAPTER_BINDING_UNBOUND")
            owner.binding_attempted = True
            result = owner.invoke("bind", bind, slot, binding_hook=True)
            require(result is None, "BIND_RESULT")
            require(owner.bound_adapter is adapter, "BINDING_NOT_RETAINED")
            self._registry_state(self.delegated_state, "bind")
            owner.checkpoint("bind")
            owner.state = "ADAPTER_BOUND"
            return adapter

    def restore(self, permit):
        with self.owner.flight():
            owner, binding = self.owner, self.owner.binding
            require(
                type(permit) is _RestorePermit
                and permit is owner.restore_permit
                and permit.owner is owner
                and permit.slot is owner.slot
                and not permit.used,
                "RESTORE_PERMIT",
            )
            require(owner.state == "ADAPTER_BOUND", "RESTORE_STATE")
            self._registry_state(self.delegated_state, "restore")
            owner.checkpoint("restore")
            permit.used = True
            restored = owner.invoke(
                "restore",
                binding.registry.restore_registration,
                "hmp",
                self.delegated_state,
                self.original_state,
                scope=binding.scope,
            )
            require(restored is True, "RESTORE_CAS_FAILED")
            self._registry_state(self.original_state, "restore")
            owner.checkpoint("restore")
            owner.state = "RESTORED"

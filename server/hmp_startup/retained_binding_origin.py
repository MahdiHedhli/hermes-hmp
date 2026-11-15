"""Selected helper inspection DATA, held by the early parent; not an audit grant.

The independent parent authenticates this module's primitives/globals/function
code/defaults before dispatch and retains the literal capture return. Standalone
coherent copies remain DATA, not original entry ownership. No caller skips an
audit using this component. Only loaded HMP objects are read, never profiles/files.
"""
import sys
from types import CellType, FunctionType, ModuleType


_MODULES = (
    "hmp_plugin.presentation_gateway_package",
    "hmp_plugin.presentation_gateway_recipe",
    "hmp_plugin.presentation_startup_selection",
    "hmp_plugin.presentation_gateway_activation",
    "hmp_plugin.presentation_startup_artifacts",
    "hmp_startup.gateway_approval",
    "hmp_startup.gateway_entry",
    "hmp_startup.runtime_files",
    "hmp_startup.entry_files",
    "hmp_startup.cache_context",
    "hmp_startup.cache_candidates",
)
# Only the listed activation/approval/entry/cache values change during allocation. Their
# keys remain required; the original retained-scope body freshly joins their
# values to its actual owner/scope. This DATA checker supplies no such authority.
_LIVE_GLOBALS = (
    (),
    (),
    (),
    ("_ENTRY_OWNER", "_ENTRY_CELL"),
    (),
    ("_OWNER", "_CELL", "_ROOT", "_FACT"),
    ("_OWNER", "_CELL", "_STARTED", "_START_ATTEMPTED", "_ENTRY_ORIGIN"),
    (),
    (),
    ("_OWNER", "_ROOT", "_FACT"),
    (),
)
_CLASSES = (
    (0, "GatewayPackageOwner"),
    (0, "_Manifest"),
    (1, "GatewayRecipeOwner"),
    (2, "StartupSelectionOwner"),
    (2, "_Scope"),
    (2, "_ApprovedSelectionSource"),
    (2, "GatewayStartupSelection"),
    (2, "SelectionLoadError"),
    (0, "PackageInventoryError"),
    (1, "GatewayRecipeError"),
    (3, "GatewayActivationOwner"),
    (3, "_ActivationScope"),
    (3, "ActivationCaptureError"),
    (4, "ExpectedArtifact"),
    (4, "ArtifactObservationError"),
    (4, "_Descriptor"),
    (4, "_NativeScopeRegistration"),
    (4, "_NativeOpenAllocation"),
    (4, "_NativeCloseAllocation"),
    (4, "_NativeOpenedDescriptor"),
    (0, "RetainedPackageData"),
    (0, "_Scan"),
    (1, "_Recipe"),
    (5, "GatewayApprovalOwner"),
    (5, "GatewayApprovalError"),
    (5, "_RootSource"),
    (5, "GatewayOperatorApproval"),
    (6, "GatewayEntryOwner"),
    (6, "GatewayEntryError"),
    (6, "_Invocation"),
    (6, "_EntryOrigin"),
    (6, "EntryStartupData"),
    (6, "_InterpreterOrigin"),
    (6, "InterpreterStartupData"),
    (6, "_NativeIOOrigin"),
    (6, "_NativeFileLineage"),
    (6, "_NativeFileLedger"),
    (6, "_NativeFilePhase"),
    (4, "OperatorApprovalPath"),
    (4, "_OperatorFileReceipt"),
    (4, "_ReadEffect"),
    (7, "RuntimeFilesError"),
    (7, "RuntimePackage"),
    (7, "LinkHop"),
    (7, "ExecutableLinkPlan"),
    (7, "RuntimeFilePlan"),
    (8, "EntryFilesError"),
    (8, "_Inputs"),
    (8, "EntryFileSnapshotOwner"),
    (9, "CacheContextError"),
    (9, "CacheInputData"),
    (9, "_ContextSource"),
    (9, "CacheContextOwner"),
    (10, "CacheCandidateError"),
    (10, "PlannedCachePath"),
)
_FUNCTIONS = (
    (0, "GatewayPackageOwner", "_retained_binding"),
    (1, "GatewayRecipeOwner", "_retained_binding"),
    (0, None, "_require"),
    (1, None, "_require"),
    (1, None, "_same_recipe_binding"),
    (2, "StartupSelectionOwner", "_retained_binding"),
    (2, None, "_approved_recipe"),
    (2, None, "_approval_binding"),
    (2, None, "_require"),
    (2, "SelectionLoadError", "__init__"),
    (0, "PackageInventoryError", "__init__"),
    (1, "GatewayRecipeError", "__init__"),
    (3, "GatewayActivationOwner", "_retained_scope"),
    (3, None, "_require"),
    (3, "ActivationCaptureError", "__init__"),
    (4, None, "_descriptor_closed_in_scope"),
    (4, None, "_native_descriptor_closed"),
    (4, None, "_native_descriptor_opened"),
    (4, None, "_native_file_allocation_original"),
    (4, None, "_expected"),
    (4, None, "_require"),
    (4, "ArtifactObservationError", "__init__"),
    (5, "GatewayApprovalOwner", "_retained_binding"),
    (5, "GatewayApprovalOwner", "_seal"),
    (5, "GatewayApprovalOwner", "_closed_custody"),
    (5, None, "_require"),
    (5, None, "_same_entry"),
    (5, None, "_api_state"),
    (5, "GatewayApprovalError", "__init__"),
    (6, "GatewayEntryOwner", "_retained_binding"),
    (6, None, "_native_file_ledger_shape"),
    (6, None, "_require"),
    (6, "GatewayEntryError", "__init__"),
    (4, None, "_closed_file_graph_mirrors"),
    (4, None, "_scope_file_graph_mirrors"),
    (4, None, "_loaded_owner_graph_mirrors"),
    (4, None, "_cache_context_graph_mirrors"),
    (4, None, "_approval_graph_mirrors"),
    (4, None, "_entry_graph_mirrors"),
    (4, None, "_activation_graph_mirrors"),
    (4, None, "_native_io_graph_mirrors"),
    (4, None, "_interpreter_graph_mirrors"),
    (7, "RuntimeFilesError", "__init__"),
    (7, None, "_require"),
    (7, None, "_pairs"),
    (7, None, "_document"),
    (7, None, "_path"),
    (7, None, "_inside"),
    (7, None, "_typed_equal"),
    (7, None, "_library_name"),
    (7, "LinkHop", "__repr__"),
    (7, "ExecutableLinkPlan", "__repr__"),
    (7, None, "_link_plan"),
    (7, "RuntimeFilePlan", "__repr__"),
    (7, None, "build_runtime_plan"),
    (7, None, "build_runtime_link_plan"),
    (7, None, "_build_runtime_plan"),
    (7, None, "plan_current"),
    (7, None, "loaded_origins"),
    (8, "EntryFilesError", "__init__"),
    (8, None, "_require"),
    (8, None, "_same_package"),
    (8, None, "_pairs"),
    (8, "_Inputs", "__repr__"),
    (8, None, "_decode"),
    (8, "EntryFileSnapshotOwner", "_current"),
    (8, "EntryFileSnapshotOwner", "_pure_lineage"),
    (8, "EntryFileSnapshotOwner", "_pure_current"),
    (8, "EntryFileSnapshotOwner", "_io_current"),
    (8, "EntryFileSnapshotOwner", "_names"),
    (8, "EntryFileSnapshotOwner", "_tree"),
    (8, "EntryFileSnapshotOwner", "_metadata"),
    (8, "EntryFileSnapshotOwner", "_walk"),
    (8, "EntryFileSnapshotOwner", "_origins"),
    (8, "EntryFileSnapshotOwner", "__repr__"),
    (9, "CacheContextError", "__init__"),
    (9, None, "_require"),
    (9, "CacheInputData", "__repr__"),
    (9, "_ContextSource", "__repr__"),
    (9, None, "_context"),
    (9, None, "_getter_current"),
    (9, None, "_rows"),
    (9, "CacheContextOwner", "__repr__"),
    (9, "CacheContextOwner", "_seal"),
    (9, "CacheContextOwner", "retained_binding"),
    (9, "CacheContextOwner", "current_binding"),
    (8, "EntryFileSnapshotOwner", "verify"),
    (8, "EntryFileSnapshotOwner", "verify_runtime_files"),
    (8, "EntryFileSnapshotOwner", "retain_runtime_files"),
    (8, "EntryFileSnapshotOwner", "retain_runtime_link_files"),
    (8, "EntryFileSnapshotOwner", "retain"),
    (8, "EntryFileSnapshotOwner", "_retain"),
    (8, "EntryFileSnapshotOwner", "complete"),
    (9, "CacheContextOwner", "retain"),
    (10, "CacheCandidateError", "__init__"),
    (10, None, "_require"),
    (10, None, "_location"),
    (10, None, "planned_cache_path"),
    (10, "PlannedCachePath", "__repr__"),
)


class RetainedBindingOriginError(RuntimeError):
    pass


def capture(*, _classmethod=classmethod):
    """Collect candidates before checker callbacks; an independent root is required."""
    checker = current
    registry = sys.modules
    if type(registry) is not dict or not all(type(key) is str for key in registry):
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    modules = []
    for name, live_keys in zip(_MODULES, _LIVE_GLOBALS, strict=True):
        module = registry.get(name)
        if type(module) is not ModuleType:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        namespace = vars(module)
        if (type(namespace) is not dict or not all(type(key) is str for key in namespace)
                or type(namespace.get('__name__')) is not str or namespace['__name__'] != name
                or not all(key in namespace for key in live_keys)):
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        modules.append((module, namespace, tuple((key, value)
            for key, value in namespace.items() if key not in live_keys)))
    modules = tuple(modules)
    classes = []
    for index, name in _CLASSES:
        namespace = modules[index][1]
        if not all(type(key) is str for key in namespace):
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        kind = namespace.get(name)
        if type(kind) is not type:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        names = vars(kind)
        if not all(type(key) is str for key in names):
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        classes.append((kind, kind.__bases__, tuple(names.items())))
    classes = tuple(classes)
    functions = []
    for index, owner, name in _FUNCTIONS:
        namespace = modules[index][1]
        if not all(type(key) is str for key in namespace):
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        names = namespace
        held_members = ()
        if owner is not None:
            held_kind = None
            for row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = row[0]
                    held_members = row[2]
                    break
            if type(held_kind) is not type or namespace.get(owner) is not held_kind:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            names = vars(held_kind)
        if not all(type(key) is str for key in names):
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        function = names.get(name)
        if (index, owner, name) in (
            (8, "EntryFileSnapshotOwner", "verify"),
            (8, "EntryFileSnapshotOwner", "verify_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_link_files"),
            (8, "EntryFileSnapshotOwner", "retain"),
            (8, "EntryFileSnapshotOwner", "_retain"),
            (8, "EntryFileSnapshotOwner", "complete"),
            (9, "CacheContextOwner", "retain"),
        ):
            held_wrapper = None
            for held_name, held_value in held_members:
                if held_name == name:
                    held_wrapper = held_value
                    break
            if function is not held_wrapper:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            if type(function) is not _classmethod:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            function = function.__func__
        if type(function) is not FunctionType or function.__globals__ is not namespace:
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        defaults, kw, closure = function.__defaults__, function.__kwdefaults__, function.__closure__
        if (
            (defaults is not None and type(defaults) is not tuple)
            or (
                kw is not None and (type(kw) is not dict or not all(type(key) is str for key in kw))
            )
            or (
                closure is not None
                and (
                    type(closure) is not tuple
                    or not all(type(cell) is CellType for cell in closure)
                )
            )
        ):
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        try:
            cells = () if closure is None else tuple(cell.cell_contents for cell in closure)
        except ValueError:
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        functions.append(
            (
                function,
                function.__code__,
                namespace,
                defaults,
                kw,
                () if kw is None else tuple(kw.items()),
                closure,
                cells,
            )
        )
    packet = (sys, vars(sys), registry, modules, classes, tuple(functions))
    # No delegated helper was called while selecting the candidate references.
    # The independent caller authenticates checker/code/globals/defaults and
    # rejoins the literal packet after callbacks, before any audit consolidation.
    checked = checker(packet)
    if checked is not packet:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    return packet


def current(packet, *, _classmethod=classmethod):
    """Fresh structural/code comparisons only; no original-root or effect proof."""
    if (type(packet) is tuple and len(packet) == 6) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    system, system_names, registry, modules, classes, functions = packet
    if (type(system) is ModuleType and type(system_names) is dict
          and vars(system) is system_names
          and all(type(key) is str for key in system_names)
          and type(registry) is dict and all(type(key) is str for key in registry)
          and system_names.get('modules') is registry
          and type(modules) is tuple and len(modules) == len(_MODULES)
          and type(classes) is tuple and len(classes) == len(_CLASSES)
          and type(functions) is tuple and len(functions) == len(_FUNCTIONS)) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    builtin_module = registry.get('builtins')
    if type(builtin_module) is not ModuleType:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    builtin_namespace = vars(builtin_module)
    if (type(builtin_namespace) is dict
          and all(type(key) is str for key in builtin_namespace)) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for row, name, live_keys in zip(modules, _MODULES, _LIVE_GLOBALS, strict=True):
        if (type(row) is tuple and len(row) == 3) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        module, namespace, pairs = row
        if (type(module) is ModuleType and type(namespace) is dict
              and all(type(key) is str for key in registry)
              and all(type(key) is str for key in namespace)
              and registry.get(name) is module and vars(module) is namespace
              and type(namespace.get('__name__')) is str and namespace['__name__'] == name
              and (namespace.get('__builtins__') is builtin_namespace
                   or namespace.get('__builtins__') is builtin_module)
              and type(pairs) is tuple
              and len(namespace) == len(pairs) + len(live_keys)) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        # Compare in the live-to-private direction. Allocations may run GC
        # callbacks after the initial key fence; never hash an expected name
        # into that subsequently mutable dictionary. The private index contains
        # only exact strings from the original packet, not live foreign keys.
        expected_pairs = {}
        for pair in pairs:
            if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            key, value = pair
            if key in live_keys or key in expected_pairs:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            expected_pairs[key] = value
        valid, observed, live_seen = True, 0, 0
        try:
            for key, value in namespace.items():
                if type(key) is not str:
                    valid = False
                    break
                observed += 1
                if key in live_keys:
                    live_seen += 1
                elif key not in expected_pairs or expected_pairs[key] is not value:
                    valid = False
                    break
        except RuntimeError:
            valid = False  # A changed-size/key iterator is refusal, not retry.
        if (valid is True and observed == len(pairs) + len(live_keys)
                and live_seen == len(live_keys)) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for row, (index, name) in zip(classes, _CLASSES, strict=True):
        if (type(row) is tuple and len(row) == 3) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        kind, bases, pairs = row
        if (type(kind) is type
              and all(type(key) is str for key in modules[index][1])
              and modules[index][1].get(name) is kind
              and kind.__bases__ is bases and type(pairs) is tuple) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        names = vars(kind)
        if (all(type(key) is str for key in names) and len(names) == len(pairs)) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        seen = set()
        for pair in pairs:
            if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            key, value = pair
            if (key not in seen and key in names and names[key] is value) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            seen.add(key)
    for row, (index, owner, name) in zip(functions, _FUNCTIONS, strict=True):
        if (type(row) is tuple and len(row) == 8) is not True:
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        function, code, namespace, defaults, kw, pairs, closure, cells = row
        if (
            type(namespace) is dict
            and namespace is modules[index][1]
            and type(function) is FunctionType
            and function.__globals__ is namespace
            and function.__builtins__ is builtin_namespace
            and function.__code__ is code
            and function.__defaults__ is defaults
            and (defaults is None or type(defaults) is tuple)
            and function.__kwdefaults__ is kw
            and function.__closure__ is closure
            and type(pairs) is tuple
            and type(cells) is tuple
        ) is not True:
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        names = namespace
        held_members = ()
        if (all(type(key) is str for key in namespace)) is not True:
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        if owner is not None:
            held_kind = None
            for class_row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = class_row[0]
                    held_members = class_row[2]
                    break
            if (
                type(held_kind) is type
                and all(type(key) is str for key in namespace)
                and namespace.get(owner) is held_kind
            ) is not True:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            names = vars(held_kind)
        if not all(type(key) is str for key in names):
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        raw_function = names.get(name)
        if (index, owner, name) in (
            (8, "EntryFileSnapshotOwner", "verify"),
            (8, "EntryFileSnapshotOwner", "verify_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_link_files"),
            (8, "EntryFileSnapshotOwner", "retain"),
            (8, "EntryFileSnapshotOwner", "_retain"),
            (8, "EntryFileSnapshotOwner", "complete"),
            (9, "CacheContextOwner", "retain"),
        ):
            held_wrapper = None
            for held_name, held_value in held_members:
                if held_name == name:
                    held_wrapper = held_value
                    break
            if raw_function is not held_wrapper:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            if type(raw_function) is not _classmethod:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            raw_function = raw_function.__func__
        if raw_function is not function:
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        if kw is None:
            if (pairs == ()) is not True:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        else:
            if (
                type(kw) is dict and all(type(key) is str for key in kw) and len(kw) == len(pairs)
            ) is not True:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            seen = set()
            for pair in pairs:
                if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                    raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
                key, value = pair
                if (key not in seen and key in kw and kw[key] is value) is not True:
                    raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
                seen.add(key)
        if closure is None:
            if (cells == ()) is not True:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        else:
            if (type(closure) is tuple and len(closure) == len(cells)) is not True:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            try:
                if (
                    all(
                        type(cell) is CellType and cell.cell_contents is value
                        for cell, value in zip(closure, cells, strict=True)
                    )
                ) is not True:
                    raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            except ValueError:
                raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
    if (all(type(key) is str for key in modules[0][1])
          and modules[0][1].get('GatewayRecipeOwner') is classes[2][0]
          and modules[0][1].get('_same_recipe_binding') is functions[4][0]) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # Join the imported aliases to the same defining objects, not merely to an
    # independently coherent snapshot in each importing module.
    if (all(type(key) is str for key in modules[0][1])
          and all(type(key) is str for key in modules[1][1])
          and modules[0][1].get('StartupSelectionOwner') is classes[3][0]
          and modules[1][1].get('StartupSelectionOwner') is classes[3][0]
          and modules[0][1].get('GatewayStartupSelection') is classes[6][0]
          and modules[1][1].get('GatewayStartupSelection') is classes[6][0]
          and modules[0][1].get('IoScope') is classes[4][0]
          and modules[1][1].get('_Scope') is classes[4][0]
          and modules[1][1].get('_approved_recipe') is functions[6][0]) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if (all(type(key) is str for key in modules[0][1])
          and all(type(key) is str for key in modules[1][1])
          and all(type(key) is str for key in modules[2][1])
          and all(type(key) is str for key in modules[3][1])
          and modules[0][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[1][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[2][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[2][1].get('_LATE_MODULES') is modules[3][1].get('_LATE_MODULES')) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # The shared descriptor/expectation code is held BEFORE the later engine
    # capture. Rejoining that later engine snapshot alone could adopt code drift.
    if (all(type(key) is str for key in modules[4][1])
          and modules[4][1].get('_Scope') is classes[4][0]
          and modules[4][1].get('GatewayActivationOwner') is classes[10][0]) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for index in (0, 1, 2):
        namespace = modules[index][1]
        if (all(type(key) is str for key in namespace)
              and namespace.get('ExpectedArtifact') is classes[13][0]
              and namespace.get('_descriptor_closed_in_scope') is functions[15][0]
              and namespace.get('_expected') is functions[19][0]) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # Approval's live owner/cell/root/fact values are not cached authority. Its
    # actual original validators still freshly join those values on each audit.
    if (all(type(key) is str for key in modules[5][1])
          and modules[2][1].get('_APPROVAL_OWNER_TYPE') is classes[23][0]
          and modules[5][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[5][1].get('_LATE_MODULES') is modules[3][1].get('_LATE_MODULES')
          and modules[5][1].get('ExpectedArtifact') is classes[13][0]
          and modules[5][1].get('_Scope') is classes[4][0]
          and modules[5][1].get('_descriptor_closed_in_scope') is functions[15][0]
          and modules[5][1].get('OperatorApprovalPath') is classes[38][0]
          and modules[5][1].get('_OperatorFileReceipt') is classes[39][0]
          and modules[5][1].get('_ReadEffect') is classes[40][0]) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # The root is staged before capture and published only by the original
    # entry capture's literal return. DATA currentness does not approve a root
    # value, a started allocation or the one-attempt flag; original validators do.
    if (all(type(key) is str for key in modules[6][1])
          and modules[5][1].get('GatewayEntryOwner') is classes[27][0]
          and modules[6][1].get('GatewayActivationOwner') is classes[10][0]) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for runtime_consumer, runtime_alias, runtime_definition, runtime_name in (
        (7, "_artifacts", 4, None),
        (7, "_PRIVATE", 0, "_PRIVATE"),
        (7, "_table_rows", 0, "_table_rows"),
        (7, "ExpectedArtifact", 4, "ExpectedArtifact"),
        (7, "_expected", 4, "_expected"),
        (7, "_HashedArtifact", 4, "_HashedArtifact"),
        (8, "GatewayActivationOwner", 3, "GatewayActivationOwner"),
        (8, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
        (8, "_same_origins", 0, "_same_origins"),
        (8, "_Scan", 0, "_Scan"),
        (8, "_table_rows", 0, "_table_rows"),
        (8, "_Tree", 0, "_Tree"),
        (8, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
        (8, "_same_recipe_binding", 1, "_same_recipe_binding"),
        (8, "ExpectedArtifact", 4, "ExpectedArtifact"),
        (8, "StartupArtifactOwner", 4, "StartupArtifactOwner"),
        (8, "_capture_native_scope", 4, "_capture_native_scope"),
        (8, "_descriptor_closed_in_scope", 4, "_descriptor_closed_in_scope"),
        (8, "_descriptor_refused", 4, "_descriptor_refused"),
        (8, "_expected", 4, "_expected"),
        (8, "_HashedArtifact", 4, "_HashedArtifact"),
        (8, "_identity", 4, "_identity"),
        (8, "_native_registration_tail", 4, "_native_registration_tail"),
        (8, "_native_walk_scope", 4, "_native_walk_scope"),
        (8, "_Scope", 4, "_Scope"),
        (8, "gateway_entry", 6, None),
        (8, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
        (9, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
        (9, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
        (9, "_same_recipe_binding", 1, "_same_recipe_binding"),
        (9, "ExpectedArtifact", 4, "ExpectedArtifact"),
        (9, "RuntimeFilePlan", 7, "RuntimeFilePlan"),
        (9, "RuntimePackage", 7, "RuntimePackage"),
        (9, "plan_current", 7, "plan_current"),
        (9, "EntryFileSnapshotOwner", 8, "EntryFileSnapshotOwner"),
        (9, "_Inputs", 8, "_Inputs"),
        (9, "_same_package", 8, "_same_package"),
        (9, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
        (9, "_origin_current", 6, "_origin_current"),
        (9, "PlannedCachePath", 10, "PlannedCachePath"),
        (9, "_location", 10, "_location"),
        (9, "planned_cache_path", 10, "planned_cache_path"),
        (10, "RuntimeFilesError", 7, "RuntimeFilesError"),
        (10, "_path", 7, "_path"),
    ):
        runtime_consumer_names = modules[runtime_consumer][1]
        runtime_definition_names = modules[runtime_definition][1]
        if not all(
            type(runtime_key) is str for runtime_key in runtime_consumer_names
        ) or not all(type(runtime_key) is str for runtime_key in runtime_definition_names):
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        runtime_expected = (
            modules[runtime_definition][0]
            if runtime_name is None
            else runtime_definition_names.get(runtime_name)
        )
        if (
            (runtime_name is not None and runtime_name not in runtime_definition_names)
            or runtime_alias not in runtime_consumer_names
            or runtime_consumer_names[runtime_alias] is not runtime_expected
        ):
            raise RetainedBindingOriginError("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
    return packet


def current_live(packet, bound_layout, *, _error=RuntimeError, _classmethod=classmethod):
    """Fresh mutable audit using the independently held original layout only.

    The rooted parent must establish actual original entry/capsule/layout identity
    and callee provenance BEFORE this call. Generic current() remains the complete
    untrusted DATA parser; this internal target supplies no original-root authority.
    """
    if (type(bound_layout) is not tuple or len(bound_layout) != 4
            or bound_layout[0] is not packet):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if (type(packet) is tuple and len(packet) == 6) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    system, system_names, registry, modules, classes, functions = packet
    if (type(system) is ModuleType and type(system_names) is dict
          and vars(system) is system_names
          and all(type(key) is str for key in system_names)
          and type(registry) is dict and all(type(key) is str for key in registry)
          and system_names.get('modules') is registry
          and type(modules) is tuple and len(modules) == len(_MODULES)
          and type(classes) is tuple and len(classes) == len(_CLASSES)
          and type(functions) is tuple and len(functions) == len(_FUNCTIONS)) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    builtin_module = registry.get('builtins')
    if type(builtin_module) is not ModuleType:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    builtin_namespace = vars(builtin_module)
    if (type(builtin_namespace) is dict
          and all(type(key) is str for key in builtin_namespace)) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for row, name, live_keys, column in zip(modules, _MODULES, _LIVE_GLOBALS, bound_layout[1], strict=True):
        module, namespace, pairs = row
        _, keys, values = column
        if (type(module) is ModuleType and type(namespace) is dict
              and all(type(key) is str for key in registry)
              and all(type(key) is str for key in namespace)
              and registry.get(name) is module and vars(module) is namespace
              and type(namespace.get('__name__')) is str and namespace['__name__'] == name
              and (namespace.get('__builtins__') is builtin_namespace
                   or namespace.get('__builtins__') is builtin_module)
              and len(namespace) == len(keys) + len(live_keys)) is not True:
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        # Original immutable columns were fully validated before root publication.
        # Fresh private lookup plus live-to-private iteration preserves GC refusal.
        expected_pairs = dict(zip(keys, values, strict=True))
        valid, observed, live_seen = True, 0, 0
        try:
            for key, value in namespace.items():
                if type(key) is not str:
                    valid = False
                    break
                observed += 1
                if key in live_keys:
                    live_seen += 1
                elif key not in expected_pairs or expected_pairs[key] is not value:
                    valid = False
                    break
        except RuntimeError:
            valid = False
        if (valid is True and observed == len(keys) + len(live_keys)
                and live_seen == len(live_keys)) is not True:
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for row, (index, name), column in zip(classes, _CLASSES, bound_layout[2], strict=True):
        kind, bases, pairs = row
        _, keys, values = column
        if (type(kind) is type
              and all(type(key) is str for key in modules[index][1])
              and modules[index][1].get(name) is kind and kind.__bases__ is bases) is not True:
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        names = vars(kind)
        if (all(type(key) is str for key in names) and len(names) == len(keys)) is not True:
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        for key, value in zip(keys, values, strict=True):
            if (key in names and names[key] is value) is not True:
                raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for row, (index, owner, name), column in zip(
        functions, _FUNCTIONS, bound_layout[3], strict=True
    ):
        function, code, namespace, defaults, kw, pairs, closure, cells = row
        _, keys, values = column
        if (
            type(namespace) is dict
            and namespace is modules[index][1]
            and type(function) is FunctionType
            and function.__globals__ is namespace
            and function.__builtins__ is builtin_namespace
            and function.__code__ is code
            and function.__defaults__ is defaults
            and function.__kwdefaults__ is kw
            and function.__closure__ is closure
        ) is not True:
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        names = namespace
        held_members = ()
        if (all(type(key) is str for key in namespace)) is not True:
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        if owner is not None:
            held_kind = None
            for class_row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = class_row[0]
                    held_members = class_row[2]
                    break
            if (
                type(held_kind) is type
                and all(type(key) is str for key in namespace)
                and namespace.get(owner) is held_kind
            ) is not True:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            names = vars(held_kind)
        if not all(type(key) is str for key in names):
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        raw_function = names.get(name)
        if (index, owner, name) in (
            (8, "EntryFileSnapshotOwner", "verify"),
            (8, "EntryFileSnapshotOwner", "verify_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_link_files"),
            (8, "EntryFileSnapshotOwner", "retain"),
            (8, "EntryFileSnapshotOwner", "_retain"),
            (8, "EntryFileSnapshotOwner", "complete"),
            (9, "CacheContextOwner", "retain"),
        ):
            held_wrapper = None
            for held_name, held_value in held_members:
                if held_name == name:
                    held_wrapper = held_value
                    break
            if raw_function is not held_wrapper:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            if type(raw_function) is not _classmethod:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            raw_function = raw_function.__func__
        if raw_function is not function:
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        if kw is not None:
            if (
                type(kw) is dict and all(type(key) is str for key in kw) and len(kw) == len(keys)
            ) is not True:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            for key, value in zip(keys, values, strict=True):
                if (key in kw and kw[key] is value) is not True:
                    raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        if closure is not None:
            if (type(closure) is tuple and len(closure) == len(cells)) is not True:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            try:
                if (
                    all(
                        type(cell) is CellType and cell.cell_contents is value
                        for cell, value in zip(closure, cells, strict=True)
                    )
                ) is not True:
                    raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            except ValueError:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
    if (all(type(key) is str for key in modules[0][1])
          and modules[0][1].get('GatewayRecipeOwner') is classes[2][0]
          and modules[0][1].get('_same_recipe_binding') is functions[4][0]) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # Join the imported aliases to the same defining objects, not merely to an
    # independently coherent snapshot in each importing module.
    if (all(type(key) is str for key in modules[0][1])
          and all(type(key) is str for key in modules[1][1])
          and modules[0][1].get('StartupSelectionOwner') is classes[3][0]
          and modules[1][1].get('StartupSelectionOwner') is classes[3][0]
          and modules[0][1].get('GatewayStartupSelection') is classes[6][0]
          and modules[1][1].get('GatewayStartupSelection') is classes[6][0]
          and modules[0][1].get('IoScope') is classes[4][0]
          and modules[1][1].get('_Scope') is classes[4][0]
          and modules[1][1].get('_approved_recipe') is functions[6][0]) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if (all(type(key) is str for key in modules[0][1])
          and all(type(key) is str for key in modules[1][1])
          and all(type(key) is str for key in modules[2][1])
          and all(type(key) is str for key in modules[3][1])
          and modules[0][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[1][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[2][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[2][1].get('_LATE_MODULES') is modules[3][1].get('_LATE_MODULES')) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # The shared descriptor/expectation code is held BEFORE the later engine
    # capture. Rejoining that later engine snapshot alone could adopt code drift.
    if (all(type(key) is str for key in modules[4][1])
          and modules[4][1].get('_Scope') is classes[4][0]
          and modules[4][1].get('GatewayActivationOwner') is classes[10][0]) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for index in (0, 1, 2):
        namespace = modules[index][1]
        if (all(type(key) is str for key in namespace)
              and namespace.get('ExpectedArtifact') is classes[13][0]
              and namespace.get('_descriptor_closed_in_scope') is functions[15][0]
              and namespace.get('_expected') is functions[19][0]) is not True:
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # Approval's live owner/cell/root/fact values are not cached authority. Its
    # actual original validators still freshly join those values on each audit.
    if (all(type(key) is str for key in modules[5][1])
          and modules[2][1].get('_APPROVAL_OWNER_TYPE') is classes[23][0]
          and modules[5][1].get('GatewayActivationOwner') is classes[10][0]
          and modules[5][1].get('_LATE_MODULES') is modules[3][1].get('_LATE_MODULES')
          and modules[5][1].get('ExpectedArtifact') is classes[13][0]
          and modules[5][1].get('_Scope') is classes[4][0]
          and modules[5][1].get('_descriptor_closed_in_scope') is functions[15][0]
          and modules[5][1].get('OperatorApprovalPath') is classes[38][0]
          and modules[5][1].get('_OperatorFileReceipt') is classes[39][0]
          and modules[5][1].get('_ReadEffect') is classes[40][0]) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # The root is staged before capture and published only by the original
    # entry capture's literal return. DATA currentness does not approve a root
    # value, a started allocation or the one-attempt flag; original validators do.
    if (all(type(key) is str for key in modules[6][1])
          and modules[5][1].get('GatewayEntryOwner') is classes[27][0]
          and modules[6][1].get('GatewayActivationOwner') is classes[10][0]) is not True:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for runtime_consumer, runtime_alias, runtime_definition, runtime_name in (
        (7, "_artifacts", 4, None),
        (7, "_PRIVATE", 0, "_PRIVATE"),
        (7, "_table_rows", 0, "_table_rows"),
        (7, "ExpectedArtifact", 4, "ExpectedArtifact"),
        (7, "_expected", 4, "_expected"),
        (7, "_HashedArtifact", 4, "_HashedArtifact"),
        (8, "GatewayActivationOwner", 3, "GatewayActivationOwner"),
        (8, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
        (8, "_same_origins", 0, "_same_origins"),
        (8, "_Scan", 0, "_Scan"),
        (8, "_table_rows", 0, "_table_rows"),
        (8, "_Tree", 0, "_Tree"),
        (8, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
        (8, "_same_recipe_binding", 1, "_same_recipe_binding"),
        (8, "ExpectedArtifact", 4, "ExpectedArtifact"),
        (8, "StartupArtifactOwner", 4, "StartupArtifactOwner"),
        (8, "_capture_native_scope", 4, "_capture_native_scope"),
        (8, "_descriptor_closed_in_scope", 4, "_descriptor_closed_in_scope"),
        (8, "_descriptor_refused", 4, "_descriptor_refused"),
        (8, "_expected", 4, "_expected"),
        (8, "_HashedArtifact", 4, "_HashedArtifact"),
        (8, "_identity", 4, "_identity"),
        (8, "_native_registration_tail", 4, "_native_registration_tail"),
        (8, "_native_walk_scope", 4, "_native_walk_scope"),
        (8, "_Scope", 4, "_Scope"),
        (8, "gateway_entry", 6, None),
        (8, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
        (9, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
        (9, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
        (9, "_same_recipe_binding", 1, "_same_recipe_binding"),
        (9, "ExpectedArtifact", 4, "ExpectedArtifact"),
        (9, "RuntimeFilePlan", 7, "RuntimeFilePlan"),
        (9, "RuntimePackage", 7, "RuntimePackage"),
        (9, "plan_current", 7, "plan_current"),
        (9, "EntryFileSnapshotOwner", 8, "EntryFileSnapshotOwner"),
        (9, "_Inputs", 8, "_Inputs"),
        (9, "_same_package", 8, "_same_package"),
        (9, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
        (9, "_origin_current", 6, "_origin_current"),
        (9, "PlannedCachePath", 10, "PlannedCachePath"),
        (9, "_location", 10, "_location"),
        (9, "planned_cache_path", 10, "planned_cache_path"),
        (10, "RuntimeFilesError", 7, "RuntimeFilesError"),
        (10, "_path", 7, "_path"),
    ):
        runtime_consumer_names = modules[runtime_consumer][1]
        runtime_definition_names = modules[runtime_definition][1]
        if not all(
            type(runtime_key) is str for runtime_key in runtime_consumer_names
        ) or not all(type(runtime_key) is str for runtime_key in runtime_definition_names):
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        runtime_expected = (
            modules[runtime_definition][0]
            if runtime_name is None
            else runtime_definition_names.get(runtime_name)
        )
        if (
            (runtime_name is not None and runtime_name not in runtime_definition_names)
            or runtime_alias not in runtime_consumer_names
            or runtime_consumer_names[runtime_alias] is not runtime_expected
        ):
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
    return packet


def capture_bound(
    *,
    _checker=current,
    _checker_code=current.__code__,
    _checker_defaults=current.__defaults__,
    _checker_kw=current.__kwdefaults__,
    # Definition-time snapshots are required to authenticate later defaults.
    _checker_pairs=tuple(current.__kwdefaults__.items()),  # noqa: B008
    _live=current_live,
    _live_code=current_live.__code__,
    _live_defaults=current_live.__defaults__,
    _live_kw=current_live.__kwdefaults__,
    _live_pairs=()
    if current_live.__kwdefaults__ is None
    else tuple(current_live.__kwdefaults__.items()),  # noqa: B008
    _builtins=current.__builtins__,
    _module_roles=_MODULES,
    _class_roles=_CLASSES,
    _function_roles=_FUNCTIONS,
    _live_roles=_LIVE_GLOBALS,
    _type=type,
    _tuple=tuple,
    _dict=dict,
    _str=str,
    _len=len,
    _vars=vars,
    _any=any,
    _function=FunctionType,
    _error=RuntimeError,
    _classmethod=classmethod,
    _error_kind=RetainedBindingOriginError,
    _error_bases=RetainedBindingOriginError.__bases__,
    _error_members=tuple(vars(RetainedBindingOriginError).items()),  # noqa: B008
):
    """Literal selected packet/layout/checker DATA retained by the original parent.

    Generic capture() keeps its six-field API. The independent parent authenticates
    this original factory and retains this literal return. A consistent copy is
    not original-object authority. Mutable currentness is never cached by layout.
    """
    if (_type(_checker) is not _function or _type(_live) is not _function):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    namespace = _checker.__globals__
    if _live.__globals__ is not namespace:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    fixed = (
        ("current", _checker, _checker_code, _checker_defaults, _checker_kw, _checker_pairs),
        ("current_live", _live, _live_code, _live_defaults, _live_kw, _live_pairs),
    )
    live_row = ('current_live',_live,_live_code,namespace,_live_defaults,_live_kw,_live_pairs)
    if (_type(namespace) is not _dict or _any(_type(k) is not _str for k in namespace)
            or namespace.get('_MODULES') is not _module_roles
            or namespace.get('_CLASSES') is not _class_roles
            or namespace.get('_FUNCTIONS') is not _function_roles
            or namespace.get('_LIVE_GLOBALS') is not _live_roles):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # A refusal must not dispatch a constructor replaced by the callback.
    # Keep generic APIs unchanged, but authenticate their custom error channel
    # before entering them and use the held native error for factory refusal.
    if (_type(_error_kind) is not _type
            or namespace.get('RetainedBindingOriginError') is not _error_kind
            or _error_kind.__bases__ is not _error_bases):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    error_names = _vars(_error_kind)
    if (_any(_type(k) is not _str for k in error_names)
            or _len(error_names) != _len(_error_members)
            or _any(k not in error_names or error_names[k] is not v for k,v in _error_members)):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for name, function, code, defaults, kw, pairs in fixed:
        if (_type(function) is not _function or namespace.get(name) is not function
                or function.__code__ is not code or function.__globals__ is not namespace
                or function.__builtins__ is not _builtins or function.__closure__ is not None
                or function.__defaults__ is not defaults or function.__kwdefaults__ is not kw
                or (kw is not None and (_type(kw) is not _dict
                    or _any(_type(k) is not _str for k in kw)
                    or _len(kw) != _len(pairs)
                    or _any(k not in kw or kw[k] is not v for k,v in pairs)))):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    registry = sys.modules
    if type(registry) is not dict or not all(type(key) is str for key in registry):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    modules = []
    for name, live_keys in zip(_MODULES, _LIVE_GLOBALS, strict=True):
        module = registry.get(name)
        if type(module) is not ModuleType:
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        candidate_namespace = vars(module)
        if (type(candidate_namespace) is not dict or not all(type(key) is str for key in candidate_namespace)
                or type(candidate_namespace.get('__name__')) is not str or candidate_namespace['__name__'] != name
                or not all(key in candidate_namespace for key in live_keys)):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        modules.append((module, candidate_namespace, tuple((key, value)
            for key, value in candidate_namespace.items() if key not in live_keys)))
    modules = tuple(modules)
    classes = []
    for index, name in _CLASSES:
        candidate_namespace = modules[index][1]
        if not all(type(key) is str for key in candidate_namespace):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        kind = candidate_namespace.get(name)
        if type(kind) is not type:
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        names = vars(kind)
        if not all(type(key) is str for key in names):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        classes.append((kind, kind.__bases__, tuple(names.items())))
    classes = tuple(classes)
    functions = []
    for index, owner, name in _FUNCTIONS:
        candidate_namespace = modules[index][1]
        if not all(type(key) is str for key in candidate_namespace):
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        names = candidate_namespace
        held_members = ()
        if owner is not None:
            held_kind = None
            for row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = row[0]
                    held_members = row[2]
                    break
            if type(held_kind) is not type or candidate_namespace.get(owner) is not held_kind:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            names = vars(held_kind)
        if not all(type(key) is str for key in names):
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        function = names.get(name)
        if (index, owner, name) in (
            (8, "EntryFileSnapshotOwner", "verify"),
            (8, "EntryFileSnapshotOwner", "verify_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_files"),
            (8, "EntryFileSnapshotOwner", "retain_runtime_link_files"),
            (8, "EntryFileSnapshotOwner", "retain"),
            (8, "EntryFileSnapshotOwner", "_retain"),
            (8, "EntryFileSnapshotOwner", "complete"),
            (9, "CacheContextOwner", "retain"),
        ):
            held_wrapper = None
            for held_name, held_value in held_members:
                if held_name == name:
                    held_wrapper = held_value
                    break
            if function is not held_wrapper:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            if type(function) is not _classmethod:
                raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
            function = function.__func__
        if type(function) is not FunctionType or function.__globals__ is not candidate_namespace:
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        defaults, kw, closure = function.__defaults__, function.__kwdefaults__, function.__closure__
        if (
            (defaults is not None and type(defaults) is not tuple)
            or (
                kw is not None and (type(kw) is not dict or not all(type(key) is str for key in kw))
            )
            or (
                closure is not None
                and (
                    type(closure) is not tuple
                    or not all(type(cell) is CellType for cell in closure)
                )
            )
        ):
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        try:
            cells = () if closure is None else tuple(cell.cell_contents for cell in closure)
        except ValueError:
            raise _error("BI1_RETAINED_HELPER_ORIGIN_REFUSED") from None
        functions.append(
            (
                function,
                function.__code__,
                candidate_namespace,
                defaults,
                kw,
                () if kw is None else tuple(kw.items()),
                closure,
                cells,
            )
        )
    packet = (sys, vars(sys), registry, modules, classes, tuple(functions))
    if (_type(namespace) is not _dict or _any(_type(k) is not _str for k in namespace)
            or namespace.get('_MODULES') is not _module_roles
            or namespace.get('_CLASSES') is not _class_roles
            or namespace.get('_FUNCTIONS') is not _function_roles
            or namespace.get('_LIVE_GLOBALS') is not _live_roles):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # A refusal must not dispatch a constructor replaced by the callback.
    # Keep generic APIs unchanged, but authenticate their custom error channel
    # before entering them and use the held native error for factory refusal.
    if (_type(_error_kind) is not _type
            or namespace.get('RetainedBindingOriginError') is not _error_kind
            or _error_kind.__bases__ is not _error_bases):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    error_names = _vars(_error_kind)
    if (_any(_type(k) is not _str for k in error_names)
            or _len(error_names) != _len(_error_members)
            or _any(k not in error_names or error_names[k] is not v for k,v in _error_members)):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for name, function, code, defaults, kw, pairs in fixed:
        if (_type(function) is not _function or namespace.get(name) is not function
                or function.__code__ is not code or function.__globals__ is not namespace
                or function.__builtins__ is not _builtins or function.__closure__ is not None
                or function.__defaults__ is not defaults or function.__kwdefaults__ is not kw
                or (kw is not None and (_type(kw) is not _dict
                    or _any(_type(k) is not _str for k in kw)
                    or _len(kw) != _len(pairs)
                    or _any(k not in kw or kw[k] is not v for k,v in pairs)))):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if _checker(packet) is not packet:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if (_type(namespace) is not _dict or _any(_type(k) is not _str for k in namespace)
            or namespace.get('_MODULES') is not _module_roles
            or namespace.get('_CLASSES') is not _class_roles
            or namespace.get('_FUNCTIONS') is not _function_roles
            or namespace.get('_LIVE_GLOBALS') is not _live_roles):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # A refusal must not dispatch a constructor replaced by the callback.
    # Keep generic APIs unchanged, but authenticate their custom error channel
    # before entering them and use the held native error for factory refusal.
    if (_type(_error_kind) is not _type
            or namespace.get('RetainedBindingOriginError') is not _error_kind
            or _error_kind.__bases__ is not _error_bases):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    error_names = _vars(_error_kind)
    if (_any(_type(k) is not _str for k in error_names)
            or _len(error_names) != _len(_error_members)
            or _any(k not in error_names or error_names[k] is not v for k,v in _error_members)):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for name, function, code, defaults, kw, pairs in fixed:
        if (_type(function) is not _function or namespace.get(name) is not function
                or function.__code__ is not code or function.__globals__ is not namespace
                or function.__builtins__ is not _builtins or function.__closure__ is not None
                or function.__defaults__ is not defaults or function.__kwdefaults__ is not kw
                or (kw is not None and (_type(kw) is not _dict
                    or _any(_type(k) is not _str for k in kw)
                    or _len(kw) != _len(pairs)
                    or _any(k not in kw or kw[k] is not v for k,v in pairs)))):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    module_columns = _tuple((row, _tuple(pair[0] for pair in row[2]),
                             _tuple(pair[1] for pair in row[2])) for row in packet[3])
    class_columns = _tuple((row, _tuple(pair[0] for pair in row[2]),
                            _tuple(pair[1] for pair in row[2])) for row in packet[4])
    function_columns = _tuple((row, _tuple(pair[0] for pair in row[5]),
                               _tuple(pair[1] for pair in row[5])) for row in packet[5])
    layout = (packet,module_columns,class_columns,function_columns)
    record = (packet,layout,live_row)
    if (_type(namespace) is not _dict or _any(_type(k) is not _str for k in namespace)
            or namespace.get('_MODULES') is not _module_roles
            or namespace.get('_CLASSES') is not _class_roles
            or namespace.get('_FUNCTIONS') is not _function_roles
            or namespace.get('_LIVE_GLOBALS') is not _live_roles):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # A refusal must not dispatch a constructor replaced by the callback.
    # Keep generic APIs unchanged, but authenticate their custom error channel
    # before entering them and use the held native error for factory refusal.
    if (_type(_error_kind) is not _type
            or namespace.get('RetainedBindingOriginError') is not _error_kind
            or _error_kind.__bases__ is not _error_bases):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    error_names = _vars(_error_kind)
    if (_any(_type(k) is not _str for k in error_names)
            or _len(error_names) != _len(_error_members)
            or _any(k not in error_names or error_names[k] is not v for k,v in _error_members)):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for name, function, code, defaults, kw, pairs in fixed:
        if (_type(function) is not _function or namespace.get(name) is not function
                or function.__code__ is not code or function.__globals__ is not namespace
                or function.__builtins__ is not _builtins or function.__closure__ is not None
                or function.__defaults__ is not defaults or function.__kwdefaults__ is not kw
                or (kw is not None and (_type(kw) is not _dict
                    or _any(_type(k) is not _str for k in kw)
                    or _len(kw) != _len(pairs)
                    or _any(k not in kw or kw[k] is not v for k,v in pairs)))):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if _checker(packet) is not packet:
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if (_type(namespace) is not _dict or _any(_type(k) is not _str for k in namespace)
            or namespace.get('_MODULES') is not _module_roles
            or namespace.get('_CLASSES') is not _class_roles
            or namespace.get('_FUNCTIONS') is not _function_roles
            or namespace.get('_LIVE_GLOBALS') is not _live_roles):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # A refusal must not dispatch a constructor replaced by the callback.
    # Keep generic APIs unchanged, but authenticate their custom error channel
    # before entering them and use the held native error for factory refusal.
    if (_type(_error_kind) is not _type
            or namespace.get('RetainedBindingOriginError') is not _error_kind
            or _error_kind.__bases__ is not _error_bases):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    error_names = _vars(_error_kind)
    if (_any(_type(k) is not _str for k in error_names)
            or _len(error_names) != _len(_error_members)
            or _any(k not in error_names or error_names[k] is not v for k,v in _error_members)):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    for name, function, code, defaults, kw, pairs in fixed:
        if (_type(function) is not _function or namespace.get(name) is not function
                or function.__code__ is not code or function.__globals__ is not namespace
                or function.__builtins__ is not _builtins or function.__closure__ is not None
                or function.__defaults__ is not defaults or function.__kwdefaults__ is not kw
                or (kw is not None and (_type(kw) is not _dict
                    or _any(_type(k) is not _str for k in kw)
                    or _len(kw) != _len(pairs)
                    or _any(k not in kw or kw[k] is not v for k,v in pairs)))):
            raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if (record[0] is not packet or record[1] is not layout or record[2] is not live_row
            or layout[0] is not packet or live_row[1] is not _live or live_row[2] is not _live_code):
        raise _error('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    return record

"""Selected helper inspection DATA, held by the early parent; not an audit grant.

The independent parent authenticates this module's primitives/globals/function
code/defaults before dispatch and retains the literal capture return. Standalone
coherent copies remain DATA, not original entry ownership. No caller skips an
audit using this component. Only loaded HMP objects are read, never profiles/files.
"""
import sys
from types import CellType, FunctionType, ModuleType


_MODULES = ('hmp_plugin.presentation_gateway_package',
            'hmp_plugin.presentation_gateway_recipe',
            'hmp_plugin.presentation_startup_selection',
            'hmp_plugin.presentation_gateway_activation',
            'hmp_plugin.presentation_startup_artifacts')
# Only these two values legitimately change during activation allocation. Their
# keys remain required; the original retained-scope body freshly joins their
# values to its actual owner/scope. This DATA checker supplies no such authority.
_LIVE_GLOBALS = ((), (), (), ('_ENTRY_OWNER', '_ENTRY_CELL'), ())
_CLASSES = ((0, 'GatewayPackageOwner'), (0, '_Manifest'), (1, 'GatewayRecipeOwner'),
            (2, 'StartupSelectionOwner'), (2, '_Scope'),
            (2, '_ApprovedSelectionSource'), (2, 'GatewayStartupSelection'),
            (2, 'SelectionLoadError'), (0, 'PackageInventoryError'),
            (1, 'GatewayRecipeError'), (3, 'GatewayActivationOwner'),
            (3, '_ActivationScope'), (3, 'ActivationCaptureError'),
            (4, 'ExpectedArtifact'), (4, 'ArtifactObservationError'),
            (4, '_Descriptor'), (4, '_NativeScopeRegistration'),
            (4, '_NativeOpenAllocation'), (4, '_NativeCloseAllocation'),
            (4, '_NativeOpenedDescriptor'), (0, 'RetainedPackageData'),
            (0, '_Scan'), (1, '_Recipe'))
_FUNCTIONS = ((0, 'GatewayPackageOwner', '_retained_binding'),
              (1, 'GatewayRecipeOwner', '_retained_binding'),
              (0, None, '_require'), (1, None, '_require'),
              (1, None, '_same_recipe_binding'),
              (2, 'StartupSelectionOwner', '_retained_binding'),
              (2, None, '_approved_recipe'), (2, None, '_approval_binding'),
              (2, None, '_require'), (2, 'SelectionLoadError', '__init__'),
              (0, 'PackageInventoryError', '__init__'),
              (1, 'GatewayRecipeError', '__init__'),
              (3, 'GatewayActivationOwner', '_retained_scope'),
              (3, None, '_require'), (3, 'ActivationCaptureError', '__init__'),
              (4, None, '_descriptor_closed_in_scope'),
              (4, None, '_native_descriptor_closed'),
              (4, None, '_native_descriptor_opened'),
              (4, None, '_native_file_allocation_original'),
              (4, None, '_expected'), (4, None, '_require'),
              (4, 'ArtifactObservationError', '__init__'))


class RetainedBindingOriginError(RuntimeError):
    pass


def capture():
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
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        names = namespace
        if owner is not None:
            held_kind = None
            for row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = row[0]
                    break
            if type(held_kind) is not type or namespace.get(owner) is not held_kind:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            names = vars(held_kind)
        if not all(type(key) is str for key in names):
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        function = names.get(name)
        if type(function) is not FunctionType or function.__globals__ is not namespace:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        defaults, kw, closure = function.__defaults__, function.__kwdefaults__, function.__closure__
        if ((defaults is not None and type(defaults) is not tuple)
                or (kw is not None and (type(kw) is not dict
                                        or not all(type(key) is str for key in kw)))
                or (closure is not None and (type(closure) is not tuple
                                             or not all(type(cell) is CellType for cell in closure)))):
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        try:
            cells = () if closure is None else tuple(cell.cell_contents for cell in closure)
        except ValueError:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        functions.append((function, function.__code__, namespace, defaults, kw,
                          () if kw is None else tuple(kw.items()), closure, cells))
    packet = (sys, vars(sys), registry, modules, classes, tuple(functions))
    # No delegated helper was called while selecting the candidate references.
    # The independent caller authenticates checker/code/globals/defaults and
    # rejoins the literal packet after callbacks, before any audit consolidation.
    checked = checker(packet)
    if checked is not packet:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    return packet


def current(packet):
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
    for row, name, live_keys in zip(modules, _MODULES, _LIVE_GLOBALS, strict=True):
        if (type(row) is tuple and len(row) == 3) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        module, namespace, pairs = row
        if (type(module) is ModuleType and type(namespace) is dict
              and all(type(key) is str for key in registry)
              and all(type(key) is str for key in namespace)
              and registry.get(name) is module and vars(module) is namespace
              and type(namespace.get('__name__')) is str and namespace['__name__'] == name
              and type(pairs) is tuple
              and all(key in namespace for key in live_keys)
              and len(namespace) == len(pairs) + len(live_keys)) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        seen = set()
        for pair in pairs:
            if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            key, value = pair
            if (key not in live_keys and key not in seen
                  and key in namespace and namespace[key] is value) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            seen.add(key)
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
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        function, code, namespace, defaults, kw, pairs, closure, cells = row
        if (type(namespace) is dict and namespace is modules[index][1]
              and type(function) is FunctionType and function.__globals__ is namespace
              and function.__code__ is code and function.__defaults__ is defaults
              and (defaults is None or type(defaults) is tuple)
              and function.__kwdefaults__ is kw and function.__closure__ is closure
              and type(pairs) is tuple and type(cells) is tuple) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        names = namespace
        if (all(type(key) is str for key in namespace)) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        if owner is not None:
            held_kind = None
            for class_row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = class_row[0]
                    break
            if (type(held_kind) is type
                  and all(type(key) is str for key in namespace)
                  and namespace.get(owner) is held_kind) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            names = vars(held_kind)
        if (all(type(key) is str for key in names) and names.get(name) is function) is not True:
            raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        if kw is None:
            if (pairs == ()) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        else:
            if (type(kw) is dict and all(type(key) is str for key in kw)
                  and len(kw) == len(pairs)) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            seen = set()
            for pair in pairs:
                if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                    raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
                key, value = pair
                if (key not in seen and key in kw and kw[key] is value) is not True:
                    raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
                seen.add(key)
        if closure is None:
            if (cells == ()) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
        else:
            if (type(closure) is tuple and len(closure) == len(cells)) is not True:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            try:
                if (all(type(cell) is CellType and cell.cell_contents is value
                          for cell, value in zip(closure, cells, strict=True))) is not True:
                    raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
            except ValueError:
                raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    if (all(type(key) is str for key in modules[0][1])
          and modules[0][1].get('GatewayRecipeOwner') is classes[2][0]
          and modules[0][1].get('_same_recipe_binding') is functions[4][0]) is not True:
        raise RetainedBindingOriginError('BI1_RETAINED_HELPER_ORIGIN_REFUSED') from None
    # Join the imported aliases to the same defining objects, not merely to an
    # independently coherent snapshot in each importing module. The approval
    # module imported inside _approval_binding remains a separate prerequisite.
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
    return packet

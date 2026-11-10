"""Retained helper inspection DATA; not integrated or an audit/admission grant.

The future early caller must hold the literal capture return independently and
authenticate this module's primitives/globals/functions/code/defaults before dispatch. A coherent copy or a
current export cannot nominate that original. No caller currently skips an audit
using this component. This reads loaded HMP objects only, never profiles/files.
"""
import sys
from types import CellType, FunctionType, ModuleType


_MODULES = ('hmp_plugin.presentation_gateway_package',
            'hmp_plugin.presentation_gateway_recipe')
_CLASSES = ((0, 'GatewayPackageOwner'), (0, '_Manifest'), (1, 'GatewayRecipeOwner'))
_FUNCTIONS = ((0, 'GatewayPackageOwner', '_retained_binding'),
              (1, 'GatewayRecipeOwner', '_retained_binding'),
              (0, None, '_require'), (1, None, '_require'),
              (1, None, '_same_recipe_binding'))


class RetainedBindingOriginError(RuntimeError):
    def __init__(self):
        super().__init__('BI1_RETAINED_HELPER_ORIGIN_REFUSED')


def capture():
    """Collect candidates before checker callbacks; an independent root is required."""
    checker = current
    registry = sys.modules
    if type(registry) is not dict or not all(type(key) is str for key in registry):
        raise RetainedBindingOriginError from None
    modules = []
    for name in _MODULES:
        module = registry.get(name)
        if type(module) is not ModuleType:
            raise RetainedBindingOriginError from None
        namespace = vars(module)
        if (type(namespace) is not dict or not all(type(key) is str for key in namespace)
                or type(namespace.get('__name__')) is not str or namespace['__name__'] != name):
            raise RetainedBindingOriginError from None
        modules.append((module, namespace, tuple(namespace.items())))
    modules = tuple(modules)
    classes = []
    for index, name in _CLASSES:
        namespace = modules[index][1]
        if not all(type(key) is str for key in namespace):
            raise RetainedBindingOriginError from None
        kind = namespace.get(name)
        if type(kind) is not type:
            raise RetainedBindingOriginError from None
        names = vars(kind)
        if not all(type(key) is str for key in names):
            raise RetainedBindingOriginError from None
        classes.append((kind, kind.__bases__, tuple(names.items())))
    classes = tuple(classes)
    functions = []
    for index, owner, name in _FUNCTIONS:
        namespace = modules[index][1]
        if not all(type(key) is str for key in namespace):
            raise RetainedBindingOriginError from None
        names = namespace
        if owner is not None:
            held_kind = None
            for row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = row[0]
                    break
            if type(held_kind) is not type or namespace.get(owner) is not held_kind:
                raise RetainedBindingOriginError from None
            names = vars(held_kind)
        if not all(type(key) is str for key in names):
            raise RetainedBindingOriginError from None
        function = names.get(name)
        if type(function) is not FunctionType or function.__globals__ is not namespace:
            raise RetainedBindingOriginError from None
        defaults, kw, closure = function.__defaults__, function.__kwdefaults__, function.__closure__
        if ((defaults is not None and type(defaults) is not tuple)
                or (kw is not None and (type(kw) is not dict
                                        or not all(type(key) is str for key in kw)))
                or (closure is not None and (type(closure) is not tuple
                                             or not all(type(cell) is CellType for cell in closure)))):
            raise RetainedBindingOriginError from None
        try:
            cells = () if closure is None else tuple(cell.cell_contents for cell in closure)
        except ValueError:
            raise RetainedBindingOriginError from None
        functions.append((function, function.__code__, namespace, defaults, kw,
                          () if kw is None else tuple(kw.items()), closure, cells))
    packet = (sys, vars(sys), registry, modules, classes, tuple(functions))
    # No delegated helper was called while selecting the candidate references.
    # The future caller still authenticates checker/code/globals/defaults and
    # rejoins the literal packet after callbacks, before any audit consolidation.
    checked = checker(packet)
    if checked is not packet:
        raise RetainedBindingOriginError from None
    return packet


def current(packet):
    """Fresh structural/code comparisons only; no original-root or effect proof."""
    if (type(packet) is tuple and len(packet) == 6) is not True:
        raise RetainedBindingOriginError from None
    system, system_names, registry, modules, classes, functions = packet
    if (type(system) is ModuleType and type(system_names) is dict
          and vars(system) is system_names
          and all(type(key) is str for key in system_names)
          and type(registry) is dict and all(type(key) is str for key in registry)
          and system_names.get('modules') is registry
          and type(modules) is tuple and len(modules) == len(_MODULES)
          and type(classes) is tuple and len(classes) == len(_CLASSES)
          and type(functions) is tuple and len(functions) == len(_FUNCTIONS)) is not True:
        raise RetainedBindingOriginError from None
    for row, name in zip(modules, _MODULES, strict=True):
        if (type(row) is tuple and len(row) == 3) is not True:
            raise RetainedBindingOriginError from None
        module, namespace, pairs = row
        if (type(module) is ModuleType and type(namespace) is dict
              and all(type(key) is str for key in registry)
              and all(type(key) is str for key in namespace)
              and registry.get(name) is module and vars(module) is namespace
              and type(namespace.get('__name__')) is str and namespace['__name__'] == name
              and type(pairs) is tuple and len(namespace) == len(pairs)) is not True:
            raise RetainedBindingOriginError from None
        seen = set()
        for pair in pairs:
            if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                raise RetainedBindingOriginError from None
            key, value = pair
            if (key not in seen and key in namespace and namespace[key] is value) is not True:
                raise RetainedBindingOriginError from None
            seen.add(key)
    for row, (index, name) in zip(classes, _CLASSES, strict=True):
        if (type(row) is tuple and len(row) == 3) is not True:
            raise RetainedBindingOriginError from None
        kind, bases, pairs = row
        if (type(kind) is type
              and all(type(key) is str for key in modules[index][1])
              and modules[index][1].get(name) is kind
              and kind.__bases__ is bases and type(pairs) is tuple) is not True:
            raise RetainedBindingOriginError from None
        names = vars(kind)
        if (all(type(key) is str for key in names) and len(names) == len(pairs)) is not True:
            raise RetainedBindingOriginError from None
        seen = set()
        for pair in pairs:
            if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                raise RetainedBindingOriginError from None
            key, value = pair
            if (key not in seen and key in names and names[key] is value) is not True:
                raise RetainedBindingOriginError from None
            seen.add(key)
    for row, (index, owner, name) in zip(functions, _FUNCTIONS, strict=True):
        if (type(row) is tuple and len(row) == 8) is not True:
            raise RetainedBindingOriginError from None
        function, code, namespace, defaults, kw, pairs, closure, cells = row
        if (type(namespace) is dict and namespace is modules[index][1]
              and type(function) is FunctionType and function.__globals__ is namespace
              and function.__code__ is code and function.__defaults__ is defaults
              and (defaults is None or type(defaults) is tuple)
              and function.__kwdefaults__ is kw and function.__closure__ is closure
              and type(pairs) is tuple and type(cells) is tuple) is not True:
            raise RetainedBindingOriginError from None
        names = namespace
        if (all(type(key) is str for key in namespace)) is not True:
            raise RetainedBindingOriginError from None
        if owner is not None:
            held_kind = None
            for class_row, (class_index, class_name) in zip(classes, _CLASSES, strict=True):
                if class_index == index and class_name == owner:
                    held_kind = class_row[0]
                    break
            if (type(held_kind) is type
                  and all(type(key) is str for key in namespace)
                  and namespace.get(owner) is held_kind) is not True:
                raise RetainedBindingOriginError from None
            names = vars(held_kind)
        if (all(type(key) is str for key in names) and names.get(name) is function) is not True:
            raise RetainedBindingOriginError from None
        if kw is None:
            if (pairs == ()) is not True:
                raise RetainedBindingOriginError from None
        else:
            if (type(kw) is dict and all(type(key) is str for key in kw)
                  and len(kw) == len(pairs)) is not True:
                raise RetainedBindingOriginError from None
            seen = set()
            for pair in pairs:
                if (type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str) is not True:
                    raise RetainedBindingOriginError from None
                key, value = pair
                if (key not in seen and key in kw and kw[key] is value) is not True:
                    raise RetainedBindingOriginError from None
                seen.add(key)
        if closure is None:
            if (cells == ()) is not True:
                raise RetainedBindingOriginError from None
        else:
            if (type(closure) is tuple and len(closure) == len(cells)) is not True:
                raise RetainedBindingOriginError from None
            try:
                if (all(type(cell) is CellType and cell.cell_contents is value
                          for cell, value in zip(closure, cells, strict=True))) is not True:
                    raise RetainedBindingOriginError from None
            except ValueError:
                raise RetainedBindingOriginError from None
    if (all(type(key) is str for key in modules[0][1])
          and modules[0][1].get('GatewayRecipeOwner') is classes[2][0]
          and modules[0][1].get('_same_recipe_binding') is functions[4][0]) is not True:
        raise RetainedBindingOriginError from None
    return packet

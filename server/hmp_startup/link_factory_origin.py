"""Early fixed link-policy origin preparation, not native or image admission.

The entry must retain the actual capture return before startup callbacks. This
module is not yet connected to that entry allocation. Matching/copying its DATA
does not establish the independent original-object identity required by LP2.
Imports execute initialization; later complete source/factory gates still apply.
"""
from __future__ import annotations

import sys
from types import FunctionType, ModuleType

_CAPTURE_STARTED = False


def _pin_function(name, function, namespace, *, _type=type, _function=FunctionType,
                  _tuple=tuple, _any=any, _error=RuntimeError):
    if (_type(name) is not str or _type(function) is not _function
            or function.__globals__ is not namespace or function.__closure__ is not None):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    kw = function.__kwdefaults__
    if kw is not None and (_type(kw) is not dict or _any(_type(k) is not str for k in kw)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    return (name, function, function.__code__, namespace, function.__defaults__,
            kw, () if kw is None else _tuple(kw.items()))


def _pin_type(kind, *, _type=type, _vars=vars, _function=FunctionType,
              _staticmethod=staticmethod, _tuple=tuple, _any=any, _error=RuntimeError):
    if _type(kind) is not _type:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    namespace = _vars(kind)
    fields, constructor = namespace.get('_fields'), namespace.get('__new__')
    if _type(constructor) is _staticmethod:
        constructor = constructor.__func__
    if (_type(fields) is not _tuple or _any(_type(n) is not str for n in fields)
            or _type(constructor) is not _function
            or _any(_type(k) is not str for k in constructor.__globals__)
            or constructor.__globals__.get('_tuple_new') is not _tuple.__new__):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    dispatch = _tuple((name, namespace.get(name)) for name in (
        '__getattribute__', '__getattr__', '__getitem__', '__len__', '__iter__',
        '__setattr__', '__delattr__', '__eq__', '__ne__', '__hash__', '__bool__'))
    return (kind, fields, _tuple(namespace.get(n) for n in fields), constructor,
            constructor.__code__, constructor.__globals__, constructor.__defaults__,
            kind.__bases__, dispatch)


def current(origin, *, _type=type, _vars=vars, _tuple=tuple, _len=len,
            _function=FunctionType, _module=ModuleType, _staticmethod=staticmethod,
            _any=any, _zip=zip, _error=RuntimeError):
    """Seal captured references; never nominate a current exported helper.

    Critical inspection primitives are actual function defaults. The independent
    caller must retain/check this function's code/defaults before invoking it.
    They are not caller-selectable native operations or a public wire contract.
    """
    if _type(origin) is not _tuple or _len(origin) != 5:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    environment, modules, own_functions, policy_functions, types = origin
    if (_type(environment) is not _tuple or _len(environment) != 3
            or _type(environment[0]) is not _module or _type(environment[1]) is not dict
            or _vars(environment[0]) is not environment[1]
            or _any(_type(k) is not str for k in environment[1])
            or _type(environment[2]) is not dict
            or _any(_type(k) is not str for k in environment[2])
            or environment[1].get('modules') is not environment[2]
            or _type(modules) is not _tuple or _len(modules) != 4
            or _type(own_functions) is not _tuple or _type(policy_functions) is not _tuple
            or _type(types) is not _tuple or _len(types) != 6):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    names = ('hmp_startup.link_factory_origin',
             'hmp_plugin.presentation_link_path_policy',
             'hmp_plugin.presentation_startup_artifacts', 'hmp_startup.runtime_files')
    for row, name in _zip(modules, names, strict=True):
        if (_type(row) is not _tuple or _len(row) != 3
                or _type(row[0]) is not str or row[0] != name
                or _type(row[1]) is not _module or _type(row[2]) is not dict
                or _any(_type(k) is not str for k in row[2])
                or environment[2].get(name) is not row[1]
                or _vars(row[1]) is not row[2]):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if modules[0][2].get('_CAPTURE_STARTED') is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory')
    policy_names = ('_need', '_parts', '_policy_tail', '_new_policy', '_sites',
                    '_directory', '_leaf', '_cursor_tail', '_start', '_action',
                    '_advance', '_outcome')
    for rows, expected, namespace in ((own_functions, own_names, modules[0][2]),
                                      (policy_functions, policy_names, modules[1][2])):
        if _len(rows) != _len(expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for row, name in _zip(rows, expected, strict=True):
            if (_type(row) is not _tuple or _len(row) != 7
                    or _type(row[0]) is not str or row[0] != name
                    or _type(row[1]) is not _function or row[3] is not namespace
                    or namespace.get(name) is not row[1]
                    or row[1].__code__ is not row[2] or row[1].__globals__ is not namespace
                    or row[1].__defaults__ is not row[4]
                    or row[1].__closure__ is not None or _type(row[6]) is not _tuple):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            kw = row[1].__kwdefaults__
            if kw is not row[5]:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            if kw is None:
                if row[6] != ():
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            elif (_type(kw) is not dict or _any(_type(k) is not str for k in kw)
                  or _len(kw) != _len(row[6])
                  or _any(_type(pair) is not _tuple or _len(pair) != 2
                         or _type(pair[0]) is not str
                         or pair[0] not in kw or kw[pair[0]] is not pair[1]
                         for pair in row[6])):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    exports = ((1, '_LinkPathPolicy'), (1, '_LinkPathCursor'),
               (2, 'ExpectedArtifact'), (3, 'RuntimeFilePlan'),
               (3, 'ExecutableLinkPlan'), (3, 'LinkHop'))
    for pin, (module_index, name) in _zip(types, exports, strict=True):
        if (_type(pin) is not _tuple or _len(pin) != 9 or _type(pin[0]) is not _type
                or modules[module_index][2].get(name) is not pin[0]
                or _type(pin[1]) is not _tuple or _any(_type(n) is not str for n in pin[1])
                or _type(pin[2]) is not _tuple or _len(pin[2]) != _len(pin[1])
                or _type(pin[3]) is not _function or _type(pin[5]) is not dict
                or _any(_type(k) is not str for k in pin[5])
                or _type(pin[8]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        kind, fields, members, constructor, code, globals_, defaults, bases, dispatch = pin
        namespace = _vars(kind)
        actual = namespace.get('__new__')
        if _type(actual) is _staticmethod:
            actual = actual.__func__
        if (namespace.get('_fields') is not fields or actual is not constructor
                or constructor.__code__ is not code or constructor.__globals__ is not globals_
                or constructor.__defaults__ is not defaults or kind.__bases__ is not bases
                or globals_.get('_tuple_new') is not _tuple.__new__
                or _any(namespace.get(n) is not member
                       for n, member in _zip(fields, members, strict=True))
                or _any(_type(row) is not _tuple or _len(row) != 2 or _type(row[0]) is not str
                       or namespace.get(row[0]) is not row[1] for row in dispatch)):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    return origin


def capture(*, _type=type, _vars=vars, _tuple=tuple, _function=FunctionType,
            _module=ModuleType, _sys=sys, _len=len, _any=any, _error=RuntimeError):
    """Capture once at the future trusted entry boundary, before callbacks."""
    global _CAPTURE_STARTED
    if _CAPTURE_STARTED is not False:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # One attempt before initialization imports. Failure or lost return cannot
    # nominate later current exports or recover a receipt from a global slot.
    _CAPTURE_STARTED = True
    if _type(_sys) is not _module:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    sys_namespace = _vars(_sys)
    if _any(_type(k) is not str for k in sys_namespace):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    registry = sys_namespace.get('modules')
    if _type(registry) is not dict or _any(_type(k) is not str for k in registry):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    own = registry.get('hmp_startup.link_factory_origin')
    if _type(own) is not _module:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    namespace = _vars(own)
    if _any(_type(k) is not str for k in namespace):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    pin_function, pin_type, check = _pin_function, _pin_type, current
    own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory')
    own_functions = _tuple(pin_function(name, namespace.get(name), namespace) for name in own_names)
    from hmp_plugin import presentation_link_path_policy as policy
    from hmp_plugin import presentation_startup_artifacts as artifacts
    from hmp_startup import runtime_files

    if (_type(_sys) is not _module or _type(own) is not _module
            or _vars(own) is not namespace
            or _any(_type(k) is not str for k in namespace)
            or _any(_type(k) is not str for k in _vars(_sys))
            or _vars(_sys).get('modules') is not registry):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # Imports can execute initialization. Rejoin held local helpers/defaults
    # without invoking any current replacement before using the captured check.
    for name, function, code, globals_, defaults, kw, pairs in own_functions:
        if (namespace.get(name) is not function or function.__code__ is not code
                or function.__globals__ is not globals_ or function.__defaults__ is not defaults
                or function.__kwdefaults__ is not kw
                or (kw is not None and (_type(kw) is not dict
                    or _any(_type(k) is not str for k in kw) or _len(kw) != _len(pairs)
                    or _any(k not in kw or kw[k] is not value for k, value in pairs)))):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    modules = _tuple((_vars(module).get('__name__'), module, _vars(module))
                     for module in (own, policy, artifacts, runtime_files)
                     if _type(module) is _module)
    if (_len(modules) != 4
            or _any(_any(_type(k) is not str for k in row[2]) for row in modules)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    policy_namespace = modules[1][2]
    policy_names = ('_need', '_parts', '_policy_tail', '_new_policy', '_sites',
                    '_directory', '_leaf', '_cursor_tail', '_start', '_action',
                    '_advance', '_outcome')
    functions = _tuple(pin_function(name, policy_namespace.get(name), policy_namespace)
                       for name in policy_names)
    kinds = _tuple(pin_type(modules[index][2].get(name)) for index, name in (
        (1, '_LinkPathPolicy'), (1, '_LinkPathCursor'), (2, 'ExpectedArtifact'),
        (3, 'RuntimeFilePlan'), (3, 'ExecutableLinkPlan'), (3, 'LinkHop')))
    result = ((_sys, _vars(_sys), registry), modules, own_functions, functions, kinds)
    return check(result)


def factory(origin, *, _type=type, _tuple=tuple, _len=len, _any=any,
            _function=FunctionType, _error=RuntimeError):
    """Return a held factory after its captured validator rejoins.

    Callers must separately prove this exact origin is the one retained by their
    original entry/lineage. This DATA helper cannot establish that ownership.
    """
    if (_type(origin) is not _tuple or _len(origin) != 5
            or _type(origin[2]) is not _tuple or _len(origin[2]) != 5):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    row = origin[2][3]
    if (_type(row) is not _tuple or _len(row) != 7
            or _type(row[0]) is not str or row[0] != 'current'
            or _type(row[1]) is not _function or _type(row[3]) is not dict
            or _any(_type(k) is not str for k in row[3])
            or row[3].get('current') is not row[1]
            or row[1].__globals__ is not row[3] or row[1].__code__ is not row[2]
            or row[1].__defaults__ is not row[4] or row[1].__kwdefaults__ is not row[5]
            or _type(row[5]) is not dict or _type(row[6]) is not _tuple
            or _any(_type(k) is not str for k in row[5])
            or _len(row[5]) != _len(row[6])
            or _any(_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not str
                    or pair[0] not in row[5] or row[5][pair[0]] is not pair[1]
                    for pair in row[6])):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    row[1](origin)  # actual held validator, never a current export selection
    return origin[3][3][1]

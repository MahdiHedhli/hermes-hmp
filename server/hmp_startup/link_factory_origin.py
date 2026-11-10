"""Early fixed link-policy origin preparation, not native or image admission.

The actual entry/Scope binding retains this capture before startup callbacks.
Matching/copying its DATA does not establish independent original-object identity
or permission for a native effect. Encoding preparation does not enable images.
Imports execute initialization; later complete source/factory gates still apply.
"""
from __future__ import annotations

import sys
from types import BuiltinFunctionType, FunctionType, MethodDescriptorType, ModuleType, CellType
from typing import NamedTuple

_CAPTURE_STARTED = False


class _FilesystemEncodingOrigin(NamedTuple):
    module: ModuleType
    namespace: dict
    get_encoding: object
    get_errors: object
    encode: object
    encoding: str
    errors: str

    def __repr__(self):
        return '<OriginalFilesystemEncoding DATA not-admission redacted>'


class _EncodedBasename(NamedTuple):
    origin: tuple
    name: str
    value: bytes
    encoding_origin: _FilesystemEncodingOrigin

    def __repr__(self):
        return '<ActualEncodedBasename DATA not-native-arguments redacted>'


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
            _any=any, _zip=zip, _builtin=BuiltinFunctionType,
            _descriptor=MethodDescriptorType, _str=str, _error=RuntimeError):
    """Seal captured references; never nominate a current exported helper.

    Critical inspection primitives are actual function defaults. The independent
    caller must retain/check this function's code/defaults before invoking it.
    They are not caller-selectable native operations or a public wire contract.
    """
    if _type(origin) is not _tuple or _len(origin) != 5:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    environment, modules, own_functions, policy_functions, types = origin
    if (_type(environment) is not _tuple or _len(environment) != 6
            or _type(environment[0]) is not _module or _type(environment[1]) is not dict
            or _vars(environment[0]) is not environment[1]
            or _any(_type(k) is not str for k in environment[1])
            or _type(environment[2]) is not dict
            or _any(_type(k) is not str for k in environment[2])
            or environment[1].get('modules') is not environment[2]
            or _type(modules) is not _tuple or _len(modules) != 4
            or _type(own_functions) is not _tuple or _type(policy_functions) is not _tuple
            or _type(types) is not _tuple or _len(types) != 11):
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
                or _vars(row[1]) is not row[2]
                or _type(row[2].get('__name__')) is not str
                or row[2]['__name__'] != name):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if modules[0][2].get('_CAPTURE_STARTED') is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory', 'blueprint_factory', 'encode_basename')
    policy_names = ('_need', '_parts', '_policy_tail', '_new_policy', '_sites',
                    '_directory', '_leaf', '_cursor_tail', '_start', '_action',
                    '_advance', '_outcome', '_scope_blueprint_guard',
                    '_scope_blueprint_cohort', '_scope_blueprint_tail', '_new_scope_blueprint')
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
               (3, 'ExecutableLinkPlan'), (3, 'LinkHop'),
               (1, '_LinkScopeBlueprint'), (2, '_RuntimeSource'), (2, '_Scope'),
               (0, '_FilesystemEncodingOrigin'), (0, '_EncodedBasename'))
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
    encoding_origin = environment[3]
    if (_type(encoding_origin) is not types[9][0]
            or _tuple.__len__(encoding_origin) != 7):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    encoded_module, encoded_namespace, get_encoding, get_errors, encode, encoding, errors = encoding_origin
    if (encoded_module is not environment[0] or encoded_namespace is not environment[1]
            or _type(get_encoding) is not _builtin or _type(get_errors) is not _builtin
            or get_encoding.__self__ is not encoded_module or get_errors.__self__ is not encoded_module
            or get_encoding.__name__ != 'getfilesystemencoding'
            or get_errors.__name__ != 'getfilesystemencodeerrors'
            or encoded_namespace.get('getfilesystemencoding') is not get_encoding
            or encoded_namespace.get('getfilesystemencodeerrors') is not get_errors
            or _type(encode) is not _descriptor or encode.__objclass__ is not _str
            or encode.__name__ != 'encode' or _vars(_str).get('encode') is not encode
            or _type(encoding) is not _str or _type(errors) is not _str
            or not 1 <= _len(encoding) <= 64 or not 1 <= _len(errors) <= 64
            or _any(not (c.isascii() and (c.isalnum() or c in '._-')) for c in encoding + errors)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None

    engine = environment[4]
    if (_type(engine) is not _tuple or _len(engine) != 6
            or _type(engine[0]) is not _module or _type(engine[2]) is not _tuple
            or _type(engine[4]) is not _tuple or _len(engine[4]) != 4
            or engine[4][0] is not environment[0] or engine[4][1] is not environment[1]
            or engine[4][2] is not environment[2]
            or environment[2].get('hmp_plugin.presentation_native_link') is not engine[0]
            or engine[5] is not environment[5]):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    selected = _tuple(row for row in engine[2]
                      if _type(row) is _tuple and _len(row) == 7
                      and _type(row[0]) is _str and row[0] == '_engine_origin_tail')
    if _len(selected) != 1:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    held = selected[0]
    namespace = _vars(engine[0])
    if (_any(_type(k) is not _str for k in namespace)
            or held[3] is not namespace or _type(held[1]) is not _function
            or namespace.get(held[0]) is not held[1] or held[1].__globals__ is not namespace
            or held[1].__code__ is not held[2] or held[1].__defaults__ is not held[4]
            or held[1].__kwdefaults__ is not held[5]
            or _type(held[5]) is not dict or _type(held[6]) is not _tuple
            or _any(_type(k) is not _str for k in held[5])
            or _len(held[5]) != _len(held[6])
            or _any(_type(pair) is not _tuple or _len(pair) != 2
                    or _type(pair[0]) is not _str or pair[0] not in held[5]
                    or held[5][pair[0]] is not pair[1] for pair in held[6])):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if held[1](engine) is not engine:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    return origin


def capture(*,
            _type=type,
            _vars=vars,
            _tuple=tuple,
            _function=FunctionType,
            _module=ModuleType,
            _sys=sys,
            _len=len,
            _any=any,
            _zip=zip,
            _staticmethod=staticmethod,
            _builtin=BuiltinFunctionType,
            _descriptor=MethodDescriptorType,
            _str=str,
            _dict=dict,
            _cell=CellType,
            _enumerate=enumerate,
            _error=RuntimeError):
    """Capture once at the future trusted entry boundary, before callbacks."""
    global _CAPTURE_STARTED
    if _CAPTURE_STARTED is not False:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    _CAPTURE_STARTED = True
    if _type(_sys) is not _module:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    sys_namespace = _vars(_sys)
    if _any((_type(k) is not _str for k in sys_namespace)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    registry = sys_namespace.get('modules')
    if _type(registry) is not _dict or _any((_type(k) is not _str for k in registry)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    own = registry.get('hmp_startup.link_factory_origin')
    if _type(own) is not _module:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    namespace = _vars(own)
    if _any((_type(k) is not _str for k in namespace)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    pin_function, pin_type, check = (_pin_function, _pin_type, current)
    own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory', 'blueprint_factory', 'encode_basename')
    own_functions = _tuple((pin_function(name, namespace.get(name), namespace) for name in own_names))
    from hmp_plugin import presentation_link_path_policy as policy
    from hmp_plugin import presentation_startup_artifacts as artifacts
    from hmp_startup import runtime_files
    from hmp_plugin import presentation_native_link as engine
    if (_type(_sys) is not _module
            or _type(own) is not _module
            or _vars(own) is not namespace
            or _any((_type(k) is not _str for k in namespace))
            or _any((_type(k) is not _str for k in _vars(_sys)))
            or _vars(_sys).get('modules') is not registry):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for name, function, code, globals_, defaults, kw, pairs in own_functions:
        if (namespace.get(name) is not function
                or function.__code__ is not code
                or function.__globals__ is not globals_
                or function.__defaults__ is not defaults
                or function.__kwdefaults__ is not kw
                or (kw is not None and (_type(kw) is not _dict or _any((_type(k) is not _str for k in kw)) or _len(kw) != _len(pairs) or _any((k not in kw or kw[k] is not value for k, value in pairs))))):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    module_names = ('hmp_startup.link_factory_origin',
                    'hmp_plugin.presentation_link_path_policy',
                    'hmp_plugin.presentation_startup_artifacts', 'hmp_startup.runtime_files')
    modules = _tuple((name, module, _vars(module)) for name, module in
                     _zip(module_names, (own, policy, artifacts, runtime_files), strict=True)
                     if _type(module) is _module)
    if _len(modules) != 4 or _any((_any((_type(k) is not _str for k in row[2])) for row in modules)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if _any(_type(row[2].get('__name__')) is not _str
            or row[2]['__name__'] != row[0] or registry.get(row[0]) is not row[1]
            for row in modules):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    engine_capture = engine._capture_engine
    engine_capture_code = engine_capture.__code__
    expected_capture_defaults = dict(_type=_type, _tuple=_tuple, _dict=_dict, _str=_str,
                                     _len=_len, _vars=_vars, _any=_any, _zip=_zip,
                                     _module=_module, _function=_function, _cell=_cell, _builtin=_builtin, _error=_error)
    capture_kw = engine_capture.__kwdefaults__
    if (type(capture_kw) is not dict or any(type(k) is not str for k in capture_kw)
            or len(capture_kw) != len(expected_capture_defaults)
            or any(k not in capture_kw or capture_kw[k] is not value
                   for k, value in expected_capture_defaults.items())):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    engine_origin = engine_capture()
    if (_type(engine_origin) is not _tuple or _len(engine_origin) != 6
            or _type(engine_origin[4]) is not _tuple or _len(engine_origin[4]) != 4
            or engine_origin[4][0] is not _sys or engine_origin[4][1] is not sys_namespace
            or engine_origin[4][2] is not registry):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (engine._capture_engine is not engine_capture
            or engine_capture.__code__ is not engine_capture_code):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    engine_layout = engine_origin[5]
    engine_check = next(row for row in engine_origin[2] if row[0] == '_engine_origin_tail')
    policy_namespace = modules[1][2]
    policy_names = ('_need', '_parts', '_policy_tail', '_new_policy', '_sites', '_directory', '_leaf', '_cursor_tail', '_start', '_action', '_advance', '_outcome', '_scope_blueprint_guard', '_scope_blueprint_cohort', '_scope_blueprint_tail', '_new_scope_blueprint')
    functions = _tuple((pin_function(name, policy_namespace.get(name), policy_namespace) for name in policy_names))
    kinds = _tuple((pin_type(modules[index][2].get(name)) for index, name in ((1, '_LinkPathPolicy'), (1, '_LinkPathCursor'), (2, 'ExpectedArtifact'), (3, 'RuntimeFilePlan'), (3, 'ExecutableLinkPlan'), (3, 'LinkHop'), (1, '_LinkScopeBlueprint'), (2, '_RuntimeSource'), (2, '_Scope'), (0, '_FilesystemEncodingOrigin'), (0, '_EncodedBasename'))))
    encoding_kind = kinds[9][0]
    get_encoding = sys_namespace.get('getfilesystemencoding')
    get_errors = sys_namespace.get('getfilesystemencodeerrors')
    encode = _vars(_str).get('encode')
    if (_type(get_encoding) is not _builtin
            or _type(get_errors) is not _builtin
            or get_encoding.__self__ is not _sys
            or get_errors.__self__ is not _sys
            or get_encoding.__name__ != 'getfilesystemencoding'
            or get_errors.__name__ != 'getfilesystemencodeerrors'
            or _type(encode) is not _descriptor
            or encode.__objclass__ is not _str):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None

    def rejoin():
        if (_type(_sys) is not _module or _any(_type(k) is not _str for k in registry)
                or _any(_type(row[1]) is not _module or _vars(row[1]) is not row[2]
                        or _any(_type(k) is not _str for k in row[2])
                    or _type(row[2].get('__name__')) is not _str
                    or row[2]['__name__'] != row[0]
                    or registry.get(row[0]) is not row[1] for row in modules)):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if (_any((_type(k) is not _str for k in namespace))
                or _any((_any((_type(k) is not _str for k in row[2])) for row in modules))
                or _vars(_sys) is not sys_namespace
                or _any((_type(k) is not _str for k in sys_namespace))
                or sys_namespace.get('modules') is not registry
                or sys_namespace.get('getfilesystemencoding') is not get_encoding
                or sys_namespace.get('getfilesystemencodeerrors') is not get_errors
                or _vars(_str).get('encode') is not encode):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for name, function, code, globals_, defaults, kw, pairs in own_functions:
            if (namespace.get(name) is not function
                    or function.__code__ is not code
                    or function.__globals__ is not globals_
                    or function.__defaults__ is not defaults
                    or function.__kwdefaults__ is not kw
                    or (kw is not None and (_any((_type(k) is not _str for k in kw)) or _len(kw) != _len(pairs) or _any((k not in kw or kw[k] is not value for k, value in pairs))))):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        exports = ((1, '_LinkPathPolicy'), (1, '_LinkPathCursor'), (2, 'ExpectedArtifact'), (3, 'RuntimeFilePlan'), (3, 'ExecutableLinkPlan'), (3, 'LinkHop'), (1, '_LinkScopeBlueprint'), (2, '_RuntimeSource'), (2, '_Scope'), (0, '_FilesystemEncodingOrigin'), (0, '_EncodedBasename'))
        for pin, (module_index, name) in _zip(kinds, exports, strict=True):
            kind, fields, members, constructor, code, globals_, defaults, bases, dispatch = pin
            if _type(kind) is not _type:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            names = _vars(kind)
            actual = names.get('__new__')
            if _type(actual) is _staticmethod:
                actual = actual.__func__
            if (modules[module_index][2].get(name) is not kind
                    or names.get('_fields') is not fields
                    or actual is not constructor
                    or constructor.__code__ is not code
                    or constructor.__globals__ is not globals_
                    or constructor.__defaults__ is not defaults
                    or kind.__bases__ is not bases
                    or _any((_type(k) is not _str for k in globals_))
                    or globals_.get('_tuple_new') is not _tuple.__new__
                    or _any((names.get(n) is not member for n, member in _zip(fields, members, strict=True)))
                    or _any((names.get(n) is not member for n, member in dispatch))):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if (engine_capture.__code__ is not engine_capture_code
                or _type(engine_origin) is not _tuple or _len(engine_origin) != 6
                or engine_origin[0] is not engine or engine_origin[5] is not engine_layout
                or engine_check[1].__code__ is not engine_check[2]
                or engine_check[1].__defaults__ is not engine_check[4]
                or engine_check[1].__kwdefaults__ is not engine_check[5]):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if engine_check[1](engine_origin) is not engine_origin:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    rejoin()
    encoding = get_encoding()
    rejoin()
    errors = get_errors()
    rejoin()
    if (_type(encoding) is not _str
            or _type(errors) is not _str
            or not 1 <= _len(encoding) <= 64
            or not 1 <= _len(errors) <= 64
            or _any((not (c.isascii() and (c.isalnum() or c in '._-')) for c in encoding + errors))):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    values = (_sys, sys_namespace, get_encoding, get_errors, encode, encoding, errors)
    # Last primitive original-function/type seal after the helper return.
    if (_type(_sys) is not _module or _any(_type(k) is not _str for k in registry)
            or _any(_type(row[1]) is not _module or _vars(row[1]) is not row[2]
                    or _any(_type(k) is not _str for k in row[2])
                    or _type(row[2].get('__name__')) is not _str
                    or row[2]['__name__'] != row[0]
                    or registry.get(row[0]) is not row[1] for row in modules)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if _any((_type(k) is not _str for k in namespace)) or _any((_any((_type(k) is not _str for k in row[2])) for row in modules)) or _vars(_sys) is not sys_namespace or _any((_type(k) is not _str for k in sys_namespace)) or (sys_namespace.get('modules') is not registry) or (sys_namespace.get('getfilesystemencoding') is not get_encoding) or (sys_namespace.get('getfilesystemencodeerrors') is not get_errors) or (_vars(_str).get('encode') is not encode):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for name, function, code, globals_, defaults, kw, pairs in own_functions:
        if namespace.get(name) is not function or function.__code__ is not code or function.__globals__ is not globals_ or (function.__defaults__ is not defaults) or (function.__kwdefaults__ is not kw) or (kw is not None and (_any((_type(k) is not _str for k in kw)) or _len(kw) != _len(pairs) or _any((k not in kw or kw[k] is not value for k, value in pairs)))):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    exports = ((1, '_LinkPathPolicy'), (1, '_LinkPathCursor'), (2, 'ExpectedArtifact'), (3, 'RuntimeFilePlan'), (3, 'ExecutableLinkPlan'), (3, 'LinkHop'), (1, '_LinkScopeBlueprint'), (2, '_RuntimeSource'), (2, '_Scope'), (0, '_FilesystemEncodingOrigin'), (0, '_EncodedBasename'))
    for pin, (module_index, name) in _zip(kinds, exports, strict=True):
        kind, fields, members, constructor, code, globals_, defaults, bases, dispatch = pin
        if _type(kind) is not _type:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        names = _vars(kind)
        actual = names.get('__new__')
        if _type(actual) is _staticmethod:
            actual = actual.__func__
        if modules[module_index][2].get(name) is not kind or names.get('_fields') is not fields or actual is not constructor or (constructor.__code__ is not code) or (constructor.__globals__ is not globals_) or (constructor.__defaults__ is not defaults) or (kind.__bases__ is not bases) or _any((_type(k) is not _str for k in globals_)) or (globals_.get('_tuple_new') is not _tuple.__new__) or _any((names.get(n) is not member for n, member in _zip(fields, members, strict=True))) or _any((names.get(n) is not member for n, member in dispatch)):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    constructor = _tuple.__getitem__(_tuple.__getitem__(kinds, 9), 3)
    encoding_origin = constructor(encoding_kind, *values)
    rejoin()
    if (_type(encoding_origin) is not encoding_kind
            or _tuple.__len__(encoding_origin) != _len(values)
            or _any((_tuple.__getitem__(encoding_origin, i) is not value for i, value in _enumerate(values)))):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    result = ((_sys, sys_namespace, registry, encoding_origin, engine_origin, engine_layout), modules, own_functions, functions, kinds)
    if (_type(_sys) is not _module or _any(_type(k) is not _str for k in registry)
            or _any(_type(row[1]) is not _module or _vars(row[1]) is not row[2]
                    or _any(_type(k) is not _str for k in row[2])
                    or _type(row[2].get('__name__')) is not _str
                    or row[2]['__name__'] != row[0]
                    or registry.get(row[0]) is not row[1] for row in modules)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if _any((_type(k) is not _str for k in namespace)) or _any((_any((_type(k) is not _str for k in row[2])) for row in modules)) or _vars(_sys) is not sys_namespace or _any((_type(k) is not _str for k in sys_namespace)) or (sys_namespace.get('modules') is not registry) or (sys_namespace.get('getfilesystemencoding') is not get_encoding) or (sys_namespace.get('getfilesystemencodeerrors') is not get_errors) or (_vars(_str).get('encode') is not encode):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for name, function, code, globals_, defaults, kw, pairs in own_functions:
        if namespace.get(name) is not function or function.__code__ is not code or function.__globals__ is not globals_ or (function.__defaults__ is not defaults) or (function.__kwdefaults__ is not kw) or (kw is not None and (_any((_type(k) is not _str for k in kw)) or _len(kw) != _len(pairs) or _any((k not in kw or kw[k] is not value for k, value in pairs)))):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    exports = ((1, '_LinkPathPolicy'), (1, '_LinkPathCursor'), (2, 'ExpectedArtifact'), (3, 'RuntimeFilePlan'), (3, 'ExecutableLinkPlan'), (3, 'LinkHop'), (1, '_LinkScopeBlueprint'), (2, '_RuntimeSource'), (2, '_Scope'), (0, '_FilesystemEncodingOrigin'), (0, '_EncodedBasename'))
    for pin, (module_index, name) in _zip(kinds, exports, strict=True):
        kind, fields, members, constructor, code, globals_, defaults, bases, dispatch = pin
        if _type(kind) is not _type:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        names = _vars(kind)
        actual = names.get('__new__')
        if _type(actual) is _staticmethod:
            actual = actual.__func__
        if modules[module_index][2].get(name) is not kind or names.get('_fields') is not fields or actual is not constructor or (constructor.__code__ is not code) or (constructor.__globals__ is not globals_) or (constructor.__defaults__ is not defaults) or (kind.__bases__ is not bases) or _any((_type(k) is not _str for k in globals_)) or (globals_.get('_tuple_new') is not _tuple.__new__) or _any((names.get(n) is not member for n, member in _zip(fields, members, strict=True))) or _any((names.get(n) is not member for n, member in dispatch)):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    return check(result)


def factory(origin, *, _type=type, _tuple=tuple, _len=len, _any=any,
            _function=FunctionType, _error=RuntimeError):
    """Return a held factory after its captured validator rejoins.

    Callers must separately prove this exact origin is the one retained by their
    original entry/lineage. This DATA helper cannot establish that ownership.
    """
    if (_type(origin) is not _tuple or _len(origin) != 5
            or _type(origin[2]) is not _tuple or _len(origin[2]) != 7):
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


def blueprint_factory(origin, *, _type=type, _tuple=tuple, _len=len, _error=RuntimeError):
    """One fixed held blueprint entry point; no caller-selected helper name."""
    # Own fixed row4 is factory, row3 is current; both are early captured. The
    # caller must seal this helper itself before invoking it, as for factory().
    if _type(origin) is not _tuple or _len(origin) != 5:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    rows = origin[2]
    if _type(rows) is not _tuple or _len(rows) != 7:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    row = rows[4]
    if (_type(row) is not _tuple or _len(row) != 7 or _type(row[0]) is not str
            or row[0] != 'factory' or _type(row[1]) is not FunctionType
            or _type(row[3]) is not dict or any(_type(k) is not str for k in row[3])
            or row[3].get('factory') is not row[1]
            or row[1].__code__ is not row[2] or row[1].__globals__ is not row[3]
            or row[1].__defaults__ is not row[4] or row[1].__kwdefaults__ is not row[5]
            or _type(row[5]) is not dict or _type(row[6]) is not _tuple
            or any(_type(k) is not str for k in row[5])
            or _len(row[5]) != _len(row[6])
            or any(_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not str
                   or pair[0] not in row[5] or row[5][pair[0]] is not pair[1]
                   for pair in row[6])):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    row[1](origin)
    return origin[3][15][1]


def encode_basename(origin, name, *,
            _type=type,
            _tuple=tuple,
            _len=len,
            _function=FunctionType,
            _any=any,
            _str=str,
            _bytes=bytes,
            _dict=dict,
            _ord=ord,
            _enumerate=enumerate,
            _vars=vars,
            _staticmethod=staticmethod,
            _zip=zip,
            _error=RuntimeError):
    """Encode one exact basename with original interpreter settings and C method.

    No os.fsencode lookup or UTF-8 substitution. Caller must hold the actual
    return across its resource constructor and bind it to its original policy
    row. This helper alone grants no filesystem operation, path or byte credit.
    Codec machinery may execute initialization; complete factory/source and
    native-effect integration remain separate requirements.
    """
    if (_type(origin) is not _tuple
            or _len(origin) != 5
            or _type(origin[2]) is not _tuple
            or _len(origin[2]) != 7):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    row = origin[2][3]

    def rejoin():
        if (_type(row) is not _tuple
                or _len(row) != 7
                or _type(row[0]) is not _str
                or row[0] != 'current'
                or _type(row[1]) is not _function
                or _type(row[3]) is not _dict
                or _any((_type(k) is not _str for k in row[3]))
                or row[3].get('current') is not row[1]
                or row[1].__code__ is not row[2]
                or row[1].__globals__ is not row[3]
                or row[1].__defaults__ is not row[4]
                or row[1].__kwdefaults__ is not row[5]
                or _type(row[5]) is not _dict
                or _type(row[6]) is not _tuple
                or _any((_type(k) is not _str for k in row[5]))
                or _len(row[5]) != _len(row[6])
                or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in row[5]) or (row[5][pair[0]] is not pair[1]) for pair in row[6]))):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if row[1](origin) is not origin:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    rejoin()
    if (_type(name) is not _str
            or not 1 <= _len(name) <= 4096
            or name in ('.', '..')
            or '/' in name
            or _any((_ord(c) < 32 or _ord(c) == 127 or 55296 <= _ord(c) <= 57343 for c in name))):
        raise _error('BI1_LINK_BASENAME_REFUSED') from None
    encoding_origin = _tuple.__getitem__(_tuple.__getitem__(origin, 0), 3)
    get_encoding = _tuple.__getitem__(encoding_origin, 2)
    get_errors = _tuple.__getitem__(encoding_origin, 3)
    encode = _tuple.__getitem__(encoding_origin, 4)
    encoding = _tuple.__getitem__(encoding_origin, 5)
    errors = _tuple.__getitem__(encoding_origin, 6)
    actual_encoding = get_encoding()
    rejoin()
    actual_errors = get_errors()
    rejoin()
    if (_type(actual_encoding) is not _str
            or _type(actual_errors) is not _str
            or actual_encoding != encoding
            or actual_errors != errors):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    data = encode(name, encoding, errors)
    rejoin()
    if (_type(data) is not _bytes
            or not 1 <= _len(data) <= 4096
            or b'/' in data
            or b'\x00' in data
            or data in (b'.', b'..')):
        raise _error('BI1_LINK_BASENAME_REFUSED') from None
    actual_encoding = get_encoding()
    rejoin()
    actual_errors = get_errors()
    rejoin()
    if (_type(actual_encoding) is not _str
            or _type(actual_errors) is not _str
            or actual_encoding != encoding
            or actual_errors != errors):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    pin = origin[4][10]
    kind, fields, members, constructor, code, constructor_globals, defaults, bases, dispatch = pin
    if _type(kind) is not _type:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    names = _vars(kind)
    actual = names.get('__new__')
    if _type(actual) is _staticmethod:actual = actual.__func__
    if (_any(_type(k) is not _str for k in origin[1][0][2])
            or origin[1][0][2].get('_EncodedBasename') is not kind
            or names.get('_fields') is not fields or actual is not constructor
            or constructor.__code__ is not code or constructor.__globals__ is not constructor_globals
            or constructor.__defaults__ is not defaults or kind.__bases__ is not bases
            or _any(_type(k) is not _str for k in constructor_globals)
            or constructor_globals.get('_tuple_new') is not _tuple.__new__
            or _any(names.get(n) is not member for n, member in _zip(fields, members, strict=True))
            or _any(names.get(n) is not member for n, member in dispatch)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    values = (origin, name, data, encoding_origin)
    result = constructor(kind, *values)
    rejoin()
    pin = origin[4][10]
    kind, fields, members, constructor, code, constructor_globals, defaults, bases, dispatch = pin
    if _type(kind) is not _type:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    names = _vars(kind)
    actual = names.get('__new__')
    if _type(actual) is _staticmethod:actual = actual.__func__
    if (_any(_type(k) is not _str for k in origin[1][0][2])
            or origin[1][0][2].get('_EncodedBasename') is not kind
            or names.get('_fields') is not fields or actual is not constructor
            or constructor.__code__ is not code or constructor.__globals__ is not constructor_globals
            or constructor.__defaults__ is not defaults or kind.__bases__ is not bases
            or _any(_type(k) is not _str for k in constructor_globals)
            or constructor_globals.get('_tuple_new') is not _tuple.__new__
            or _any(names.get(n) is not member for n, member in _zip(fields, members, strict=True))
            or _any(names.get(n) is not member for n, member in dispatch)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_type(result) is not kind
            or _tuple.__len__(result) != _len(values)
            or _any((_tuple.__getitem__(result, i) is not value for i, value in _enumerate(values)))):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    return result

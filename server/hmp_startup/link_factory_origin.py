"""Early fixed link-policy origin preparation, not native or image admission.

The actual entry/Scope binding retains this capture before startup callbacks.
Matching/copying its DATA does not establish independent original-object identity
or permission for a native effect. Encoding preparation does not enable images.
Imports execute initialization; later complete source/factory gates still apply.
"""
from __future__ import annotations

import sys
from types import BuiltinFunctionType, FunctionType, MethodDescriptorType, ModuleType, CellType, GetSetDescriptorType
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
            _descriptor=MethodDescriptorType, _str=str, _dict=dict,
            _all=all, _set=set, _value_error=ValueError, _cell=CellType,
            _bool=bool, _int=int, _list=list, _bytes=bytes, _bytearray=bytearray,
            _sum=sum, _ord=ord, _super=super, _error=RuntimeError):
    """Seal captured references; never nominate a current exported helper.

    Critical inspection primitives are actual function defaults. The independent
    caller must retain/check this function's code/defaults before invoking it.
    They are not caller-selectable native operations or a public wire contract.
    """
    if _type(origin) is not _tuple or _len(origin) != 5:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    environment, modules, own_functions, policy_functions, types = origin
    if (_type(environment) is not _tuple or _len(environment) != 8
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
    own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory', 'blueprint_factory', 'encode_basename', 'current_started')
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

    helper_capsule = environment[6]
    helper_system, helper_registry = environment[0], environment[2]
    helper_expected_builtins = (_type, _vars, _tuple, _len, _dict, _str, _any, _zip,
                                _all, _set, _error, _value_error,
                                _bool, _int, _list, _bytes, _bytearray, _sum, _ord, _super)
    # Authenticate the component before dispatch; the actual parent holds this DATA.
    if (_type(helper_capsule) is not _tuple or _len(helper_capsule) != 7
            or _type(helper_capsule[0]) is not _module
            or _type(helper_capsule[1]) is not _dict
            or _type(helper_capsule[2]) is not _tuple
            or _type(helper_capsule[3]) is not _tuple or _len(helper_capsule[3]) != 2
            or _type(helper_capsule[4]) is not _tuple or _len(helper_capsule[4]) != 3
            or _type(helper_capsule[5]) is not _tuple or _len(helper_capsule[5]) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_module, helper_namespace, helper_pairs = helper_capsule[:3]
    helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs = helper_capsule[5]
    if (_any(_type(k) is not _str for k in helper_registry)
            or helper_registry.get('hmp_startup.retained_binding_origin') is not helper_module
            or _vars(helper_module) is not helper_namespace
            or _any(_type(k) is not _str for k in helper_namespace)
            or _len(helper_namespace) != _len(helper_pairs)
            or helper_namespace.get('sys') is not helper_system
            or _type(helper_builtin_module) is not _module
            or _type(helper_builtin_namespace) is not _dict
            or helper_registry.get('builtins') is not helper_builtin_module
            or _vars(helper_builtin_module) is not helper_builtin_namespace
            or _any(_type(k) is not _str for k in helper_builtin_namespace)
            or helper_namespace.get('__builtins__') is not helper_builtin_namespace
            or _type(helper_primitive_pairs) is not _tuple
            or _len(helper_primitive_pairs) != 20):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_namespace
                or helper_namespace[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    for helper_pair, helper_name, helper_expected in _zip(
            helper_primitive_pairs,
            ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
             'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True):
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str or helper_pair[0] != helper_name
                or helper_pair[1] is not helper_expected
                or helper_builtin_namespace.get(helper_name) is not helper_expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_row, helper_name in _zip(helper_capsule[3], ('capture', 'current'), strict=True):
        if (_type(helper_row) is not _tuple or _len(helper_row) != 7
                or _type(helper_row[0]) is not _str or helper_row[0] != helper_name
                or _type(helper_row[1]) is not _function or helper_row[3] is not helper_namespace
                or helper_namespace.get(helper_name) is not helper_row[1]
                or helper_row[1].__code__ is not helper_row[2]
                or helper_row[1].__globals__ is not helper_namespace
                or helper_row[1].__builtins__ is not helper_builtin_namespace
                or helper_row[1].__defaults__ is not helper_row[4]
                or helper_row[1].__kwdefaults__ is not helper_row[5]
                or helper_row[1].__closure__ is not None
                or _type(helper_row[6]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw, helper_kw_pairs = helper_row[5], helper_row[6]
        if helper_kw is None:
            if _len(helper_kw_pairs) != 0:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_kw) is not _dict or _any(_type(k) is not _str for k in helper_kw)
                    or _len(helper_kw) != _len(helper_kw_pairs)):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_seen = {}
            for helper_pair in helper_kw_pairs:
                if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                        or _type(helper_pair[0]) is not _str):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_key, helper_value = helper_pair
                if (helper_key in helper_seen or helper_key not in helper_kw
                        or helper_kw[helper_key] is not helper_value):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_seen[helper_key] = helper_value
    helper_error_kind, helper_error_bases, helper_error_pairs = helper_capsule[4]
    if (_type(helper_error_kind) is not _type
            or helper_namespace.get('RetainedBindingOriginError') is not helper_error_kind
            or _type(helper_error_bases) is not _tuple or _len(helper_error_bases) != 1
            or helper_error_bases[0] is not helper_expected_builtins[10]
            or helper_error_kind.__bases__ is not helper_error_bases
            or _type(helper_error_pairs) is not _tuple):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if (_any(_type(k) is not _str for k in helper_error_names)
            or _len(helper_error_names) != _len(helper_error_pairs)
            or '__init__' in helper_error_names or '__new__' in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_error_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_error_names
                or helper_error_names[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    helper_packet = helper_capsule[6]
    if (_type(helper_packet) is not _tuple or _len(helper_packet) != 6
            or helper_packet[0] is not environment[0] or helper_packet[1] is not environment[1]
            or helper_packet[2] is not environment[2]):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    try:
        helper_checked = helper_capsule[3][1][1](helper_packet)
    except _error:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (helper_checked is not helper_packet or origin[0] is not environment
            or environment[6] is not helper_capsule):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # Authenticate the component before dispatch; the actual parent holds this DATA.
    if (_type(helper_capsule) is not _tuple or _len(helper_capsule) != 7
            or _type(helper_capsule[0]) is not _module
            or _type(helper_capsule[1]) is not _dict
            or _type(helper_capsule[2]) is not _tuple
            or _type(helper_capsule[3]) is not _tuple or _len(helper_capsule[3]) != 2
            or _type(helper_capsule[4]) is not _tuple or _len(helper_capsule[4]) != 3
            or _type(helper_capsule[5]) is not _tuple or _len(helper_capsule[5]) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_module, helper_namespace, helper_pairs = helper_capsule[:3]
    helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs = helper_capsule[5]
    if (_any(_type(k) is not _str for k in helper_registry)
            or helper_registry.get('hmp_startup.retained_binding_origin') is not helper_module
            or _vars(helper_module) is not helper_namespace
            or _any(_type(k) is not _str for k in helper_namespace)
            or _len(helper_namespace) != _len(helper_pairs)
            or helper_namespace.get('sys') is not helper_system
            or _type(helper_builtin_module) is not _module
            or _type(helper_builtin_namespace) is not _dict
            or helper_registry.get('builtins') is not helper_builtin_module
            or _vars(helper_builtin_module) is not helper_builtin_namespace
            or _any(_type(k) is not _str for k in helper_builtin_namespace)
            or helper_namespace.get('__builtins__') is not helper_builtin_namespace
            or _type(helper_primitive_pairs) is not _tuple
            or _len(helper_primitive_pairs) != 20):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_namespace
                or helper_namespace[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    for helper_pair, helper_name, helper_expected in _zip(
            helper_primitive_pairs,
            ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
             'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True):
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str or helper_pair[0] != helper_name
                or helper_pair[1] is not helper_expected
                or helper_builtin_namespace.get(helper_name) is not helper_expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_row, helper_name in _zip(helper_capsule[3], ('capture', 'current'), strict=True):
        if (_type(helper_row) is not _tuple or _len(helper_row) != 7
                or _type(helper_row[0]) is not _str or helper_row[0] != helper_name
                or _type(helper_row[1]) is not _function or helper_row[3] is not helper_namespace
                or helper_namespace.get(helper_name) is not helper_row[1]
                or helper_row[1].__code__ is not helper_row[2]
                or helper_row[1].__globals__ is not helper_namespace
                or helper_row[1].__builtins__ is not helper_builtin_namespace
                or helper_row[1].__defaults__ is not helper_row[4]
                or helper_row[1].__kwdefaults__ is not helper_row[5]
                or helper_row[1].__closure__ is not None
                or _type(helper_row[6]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw, helper_kw_pairs = helper_row[5], helper_row[6]
        if helper_kw is None:
            if _len(helper_kw_pairs) != 0:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_kw) is not _dict or _any(_type(k) is not _str for k in helper_kw)
                    or _len(helper_kw) != _len(helper_kw_pairs)):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_seen = {}
            for helper_pair in helper_kw_pairs:
                if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                        or _type(helper_pair[0]) is not _str):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_key, helper_value = helper_pair
                if (helper_key in helper_seen or helper_key not in helper_kw
                        or helper_kw[helper_key] is not helper_value):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_seen[helper_key] = helper_value
    helper_error_kind, helper_error_bases, helper_error_pairs = helper_capsule[4]
    if (_type(helper_error_kind) is not _type
            or helper_namespace.get('RetainedBindingOriginError') is not helper_error_kind
            or _type(helper_error_bases) is not _tuple or _len(helper_error_bases) != 1
            or helper_error_bases[0] is not helper_expected_builtins[10]
            or helper_error_kind.__bases__ is not helper_error_bases
            or _type(helper_error_pairs) is not _tuple):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if (_any(_type(k) is not _str for k in helper_error_names)
            or _len(helper_error_names) != _len(helper_error_pairs)
            or '__init__' in helper_error_names or '__new__' in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_error_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_error_names
                or helper_error_names[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value

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
    audit_record = environment[7]
    if (_type(audit_record) is not _tuple or _len(audit_record) != 3
            or audit_record[0] is not engine
            or audit_record[1] is not environment[5]
            or audit_record[2] is not held):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
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
    # Final selected-helper seal is inline: no checker-return window follows.
    if (origin[0] is not environment or environment[6] is not helper_capsule
            or environment[7] is not audit_record
            or audit_record[0] is not engine
            or audit_record[1] is not environment[5]
            or audit_record[2] is not held):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # Authenticate the component before dispatch; the actual parent holds this DATA.
    if (_type(helper_capsule) is not _tuple or _len(helper_capsule) != 7
            or _type(helper_capsule[0]) is not _module
            or _type(helper_capsule[1]) is not _dict
            or _type(helper_capsule[2]) is not _tuple
            or _type(helper_capsule[3]) is not _tuple or _len(helper_capsule[3]) != 2
            or _type(helper_capsule[4]) is not _tuple or _len(helper_capsule[4]) != 3
            or _type(helper_capsule[5]) is not _tuple or _len(helper_capsule[5]) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_module, helper_namespace, helper_pairs = helper_capsule[:3]
    helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs = helper_capsule[5]
    if (_any(_type(k) is not _str for k in helper_registry)
            or helper_registry.get('hmp_startup.retained_binding_origin') is not helper_module
            or _vars(helper_module) is not helper_namespace
            or _any(_type(k) is not _str for k in helper_namespace)
            or _len(helper_namespace) != _len(helper_pairs)
            or helper_namespace.get('sys') is not helper_system
            or _type(helper_builtin_module) is not _module
            or _type(helper_builtin_namespace) is not _dict
            or helper_registry.get('builtins') is not helper_builtin_module
            or _vars(helper_builtin_module) is not helper_builtin_namespace
            or _any(_type(k) is not _str for k in helper_builtin_namespace)
            or helper_namespace.get('__builtins__') is not helper_builtin_namespace
            or _type(helper_primitive_pairs) is not _tuple
            or _len(helper_primitive_pairs) != 20):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_namespace
                or helper_namespace[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    for helper_pair, helper_name, helper_expected in _zip(
            helper_primitive_pairs,
            ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
             'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True):
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str or helper_pair[0] != helper_name
                or helper_pair[1] is not helper_expected
                or helper_builtin_namespace.get(helper_name) is not helper_expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_row, helper_name in _zip(helper_capsule[3], ('capture', 'current'), strict=True):
        if (_type(helper_row) is not _tuple or _len(helper_row) != 7
                or _type(helper_row[0]) is not _str or helper_row[0] != helper_name
                or _type(helper_row[1]) is not _function or helper_row[3] is not helper_namespace
                or helper_namespace.get(helper_name) is not helper_row[1]
                or helper_row[1].__code__ is not helper_row[2]
                or helper_row[1].__globals__ is not helper_namespace
                or helper_row[1].__builtins__ is not helper_builtin_namespace
                or helper_row[1].__defaults__ is not helper_row[4]
                or helper_row[1].__kwdefaults__ is not helper_row[5]
                or helper_row[1].__closure__ is not None
                or _type(helper_row[6]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw, helper_kw_pairs = helper_row[5], helper_row[6]
        if helper_kw is None:
            if _len(helper_kw_pairs) != 0:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_kw) is not _dict or _any(_type(k) is not _str for k in helper_kw)
                    or _len(helper_kw) != _len(helper_kw_pairs)):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_seen = {}
            for helper_pair in helper_kw_pairs:
                if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                        or _type(helper_pair[0]) is not _str):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_key, helper_value = helper_pair
                if (helper_key in helper_seen or helper_key not in helper_kw
                        or helper_kw[helper_key] is not helper_value):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_seen[helper_key] = helper_value
    helper_error_kind, helper_error_bases, helper_error_pairs = helper_capsule[4]
    if (_type(helper_error_kind) is not _type
            or helper_namespace.get('RetainedBindingOriginError') is not helper_error_kind
            or _type(helper_error_bases) is not _tuple or _len(helper_error_bases) != 1
            or helper_error_bases[0] is not helper_expected_builtins[10]
            or helper_error_kind.__bases__ is not helper_error_bases
            or _type(helper_error_pairs) is not _tuple):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if (_any(_type(k) is not _str for k in helper_error_names)
            or _len(helper_error_names) != _len(helper_error_pairs)
            or '__init__' in helper_error_names or '__new__' in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_error_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_error_names
                or helper_error_names[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    helper_final_packet = helper_packet
    helper_data_modules = helper_namespace['_MODULES']
    helper_data_classes = helper_namespace['_CLASSES']
    helper_data_functions = helper_namespace['_FUNCTIONS']
    helper_data_live_globals = helper_namespace['_LIVE_GLOBALS']
    if (_type(helper_final_packet) is _tuple and _len(helper_final_packet) == 6) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_final_system, helper_final_system_names, helper_final_registry, helper_final_modules, helper_final_classes, helper_final_functions = helper_final_packet
    if (_type(helper_final_system) is _module and _type(helper_final_system_names) is _dict and (_vars(helper_final_system) is helper_final_system_names) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_system_names)) and (_type(helper_final_registry) is _dict) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_registry)) and (helper_final_system_names.get('modules') is helper_final_registry) and (_type(helper_final_modules) is _tuple) and (_len(helper_final_modules) == _len(helper_data_modules)) and (_type(helper_final_classes) is _tuple) and (_len(helper_final_classes) == _len(helper_data_classes)) and (_type(helper_final_functions) is _tuple) and (_len(helper_final_functions) == _len(helper_data_functions))) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_final_builtin_module = helper_final_registry.get('builtins')
    if _type(helper_final_builtin_module) is not _module:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_final_builtin_namespace = _vars(helper_final_builtin_module)
    if (_type(helper_final_builtin_namespace) is _dict and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_builtin_namespace))) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_final_row, helper_final_name, helper_final_live_keys in _zip(helper_final_modules, helper_data_modules, helper_data_live_globals, strict=True):
        if (_type(helper_final_row) is _tuple and _len(helper_final_row) == 3) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_module, helper_final_namespace, helper_final_pairs = helper_final_row
        if (_type(helper_final_module) is _module and _type(helper_final_namespace) is _dict and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_registry)) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) and (helper_final_registry.get(helper_final_name) is helper_final_module) and (_vars(helper_final_module) is helper_final_namespace) and (_type(helper_final_namespace.get('__name__')) is _str) and (helper_final_namespace['__name__'] == helper_final_name) and (helper_final_namespace.get('__builtins__') is helper_final_builtin_namespace or helper_final_namespace.get('__builtins__') is helper_final_builtin_module) and (_type(helper_final_pairs) is _tuple) and (_len(helper_final_namespace) == _len(helper_final_pairs) + _len(helper_final_live_keys))) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_expected_pairs = {}
        for helper_final_pair in helper_final_pairs:
            if (_type(helper_final_pair) is _tuple and _len(helper_final_pair) == 2 and (_type(helper_final_pair[0]) is _str)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_key, helper_final_value = helper_final_pair
            if helper_final_key in helper_final_live_keys or helper_final_key in helper_final_expected_pairs:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_expected_pairs[helper_final_key] = helper_final_value
        helper_final_valid, helper_final_observed, helper_final_live_seen = (True, 0, 0)
        try:
            for helper_final_key, helper_final_value in helper_final_namespace.items():
                if _type(helper_final_key) is not _str:
                    helper_final_valid = False
                    break
                helper_final_observed += 1
                if helper_final_key in helper_final_live_keys:
                    helper_final_live_seen += 1
                elif helper_final_key not in helper_final_expected_pairs or helper_final_expected_pairs[helper_final_key] is not helper_final_value:
                    helper_final_valid = False
                    break
        except _error:
            helper_final_valid = False
        if (helper_final_valid is True and helper_final_observed == _len(helper_final_pairs) + _len(helper_final_live_keys) and (helper_final_live_seen == _len(helper_final_live_keys))) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_final_row, (helper_final_index, helper_final_name) in _zip(helper_final_classes, helper_data_classes, strict=True):
        if (_type(helper_final_row) is _tuple and _len(helper_final_row) == 3) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_kind, helper_final_bases, helper_final_pairs = helper_final_row
        if (_type(helper_final_kind) is _type and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[helper_final_index][1])) and (helper_final_modules[helper_final_index][1].get(helper_final_name) is helper_final_kind) and (helper_final_kind.__bases__ is helper_final_bases) and (_type(helper_final_pairs) is _tuple)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_names = _vars(helper_final_kind)
        if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_names)) and _len(helper_final_names) == _len(helper_final_pairs)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_seen = _set()
        for helper_final_pair in helper_final_pairs:
            if (_type(helper_final_pair) is _tuple and _len(helper_final_pair) == 2 and (_type(helper_final_pair[0]) is _str)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_key, helper_final_value = helper_final_pair
            if (helper_final_key not in helper_final_seen and helper_final_key in helper_final_names and (helper_final_names[helper_final_key] is helper_final_value)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_seen.add(helper_final_key)
    for helper_final_row, (helper_final_index, helper_final_owner, helper_final_name) in _zip(helper_final_functions, helper_data_functions, strict=True):
        if (_type(helper_final_row) is _tuple and _len(helper_final_row) == 8) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_function, helper_final_code, helper_final_namespace, helper_final_defaults, helper_final_kw, helper_final_pairs, helper_final_closure, helper_final_cells = helper_final_row
        if (_type(helper_final_namespace) is _dict and helper_final_namespace is helper_final_modules[helper_final_index][1] and (_type(helper_final_function) is _function) and (helper_final_function.__globals__ is helper_final_namespace) and (helper_final_function.__builtins__ is helper_final_builtin_namespace) and (helper_final_function.__code__ is helper_final_code) and (helper_final_function.__defaults__ is helper_final_defaults) and (helper_final_defaults is None or _type(helper_final_defaults) is _tuple) and (helper_final_function.__kwdefaults__ is helper_final_kw) and (helper_final_function.__closure__ is helper_final_closure) and (_type(helper_final_pairs) is _tuple) and (_type(helper_final_cells) is _tuple)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_names = helper_final_namespace
        if _all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if helper_final_owner is not None:
            helper_final_held_kind = None
            for helper_final_class_row, (helper_final_class_index, helper_final_class_name) in _zip(helper_final_classes, helper_data_classes, strict=True):
                if helper_final_class_index == helper_final_index and helper_final_class_name == helper_final_owner:
                    helper_final_held_kind = helper_final_class_row[0]
                    break
            if (_type(helper_final_held_kind) is _type and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) and (helper_final_namespace.get(helper_final_owner) is helper_final_held_kind)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_names = _vars(helper_final_held_kind)
        if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_names)) and helper_final_names.get(helper_final_name) is helper_final_function) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if helper_final_kw is None:
            if (helper_final_pairs == ()) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_final_kw) is _dict and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_kw)) and (_len(helper_final_kw) == _len(helper_final_pairs))) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_seen = _set()
            for helper_final_pair in helper_final_pairs:
                if (_type(helper_final_pair) is _tuple and _len(helper_final_pair) == 2 and (_type(helper_final_pair[0]) is _str)) is not True:
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_final_key, helper_final_value = helper_final_pair
                if (helper_final_key not in helper_final_seen and helper_final_key in helper_final_kw and (helper_final_kw[helper_final_key] is helper_final_value)) is not True:
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_final_seen.add(helper_final_key)
        if helper_final_closure is None:
            if (helper_final_cells == ()) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_final_closure) is _tuple and _len(helper_final_closure) == _len(helper_final_cells)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            try:
                if _all((_type(helper_final_cell) is _cell and helper_final_cell.cell_contents is helper_final_value for helper_final_cell, helper_final_value in _zip(helper_final_closure, helper_final_cells, strict=True))) is not True:
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            except _value_error:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[0][1])) and helper_final_modules[0][1].get('GatewayRecipeOwner') is helper_final_classes[2][0] and (helper_final_modules[0][1].get('_same_recipe_binding') is helper_final_functions[4][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[0][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[1][1])) and (helper_final_modules[0][1].get('StartupSelectionOwner') is helper_final_classes[3][0]) and (helper_final_modules[1][1].get('StartupSelectionOwner') is helper_final_classes[3][0]) and (helper_final_modules[0][1].get('GatewayStartupSelection') is helper_final_classes[6][0]) and (helper_final_modules[1][1].get('GatewayStartupSelection') is helper_final_classes[6][0]) and (helper_final_modules[0][1].get('IoScope') is helper_final_classes[4][0]) and (helper_final_modules[1][1].get('_Scope') is helper_final_classes[4][0]) and (helper_final_modules[1][1].get('_approved_recipe') is helper_final_functions[6][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[0][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[1][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[2][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[3][1])) and (helper_final_modules[0][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[1][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[2][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[2][1].get('_LATE_MODULES') is helper_final_modules[3][1].get('_LATE_MODULES'))) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[4][1])) and helper_final_modules[4][1].get('_Scope') is helper_final_classes[4][0] and (helper_final_modules[4][1].get('GatewayActivationOwner') is helper_final_classes[10][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_final_index in (0, 1, 2):
        helper_final_namespace = helper_final_modules[helper_final_index][1]
        if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) and helper_final_namespace.get('ExpectedArtifact') is helper_final_classes[13][0] and (helper_final_namespace.get('_descriptor_closed_in_scope') is helper_final_functions[15][0]) and (helper_final_namespace.get('_expected') is helper_final_functions[19][0])) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[5][1])) and helper_final_modules[2][1].get('_APPROVAL_OWNER_TYPE') is helper_final_classes[23][0] and (helper_final_modules[5][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[5][1].get('_LATE_MODULES') is helper_final_modules[3][1].get('_LATE_MODULES')) and (helper_final_modules[5][1].get('ExpectedArtifact') is helper_final_classes[13][0]) and (helper_final_modules[5][1].get('_Scope') is helper_final_classes[4][0]) and (helper_final_modules[5][1].get('_descriptor_closed_in_scope') is helper_final_functions[15][0]) and (helper_final_modules[5][1].get('OperatorApprovalPath') is helper_final_classes[38][0]) and (helper_final_modules[5][1].get('_OperatorFileReceipt') is helper_final_classes[39][0]) and (helper_final_modules[5][1].get('_ReadEffect') is helper_final_classes[40][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[6][1])) and helper_final_modules[5][1].get('GatewayEntryOwner') is helper_final_classes[27][0] and (helper_final_modules[6][1].get('GatewayActivationOwner') is helper_final_classes[10][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    return origin


def current_started(origin, *, _type=type, _vars=vars, _tuple=tuple, _len=len,
            _function=FunctionType, _module=ModuleType, _staticmethod=staticmethod,
            _any=any, _zip=zip, _builtin=BuiltinFunctionType,
            _descriptor=MethodDescriptorType, _str=str, _dict=dict,
            _all=all, _set=set, _value_error=ValueError, _cell=CellType,
            _bool=bool, _int=int, _list=list, _bytes=bytes, _bytearray=bytearray,
            _sum=sum, _ord=ord, _super=super, _getset=GetSetDescriptorType, _error=RuntimeError):
    """Strict original-started-root audit; never a missing-root generic fallback.

    Capture and standalone DATA use current. Actual Scope callers must also join
    their independently held record before selecting this captured fixed row.
    """
    if _type(origin) is not _tuple or _len(origin) != 5:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    environment, modules, own_functions, policy_functions, types = origin
    if (_type(environment) is not _tuple or _len(environment) != 8
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
    own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory', 'blueprint_factory', 'encode_basename', 'current_started')
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

    helper_capsule = environment[6]
    helper_system, helper_registry = environment[0], environment[2]
    helper_expected_builtins = (_type, _vars, _tuple, _len, _dict, _str, _any, _zip,
                                _all, _set, _error, _value_error,
                                _bool, _int, _list, _bytes, _bytearray, _sum, _ord, _super)
    # Authenticate the component before dispatch; the actual parent holds this DATA.
    if (_type(helper_capsule) is not _tuple or _len(helper_capsule) != 7
            or _type(helper_capsule[0]) is not _module
            or _type(helper_capsule[1]) is not _dict
            or _type(helper_capsule[2]) is not _tuple
            or _type(helper_capsule[3]) is not _tuple or _len(helper_capsule[3]) != 2
            or _type(helper_capsule[4]) is not _tuple or _len(helper_capsule[4]) != 3
            or _type(helper_capsule[5]) is not _tuple or _len(helper_capsule[5]) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_module, helper_namespace, helper_pairs = helper_capsule[:3]
    helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs = helper_capsule[5]
    if (_any(_type(k) is not _str for k in helper_registry)
            or helper_registry.get('hmp_startup.retained_binding_origin') is not helper_module
            or _vars(helper_module) is not helper_namespace
            or _any(_type(k) is not _str for k in helper_namespace)
            or _len(helper_namespace) != _len(helper_pairs)
            or helper_namespace.get('sys') is not helper_system
            or _type(helper_builtin_module) is not _module
            or _type(helper_builtin_namespace) is not _dict
            or helper_registry.get('builtins') is not helper_builtin_module
            or _vars(helper_builtin_module) is not helper_builtin_namespace
            or _any(_type(k) is not _str for k in helper_builtin_namespace)
            or helper_namespace.get('__builtins__') is not helper_builtin_namespace
            or _type(helper_primitive_pairs) is not _tuple
            or _len(helper_primitive_pairs) != 20):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_namespace
                or helper_namespace[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    for helper_pair, helper_name, helper_expected in _zip(
            helper_primitive_pairs,
            ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
             'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True):
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str or helper_pair[0] != helper_name
                or helper_pair[1] is not helper_expected
                or helper_builtin_namespace.get(helper_name) is not helper_expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_row, helper_name in _zip(helper_capsule[3], ('capture', 'current'), strict=True):
        if (_type(helper_row) is not _tuple or _len(helper_row) != 7
                or _type(helper_row[0]) is not _str or helper_row[0] != helper_name
                or _type(helper_row[1]) is not _function or helper_row[3] is not helper_namespace
                or helper_namespace.get(helper_name) is not helper_row[1]
                or helper_row[1].__code__ is not helper_row[2]
                or helper_row[1].__globals__ is not helper_namespace
                or helper_row[1].__builtins__ is not helper_builtin_namespace
                or helper_row[1].__defaults__ is not helper_row[4]
                or helper_row[1].__kwdefaults__ is not helper_row[5]
                or helper_row[1].__closure__ is not None
                or _type(helper_row[6]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw, helper_kw_pairs = helper_row[5], helper_row[6]
        if helper_kw is None:
            if _len(helper_kw_pairs) != 0:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_kw) is not _dict or _any(_type(k) is not _str for k in helper_kw)
                    or _len(helper_kw) != _len(helper_kw_pairs)):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_seen = {}
            for helper_pair in helper_kw_pairs:
                if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                        or _type(helper_pair[0]) is not _str):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_key, helper_value = helper_pair
                if (helper_key in helper_seen or helper_key not in helper_kw
                        or helper_kw[helper_key] is not helper_value):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_seen[helper_key] = helper_value
    helper_error_kind, helper_error_bases, helper_error_pairs = helper_capsule[4]
    if (_type(helper_error_kind) is not _type
            or helper_namespace.get('RetainedBindingOriginError') is not helper_error_kind
            or _type(helper_error_bases) is not _tuple or _len(helper_error_bases) != 1
            or helper_error_bases[0] is not helper_expected_builtins[10]
            or helper_error_kind.__bases__ is not helper_error_bases
            or _type(helper_error_pairs) is not _tuple):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if (_any(_type(k) is not _str for k in helper_error_names)
            or _len(helper_error_names) != _len(helper_error_pairs)
            or '__init__' in helper_error_names or '__new__' in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_error_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_error_names
                or helper_error_names[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    helper_packet = helper_capsule[6]
    if (_type(helper_packet) is not _tuple or _len(helper_packet) != 6
            or helper_packet[0] is not environment[0] or helper_packet[1] is not environment[1]
            or helper_packet[2] is not environment[2]):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    try:
        helper_checked = helper_capsule[3][1][1](helper_packet)
    except _error:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (helper_checked is not helper_packet or origin[0] is not environment
            or environment[6] is not helper_capsule):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # Authenticate the component before dispatch; the actual parent holds this DATA.
    if (_type(helper_capsule) is not _tuple or _len(helper_capsule) != 7
            or _type(helper_capsule[0]) is not _module
            or _type(helper_capsule[1]) is not _dict
            or _type(helper_capsule[2]) is not _tuple
            or _type(helper_capsule[3]) is not _tuple or _len(helper_capsule[3]) != 2
            or _type(helper_capsule[4]) is not _tuple or _len(helper_capsule[4]) != 3
            or _type(helper_capsule[5]) is not _tuple or _len(helper_capsule[5]) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_module, helper_namespace, helper_pairs = helper_capsule[:3]
    helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs = helper_capsule[5]
    if (_any(_type(k) is not _str for k in helper_registry)
            or helper_registry.get('hmp_startup.retained_binding_origin') is not helper_module
            or _vars(helper_module) is not helper_namespace
            or _any(_type(k) is not _str for k in helper_namespace)
            or _len(helper_namespace) != _len(helper_pairs)
            or helper_namespace.get('sys') is not helper_system
            or _type(helper_builtin_module) is not _module
            or _type(helper_builtin_namespace) is not _dict
            or helper_registry.get('builtins') is not helper_builtin_module
            or _vars(helper_builtin_module) is not helper_builtin_namespace
            or _any(_type(k) is not _str for k in helper_builtin_namespace)
            or helper_namespace.get('__builtins__') is not helper_builtin_namespace
            or _type(helper_primitive_pairs) is not _tuple
            or _len(helper_primitive_pairs) != 20):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_namespace
                or helper_namespace[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    for helper_pair, helper_name, helper_expected in _zip(
            helper_primitive_pairs,
            ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
             'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True):
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str or helper_pair[0] != helper_name
                or helper_pair[1] is not helper_expected
                or helper_builtin_namespace.get(helper_name) is not helper_expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_row, helper_name in _zip(helper_capsule[3], ('capture', 'current'), strict=True):
        if (_type(helper_row) is not _tuple or _len(helper_row) != 7
                or _type(helper_row[0]) is not _str or helper_row[0] != helper_name
                or _type(helper_row[1]) is not _function or helper_row[3] is not helper_namespace
                or helper_namespace.get(helper_name) is not helper_row[1]
                or helper_row[1].__code__ is not helper_row[2]
                or helper_row[1].__globals__ is not helper_namespace
                or helper_row[1].__builtins__ is not helper_builtin_namespace
                or helper_row[1].__defaults__ is not helper_row[4]
                or helper_row[1].__kwdefaults__ is not helper_row[5]
                or helper_row[1].__closure__ is not None
                or _type(helper_row[6]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw, helper_kw_pairs = helper_row[5], helper_row[6]
        if helper_kw is None:
            if _len(helper_kw_pairs) != 0:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_kw) is not _dict or _any(_type(k) is not _str for k in helper_kw)
                    or _len(helper_kw) != _len(helper_kw_pairs)):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_seen = {}
            for helper_pair in helper_kw_pairs:
                if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                        or _type(helper_pair[0]) is not _str):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_key, helper_value = helper_pair
                if (helper_key in helper_seen or helper_key not in helper_kw
                        or helper_kw[helper_key] is not helper_value):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_seen[helper_key] = helper_value
    helper_error_kind, helper_error_bases, helper_error_pairs = helper_capsule[4]
    if (_type(helper_error_kind) is not _type
            or helper_namespace.get('RetainedBindingOriginError') is not helper_error_kind
            or _type(helper_error_bases) is not _tuple or _len(helper_error_bases) != 1
            or helper_error_bases[0] is not helper_expected_builtins[10]
            or helper_error_kind.__bases__ is not helper_error_bases
            or _type(helper_error_pairs) is not _tuple):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if (_any(_type(k) is not _str for k in helper_error_names)
            or _len(helper_error_names) != _len(helper_error_pairs)
            or '__init__' in helper_error_names or '__new__' in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_error_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_error_names
                or helper_error_names[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value

    # The selected-helper packet was fully checked above, including its exact
    # module/class schemas. Hold actual original started roots before live dispatch.
    started_entry_module, started_entry_names, _ = helper_packet[3][6]
    started_entry_kind = helper_packet[4][30][0]
    started_invocation_kind = helper_packet[4][29][0]
    started_lineage_kind = helper_packet[4][35][0]
    started_owner_kind = helper_packet[4][27][0]
    if (_type(started_entry_module) is not _module
            or _type(started_entry_names) is not _dict
            or _vars(started_entry_module) is not started_entry_names
            or _any(_type(k) is not _str for k in started_entry_names)
            or environment[2].get('hmp_startup.gateway_entry') is not started_entry_module):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    started_origin = started_entry_names.get('_ENTRY_ORIGIN')
    started_root = started_entry_names.get('_STARTED')
    started_cell = started_entry_names.get('_CELL')
    started_owner = started_entry_names.get('_OWNER')
    if (_type(started_entry_kind) is not _type or _type(started_origin) is not started_entry_kind
            or _tuple.__len__(started_origin) != 12
            or _type(started_root) is not _tuple or _len(started_root) != 7
            or _type(started_cell) is not _tuple or _len(started_cell) != 2
            or _type(started_owner_kind) is not _type or _type(started_owner) is not started_owner_kind
            or started_root[0] is not started_owner or started_root[2] is not started_cell
            or started_root[5] is not started_origin or started_cell[0] is not started_owner
            or _tuple.__getitem__(started_origin, 10) is not origin
            or _tuple.__getitem__(started_origin, 11) is not environment[7]):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    started_invocation = started_root[1]
    if (_type(started_invocation_kind) is not _type
            or _type(started_invocation) is not started_invocation_kind
            or _tuple.__len__(started_invocation) != 11
            or started_cell[1] is not started_invocation):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    started_lineage = _tuple.__getitem__(started_invocation, 9)
    if (_type(started_lineage_kind) is not _type
            or _type(started_lineage) is not started_lineage_kind
            or _tuple.__len__(started_lineage) != 6
            or _tuple.__getitem__(started_lineage, 0) is not started_owner
            or _tuple.__getitem__(started_lineage, 4) is not origin
            or _tuple.__getitem__(started_lineage, 5) is not environment[7]):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    started_descriptors = _tuple(pair[1] for pair in helper_packet[4][27][2]
                                 if pair[0] == '__dict__')
    if (_len(started_descriptors) != 1 or _type(started_descriptors[0]) is not _getset
            or started_descriptors[0].__objclass__ is not started_owner_kind):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    started_dict_descriptor = started_descriptors[0]
    started_owner_names = started_dict_descriptor.__get__(started_owner, started_owner_kind)
    if (_type(started_owner) is not started_owner_kind
            or _type(started_entry_module) is not _module
            or _vars(started_entry_module) is not started_entry_names
            or _any(_type(k) is not _str for k in started_entry_names)
            or _any(_type(k) is not _str for k in environment[2])
            or environment[2].get('hmp_startup.gateway_entry') is not started_entry_module
            or started_entry_names.get('_ENTRY_ORIGIN') is not started_origin
            or started_entry_names.get('_STARTED') is not started_root
            or started_entry_names.get('_CELL') is not started_cell
            or started_entry_names.get('_OWNER') is not started_owner
            or _type(started_owner_names) is not _dict
            or _any(_type(k) is not _str for k in started_owner_names)
            or started_dict_descriptor.__get__(started_owner, started_owner_kind) is not started_owner_names
            or started_owner_names.get('_scope') is not started_invocation
            or started_owner_names.get('_started_cell') is not started_root
            or started_owner_names.get('_ready') is not True
            or started_owner_names.get('_failed') is not False
            or _tuple.__getitem__(started_origin, 10) is not origin
            or _tuple.__getitem__(started_origin, 11) is not environment[7]
            or _tuple.__getitem__(started_lineage, 4) is not origin
            or _tuple.__getitem__(started_lineage, 5) is not environment[7]):
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
    audit_record = environment[7]
    if (_type(audit_record) is not _tuple or _len(audit_record) != 3
            or audit_record[0] is not engine
            or audit_record[1] is not environment[5]
            or audit_record[2] is not held):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
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
    live_rows = _tuple(row for row in engine[2]
                       if _type(row) is _tuple and _len(row) == 7
                       and _type(row[0]) is _str and row[0] == '_engine_live_tail')
    if _len(live_rows) != 1:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    live_row = live_rows[0]
    live_checker = live_row[1]
    if (_any(_type(k) is not _str for k in namespace)
            or live_row[3] is not namespace or _type(live_checker) is not _function
            or namespace.get('_engine_live_tail') is not live_checker
            or live_checker.__code__ is not live_row[2]
            or live_checker.__globals__ is not namespace
            or live_checker.__builtins__ is not helper_builtin_namespace
            or live_checker.__defaults__ is not live_row[4]
            or live_checker.__closure__ is not None
            or live_checker.__kwdefaults__ is not live_row[5]
            or _type(live_row[5]) is not _dict or _type(live_row[6]) is not _tuple
            or _any(_type(k) is not _str for k in live_row[5])
            or _len(live_row[5]) != _len(live_row[6])
            or _any(_type(pair) is not _tuple or _len(pair) != 2
                    or _type(pair[0]) is not _str or pair[0] not in live_row[5]
                    or live_row[5][pair[0]] is not pair[1] for pair in live_row[6])):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_type(started_owner) is not started_owner_kind
            or _type(started_entry_module) is not _module
            or _vars(started_entry_module) is not started_entry_names
            or _any(_type(k) is not _str for k in started_entry_names)
            or _any(_type(k) is not _str for k in environment[2])
            or environment[2].get('hmp_startup.gateway_entry') is not started_entry_module
            or started_entry_names.get('_ENTRY_ORIGIN') is not started_origin
            or started_entry_names.get('_STARTED') is not started_root
            or started_entry_names.get('_CELL') is not started_cell
            or started_entry_names.get('_OWNER') is not started_owner
            or _type(started_owner_names) is not _dict
            or _any(_type(k) is not _str for k in started_owner_names)
            or started_dict_descriptor.__get__(started_owner, started_owner_kind) is not started_owner_names
            or started_owner_names.get('_scope') is not started_invocation
            or started_owner_names.get('_started_cell') is not started_root
            or started_owner_names.get('_ready') is not True
            or started_owner_names.get('_failed') is not False
            or _tuple.__getitem__(started_origin, 10) is not origin
            or _tuple.__getitem__(started_origin, 11) is not environment[7]
            or _tuple.__getitem__(started_lineage, 4) is not origin
            or _tuple.__getitem__(started_lineage, 5) is not environment[7]):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if live_checker(engine, environment[5]) is not engine:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_type(started_owner) is not started_owner_kind
            or _type(started_entry_module) is not _module
            or _vars(started_entry_module) is not started_entry_names
            or _any(_type(k) is not _str for k in started_entry_names)
            or _any(_type(k) is not _str for k in environment[2])
            or environment[2].get('hmp_startup.gateway_entry') is not started_entry_module
            or started_entry_names.get('_ENTRY_ORIGIN') is not started_origin
            or started_entry_names.get('_STARTED') is not started_root
            or started_entry_names.get('_CELL') is not started_cell
            or started_entry_names.get('_OWNER') is not started_owner
            or _type(started_owner_names) is not _dict
            or _any(_type(k) is not _str for k in started_owner_names)
            or started_dict_descriptor.__get__(started_owner, started_owner_kind) is not started_owner_names
            or started_owner_names.get('_scope') is not started_invocation
            or started_owner_names.get('_started_cell') is not started_root
            or started_owner_names.get('_ready') is not True
            or started_owner_names.get('_failed') is not False
            or _tuple.__getitem__(started_origin, 10) is not origin
            or _tuple.__getitem__(started_origin, 11) is not environment[7]
            or _tuple.__getitem__(started_lineage, 4) is not origin
            or _tuple.__getitem__(started_lineage, 5) is not environment[7]):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_any(_type(k) is not _str for k in namespace)
            or live_row[3] is not namespace or _type(live_checker) is not _function
            or namespace.get('_engine_live_tail') is not live_checker
            or live_checker.__code__ is not live_row[2]
            or live_checker.__globals__ is not namespace
            or live_checker.__builtins__ is not helper_builtin_namespace
            or live_checker.__defaults__ is not live_row[4]
            or live_checker.__closure__ is not None
            or live_checker.__kwdefaults__ is not live_row[5]
            or _type(live_row[5]) is not _dict or _type(live_row[6]) is not _tuple
            or _any(_type(k) is not _str for k in live_row[5])
            or _len(live_row[5]) != _len(live_row[6])
            or _any(_type(pair) is not _tuple or _len(pair) != 2
                    or _type(pair[0]) is not _str or pair[0] not in live_row[5]
                    or live_row[5][pair[0]] is not pair[1] for pair in live_row[6])):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # Final selected-helper seal is inline: no checker-return window follows.
    if (origin[0] is not environment or environment[6] is not helper_capsule
            or environment[7] is not audit_record
            or audit_record[0] is not engine
            or audit_record[1] is not environment[5]
            or audit_record[2] is not held):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # Authenticate the component before dispatch; the actual parent holds this DATA.
    if (_type(helper_capsule) is not _tuple or _len(helper_capsule) != 7
            or _type(helper_capsule[0]) is not _module
            or _type(helper_capsule[1]) is not _dict
            or _type(helper_capsule[2]) is not _tuple
            or _type(helper_capsule[3]) is not _tuple or _len(helper_capsule[3]) != 2
            or _type(helper_capsule[4]) is not _tuple or _len(helper_capsule[4]) != 3
            or _type(helper_capsule[5]) is not _tuple or _len(helper_capsule[5]) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_module, helper_namespace, helper_pairs = helper_capsule[:3]
    helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs = helper_capsule[5]
    if (_any(_type(k) is not _str for k in helper_registry)
            or helper_registry.get('hmp_startup.retained_binding_origin') is not helper_module
            or _vars(helper_module) is not helper_namespace
            or _any(_type(k) is not _str for k in helper_namespace)
            or _len(helper_namespace) != _len(helper_pairs)
            or helper_namespace.get('sys') is not helper_system
            or _type(helper_builtin_module) is not _module
            or _type(helper_builtin_namespace) is not _dict
            or helper_registry.get('builtins') is not helper_builtin_module
            or _vars(helper_builtin_module) is not helper_builtin_namespace
            or _any(_type(k) is not _str for k in helper_builtin_namespace)
            or helper_namespace.get('__builtins__') is not helper_builtin_namespace
            or _type(helper_primitive_pairs) is not _tuple
            or _len(helper_primitive_pairs) != 20):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_namespace
                or helper_namespace[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    for helper_pair, helper_name, helper_expected in _zip(
            helper_primitive_pairs,
            ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
             'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True):
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str or helper_pair[0] != helper_name
                or helper_pair[1] is not helper_expected
                or helper_builtin_namespace.get(helper_name) is not helper_expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_row, helper_name in _zip(helper_capsule[3], ('capture', 'current'), strict=True):
        if (_type(helper_row) is not _tuple or _len(helper_row) != 7
                or _type(helper_row[0]) is not _str or helper_row[0] != helper_name
                or _type(helper_row[1]) is not _function or helper_row[3] is not helper_namespace
                or helper_namespace.get(helper_name) is not helper_row[1]
                or helper_row[1].__code__ is not helper_row[2]
                or helper_row[1].__globals__ is not helper_namespace
                or helper_row[1].__builtins__ is not helper_builtin_namespace
                or helper_row[1].__defaults__ is not helper_row[4]
                or helper_row[1].__kwdefaults__ is not helper_row[5]
                or helper_row[1].__closure__ is not None
                or _type(helper_row[6]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw, helper_kw_pairs = helper_row[5], helper_row[6]
        if helper_kw is None:
            if _len(helper_kw_pairs) != 0:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_kw) is not _dict or _any(_type(k) is not _str for k in helper_kw)
                    or _len(helper_kw) != _len(helper_kw_pairs)):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_seen = {}
            for helper_pair in helper_kw_pairs:
                if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                        or _type(helper_pair[0]) is not _str):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_key, helper_value = helper_pair
                if (helper_key in helper_seen or helper_key not in helper_kw
                        or helper_kw[helper_key] is not helper_value):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_seen[helper_key] = helper_value
    helper_error_kind, helper_error_bases, helper_error_pairs = helper_capsule[4]
    if (_type(helper_error_kind) is not _type
            or helper_namespace.get('RetainedBindingOriginError') is not helper_error_kind
            or _type(helper_error_bases) is not _tuple or _len(helper_error_bases) != 1
            or helper_error_bases[0] is not helper_expected_builtins[10]
            or helper_error_kind.__bases__ is not helper_error_bases
            or _type(helper_error_pairs) is not _tuple):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if (_any(_type(k) is not _str for k in helper_error_names)
            or _len(helper_error_names) != _len(helper_error_pairs)
            or '__init__' in helper_error_names or '__new__' in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_error_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_error_names
                or helper_error_names[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    helper_final_packet = helper_packet
    helper_data_modules = helper_namespace['_MODULES']
    helper_data_classes = helper_namespace['_CLASSES']
    helper_data_functions = helper_namespace['_FUNCTIONS']
    helper_data_live_globals = helper_namespace['_LIVE_GLOBALS']
    if (_type(helper_final_packet) is _tuple and _len(helper_final_packet) == 6) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_final_system, helper_final_system_names, helper_final_registry, helper_final_modules, helper_final_classes, helper_final_functions = helper_final_packet
    if (_type(helper_final_system) is _module and _type(helper_final_system_names) is _dict and (_vars(helper_final_system) is helper_final_system_names) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_system_names)) and (_type(helper_final_registry) is _dict) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_registry)) and (helper_final_system_names.get('modules') is helper_final_registry) and (_type(helper_final_modules) is _tuple) and (_len(helper_final_modules) == _len(helper_data_modules)) and (_type(helper_final_classes) is _tuple) and (_len(helper_final_classes) == _len(helper_data_classes)) and (_type(helper_final_functions) is _tuple) and (_len(helper_final_functions) == _len(helper_data_functions))) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_final_builtin_module = helper_final_registry.get('builtins')
    if _type(helper_final_builtin_module) is not _module:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_final_builtin_namespace = _vars(helper_final_builtin_module)
    if (_type(helper_final_builtin_namespace) is _dict and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_builtin_namespace))) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_final_row, helper_final_name, helper_final_live_keys in _zip(helper_final_modules, helper_data_modules, helper_data_live_globals, strict=True):
        if (_type(helper_final_row) is _tuple and _len(helper_final_row) == 3) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_module, helper_final_namespace, helper_final_pairs = helper_final_row
        if (_type(helper_final_module) is _module and _type(helper_final_namespace) is _dict and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_registry)) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) and (helper_final_registry.get(helper_final_name) is helper_final_module) and (_vars(helper_final_module) is helper_final_namespace) and (_type(helper_final_namespace.get('__name__')) is _str) and (helper_final_namespace['__name__'] == helper_final_name) and (helper_final_namespace.get('__builtins__') is helper_final_builtin_namespace or helper_final_namespace.get('__builtins__') is helper_final_builtin_module) and (_type(helper_final_pairs) is _tuple) and (_len(helper_final_namespace) == _len(helper_final_pairs) + _len(helper_final_live_keys))) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_expected_pairs = {}
        for helper_final_pair in helper_final_pairs:
            if (_type(helper_final_pair) is _tuple and _len(helper_final_pair) == 2 and (_type(helper_final_pair[0]) is _str)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_key, helper_final_value = helper_final_pair
            if helper_final_key in helper_final_live_keys or helper_final_key in helper_final_expected_pairs:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_expected_pairs[helper_final_key] = helper_final_value
        helper_final_valid, helper_final_observed, helper_final_live_seen = (True, 0, 0)
        try:
            for helper_final_key, helper_final_value in helper_final_namespace.items():
                if _type(helper_final_key) is not _str:
                    helper_final_valid = False
                    break
                helper_final_observed += 1
                if helper_final_key in helper_final_live_keys:
                    helper_final_live_seen += 1
                elif helper_final_key not in helper_final_expected_pairs or helper_final_expected_pairs[helper_final_key] is not helper_final_value:
                    helper_final_valid = False
                    break
        except _error:
            helper_final_valid = False
        if (helper_final_valid is True and helper_final_observed == _len(helper_final_pairs) + _len(helper_final_live_keys) and (helper_final_live_seen == _len(helper_final_live_keys))) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_final_row, (helper_final_index, helper_final_name) in _zip(helper_final_classes, helper_data_classes, strict=True):
        if (_type(helper_final_row) is _tuple and _len(helper_final_row) == 3) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_kind, helper_final_bases, helper_final_pairs = helper_final_row
        if (_type(helper_final_kind) is _type and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[helper_final_index][1])) and (helper_final_modules[helper_final_index][1].get(helper_final_name) is helper_final_kind) and (helper_final_kind.__bases__ is helper_final_bases) and (_type(helper_final_pairs) is _tuple)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_names = _vars(helper_final_kind)
        if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_names)) and _len(helper_final_names) == _len(helper_final_pairs)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_seen = _set()
        for helper_final_pair in helper_final_pairs:
            if (_type(helper_final_pair) is _tuple and _len(helper_final_pair) == 2 and (_type(helper_final_pair[0]) is _str)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_key, helper_final_value = helper_final_pair
            if (helper_final_key not in helper_final_seen and helper_final_key in helper_final_names and (helper_final_names[helper_final_key] is helper_final_value)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_seen.add(helper_final_key)
    for helper_final_row, (helper_final_index, helper_final_owner, helper_final_name) in _zip(helper_final_functions, helper_data_functions, strict=True):
        if (_type(helper_final_row) is _tuple and _len(helper_final_row) == 8) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_function, helper_final_code, helper_final_namespace, helper_final_defaults, helper_final_kw, helper_final_pairs, helper_final_closure, helper_final_cells = helper_final_row
        if (_type(helper_final_namespace) is _dict and helper_final_namespace is helper_final_modules[helper_final_index][1] and (_type(helper_final_function) is _function) and (helper_final_function.__globals__ is helper_final_namespace) and (helper_final_function.__builtins__ is helper_final_builtin_namespace) and (helper_final_function.__code__ is helper_final_code) and (helper_final_function.__defaults__ is helper_final_defaults) and (helper_final_defaults is None or _type(helper_final_defaults) is _tuple) and (helper_final_function.__kwdefaults__ is helper_final_kw) and (helper_final_function.__closure__ is helper_final_closure) and (_type(helper_final_pairs) is _tuple) and (_type(helper_final_cells) is _tuple)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_final_names = helper_final_namespace
        if _all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if helper_final_owner is not None:
            helper_final_held_kind = None
            for helper_final_class_row, (helper_final_class_index, helper_final_class_name) in _zip(helper_final_classes, helper_data_classes, strict=True):
                if helper_final_class_index == helper_final_index and helper_final_class_name == helper_final_owner:
                    helper_final_held_kind = helper_final_class_row[0]
                    break
            if (_type(helper_final_held_kind) is _type and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) and (helper_final_namespace.get(helper_final_owner) is helper_final_held_kind)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_names = _vars(helper_final_held_kind)
        if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_names)) and helper_final_names.get(helper_final_name) is helper_final_function) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if helper_final_kw is None:
            if (helper_final_pairs == ()) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_final_kw) is _dict and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_kw)) and (_len(helper_final_kw) == _len(helper_final_pairs))) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_final_seen = _set()
            for helper_final_pair in helper_final_pairs:
                if (_type(helper_final_pair) is _tuple and _len(helper_final_pair) == 2 and (_type(helper_final_pair[0]) is _str)) is not True:
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_final_key, helper_final_value = helper_final_pair
                if (helper_final_key not in helper_final_seen and helper_final_key in helper_final_kw and (helper_final_kw[helper_final_key] is helper_final_value)) is not True:
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_final_seen.add(helper_final_key)
        if helper_final_closure is None:
            if (helper_final_cells == ()) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_final_closure) is _tuple and _len(helper_final_closure) == _len(helper_final_cells)) is not True:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            try:
                if _all((_type(helper_final_cell) is _cell and helper_final_cell.cell_contents is helper_final_value for helper_final_cell, helper_final_value in _zip(helper_final_closure, helper_final_cells, strict=True))) is not True:
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            except _value_error:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[0][1])) and helper_final_modules[0][1].get('GatewayRecipeOwner') is helper_final_classes[2][0] and (helper_final_modules[0][1].get('_same_recipe_binding') is helper_final_functions[4][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[0][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[1][1])) and (helper_final_modules[0][1].get('StartupSelectionOwner') is helper_final_classes[3][0]) and (helper_final_modules[1][1].get('StartupSelectionOwner') is helper_final_classes[3][0]) and (helper_final_modules[0][1].get('GatewayStartupSelection') is helper_final_classes[6][0]) and (helper_final_modules[1][1].get('GatewayStartupSelection') is helper_final_classes[6][0]) and (helper_final_modules[0][1].get('IoScope') is helper_final_classes[4][0]) and (helper_final_modules[1][1].get('_Scope') is helper_final_classes[4][0]) and (helper_final_modules[1][1].get('_approved_recipe') is helper_final_functions[6][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[0][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[1][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[2][1])) and _all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[3][1])) and (helper_final_modules[0][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[1][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[2][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[2][1].get('_LATE_MODULES') is helper_final_modules[3][1].get('_LATE_MODULES'))) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[4][1])) and helper_final_modules[4][1].get('_Scope') is helper_final_classes[4][0] and (helper_final_modules[4][1].get('GatewayActivationOwner') is helper_final_classes[10][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_final_index in (0, 1, 2):
        helper_final_namespace = helper_final_modules[helper_final_index][1]
        if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_namespace)) and helper_final_namespace.get('ExpectedArtifact') is helper_final_classes[13][0] and (helper_final_namespace.get('_descriptor_closed_in_scope') is helper_final_functions[15][0]) and (helper_final_namespace.get('_expected') is helper_final_functions[19][0])) is not True:
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[5][1])) and helper_final_modules[2][1].get('_APPROVAL_OWNER_TYPE') is helper_final_classes[23][0] and (helper_final_modules[5][1].get('GatewayActivationOwner') is helper_final_classes[10][0]) and (helper_final_modules[5][1].get('_LATE_MODULES') is helper_final_modules[3][1].get('_LATE_MODULES')) and (helper_final_modules[5][1].get('ExpectedArtifact') is helper_final_classes[13][0]) and (helper_final_modules[5][1].get('_Scope') is helper_final_classes[4][0]) and (helper_final_modules[5][1].get('_descriptor_closed_in_scope') is helper_final_functions[15][0]) and (helper_final_modules[5][1].get('OperatorApprovalPath') is helper_final_classes[38][0]) and (helper_final_modules[5][1].get('_OperatorFileReceipt') is helper_final_classes[39][0]) and (helper_final_modules[5][1].get('_ReadEffect') is helper_final_classes[40][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_all((_type(helper_final_key) is _str for helper_final_key in helper_final_modules[6][1])) and helper_final_modules[5][1].get('GatewayEntryOwner') is helper_final_classes[27][0] and (helper_final_modules[6][1].get('GatewayActivationOwner') is helper_final_classes[10][0])) is not True:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (_type(started_owner) is not started_owner_kind
            or _type(started_entry_module) is not _module
            or _vars(started_entry_module) is not started_entry_names
            or _any(_type(k) is not _str for k in started_entry_names)
            or _any(_type(k) is not _str for k in environment[2])
            or environment[2].get('hmp_startup.gateway_entry') is not started_entry_module
            or started_entry_names.get('_ENTRY_ORIGIN') is not started_origin
            or started_entry_names.get('_STARTED') is not started_root
            or started_entry_names.get('_CELL') is not started_cell
            or started_entry_names.get('_OWNER') is not started_owner
            or _type(started_owner_names) is not _dict
            or _any(_type(k) is not _str for k in started_owner_names)
            or started_dict_descriptor.__get__(started_owner, started_owner_kind) is not started_owner_names
            or started_owner_names.get('_scope') is not started_invocation
            or started_owner_names.get('_started_cell') is not started_root
            or started_owner_names.get('_ready') is not True
            or started_owner_names.get('_failed') is not False
            or _tuple.__getitem__(started_origin, 10) is not origin
            or _tuple.__getitem__(started_origin, 11) is not environment[7]
            or _tuple.__getitem__(started_lineage, 4) is not origin
            or _tuple.__getitem__(started_lineage, 5) is not environment[7]):
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
            _all=all,
            _set=set,
            _value_error=ValueError,
            _bool=bool, _int=int, _list=list, _bytes=bytes, _bytearray=bytearray,
            _sum=sum, _ord=ord, _super=super,
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
    own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory', 'blueprint_factory', 'encode_basename', 'current_started')
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
    # Hold the component's original exports before invoking its capture callback.
    helper_system, helper_registry = _sys, registry
    helper_expected_builtins = (_type, _vars, _tuple, _len, _dict, _str, _any, _zip,
                                _all, _set, _error, _value_error,
                                _bool, _int, _list, _bytes, _bytearray, _sum, _ord, _super)
    helper_builtin_module = registry.get('builtins')
    if _type(helper_builtin_module) is not _module:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_builtin_namespace = _vars(helper_builtin_module)
    if (_type(helper_builtin_namespace) is not _dict
            or _any(_type(k) is not _str for k in helper_builtin_namespace)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_primitive_pairs = _tuple(_zip(
        ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
         'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True))
    if _any(helper_builtin_namespace.get(name) is not value
            for name, value in helper_primitive_pairs):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    from hmp_startup import retained_binding_origin as retained_helpers
    if (_type(retained_helpers) is not _module
            or _any(_type(k) is not _str for k in registry)
            or registry.get('hmp_startup.retained_binding_origin') is not retained_helpers):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_namespace = _vars(retained_helpers)
    if (_type(helper_namespace) is not _dict
            or _any(_type(k) is not _str for k in helper_namespace)):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_pairs = _tuple(helper_namespace.items())
    helper_functions = []
    for helper_name in ('capture', 'current'):
        helper_function = helper_namespace.get(helper_name)
        if (_type(helper_function) is not _function
                or helper_function.__globals__ is not helper_namespace
                or helper_function.__closure__ is not None):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw = helper_function.__kwdefaults__
        if (helper_kw is not None and (_type(helper_kw) is not _dict
                or _any(_type(k) is not _str for k in helper_kw))):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_functions.append((helper_name, helper_function, helper_function.__code__,
            helper_namespace, helper_function.__defaults__, helper_kw,
            () if helper_kw is None else _tuple(helper_kw.items())))
    helper_error_kind = helper_namespace.get('RetainedBindingOriginError')
    if _type(helper_error_kind) is not _type:
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if _any(_type(k) is not _str for k in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_capsule = (retained_helpers, helper_namespace, helper_pairs,
        _tuple(helper_functions),
        (helper_error_kind, helper_error_kind.__bases__, _tuple(helper_error_names.items())),
        (helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs), None)
    # Authenticate the component before dispatch; the actual parent holds this DATA.
    if (_type(helper_capsule) is not _tuple or _len(helper_capsule) != 7
            or _type(helper_capsule[0]) is not _module
            or _type(helper_capsule[1]) is not _dict
            or _type(helper_capsule[2]) is not _tuple
            or _type(helper_capsule[3]) is not _tuple or _len(helper_capsule[3]) != 2
            or _type(helper_capsule[4]) is not _tuple or _len(helper_capsule[4]) != 3
            or _type(helper_capsule[5]) is not _tuple or _len(helper_capsule[5]) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_module, helper_namespace, helper_pairs = helper_capsule[:3]
    helper_builtin_module, helper_builtin_namespace, helper_primitive_pairs = helper_capsule[5]
    if (_any(_type(k) is not _str for k in helper_registry)
            or helper_registry.get('hmp_startup.retained_binding_origin') is not helper_module
            or _vars(helper_module) is not helper_namespace
            or _any(_type(k) is not _str for k in helper_namespace)
            or _len(helper_namespace) != _len(helper_pairs)
            or helper_namespace.get('sys') is not helper_system
            or _type(helper_builtin_module) is not _module
            or _type(helper_builtin_namespace) is not _dict
            or helper_registry.get('builtins') is not helper_builtin_module
            or _vars(helper_builtin_module) is not helper_builtin_namespace
            or _any(_type(k) is not _str for k in helper_builtin_namespace)
            or helper_namespace.get('__builtins__') is not helper_builtin_namespace
            or _type(helper_primitive_pairs) is not _tuple
            or _len(helper_primitive_pairs) != 20):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_namespace
                or helper_namespace[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    for helper_pair, helper_name, helper_expected in _zip(
            helper_primitive_pairs,
            ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set',
             'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray',
             'sum', 'ord', 'super'), helper_expected_builtins, strict=True):
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str or helper_pair[0] != helper_name
                or helper_pair[1] is not helper_expected
                or helper_builtin_namespace.get(helper_name) is not helper_expected):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for helper_row, helper_name in _zip(helper_capsule[3], ('capture', 'current'), strict=True):
        if (_type(helper_row) is not _tuple or _len(helper_row) != 7
                or _type(helper_row[0]) is not _str or helper_row[0] != helper_name
                or _type(helper_row[1]) is not _function or helper_row[3] is not helper_namespace
                or helper_namespace.get(helper_name) is not helper_row[1]
                or helper_row[1].__code__ is not helper_row[2]
                or helper_row[1].__globals__ is not helper_namespace
                or helper_row[1].__builtins__ is not helper_builtin_namespace
                or helper_row[1].__defaults__ is not helper_row[4]
                or helper_row[1].__kwdefaults__ is not helper_row[5]
                or helper_row[1].__closure__ is not None
                or _type(helper_row[6]) is not _tuple):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_kw, helper_kw_pairs = helper_row[5], helper_row[6]
        if helper_kw is None:
            if _len(helper_kw_pairs) != 0:
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        else:
            if (_type(helper_kw) is not _dict or _any(_type(k) is not _str for k in helper_kw)
                    or _len(helper_kw) != _len(helper_kw_pairs)):
                raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            helper_seen = {}
            for helper_pair in helper_kw_pairs:
                if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                        or _type(helper_pair[0]) is not _str):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_key, helper_value = helper_pair
                if (helper_key in helper_seen or helper_key not in helper_kw
                        or helper_kw[helper_key] is not helper_value):
                    raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                helper_seen[helper_key] = helper_value
    helper_error_kind, helper_error_bases, helper_error_pairs = helper_capsule[4]
    if (_type(helper_error_kind) is not _type
            or helper_namespace.get('RetainedBindingOriginError') is not helper_error_kind
            or _type(helper_error_bases) is not _tuple or _len(helper_error_bases) != 1
            or helper_error_bases[0] is not helper_expected_builtins[10]
            or helper_error_kind.__bases__ is not helper_error_bases
            or _type(helper_error_pairs) is not _tuple):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_error_names = _vars(helper_error_kind)
    if (_any(_type(k) is not _str for k in helper_error_names)
            or _len(helper_error_names) != _len(helper_error_pairs)
            or '__init__' in helper_error_names or '__new__' in helper_error_names):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_seen = {}
    for helper_pair in helper_error_pairs:
        if (_type(helper_pair) is not _tuple or _len(helper_pair) != 2
                or _type(helper_pair[0]) is not _str):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_key, helper_value = helper_pair
        if (helper_key in helper_seen or helper_key not in helper_error_names
                or helper_error_names[helper_key] is not helper_value):
            raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        helper_seen[helper_key] = helper_value
    helper_packet = helper_capsule[3][0][1]()
    if (_type(helper_packet) is not _tuple or _len(helper_packet) != 6
            or helper_packet[0] is not _sys or helper_packet[1] is not sys_namespace
            or helper_packet[2] is not registry):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    helper_capsule = (*helper_capsule[:6], helper_packet)

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
    audit_record = engine_capture()
    if (_type(audit_record) is not _tuple or _len(audit_record) != 3):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    engine_origin, engine_layout, engine_check = audit_record
    if (_type(engine_origin) is not _tuple or _len(engine_origin) != 6
            or _type(engine_origin[4]) is not _tuple or _len(engine_origin[4]) != 4
            or engine_origin[4][0] is not _sys or engine_origin[4][1] is not sys_namespace
            or engine_origin[4][2] is not registry):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (engine._capture_engine is not engine_capture
            or engine_capture.__code__ is not engine_capture_code):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if (engine_origin[5] is not engine_layout
            or _type(engine_check) is not _tuple or _len(engine_check) != 7
            or _type(engine_check[0]) is not _str
            or engine_check[0] != '_engine_origin_tail'
            or _len(_tuple(row for row in engine_origin[2] if row is engine_check)) != 1):
        raise _error('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
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
        if (audit_record[0] is not engine_origin
                or audit_record[1] is not engine_layout
                or audit_record[2] is not engine_check
                or engine_capture.__code__ is not engine_capture_code
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
    result = ((_sys, sys_namespace, registry, encoding_origin, engine_origin, engine_layout, helper_capsule, audit_record), modules, own_functions, functions, kinds)
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
            or _type(origin[2]) is not _tuple or _len(origin[2]) != 8):
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
    if _type(rows) is not _tuple or _len(rows) != 8:
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
            or _len(origin[2]) != 8):
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

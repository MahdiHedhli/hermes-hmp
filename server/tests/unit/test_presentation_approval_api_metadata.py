"""Disposable native API metadata; no root API execution, files or admission."""
from importlib.machinery import ModuleSpec
import sys
from types import ModuleType

import pytest

from hmp_startup import gateway_approval as approval


@pytest.fixture
def source(monkeypatch):
    module = ModuleType('hermes_constants')
    filename = '/synthetic/hermes_constants.py'
    module.__file__ = filename
    loader = object()
    module.__spec__ = ModuleSpec('hermes_constants', loader, origin=filename)
    calls = []
    namespace = vars(module)
    namespace['api_calls'] = calls
    exec(compile('def get_default_hermes_root():\n    api_calls.append(True)\n'
                 '    raise AssertionError("native API must not execute")\n', filename, 'exec'), namespace)
    function = namespace['get_default_hermes_root']
    monkeypatch.setitem(sys.modules, 'hermes_constants', module)
    record = approval._RootSource(None, (), module, namespace, function, function.__code__,
        filename, module.__spec__, filename, loader, '/synthetic', filename)
    yield record
    assert calls == []


def test_native_api_metadata_accepts_without_executing_api(source):
    assert approval._api_state(source) is None


@pytest.mark.parametrize('where', ('registry', 'module', 'spec'))
def test_native_metadata_foreign_keys_refuse_before_comparison(source, where):
    namespace, lookup = ((sys.modules, 'hermes_constants') if where == 'registry' else
                         (source.namespace, 'get_default_hermes_root') if where == 'module' else
                         (vars(source.spec), 'origin'))
    original = namespace[lookup]
    armed = [False]
    calls = []
    target_hash = hash(lookup)

    class Foreign:
        def __hash__(self):return target_hash
        def __eq__(self, other):
            if not armed[0]:return False
            calls.append('eq')
            raise AssertionError('foreign metadata key comparison')

    key = Foreign()
    del namespace[lookup]
    namespace[key] = None
    armed[0] = True
    try:
        with pytest.raises(approval.GatewayApprovalError):approval._api_state(source)
    finally:
        armed[0] = False
        namespace.pop(key)
        namespace[lookup] = original
    assert calls == []


def test_native_metadata_file_type_refuses_without_foreign_equality(source):
    calls = []

    class Foreign:
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign file comparison')

    changed = source._replace(file=Foreign())
    with pytest.raises(approval.GatewayApprovalError):approval._api_state(changed)
    assert calls == []


def test_native_metadata_avoids_mutable_spec_getattribute(source, monkeypatch):
    calls = []
    original = ModuleSpec.__getattribute__

    def foreign(self, name):
        if name == '__dict__':
            calls.append(name)
            raise AssertionError('mutable spec getter executed')
        return original(self, name)

    with monkeypatch.context() as patch:
        patch.setattr(ModuleSpec, '__getattribute__', foreign)
        assert approval._api_state(source) is None
    assert calls == []


@pytest.mark.parametrize('field', ('source', 'module', 'namespace', 'spec'))
def test_native_metadata_foreign_fields_refuse_without_getters(source, field):
    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign metadata field getter')

    changed = Foreign() if field == 'source' else source._replace(**{field: Foreign()})
    with pytest.raises(approval.GatewayApprovalError):approval._api_state(changed)
    assert calls == []


def test_native_metadata_foreign_registry_refuses_without_protocols(source):
    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign registry protocol')

    original = sys.modules
    caught = None
    try:
        sys.modules = Foreign()
        try:approval._api_state(source)
        except approval.GatewayApprovalError as error:caught = error
    finally:sys.modules = original
    assert type(caught) is approval.GatewayApprovalError and calls == []


@pytest.mark.parametrize('kind', ('foreign', 'wrong-owner', 'wrong-name'))
def test_native_metadata_rejects_substitute_descriptor_without_access(source, kind):
    from types import FunctionType
    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign descriptor access')

    descriptor = (Foreign() if kind == 'foreign' else
                  FunctionType.__dict__['__code__'] if kind == 'wrong-owner' else
                  ModuleSpec.__dict__['__weakref__'])
    with pytest.raises(approval.GatewayApprovalError):
        approval._api_state(source, _spec_dict=descriptor)
    assert calls == []

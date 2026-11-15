"""Malformed typed cache DATA must refuse before invoking foreign hooks or IO."""
from types import SimpleNamespace

import pytest
from hmp_startup import cache_reader

from hmp_plugin import presentation_startup_artifacts as artifacts


@pytest.mark.parametrize('field', ('descriptor', 'effect', 'reads'))
def test_cache_native_preflight_rejects_foreign_fields_without_hooks(monkeypatch, field):
    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign attribute invoked')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length invoked')

    owner = object.__new__(cache_reader.DeclaredCacheReadOwner)
    scope = SimpleNamespace(reads=[])
    registration = object()
    values = dict.fromkeys(artifacts._NativeReadConsumer._fields)
    values.update(owner=owner, scope=scope, registration=registration,
                  descriptor=artifacts._NativeOpenedDescriptor(None, 1234, None),
                  effect=[None], requested=4096)
    if field == 'reads':
        scope.reads = Foreign()
    else:
        values[field] = Foreign()
    consumer = artifacts._NativeReadConsumer(**values)
    monkeypatch.setattr(cache_reader, '_capture_native_work_origin', lambda *args: object())
    monkeypatch.setattr(cache_reader, '_native_walk_scope', lambda *args: scope)
    with pytest.raises(cache_reader.CacheReadError):
        owner._read_native(1234, 4096, scope, registration, consumer)
    assert calls == []
    assert vars(owner) == {}  # no journal, debit, claim or reader mutation

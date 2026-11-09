"""Refuse constructor side effects before scope publication or registration."""
import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts
from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner


@pytest.mark.parametrize('mutation', ('returned_field', 'owner_slot', 'records', 'activation_slot', 'guard_alias'))
def test_startup_scope_constructor_cannot_publish_changed_state(monkeypatch, mutation):
    activation = object.__new__(GatewayActivationOwner)
    activation._artifact_owner = activation._artifact_cell = None
    activation._artifact_attempt_cell = activation._artifact_fact_cell = None
    activation._scope = object()
    monkeypatch.setattr(GatewayActivationOwner, 'current', classmethod(lambda cls, owner: None))
    kind = artifacts._Scope
    original = kind.__new__
    foreign = object()
    foreign_calls = []
    registered = []
    monkeypatch.setattr(artifacts, '_register_native_scope', lambda *args: registered.append(args))

    def changed(cls, *values):
        owner = activation._artifact_owner
        if mutation == 'guard_alias':
            monkeypatch.setattr(artifacts, '_require', lambda value: foreign_calls.append(value))
        elif mutation == 'owner_slot':
            owner._scope = foreign
        elif mutation == 'records':
            values[4].append(foreign)
        elif mutation == 'activation_slot':
            activation._artifact_cell = foreign
        elif mutation == 'returned_field':
            values = (*values[:2], (), *values[3:])
        return original(cls, *values)

    monkeypatch.setattr(kind, '__new__', staticmethod(changed))
    expected = (object(),)
    with pytest.raises(artifacts.ArtifactObservationError) as caught:
        artifacts.StartupArtifactOwner._retain(activation, expected, None)
    owner = caught.value.failed_owner
    assert owner is activation._artifact_owner
    assert owner._failed is True
    assert owner._origin is None
    assert owner._scope is (foreign if mutation == 'owner_slot' else None)
    assert owner._cell is owner._root_cell is None
    if mutation == 'activation_slot':
        assert activation._artifact_cell is foreign
    assert registered == []
    assert foreign_calls == []

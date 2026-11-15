"""Shared stages refuse a foreign operation before accessing it."""
import pytest

from hmp_plugin import presentation_native_metadata as metadata
from hmp_plugin.presentation_startup_artifacts import ArtifactObservationError


@pytest.mark.parametrize('stage', ('produce', 'consume', 'ack'))
def test_shared_probe_stage_refuses_foreign_operation_without_hooks(stage):
    hooks = []

    class ForeignOperation:
        def __getattribute__(self, name):
            hooks.append(name)
            raise AssertionError('foreign operation accessed')

    consumer = metadata._ProbeConsumer(None, ForeignOperation(), None, [None], ())
    function, arguments = {
        'produce': (metadata._produce_probe_shared, (None, consumer)),
        'consume': (metadata._consume_probe_shared, (None, consumer, object())),
        'ack': (metadata._ack_probe_shared, (None, consumer, object(), object())),
    }[stage]
    with pytest.raises(ArtifactObservationError):
        function(*arguments)
    assert hooks == []

"""New graph checkers must be retained before later code/metadata drift."""
import importlib
import sys

import pytest

from hmp_plugin import presentation_startup_artifacts as artifacts
from hmp_startup import retained_binding_origin as origin

NAMES = ('_closed_file_graph_mirrors', '_scope_file_graph_mirrors',
         '_loaded_owner_graph_mirrors', '_cache_context_graph_mirrors',
         '_approval_graph_mirrors', '_entry_graph_mirrors',
         '_activation_graph_mirrors', '_native_io_graph_mirrors',
         '_interpreter_graph_mirrors')


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('drift', ['code', 'defaults', 'keyword_defaults'])
def test_graph_checker_drift_refuses_without_dispatch(monkeypatch, name, drift):
    importlib.import_module('hmp_startup.gateway_approval')
    packet = origin.capture()
    function = getattr(artifacts, name)
    calls = []

    def foreign(*args, **kwargs):
        raise AssertionError('changed graph checker dispatched')

    def observe(frame, event, value):
        if event == 'call' and frame.f_code is foreign.__code__:
            calls.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with monkeypatch.context() as change:
            if drift == 'code':
                assert function.__code__.co_freevars == foreign.__code__.co_freevars == ()
                change.setattr(function, '__code__', foreign.__code__)
            elif drift == 'defaults':
                change.setattr(function, '__defaults__', (object(),))
            else:
                change.setattr(function, '__kwdefaults__', {'unexpected': object()})
            with pytest.raises(origin.RetainedBindingOriginError):
                origin.current(packet)
    finally:
        sys.setprofile(None)
    assert calls == []
    assert origin.current(packet) is packet

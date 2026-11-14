"""Synthetic automatic-GC dictionary mutation at the selected DATA checker."""
import ast
import gc
from pathlib import Path
import sys

import pytest

from hmp_startup import gateway_approval  # Complete normal entry/selection aliases.
from hmp_startup import retained_binding_origin as origin
from hmp_plugin import presentation_gateway_package as package


@pytest.mark.parametrize('where', ('component', 'parent'))
def test_gc_callback_cannot_invoke_foreign_key_equality(monkeypatch, where):
    module = origin
    if where == 'parent':
        from hmp_startup import link_factory_origin as module
        monkeypatch.setattr(module, '_CAPTURE_STARTED', False)
    packet = module.capture()
    checker = module.current
    expected_error = origin.RetainedBindingOriginError if where == 'component' else RuntimeError
    tree = ast.parse(Path(module.__file__).read_text())
    current = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name == 'current')
    boundary = [n for n in ast.walk(current) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == 'all'
                and len(n.args) == 1 and isinstance(n.args[0], ast.GeneratorExp)
                and isinstance(n.args[0].generators[0].iter, ast.Name)
                and n.args[0].generators[0].iter.id == 'live_keys']
    if boundary:
        assert len(boundary) == 1
        target_line = boundary[0].lineno
    else:
        boundary = [n for n in ast.walk(current) if isinstance(n, ast.For)
                    and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Attribute)
                    and isinstance(n.iter.func.value, ast.Name)
                    and n.iter.func.value.id.endswith('namespace') and n.iter.func.attr == 'items']
        assert len(boundary) == 1
        target_line = boundary[0].lineno
    if where == 'parent':
        # The parent case exercises its actual prefix fence. It is an earlier
        # allocation window, not the component's post-key-fence causal witness.
        assignment = next(n for n in ast.walk(current) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Tuple) and any(
                              isinstance(item, ast.Name) and item.id == 'helper_final_namespace'
                              for item in t.elts) for t in n.targets))
        target_line = min(n.lineno for n in ast.walk(current)
                          if isinstance(n, ast.If) and n.lineno > assignment.lineno)
    namespace_name = 'namespace' if where == 'component' else 'helper_final_namespace'
    namespace = vars(package)
    original = namespace['_require']
    calls = []
    mutated = []
    refused = False
    refusal_type = refusal_args = None
    observed = set()

    class ForeignKey:
        def __hash__(self):
            return hash('_require')

        def __eq__(self, other):
            calls.append('foreign equality')
            raise AssertionError('foreign equality ran inside checker')

    foreign = ForeignKey()

    def callback(phase, details):
        if phase != 'start' or mutated:
            return
        frame = sys._getframe()
        while frame is not None:
            if frame.f_code is checker.__code__:
                if frame.f_locals.get(namespace_name) is namespace:
                    observed.add(frame.f_lineno)
                    if frame.f_lineno == target_line:
                        namespace.pop('_require')
                        namespace[foreign] = original
                        mutated.append(True)
                return
            frame = frame.f_back

    enabled, thresholds = gc.isenabled(), gc.get_threshold()
    gc.disable()
    # Genuine cyclic garbage and an allocation threshold, not a trace hook or
    # explicit collection from inside the checker, cause the callback.
    for _ in range(50):
        cycle = []
        cycle.append(cycle)
    cycle = None
    gc.callbacks.append(callback)
    try:
        gc.set_threshold(1, 1, 1)
        gc.enable()
        try:
            checker(packet)
        except expected_error as caught:
            refused = True
            refusal_type, refusal_args = type(caught), caught.args
        finally:
            gc.disable()
    finally:
        gc.callbacks.remove(callback)
        if mutated:
            namespace.pop(foreign)
            namespace['_require'] = original
        gc.set_threshold(*thresholds)
        if enabled:
            gc.enable()
    assert mutated == [True], (target_line, sorted(observed))
    assert refused is True
    assert refusal_type is expected_error
    assert refusal_args == (('BI1_RETAINED_HELPER_ORIGIN_REFUSED' if where == 'component'
                             else 'BI1_LINK_FACTORY_ORIGIN_REFUSED'),)
    assert calls == []

"""Immutable layout correspondence; not effect authority or image delivery."""
import pytest

from hmp_plugin import presentation_native_link as link
from .test_presentation_link_metadata_boundary import Foreign


def test_capture_retains_original_rows_and_columns_without_live_state_cache():
    origin = link._capture_engine()
    assert len(origin) == 6 and origin[5][0] is origin[4]
    for (module, classes), original in zip(origin[5][1], origin[4][3], strict=True):
        assert module is original
        for (row, keys, values), actual in zip(classes, original[4], strict=True):
            assert row is actual
            assert type(keys) is type(values) is tuple
            for pair, key, value in zip(row[2], keys, values, strict=True):
                assert pair[0] is key and pair[1] is value
    assert link._engine_origin_tail(origin) is origin


@pytest.mark.parametrize('slot', ('layout', 'modules', 'module_row', 'classes',
                                  'class_row', 'keys', 'values', 'key'))
def test_layout_fences_foreign_protocols_before_correspondence_use(slot):
    origin = link._capture_engine()
    calls = []
    foreign = Foreign(calls)
    layout = origin[5]
    modules = list(layout[1])
    index = next(i for i, row in enumerate(modules) if row[1])
    module, classes = modules[index]
    classes = list(classes)
    row, keys, values = classes[0]
    if slot == 'layout':
        changed = foreign
    elif slot == 'modules':
        changed = (layout[0], foreign)
    else:
        if slot == 'module_row':
            modules[index] = foreign
        elif slot == 'classes':
            modules[index] = (module, foreign)
        else:
            if slot == 'class_row':
                classes[0] = foreign
            elif slot == 'keys':
                classes[0] = (row, foreign, values)
            elif slot == 'values':
                classes[0] = (row, keys, foreign)
            else:
                classes[0] = (row, (foreign, *keys[1:]), values)
            modules[index] = (module, tuple(classes))
        changed = (layout[0], tuple(modules))
    with pytest.raises(link.ArtifactObservationError):
        link._engine_origin_tail((*origin[:5], changed))
    assert calls == []


@pytest.mark.parametrize('fault', ('dependency_copy', 'module_copy', 'class_copy',
                                   'missing_key', 'duplicate_key', 'value'))
def test_layout_rejects_copied_rows_and_noncorresponding_columns(fault):
    origin = link._capture_engine()
    layout = origin[5]
    modules = list(layout[1])
    index = next(i for i, row in enumerate(modules)
                 if any(len(c[1]) >= 2 for c in row[1]))
    module, classes = modules[index]
    classes = list(classes)
    cindex = next(i for i, c in enumerate(classes) if len(c[1]) >= 2)
    row, keys, values = classes[cindex]
    if fault == 'dependency_copy':
        changed = (tuple(list(layout[0])), layout[1])
    else:
        if fault == 'module_copy':
            modules[index] = (tuple(list(module)), tuple(classes))
        else:
            if fault == 'class_copy':
                classes[cindex] = (tuple(list(row)), keys, values)
            elif fault == 'missing_key':
                classes[cindex] = (row, keys[:-1], values)
            elif fault == 'duplicate_key':
                classes[cindex] = (row, (keys[0], keys[0], *keys[2:]), values)
            else:
                classes[cindex] = (row, keys, (object(), *values[1:]))
            modules[index] = (module, tuple(classes))
        changed = (layout[0], tuple(modules))
    with pytest.raises(link.ArtifactObservationError):
        link._engine_origin_tail((*origin[:5], changed))


@pytest.mark.parametrize('fault', ('value', 'renamed_none', 'extra', 'reordered'))
def test_live_class_columns_compare_keys_before_none_values(monkeypatch, fault):
    """A missing None-valued key must not masquerade as a successful get()."""
    import sys
    from pathlib import Path

    from hmp_plugin import presentation_metadata_custody as custody

    kind = custody._DirectoryPayload
    name = '_synthetic_none_column'
    monkeypatch.setattr(kind, name, None, raising=False)
    original = link._capture_engine()
    assert link._engine_origin_tail(original) is original
    calls = []
    if fault == 'value':
        monkeypatch.setattr(kind, name, Foreign(calls))
    elif fault == 'renamed_none':
        monkeypatch.delattr(kind, name)
        monkeypatch.setattr(kind, name + '_renamed', None, raising=False)
    elif fault == 'extra':
        monkeypatch.setattr(kind, name + '_extra', None, raising=False)
    else:
        monkeypatch.delattr(kind, name)
        monkeypatch.setattr(kind, name, None, raising=False)

    code = link._engine_origin_tail.__code__
    source = Path(code.co_filename).read_text().splitlines()
    end = max(line for _, _, line in code.co_lines() if line is not None)
    boundary = [i + 1 for i in range(code.co_firstlineno - 1, end)
                if 'if ' in source[i] and '_map(_type, names)' in source[i]]
    assert len(boundary) == 1
    observed = []

    def trace(frame, event, value):
        if frame.f_code is not code:
            return None
        if (event == 'line' and frame.f_lineno == boundary[0]
                and frame.f_locals.get('kind') is kind):
            observed.append(True)
        return trace

    prior = sys.gettrace()
    assert prior is None
    sys.settrace(trace)
    try:
        if fault == 'reordered':
            assert link._engine_origin_tail(original) is original
        else:
            with pytest.raises(link.ArtifactObservationError):
                link._engine_origin_tail(original)
    finally:
        sys.settrace(prior)
    assert observed and calls == []

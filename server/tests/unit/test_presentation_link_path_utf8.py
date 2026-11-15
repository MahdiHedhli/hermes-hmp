"""Generic executable-link path validation preserves its original public contract."""
import sys

import pytest

from hmp_plugin import presentation_link_path_policy as policy


def original_parts(path):
    policy._need(type(path) is str and 1 < len(path) <= 4096
                 and path.startswith('/')
                 and all(32 <= ord(c) != 127 and not 0xD800 <= ord(c) <= 0xDFFF
                         for c in path))
    parts = tuple(path[1:].split('/'))
    policy._need(1 <= len(parts) <= 64 and 1 < len(path.encode('utf-8')) <= 4096
                 and all(part not in ('', '.', '..') for part in parts))
    return ('/', *parts)


def outcome(function, path):
    try:
        return ('returned', function(path))
    except policy.ArtifactObservationError:
        return ('refused',)


def test_every_unicode_codepoint_preserves_original_path_results():
    for point in range(0x110000):
        path = '/a' + chr(point) + '/leaf'
        assert outcome(policy._parts, path) == outcome(original_parts, path), point


@pytest.mark.parametrize('path', [
    '', '/', 'relative', '//leaf', '/a//leaf', '/a/', '/./leaf', '/../leaf',
    '/a/./leaf', '/a/../leaf', '/leaf/.', '/leaf/..',
    '/a' + '/b' * 63, '/a' + '/b' * 64,
    '/' + 'a' * 4095, '/' + 'a' * 4096,
    '/' + 'é' * 2047 + 'a', '/' + 'é' * 2048,
    '/' + '\U00010000' * 1023 + 'abc', '/' + '\U00010000' * 1024,
    '/leaf\x00', '/\x1fleaf', '/leaf\x7f', '/\ud800leaf', '/leaf\udfff',
    '/a b/é/日本語', '/\x85/\u200b/\U0010ffff', None, b'/leaf', 7,
])
def test_path_boundary_results_match_original(path):
    assert outcome(policy._parts, path) == outcome(original_parts, path)


@pytest.mark.parametrize('method', ('__len__', 'startswith', 'encode', '__getitem__'))
def test_foreign_string_subclass_never_runs_hooks(method):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign path method ran')

    kind = type('ForeignPath', (str,), {method: foreign})
    with pytest.raises(policy.ArtifactObservationError):
        policy._parts(kind('/leaf'))
    assert calls == []


@pytest.mark.parametrize('path', ['/\ud800leaf', '/leaf\udfff'])
def test_surrogate_refusal_retains_no_encoding_error_context(path):
    with pytest.raises(policy.ArtifactObservationError) as caught:
        policy._parts(path)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


@pytest.mark.parametrize('path', ['/valid/leaf', '/leaf\x00', '/\ud800leaf',
                                  'relative', '/' + 'é' * 2048, '/a//leaf'])
def test_original_project_guard_call_sequence_is_preserved(monkeypatch, path):
    original_need = policy._need
    traces = []
    for function in (original_parts, policy._parts):
        calls = []

        def recorded(value, calls=calls):
            calls.append(value)
            return original_need(value)

        with monkeypatch.context() as scoped:
            scoped.setattr(policy, '_need', recorded)
            result = outcome(function, path)
        traces.append((calls, result))
    assert traces[0] == traces[1]


@pytest.mark.parametrize('path', ['/leaf\x00', '/\ud800leaf'])
def test_invalid_characters_cannot_cross_a_successful_guard_callback(monkeypatch, path):
    original_need = policy._need
    successful = []
    foreign = []

    def changed(value):
        foreign.append(value)
        raise AssertionError('replacement guard executed')

    def observed(value):
        if value is True:
            successful.append(True)
            monkeypatch.setattr(policy, '_need', changed)
        return original_need(value)

    monkeypatch.setattr(policy, '_need', observed)
    with pytest.raises(policy.ArtifactObservationError):
        policy._parts(path)
    assert successful == foreign == []


@pytest.mark.parametrize('replacement', ['/' + 'a' * 4096, '/' + 'é' * 2048,
                                          '/changed/valid'])
def test_byte_bound_reads_current_path_after_original_guard_return(replacement):
    results = []
    for function in (original_parts, policy._parts):
        ready, changed, witnessed = [], [], []
        code, guard_code = function.__code__, policy._need.__code__

        def observe(frame, event, value, code=code, guard_code=guard_code,
                    ready=ready, changed=changed, witnessed=witnessed):
            if event == 'call':
                if frame.f_code not in (code, guard_code):
                    return None
                frame.f_trace_lines = frame.f_code is code
            if (event == 'return' and frame.f_code is guard_code
                    and frame.f_back.f_code is code and not ready):
                ready.append(True)
            if event == 'line' and frame.f_code is code and ready:
                if not changed:
                    frame.f_locals['path'] = replacement
                    changed.append(True)
                else:
                    assert frame.f_locals['path'] is replacement
                    witnessed.append(True)
            return observe

        previous = sys.gettrace()
        assert previous is None
        sys.settrace(observe)
        try:
            result = outcome(function, '/original/leaf')
        finally:
            sys.settrace(previous)
        assert ready == changed == [True] and witnessed
        results.append(result)
    assert results[0] == results[1]

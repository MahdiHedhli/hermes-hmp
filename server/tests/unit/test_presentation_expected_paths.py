"""Actual artifact validator preserves its exact ASCII-control path boundary."""
import pytest

from hmp_plugin.presentation_startup_artifacts import (
    ArtifactObservationError, ExpectedArtifact, _expected,
)


@pytest.mark.parametrize('codepoint', [*range(32), 127])
def test_ascii_control_rejected_at_every_path_position(codepoint):
    for path in ('/' + chr(codepoint) + 'leaf', '/a' + chr(codepoint) + '/leaf',
                 '/leaf' + chr(codepoint)):
        with pytest.raises(ArtifactObservationError):
            _expected((ExpectedArtifact(path, 0, '0' * 64),))


@pytest.mark.parametrize('path', ['/a b/module.py', '/é/日本語.py', '/a\x85/leaf',
                                  '/a\u200b/leaf', '/a\U0010ffff/leaf'])
def test_non_ascii_and_space_preserve_existing_acceptance(path):
    _expected((ExpectedArtifact(path, 0, '0' * 64),))


@pytest.mark.parametrize('codepoint', [*range(256), 0x200b, 0xffff, 0x10ffff])
def test_digest_alphabet_at_start_middle_and_end(codepoint):
    character = chr(codepoint)
    for offset in (0, 31, 63):
        digest = 'a' * offset + character + 'a' * (63 - offset)
        row = ExpectedArtifact('/synthetic/leaf', 0, digest)
        if character in '0123456789abcdef':
            _expected((row,))
        else:
            with pytest.raises(ArtifactObservationError):
                _expected((row,))


@pytest.mark.parametrize('digest', ['', 'a' * 63, 'a' * 65, b'a' * 64, None])
def test_digest_length_and_exact_type_remain_required(digest):
    with pytest.raises(ArtifactObservationError):
        _expected((ExpectedArtifact('/synthetic/leaf', 0, digest),))


def test_digest_subclass_cannot_run_strip():
    calls = []

    class ForeignDigest(str):
        def strip(self, characters=None):
            calls.append(characters)
            return ''

    with pytest.raises(ArtifactObservationError):
        _expected((ExpectedArtifact('/synthetic/leaf', 0, ForeignDigest('a' * 64)),))
    assert calls == []

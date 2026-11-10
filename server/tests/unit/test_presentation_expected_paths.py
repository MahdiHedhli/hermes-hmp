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
